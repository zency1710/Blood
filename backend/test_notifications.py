"""Test script to demonstrate the notification system"""
import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bloodbank.db')

def test_notifications():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 60)
    print("NOTIFICATION SYSTEM TEST")
    print("=" * 60)
    
    # Check if notifications table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'")
    if cursor.fetchone():
        print("✓ Notifications table exists")
    else:
        print("✗ Notifications table does not exist")
        conn.close()
        return
    
    # Get all users
    cursor.execute("SELECT id, name, email FROM users")
    users = cursor.fetchall()
    print(f"\n✓ Found {len(users)} users in the system:")
    for user in users:
        print(f"  - User {user['id']}: {user['name']} ({user['email']})")
    
    # Get all user requests
    cursor.execute("SELECT id, user_id, patient_name, blood_group, status FROM user_requests")
    requests = cursor.fetchall()
    print(f"\n✓ Found {len(requests)} user requests:")
    for req in requests:
        print(f"  - Request {req['id']}: Patient {req['patient_name']}, Blood Group {req['blood_group']}, Status: {req['status']}")
    
    # Get all notifications
    cursor.execute("SELECT * FROM notifications ORDER BY created_at DESC")
    notifications = cursor.fetchall()
    print(f"\n✓ Found {len(notifications)} notifications:")
    for notif in notifications:
        is_read = "Read" if notif['is_read'] == 1 else "Unread"
        print(f"  - Notification {notif['id']} for User {notif['user_id']}: {notif['title']}")
        print(f"    Type: {notif['type']}, Status: {is_read}")
        print(f"    Message: {notif['message']}")
        print(f"    Created: {notif['created_at']}")
        print()
    
    # Count unread notifications per user
    print("\nUnread Notifications by User:")
    for user in users:
        cursor.execute("SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0", (user['id'],))
        count = cursor.fetchone()['count']
        print(f"  - {user['name']}: {count} unread notification(s)")
    
    conn.close()
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)

if __name__ == '__main__':
    test_notifications()
