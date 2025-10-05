import os
import time
from flask import Flask, request, jsonify
import redis

app = Flask(__name__)

# 環境変数からRedis接続情報を取得
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
RATE_LIMIT = int(os.getenv("RATE_LIMIT", 5))
WINDOW_SECONDS = int(os.getenv("WINDOW_SECONDS", 60))

# Redis接続
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def get_client_ip():
    """クライアントIPアドレスを取得"""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0]
    return request.remote_addr


def check_rate_limit(client_ip):
    """
    スライディングウィンドウログ方式でレート制限をチェック

    Args:
        client_ip: クライアントのIPアドレス

    Returns:
        tuple: (is_allowed, remaining, reset_time)
    """
    current_time = time.time()
    window_start_timestamp = current_time - WINDOW_SECONDS

    # Redisキー: rate_limit:{client_ip}
    key = f"rate_limit:{client_ip}"

    try:
        with redis_client.pipeline() as pipe:
            # 1. ウィンドウ外の古いタイムスタンプを削除
            pipe.zremrangebyscore(key, 0, window_start_timestamp)

            # 2. 現在のリクエストのタイムスタンプを追加
            #    ユニークなメンバーにするため、タイムスタンプとナノ秒を組み合わせる
            pipe.zadd(key, {f"{current_time}": current_time})

            # 3. 現在のウィンドウ内のリクエスト数を取得
            pipe.zcard(key)

            # 4. キーにTTLを設定して自動クリーンアップ
            pipe.expire(key, WINDOW_SECONDS)

            # トランザクション実行
            results = pipe.execute()

        current_count = results[2]

        # 残りリクエスト数を計算
        remaining = max(0, RATE_LIMIT - current_count)

        # 次のリセットは常に1秒後（最も古いリクエストがウィンドウから外れるため）
        reset_time = int(current_time + 1)

        # レート制限チェック
        is_allowed = current_count <= RATE_LIMIT

        return is_allowed, remaining, reset_time

    except redis.RedisError as e:
        app.logger.error(f"Redis error: {e}")
        # Redisエラー時は通過させる（フェイルオープン）
        return True, RATE_LIMIT, int(current_time + WINDOW_SECONDS)


@app.before_request
def rate_limit_check():
    """全リクエスト前にレート制限をチェック"""
    # ヘルスチェックエンドポイントは除外
    if request.path == "/health":
        return None

    client_ip = get_client_ip()
    is_allowed, remaining, reset_time = check_rate_limit(client_ip)

    # レスポンスヘッダを設定するための情報を保存
    request.rate_limit_info = {
        "limit": RATE_LIMIT,
        "remaining": remaining,
        "reset": reset_time,
    }

    if not is_allowed:
        response = jsonify(
            {
                "error": "Too Many Requests",
                "message": f"Rate limit exceeded. Try again in {reset_time - int(time.time())} seconds.",
            }
        )
        response.status_code = 429
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        response.headers["Retry-After"] = str(reset_time - int(time.time()))
        return response


@app.after_request
def add_rate_limit_headers(response):
    """レスポンスヘッダにレート制限情報を追加"""
    if hasattr(request, "rate_limit_info"):
        info = request.rate_limit_info
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
    return response


@app.route("/health", methods=["GET"])
def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        redis_client.ping()
        return jsonify({"status": "healthy", "redis": "connected"}), 200
    except redis.RedisError:
        return jsonify({"status": "unhealthy", "redis": "disconnected"}), 503


@app.route("/api/test", methods=["GET"])
def test_endpoint():
    """テスト用APIエンドポイント"""
    client_ip = get_client_ip()
    return jsonify(
        {
            "message": "Request successful",
            "client_ip": client_ip,
            "timestamp": int(time.time()),
        }
    ), 200


@app.route("/api/reset", methods=["POST"])
def reset_rate_limit():
    """レート制限をリセット（テスト用）"""
    client_ip = get_client_ip()
    pattern = f"rate_limit:{client_ip}:*"

    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            return jsonify(
                {"message": "Rate limit reset successfully", "deleted_keys": len(keys)}
            ), 200
        else:
            return jsonify({"message": "No rate limit data found"}), 200
    except redis.RedisError as e:
        return jsonify({"error": "Failed to reset rate limit", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
