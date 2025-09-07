import redis
import threading
import time
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Redis connection
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

STREAM_KEY = "line_stream"
GROUP_NAME = "line_consumers"
MAXLEN = 1000  # Stream capacity limit

# Create consumer group
try:
    redis_client.xgroup_create(STREAM_KEY, GROUP_NAME, id='0', mkstream=True)
except redis.exceptions.ResponseError as e:
    if "BUSYGROUP" not in str(e):
        raise

# Message deduplication (in-memory, consider persistence for production)
processed_ids = set()

@app.route('/produce', methods=['POST'])
def produce():
    """Produce a message to the stream."""
    message = request.json.get('message')
    # Trim stream to limit capacity
    msg_id = redis_client.xadd(STREAM_KEY, {'message': message}, maxlen=MAXLEN, approximate=True)
    return jsonify({'id': msg_id})

@app.route('/consume', methods=['POST'])
def consume():
    """Consume messages from the stream."""
    consumer = request.json.get('consumer')
    count = request.json.get('count', 1)
    # Get unprocessed messages
    msgs = redis_client.xreadgroup(GROUP_NAME, consumer, {STREAM_KEY: '>'}, count=count, block=1000)
    results = []
    for stream, messages in msgs:
        for msg_id, fields in messages:
            # Deduplication
            if msg_id in processed_ids:
                continue
            processed_ids.add(msg_id)
            results.append({'id': msg_id, 'message': fields['message']})
            # Acknowledge
            redis_client.xack(STREAM_KEY, GROUP_NAME, msg_id)
    return jsonify({'messages': results})

@app.route('/pending', methods=['GET'])
def pending():
    """Get pending messages."""
    consumer = request.json.get('consumer')
    # Get pending messages
    pending = redis_client.xpending(STREAM_KEY, GROUP_NAME)
    return jsonify({'pending': pending})

@app.route('/replay', methods=['POST'])
def replay():
    """Replay pending messages."""
    consumer = request.json.get('consumer')
    # Redeliver pending messages
    pending = redis_client.xpending(STREAM_KEY, GROUP_NAME)
    results = []
    for msg in pending['consumers']:
        if msg['consumer'] == consumer:
            msg_id = msg['message_id']
            if msg_id not in processed_ids:
                msg_data = redis_client.xrange(STREAM_KEY, min=msg_id, max=msg_id)
                for mid, fields in msg_data:
                    results.append({'id': mid, 'message': fields['message']})
    return jsonify({'replay': results})

@app.route('/trim', methods=['POST'])
def trim():
    """Trim the stream."""
    maxlen = request.json.get('maxlen', MAXLEN)
    redis_client.xtrim(STREAM_KEY, maxlen=maxlen, approximate=True)
    return jsonify({'status': 'trimmed', 'maxlen': maxlen})

@app.route('/group_info', methods=['GET'])
def group_info():
    """Get consumer group info."""
    info = redis_client.xinfo_groups(STREAM_KEY)
    return jsonify({'groups': info})

@app.route('/stream_info', methods=['GET'])
def stream_info():
    """Get stream info."""
    info = redis_client.xinfo_stream(STREAM_KEY)
    return jsonify({'stream': info})

# Consumer failure auto-failover (simple: redeliver pending)
def failover_monitor():
    """Monitor for failed consumers and redeliver."""
    while True:
        pending = redis_client.xpending(STREAM_KEY, GROUP_NAME)
        for msg in pending['consumers']:
            if msg['pending'] > 0 and time.time() - msg['idle'] > 10:
                # Redeliver if idle > 10s
                msg_id = msg['message_id']
                msg_data = redis_client.xrange(STREAM_KEY, min=msg_id, max=msg_id)
                for mid, fields in msg_data:
                    print(f"Failover: {mid} -> {fields['message']}")
        time.sleep(5)

threading.Thread(target=failover_monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
