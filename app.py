from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app)

messages = []
typing_users = set()

@app.route('/')
def index():
    return render_template('index.html', messages=messages)

@socketio.on('send_message')
def handle_message(data):
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

@socketio.on('typing')
def handle_typing(data):
    username = data['username']
    is_typing = data['is_typing']

    if is_typing:
        typing_users.add(username)
    else:
        typing_users.discard(username)

    emit('typing_update', {'typing_users': list(typing_users)}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)