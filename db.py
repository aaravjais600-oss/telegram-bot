from pymongo import MongoClient
from config import MONGO_URL

client = MongoClient(MONGO_URL)
db = client["telegram_bot"]

# ✅ collections
users = db["users"]
settings = db["settings"]


# =========================
# USER FUNCTIONS
# =========================
def add_user(user_id):
    if not users.find_one({"user_id": user_id}):
        users.insert_one({
            "user_id": user_id
        })


def get_all_users():
    return [user["user_id"] for user in users.find()]


# =========================
# SETTINGS FUNCTIONS
# =========================
def set_setting(key, value):
    settings.update_one(
        {"key": key},
        {"$set": {"value": value}},
        upsert=True
    )


def get_setting(key, default=None):
    data = settings.find_one({"key": key})
    return data["value"] if data else default
