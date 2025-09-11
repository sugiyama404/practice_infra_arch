from flask import Flask, request, jsonify, make_response
import redis
import json
import uuid
from datetime import timedelta
import os

app = Flask(__name__)

# Redis接続設定
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

SESSION_TIME = timedelta(minutes=30)

def get_session_id():
    return request.cookies.get('session_id')

def create_session():
    session_id = str(uuid.uuid4())
    return session_id

@app.route('/login', methods=['POST'])
def login():
    user_data = request.json
    if not user_data or 'username' not in user_data:
        return jsonify({"error": "Username is required"}), 400

    session_id = create_session()
    session_key = f"session:{session_id}"
    
    session_data = {
        "username": user_data['username'],
        "role": "user"
    }
    
    redis_client.setex(session_key, SESSION_TIME, json.dumps(session_data))
    
    response = make_response(jsonify({"message": "Login successful", "session_id": session_id}))
    response.set_cookie('session_id', session_id, httponly=True, max_age=SESSION_TIME.total_seconds(), secure=False, samesite='Lax', path='/')
    
    return response

@app.route('/me', methods=['GET'])
def me():
    session_id = get_session_id()
    if not session_id:
        return jsonify({"error": "Not authenticated"}), 401
        
    session_key = f"session:{session_id}"
    session_data_json = redis_client.get(session_key)
    
    if not session_data_json:
        return jsonify({"error": "Session not found or expired"}), 401
        
    # セッションの有効期限を延長
    redis_client.expire(session_key, SESSION_TIME)
    
    session_data = json.loads(session_data_json)
    return jsonify(session_data)

@app.route('/logout', methods=['POST'])
def logout():
    session_id = get_session_id()
    if session_id:
        session_key = f"session:{session_id}"
        redis_client.delete(session_key)
        
    response = make_response(jsonify({"message": "Logout successful"}))
    response.delete_cookie('session_id')
    
    return response

@app.route('/health', methods=['GET'])
def health():
    try:
        redis_client.ping()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
