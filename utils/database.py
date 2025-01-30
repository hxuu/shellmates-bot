import sqlite3


def init_db():
    conn = sqlite3.connect('./data/dataset.db')
    cursor = conn.cursor()

    # creer participant availability table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS participant_availability (
        participant_id INTEGER PRIMARY KEY,
        username TEXT,
        start_time TEXT,
        end_time TEXT,
        timezone TEXT
    )
    ''')

    # creer activity log table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS activity_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        participant_id INTEGER,
        status TEXT,
        timestamp TEXT,
        FOREIGN KEY (participant_id) REFERENCES participant_availability(participant_id)
    )
    ''')

    conn.commit()
    conn.close()


init_db()
