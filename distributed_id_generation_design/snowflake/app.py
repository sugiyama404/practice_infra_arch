from flask import Flask
from flask import jsonify
import time
import threading

app = Flask(__name__)

# Snowflakeパラメータ（簡易版）
EPOCH = 1609459200000  # 2021-01-01
machine_id = 1

sequence = 0
last_timestamp = -1
lock = threading.Lock()

def current_millis():
    return int(time.time() * 1000)

def next_id():
    global sequence, last_timestamp
    with lock:
        timestamp = current_millis()
        if timestamp == last_timestamp:
            sequence += 1
        else:
            sequence = 0
            last_timestamp = timestamp
        id = ((timestamp - EPOCH) << 22) | (machine_id << 12) | sequence
        return id

@app.route("/generate", methods=["GET"])
def generate_id():
    id = next_id()
    return jsonify({"id": id})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
