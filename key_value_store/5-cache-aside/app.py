from flask import Flask, request, jsonify
import redis
import json
import time
import hashlib
from datetime import datetime, timedelta
import os
import psycopg2


class CacheAsideKVS:
    def __init__(self, redis_host="redis", redis_port=6379, db_host="db", db_port=5432):
        self.redis_client = redis.Redis(
            host=redis_host, port=redis_port, decode_responses=True
        )
        self.db_conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=os.environ.get("POSTGRES_DB", "cache_aside_db"),
            user=os.environ.get("POSTGRES_USER", "postgres"),
            password=os.environ.get("POSTGRES_PASSWORD", "password"),
        )
        self.cache_stats = {"hits": 0, "misses": 0}
        self._init_db()

    def _init_db(self):
        with self.db_conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_data (
                    entity_type VARCHAR(50),
                    entity_id VARCHAR(100),
                    data JSONB,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (entity_type, entity_id)
                )
            """)
            self.db_conn.commit()

    def get(self, entity_type, entity_id):
        cache_key = f"cache:{entity_type}:{entity_id}"

        # Cache Hit チェック
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            self.cache_stats["hits"] += 1
            return {
                "data": json.loads(cached_data),
                "source": "cache",
                "timestamp": datetime.now().isoformat(),
            }

        # Cache Miss - DBから取得
        self.cache_stats["misses"] += 1
        db_data = self._db_read(entity_type, entity_id)
        if db_data is None:
            return {
                "data": None,
                "source": "database",
                "timestamp": datetime.now().isoformat(),
            }

        # キャッシュに保存 (TTL: 300秒)
        self.redis_client.setex(cache_key, 300, json.dumps(db_data))

        return {
            "data": db_data,
            "source": "database",
            "timestamp": datetime.now().isoformat(),
        }

    def set(self, entity_type, entity_id, data):
        # Write-Through: DBとキャッシュ両方に書き込み
        cache_key = f"cache:{entity_type}:{entity_id}"

        # DB書き込み
        self._db_write(entity_type, entity_id, data)

        # キャッシュ更新
        self.redis_client.setex(cache_key, 300, json.dumps(data))

        return {"status": "success", "cache_updated": True}

    def invalidate(self, entity_type, entity_id=None):
        if entity_id:
            # 特定エンティティのキャッシュ削除
            cache_key = f"cache:{entity_type}:{entity_id}"
            self.redis_client.delete(cache_key)
            return {"invalidated": cache_key}
        else:
            # エンティティタイプ全体のキャッシュ削除
            pattern = f"cache:{entity_type}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            return {"invalidated_count": len(keys)}

    def get_stats(self):
        total = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_ratio = (self.cache_stats["hits"] / total * 100) if total > 0 else 0

        return {
            "cache_hits": self.cache_stats["hits"],
            "cache_misses": self.cache_stats["misses"],
            "hit_ratio": round(hit_ratio, 2),
            "cache_size": self.redis_client.dbsize(),
        }

    def _db_read(self, entity_type, entity_id):
        with self.db_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT data, updated_at FROM cache_data
                WHERE entity_type = %s AND entity_id = %s
            """,
                (entity_type, entity_id),
            )
            result = cursor.fetchone()

            if result:
                data, updated_at = result
                return {
                    "id": entity_id,
                    "type": entity_type,
                    "data": data,
                    "updated_at": updated_at.isoformat(),
                }
            else:
                return None  # Return None if not found in DB

    def _db_write(self, entity_type, entity_id, data):
        with self.db_conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO cache_data (entity_type, entity_id, data, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (entity_type, entity_id)
                DO UPDATE SET data = EXCLUDED.data, updated_at = CURRENT_TIMESTAMP
            """,
                (entity_type, entity_id, json.dumps(data)),
            )
            self.db_conn.commit()
        return True


app = Flask(__name__)
cache_kvs = CacheAsideKVS()


@app.route("/get/<entity_type>/<entity_id>")
def get_cached_data(entity_type, entity_id):
    result = cache_kvs.get(entity_type, entity_id)
    return jsonify(result)


@app.route("/set/<entity_type>/<entity_id>", methods=["POST"])
def set_cached_data(entity_type, entity_id):
    data = request.json
    result = cache_kvs.set(entity_type, entity_id, data)
    return jsonify(result)


@app.route("/invalidate/<entity_type>")
@app.route("/invalidate/<entity_type>/<entity_id>")
def invalidate_cache(entity_type, entity_id=None):
    result = cache_kvs.invalidate(entity_type, entity_id)
    return jsonify(result)


@app.route("/stats")
def get_cache_stats():
    return jsonify(cache_kvs.get_stats())


@app.route("/health", methods=["GET"])
def health():
    try:
        # Check Redis connection
        cache_kvs.redis_client.ping()
        # Check DB connection
        cache_kvs.db_conn.cursor().execute("SELECT 1")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, reload=True)
