import redis
import threading
import time
from flask import Flask, request, jsonify
import hashlib
from typing import Dict, List
import os

app = Flask(__name__)


class HashRing:
    def __init__(self, nodes, replicas=100):
        self.nodes = nodes
        self.replicas = replicas
        self.ring = {}
        for node in nodes:
            for i in range(replicas):
                key = self.gen_key(f"{node}:{i}")
                self.ring[key] = node
        self.sorted_keys = sorted(self.ring.keys())

    def gen_key(self, key):
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def get_node(self, key):
        if not self.ring:
            return None
        hash_key = self.gen_key(key)
        for ring_key in self.sorted_keys:
            if hash_key <= ring_key:
                return self.ring[ring_key]
        return self.ring[self.sorted_keys[0]]

    def add_node(self, node):
        self.nodes.append(node)
        for i in range(self.replicas):
            key = self.gen_key(f"{node}:{i}")
            self.ring[key] = node
        self.sorted_keys = sorted(self.ring.keys())

    def remove_node(self, node):
        if node in self.nodes:
            self.nodes.remove(node)
            keys_to_remove = [k for k, v in self.ring.items() if v == node]
            for k in keys_to_remove:
                del self.ring[k]
            self.sorted_keys = sorted(self.ring.keys())


# Consistent hashing with virtual nodes
class ShardNode:
    """Node with master-slave replication."""

    def __init__(self, name, host, master_port, slave_port):
        self.name = name
        self.master = redis.Redis(host=host, port=master_port, decode_responses=True)
        self.slave = redis.Redis(host=host, port=slave_port, decode_responses=True)
        self.alive = True

    def is_alive(self):
        try:
            return self.master.ping()
        except Exception:
            return False


def get_redis_nodes():
    redis_nodes_str = os.environ.get(
        "REDIS_NODES", "redis-node1:6379,redis-node2:6379,redis-node3:6379"
    )
    nodes = []
    for node_addr in redis_nodes_str.split(","):
        host, port = node_addr.split(":")
        nodes.append(
            {
                "name": f"node{len(nodes) + 1}",
                "host": host,
                "master_port": int(port),
                "slave_port": int(port),
            }
        )
    return nodes


NODES = get_redis_nodes()
nodes = {
    n["name"]: ShardNode(n["name"], n["host"], n["master_port"], n["slave_port"])
    for n in NODES
}
ring = HashRing(list(nodes.keys()), replicas=100)  # Virtual nodes to reduce hotspots


# Dynamic node addition/removal
@app.route("/add_node", methods=["POST"])
def add_node():
    # Add a new node to the ring
    name = request.json.get("name")
    master = request.json.get("master")
    slave = request.json.get("slave")
    nodes[name] = ShardNode(name, master, slave)
    ring.add_node(name)
    return jsonify({"status": "added", "nodes": list(ring.nodes)})


@app.route("/remove_node", methods=["POST"])
def remove_node():
    # Remove a node from the ring
    name = request.json.get("name")
    if name in nodes:
        del nodes[name]
        ring.remove_node(name)
    return jsonify({"status": "removed", "nodes": list(ring.nodes)})


# Rebalancing data
@app.route("/rebalance", methods=["POST"])
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
    return jsonify({"status": "rebalanced"})


# Read-write separation
@app.route("/write", methods=["POST"])
def write():
    # Write to master
    key = request.json.get("key")
    value = request.json.get("value")
    target = ring.get_node(key)
    node = nodes[target]
    if not node.is_alive():
        return jsonify({"error": "Node unavailable"}), 500
    node.master.set(key, value)
    node.slave.set(key, value)  # Replicate to slave
    return jsonify({"status": "ok", "node": target})


@app.route("/read", methods=["GET"])
def read():
    # Read from slave
    key = request.args.get("key")
    target = ring.get_node(key)
    node = nodes[target]
    if not node.is_alive():
        return jsonify({"error": "Node unavailable"}), 500
    value = node.slave.get(key)
    return jsonify({"value": value, "node": target})


# Automatic failure detection and failover
@app.route("/health", methods=["GET"])
def health():
    # Get health status of nodes
    health_status = {n: nodes[n].is_alive() for n in nodes}
    all_alive = all(health_status.values())

    if all_alive:
        return jsonify({"status": "ok", "nodes": health_status}), 200
    else:
        return jsonify({"status": "error", "nodes": health_status}), 503
    return jsonify({"nodes": health})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, reload=True)
