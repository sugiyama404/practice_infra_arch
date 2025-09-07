from flask import Flask, request, jsonify, make_response
import redis
import json
import uuid
from datetime import timedelta

app = Flask(__name__)
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
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
    response.set_cookie('session_id', session_id, httponly=True, max_age=SESSION_TIME.total_seconds())
    
    return response

@app.route('/me')
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
