from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, send_from_directory, jsonify, current_app
from sql import SQL
import sqlite3
from datetime import datetime
import re
import os
import uuid
from werkzeug.utils import secure_filename
import subprocess
import json

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = os.path.join('uploads', 'worksheets')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_worksheet_images(note_id, files):
    """Save uploaded worksheet images and return a list of saved filenames"""
    if 'worksheet_images' not in files:
        return []
    
    saved_files = []
    for file in files.getlist('worksheet_images'):
        if file and allowed_file(file.filename):
            # Generate a unique filename to prevent collisions
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4()}.{ext}"
            
            # Ensure the upload directory exists
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
            # Save the file
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            # Save file info to database using raw SQLite connection
            conn = sqlite3.connect('notes.db')
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO worksheet_images (note_id, filename, original_filename)
                VALUES (?, ?, ?)
            """, (note_id, filename, file.filename))
            
            # Get the ID of the last inserted row
            worksheet_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            saved_files.append({
                'id': worksheet_id,
                'filename': filename,
                'original_filename': file.filename
            })
    
    # Update the has_worksheet flag on the note
    if saved_files:
        db = SQL("sqlite:///notes.db")
        db.execute("""
            UPDATE notes 
            SET has_worksheet = 1 
            WHERE id = :note_id
        """, note_id=note_id)
    
    return saved_files

def get_worksheet_images(note_id):
    """Get all worksheet images for a note"""
    db = SQL("sqlite:///notes.db")
    return db.execute("""
        SELECT id, filename, original_filename, 
               strftime('%Y-%m-%d %H:%M', upload_date) as upload_date
        FROM worksheet_images 
        WHERE note_id = :note_id
        ORDER BY upload_date DESC
    """, note_id=note_id)

# Initialize Blueprint
notes_bp = Blueprint('notes', __name__, url_prefix='/notes')

@notes_bp.route('')
def index():
    """Display all notes"""
    
    db = SQL("sqlite:///notes.db")
    notes = db.execute("""
        SELECT id, title, unit_number, 
               strftime('%Y-%m-%d', created_at) as created_date,
               strftime('%Y-%m-%d', last_updated) as last_updated,
               is_favorite, has_worksheet
        FROM notes 
        ORDER BY 
            CASE WHEN unit_number = '' OR unit_number IS NULL THEN 1 ELSE 0 END,
            CAST(unit_number AS INTEGER) DESC,
            last_updated DESC
    """)
    
    # Group notes by unit number for better organization
    notes_by_unit = {}
    for note in notes:
        unit = note.get('unit_number', 'Ungrouped')
        if unit not in notes_by_unit:
            notes_by_unit[unit] = []
        notes_by_unit[unit].append(note)
    
    return render_template('notes/index.html', 
                         notes_by_unit=notes_by_unit)

@notes_bp.route('/add', methods=['GET', 'POST'])
def add_note():
    """Add a new note"""
    if not session.get("name"):
        return redirect("/auth/login")
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        unit_number = request.form.get('unit_number', '').strip()
        tags = request.form.get('tags', '').strip()
        related_entries = request.form.get('related_entries', '').strip()
        comments = request.form.get('comments', '').strip()
        is_favorite = 1 if request.form.get('is_favorite') else 0
        
        if not title or not content:
            flash('Title and content are required', 'error')
            return render_template('notes/add.html',
                                title=title,
                                content=content,
                                unit_number=unit_number,
                                tags=tags,
                                related_entries=related_entries,
                                comments=comments,
                                is_favorite=is_favorite)
        
        try:
            unit_number = int(unit_number) if unit_number else None
            
            # Use a raw SQLite connection to get the lastrowid
            conn = sqlite3.connect('notes.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO notes (title, content, unit_number, tags, 
                                 related_entries, comments, is_favorite)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, 
            (title,
             content,
             unit_number,
             tags if tags else None,
             related_entries if related_entries else None,
             comments if comments else None,
             is_favorite))
            
            # Get the last inserted row ID
            note_id = cursor.lastrowid
            conn.commit()
            conn.close()
            if 'worksheet_images' in request.files:
                saved_files = save_worksheet_images(note_id, request.files)
                if saved_files:
                    flash(f'Successfully uploaded {len(saved_files)} worksheet file(s)!', 'success')
            
            flash('Note added successfully!', 'success')
            return redirect(url_for('notes.view_note', note_id=note_id))
            
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
            return render_template('notes/add.html',
                                title=title,
                                content=content,
                                unit_number=unit_number,
                                tags=tags,
                                related_entries=related_entries,
                                comments=comments,
                                is_favorite=is_favorite)
    
    return render_template('notes/add.html')

@notes_bp.route('/edit/<int:note_id>', methods=['GET', 'POST'])
def edit_note(note_id):
    """Edit an existing note"""
    if not session.get("name"):
        return redirect("/auth/login")
    
    db = SQL("sqlite:///notes.db")
    
    # Get the note first to ensure it exists
    note = db.execute("SELECT * FROM notes WHERE id = :id", id=note_id)
    if not note:
        abort(404)
    
    note = note[0]
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        unit_number = request.form.get('unit_number', '').strip()
        tags = request.form.get('tags', '').strip()
        related_entries = request.form.get('related_entries', '').strip()
        comments = request.form.get('comments', '').strip()
        is_favorite = 1 if request.form.get('is_favorite') else 0
        
        # Validate required fields
        if not title or not content:
            flash('Title and content are required', 'error')
            return render_template('notes/edit.html', note={
                'id': note_id,
                'title': title,
                'content': content,
                'unit_number': unit_number,
                'tags': tags,
                'related_entries': related_entries,
                'comments': comments,
                'is_favorite': is_favorite
            })
        
        try:
            unit_number = int(unit_number) if unit_number else None
            
            # Update the note
            db.execute("""
                UPDATE notes 
                SET title = :title,
                    content = :content,
                    unit_number = :unit_number,
                    tags = :tags,
                    related_entries = :related_entries,
                    comments = :comments,
                    is_favorite = :is_favorite,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = :id
            """, 
            id=note_id,
            title=title,
            content=content,
            unit_number=unit_number,
            tags=tags if tags else None,
            related_entries=related_entries if related_entries else None,
            comments=comments if comments else None,
            is_favorite=is_favorite)
            
            # Handle worksheet images if any
            if 'worksheet_images' in request.files:
                saved_files = save_worksheet_images(note_id, request.files)
                if saved_files:
                    flash(f'Successfully uploaded {len(saved_files)} worksheet file(s)!', 'success')
            
            flash('Note updated successfully!', 'success')
            return redirect(url_for('notes.view_note', note_id=note_id))
            
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
            return render_template('notes/edit.html', note={
                'id': note_id,
                'title': title,
                'content': content,
                'unit_number': unit_number,
                'tags': tags,
                'related_entries': related_entries,
                'comments': comments,
                'is_favorite': is_favorite
            })
    
    # GET request - show edit form with current note data
    # Get worksheet images for this note
    worksheet_images = get_worksheet_images(note_id)
    note['worksheet_images'] = worksheet_images
    
    return render_template('notes/edit.html', note=note)

@notes_bp.route('/<int:note_id>/content')
def get_note_content(note_id):
    """Get the full content of a note by ID for search functionality"""
    db = SQL("sqlite:///notes.db")
    note = db.execute("SELECT content FROM notes WHERE id = ?", note_id)
    
    if not note:
        return {"error": "Note not found"}, 404
        
    return {"content": note[0]['content']}

@notes_bp.route('/worksheet/<filename>')
def serve_worksheet(filename):
    """Serve uploaded worksheet files"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@notes_bp.route('/<int:note_id>/delete', methods=['POST'])
