from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, date
from sql import SQL
import os

# Create blueprint
calendar_bp = Blueprint('calendar', __name__, url_prefix='/calendar')

def get_calendar_db():
    """Helper function to get a database connection for the calendar."""
    return SQL("sqlite:///calendar.db")

@calendar_bp.route('/')
def index():
    """Display the calendar view."""
    if not session.get("name"):
        flash('Please log in to view the calendar.', 'error')
        return redirect(url_for('auth.login'))
    
    # Get current date
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)
    
    # Get entries for the month
    db = get_calendar_db()
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    entries = db.execute(
        """
        SELECT id, entry_date, title, description 
        FROM calendar_entries 
        WHERE user_id = :user_id 
        AND entry_date >= :start_date 
        AND entry_date < :end_date
        ORDER BY entry_date
        """,
        user_id=session.get("id"),
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat()
    )
    
    # Organize entries by date
    entries_by_date = {}
    for entry in entries:
        entry_date = datetime.strptime(entry['entry_date'], '%Y-%m-%d').date()
        if entry_date not in entries_by_date:
            entries_by_date[entry_date] = []
        entries_by_date[entry_date].append(entry)
    
    return render_template(
        'calendar/index.html',
        year=year,
        month=month,
        today=today,
        entries=entries_by_date
    )

@calendar_bp.route('/add', methods=['GET', 'POST'])
def add_entry():
    """Add a new calendar entry."""
    if 'user_id' not in session:
        flash('Please log in to add calendar entries.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        entry_date = request.form.get('entry_date')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        
        if not title:
            flash('Title is required.', 'error')
            return render_template('calendar/add.html', 
                               entry_date=entry_date,
                               title=title,
                               description=description)
        
        try:
            db = get_calendar_db()
            db.execute(
                """
                INSERT INTO calendar_entries (user_id, entry_date, title, description)
                VALUES (:user_id, :entry_date, :title, :description)
                """,
                user_id=session['user_id'],
                entry_date=entry_date,
                title=title,
                description=description if description else None
            )
            
            flash('Calendar entry added successfully!', 'success')
            return redirect(url_for('calendar.index'))
            
        except Exception as e:
            flash(f'Error adding calendar entry: {str(e)}', 'error')
            return render_template('calendar/add.html', 
                               entry_date=entry_date,
                               title=title,
                               description=description)
    
    # For GET request, pre-fill the date if provided
    entry_date = request.args.get('date')
    if entry_date:
        try:
            # Validate date format
            datetime.strptime(entry_date, '%Y-%m-%d')
        except ValueError:
            entry_date = date.today().isoformat()
    else:
        entry_date = date.today().isoformat()
    
    return render_template('calendar/add.html', entry_date=entry_date)

@calendar_bp.route('/entry/<int:entry_id>')
def view_entry(entry_id):
    """View a specific calendar entry."""
    if 'user_id' not in session:
        flash('Please log in to view calendar entries.', 'error')
        return redirect(url_for('auth.login'))
    
    db = get_calendar_db()
    entry = db.execute(
        """
        SELECT id, entry_date, title, description 
        FROM calendar_entries 
        WHERE id = :id AND user_id = :user_id
        """,
        id=entry_id,
        user_id=session['user_id']
    )
    
    if not entry:
        flash('Calendar entry not found or access denied.', 'error')
        return redirect(url_for('calendar.index'))
    
    return render_template('calendar/view.html', entry=entry[0])

@calendar_bp.route('/entry/<int:entry_id>/edit', methods=['GET', 'POST'])
def edit_entry(entry_id):
    """Edit a calendar entry."""
    if 'user_id' not in session:
        flash('Please log in to edit calendar entries.', 'error')
        return redirect(url_for('auth.login'))
    
    db = get_calendar_db()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        
        if not title:
            flash('Title is required.', 'error')
            return render_template('calendar/edit.html', 
                               id=entry_id,
                               title=title,
                               description=description)
        
        try:
            db.execute(
                """
                UPDATE calendar_entries 
                SET title = :title, 
                    description = :description,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id AND user_id = :user_id
                """,
                id=entry_id,
                user_id=session['user_id'],
                title=title,
                description=description if description else None
            )
            
            flash('Calendar entry updated successfully!', 'success')
            return redirect(url_for('calendar.view_entry', entry_id=entry_id))
            
        except Exception as e:
            flash(f'Error updating calendar entry: {str(e)}', 'error')
            return render_template('calendar/edit.html', 
                               id=entry_id,
                               title=title,
                               description=description)
    
    # For GET request, load the entry
    entry = db.execute(
        """
        SELECT id, entry_date, title, description 
        FROM calendar_entries 
        WHERE id = :id AND user_id = :user_id
        """,
        id=entry_id,
        user_id=session['user_id']
    )
    
    if not entry:
        flash('Calendar entry not found or access denied.', 'error')
        return redirect(url_for('calendar.index'))
    
    return render_template('calendar/edit.html', **entry[0])

@calendar_bp.route('/entry/<int:entry_id>/delete', methods=['POST'])
def delete_entry(entry_id):
    """Delete a calendar entry."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    try:
        db = get_calendar_db()
        result = db.execute(
            """
            DELETE FROM calendar_entries 
            WHERE id = :id AND user_id = :user_id
            """,
            id=entry_id,
            user_id=session['user_id']
        )
        
        if result.rowcount > 0:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Entry not found or access denied'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@calendar_bp.route('/api/entries')
def api_entries():
    """API endpoint to get calendar entries for a date range."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    if not start_date or not end_date:
        return jsonify({'error': 'Start and end dates are required'}), 400
    
    try:
        db = get_calendar_db()
        entries = db.execute(
            """
            SELECT id, entry_date as start, title, description
            FROM calendar_entries 
            WHERE user_id = :user_id 
            AND entry_date >= :start_date 
            AND entry_date <= :end_date
            ORDER BY entry_date
            """,
            user_id=session['user_id'],
            start_date=start_date,
            end_date=end_date
        )
        
        # Format for FullCalendar
        formatted_entries = []
        for entry in entries:
            formatted_entries.append({
                'id': entry['id'],
                'title': entry['title'],
                'start': entry['start'],
                'description': entry['description'],
                'url': url_for('calendar.view_entry', entry_id=entry['id'])
            })
        
        return jsonify(formatted_entries)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def init_app(app):
    """Initialize the calendar blueprint with the app."""
    app.register_blueprint(calendar_bp)
