from pymongo import MongoClient
from datetime import datetime, timedelta
from bson import ObjectId
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client[os.getenv('MONGODB_DB', 'expense_tracker')]

# Collections
expenses_collection = db['expenses']
groups_collection = db['groups']
sessions_collection = db['sessions']
user_mappings_collection = db['user_mappings']
budgets_collection = db['budgets']

def get_user_id(phone_number):
    normalized_phone = phone_number.strip().replace(" ", "").replace("-", "").replace("whatsapp:", "").lstrip("+")
    
    mapping = user_mappings_collection.find_one({"phone_numbers": normalized_phone})
    
    if mapping:
        return mapping["user_id"]
    
    user_id = str(ObjectId())
    user_mappings_collection.insert_one({
        "user_id": user_id,
        "phone_numbers": [normalized_phone],
        "created_at": datetime.utcnow()
    })
    
    return user_id

def add_phone_to_user(user_id, phone_number):
    normalized_phone = phone_number.strip().replace(" ", "").replace("-", "").replace("whatsapp:", "").lstrip("+")
    
    mapping = user_mappings_collection.find_one({
        "user_id": user_id,
        "phone_numbers": normalized_phone
    })
    
    if not mapping:
        user_mappings_collection.update_one(
            {"user_id": user_id},
            {"$addToSet": {"phone_numbers": normalized_phone}}
        )
        return True
    
    return False

def load_expenses():
    return list(expenses_collection.find({}, {'_id': 0}))

def save_expenses(expenses):
    expenses_collection.delete_many({})
    if expenses:
        expenses_collection.insert_many(expenses)

def load_groups():
    return list(groups_collection.find({}, {'_id': 0}))

def save_groups(groups):
    groups_collection.delete_many({})
    if groups:
        groups_collection.insert_many(groups)

def load_sessions():
    return {str(session['user']): session['data'] for session in sessions_collection.find({}, {'_id': 0})}

def save_sessions(sessions):
    sessions_collection.delete_many({})
    if sessions:
        session_docs = [{'user': user, 'data': data} for user, data in sessions.items()]
        sessions_collection.insert_many(session_docs)

def add_expense(expense):
    expense['created_at'] = datetime.utcnow()
    expenses_collection.insert_one(expense)

def add_group(group):
    group['created_at'] = datetime.utcnow()
    groups_collection.insert_one(group)

def update_group(group_name, update_data):
    groups_collection.update_one(
        {'name': group_name},
        {'$set': update_data}
    )

def get_group_by_name(name):
    return groups_collection.find_one({'name': name}, {'_id': 0})

def get_user_expenses(user):
    user_id = get_user_id(user)
    
    mapping = user_mappings_collection.find_one({"user_id": user_id})
    if not mapping:
        return []

    phone_numbers = [f"whatsapp:+{phone}" for phone in mapping["phone_numbers"]]
    return list(expenses_collection.find({"user": {"$in": phone_numbers}}, {'_id': 0}))

def get_user_groups(user):
    user_mapping = user_mappings_collection.find_one({"phone_numbers": user})
    if not user_mapping:
        return []
    
    user_phone_numbers = user_mapping.get("phone_numbers", [])
    
    phone_patterns = [re.escape(phone) for phone in user_phone_numbers]
    
    return list(groups_collection.find(
        {"members": {"$in": user_phone_numbers}}
    ))

def get_user_budget(user_id):
    return budgets_collection.find_one({"user_id": user_id}, {'_id': 0})

def set_user_budget(user_id, budget_data):
    budgets_collection.update_one(
        {"user_id": user_id},
        {"$set": budget_data},
        upsert=True
    )

def get_user_budget_usage(user_id, month=None):
    if month is None:
        # Get current month's usage
        from datetime import datetime
        month = datetime.utcnow().strftime("%Y-%m")
    
    # Get user's phone numbers
    mapping = user_mappings_collection.find_one({"user_id": user_id})
    if not mapping:
        return {}
    
    phone_numbers = [f"whatsapp:+{phone}" for phone in mapping["phone_numbers"]]
    
    # Get all expenses for the user in the specified month
    expenses = list(expenses_collection.find({
        "user": {"$in": phone_numbers},
        "created_at": {
            "$gte": datetime.strptime(f"{month}-01", "%Y-%m-%d"),
            "$lt": datetime.strptime(f"{month}-01", "%Y-%m-%d").replace(day=28) + timedelta(days=4)
        }
    }))
    
    # Calculate usage by category
    usage = {}
    for expense in expenses:
        category = expense.get("category", "other")
        usage[category] = usage.get(category, 0) + expense["amount"]
    
    return usage 