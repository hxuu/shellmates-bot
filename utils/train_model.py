import xgboost as xgb
import pandas as pd
import pickle
from utils.prepare_data import load_activity_data
MODEL_PATH = './models/xgboost_model.pkl'

#recap de ce qu'il fait ce code 
#Charge les features depuis prepare_data.py
#Entraîne un modèle XGBoost pour prédire si un utilisateur sera en ligne à une heure donnée
#Sauvegarde le modèle dans ./models/xgboost_model.pkl

def train_model():
    df = load_activity_data()

    # Définir les features et la cible (heure où l'utilisateur est souvent online)
    X = df[['day_of_week', 'hour', 'is_weekend']]
    y = df['status']

    # Créer un modèle XGBoost
    model = xgb.XGBClassifier(n_estimators=100, learning_rate=0.1, max_depth=3)
    model.fit(X, y)

    # Sauvegarder le modèle
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)

    print("✅ Modèle XGBoost entraîné et sauvegardé.")

if __name__ == "__main__":
    train_model()
