# backend/app.py
import os
import random
import string
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity, decode_token
)
from flask_mail import Mail, Message
from flask_socketio import SocketIO, emit, join_room
from marshmallow import ValidationError

from db import (
    add_recent_room, delete_otp, get_messages,
    get_otp, get_recent_rooms, get_user,
    otps_collection, save_message, save_otp,
    save_user, users_collection
)
from schemas import LoginSchema, RegisterSchema

# Load environment variables from .env
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['MAIL_SERVER'] = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('SMTP_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('SMTP_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('SMTP_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('SMTP_USERNAME')

# Initialize Flask-Mail
mail = Mail(app)

# Configure CORS
CORS(app, resources={
    r"/api/*": {
        "origins": "http://localhost:5173",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type", "Authorization"]
    }
}, supports_credentials=True)

# Initialize SocketIO with specific CORS settings
socketio = SocketIO(app, cors_allowed_origins="http://localhost:5173")

# Initialize JWT Manager
jwt = JWTManager(app)


# Utility Functions
def generate_otp(length=6):
    """Generates a numeric OTP of specified length."""
    return ''.join(random.choices(string.digits, k=length))

def send_otp_via_email(email, otp):
    """Sends OTP to the user's email."""
    subject = 'Your OTP Code for ViBee'
    body = f'Your OTP code is {otp}. It expires in 10 minutes.'

    msg = Message(subject=subject, recipients=[email], body=body)

    try:
        mail.send(msg)
        print(f"OTP sent to {email}")
        return True
    except Exception as e:
        print(f"Failed to send OTP: {e}")
        return False

# Dictionary to store user sessions
users = {}

# Initialize Schemas
register_schema = RegisterSchema()
login_schema = LoginSchema()

# Routes
## User Registration
@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return jsonify({'msg': 'Preflight request successful'}), 200

    try:
        data = register_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    username = data['username']
    email = data['email']
    password = data['password']

    if get_user(username):
        return jsonify({'msg': 'User already exists'}), 409

    success = save_user(username, email, password)
    if not success:
        return jsonify({'msg': 'Failed to create user'}), 500

    # Generate OTP
    otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # Save OTP
    otp_saved = save_otp(email, otp, expires_at)
    if not otp_saved:
        return jsonify({'msg': 'Failed to generate OTP'}), 500

    # Send OTP
    email_sent = send_otp_via_email(email, otp)
    if not email_sent:
        return jsonify({'msg': 'Failed to send OTP'}), 500

    return jsonify({'msg': 'User registered successfully. Please verify your email with the OTP sent.'}), 201

## User Login
@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return jsonify({'msg': 'Preflight request successful'}), 200

    try:
        data = login_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    username = data['username']
    password_input = data['password']

    user = get_user(username)
    if user and user.check_password(password_input):
        if user.is_active:
            access_token = create_access_token(identity=username)
            return jsonify({'access_token': access_token}), 200
        return jsonify({'msg': 'Account not verified. Please verify your email with the OTP sent.'}), 403
    else:
        return jsonify({'msg': 'Invalid credentials'}), 401

## Protected Route
@app.route('/api/protected', methods=['GET', 'OPTIONS'])
@jwt_required()
def protected():
    if request.method == 'OPTIONS':
        return jsonify({'msg': 'Preflight request successful'}), 200

    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

## Fetch Recent Rooms
@app.route('/api/recent_rooms', methods=['GET'])
@jwt_required()
def recent_rooms():
    current_user = get_jwt_identity()
    rooms = get_recent_rooms(current_user)
    return jsonify({'recent_rooms': rooms}), 200

## Fetch Messages from a Room
@app.route('/api/messages/<roomid>', methods=['GET'])
@jwt_required()
def fetch_messages(roomid):
    current_user = get_jwt_identity()
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
    except ValueError:
        return jsonify({'msg': 'Invalid limit or offset'}), 400

    messages = get_messages(roomid, limit=limit, offset=offset)
    formatted_messages = [
        {
            'username': msg['username'],
            'message': msg['message'],
            'timestamp': msg['timestamp'].isoformat() + 'Z'
        }
        for msg in messages
    ]
    return jsonify({'messages': formatted_messages}), 200

## Verify OTP
@app.route('/api/verify-otp', methods=['POST', 'OPTIONS'])
def verify_otp():
    if request.method == 'OPTIONS':
        return jsonify({'msg': 'Preflight request successful'}), 200

    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')

    if not email or not otp:
        return jsonify({'msg': 'Email and OTP are required.'}), 400

    otp_entry = get_otp(email, otp)
    if not otp_entry:
        return jsonify({'msg': 'Invalid OTP.'}), 400

    if datetime.utcnow() > otp_entry['expires_at']:
        return jsonify({'msg': 'OTP has expired.'}), 400

    # Activate the user
    try:
        users_collection.update_one({'email': email}, {'$set': {'is_active': True}})
    except Exception as e:
        print(f"Error activating user: {e}")
        return jsonify({'msg': 'Failed to activate account.'}), 500

    # Delete the OTP entry
    delete_otp(email, otp)

    return jsonify({'msg': 'Account verified successfully.'}), 200

## Resend OTP
@app.route('/api/resend-otp', methods=['POST', 'OPTIONS'])
def resend_otp():
    if request.method == 'OPTIONS':
        return jsonify({'msg': 'Preflight request successful'}), 200

    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'msg': 'Email is required.'}), 400

    # Find the user by email
    user = users_collection.find_one({'email': email})
    if not user:
        return jsonify({'msg': 'User does not exist.'}), 400

    if user.get('is_active'):
        return jsonify({'msg': 'Account is already active.'}), 400

    # Generate new OTP
    otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # Update or insert OTP
    try:
        otps_collection.update_one(
            {'email': email},
            {'$set': {'otp': otp, 'expires_at': expires_at}},
            upsert=True
        )
    except Exception as e:
        print(f"Error updating OTP: {e}")
        return jsonify({'msg': 'Failed to generate OTP.'}), 500

    # Send OTP
    email_sent = send_otp_via_email(email, otp)
    if not email_sent:
        return jsonify({'msg': 'Failed to send OTP'}), 500

    return jsonify({'msg': 'OTP resent successfully.'}), 200

