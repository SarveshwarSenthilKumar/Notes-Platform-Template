import os
import sqlite3
import time
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()
# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("Please set the GEMINI_API_KEY in your .env file")

# Configure the API key
genai.configure(api_key=GEMINI_API_KEY)

# Use Gemini 2.5 Flash
model_name = 'gemini-2.5-flash'
print(f"Using model: {model_name}")
model = genai.GenerativeModel(model_name)

# Rate limiting settings
RATE_LIMIT_DELAY = 5  # seconds between requests
last_request_time = 0

def get_db_connection(db_path):
    """Create and return a database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_notes():
    """Retrieve all notes from the database."""
    db_path = os.path.join(os.path.dirname(__file__), 'notes.db')
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, title, content FROM notes")
        return cursor.fetchall()
    finally:
        conn.close()

def enhance_note_content(title, content):
    """Use OpenAI to enhance the note content while preserving its structure."""
    system_prompt = """
    You are a legal expert and educator. Your task is to enhance legal notes while preserving their structure and core concepts.
    For each note:
    1. Keep the original structure and key points
    2. Improve clarity and flow
    3. Add relevant examples or case law where appropriate
    4. Include related legal principles or exceptions
    5. Use clear, concise language
    6. Maintain any existing formatting like lists or sections
    7. Add "Key Concepts" and "Practical Applications" sections if missing
    """
    
    global last_request_time
    
    # Rate limiting
    time_since_last = time.time() - last_request_time
    if time_since_last < RATE_LIMIT_DELAY:
        sleep_time = RATE_LIMIT_DELAY - time_since_last
        print(f"  ⏳ Rate limiting: Waiting {sleep_time:.1f} seconds...")
        time.sleep(sleep_time)
    
    last_request_time = time.time()
    
    try:
        # Combine system prompt and user content
        full_prompt = f"""{system_prompt}
        
        Title: {title}
        
        Current Content:
        {content}
        
        Please enhance this note while preserving its structure and key points.
        Keep the original formatting and structure intact.
        """
        
        print(f"  Processing with {model_name}...")
        
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.5,  # Slightly more focused responses
                max_output_tokens=2000,
                top_p=0.8,
                top_k=32
            )
        )
        
        if not response.text:
            raise ValueError("Empty response from model")
            
        return response.text.strip()
        
    except Exception as e:
        error_msg = str(e)
        print(f"  ⚠ Error: {error_msg[:200]}...")  # Truncate long error messages
        
        # Handle rate limiting
        if "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            retry_after = 60  # Default retry after 60 seconds
            if "retry after" in error_msg.lower():
                # Try to extract the retry time from the error message
                import re
                match = re.search(r'retry after (\d+)', error_msg.lower())
                if match:
                    retry_after = int(match.group(1)) + 5  # Add buffer time
            
            print(f"  ⏳ Rate limited. Waiting {retry_after} seconds before retry...")
            time.sleep(retry_after)
            return enhance_note_content(title, content)  # Recursive retry
            
        return None  # For other errors, return None to skip this note
    except Exception as e:
        print(f"Error enhancing note '{title}': {str(e)}")
        return None

def update_note(note_id, enhanced_content):
    """Update the note in the database with enhanced content."""
    db_path = os.path.join(os.path.dirname(__file__), 'notes.db')
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE notes SET content = ? WHERE id = ?",
            (enhanced_content, note_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating note {note_id}: {str(e)}")
        return False
    finally:
        conn.close()

def backup_notes():
    """Create a backup of the notes database."""
    import shutil
    from datetime import datetime
    
    original_db = os.path.join(os.path.dirname(__file__), 'notes.db')
    backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
    
    # Create backups directory if it doesn't exist
    os.makedirs(backup_dir, exist_ok=True)
    
    # Create timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f'notes_backup_{timestamp}.db')
    
    shutil.copy2(original_db, backup_file)
    print(f"Created backup at: {backup_file}")
    return backup_file

def main():
    # Create backup before making any changes
    print("Creating backup of notes database...")
    backup_path = backup_notes()
    print(f"Backup created at: {backup_path}\n")
    
    # Get all notes
    notes = get_notes()
    print(f"Found {len(notes)} notes to process\n")
    print(os.getenv('OPENAI_API_KEY'))
    
    for note in notes:
        note_id = note['id']
        title = note['title']
        content = note['content']
        
        print(f"Processing: {title} (ID: {note_id})")
        
        # Enhance the note content
        enhanced_content = enhance_note_content(title, content)
        
        if enhanced_content and enhanced_content != content:
            print(f"  ✓ Enhanced content generated")
            
            # Update the note in the database
            if update_note(note_id, enhanced_content):
                print(f"  ✓ Successfully updated in database")
            else:
                print(f"  ✗ Failed to update in database")
            
            # Add a small delay to avoid rate limiting
            time.sleep(2)
        else:
            print("  ⚠ No changes made to the note")
        
        print()  # Add a blank line between notes
    
    print("\nNote enhancement process completed!")

if __name__ == "__main__":
    main()
