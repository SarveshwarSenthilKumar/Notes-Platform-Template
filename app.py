
from flask import Flask, render_template, request, redirect, session, jsonify, flash, url_for
from flask_session import Session
from datetime import datetime, date
import pytz
import os
import re
from dotenv import load_dotenv
from sql import *  # Used for database connection and management
from SarvAuth import *  # Used for user authentication functions
from auth import auth_blueprint
from dictionary_routes import dict_bp as dictionary_blueprint
from notes_routes import notes_bp as notes_blueprint
from test_routes import test_bp as test_blueprint
from calendar_routes import calendar_bp as calendar_blueprint
from ai_routes import ai_bp as ai_blueprint

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Test route to verify environment variables
@app.route('/test-env')
def test_env():
    gemini_key = os.getenv('GEMINI_API_KEY')
    return f"GEMINI_API_KEY is set: {'Yes' if gemini_key else 'No'}"

# Configure session
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config['SECRET_KEY'] = os.urandom(24)  # Required for flash messages

# Initialize extensions
Session(app)

# Initialize blueprints
def init_blueprints(app):
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(dictionary_blueprint, url_prefix='/dictionary')
    app.register_blueprint(notes_blueprint, url_prefix='/notes')
    app.register_blueprint(calendar_blueprint, url_prefix='/calendar')
    app.register_blueprint(ai_blueprint, url_prefix='/ai')
    
    # Initialize test blueprint
    from test_routes import init_app as init_test_app
    init_test_app(app)

# Initialize all blueprints
init_blueprints(app)

# Configuration
autoRun = True  # Set to True to run the server automatically when app.py is executed
port = 5000  # Change to any available port
authentication = True  # Set to False to disable authentication

# This route always redirects to the dictionary
@app.route("/", methods=["GET"])
def index():
    return redirect(url_for('dictionary.index'))

@app.route('/search')
def search():
    """Unified search across dictionary and notes"""
    query = request.args.get('q', '').strip()
    
    dictionary_results = []
    notes_results = []
    
    if query:
        # Clean and prepare the query
        clean_query = ' '.join(word for word in query.split() if len(word) > 2)
        if not clean_query:
            return render_template('search.html',
                               query=query,
                               dictionary_results=[],
                               notes_results=[])
        
        # Search in dictionary
        try:
            db = SQL("sqlite:///dictionary.db")
            
            # Use a simple LIKE query that works with the existing schema
            dict_query = """
                SELECT id, word_phrase, 
                       substr(definition, 1, 200) || '...' as definition
                FROM entries
                WHERE LOWER(word_phrase) LIKE LOWER(:query) 
                   OR LOWER(definition) LIKE LOWER(:query)
                LIMIT 10
            """
            dictionary_results = db.execute(dict_query, query=f"%{clean_query}%")
                    
        except Exception as e:
            app.logger.error(f"Error searching dictionary: {str(e)}")
            dictionary_results = []
        
        # Search in notes
        try:
            db = SQL("sqlite:///notes.db")
            
            # Use a simple LIKE query that works with the existing schema
            notes_query = """
                SELECT id, title, 
                       substr(content, 1, 200) || '...' as content
                FROM notes
                WHERE LOWER(title) LIKE LOWER(:query) 
                   OR LOWER(content) LIKE LOWER(:query)
                LIMIT 10
            """
            notes_results = db.execute(notes_query, query=f"%{clean_query}%")
                    
        except Exception as e:
            app.logger.error(f"Error searching notes: {str(e)}")
            notes_results = []
    
    # Highlight the search terms in the results
    for result in dictionary_results:
        if 'word_phrase' in result:
            result['word_phrase'] = highlight_text(result['word_phrase'], clean_query)
        if 'definition' in result and result['definition']:
            result['definition'] = highlight_text(result['definition'], clean_query)
    
    for result in notes_results:
        if 'title' in result:
            result['title'] = highlight_text(result['title'], clean_query)
        if 'content' in result and result['content']:
            result['content'] = highlight_text(result['content'], clean_query)
    
    return render_template('search.html',
                         query=query,
                         dictionary_results=dictionary_results,
                         notes_results=notes_results)

def highlight_text(text, query):
    """Highlight search terms in the text"""
    if not text or not query:
        return text or ''
    
    try:
        # Escape special regex characters in the query
        query = re.escape(query)
        # Create a case-insensitive regex pattern
        pattern = re.compile(f'({query})', re.IGNORECASE)
        # Replace matches with highlighted span
        return pattern.sub(r'<span class="highlight">\1</span>', text)
    except Exception as e:
        app.logger.error(f"Error highlighting text: {str(e)}")
        return text

