"""Debug script to check request and notification linkage"""
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bloodbank.db')

def debug_requests():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 80)
    print("DEBUG: REQUESTS AND NOTIFICATIONS")
    print("=" * 80)
    
    # Check all requests
    print("\n1. ALL REQUESTS (from requests table):")
    print("-" * 80)
    cursor.execute("SELECT id, patient_name, blood_group, status, contact FROM requests")
    requests = cursor.fetchall()
    for req in requests:
        print(f"  Request ID: {req['id']}")
        print(f"  Patient: {req['patient_name']}")
        print(f"  Blood Group: {req['blood_group']}")
        print(f"  Status: {req['status']}")
        print(f"  Contact: {req['contact']}")
        print()
    
    # Check all user_requests
    print("\n2. ALL USER_REQUESTS (from user_requests table):")
    print("-" * 80)
    cursor.execute("SELECT id, user_id, request_id, patient_name, blood_group, status FROM user_requests")
    user_requests = cursor.fetchall()
    for ur in user_requests:
        print(f"  User Request ID: {ur['id']}")
        print(f"  User ID: {ur['user_id']}")
        print(f"  Linked Request ID: {ur['request_id']}")
        print(f"  Patient: {ur['patient_name']}")
        print(f"  Blood Group: {ur['blood_group']}")
        print(f"  Status: {ur['status']}")
        print()
    
    # Check linkage
    print("\n3. LINKAGE CHECK:")
    print("-" * 80)
    for req in requests:
        cursor.execute("SELECT COUNT(*) as count FROM user_requests WHERE request_id = ?", (req['id'],))
        count = cursor.fetchone()['count']
        print(f"  Request ID {req['id']} ({req['patient_name']}) -> {count} user_request(s) linked")
    
    # Check notifications
    print("\n4. ALL NOTIFICATIONS:")
    print("-" * 80)
    cursor.execute("SELECT id, user_id, request_id, title, message, type, is_read FROM notifications")
    notifications = cursor.fetchall()
    if notifications:
        for notif in notifications:
            print(f"  Notification ID: {notif['id']}")
            print(f"  User ID: {notif['user_id']}")
            print(f"  User Request ID: {notif['request_id']}")
            print(f"  Title: {notif['title']}")
            print(f"  Type: {notif['type']}")
            print(f"  Read: {'Yes' if notif['is_read'] == 1 else 'No'}")
            print()
    else:
        print("  No notifications found!")
    
    conn.close()
    print("=" * 80)

if __name__ == '__main__':
    debug_requests()
