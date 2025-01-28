import os
import json

REMINDER_FILE = "data/reminders.json"


def ensure_data_file():
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE, "w") as file:
            json.dump({"REMINDERS": []}, file)


def load_reminders():
    ensure_data_file()
    try:
        with open(REMINDER_FILE, "r") as file:
            data = json.load(file)
            return data.get("REMINDERS", [])
    except (json.JSONDecodeError, FileNotFoundError):
        print("No reminders found")
        return []


def save_reminders(reminders):
    ensure_data_file()
    try:
        with open(REMINDER_FILE, "w") as file:
            json.dump({"REMINDERS": reminders}, file, indent=4)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde : {e}")

