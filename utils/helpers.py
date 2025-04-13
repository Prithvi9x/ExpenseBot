import json
import os

def normalize(phone):
    return phone.strip().replace(" ", "").replace("-", "").replace("whatsapp:", "").lstrip("+")

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2) 