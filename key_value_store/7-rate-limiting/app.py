from flask import Flask, request, jsonify
import redis
import time
import os

app = Flask(__name__)

# Redis接続設定
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# 固定ウィンドウカウンタアルゴリズム
def is_rate_limited_fixed_window(user_id, limit=10, window=60):
    key = f"rate_limit:fixed:{user_id}"
    
    current_requests = redis_client.get(key)
    
    if current_requests is None:
        redis_client.setex(key, window, 1)
        return False
        
    if int(current_requests) >= limit:
        return True
        
    redis_client.incr(key)
    return False

# スライディングウィンドウログアルゴリズム
def is_rate_limited_sliding_window(user_id, limit=10, window=60):
    key = f"rate_limit:sliding:{user_id}"
    now = time.time()
    
    # トランザクション開始
    pipe = redis_client.pipeline()
    
    # 古いリクエストを削除
    pipe.zremrangebyscore(key, 0, now - window)
    # 新しいリクエストを追加
    pipe.zadd(key, {now: now})
    # 現在のウィンドウ内のリクエスト数を取得
    pipe.zcard(key)
    # ウィンドウの有効期限を設定
    pipe.expire(key, window)
    
    # トランザクション実行
    results = pipe.execute()
    request_count = results[2]
    
    return request_count > limit

@app.route('/limited_fixed')
def limited_fixed():
    user_id = request.args.get('user_id', 'default_user')
    if is_rate_limited_fixed_window(user_id):
        return jsonify({"error": "Rate limit exceeded"}), 429
    return jsonify({"message": "Request successful"})

@app.route('/limited_sliding')
def limited_sliding():
    user_id = request.args.get('user_id', 'default_user')
    if is_rate_limited_sliding_window(user_id):
        return jsonify({"error": "Rate limit exceeded"}), 429
    return jsonify({"message": "Request successful"})

@app.route('/health', methods=['GET'])
def health():
    try:
        redis_client.ping()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
