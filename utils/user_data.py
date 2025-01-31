import json
from pathlib import Path

USER_DATA_PATH = Path('./data/user_emails.json')
        
def save_user_email(user_id: int, email: str, roles: list):
    data = get_user_emails()
    data[str(user_id)] = {
        "email": email,
        "roles": [str(role_id) for role_id in roles]
    }
    with open(USER_DATA_PATH, 'w') as f:
        json.dump(data, f)

def get_user_emails():
    if not USER_DATA_PATH.exists():
        return {}
    with open(USER_DATA_PATH, 'r') as f:
        return json.load(f)