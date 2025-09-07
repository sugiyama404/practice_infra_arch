import os
import glob
import pandas as pd

data_dirs = [
    '../1-coordinator-ring/data',
    '../2-gmail-pubsub/data',
    '../3-line-streams/data',
    '../4-quorum-consistency/data',
    '../5-sharding-replica/data',
    '../6-distributed-lock/data',
    '../7-bloom-sstable/data'
]

output_dir = '../analysis/data'
os.makedirs(output_dir, exist_ok=True)

all_dfs = []
for d in data_dirs:
    csv_files = glob.glob(os.path.join(d, '*.csv'))
    for f in csv_files:
        df = pd.read_csv(f)
        df['source'] = os.path.basename(d)
        all_dfs.append(df)

if all_dfs:
    merged = pd.concat(all_dfs, ignore_index=True)
    merged.to_csv(os.path.join(output_dir, 'all_patterns_metrics.csv'), index=False)
    print('CSV files imported and merged to analysis/data/all_patterns_metrics.csv')
else:
    print('No CSV files found in pattern data directories.')
