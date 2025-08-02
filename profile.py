import json
import os

def load_profile(user):
    filename = f"{user['name']}_profile.json"
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {"name": user["name"], "premium": user.get("premium", False)}

def save_profile(user, profile):
    filename = f"{user['name']}_profile.json"
    with open(filename, "w") as f:
        json.dump(profile, f)
