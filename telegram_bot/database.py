import json
import os
import random
import string
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "keys_db.json")

def load_db():
    if not os.path.exists(DB_FILE):
        default_db = {
            "DEMO_KEY": {"credits": 5, "created_at": datetime.now().isoformat(), "total_used": 0, "plan_name": "Demo Plan"},
            "users": {}  # telegram_id -> active_key
        }
        save_db(default_db)
        return default_db
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"DEMO_KEY": {"credits": 5, "created_at": datetime.now().isoformat(), "total_used": 0}, "users": {}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_user_key(user_id):
    db = load_db()
    return db.get("users", {}).get(str(user_id))

def set_user_key(user_id, key):
    db = load_db()
    if "users" not in db:
        db["users"] = {}
    db["users"][str(user_id)] = key
    save_db(db)

def get_key_data(key):
    db = load_db()
    return db.get(key.upper())

def generate_key(credits=1, plan_name="Standard Plan"):
    db = load_db()
    rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    new_key = f"GPTIND_{rand_str}"
    db[new_key] = {
        "credits": int(credits),
        "plan_name": plan_name,
        "created_at": datetime.now().isoformat(),
        "total_used": 0,
        "refunded_orders": {}
    }
    save_db(db)
    return new_key, db[new_key]

def deduct_credit(key):
    db = load_db()
    key_upper = key.upper()
    if key_upper in db and db[key_upper].get("credits", 0) > 0:
        db[key_upper]["credits"] -= 1
        db[key_upper]["total_used"] = db[key_upper].get("total_used", 0) + 1
        save_db(db)
        return True, db[key_upper]["credits"]
    return False, 0

def refund_credit(key, order_code):
    db = load_db()
    key_upper = key.upper()
    if key_upper in db:
        if "refunded_orders" not in db[key_upper]:
            db[key_upper]["refunded_orders"] = {}
        if order_code not in db[key_upper]["refunded_orders"]:
            db[key_upper]["refunded_orders"][order_code] = True
            db[key_upper]["credits"] = db[key_upper].get("credits", 0) + 1
            save_db(db)
            return True, db[key_upper]["credits"]
    return False, db.get(key_upper, {}).get("credits", 0)

def add_credits(key, credits_to_add):
    db = load_db()
    key_upper = key.upper()
    if key_upper not in db:
        db[key_upper] = {"credits": 0, "created_at": datetime.now().isoformat(), "total_used": 0}
    db[key_upper]["credits"] += int(credits_to_add)
    save_db(db)
    return db[key_upper]["credits"]

def revoke_key(key):
    db = load_db()
    key_upper = key.upper()
    if key_upper in db:
        del db[key_upper]
        save_db(db)
        return True
    return False

def list_all_keys():
    db = load_db()
    keys_list = {k: v for k, v in db.items() if k != "users"}
    return keys_list
