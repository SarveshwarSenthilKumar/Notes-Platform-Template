import sqlite3
import os

# Create or overwrite the notes database
database = open('notes.db', 'w')
database.truncate(0)  
database.close()

# Create uploads/worksheets directory if it doesn't exist
os.makedirs('uploads/worksheets', exist_ok=True)

# Connect to the SQLite database
connection = sqlite3.connect("notes.db")
crsr = connection.cursor()

# Define the notes table structure
create_notes_table_sql = """
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,                -- short title for the note
    content TEXT NOT NULL,              -- the full note text
    unit_number INTEGER,                -- optional: to group with course units
    tags TEXT,                          -- comma-separated or JSON for filtering/search
    related_entries TEXT,               -- store glossary ids (e.g., "1,4,5") for cross-linking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    views INTEGER DEFAULT 0,            -- track popularity
    is_favorite BOOLEAN DEFAULT 0,      -- quick flag for starred notes
    comments TEXT,                      -- optional: your own thoughts or annotations
    has_worksheet BOOLEAN DEFAULT 0     -- flag indicating if note has worksheet images
)
"""

# Define the worksheet_images table structure
create_worksheet_images_table_sql = """
CREATE TABLE worksheet_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,           -- reference to the note
    filename TEXT NOT NULL,             -- stored filename on disk
    original_filename TEXT NOT NULL,    -- original filename from upload
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE
)
"""

# Create the tables
crsr.execute(create_notes_table_sql)
crsr.execute(create_worksheet_images_table_sql)

# Create indexes for better performance
crsr.execute("CREATE INDEX idx_notes_unit ON notes(unit_number)")
crsr.execute("CREATE INDEX idx_notes_favorite ON notes(is_favorite)")
crsr.execute("CREATE INDEX idx_worksheet_images_note_id ON worksheet_images(note_id)")

# Create trigger for automatic last_updated timestamp
crsr.execute("""
CREATE TRIGGER IF NOT EXISTS update_notes_timestamp
AFTER UPDATE ON notes
BEGIN
    UPDATE notes 
    SET last_updated = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;
""")

# Commit changes and close the connection
connection.commit()
connection.close()

print("Notes database created successfully with required tables and indexes.")
print("Created 'uploads/worksheets' directory for storing worksheet images.")
