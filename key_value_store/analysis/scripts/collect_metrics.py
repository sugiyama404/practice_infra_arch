import time
import requests
import json
import os

data_dir = os.path.join(os.path.dirname(__file__), '../data')
os.makedirs(data_dir, exist_ok=True)

# 各パターンAPIエンドポイント例
ENDPOINTS = {
    'coordinator_ring': 'http://localhost:8000/health',
    'quorum_consistency': 'http://localhost:8000/read?key=health_check',
    'sharding_replica': 'http://localhost:5000/status',
    'distributed_lock': 'http://localhost:8000/stats',
    'cache_aside': 'http://localhost:8000/stats',
    'bloom_sstable': 'http://localhost:5000/stats',
    'rate_limiting': 'http://localhost:8000/check_rate',
    'line_streams': 'http://localhost:8000/stream_info',
    'session_store': 'http://localhost:8000/stats',
    'leaderboard': 'http://localhost:8000/top/10'
}

RESULTS = {}

for name, url in ENDPOINTS.items():
    start = time.time()
    try:
        resp = requests.get(url, timeout=3)
        latency = time.time() - start
        RESULTS[name] = {
            'latency': latency,
            'status_code': resp.status_code,
            'data': resp.json()
        }
    except Exception as e:
        RESULTS[name] = {'error': str(e)}

with open(os.path.join(data_dir, 'metrics.json'), 'w') as f:
    json.dump(RESULTS, f, indent=2)

print('Metrics collected:', RESULTS)
