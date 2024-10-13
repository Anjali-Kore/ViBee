# backend/app.py

from flask import Flask, jsonify, request
from flask_socketio import SocketIO, join_room, emit
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity, decode_token
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime
from flask_cors import CORS
from db import get_user, save_user, get_recent_rooms, add_recent_room, save_message, get_messages
from werkzeug.security import generate_password_hash, check_password_hash
from schemas import RegisterSchema, LoginSchema
from marshmallow import ValidationError

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my secret key'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'  # Change this!

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
jwt = JWTManager(app)

# Dictionary to store user sessions
users = {}

# Initialize Schemas
register_schema = RegisterSchema()
login_schema = LoginSchema()

# User Registration
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
    if success:
        return jsonify({'msg': 'User created successfully'}), 201
    else:
        return jsonify({'msg': 'Failed to create user'}), 500

# User Login with Rate Limiting
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
        access_token = create_access_token(identity=username)
        return jsonify({'access_token': access_token}), 200
    else:
        return jsonify({'msg': 'Invalid credentials'}), 401

# Protected Route Example
@app.route('/api/protected', methods=['GET', 'OPTIONS'])
@jwt_required()
def protected():
    if request.method == 'OPTIONS':
        return jsonify({'msg': 'Preflight request successful'}), 200

    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

# API Endpoint to Fetch Recent Rooms
@app.route('/api/recent_rooms', methods=['GET'])
@jwt_required()
def recent_rooms():
    current_user = get_jwt_identity()
    rooms = get_recent_rooms(current_user)
    return jsonify({'recent_rooms': rooms}), 200

# API Endpoint to Fetch Messages from a Room
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

if __name__ == "__main__":
    socketio.run(app, debug=True)
