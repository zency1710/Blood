"""Test script to verify user database operations"""
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bloodbank.db')

def test_users_table():
    """Test if users table exists and operations work"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Check if table exists
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cur.fetchone():
            print("ERROR: Users table does not exist!")
            return False
        
        print("[OK] Users table exists")
        
        # Test insert
        test_user = {
            'name': 'Test User',
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'contact': '1234567890',
            'blood_group': 'O+'
        }
        
        cur = conn.execute(
            'INSERT INTO users (name, username, email, password, contact, blood_group) VALUES (?, ?, ?, ?, ?, ?)',
            (test_user['name'], test_user['username'], test_user['email'], 
             test_user['password'], test_user['contact'], test_user['blood_group'])
        )
        conn.commit()
        user_id = cur.lastrowid
        print(f"[OK] Inserted test user with ID: {user_id}")
        
        # Test select
        cur = conn.execute('SELECT * FROM users WHERE id=?', (user_id,))
        row = cur.fetchone()
        if row:
            print(f"[OK] Retrieved user: {dict(row)}")
        else:
            print("ERROR: Could not retrieve inserted user!")
            return False
        
        # Test update
        cur = conn.execute('UPDATE users SET name=?, contact=? WHERE id=?', 
                         ('Updated Test User', '9876543210', user_id))
        conn.commit()
        print(f"[OK] Updated user ID: {user_id}")
        
        # Verify update
        cur = conn.execute('SELECT * FROM users WHERE id=?', (user_id,))
        row = cur.fetchone()
        if row and row['name'] == 'Updated Test User':
            print(f"[OK] Update verified: {dict(row)}")
        else:
            print("ERROR: Update not reflected!")
            return False
        
        # Test delete
        cur = conn.execute('DELETE FROM users WHERE id=?', (user_id,))
        conn.commit()
        print(f"[OK] Deleted user ID: {user_id}")
        
        # Verify delete
        cur = conn.execute('SELECT * FROM users WHERE id=?', (user_id,))
        if not cur.fetchone():
            print("[OK] Delete verified: User no longer exists")
        else:
            print("ERROR: User still exists after delete!")
            return False
        
        print("\n[SUCCESS] All database operations working correctly!")
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    test_users_table()

