import time
import requests
import json
import os

data_dir = os.path.join(os.path.dirname(__file__), '../data')
os.makedirs(data_dir, exist_ok=True)

# 各パターンAPIエンドポイント例
ENDPOINTS = {
    'coordinator_ring': 'http://localhost:5000/health',
    'gmail_pubsub': 'http://localhost:5000/stats',
    'line_streams': 'http://localhost:5000/stream_info',
    'quorum_consistency': 'http://localhost:5000/status',
    'sharding_replica': 'http://localhost:5000/status',
    'distributed_lock': 'http://localhost:5000/stats',
    'bloom_sstable': 'http://localhost:5000/stats'
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
