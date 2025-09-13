import time
import threading
from flask import Flask, request, jsonify
from redlock import RedLock
import os
from collections import deque, defaultdict

app = Flask(__name__)

# Redis nodes configuration
def get_redis_nodes():
    nodes_str = os.environ.get(
        "REDIS_NODES",
        f"{os.environ.get('REDIS_HOST', 'redis')}:{os.environ.get('REDIS_PORT', 6379)}"
    )
    nodes = []
    for node_addr in nodes_str.split(','):
        host, port = node_addr.split(':')
        nodes.append({'host': host, 'port': int(port)})
    return nodes

NODES = get_redis_nodes()

# State
lock_queues = defaultdict(deque)  
lock_stats = defaultdict(lambda: {'acquired': 0, 'released': 0, 'deadlocks': 0})
active_locks = {}  
heartbeats = {}  # (owner, key) -> last ts
LEASE_TTL = 5000  # ms
HEARTBEAT_INTERVAL = 2  # sec
state_lock = threading.Lock()  # global lock for shared structures


@app.route('/acquire', methods=['POST'])
def acquire():
    key = request.json.get('key')
    owner = request.json.get('owner')
    if not key or not owner:
        return jsonify({'status': 'error', 'message': 'key and owner are required'}), 400

    with state_lock:
        lock_queues[key].append(owner)

        if lock_queues[key][0] != owner:
            return jsonify({'status': 'waiting', 'queue': list(lock_queues[key])})

        redlock = RedLock(key, [{'host': n['host'], 'port': n['port']} for n in NODES], ttl=LEASE_TTL)
        if redlock.acquire():
            active_locks[key] = {
                'redlock': redlock,
                'owner': owner,
                'expires': time.time() + LEASE_TTL/1000
            }
            lock_stats[key]['acquired'] += 1
            heartbeats[(owner, key)] = time.time()
            return jsonify({'status': 'acquired', 'key': key, 'owner': owner})
        else:
            lock_stats[key]['deadlocks'] += 1
            # 失敗したら待ち行列を進める
            if lock_queues[key] and lock_queues[key][0] == owner:
                lock_queues[key].popleft()
            return jsonify({'status': 'failed', 'reason': 'deadlock or unavailable'})


@app.route('/release', methods=['POST'])
def release():
    key = request.json.get('key')
    owner = request.json.get('owner')
    if not key or not owner:
        return jsonify({'status': 'error', 'message': 'key and owner are required'}), 400

    with state_lock:
        info = active_locks.get(key)
        if info and info['owner'] == owner:
            try:
                info['redlock'].release()
            except Exception:
                pass
            lock_stats[key]['released'] += 1
            if lock_queues[key]:
                lock_queues[key].popleft()
            active_locks.pop(key, None)
            heartbeats.pop((owner, key), None)
            return jsonify({'status': 'released', 'key': key})
    return jsonify({'status': 'not_owner'}), 400


@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    key = request.json.get('key')
    owner = request.json.get('owner')
    if not key or not owner:
        return jsonify({'status': 'error', 'message': 'key and owner are required'}), 400
    with state_lock:
        heartbeats[(owner, key)] = time.time()
    return jsonify({'status': 'heartbeat', 'owner': owner, 'key': key})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200


@app.route('/stats', methods=['GET'])
def stats():
    with state_lock:
        return jsonify({
            'stats': lock_stats,
            'active_locks': list(active_locks.keys())
        })


def lock_monitor():
    while True:
        now = time.time()
        with state_lock:
            for key, info in list(active_locks.items()):
                owner = info['owner']
                hb_key = (owner, key)
                expired = now > info['expires']
                hb_expired = hb_key in heartbeats and now - heartbeats[hb_key] > HEARTBEAT_INTERVAL * 3

                if expired or hb_expired:
                    try:
                        info['redlock'].release()
                    except Exception:
                        pass
                    lock_stats[key]['released'] += 1
                    if lock_queues[key]:
                        lock_queues[key].popleft()
                    active_locks.pop(key, None)
                    heartbeats.pop(hb_key, None)
        time.sleep(1)


threading.Thread(target=lock_monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
