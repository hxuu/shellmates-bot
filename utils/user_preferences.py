import json
import os

def load_data_pref(data_file):
    if not os.path.exists(data_file) or os.path.getsize(data_file) == 0:
        with open(data_file, 'w') as f:
            json.dump({}, f)
    try:
        with open(data_file, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Reset the file to an empty dictionary if corrupted
        with open(data_file, 'w') as f:
            json.dump({}, f)
        return {}

def save_data_pref(data_file, data):
    """
    Save user availability to the JSON file.
    """
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=4)