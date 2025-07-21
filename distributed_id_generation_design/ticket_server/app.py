from flask import Flask, jsonify
import threading

app = Flask(__name__)
counter = 100000
lock = threading.Lock()

@app.route("/generate", methods=["GET"])
def generate_id():
    global counter
    with lock:
        counter += 1
        return jsonify({"id": counter})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
