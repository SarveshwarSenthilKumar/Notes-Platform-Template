import os
import sqlite3
from datetime import datetime

def migrate():
    # Create uploads/worksheets directory if it doesn't exist
    os.makedirs('uploads/worksheets', exist_ok=True)
    
    # Get the absolute path to the database file in the project root
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'notes.db'))
    print(f"Connecting to database at: {db_path}")
    
    # Connect to the database using absolute path
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create worksheet_images table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS worksheet_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE
        )
        """)
        
        # Create index for better performance
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_worksheet_images_note_id 
        ON worksheet_images (note_id)
        """)
        
        # Add a column to notes table to track if it has worksheet images
        try:
            cursor.execute("""
            ALTER TABLE notes 
            ADD COLUMN has_worksheet BOOLEAN DEFAULT 0
            """)
        except sqlite3.OperationalError:
            # Column already exists
            pass
            
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
