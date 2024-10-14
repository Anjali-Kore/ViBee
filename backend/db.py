# backend/db.py

import os
from datetime import datetime

from dotenv import load_dotenv
from pymongo import MongoClient, DESCENDING
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables from .env
load_dotenv()

# Configuration
MONGODB_URI = os.getenv('MONGODB_URI')  # MongoDB connection string

# Initialize MongoDB Client
client = MongoClient(MONGODB_URI)
chat_db = client.get_database('Chatapp')

# Collections
users_collection = chat_db.get_collection('users')
messages_collection = chat_db.get_collection('messages')  # Collection for messages
otps_collection = chat_db.get_collection('otps')  # Collection for OTPs


# User Model
class User:
    def __init__(self, username, email, password_hash, is_active=False, recent_rooms=None):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.is_active = is_active
        self.recent_rooms = recent_rooms if recent_rooms else []

    def check_password(self, password_input):
        """Check if the provided password matches the stored password hash."""
        return check_password_hash(self.password_hash, password_input)


# User Management Functions
def save_user(username, email, password):
    """
    Saves a new user to the users collection.
    
    Args:
        username (str): The username of the user.
        email (str): The user's email address.
        password (str): The user's password.
    
    Returns:
        bool: True if the user was saved successfully, False otherwise.
    """
    password_hash = generate_password_hash(password)
    try:
        users_collection.insert_one({
            '_id': username,
            'email': email,
            'password': password_hash,
            'is_active': False,  # Initialize as inactive
            'recent_rooms': []
        })
        return True
    except Exception as e:
        print(f"Error saving user: {e}")
        return False


def get_user(username):
    """
    Retrieves a user from the users collection by username.
    
    Args:
        username (str): The username of the user.
    
    Returns:
        User or None: Returns a User object if found, otherwise None.
    """
    try:
        user_data = users_collection.find_one({'_id': username})
        if user_data:
            return User(
                username=user_data['_id'],
                email=user_data['email'],
                is_active=user_data['is_active'],
                password_hash=user_data['password'],
                recent_rooms=user_data.get('recent_rooms', []),
            )
        return None
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None


# Recent Rooms Management
def get_recent_rooms(username, limit=5):
    """
    Retrieves the recent chat rooms for a user.
    
    Args:
        username (str): The username of the user.
        limit (int): The maximum number of recent rooms to retrieve.
    
    Returns:
        list: A list of recent room IDs.
    """
    try:
        user_data = users_collection.find_one({'_id': username}, {'recent_rooms': 1})
        if user_data and 'recent_rooms' in user_data:
            return user_data['recent_rooms']
        return []
    except Exception as e:
        print(f"Error fetching recent rooms: {e}")
        return []


def add_recent_room(username, roomid, limit=5):
    """
    Adds a room to the user's list of recent rooms.
    
    Args:
        username (str): The username of the user.
        roomid (str): The ID of the room to add.
        limit (int): The maximum number of recent rooms to keep.
    
    Returns:
        bool: True if the room was added successfully, False otherwise.
    """
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


# Message Persistence Functions
def save_message(roomid, username, message):
    """
    Saves a message to the messages collection.
    
    Args:
        roomid (str): The ID of the room where the message was sent.
        username (str): The username of the sender.
        message (str): The message content.
    
    Returns:
        bool: True if the message was saved successfully, False otherwise.
    """
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
    """
    Retrieves messages from a specific room with pagination.
    
    Args:
        roomid (str): The ID of the room.
        limit (int): The number of messages to retrieve.
        offset (int): The number of messages to skip.
    
    Returns:
        list: A list of message dictionaries.
    """
    try:
        cursor = messages_collection.find({'roomid': roomid}).sort('timestamp', DESCENDING).skip(offset).limit(limit)
        messages = list(cursor)
        messages.reverse()  # To return messages in chronological order
        return messages
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return []


# OTP Management Functions
def save_otp(email, otp, expires_at):
    """
    Saves an OTP to the otps collection.
    
    Args:
        email (str): The email address associated with the OTP.
        otp (str): The OTP code.
        expires_at (datetime): The expiration time of the OTP.
    
    Returns:
        bool: True if the OTP was saved successfully, False otherwise.
    """
    try:
        otps_collection.insert_one({
            'email': email,
            'otp': otp,
            'expires_at': expires_at
        })
        return True
    except Exception as e:
        print(f"Error saving OTP: {e}")
        return False


def get_otp(email, otp):
    """
    Retrieves an OTP from the otps collection.
    
    Args:
        email (str): The email address associated with the OTP.
        otp (str): The OTP code.
    
    Returns:
        dict or None: The OTP document if found, otherwise None.
    """
    try:
        return otps_collection.find_one({'email': email, 'otp': otp})
    except Exception as e:
        print(f"Error fetching OTP: {e}")
        return None


def delete_otp(email, otp):
    """
    Deletes an OTP from the otps collection.
    
    Args:
        email (str): The email address associated with the OTP.
        otp (str): The OTP code.
    
    Returns:
        bool: True if the OTP was deleted successfully, False otherwise.
    """
    try:
        otps_collection.delete_one({'email': email, 'otp': otp})
        return True
    except Exception as e:
        print(f"Error deleting OTP: {e}")
        return False


def update_otp(email, otp, new_otp, new_expires_at):
    """
    Updates an existing OTP in the otps collection.
    
    Args:
        email (str): The email address associated with the OTP.
        otp (str): The current OTP code.
        new_otp (str): The new OTP code.
        new_expires_at (datetime): The new expiration time.
    
    Returns:
        bool: True if the OTP was updated successfully, False otherwise.
    """
    try:
        otps_collection.update_one(
            {'email': email, 'otp': otp},
            {'$set': {'otp': new_otp, 'expires_at': new_expires_at}}
        )
        return True
    except Exception as e:
        print(f"Error updating OTP: {e}")
        return False
