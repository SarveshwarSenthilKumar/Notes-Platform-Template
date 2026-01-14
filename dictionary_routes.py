from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, abort, jsonify
from sql import SQL
import sqlite3
from datetime import datetime
import re

def render_entry(entry_id, is_public=False):
    """Helper function to render an entry (used by both public and authenticated views)"""
    db = SQL("sqlite:///dictionary.db")
    
    try:
        # Increment view count only for public views
        if is_public:
            db.execute("""
                UPDATE entries 
                SET views = COALESCE(views, 0) + 1 
                WHERE id = :id
            """, id=entry_id)
        
        # Get the entry with all fields
        entry = db.execute("""
            SELECT id, word_phrase, definition, example, views, unit_number, comments,
                   strftime('%Y-%m-%d', created_at) as created_date,
                   strftime('%Y-%m-%d', last_updated) as last_updated
            FROM entries 
            WHERE id = :id
        """, id=entry_id)
        
        if not entry:
            flash('Entry not found', 'error')
            return redirect(url_for('dictionary.index'))
            
        # Get related terms
        related_terms = get_related_terms(entry[0]['word_phrase'], entry_id)
        
        return render_template('dictionary/entry.html', 
                            entry=entry[0], 
                            related_terms=related_terms,
                            is_public=is_public)
    except Exception as e:
        current_app.logger.error(f"Error in render_entry for entry {entry_id}: {str(e)}")
        flash('An error occurred while loading the entry', 'error')
        return redirect(url_for('dictionary.index'))

# Initialize Blueprint
dict_bp = Blueprint('dictionary', __name__, url_prefix='/dictionary')

def get_related_terms(word_phrase, current_id=None, limit=5):
    """Find related terms based on word similarity"""
    if not word_phrase:
        return []
    
    # Extract keywords (simple approach - split by spaces and common separators)
    keywords = re.findall(r'\b\w+\b', word_phrase.lower())
    if not keywords:
        return []
    
    # Build a query to find related terms
    db = SQL("sqlite:///dictionary.db")
    
    # Create a list to hold conditions and params
    conditions = []
    params = {}
    
    # Add conditions for each keyword
    for i, keyword in enumerate(keywords[:3]):  # Limit to first 3 keywords
        if len(keyword) > 2:  # Only consider words longer than 2 characters
            conditions.append(f"(word_phrase LIKE :kw{i} OR definition LIKE :kw{i})")
            params[f'kw{i}'] = f'%{keyword}%'
    
    if not conditions:
        return []
    
    # Build the query
    query = """
        SELECT id, word_phrase, definition, 
               (SELECT COUNT(*) FROM entries e2 WHERE e2.id != entries.id 
                AND (e2.word_phrase LIKE '%' || entries.word_phrase || '%' 
                     OR entries.word_phrase LIKE '%' || e2.word_phrase || '%')) as relevance
        FROM entries
        WHERE (""" + " OR ".join(conditions) + ")"
    
    if current_id:
        query += " AND id != :current_id"
        params['current_id'] = current_id
    
    query += """
        GROUP BY id
        ORDER BY relevance DESC, LENGTH(word_phrase) ASC
        LIMIT :limit
    """
    
    params['limit'] = limit
    
    try:
        return db.execute(query, **params)
    except Exception as e:
        current_app.logger.error(f"Error finding related terms: {str(e)}")
        return []

@dict_bp.route('')
def index():
    
    db = SQL("sqlite:///dictionary.db")
    entries = db.execute("""
        SELECT id, word_phrase, definition, example, views, 
               strftime('%Y-%m-%d', created_at) as created_date
        FROM entries 
        ORDER BY word_phrase ASC
    """)
    return render_template("dictionary/index.html", entries=entries)

