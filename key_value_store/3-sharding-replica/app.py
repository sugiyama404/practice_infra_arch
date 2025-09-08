import redis
import threading
import time
from flask import Flask, request, jsonify
from hash_ring import HashRing
from typing import Dict, List

app = Flask(__name__)

# Consistent hashing with virtual nodes
class ShardNode:
    """Node with master-slave replication."""
    def __init__(self, name, master_port, slave_port):
        self.name = name
        self.master = redis.Redis(host='localhost', port=master_port, decode_responses=True)
        self.slave = redis.Redis(host='localhost', port=slave_port, decode_responses=True)
        self.alive = True
    def is_alive(self):
        try:
            return self.master.ping() and self.slave.ping()
        except Exception:
            return False

NODES = [
    {'name': 'node1', 'master': 6379, 'slave': 6389},
    {'name': 'node2', 'master': 6380, 'slave': 6390},
    {'name': 'node3', 'master': 6381, 'slave': 6391}
]

nodes = {n['name']: ShardNode(n['name'], n['master'], n['slave']) for n in NODES}
ring = HashRing(list(nodes.keys()), replicas=100)  # Virtual nodes to reduce hotspots

# Dynamic node addition/removal
@app.route('/add_node', methods=['POST'])
def add_node():
    # Add a new node to the ring
    name = request.json.get('name')
    master = request.json.get('master')
    slave = request.json.get('slave')
    nodes[name] = ShardNode(name, master, slave)
    ring.nodes.append(name)
    ring._sorted_keys = sorted([ring.gen_key(n) for n in ring.nodes])
    return jsonify({'status': 'added', 'nodes': ring.nodes})

@app.route('/remove_node', methods=['POST'])
def remove_node():
    # Remove a node from the ring
    name = request.json.get('name')
    if name in nodes:
        del nodes[name]
        ring.nodes.remove(name)
        ring._sorted_keys = sorted([ring.gen_key(n) for n in ring.nodes])
    return jsonify({'status': 'removed', 'nodes': ring.nodes})

# Rebalancing data
@app.route('/rebalance', methods=['POST'])
def rebalance():
    # Simple rebalance: redistribute all keys
    all_keys = []
    for n in nodes.values():
        all_keys += n.master.keys()
    for key in all_keys:
        target = ring.get_node(key)
        value = nodes[target].master.get(key)
        for n in nodes.values():
            if n.name != target:
                n.master.delete(key)
        nodes[target].master.set(key, value)
    return jsonify({'status': 'rebalanced'})

# Read-write separation
@app.route('/write', methods=['POST'])
def write():
    # Write to master
    key = request.json.get('key')
    value = request.json.get('value')
    target = ring.get_node(key)
    node = nodes[target]
    if not node.is_alive():
        return jsonify({'error': 'Node unavailable'}), 500
    node.master.set(key, value)
    node.slave.set(key, value)  # Replicate to slave
    return jsonify({'status': 'ok', 'node': target})

@app.route('/read', methods=['GET'])
def read():
    # Read from slave
    key = request.args.get('key')
    target = ring.get_node(key)
    node = nodes[target]
    if not node.is_alive():
        return jsonify({'error': 'Node unavailable'}), 500
    value = node.slave.get(key)
    return jsonify({'value': value, 'node': target})

# Automatic failure detection and failover
@app.route('/status', methods=['GET'])
def status():
    # Get health status of nodes
    health = {n: nodes[n].is_alive() for n in nodes}
    return jsonify({'nodes': health})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
