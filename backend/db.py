from pymongo import MongoClient, DESCENDING
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from dotenv import load_dotenv
import os
load_dotenv()

# Replace with your actual MongoDB URI
MONGODB_URI = os.getenv('MONGO_URI')  # For local MongoDB 


client = MongoClient(MONGODB_URI)
chat_db = client.get_database('Chatapp')
users_collection = chat_db.get_collection('users')
messages_collection = chat_db.get_collection('messages')  # Collection for messages

class User:
    def __init__(self, username, email, password_hash, recent_rooms=None):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.recent_rooms = recent_rooms if recent_rooms else []

    def check_password(self, password_input):
        return check_password_hash(self.password_hash, password_input)

def save_user(username, email, password):
    password_hash = generate_password_hash(password)
    try:
        users_collection.insert_one({
            '_id': username,
            'email': email,
            'password': password_hash,
            'recent_rooms': []  # Initialize empty recent_rooms
        })
        return True
    except Exception as e:
        print(f"Error saving user: {e}")
        return False

def get_user(username):
    try:
        user_data = users_collection.find_one({'_id': username})
        if user_data:
            return User(
                username=user_data['_id'],
                email=user_data['email'],
                password_hash=user_data['password'],
                recent_rooms=user_data.get('recent_rooms', [])
            )
        return None
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None

def get_recent_rooms(username, limit=5):
    try:
        user_data = users_collection.find_one({'_id': username}, {'recent_rooms': 1})
        if user_data and 'recent_rooms' in user_data:
            return user_data['recent_rooms']
        return []
    except Exception as e:
        print(f"Error fetching recent rooms: {e}")
        return []

def add_recent_room(username, roomid, limit=5):
    try:
        # Remove the room if it already exists to avoid duplicates
        users_collection.update_one(
            {'_id': username},
            {'$pull': {'recent_rooms': roomid}}
        )
        # Add the room to the beginning of the list
        users_collection.update_one(
            {'_id': username},
            {'$push': {'recent_rooms': {'$each': [roomid], '$position': 0, '$slice': limit}}}
        )
        return True
    except Exception as e:
        print(f"Error adding recent room: {e}")
        return False

# Functions for Message Persistence

def save_message(roomid, username, message):
    """Saves a message to the messages collection."""
    try:
        messages_collection.insert_one({
            'roomid': roomid,
            'username': username,
            'message': message,
            'timestamp': datetime.utcnow()
        })
        return True
    except Exception as e:
        print(f"Error saving message: {e}")
        return False

def get_messages(roomid, limit=50, offset=0):
    """Retrieves messages from a room with pagination."""
    try:
        cursor = messages_collection.find({'roomid': roomid}).sort('timestamp', DESCENDING).skip(offset).limit(limit)
        messages = list(cursor)
        messages.reverse()
        return messages
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return []
