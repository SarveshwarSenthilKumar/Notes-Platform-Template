import sqlite3
import os

def create_calendar_db():
    # Create or overwrite the calendar database
    if os.path.exists('calendar.db'):
        os.remove('calendar.db')
    
    connection = sqlite3.connect("calendar.db")
    crsr = connection.cursor()

    # Create calendar_entries table
    crsr.execute("""
    CREATE TABLE calendar_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        entry_date DATE NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # Create an index for faster date-based queries
    crsr.execute("CREATE INDEX idx_calendar_entries_user_date ON calendar_entries(user_id, entry_date)")
    
    connection.commit()
    crsr.close()
    connection.close()
    print("Calendar database created successfully!")

if __name__ == '__main__':
    create_calendar_db()
