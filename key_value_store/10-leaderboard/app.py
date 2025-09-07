from flask import Flask, request, jsonify
import redis

app = Flask(__name__)
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
LEADERBOARD_KEY = "leaderboard:global"

@app.route('/score', methods=['POST'])
def update_score():
    data = request.json
    user_id = data.get('user_id')
    score = data.get('score')
    
    if not user_id or score is None:
        return jsonify({"error": "user_id and score are required"}), 400
        
    # Sorted Setにスコアを追加
    redis_client.zadd(LEADERBOARD_KEY, {user_id: float(score)})
    
    return jsonify({"message": f"Score updated for {user_id}"})

@app.route('/top/<int:n>')
def get_top_n(n):
    # スコアが高い順に取得 (withscores=Trueでスコアも取得)
    top_users = redis_client.zrevrange(LEADERBOARD_KEY, 0, n-1, withscores=True)
    
    result = [{"user_id": user, "score": score} for user, score in top_users]
    return jsonify(result)

@app.route('/rank/<user_id>')
def get_rank(user_id):
    # 0-basedのランクを取得
    rank = redis_client.zrevrank(LEADERBOARD_KEY, user_id)
    
    if rank is None:
        return jsonify({"error": "User not found in leaderboard"}), 404
        
    score = redis_client.zscore(LEADERBOARD_KEY, user_id)
    
    return jsonify({"user_id": user_id, "rank": rank + 1, "score": score})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
