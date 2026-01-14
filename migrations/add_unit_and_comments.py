import sqlite3
from datetime import datetime

def migrate():
    # Connect to the database
    conn = sqlite3.connect('dictionary.db')
    cursor = conn.cursor()
    
    try:
        # Add unit_number column if it doesn't exist
        cursor.execute("""
        ALTER TABLE entries 
        ADD COLUMN unit_number INTEGER DEFAULT NULL
        """)
        
        # Add comments column if it doesn't exist
        cursor.execute("""
        ALTER TABLE entries 
        ADD COLUMN comments TEXT DEFAULT NULL
        """)
        
        # Commit changes
        conn.commit()
        print("Migration completed successfully!")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Columns already exist. Migration not needed.")
        else:
            print(f"Error during migration: {e}")
            conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
