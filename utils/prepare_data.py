import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = './data/dataset.db'

#recap de ce qu'il fait ce code:
#Charge les logs de activity_log
#Convertit les timestamps en date/heure
#Extrait des features utiles (heure, jour de la semaine, week-end, statut online/offline)

def load_activity_data():
    conn = sqlite3.connect(DB_PATH)
    query = '''
    SELECT participant_id, timestamp, status FROM activity_log ORDER BY timestamp
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convertir le timestamp en datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    
    # Extraire les features temporelles
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0 = lundi, 6 = dimanche
    df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)

    # Convertir 'status' en numérique (1 = online, 0 = offline)
    df['status'] = df['status'].apply(lambda x: 1 if x == 'online' else 0)

    return df

if __name__ == "__main__":
    data = load_activity_data()
    print(data.head())  # Vérifier les premières lignes

