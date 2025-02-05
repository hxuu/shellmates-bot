import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from utils.train_model import MODEL_PATH

#recap de ce qu'il fait ce code :
#Charge le modèle XGBoost
#Teste chaque heure de la journée et prédit la meilleure heure pour envoyer un rappel

def load_model():
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    return model

def predict_best_reminder_time():
    model = load_model()
    
    # Générer les features pour les prochaines heures
    now = datetime.now()
    hours = np.arange(0, 24)  # Tester toutes les heures de la journée
    
    predictions = []
    for hour in hours:
        data = pd.DataFrame({
            'day_of_week': [now.weekday()] * 24,
            'hour': [hour] * 24,
            'is_weekend': [1 if now.weekday() >= 5 else 0] * 24
        })
        
        prob = model.predict_proba(data)[:, 1]  # Probabilité d'être online
        predictions.append((hour, prob.mean()))

    # Trouver l'heure avec la plus grande probabilité d'être online
    best_hour = max(predictions, key=lambda x: x[1])[0]

    print(f"⏰ Heure optimale du rappel : {best_hour}:00")

if __name__ == "__main__":
    predict_best_reminder_time()
