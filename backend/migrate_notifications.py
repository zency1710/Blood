"""Migration script to add notifications table to existing database"""
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bloodbank.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if notifications table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'")
        if cursor.fetchone():
            print("Notifications table already exists. Skipping migration.")
            conn.close()
            return
        
        # Create notifications table
        cursor.execute('''
            CREATE TABLE notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                request_id INTEGER,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (request_id) REFERENCES user_requests (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        print("✓ Notifications table created successfully!")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("Starting database migration...")
    migrate()
    print("Migration completed!")
