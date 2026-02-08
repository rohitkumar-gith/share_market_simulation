import sqlite3
import os

# Connect to the database
db_path = os.path.join("share_market_system", "market_simulation.db")

# Check if DB exists
if not os.path.exists(db_path):
    # Try looking in current directory if not found in subfolder
    if os.path.exists("market_simulation.db"):
        db_path = "market_simulation.db"
    else:
        print("Error: Could not find 'market_simulation.db'")
        exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Ask for username
target_user = input("Enter the username to promote to Admin: ")

# Check if user exists
cursor.execute("SELECT * FROM users WHERE username = ?", (target_user,))
user = cursor.fetchone()

if user:
    # Update is_admin to 1
    cursor.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (target_user,))
    conn.commit()
    print(f"\nSUCCESS! User '{target_user}' is now an Admin.")
    print("Restart the application to see the 'ADMIN PANEL' button.")
else:
    print(f"\nError: User '{target_user}' not found.")

conn.close()