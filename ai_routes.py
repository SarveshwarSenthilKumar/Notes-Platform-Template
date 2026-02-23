from flask import Blueprint, render_template, request, jsonify, session
from sql import SQL
import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("Please set the GEMINI_API_KEY in your .env file")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Rate limiting
RATE_LIMIT_DELAY = 2  # seconds between requests
last_request_time = 0

# Initialize Blueprint
ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

def get_all_notes():
    """Retrieve all notes from the database"""
    db = SQL("sqlite:///notes.db")
    notes = db.execute("""
        SELECT id, title, content, unit_number, tags, comments, created_at, last_updated
        FROM notes 
        ORDER BY unit_number, title
    """)
    return notes

def get_note_context():
    """Prepare the context from all notes for the AI"""
    notes = get_all_notes()
    context = ""
    for note in notes:
        context += f"""
        --- Note: {note['title']} ---
        Unit: {note['unit_number']}
        Tags: {note['tags'] or 'None'}
        Content: {note['content']}
        Comments: {note['comments'] or 'None'}
        Created: {note['created_at']}
        Last Updated: {note['last_updated']}
        
        """
    return context

@ai_bp.route('/chat', methods=['GET', 'POST'])
def chat():
    """Main chat interface for AI Q&A"""
    if request.method == 'POST':
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        try:
            global last_request_time
            
            # Enforce rate limiting
            current_time = time.time()
            time_since_last = current_time - last_request_time
            if time_since_last < RATE_LIMIT_DELAY:
                time.sleep(RATE_LIMIT_DELAY - time_since_last)
            
            # Get context from notes
            context = get_note_context()
            
            # Prepare the conversation
            system_prompt = """You are a helpful AI assistant that helps with studying and understanding notes. 
            You have access to the user's personal notes and can answer questions, generate study questions, 
            and provide explanations based on the notes. Be concise and accurate in your responses.
            
            Here are the user's notes for context:
            """ + context
            
            # Update last request time
            last_request_time = time.time()
            
            # Call Gemini API
            chat = model.start_chat(history=[])
            response = chat.send_message(
                system_prompt + "\n\nUser: " + user_message + "\nAssistant:",
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 80000,  # Increased from 1000 to 80000 for longer responses
                }
            )
            
            ai_response = response.text.strip()
            return jsonify({'response': ai_response})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # GET request - render the chat interface
    return render_template('ai_chat.html')

def init_app(app):
    """Initialize the AI blueprint with the app"""
    app.register_blueprint(ai_bp)
    return app
