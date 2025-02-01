import sqlite3
from datetime import datetime

def record_activity(participant_id, status):
    conn = sqlite3.connect('./data/dataset.db')
    cursor = conn.cursor()

    # Record changement de status
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('''
    INSERT INTO activity_log (participant_id, status, timestamp)
    VALUES (?, ?, ?)
    ''', (participant_id, status, timestamp))

    conn.commit()
    conn.close()
