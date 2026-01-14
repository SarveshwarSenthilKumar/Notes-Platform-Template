from sql import SQL
from SarvAuth import hash
import getpass

def create_user():
    print("=== Create New User ===")
    
    # Get user input
    username = input("Username: ").strip().lower()
    password = getpass.getpass("Password: ").strip()
    email = input("Email: ").strip().lower()
    full_name = input("Full Name: ").strip()
    
    # Hash the password
    hashed_password = hash(password)
    
    # Connect to the database
    db = SQL("sqlite:///users.db")
    
    try:
        # Check if username already exists
        existing_user = db.execute("SELECT * FROM users WHERE username = :username", username=username)
        if existing_user:
            print("Error: Username already exists!")
            return
            
        # Insert new user
        db.execute(
            """
            INSERT INTO users (username, password, emailaddress, name, accountStatus, role)
            VALUES (:username, :password, :email, :name, 'active', 'user')
            """,
            username=username,
            password=hashed_password,
            email=email,
            name=full_name
        )
        
        print(f"\nUser '{username}' created successfully!")
        
    except Exception as e:
        print(f"Error creating user: {str(e)}")

if __name__ == "__main__":
    create_user()
