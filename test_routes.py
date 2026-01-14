from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, current_app
from sql import SQL
import random
import openai
from openai import OpenAI
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Blueprint
test_bp = Blueprint('tests', __name__, url_prefix='/tests')

# In-memory storage for quiz sessions (in production, use a database)
quiz_sessions = {}

def get_user_notes(user_id):
    """Fetch user's notes from the database"""
    db = SQL("sqlite:///notes.db")
    return db.execute("SELECT * FROM notes WHERE user_id = ?", [user_id])

def get_dictionary_terms():
    """Fetch dictionary terms from the database"""
    db = SQL("sqlite:///dictionary.db")
    return db.execute("SELECT * FROM dictionary")

def generate_ai_quiz(user_id, num_questions=10):
    """Generate a quiz using OpenAI's API based on user's notes and dictionary terms"""
    try:
        # Get user's notes and dictionary terms
        notes = get_user_notes(user_id)
        terms = get_dictionary_terms()
        
        if not notes and not terms:
            return None, "No content available to generate quiz"
        
        # Prepare context for the AI
        context = ""
        if notes:
            context += "User's notes:\n"
            for note in notes[:10]:  # Limit to first 10 notes to avoid context window issues
                context += f"- {note.get('title', 'Untitled')}: {note.get('content', '')[:200]}...\n"
        
        if terms:
            context += "\nLegal Terms:\n"
            for term in terms[:20]:  # Limit to first 20 terms
                context += f"- {term.get('term', '')}: {term.get('definition', '')[:150]}...\n"
        
        # Generate quiz using OpenAI
        prompt = f"""
        You are a legal studies tutor. Create a {num_questions}-question multiple choice quiz based on the following content.
        For each question, provide:
        1. A clear, well-formatted question
        2. 4 possible answers (a, b, c, d)
        3. The correct answer (a, b, c, or d)
        4. A brief explanation of why the answer is correct
        
        Content to base the quiz on:
        {context}
        
        Format your response as a JSON object with the following structure:
        {{
            "questions": [
                {{
                    "question": "...",
                    "options": ["...", "...", "...", "..."],
                    "correctAnswer": 0,  // index of correct answer (0-3)
                    "explanation": "..."
                }}
            ]
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": "You are a helpful legal studies tutor that creates educational quizzes."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        # Parse the response
        quiz_data = json.loads(response.choices[0].message.content)
        
        # Add unique IDs to questions for tracking
        for i, question in enumerate(quiz_data['questions']):
            question['id'] = f"q_{int(time.time())}_{i}"
        
        return quiz_data['questions'], None
        
    except Exception as e:
        current_app.logger.error(f"Error generating AI quiz: {str(e)}")
        return None, str(e)

def generate_definition_question(word, definition):
    """Generate a definition-based question"""
    question = f"What is the definition of '{word}'?"
    return {
        'type': 'definition',
        'question': question,
        'answer': definition,
        'options': []
    }

def generate_example_question(word, example):
    """Generate an example usage question"""
    if not example:
        return None
        
    # Replace the word/phrase with a blank in the example
    blanked_example = example.replace(word, '__________')
    question = f"Complete the following sentence: {blanked_example}"
    
    return {
        'type': 'fill_blank',
        'question': question,
        'answer': word,
        'options': []
    }

def generate_mcq_question(word, definition, all_definitions):
    """Generate a multiple-choice question"""
    if len(all_definitions) < 3:
        return None
        
    # Get 3 random incorrect definitions
    other_definitions = [d for d in all_definitions if d != definition]
    if len(other_definitions) > 3:
        other_definitions = random.sample(other_definitions, 3)
    
    options = [definition] + other_definitions
    random.shuffle(options)
    
    return {
        'type': 'multiple_choice',
        'question': f"What is the correct definition of '{word}'?",
        'answer': definition,
        'options': options
    }

@test_bp.route('/generate/<int:unit_number>')
def generate_test(unit_number):
    if not session.get("name"):
        return redirect(url_for('auth.login', next=request.url))
    
    try:
        print(f"\n=== Starting test generation for unit {unit_number} ===")
        print("Current user:", session.get("name"))
        # Connect to both databases
        dict_db = SQL("sqlite:///dictionary.db")
        notes_db = SQL("sqlite:///notes.db")
        
        # Get dictionary entries for the unit
        print("Fetching dictionary entries...")
        dictionary_entries = dict_db.execute("""
            SELECT id, word_phrase, definition, example, unit_number
            FROM entries 
            WHERE unit_number = :unit_number
            ORDER BY RANDOM()
            LIMIT 20  # Limit to 20 terms to keep the test manageable
        """, unit_number=unit_number)
        print(f"Found {len(dictionary_entries)} dictionary entries")
        
        # Get notes for the unit
        print("Fetching notes...")
        notes = notes_db.execute("""
            SELECT id, title, content, unit_number
            FROM notes
            WHERE unit_number = :unit_number
            ORDER BY RANDOM()
            LIMIT 5  # Limit to 5 notes to keep the test focused
        """, unit_number=unit_number)
        print(f"Found {len(notes)} notes")
        
        # Generate test questions from dictionary entries
        test_questions = []
        all_definitions = [entry['definition'] for entry in dictionary_entries]
        
        print(f"Generating questions from {len(dictionary_entries)} dictionary entries...")
        for entry in dictionary_entries:
            # Add definition question
            test_questions.append(generate_definition_question(
                entry['word_phrase'], 
                entry['definition']
            ))
            
            # Add example question if available
            if entry.get('example'):
                example_q = generate_example_question(
                    entry['word_phrase'],
                    entry['example']
                )
                if example_q:
                    test_questions.append(example_q)
            
            # Add multiple choice question if we have enough definitions
            mcq = generate_mcq_question(
                entry['word_phrase'],
                entry['definition'],
                all_definitions
            )
            if mcq:
                test_questions.append(mcq)
        
        # Add questions from notes (simple recall questions)
        print(f"Generating questions from {len(notes)} notes...")
        for note in notes:
            # Simple question based on note title
            test_questions.append({
                'type': 'short_answer',
                'question': f"What are the key points about '{note['title']}'?",
                'answer': note['content'],
                'options': []
            })
        
        # Shuffle the questions
        random.shuffle(test_questions)
        
        # Limit to 15 questions total
        test_questions = test_questions[:15]
        
        print(f"\n=== DEBUG: Generated {len(test_questions)} questions ===")
        
        # Debug: Print all questions
        for i, q in enumerate(test_questions):
            print(f"Question {i+1} (Type: {q['type']}): {q['question'][:100]}...")
            if 'options' in q and q['options']:
                print(f"  Options: {q['options']}")
        
        # Use forward slashes for template path (Jinja2 uses forward slashes on all platforms)
        template_path = 'tests/generate.html'
        print(f"\n=== DEBUG: Attempting to render template: {template_path}")
        
        # Debug: Check if template exists and can be rendered
        from flask import current_app, render_template_string
        with current_app.app_context():
            try:
                # Test template rendering with a simple string
                test_render = render_template_string('Test template rendering: {{ test_var }}', test_var='SUCCESS')
                print(f"Template rendering test: {test_render}")
                
                # Try to get the actual template
                template = current_app.jinja_env.get_or_select_template(template_path)
                print("Template found and loaded successfully")
                
                # Try rendering with test data
                test_data = [
                    {
                        'type': 'test',
                        'question': 'Test question',
                        'answer': 'Test answer',
                        'options': []
                    }
                ]
                test_output = render_template(template_path, 
                                          test_questions=test_data,
                                          unit_number=unit_number)
                print(f"Test render successful. Output length: {len(test_output) if test_output else 0} characters")
                
            except Exception as e:
                print(f"\n=== TEMPLATE ERROR ===")
                print(f"Error: {str(e)}")
                import traceback
                traceback.print_exc()
                print("====================\n")
                raise
        
        # Render the actual template
        print("\n=== Rendering actual template with real data ===")
        return render_template(template_path,
                             test_questions=test_questions,
                             unit_number=unit_number)
                             
    except Exception as e:
        import traceback
        error_msg = f'Error generating test: {str(e)}\n\n{traceback.format_exc()}'
        print("\n" + "="*50)
        print("ERROR IN TEST GENERATION:")
        print(error_msg)
        print("="*50 + "\n")
        flash('Error generating test. Please check the server logs for details.', 'error')
        return redirect(url_for('dictionary.index'))

@test_bp.route('/ai_test/<int:unit_number>')
def ai_test(unit_number):
    if not session.get("name"):
        return redirect(url_for('auth.login', next=request.url))
    
    return render_template('tests/ai_test.html', unit_number=unit_number)

@test_bp.route('/api/ai_test/start', methods=['POST'])
def start_ai_test():
    if not session.get("name"):
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    unit_number = data.get('unit_number')
    
    # Get all relevant content for context
    dict_db = SQL("sqlite:///dictionary.db")
    notes_db = SQL("sqlite:///notes.db")
    
    # Get dictionary entries
    dictionary_entries = dict_db.execute("""
        SELECT word_phrase, definition, example, unit_number
        FROM entries 
        WHERE unit_number = :unit_number
    """, unit_number=unit_number)
    
    # Get notes
    notes = notes_db.execute("""
        SELECT title, content, unit_number
        FROM notes
        WHERE unit_number = :unit_number
    """, unit_number=unit_number)
    
    # Format the context
    context = ""
    
    if dictionary_entries:
        context += "Dictionary Terms:\n"
        for entry in dictionary_entries:
            context += f"- {entry['word_phrase']}: {entry['definition']}"
            if entry['example']:
                context += f" (Example: {entry['example']})"
            context += "\n"
    
    if notes:
        context += "\nNotes:\n"
        for note in notes:
            context += f"- {note['title']}: {note['content']}\n"
    
    # Initial prompt for the AI
    system_prompt = f"""You are a helpful AI tutor helping a law student study for their unit {unit_number} test. 
    You have access to the following study materials:
    {context}
    
    Your task is to:
    1. Start with a friendly greeting and explain the test format
    2. Ask one question at a time
    3. Wait for the student's response
    4. Provide feedback on their answer
    5. Keep track of the score
    6. At the end, provide a summary of the test results
    
    Make the questions challenging but fair, and provide helpful explanations.
    """
    
    # Start the conversation
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": "Hello! I'm your AI tutor. I'll be asking you questions based on your study materials. Let's begin with the first question..."}
        ],
        temperature=0.7
    )
    
    return jsonify({
        "messages": [
            {"role": "assistant", "content": response.choices[0].message.content}
        ]
    })

@test_bp.route('/api/ai_test/chat', methods=['POST'])
def chat():
    if not session.get("name"):
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.get_json()
    if not data or 'messages' not in data:
        return jsonify({"error": "Invalid request data"}), 400
        
    messages = data['messages']
    if not isinstance(messages, list):
        return jsonify({"error": "Messages must be an array"}), 400
    
    try:
        # Ensure we don't exceed context window (last 10 messages)
        recent_messages = messages[-10:]
        
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=recent_messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        if not response.choices or not response.choices[0].message.content:
            return jsonify({"error": "No response from AI"}), 500
        
        return jsonify({
            "messages": [
                {"role": "assistant", "content": response.choices[0].message.content}
            ]
        })
    except Exception as e:
        print(f"Error in chat route: {str(e)}")
        return jsonify({
            "error": "Sorry, I encountered an error processing your request. Please try again."
        }), 500

@test_bp.route('/ai-quiz')
def ai_quiz():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # Generate a new quiz session ID
    session_id = f"quiz_{int(time.time())}"
    
    # Generate questions using AI
    questions, error = generate_ai_quiz(session['user_id'])
    
    if error or not questions:
        flash('Failed to generate quiz. Please try again later.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Store the quiz in the session
    quiz_sessions[session_id] = {
        'questions': questions,
        'user_id': session['user_id'],
        'started_at': datetime.now().isoformat(),
        'answers': {},
        'completed': False
    }
    
    # Store the session ID in the user's session
    session['current_quiz'] = session_id
    
    return render_template('ai_quiz.html', session_id=session_id)

@test_bp.route('/api/ai-quiz', methods=['GET'])
def api_get_quiz():
    if 'user_id' not in session or 'current_quiz' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    session_id = session['current_quiz']
    if session_id not in quiz_sessions:
        return jsonify({'error': 'Quiz session not found'}), 404
    
    # Return only the questions (without answers)
    quiz_data = quiz_sessions[session_id]
    questions = []
    
    for q in quiz_data['questions']:
        question = {
            'id': q['id'],
            'question': q['question'],
            'options': q['options'],
            'type': 'multiple_choice'
        }
        questions.append(question)
    
    return jsonify({
        'questions': questions,
        'total_questions': len(questions)
    })

@test_bp.route('/api/quiz-results', methods=['POST'])
def api_submit_quiz():
    if 'user_id' not in session or 'current_quiz' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    session_id = session['current_quiz']
    if session_id not in quiz_sessions:
        return jsonify({'error': 'Quiz session not found'}), 404
    
    data = request.get_json()
    if not data or 'answers' not in data:
        return jsonify({'error': 'Invalid request data'}), 400
    
    # Update the quiz session with the user's answers
    quiz_sessions[session_id]['answers'] = data.get('answers', {})
    quiz_sessions[session_id]['completed'] = True
    quiz_sessions[session_id]['completed_at'] = datetime.now().isoformat()
    quiz_sessions[session_id]['score'] = data.get('score', 0)
    quiz_sessions[session_id]['total_questions'] = data.get('total', 0)
    
    # Here you could save the results to a database
    # save_quiz_results(session['user_id'], quiz_sessions[session_id])
    
    return jsonify({'success': True})

def init_app(app):
    # Register the blueprint with the app
    app.register_blueprint(test_bp)
    return test_bp
