import sqlite3
import os

# Get the directory containing this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bloodbank.db')

# SQL statements to create tables
SCHEMA = """
CREATE TABLE IF NOT EXISTS donors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER,
    blood_group TEXT NOT NULL,
    contact TEXT,
    city TEXT,
    last_donation_date TEXT
);

CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT NOT NULL,
    blood_group TEXT NOT NULL,
    units INTEGER,
    hospital TEXT,
    city TEXT,
    contact TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    contact TEXT,
    blood_group TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: user_donations (tracks donation history for registered users)
CREATE TABLE IF NOT EXISTS user_donations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    donor_id INTEGER,
    blood_group TEXT NOT NULL,
    donation_date TEXT NOT NULL,
    location TEXT,
    units_donated INTEGER DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (donor_id) REFERENCES donors (id) ON DELETE SET NULL
);

-- Table: user_requests (tracks blood request history for registered users)
CREATE TABLE IF NOT EXISTS user_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    request_id INTEGER,
    patient_name TEXT NOT NULL,
    blood_group TEXT NOT NULL,
    units_requested INTEGER,
    hospital TEXT,
    city TEXT,
    contact TEXT,
    urgency_level TEXT DEFAULT 'normal',
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (request_id) REFERENCES requests (id) ON DELETE SET NULL
);

-- Insert default admin account
INSERT OR IGNORE INTO admin (username, password) VALUES ('admin', 'admin123');
"""

def init_db():
    # Create a new database connection
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Execute the schema
        conn.executescript(SCHEMA)
        print(f"Database initialized successfully at {DB_PATH}")
        print("Default admin credentials:")
        print("Username: admin")
        print("Password: admin123")
        
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
    
    finally:
        conn.commit()
        conn.close()

if __name__ == "__main__":
    init_db()
