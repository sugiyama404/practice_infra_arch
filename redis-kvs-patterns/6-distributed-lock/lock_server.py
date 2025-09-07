import time
import threading
from flask import Flask, request, jsonify
from redlock import Redlock
import redis
from collections import deque, defaultdict

app = Flask(__name__)

# Redisノード構成
NODES = [
    {'host': 'localhost', 'port': 6379},
    {'host': 'localhost', 'port': 6380},
    {'host': 'localhost', 'port': 6381}
]
redlock = Redlock([{'host': n['host'], 'port': n['port']} for n in NODES])

# ロック待機キュー・統計
lock_queues = defaultdict(deque)  # key -> queue of requestors
lock_stats = defaultdict(lambda: {'acquired': 0, 'released': 0, 'deadlocks': 0})
active_locks = {}  # key -> {'lock': lock, 'owner': owner, 'expires': ts}
heartbeats = {}  # owner -> last heartbeat
LEASE_TTL = 5000  # ms
HEARTBEAT_INTERVAL = 2  # sec

@app.route('/acquire', methods=['POST'])
def acquire():
    key = request.json.get('key')
    owner = request.json.get('owner')
    # 待機キュー管理
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
    owner = request.json.get('owner')
    heartbeats[owner] = time.time()
    return jsonify({'status': 'heartbeat', 'owner': owner})

@app.route('/stats', methods=['GET'])
def stats():
    return jsonify({'stats': lock_stats, 'active_locks': list(active_locks.keys())})

# デッドロック検出・自動解除・障害ノード対応

def lock_monitor():
    while True:
        now = time.time()
        for key, info in list(active_locks.items()):
            # TTL切れ
            if now > info['expires']:
                redlock.unlock(info['lock'])
                lock_stats[key]['released'] += 1
                lock_queues[key].popleft()
                active_locks.pop(key)
            # ハートビート切れ
            owner = info['owner']
            if owner in heartbeats and now - heartbeats[owner] > HEARTBEAT_INTERVAL * 3:
                redlock.unlock(info['lock'])
                lock_stats[key]['released'] += 1
                lock_queues[key].popleft()
                active_locks.pop(key)
        time.sleep(1)

threading.Thread(target=lock_monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
