from flask import Flask, request, jsonify
import redis
import json
import time
import hashlib
from datetime import datetime, timedelta

class CacheAsideKVS:
    def __init__(self, redis_host='redis', redis_port=6379):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.cache_stats = {'hits': 0, 'misses': 0}
        
    def get(self, entity_type, entity_id):
        cache_key = f"cache:{entity_type}:{entity_id}"
        
        # Cache Hit チェック
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            self.cache_stats['hits'] += 1
            return {
                'data': json.loads(cached_data),
                'source': 'cache',
                'timestamp': datetime.now().isoformat()
            }
        
        # Cache Miss - DBから取得（シミュレーション）
        self.cache_stats['misses'] += 1
        db_data = self._simulate_db_read(entity_type, entity_id)
        
        # キャッシュに保存 (TTL: 300秒)
        self.redis_client.setex(cache_key, 300, json.dumps(db_data))
        
        return {
            'data': db_data,
            'source': 'database',
            'timestamp': datetime.now().isoformat()
        }
    
    def set(self, entity_type, entity_id, data):
        # Write-Through: DBとキャッシュ両方に書き込み
        cache_key = f"cache:{entity_type}:{entity_id}"
        
        # DB書き込み（シミュレーション）
        self._simulate_db_write(entity_type, entity_id, data)
        
        # キャッシュ更新
        self.redis_client.setex(cache_key, 300, json.dumps(data))
        
        return {'status': 'success', 'cache_updated': True}
    
    def invalidate(self, entity_type, entity_id=None):
        if entity_id:
            # 特定エンティティのキャッシュ削除
            cache_key = f"cache:{entity_type}:{entity_id}"
            self.redis_client.delete(cache_key)
            return {'invalidated': cache_key}
        else:
            # エンティティタイプ全体のキャッシュ削除
            pattern = f"cache:{entity_type}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            return {'invalidated_count': len(keys)}
    
    def get_stats(self):
        total = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_ratio = (self.cache_stats['hits'] / total * 100) if total > 0 else 0
        
        return {
            'cache_hits': self.cache_stats['hits'],
            'cache_misses': self.cache_stats['misses'],
            'hit_ratio': round(hit_ratio, 2),
            'cache_size': self.redis_client.dbsize()
        }
    
    def _simulate_db_read(self, entity_type, entity_id):
        # DB読み取りレイテンシをシミュレート
        time.sleep(0.1)  # 100ms delay
        
        return {
            'id': entity_id,
            'type': entity_type,
            'data': f'Database data for {entity_type}:{entity_id}',
            'updated_at': (datetime.now() - timedelta(minutes=5)).isoformat()
        }
    
    def _simulate_db_write(self, entity_type, entity_id, data):
        # DB書き込みレイテンシをシミュレート
        time.sleep(0.05)  # 50ms delay
        return True

app = Flask(__name__)
cache_kvs = CacheAsideKVS()

@app.route('/get/<entity_type>/<entity_id>')
def get_cached_data(entity_type, entity_id):
    result = cache_kvs.get(entity_type, entity_id)
    return jsonify(result)

@app.route('/set/<entity_type>/<entity_id>', methods=['POST'])
def set_cached_data(entity_type, entity_id):
    data = request.json
    result = cache_kvs.set(entity_type, entity_id, data)
    return jsonify(result)

@app.route('/invalidate/<entity_type>')
@app.route('/invalidate/<entity_type>/<entity_id>')
def invalidate_cache(entity_type, entity_id=None):
    result = cache_kvs.invalidate(entity_type, entity_id)
    return jsonify(result)

@app.route('/stats')
def get_cache_stats():
    return jsonify(cache_kvs.get_stats())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
