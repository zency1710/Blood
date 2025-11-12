-- Blood Bank Database Schema

-- Table: donors
CREATE TABLE donors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER,
    blood_group TEXT NOT NULL,
    contact TEXT,
    city TEXT,
    last_donation_date TEXT
);

-- Table: requests
CREATE TABLE requests (
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

-- Table: admin
CREATE TABLE admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);

-- Table: user_donations (tracks donation history for registered users)
CREATE TABLE user_donations (
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
CREATE TABLE user_requests (
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

-- Table: notifications (tracks notifications for users about their requests)
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
);

-- Table: users (registered users of the system)
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

-- Insert default admin account
INSERT INTO admin (username, password) VALUES ('admin', 'admin123');
