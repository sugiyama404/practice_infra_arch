from flask import Flask, request, jsonify
from node_ring import CoordinatorRing
import threading
import time

app = Flask(__name__)
node_ports = {
    "node1": 6379,
    "node2": 6380,
    "node3": 6381
}
ring = CoordinatorRing(node_ports)
ring.start_health_thread()

@app.route("/write", methods=["POST"])
def write():
    key = request.json.get("key")
    value = request.json.get("value")
    try:
        ring.write(key, value)
        return jsonify({"status": "ok", "leader": ring.leader, "vector_clock": ring.vector_clock(ring.leader)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/read", methods=["GET"])
def read():
    key = request.args.get("key")
    try:
        value, vc = ring.read(key)
        return jsonify({"value": value, "vector_clock": vc, "leader": ring.leader}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    status = {n: ring.nodes[n].alive for n in ring.ring}
    return jsonify({"nodes": status, "leader": ring.leader}), 200

@app.route("/exclude_failed", methods=["POST"])
def exclude_failed():
    ring.exclude_failed_nodes()
    return jsonify({"ring": ring.ring}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
