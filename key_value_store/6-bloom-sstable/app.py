import os
import threading
import time
from flask import Flask, request, jsonify
from pybloom_live import BloomFilter
from sortedcontainers import SortedDict
import diskcache
import redis

app = Flask(__name__)
DATA_DIR = './data'
os.makedirs(DATA_DIR, exist_ok=True)

# Redis connection
REDIS_HOST = os.environ.get("REDIS_HOST", "redis-node1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

@app.route('/write', methods=['POST'])
def write():
    data = request.get_json()
    if not data or 'key' not in data or 'value' not in data:
        return jsonify({'status': 'error', 'message': 'Missing key or value'}), 400
    key = data['key']
    value = data['value']
    memtable[key] = value
    bloom.add(key)
    try:
        redis_client.set(key, value)
    except Exception as e:
        pass
    if len(memtable) >= MEMTABLE_LIMIT:
        write_sstable(memtable)
        memtable.clear()
    return jsonify({'status': 'ok', 'key': key, 'value': value})

@app.route('/read', methods=['GET'])
def read():
    key = request.args.get('key')
    if not key:
        return jsonify({'status': 'error', 'message': 'Missing key'}), 400
    if key in memtable:
        return jsonify({'status': 'ok', 'key': key, 'value': memtable[key]})
    try:
        value = redis_client.get(key)
        if value is not None:
            return jsonify({'status': 'ok', 'key': key, 'value': value})
    except Exception as e:
        pass
    # SSTable fallback
    for fname in sorted([f for f in os.listdir(DATA_DIR) if f.startswith('sstable_')]):
        with open(os.path.join(DATA_DIR, fname)) as f:
            for line in f:
                k, v = line.strip().split('\t')
                if k == key:
                    return jsonify({'status': 'ok', 'key': key, 'value': v})
    return jsonify({'status': 'not_found', 'key': key}), 404
# Bloom Filter for fast lookups
bloom = BloomFilter(capacity=10000, error_rate=0.001)

# MemTable (in-memory sorted)
memtable = SortedDict()
MEMTABLE_LIMIT = 1000

# Commit Log (WAL)
WAL_PATH = os.path.join(DATA_DIR, 'commit.log')

# SSTable (disk sorted)
def write_sstable(data, level=0):
    """Write data to SSTable file."""
    fname = os.path.join(DATA_DIR, f'sstable_level{level}_{int(time.time())}.sst')
    with open(fname, 'w') as f:
        for k, v in data.items():
            f.write(f'{k}\t{v}\n')
    return fname

def read_sstable():
    """Read all SSTable files and merge."""
    files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith('sstable_')])
    sstable = SortedDict()
    for fname in files:
        with open(os.path.join(DATA_DIR, fname)) as f:
            for line in f:
                k, v = line.strip().split('\t')
                sstable[k] = v
    return sstable

# LSM-Tree compaction
def lsm_compact():
    """Compact SSTable files."""
    files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith('sstable_')])
    if len(files) > 2:
        merged = SortedDict()
        for fname in files:
            with open(os.path.join(DATA_DIR, fname)) as f:
                for line in f:
                    k, v = line.strip().split('\t')
                    merged[k] = v
        out = write_sstable(merged, level=1)
        for fname in files:
            os.remove(os.path.join(DATA_DIR, fname))

# L1/L2 cache
l1_cache = memtable
l2_cache = diskcache.Cache(os.path.join(DATA_DIR, 'l2cache'))

# WAL write
def write_wal(key, value):
    """Write to Write-Ahead Log."""
    with open(WAL_PATH, 'a') as f:
        f.write(f'{key}\t{value}\n')

@app.route('/put', methods=['POST'])
def put():
    """Put key-value pair."""
    key = request.json.get('key')
    value = request.json.get('value')
    bloom.add(key)
    memtable[key] = value
    l2_cache[key] = value
    write_wal(key, value)
    if len(memtable) >= MEMTABLE_LIMIT:
        write_sstable(memtable)
        memtable.clear()
    return jsonify({'status': 'ok'})

@app.route('/get', methods=['GET'])
def get():
    """Get value for key."""
    key = request.args.get('key')
    if key not in bloom:
        return jsonify({'found': False})
    if key in l1_cache:
        return jsonify({'value': l1_cache[key], 'cache': 'L1'})
    if key in l2_cache:
        return jsonify({'value': l2_cache[key], 'cache': 'L2'})
    sstable = read_sstable()
    if key in sstable:
        return jsonify({'value': sstable[key], 'cache': 'SSTable'})
    return jsonify({'found': False})

@app.route('/compact', methods=['POST'])
def compact():
    """Trigger compaction."""
    lsm_compact()
    return jsonify({'status': 'compacted'})

@app.route('/stats', methods=['GET'])
def stats():
    """Get statistics."""
    return jsonify({
        'memtable_size': len(memtable),
        'bloom_items': bloom.count,
        'l1_cache': len(l1_cache),
        'l2_cache': len(l2_cache),
        'sstable_files': len([f for f in os.listdir(DATA_DIR) if f.startswith('sstable_')])
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    try:
        redis_client.ping()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 503

# Background compaction
def compact_worker():
    """Background compaction worker."""
    while True:
        lsm_compact()
        time.sleep(30)

threading.Thread(target=compact_worker, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
