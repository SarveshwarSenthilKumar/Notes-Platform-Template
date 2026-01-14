import sqlite3

def setup_dictionary_fts():
    """Set up FTS for the dictionary database"""
    conn = sqlite3.connect('dictionary.db')
    cursor = conn.cursor()
    
    # Create FTS virtual table if it doesn't exist
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts 
        USING fts5(
            word_phrase, 
            definition, 
            example, 
            content='entries', 
            content_rowid='id',
            tokenize='porter unicode61'
        )
    """)
    
    # Check if the FTS table is empty
    cursor.execute("SELECT COUNT(*) FROM entries_fts")
    if cursor.fetchone()[0] == 0:
        # Populate the FTS table with existing data
        cursor.execute("""
            INSERT INTO entries_fts (rowid, word_phrase, definition, example)
            SELECT id, word_phrase, definition, example FROM entries
        """)
    
    conn.commit()
    conn.close()

def setup_notes_fts():
    """Set up FTS for the notes database"""
    conn = sqlite3.connect('notes.db')
    cursor = conn.cursor()
    
    # Create FTS virtual table if it doesn't exist
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts 
        USING fts5(
            title, 
            content, 
            tags,
            content='notes', 
            content_rowid='id',
            tokenize='porter unicode61'
        )
    """)
    
    # Check if the FTS table is empty
    cursor.execute("SELECT COUNT(*) FROM notes_fts")
    if cursor.fetchone()[0] == 0:
        # Populate the FTS table with existing data
        cursor.execute("""
            INSERT INTO notes_fts (rowid, title, content, tags)
            SELECT id, title, content, tags FROM notes
        """)
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("Setting up full-text search for dictionary...")
    setup_dictionary_fts()
    
    print("Setting up full-text search for notes...")
    setup_notes_fts()
    
    print("Full-text search setup complete!")
