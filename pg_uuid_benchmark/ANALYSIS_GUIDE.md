# ID Benchmark Analysis Guide

## 🎯 目的

PostgreSQL・MySQL・Redisで、異なるID方式（UUIDv4／UUIDv7／連番／Snowflake）による検索速度を実測し、比較・分析する。

特に **PostgreSQL 18 で報告されているUUIDv7の高速化（UUIDv4比 約3倍）** を再現・検証する。

---

## 🔍 発見された問題

### 1. **PostgreSQL 18 でのデータ不足**

**問題:**
- `pg_uuid` (PostgreSQL 18) では、意図的に `uuid_v4_test` と `uuid_v7_test` のみをseedしている
- `seq_id_test` と `snowflake_test` のテーブルは存在するが、データが空
- 結果として、完全なクロスデータベース比較ができない

**原因:**
```python
pg_uuid_summaries = seed_postgres(
    connections.pg_uuid,
    RECORD_COUNT,
    config,
    include_tables=['uuid_v4_test', 'uuid_v7_test']  # ← これが原因
)
```

**解決策:**

**オプション A: 完全比較を行う場合**
```python
# include_tables を削除して全テーブルをseed
pg_uuid_summaries = seed_postgres(
    connections.pg_uuid,
    RECORD_COUNT,
    config
)
```

**オプション B: UUID専用の比較を維持する場合**
- 現在の設計を維持（推奨）
- ドキュメントで「PostgreSQL 18はUUID専用ベンチマーク」と明記
- `postgres_mixed` (PostgreSQL 17) で全ID戦略を比較

---

### 2. **lookup benchmark実行セルの欠落**

**問題:**
- `lookup_jobs` を準備するセルは存在
- しかし、実際に測定を実行して `results` を生成するセルが不足
- グラフ描画セルで `results_df` や `lookup_df` が未定義になる

**解決策:**
以下のセルを追加済み:

```python
# 新規追加: lookup benchmarkの実行
results = []
for label, fetcher, sample_ids in lookup_jobs:
    parts = label.split('::')
    database = parts[0]
    id_type = parts[1]
    operation = parts[2]

    metrics = measure_operation(
        operation=lambda: [fetcher(id_val) for id_val in sample_ids],
        label=label
    )

    results.append({
        'database': database,
        'id_type': id_type,
        'operation': operation,
        'avg_ms': metrics['avg_ms'],
        'p95_ms': metrics['p95_ms'],
        'min_ms': metrics['min_ms'],
        'max_ms': metrics['max_ms'],
        'lookups': len(sample_ids),
    })

results_df = results_to_frame(results)
```

```python
# 新規追加: lookup_df の明示的な生成
lookup_df = results_df[results_df['operation'] == 'lookup'].copy()
lookup_df.sort_values(['database', 'id_type']).reset_index(drop=True)
```

---

### 3. **分析セルの不足**

**問題:**
- データは収集されるが、クロスデータベース比較やUUIDv4 vs UUIDv7の定量分析が不足

**解決策:**
以下の分析セルを追加:

#### A. クロスデータベース比較
```python
# ID戦略ごとにデータベース間を比較
comparison_df = lookup_df.pivot_table(
    index='id_type',
    columns='database',
    values='avg_ms',
    aggfunc='mean'
)

# PostgreSQL mixedを基準とした相対性能
if 'postgres_mixed' in comparison_df.columns:
    for col in comparison_df.columns:
        comparison_df[f'{col}_relative'] = comparison_df[col] / comparison_df['postgres_mixed']

comparison_df
```

#### B. UUIDv7 高速化の定量分析
```python
uuid_comparison = lookup_df[lookup_df['id_type'].isin(['uuid_v4', 'uuid_v7'])].copy()
uuid_pivot = uuid_comparison.pivot_table(
    index='database',
    columns='id_type',
    values='avg_ms'
)

# 高速化倍率: UUIDv4 / UUIDv7
uuid_pivot['speedup_v7_over_v4'] = uuid_pivot['uuid_v4'] / uuid_pivot['uuid_v7']
uuid_pivot['improvement_pct'] = (uuid_pivot['speedup_v7_over_v4'] - 1) * 100

print("UUIDv7 Performance Improvement over UUIDv4:")
uuid_pivot[['uuid_v4', 'uuid_v7', 'speedup_v7_over_v4', 'improvement_pct']]
```

---

## 📊 実行手順

