import time
import threading
from flask import Flask, request, jsonify
from redlock import Redlock
import redis
from collections import deque, defaultdict
import os

app = Flask(__name__)

# Redis nodes configuration
def get_redis_nodes():
    # Get Redis nodes from environment
    nodes_str = os.environ.get("REDIS_NODES", "localhost:6379,localhost:6380,localhost:6381")
    nodes = []
    for node_addr in nodes_str.split(','):
        host, port = node_addr.split(':')
        nodes.append({'host': host, 'port': int(port)})
    return nodes

NODES = get_redis_nodes()
redlock = Redlock([{'host': n['host'], 'port': n['port']} for n in NODES])

# Lock waiting queue and statistics
lock_queues = defaultdict(deque)  # key -> queue of requestors
lock_stats = defaultdict(lambda: {'acquired': 0, 'released': 0, 'deadlocks': 0})
active_locks = {}  # key -> {'lock': lock, 'owner': owner, 'expires': ts}
heartbeats = {}  # owner -> last heartbeat
LEASE_TTL = 5000  # ms
HEARTBEAT_INTERVAL = 2  # sec

@app.route('/acquire', methods=['POST'])
def acquire():
    # Acquire a distributed lock
    key = request.json.get('key')
    owner = request.json.get('owner')
    # Manage waiting queue
    lock_queues[key].append(owner)
    if lock_queues[key][0] != owner:
        return jsonify({'status': 'waiting', 'queue': list(lock_queues[key])})
    lock = redlock.lock(key, LEASE_TTL)
    if lock:
        active_locks[key] = {'lock': lock, 'owner': owner, 'expires': time.time() + LEASE_TTL/1000}
        lock_stats[key]['acquired'] += 1
        return jsonify({'status': 'acquired', 'key': key, 'owner': owner})
    else:
        lock_stats[key]['deadlocks'] += 1
        return jsonify({'status': 'failed', 'reason': 'deadlock or unavailable'})

@app.route('/release', methods=['POST'])
def release():
    # Release the lock
    key = request.json.get('key')
    owner = request.json.get('owner')
    info = active_locks.get(key)
    if info and info['owner'] == owner:
        redlock.unlock(info['lock'])
        lock_stats[key]['released'] += 1
        lock_queues[key].popleft()
        active_locks.pop(key)
        return jsonify({'status': 'released', 'key': key})
    return jsonify({'status': 'not_owner'}), 400

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    # Send heartbeat to keep lock alive
    owner = request.json.get('owner')
    heartbeats[owner] = time.time()
    return jsonify({'status': 'heartbeat', 'owner': owner})

@app.route('/health', methods=['GET'])
def health():
    # Simple health check
    return jsonify({'status': 'ok'}), 200

@app.route('/stats', methods=['GET'])
def stats():
    # Get lock statistics
    return jsonify({'stats': lock_stats, 'active_locks': list(active_locks.keys())})

# Deadlock detection, auto-release, failure handling

def lock_monitor():
    # Monitor locks and handle expirations
    while True:
        now = time.time()
        for key, info in list(active_locks.items()):
            # Expire locks
            if now > info['expires']:
                redlock.unlock(info['lock'])
                lock_stats[key]['released'] += 1
                lock_queues[key].popleft()
                active_locks.pop(key)
            # Expire heartbeats
            owner = info['owner']
            if owner in heartbeats and now - heartbeats[owner] > HEARTBEAT_INTERVAL * 3:
                redlock.unlock(info['lock'])
                lock_stats[key]['released'] += 1
                lock_queues[key].popleft()
                active_locks.pop(key)
        time.sleep(1)

threading.Thread(target=lock_monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