# Add a custom filter to highlight text in search results
@app.template_filter('highlight')
def highlight_filter(s, query):
    if not query or not s:
        return s
    try:
        query = re.escape(query)
        return re.sub(f'({query})', 
                     r'<span class="highlight">\1</span>', 
                     s, 
                     flags=re.IGNORECASE)
    except:
        return s

def get_db_connection(db_name):
    """Create and return a database connection"""
    return SQL(f"sqlite:///{db_name}")

def close_db_connection(db):
    """Close a database connection if it exists"""
    if db and hasattr(db, 'db') and db.db:
        try:
            db.db.close()
        except Exception as e:
            print(f"Error closing database connection: {e}")
        # Clear the connection
        db.db = None

@app.route('/api/search/dictionary')
def api_search_dictionary():
    """API endpoint for searching dictionary entries"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    db = None
    try:
        # Get database connection
        db = get_db_connection('dictionary.db')
        # Search in word_phrase, definition, and example fields
        results = db.execute("""
            SELECT id, word_phrase, definition, example, 
                   (CASE 
                       WHEN word_phrase LIKE ? THEN 1  -- Highest priority: exact match at start of word_phrase
                       WHEN word_phrase LIKE ? THEN 2  -- High priority: match at start of word_phrase
                       WHEN definition LIKE ? OR example LIKE ? THEN 3  -- Medium priority: match in definition or example
                       ELSE 4  -- Lower priority: match anywhere in word_phrase
                    END) as priority
            FROM entries
            WHERE word_phrase LIKE ? OR definition LIKE ? OR example LIKE ?
            ORDER BY priority, word_phrase
            LIMIT 5
        """, 
        f"{query}%", f"%{query}%", f"%{query}%", f"%{query}%", 
        f"%{query}%", f"%{query}%", f"%{query}%")
        
        return jsonify(results)
    except Exception as e:
        print(f"Error in dictionary search: {str(e)}")
        return jsonify({"error": "An error occurred while searching the dictionary"}), 500
    finally:
        if db:
            close_db_connection(db)

@app.route('/api/search/notes')
def api_search_notes():
    """API endpoint for searching notes"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    db = None
    try:
        # Get database connection
        db = get_db_connection('notes.db')
        
        # Split query into individual words for more flexible searching
        search_terms = [f"%{term}%" for term in query.split() if term.strip()]
        if not search_terms:
            return jsonify([])
            
        # Build the WHERE clause to search in title or content
        where_conditions = []
        params = []
        
        for term in search_terms:
            where_conditions.append("(title LIKE ? OR content LIKE ?)")
            params.extend([term, term])
            
        where_clause = " OR ".join(where_conditions)
        
        # Search in title and content fields with priority to title matches
        results = db.execute(f"""
            SELECT id, title, content, last_updated,
                   (CASE 
                       WHEN title LIKE ? THEN 1  -- Highest priority: match in title
                       ELSE 2  -- Lower priority: match in content
                    END) as priority
            FROM notes
            WHERE {where_clause}
            ORDER BY priority, last_updated DESC
            LIMIT 5
        """, *([f"%{query}%"] + params))
        
        # Format the results with highlighted content
        formatted_results = []
        for row in results:
            # Find the position of the first match in content for snippet
            content_lower = row['content'].lower()
            query_lower = query.lower()
            match_pos = content_lower.find(query_lower)
            
            # Create a snippet around the match (50 chars before and after)
            if match_pos >= 0:
                start = max(0, match_pos - 50)
                end = min(len(row['content']), match_pos + len(query) + 50)
                snippet = ('...' if start > 0 else '') + row['content'][start:end] + ('...' if end < len(row['content']) else '')
            else:
                snippet = row['content'][:150] + ('...' if len(row['content']) > 150 else '')
            
            formatted_results.append({
                'id': row['id'],
                'title': row['title'],
                'content': row['content'],  # Include full content for client-side highlighting
                'snippet': snippet,        # Include a snippet for the preview
                'last_updated': row['last_updated']
            })
        
        return jsonify(formatted_results)
    except Exception as e:
        print(f"Error in notes search: {str(e)}")
        app.logger.error(f"API search error (notes): {str(e)}")
        return jsonify({"error": "An error occurred while searching notes"}), 500
    finally:
        if db:
            close_db_connection(db)

if autoRun:
    if __name__ == '__main__':
        app.run(debug=True, port=port, use_reloader=False)