@dict_bp.route('/add', methods=['GET', 'POST'])
def add_entry():
    if not session.get("name"):
        return redirect("/auth/login")
        
    if request.method == 'POST':
        word_phrase = request.form.get('word_phrase', '').strip()
        definition = request.form.get('definition', '').strip()
        example = request.form.get('example', '').strip()
        unit_number = request.form.get('unit_number', '').strip()
        comments = request.form.get('comments', '').strip()
        
        if not word_phrase or not definition:
            flash('Word/Phrase and Definition are required', 'error')
            return render_template('dictionary/add.html', 
                                word_phrase=word_phrase,
                                definition=definition,
                                example=example,
                                unit_number=unit_number,
                                comments=comments)
        
        # Convert unit_number to int if provided, otherwise set to None
        try:
            unit_number = int(unit_number) if unit_number else None
        except (ValueError, TypeError):
            unit_number = None
        
        try:
            db = SQL("sqlite:///dictionary.db")
            db.execute("""
                INSERT INTO entries (word_phrase, definition, example, unit_number, comments)
                VALUES (:word_phrase, :definition, :example, :unit_number, :comments)
            """, 
            word_phrase=word_phrase, 
            definition=definition, 
            example=example if example else None,
            unit_number=unit_number,
            comments=comments if comments else None)
            
            flash('Entry added successfully!', 'success')
            return redirect(url_for('dictionary.index'))
            
        except sqlite3.IntegrityError:
            flash('This word/phrase already exists in the dictionary', 'error')
            return render_template('dictionary/add.html',
                                word_phrase=word_phrase,
                                definition=definition,
                                example=example)
    
    return render_template('dictionary/add.html')

@dict_bp.route('/public/entry/<int:entry_id>')
def public_view_entry(entry_id):
    """Public view of an entry (no authentication required)"""
    return render_entry(entry_id, is_public=True)

@dict_bp.route('/entry/<int:entry_id>')
def view_entry(entry_id):
    """Authenticated view of an entry (with edit/delete controls)"""
    if not session.get("name"):
        return redirect(url_for('dictionary.public_view_entry', entry_id=entry_id))
    return render_entry(entry_id, is_public=False)

@dict_bp.route('/entry/<int:entry_id>/edit', methods=['GET', 'POST'])
def edit_entry(entry_id):
    if not session.get("name"):
        return redirect("/auth/login")
        
    db = SQL("sqlite:///dictionary.db")
    
    # Get the existing entry with all fields
    entry = db.execute("""
        SELECT id, word_phrase, definition, example, unit_number, comments
        FROM entries 
        WHERE id = :id
    """, id=entry_id)
    
    if not entry:
        flash('Entry not found', 'error')
        return redirect(url_for('dictionary.index'))
        
    entry = entry[0]
    
    if request.method == 'POST':
        try:
            word_phrase = request.form.get('word_phrase', '').strip()
            definition = request.form.get('definition', '').strip()
            example = request.form.get('example', '').strip()
            unit_number = request.form.get('unit_number', '').strip()
            comments = request.form.get('comments', '').strip()
            
            if not word_phrase or not definition:
                flash('Word/phrase and definition are required', 'error')
                return redirect(url_for('dictionary.edit_entry', entry_id=entry_id))
            
            # Convert unit_number to int if provided, otherwise set to None
            try:
                unit_number = int(unit_number) if unit_number else None
            except (ValueError, TypeError):
                unit_number = None
            
            # Update the entry
            db.execute("""
                UPDATE entries 
                SET word_phrase = :word_phrase,
                    definition = :definition,
                    example = :example,
                    unit_number = :unit_number,
                    comments = :comments,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = :id
            """, 
            word_phrase=word_phrase,
            unit_number=unit_number,
            comments=comments if comments else None,
            definition=definition,
            example=example if example else None,
            id=entry_id)
            
            flash('Entry updated successfully!', 'success')
            return redirect(url_for('dictionary.view_entry', entry_id=entry_id))
            
        except Exception as e:
            current_app.logger.error(f"Error updating entry {entry_id}: {str(e)}")
            flash('An error occurred while updating the entry', 'error')
            return redirect(url_for('dictionary.edit_entry', entry_id=entry_id))
    
    return render_template('dictionary/edit.html', entry=entry)

