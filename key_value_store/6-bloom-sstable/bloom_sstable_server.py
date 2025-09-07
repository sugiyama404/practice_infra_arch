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

# Redis接続設定
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Bloom Filter
bloom = BloomFilter(capacity=10000, error_rate=0.001)

# MemTable (in-memory sorted)
memtable = SortedDict()
MEMTABLE_LIMIT = 1000

# Commit Log (WAL)
WAL_PATH = os.path.join(DATA_DIR, 'commit.log')

# SSTable (disk sorted)
def write_sstable(data, level=0):
    fname = os.path.join(DATA_DIR, f'sstable_level{level}_{int(time.time())}.sst')
    with open(fname, 'w') as f:
        for k, v in data.items():
            f.write(f'{k}\t{v}\n')
    return fname

def read_sstable():
    files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith('sstable_')])
    sstable = SortedDict()
    for fname in files:
        with open(os.path.join(DATA_DIR, fname)) as f:
            for line in f:
                k, v = line.strip().split('\t')
                sstable[k] = v
    return sstable

# LSM-Tree圧縮
def lsm_compact():
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

# L1/L2キャッシュ
l1_cache = memtable
l2_cache = diskcache.Cache(os.path.join(DATA_DIR, 'l2cache'))

# WAL書き込み
def write_wal(key, value):
    with open(WAL_PATH, 'a') as f:
        f.write(f'{key}\t{value}\n')

@app.route('/put', methods=['POST'])
def put():
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
    lsm_compact()
    return jsonify({'status': 'compacted'})

@app.route('/stats', methods=['GET'])
def stats():
    return jsonify({
        'memtable_size': len(memtable),
        'bloom_items': bloom.count,
        'l1_cache': len(l1_cache),
        'l2_cache': len(l2_cache),
        'sstable_files': len([f for f in os.listdir(DATA_DIR) if f.startswith('sstable_')])
    })

# バックグラウンド圧縮

def compact_worker():
    while True:
        lsm_compact()
        time.sleep(30)

threading.Thread(target=compact_worker, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
