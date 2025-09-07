import redis
import threading
import time
from flask import Flask, request, jsonify
from merklelib import MerkleTree
from typing import Dict, List
import os
import json

app = Flask(__name__)

def get_node_configs():
    redis_nodes_str = os.environ.get("REDIS_NODES", "localhost:6379,localhost:6380,localhost:6381")
    node_configs = []
    for node_addr in redis_nodes_str.split(','):
        host, port = node_addr.split(':')
        node_configs.append({"host": host, "port": int(port)})
    return node_configs

NODE_CONFIGS = get_node_configs()
NODES = [config['port'] for config in NODE_CONFIGS]
W = 2
R = 2


class VectorClock:
    def __init__(self, nodes):
        self.clock = {n: 0 for n in nodes}
    def increment(self, node):
        self.clock[node] += 1
    def update(self, other):
        for n, v in other.items():
            self.clock[n] = max(self.clock.get(n, 0), v)
    def get(self):
        return self.clock.copy()
    def __str__(self):
        return str(self.clock)

class KVSNode:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.redis = redis.Redis(host=self.host, port=self.port, decode_responses=True)
        self.vc = VectorClock(NODES)
        self.hinted_handoff = {}
    def is_alive(self):
        try:
            return self.redis.ping()
        except Exception:
            return False
    def set(self, key, value, vc):
        self.redis.set(key, value)
        self.redis.set(f"vc:{key}", str(vc))
    def get(self, key):
        value = self.redis.get(key)
        vc_str = self.redis.get(f"vc:{key}")
        try:
            vc = json.loads(vc_str.replace("'", "\"")) if vc_str else None
        except (json.JSONDecodeError, AttributeError):
            vc = None
        return value, vc
    def store_hinted(self, key, value, vc):
        self.hinted_handoff[key] = (value, vc)
    def flush_hinted(self):
        for key, (value, vc) in self.hinted_handoff.items():
            self.set(key, value, vc)
        self.hinted_handoff.clear()

nodes = [KVSNode(config['host'], config['port']) for config in NODE_CONFIGS]

# Merkle Tree for integrity
class KVSIntegrity:
    def __init__(self):
        self.tree = MerkleTree()
    def update(self, key, value):
        self.tree.append(f"{key}:{value}")
    def verify(self):
        return self.tree.root_hash

integrity = KVSIntegrity()

@app.route('/write', methods=['POST'])
def write():
    key = request.json.get('key')
    value = request.json.get('value')
    alive = [n for n in nodes if n.is_alive()]
    if len(alive) < W:
        return jsonify({'error': 'Quorum not met'}), 500
    # ベクトルクロック更新
    for n in alive[:W]:
        n.vc.increment(n.port)
        n.set(key, value, n.vc.get())
        integrity.update(key, value)
    # 障害ノードへのヒンテッドハンドオフ
    for n in nodes:
        if not n.is_alive():
            n.store_hinted(key, value, n.vc.get())
    return jsonify({'status': 'ok', 'vector_clock': str(alive[0].vc)}), 200

@app.route('/read', methods=['GET'])
def read():
    key = request.args.get('key')
    alive = [n for n in nodes if n.is_alive()]
    if len(alive) < R:
        return jsonify({'error': 'Quorum not met'}), 500
    # Rノードから取得
    results = []
    vcs = []
    for n in alive[:R]:
        value, vc = n.get(key)
        results.append(value)
        vcs.append(vc)
    # ベクトルクロック競合検出
    if len(set(str(vc) for vc in vcs if vc)) > 1:
        # リードリペア: 最新値で全ノード修復
        latest = results[0]
        for n in alive:
            n.set(key, latest, vcs[0])
        return jsonify({'value': latest, 'repair': True, 'vector_clocks': vcs}), 200
    return jsonify({'value': results[0], 'repair': False, 'vector_clocks': vcs}), 200

@app.route('/flush_hinted', methods=['POST'])
def flush_hinted():
    for n in nodes:
        n.flush_hinted()
    return jsonify({'status': 'flushed'}), 200

@app.route('/integrity', methods=['GET'])
def integrity_check():
    return jsonify({'merkle_root': integrity.verify()}), 200

@app.route('/status', methods=['GET'])
def status():
    return jsonify({'nodes': [n.is_alive() for n in nodes]}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