### 1. 環境準備
```bash
cd pg_uuid_benchmark
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 2. ノートブック実行順序

1. **セル 1-3**: 環境確認
2. **セル 4-6**: 設定とインポート
3. **セル 7-8**: Docker Compose起動
4. **セル 9-12**: 接続とbootstrap
5. **セル 13-21**: データのseed（PostgreSQL, MySQL, Redis）
6. **セル 22-23**: lookup jobsの準備
7. **セル 24-25**: ✨ **新規** lookup benchmarkの実行
8. **セル 26-27**: lookup結果の可視化
9. **セル 28-30**: ✨ **新規** クロスデータベース比較
10. **セル 31**: results.csvへの保存
11. **セル 32-34**: PostgreSQL UUID詳細比較

### 3. 完全比較を行う場合の修正

セル16を以下のように変更:
```python
# Before (UUID専用)
pg_uuid_summaries = seed_postgres(
    connections.pg_uuid,
    RECORD_COUNT,
    config,
    include_tables=['uuid_v4_test', 'uuid_v7_test']
)

# After (全ID戦略)
pg_uuid_summaries = seed_postgres(
    connections.pg_uuid,
    RECORD_COUNT,
    config
)
```

---

## 🎯 期待される成果

### 1. **lookupレイテンシーの比較**
- データベース別、ID戦略別の平均・P95レイテンシー
- グラフ: `bar_latency(lookup_df, metric='avg_ms')`

### 2. **UUIDv7 高速化の検証**
- PostgreSQL 18 で **UUIDv7 ≒ 3x faster than UUIDv4** の再現
- 他のデータベース（MySQL, Redis）での傾向確認

### 3. **ID戦略の選択指針**
- **連番 (seq_id)**: 最速だが分散システムに不向き
- **UUIDv4**: ランダムでインデックス肥大化リスク
- **UUIDv7**: 時系列ソート可能で高速（PostgreSQL 18で特に顕著）
- **Snowflake**: 分散ID生成、時系列保証、コンパクト

### 4. **データベース別の特性**
- **PostgreSQL**: UUIDv7で大幅改善、btreeインデックス効率化
- **MySQL**: 文字列UUIDでも比較的良好
- **Redis**: メモリベースで全戦略が高速（<0.1ms）

---

## 📝 Findings記入例

```markdown
### Findings

**Lookup Performance Summary:**
- **Redis**: 全ID戦略で 0.07-0.08ms（最速、メモリベース）
- **PostgreSQL 17**: seq_id 0.32ms、UUIDv4/v7 0.31-0.32ms（ほぼ同等）
- **PostgreSQL 18**: UUIDv7が0.31ms、UUIDv4より **XX%高速化を確認**
- **MySQL**: 0.31-0.33ms（文字列UUIDでも許容範囲）

**UUIDv7 Advantages:**
- PostgreSQL 18 で insert性能 約3倍向上（secondary workload）
- インデックスの局所性向上によりキャッシュヒット率改善
- 時系列ソート可能でORDER BY不要

**Trade-offs:**
- **seq_id**: 最速だが分散環境で衝突リスク、予測可能性の問題
- **UUIDv4**: ランダム性高いがインデックス断片化
- **Snowflake**: 生成に追加インフラ必要、ビット構成の理解が必要

**Recommendation:**
- **新規PostgreSQL 18プロジェクト**: UUIDv7を第一選択
- **分散システム**: SnowflakeまたはUUIDv7
- **レガシー互換**: UUIDv4（既存システムとの統合時）
```

---

## 🔧 トラブルシューティング

### エラー: `NameError: name 'lookup_df' is not defined`
**原因:** lookup benchmark実行セルをスキップした
**解決:** セル24-25を実行

### エラー: `KeyError: 'postgres_uuid18'` in results
**原因:** `pg_uuid_summaries` が空またはUUIDテーブルのみ
**解決:** セル16で `include_tables` を削除して全テーブルをseed

### データが取得できない
**確認項目:**
1. Docker Composeが起動しているか: `docker compose ps`
2. 接続情報が正しいか: `connections` オブジェクトを確認
3. seedが完了しているか: `pg_mixed_summaries`, `pg_uuid_summaries` を確認

---

## 📚 参考資料

- [PostgreSQL UUID v7 improvements](https://www.postgresql.org/docs/18/datatype-uuid.html)
- [Snowflake ID design](https://en.wikipedia.org/wiki/Snowflake_ID)
- [UUID RFC 4122bis](https://datatracker.ietf.org/doc/html/draft-peabody-dispatch-new-uuid-format)

---

**Last Updated:** 2025-10-09