def delete_note(note_id):
    """Delete a note and its associated worksheets"""
    if not session.get("name"):
        flash('You must be logged in to delete notes', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        db = SQL("sqlite:///notes.db")
        
        # First, delete any associated worksheet files and their database entries
        worksheets = db.execute("""
            SELECT filename FROM worksheet_images 
            WHERE note_id = :note_id
        """, note_id=note_id)
        
        # Delete the actual files
        for worksheet in worksheets:
            try:
                file_path = os.path.join(UPLOAD_FOLDER, worksheet['filename'])
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                current_app.logger.error(f"Error deleting worksheet file {worksheet['filename']}: {str(e)}")
        
        # Delete the note from the database
        db.execute("DELETE FROM notes WHERE id = :note_id", note_id=note_id)
        
        flash('Note deleted successfully', 'success')
        return redirect(url_for('notes.index'))
        
    except Exception as e:
        current_app.logger.error(f"Error deleting note {note_id}: {str(e)}")
        flash('An error occurred while deleting the note', 'error')
        return redirect(url_for('notes.view_note', note_id=note_id))

@notes_bp.route('/<int:note_id>/duplicate', methods=['POST'])
def duplicate_note(note_id):
    """Duplicate a note to a different unit"""
    if not session.get("name"):
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    target_unit = data.get('target_unit')
    include_worksheets = data.get('include_worksheets', True)
    
    if not target_unit:
        return jsonify({"error": "Target unit is required"}), 400
    
    try:
        # Get the original note
        db = SQL("sqlite:///notes.db")
        note = db.execute("SELECT * FROM notes WHERE id = :id", id=note_id)
        
        if not note:
            return jsonify({"error": "Note not found"}), 404
            
        note = note[0]
        
        # Create a new note with the same content but different unit
        new_note = {
            'title': f"{note['title']} (Copy)",
            'content': note['content'],
            'unit_number': target_unit,
            'tags': note.get('tags'),
            'related_entries': note.get('related_entries'),
            'comments': note.get('comments'),
            'is_favorite': 0  # Reset favorite status
        }
        
        # Insert the new note
        conn = sqlite3.connect('notes.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO notes (title, content, unit_number, tags, related_entries, comments, is_favorite)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            new_note['title'],
            new_note['content'],
            new_note['unit_number'],
            new_note['tags'],
            new_note['related_entries'],
            new_note['comments'],
            new_note['is_favorite']
        ))
        
        new_note_id = cursor.lastrowid
        
        # Handle worksheet images if requested
        if include_worksheets and note.get('has_worksheet'):
            # Get original worksheets
            worksheets = db.execute("""
                SELECT filename, original_filename 
                FROM worksheet_images 
                WHERE note_id = :note_id
            """, note_id=note_id)
            
            # Copy worksheet files and create new records
            for worksheet in worksheets:
                original_path = os.path.join(UPLOAD_FOLDER, worksheet['filename'])
                if os.path.exists(original_path):
                    # Generate new filename to avoid conflicts
                    file_ext = os.path.splitext(worksheet['filename'])[1]
                    new_filename = f"{uuid.uuid4()}{file_ext}"
                    new_path = os.path.join(UPLOAD_FOLDER, new_filename)
                    
                    # Copy the file
                    import shutil
                    shutil.copy2(original_path, new_path)
                    
                    # Create new worksheet record
                    cursor.execute("""
                        INSERT INTO worksheet_images (note_id, filename, original_filename)
                        VALUES (?, ?, ?)
                    """, (new_note_id, new_filename, worksheet['original_filename']))
            
            # Update has_worksheet flag
            cursor.execute("""
                UPDATE notes 
                SET has_worksheet = 1 
                WHERE id = ?
            """, (new_note_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "new_note_id": new_note_id,
            "message": "Note duplicated successfully"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error duplicating note: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({"error": f"Failed to duplicate note: {str(e)}"}), 500

@notes_bp.route('/delete_worksheet/<int:worksheet_id>', methods=['POST'])
def delete_worksheet(worksheet_id):
    """Delete a worksheet image"""
    if not session.get("name"):
        return redirect("/auth/login")
    
    db = SQL("sqlite:///notes.db")
    
    # Get the worksheet to delete
    worksheet = db.execute("""
        SELECT id, note_id, filename 
        FROM worksheet_images 
        WHERE id = :id
    """, id=worksheet_id)
    
    if not worksheet:
        flash('Worksheet not found', 'error')
        return redirect(url_for('notes.index'))
    
    worksheet = worksheet[0]
    
    try:
        # Delete the file
        filepath = os.path.join(UPLOAD_FOLDER, worksheet['filename'])
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Delete the database record
        db.execute("DELETE FROM worksheet_images WHERE id = :id", id=worksheet_id)
        
        # Check if there are any remaining worksheets for this note
        remaining = db.execute("""
            SELECT COUNT(*) as count 
            FROM worksheet_images 
            WHERE note_id = :note_id
        """, note_id=worksheet['note_id'])
        
        # Update the has_worksheet flag if no more worksheets
        if remaining and remaining[0]['count'] == 0:
            db.execute("""
                UPDATE notes 
                SET has_worksheet = 0 
                WHERE id = :note_id
            """, note_id=worksheet['note_id'])
        
        flash('Worksheet deleted successfully', 'success')
        return redirect(url_for('notes.edit_note', note_id=worksheet['note_id']))
    
    except Exception as e:
        flash(f'Error deleting worksheet: {str(e)}', 'error')
        return redirect(url_for('notes.edit_note', note_id=worksheet['note_id']))

@notes_bp.route('/view/<int:note_id>')
def view_note(note_id):
    """View a specific note"""
    
    db = SQL("sqlite:///notes.db")
    
    # Get the note
    note = db.execute("""
        SELECT *,
               strftime('%Y-%m-%d', created_at) as created_date,
               strftime('%Y-%m-%d', last_updated) as last_updated
        FROM notes 
        WHERE id = :id
    """, id=note_id)
    
    if not note:
        abort(404)
    
    note = note[0]
    
    # Increment view count
    db.execute("""
        UPDATE notes 
        SET views = COALESCE(views, 0) + 1 
        WHERE id = :id
    """, id=note_id)
    
    # Parse content for markdown-like formatting
    content = note['content']
    
    # Convert markdown headers to HTML
    content = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)
    content = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
    content = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
    
    # Convert bold and italic
    content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
    content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
    
    # Convert lists
    content = re.sub(r'^\s*[-*] (.*?)$', r'<li>\1</li>', content, flags=re.MULTILINE)
    content = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', content, flags=re.DOTALL)
    
    # Convert blockquotes
    content = re.sub(r'^> (.*?)$', r'<blockquote>\1</blockquote>', content, flags=re.MULTILINE)
    
    # Convert line breaks to <br> tags
    content = content.replace('\n', '<br>')
    
    # Handle asides (Notion-style callouts)
    content = re.sub(
        r'<aside>\s*💡\s*(.*?)\s*</aside>', 
        r'<div class="callout"><div class="callout-emoji">💡</div><div class="callout-content">\1</div></div>', 
        content, 
        flags=re.DOTALL
    )
    
    # Split content into sections based on headers
    sections = re.split(r'(<h[1-3]>.*?</h[1-3]>)', content)
    
    # Process each section to ensure proper HTML structure
    processed_sections = []
    for i, section in enumerate(sections):
        if section.startswith('<h'):
            # This is a header, add it to the processed sections
            processed_sections.append(section)
        elif section.strip():
            # This is content, wrap it in a paragraph if it's not already in a block element
            if not any(tag in section for tag in ['<p>', '<ul>', '<ol>', '<blockquote>', '<div class="callout">']):
                section = f'<p>{section}</p>'
            processed_sections.append(section)
    
    # Join the sections back together
    processed_content = '\n'.join(processed_sections)
    
    # Get related entries if any
    related_entries = []
    if note.get('related_entries'):
        entry_ids = [int(id_str.strip()) for id_str in note['related_entries'].split(',') if id_str.strip().isdigit()]
        if entry_ids:
            # Connect to the dictionary database
            dict_db = SQL("sqlite:///dictionary.db")
            related_entries = dict_db.execute("""
                SELECT id, word_phrase 
                FROM entries 
                WHERE id IN ({})
            """.format(','.join(['?'] * len(entry_ids))), *entry_ids)
    
    # Get worksheet images for this note
    worksheet_images = []
    if note.get('has_worksheet'):
        worksheet_images = get_worksheet_images(note_id)
    
    return render_template('notes/view.html', 
                         note=note, 
                         content=processed_content,
                         related_entries=related_entries,
                         worksheet_images=worksheet_images)

@notes_bp.route('/<int:note_id>/enhance', methods=['POST'])
def enhance_note(note_id):
    """Enhance a note using AI"""
    try:
        # Get the note from the database
        db = SQL("sqlite:///notes.db")
        note = db.execute("SELECT * FROM notes WHERE id = :id", id=note_id)
        
        if not note:
            return jsonify({'success': False, 'message': 'Note not found'}), 404
            
        # Get any additional instructions from the request
        data = request.get_json()
        comment = data.get('comment', '')
        
        try:
            # Import the enhance_note module directly instead of using subprocess
            import sys
            import os
            # Add the current directory to the path to ensure imports work
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from enhance_note import enhance_note_content, update_note
            
            # Get the note content
            note_content = note[0]['content']
            note_title = note[0]['title']
            
            # Enhance the note content
            try:
                enhanced_content = enhance_note_content(note_title, note_content, comment)
                print(f"Debug: enhanced_content type: {type(enhanced_content)}, length: {len(enhanced_content) if enhanced_content else 'None'}")
                
                if not enhanced_content:
                    raise ValueError("Failed to enhance note content - returned None or empty")
            except Exception as enhance_error:
                print(f"Debug: Error during enhancement: {str(enhance_error)}")
                raise ValueError(f"Failed to enhance note content: {str(enhance_error)}")
                
            # Update the note in the database
            update_success = update_note(note_id, enhanced_content)
            
            if not update_success:
                raise ValueError("Failed to update note in database")
                
            # Get the updated note to return
            updated_note = db.execute("SELECT * FROM notes WHERE id = :id", id=note_id)
            
            if not updated_note:
                raise ValueError("Failed to retrieve updated note")
                
            return jsonify({
                'success': True,
                'message': 'Note enhanced successfully',
                'content': updated_note[0]['content']
            })
            
        except Exception as e:
            print(f"Error in enhance_note: {str(e)}")
            # Try to get more detailed error information
            import traceback
            error_details = traceback.format_exc()
            print(f"Error details: {error_details}")
            
            return jsonify({
                'success': False,
                'message': 'Error enhancing note',
                'error': str(e),
                'details': error_details if 'DEBUG' in os.environ else None
            }), 500
            
    except Exception as e:
        print(f"Unexpected error in enhance_note route: {str(e)}")
        import traceback
        error_details = traceback.format_exc()
        print(f"Error details: {error_details}")
        
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred',
            'error': str(e),
            'details': error_details if 'DEBUG' in os.environ else None
        }), 500

def init_app(app):
    app.register_blueprint(notes_bp)
