import sqlite3
from datetime import datetime


def add_status_to_log(participant_id, status):
    """
    Adds a status log (online/offline) for a participant to the database.
    """
    try:
        conn = sqlite3.connect('./data/dataset.db')
        cursor = conn.cursor()

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('''
        INSERT INTO activity_log (participant_id, status, timestamp)
        VALUES (?, ?, ?)
        ''', (participant_id, status, timestamp))

        conn.commit()
    except sqlite3.Error as e:
        print(f"Error inserting status log: {e}")
    finally:
        conn.close()


def aggregate_participant_activity(participant_id):
    """
    Aggregates a participant's activity (online/offline) into a daily summary.
    This function processes the activity logs and stores a summary of online and offline times for each day.
    """
    try:
        conn = sqlite3.connect('./data/dataset.db')
        cursor = conn.cursor()

        cursor.execute('''
        SELECT timestamp, status
        FROM activity_log 
        WHERE participant_id = ?
        ORDER BY timestamp
        ''', (participant_id,))

        activity_data = cursor.fetchall()

        daily_summary = {}

        for row in activity_data:
            timestamp = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
            status = row[1]

            date_key = timestamp.date()

            if date_key not in daily_summary:
                daily_summary[date_key] = {
                    'online_times': [],
                    'offline_times': []
                }

            if status == 'online':
                daily_summary[date_key]['online_times'].append(timestamp)
            else:
                daily_summary[date_key]['offline_times'].append(timestamp)

        
        for date_key, times in daily_summary.items():
            
            cursor.execute('''
            SELECT COUNT(*) FROM daily_availability
            WHERE participant_id = ? AND date = ?
            ''', (participant_id, date_key))
            existing_entry = cursor.fetchone()[0]

            if existing_entry == 0:
                cursor.execute('''
                INSERT INTO daily_availability (participant_id, date, online_times, offline_times)
                VALUES (?, ?, ?, ?)
                ''', (participant_id, date_key, str(times['online_times']), str(times['offline_times'])))
            else:
                cursor.execute('''
                UPDATE daily_availability
                SET online_times = ?, offline_times = ?
                WHERE participant_id = ? AND date = ?
                ''', (str(times['online_times']), str(times['offline_times']), participant_id, date_key))

        conn.commit()

    except sqlite3.Error as e:
        print(f"Error aggregating participant activity: {e}")
    finally:
        conn.close()