# Socket.IO Events
@socketio.on('connect')
def handle_connect(auth):
    token = auth.get('token')
    if not token:
        emit('error', {'msg': 'Missing token'})
        return False  # Disconnect the client

    try:
        decoded = decode_token(token)
        username = decoded['sub']
        users[request.sid] = username  # Associate sid with username
        print(f"User {username} connected with sid {request.sid}")
    except Exception as e:
        print(f"Invalid token: {e}")
        emit('error', {'msg': 'Invalid token'})
        return False  # Disconnect the client

@socketio.on('disconnect')
def handle_disconnect():
    username = users.pop(request.sid, None)
    if username:
        print(f"User {username} disconnected")

@socketio.on('join_room')
def handle_join_room_event(data):
    username = users.get(request.sid)
    if not username:
        emit('error', {'msg': 'Unauthorized'})
        return

    room = data.get('roomid')
    if not room:
        emit('error', {'msg': 'Missing room ID'})
        return

    join_room(room)
    app.logger.info(f"{username} has joined the room {room}")
    emit('join_room_announcement', {
        'username': 'System',
        'message': f"{username} has joined the room."
    }, room=room)

    # Add to recent rooms
    success = add_recent_room(username, room)
    if not success:
        app.logger.error(f"Failed to add room {room} to {username}'s recent rooms")

    # Fetch and send previous messages to the client
    messages = get_messages(room)
    formatted_messages = [
        {
            'username': msg['username'],
            'message': msg['message'],
            'timestamp': msg['timestamp'].isoformat() + 'Z'
        }
        for msg in messages
    ]
    emit('previous_messages', {'messages': formatted_messages})

@socketio.on('send_message')
def handle_send_message_event(data):
    username = users.get(request.sid)
    if not username:
        emit('error', {'msg': 'Unauthorized'})
        return

    room = data.get('roomid')
    message = data.get('message')

    if not room or not message:
        emit('error', {'msg': 'Missing room ID or message'})
        return

    # Save the message to the database
    success = save_message(room, username, message)
    if not success:
        emit('error', {'msg': 'Failed to save message'})
        return

    app.logger.info(f"{username} has sent a message in room {room}: {message}")
    emit('receive_message', {
        'username': username,
        'message': message,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }, room=room)

# Run the application
if __name__ == "__main__":
    socketio.run(app, debug=True)
