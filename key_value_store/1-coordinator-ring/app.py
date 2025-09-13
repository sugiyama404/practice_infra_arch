from flask import Flask, request, jsonify
from node_ring import CoordinatorRing
import threading
import time
import os

app = Flask(__name__)

def get_node_configs():
    # Retrieve Redis node configurations from environment variables
    redis_nodes_str = os.environ.get("REDIS_NODES", "localhost:6379,localhost:6380,localhost:6381")
    node_configs = {}
    for i, node_addr in enumerate(redis_nodes_str.split(',')):
        host, port = node_addr.split(':')
        node_name = f"node{i+1}"
        node_configs[node_name] = {"host": host, "port": int(port)}
    return node_configs

node_configs = get_node_configs()
ring = CoordinatorRing(node_configs)
ring.start_health_thread()

@app.route("/write", methods=["POST"])
def write():
    # Write key-value pair using the coordinator ring
    key = request.json.get("key")
    value = request.json.get("value")
    try:
        ring.write(key, value)
        return jsonify({"status": "ok", "leader": ring.leader, "vector_clock": ring.vector_clock(ring.leader)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/read", methods=["GET"])
def read():
    # Read value for the given key using the coordinator ring
    key = request.args.get("key")
    try:
        value, vc = ring.read(key)
        return jsonify({"value": value, "vector_clock": vc, "leader": ring.leader}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    # Get health status of all nodes
    status = {n: ring.nodes[n].alive for n in ring.ring}
    return jsonify({"nodes": status, "leader": ring.leader}), 200

@app.route("/exclude_failed", methods=["POST"])
def exclude_failed():
    # Exclude failed nodes from the ring
    ring.exclude_failed_nodes()
    return jsonify({"ring": ring.ring}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
