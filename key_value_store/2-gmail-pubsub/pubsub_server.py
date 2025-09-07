import redis
import threading
import time
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from collections import defaultdict

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

TOPICS = ["email", "calendar", "drive"]
subscribers = defaultdict(set)  # topic -> set of subscriber sid
subscriber_status = defaultdict(lambda: defaultdict(str))  # sid -> topic -> status
message_filters = defaultdict(dict)  # sid -> topic -> filter
backpressure_queue = defaultdict(list)  # sid -> topic -> [messages]

# Redis Pub/Sub listener thread
class RedisListener(threading.Thread):
    def __init__(self, topic):
        super().__init__()
        self.topic = topic
        self.pubsub = redis_client.pubsub()
        self.pubsub.subscribe(topic)
        self.daemon = True

    def run(self):
        for msg in self.pubsub.listen():
            if msg['type'] == 'message':
                payload = msg['data']
                # Broadcast to all subscribers of this topic
                for sid in list(subscribers[self.topic]):
                    # Filter check
                    f = message_filters[sid].get(self.topic)
                    if f and f not in payload:
                        continue
                    # Backpressure: if status is 'busy', queue message
                    if subscriber_status[sid][self.topic] == 'busy':
                        backpressure_queue[(sid, self.topic)].append(payload)
                    else:
                        socketio.emit('notification', {'topic': self.topic, 'message': payload}, room=sid)
                        subscriber_status[sid][self.topic] = 'delivered'

# Start listeners for all topics
for topic in TOPICS:
    RedisListener(topic).start()

@app.route('/publish', methods=['POST'])
def publish():
    topic = request.json.get('topic')
    message = request.json.get('message')
    if topic not in TOPICS:
        return jsonify({'error': 'Invalid topic'}), 400
    redis_client.publish(topic, message)
    return jsonify({'status': 'published'})

@app.route('/topics', methods=['GET'])
def get_topics():
    return jsonify({'topics': TOPICS})

@socketio.on('subscribe')
def handle_subscribe(data):
    topic = data.get('topic')
    sid = request.sid
    if topic not in TOPICS:
        emit('error', {'error': 'Invalid topic'})
        return
    join_room(sid)
    subscribers[topic].add(sid)
    subscriber_status[sid][topic] = 'subscribed'
    emit('subscribed', {'topic': topic})

@socketio.on('unsubscribe')
def handle_unsubscribe(data):
    topic = data.get('topic')
    sid = request.sid
    if topic in subscribers:
        subscribers[topic].discard(sid)
        subscriber_status[sid][topic] = 'unsubscribed'
    leave_room(sid)
    emit('unsubscribed', {'topic': topic})

@socketio.on('set_filter')
def handle_set_filter(data):
    topic = data.get('topic')
    filter_str = data.get('filter')
    sid = request.sid
    message_filters[sid][topic] = filter_str
    emit('filter_set', {'topic': topic, 'filter': filter_str})

@socketio.on('status')
def handle_status(data):
    topic = data.get('topic')
    status = data.get('status')  # 'busy' or 'ready'
    sid = request.sid
    subscriber_status[sid][topic] = status
    # If ready, flush backpressure queue
    if status == 'ready':
        queue = backpressure_queue.pop((sid, topic), [])
        for msg in queue:
            socketio.emit('notification', {'topic': topic, 'message': msg}, room=sid)
            subscriber_status[sid][topic] = 'delivered'
    emit('status_updated', {'topic': topic, 'status': status})

@app.route('/subscribers', methods=['GET'])
def get_subscribers():
    topic = request.args.get('topic')
    subs = list(subscribers[topic]) if topic in subscribers else []
    return jsonify({'topic': topic, 'subscribers': subs})

@app.route('/delivery_status', methods=['GET'])
def delivery_status():
    sid = request.args.get('sid')
    topic = request.args.get('topic')
    status = subscriber_status[sid][topic] if sid and topic else None
    return jsonify({'sid': sid, 'topic': topic, 'status': status})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
