import sqlite3
import os

# Create or overwrite the dictionary database
database = open('dictionary.db', 'w')
database.truncate(0)  
database.close()

# Connect to the SQLite database
connection = sqlite3.connect("dictionary.db")
crsr = connection.cursor()

# Define the table structure
create_table_sql = """
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_phrase TEXT NOT NULL,
    definition TEXT NOT NULL,
    example TEXT,
    views INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    unit_number INTEGER,
    comments TEXT
)
"""

# Create indexes for faster lookups
indexes = [
    "CREATE INDEX idx_word_phrase ON entries(word_phrase)",
    "CREATE INDEX idx_views ON entries(views)"
]

# Execute the table creation and indexes
crsr.execute(create_table_sql)
for index in indexes:
    crsr.execute(index)

# Create a trigger to update the last_updated timestamp
crsr.execute("""
CREATE TRIGGER update_entry_timestamp
AFTER UPDATE ON entries
FOR EACH ROW
BEGIN
    UPDATE entries 
    SET last_updated = CURRENT_TIMESTAMP
    WHERE id = old.id;
END;
""")

# Commit changes and close the connection
connection.commit()
crsr.close()
connection.close()

print("Dictionary database initialized successfully!")