import redis
import threading
import time
from flask import Flask, request, jsonify

app = Flask(__name__)
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

STREAM_KEY = "line_stream"
GROUP_NAME = "line_consumers"
MAXLEN = 1000  # ストリーム容量制限

# Consumer Group作成
try:
    redis_client.xgroup_create(STREAM_KEY, GROUP_NAME, id='0', mkstream=True)
except redis.exceptions.ResponseError as e:
    if "BUSYGROUP" not in str(e):
        raise

# メッセージ重複検知用
processed_ids = set()

@app.route('/produce', methods=['POST'])
def produce():
    message = request.json.get('message')
    # ストリーム容量制限・トリミング
    msg_id = redis_client.xadd(STREAM_KEY, {'message': message}, maxlen=MAXLEN, approximate=True)
    return jsonify({'id': msg_id})

@app.route('/consume', methods=['POST'])
def consume():
    consumer = request.json.get('consumer')
    count = request.json.get('count', 1)
    # 未処理メッセージ取得
    msgs = redis_client.xreadgroup(GROUP_NAME, consumer, {STREAM_KEY: '>'}, count=count, block=1000)
    results = []
    for stream, messages in msgs:
        for msg_id, fields in messages:
            # 重複検知
            if msg_id in processed_ids:
                continue
            processed_ids.add(msg_id)
            results.append({'id': msg_id, 'message': fields['message']})
            # ack
            redis_client.xack(STREAM_KEY, GROUP_NAME, msg_id)
    return jsonify({'messages': results})

@app.route('/pending', methods=['GET'])
def pending():
    consumer = request.args.get('consumer')
    # 未処理メッセージ一覧
    pending = redis_client.xpending(STREAM_KEY, GROUP_NAME)
    return jsonify({'pending': pending})

@app.route('/replay', methods=['POST'])
def replay():
    consumer = request.json.get('consumer')
    # 未処理メッセージの再配信
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
    maxlen = request.json.get('maxlen', MAXLEN)
    redis_client.xtrim(STREAM_KEY, maxlen=maxlen, approximate=True)
    return jsonify({'status': 'trimmed', 'maxlen': maxlen})

@app.route('/group_info', methods=['GET'])
def group_info():
    info = redis_client.xinfo_groups(STREAM_KEY)
    return jsonify({'groups': info})

@app.route('/stream_info', methods=['GET'])
def stream_info():
    info = redis_client.xinfo_stream(STREAM_KEY)
    return jsonify({'stream': info})

# Consumer障害時の自動フェイルオーバー（簡易: pending再配信）
def failover_monitor():
    while True:
        pending = redis_client.xpending(STREAM_KEY, GROUP_NAME)
        for msg in pending['consumers']:
            if msg['pending'] > 0 and time.time() - msg['idle'] > 10:
                # 10秒以上未処理なら再配信
                msg_id = msg['message_id']
                msg_data = redis_client.xrange(STREAM_KEY, min=msg_id, max=msg_id)
                for mid, fields in msg_data:
                    # 再配信（ここではログのみ）
                    print(f"Failover: {mid} -> {fields['message']}")
        time.sleep(5)

threading.Thread(target=failover_monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
