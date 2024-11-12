
import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from engineio.async_drivers import eventlet

# Use eventlet for WebSocket support
import eventlet
eventlet.monkey_patch()

app = Flask(__name__)
# Get configuration from environment variables
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-dev-key')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', '0') == '1'

# Configure SocketIO with proper settings for production
socketio = SocketIO(
    app,
    cors_allowed_origins="*",  # Configure according to your needs
    async_mode='eventlet',
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
)

# Store messages and typing users in memory
# Note: In production, you might want to use Redis or another persistent store
messages = []
typing_users = set()

@app.route('/')
def index():
    return render_template('index.html', messages=messages)

@socketio.on('connect')
def handle_connect():
    app.logger.info('Client connected')
    # Send existing messages to new client
    for message in messages:
        emit('receive_message', message)

@socketio.on('disconnect')
def handle_disconnect():
    app.logger.info('Client disconnected')
    # Clean up typing status when user disconnects
    # Note: This requires tracking user sessions properly
    for username in list(typing_users):
        typing_users.discard(username)
    emit('typing_update', {'typing_users': list(typing_users)}, broadcast=True)

@socketio.on('send_message')
def handle_message(data):
    try:
        message = {
            'username': data['username'],
            'message': data['message'],
            'timestamp': data['timestamp']
        }
        messages.append(message)
        # Remove user from typing set when they send a message
        typing_users.discard(data['username'])
        emit('receive_message', message, broadcast=True)
        emit('typing_update', {'typing_users': list(typing_users)}, broadcast=True)
    except Exception as e:
        app.logger.error(f'Error handling message: {str(e)}')
        emit('error', {'message': 'Error processing message'})

@socketio.on('typing')
def handle_typing(data):
    try:
        username = data['username']
        is_typing = data['is_typing']

        if is_typing:
            typing_users.add(username)
        else:
            typing_users.discard(username)

        emit('typing_update', {'typing_users': list(typing_users)}, broadcast=True)
    except Exception as e:
        app.logger.error(f'Error handling typing status: {str(e)}')
        emit('error', {'message': 'Error updating typing status'})

@socketio.on_error()
def error_handler(e):
    app.logger.error(f'SocketIO error: {str(e)}')
    emit('error', {'message': 'An error occurred'})

# Health check endpoint
@app.route('/health')
def health_check():
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8000))

    socketio.run(
        app,
        host=host,
        port=port,
        debug=app.config['DEBUG'],
        use_reloader=False,  # Disable reloader in production
        log_output=True
    )