@dict_bp.route('/entry/<int:entry_id>/delete', methods=['POST'])
def delete_entry(entry_id):
    """Delete an entry"""
    # Check if user is logged in using the same session variable as other routes
    if not session.get('name'):
        return jsonify({'success': False, 'error': 'Not authorized. Please log in.'}), 401
    
    try:
        db = SQL("sqlite:///dictionary.db")
        
        # Verify the entry exists
        entry = db.execute("SELECT * FROM entries WHERE id = ?", entry_id)
        if not entry:
            return jsonify({'success': False, 'error': 'Entry not found'}), 404
            
        # Note: If you want to verify entry ownership, uncomment and modify this section
        # if entry[0].get('user_id') != session.get('user_id'):
        #     return jsonify({'success': False, 'error': 'Not authorized to delete this entry'}), 403
            
        # Delete the entry
        db.execute("DELETE FROM entries WHERE id = ?", entry_id)
        
        return jsonify({'success': True, 'message': 'Entry deleted successfully'})
    except Exception as e:
        print(f"Error deleting entry: {str(e)}")  # Log the error for debugging
        return jsonify({'success': False, 'error': 'An error occurred while deleting the entry'}), 500

@dict_bp.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('dictionary.index'))
        
    try:
        db = SQL("sqlite:///dictionary.db")
        
        # Split query into keywords
        keywords = re.findall(r'\b\w+\b', query.lower())
        
        # Base query
        search_query = """
            SELECT id, word_phrase, definition, example, views, 
                   strftime('%Y-%m-%d', created_at) as created_date
            FROM entries
            WHERE 1=1
        """
        
        # Start with empty params list
        params = []
        
        # Add conditions based on query type
        search_fields = [
            'word_phrase',
            'definition',
            'example'
        ]
        
        if len(keywords) == 1 and ' ' not in query:
            # Single word search - check for exact match, starts with, or contains
            exact_term = keywords[0]
            starts_with = f"{exact_term}%"
            contains = f"%{exact_term}%"
            
            # Build conditions for each field
            field_conditions = []
            for field in search_fields:
                field_conditions.append(f"{field} = ?")  # Exact match
                field_conditions.append(f"{field} LIKE ?")  # Starts with
                field_conditions.append(f"{field} LIKE ?")  # Contains
                
                # Add parameters for each condition
                params.extend([exact_term, starts_with, contains])
            
            # Combine all field conditions with OR
            search_query += " AND (" + " OR ".join(field_conditions) + ")"
            
            # Add ORDER BY with relevance scoring
            search_query += """
                ORDER BY 
                    CASE 
                        WHEN word_phrase = ? THEN 1
                        WHEN word_phrase LIKE ? THEN 2
                        ELSE 3
                    END,
                    LENGTH(word_phrase) ASC,
                    word_phrase ASC
            """
            # Add parameters for ORDER BY
            params.extend([exact_term, starts_with])
        else:
            # Multi-word or phrase search
            search_query += " AND ("
            conditions = []
            
            # Add exact phrase match across all fields
            for field in search_fields:
                conditions.append(f"{field} = ?")
                conditions.append(f"{field} LIKE ?")
                params.extend([query, f"%{query}%"])
            
            # Add individual word matches across all fields
            for keyword in keywords:
                if len(keyword) > 2:  # Only consider words longer than 2 characters
                    for field in search_fields:
                        conditions.append(f"{field} LIKE ?")
                        params.append(f"%{keyword}%")
            
            search_query += " OR ".join(conditions)
            search_query += """)
                ORDER BY 
                    CASE 
                        WHEN word_phrase = ? THEN 1
                        WHEN word_phrase LIKE ? THEN 2
                        ELSE 3
                    END,
                    LENGTH(word_phrase) ASC,
                    word_phrase ASC
            """
            params.extend([query, f"{query}%"])
        
        # Add limit
        search_query += " LIMIT 50"
        
        # Execute the query
        entries = db.execute(search_query, *params)
        
        return render_template('dictionary/search.html', 
                             entries=entries, 
                             query=query)
                             
    except Exception as e:
        current_app.logger.error(f"Search error for '{query}': {str(e)}")
        flash('An error occurred during search', 'error')
        return redirect(url_for('dictionary.index'))
