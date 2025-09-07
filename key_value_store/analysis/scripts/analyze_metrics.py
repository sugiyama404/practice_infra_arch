import json
import os
import matplotlib.pyplot as plt

data_dir = os.path.join(os.path.dirname(__file__), '../data')
metrics_path = os.path.join(data_dir, 'metrics.json')

with open(metrics_path) as f:
    metrics = json.load(f)

names = list(metrics.keys())
latencies = [metrics[n].get('latency', 0) or 0 for n in names]

plt.figure(figsize=(10, 5))
plt.bar(names, latencies, color='skyblue')
plt.ylabel('Latency (sec)')
plt.title('KVS Pattern Latency Comparison')
plt.savefig(os.path.join(data_dir, 'latency_comparison.png'))
print('Latency comparison chart saved.')
