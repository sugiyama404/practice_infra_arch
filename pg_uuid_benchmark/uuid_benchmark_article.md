# データベースID生成方式の性能比較: 複数DB比較 (PostgreSQL, MySQL, Redis, MongoDB, SQLite)

## 概要

この記事では、PostgreSQL, MySQL, Redis, MongoDB, SQLiteを対象としたID生成方式（Auto-increment, UUID v4, UUID v7, Snowflake）のCRUD操作性能を比較したベンチマーク結果を解説します。データベースのスケーラビリティと分散性を考慮したID選択の指針を提供することを目的としています。

**注意**: このベンチマークではPostgreSQL 18を使用していますが、データシードの制約により、PostgreSQLの結果はUUID v4およびUUID v7のみを対象としています。Auto-incrementおよびSnowflakeの結果はMySQLから引用しています。

## 背景

現代の分散システムでは、一意なID生成が重要な課題です。従来のAuto-incrementは単一DBでは効率的ですが、分散環境では不向きです。一方、UUID v4は分散性に優れますが、性能面で課題があります。UUID v7やSnowflakeのような時間順序性を考慮した方式が注目されています。

このベンチマークでは、以下のID生成方式を比較：
- **Auto-increment**: シーケンシャルな整数ID（MySQLのみ）
- **UUID v4**: ランダムな128ビットUUID
- **UUID v7**: 時間順序性を考慮したUUID
- **Snowflake**: Twitterの分散ID生成アルゴリズム（MySQLのみ）

## ベンチマーク設定

### 環境
- **データベース**:
  - PostgreSQL 17 (postgres_mixed) - 全ID方式比較用
  - MySQL 8.3
  - Redis 7
  - MongoDB 7
  - SQLite (keinos/sqlite3:latest)
- **ストレージ**: ローカルNVMe SSD
- **ワークロード**: 挿入、更新、削除、選択操作
- **データ規模**: 数万〜数十万行
- **並行性**: 複数スレッドでの同時実行

### 測定項目
- **挿入スループット**: 1秒間に挿入できるレコード数
- **CRUD操作レイテンシ**: 各操作の応答時間
- **範囲SELECT分布**: レンジクエリの効率性
- **テーブル/インデックスサイズ**: ストレージ使用量
- **インデックス断片化**: インデックスの効率性

## 結果と考察

### PostgreSQL（UUID v4およびv7のみ）

#### 挿入スループット
![PostgreSQL 挿入スループット比較](images/postgresql_insert_throughput.png)

UUID v7がUUID v4よりも高いスループットを示しました。UUID v7の時間順序性により、B-Treeのページ分割が減少し、挿入効率が向上します。具体的には、UUID v7はタイムスタンプをMSB（最上位ビット）に配置することで、挿入がB-Treeの右端に集中し、シーケンシャル挿入に近い挙動を示します。一方、UUID v4の完全なランダム性はページ全体に分散し、頻繁なページ分割と断片化を引き起こします。これにより、UUID v7は分散システムでの書き込み性能を大幅に改善します。

| ID方式 | 相対スループット | 特徴 |
|--------|------------------|------|
| UUID v7 | 高 | 時間順序性による効率的な挿入 |
| UUID v4 | 低 | ランダム性によるページ分割増加 |

#### CRUDレイテンシ
![PostgreSQL CRUDレイテンシ比較](images/postgresql_crud_latency.png)

主キー検索では両方式で差が小さいですが、INSERT操作ではUUID v4のレイテンシが高くなります。UUID v7はシーケンシャルな挿入が可能で、性能が安定します。主キー検索はインデックスアクセスが支配的で、IDの順序性が影響しにくいですが、INSERTではB-Treeの再構築コストがUUID v4で顕著になります。また、UPDATE/DELETEも同様に、UUID v4の断片化がランダムアクセスを増加させます。

#### 範囲SELECT分布
![PostgreSQL 範囲SELECT分布](images/postgresql_range_select.png)

UUID v7は時間順序性があるため、レンジスキャン時の分布が比較的滑らかです。一方、UUID v4はランダム性が高く、アクセス分布にばらつきが生じます。範囲クエリでは、B-Treeの連続アクセスが効率的ですが、UUID v4のランダム配置はキャッシュミスを増加させ、I/Oコストを高めます。UUID v7は時間ベースの順序性により、レンジクエリのパフォーマンスを向上させ、時系列データやログ分析に適しています。

#### サイズ比較
![PostgreSQL サイズ比較](images/postgresql_size_comparison.png)

UUIDは128ビット（16バイト）で、bigint（8バイト）のAuto-incrementよりもサイズが大きいです。UUID v4は断片化の影響で、実効サイズが増加する傾向があります。インデックスサイズもUUIDの方が大きく、メモリ使用量やストレージコストに影響します。特に、UUID v4の断片化はインデックス再構築を必要とし、メンテナンスコストを増加させます。分散システムではサイズのトレードオフを考慮する必要があります。

### MySQL

#### 挿入スループット
![MySQL 挿入スループット比較](images/mysql_insert_throughput.png)

Auto-incrementが最も高いスループットを示し、UUID v7とSnowflakeがこれに次ぐ。UUID v4は顕著に低い性能を示しました。InnoDBのクラスタ化インデックス特性により、シーケンシャルIDが優位です。クラスタ化インデックスではPK順にデータが物理的に並ぶため、Auto-incrementのシーケンシャル挿入はI/Oを最小限に抑えます。UUID v7とSnowflakeも時間順序性でこれに近づきますが、UUID v4のランダム性はページ分割を激増させ、性能を低下させます。

| ID方式 | 相対スループット | 特徴 |
|--------|------------------|------|
| Auto-increment | 最高 | シーケンシャル挿入で最高性能 |
| UUID v7 | 高 | Snowflakeと同等、Auto-incrementに次ぐ |
| Snowflake | 高 | 分散性と性能のバランス |
| UUID v4 | 低 | ランダム性による性能低下 |

#### CRUDレイテンシ
![MySQL CRUDレイテンシ比較](images/mysql_crud_latency.png)

主キー検索は全方式で高速ですが、INSERTではUUID v4が高止まり。UUID v7とSnowflakeはAuto-incrementに近い性能を発揮します。クラスタ化インデックスの恩恵で、主キー検索は常に高速ですが、INSERT時のページ分割コストがUUID v4で高くなります。UPDATE/DELETEも同様に、UUID v4の断片化が影響します。Snowflakeの64ビット整数はサイズ効率が高く、UUID v7と同等の性能を維持します。

#### 範囲SELECT分布
![MySQL 範囲SELECT分布](images/mysql_range_select.png)

Auto-incrementとUUID v7はレンジアクセス時のばらつきが小さく、効率的です。UUID v4はコストのばらつきが大きく、アクセス効率が低下します。クラスタ化インデックスにより、シーケンシャルIDのレンジクエリは物理的に連続したアクセスが可能で、キャッシュ効率が高くなります。UUID v4のランダム性はこれを損ない、I/Oコストを増加させます。Snowflakeも時間順序性で安定した性能を示します。

#### サイズ比較
![MySQL サイズ比較](images/mysql_size_comparison.png)

bigint（Auto-increment）が最小サイズ。UUIDはインデックス/テーブル占有が増加、特にUUID v4の断片化影響が顕著です。クラスタ化インデックスではPKがデータ配置を決定するため、UUID v4の断片化はテーブル全体のストレージ効率を低下させます。Snowflakeの8バイトはUUIDの16バイトより効率的で、分散システムのコストを抑えます。

| ID方式 | サイズ（PK） | 特徴 |
|--------|--------------|------|
| Auto-increment (bigint) | 8バイト | 最小サイズ |
| UUID (v4/v7) | 16バイト | サイズ増加、断片化影響 |
| Snowflake | 8バイト | 整数ベースでコンパクト |

### Redis

RedisはインメモリKVSとして、高速なCRUD操作を提供します。ID生成方式による性能差は小さく、主にデータ構造の選択が影響します。

#### 挿入スループット
![Redis 挿入スループット比較](images/redis_insert_throughput.png)

全ID方式で高いスループットを示します。メモリベースのため、ディスクI/Oのボトルネックがありません。Redisのハッシュテーブル構造はIDの順序性に依存せず、ランダムアクセスでも高速です。ただし、メモリ容量が限界となり、大規模データではスワップが発生する可能性があります。

#### CRUDレイテンシ
![Redis CRUDレイテンシ比較](images/redis_crud_latency.png)

主キー検索が極めて高速。INSERT/UPDATEも低レイテンシですが、複雑なクエリはサポートされません。メモリアクセスはナノ秒オーダーですが、永続化（RDB/AOF）時はディスクI/Oが発生します。UUIDのサイズ増加はメモリ使用量に影響し、キャッシュ効率を低下させる可能性があります。

#### 範囲SELECT分布
![Redis 範囲SELECT分布](images/redis_range_select.png)

Redisはレンジクエリをサポートしますが、ソートセットを使用する場合に効率的です。ハッシュではレンジクエリが不可能ですが、ソートセット（ZSET）ではスコアベースの順序付けが可能になります。UUID v4のランダム性はソートセットのスコア設計に影響しますが、メモリベースのためアクセスは高速です。

#### サイズ比較
![Redis サイズ比較](images/redis_size_comparison.png)

メモリ使用量はデータ量に比例。UUIDのサイズ増加がメモリ消費に影響します。Redisのメモリ効率はキーのサイズに依存し、UUIDの16バイトはbigintの8バイトより消費量が増えます。メモリは貴重なリソースのため、ID方式の選択が全体のキャッシュ容量に影響します。

### MongoDB

MongoDBはドキュメント指向DBとして、柔軟なスキーマを提供します。ID生成方式による性能差はインデックス設計に依存します。

#### 挿入スループット
![MongoDB 挿入スループット比較](images/mongodb_insert_throughput.png)

ObjectId（デフォルト）やUUID v4/v7で安定した性能。Auto-incrementは手動実装が必要。MongoDBのWiredTigerストレージエンジンはB-Treeを使用し、UUID v7の時間順序性が挿入効率を高めます。ObjectIdもタイムスタンプを含むため、似た特性を示します。

#### CRUDレイテンシ
![MongoDB CRUDレイテンシ比較](images/mongodb_crud_latency.png)

主キー検索が高速。INSERTはドキュメントサイズに依存。MongoDBのインデックスはB-Treeベースで、主キー検索は効率的ですが、INSERT時のドキュメントサイズ増加（UUID含む）が性能に影響します。UUID v4のランダム性はインデックス断片化を招きます。

#### 範囲SELECT分布
![MongoDB 範囲SELECT分布](images/mongodb_range_select.png)

インデックスを使用したレンジクエリが可能。UUID v4のランダム性はインデックス効率に影響。MongoDBの複合インデックスで時間順序性を活かせば、レンジクエリが効率的になりますが、UUID v4はランダムアクセスを増加させます。

#### サイズ比較
![MongoDB サイズ比較](images/mongodb_size_comparison.png)

ドキュメントサイズが増加。UUIDは追加のストレージ消費。MongoDBのドキュメントモデルでは、UUIDの16バイトが各ドキュメントに追加され、ストレージとメモリ使用量を増加させます。ObjectIdの12バイトはUUIDより効率的です。

### SQLite

SQLiteはファイルベースの軽量DBとして、単一ファイルで動作します。並行性に制約があります。

#### 挿入スループット
![SQLite 挿入スループット比較](images/sqlite_insert_throughput.png)

Auto-incrementが最も効率的。UUID v4は性能低下が顕著。SQLiteのB-Treeインデックスはシーケンシャル挿入を最適化しますが、UUID v4のランダム性はページ分割を増加させ、単一ライター制約下で性能を低下させます。

#### CRUDレイテンシ
![SQLite CRUDレイテンシ比較](images/sqlite_crud_latency.png)

単一ライター制約のため、並行INSERTで性能が低下。SQLiteはファイルベースで、並行性に制限があります。UUID v4の断片化はVACUUM操作を必要とし、メンテナンスコストを増加させます。

#### 範囲SELECT分布
![SQLite 範囲SELECT分布](images/sqlite_range_select.png)

B-Treeインデックスを使用。シーケンシャルIDが有利。SQLiteのインデックスは効率的ですが、UUID v4のランダム性はレンジクエリの連続アクセスを妨げます。

#### サイズ比較
![SQLite サイズ比較](images/sqlite_size_comparison.png)

ファイルサイズが増加。UUIDのサイズ影響が大きい。SQLiteの単一ファイル構造では、UUIDの16バイトがデータベースサイズを直接増加させ、モバイルや組み込み環境でのコストを高めます。

## 最終結論

### 性能比較サマリー

![全データベース性能比較サマリー](images/performance_summary.png)

| データベース | ID方式 | 挿入スループット | CRUDレイテンシ | 範囲SELECT | サイズ効率 | 分散性 | 主な用途 |
|--------------|--------|------------------|----------------|------------|------------|--------|----------|
| PostgreSQL | UUID v7 | 高 | 中 | 高 | 低 | あり | 分散システム |
| PostgreSQL | UUID v4 | 低 | 高 | 低 | 低 | あり | 非推奨 |
| MySQL | Auto-increment | 最高 | 低 | 最高 | 最高 | なし | 単一DB |
| MySQL | UUID v7 | 高 | 中 | 高 | 低 | あり | 分散システム |
| MySQL | Snowflake | 高 | 中 | 高 | 高 | あり | 分散システム |
| MySQL | UUID v4 | 低 | 高 | 低 | 低 | あり | 非推奨 |
| Redis | 全方式 | 最高 | 最低 | 中 | 中 | あり | キャッシュ/KVS |
| MongoDB | ObjectId/UUID | 高 | 中 | 中 | 中 | あり | ドキュメントDB |
| SQLite | Auto-increment | 高 | 中 | 高 | 高 | なし | 軽量DB |

- **書き込み・スケール最優先**: Auto-increment（単一DB構成）- クラスタ化インデックスの恩恵で最高の挿入性能を発揮しますが、分散環境では一意性保証が困難です。
- **分散性と性能の両立**: UUID v7（Snowflakeも同等クラス）- 時間順序性を保ちつつ分散生成が可能で、書き込み性能とレンジクエリの効率をバランスよく提供します。
- **UUID v4をPKとする選択**: 書き込み・レンジアクセス・サイズ効率の観点で非推奨 - 断片化によるメンテナンスコストと性能低下が深刻です。
- **高速アクセス重視**: Redis（インメモリKVS）- メモリベースの高速アクセスが可能ですが、永続性と容量に制約があります。
- **柔軟スキーマ**: MongoDB（ドキュメント指向）- スキーマ変更に強いですが、ID方式による性能差がインデックス設計に依存します。
- **軽量・移植性**: SQLite（組み込みDB）- 単一ファイルで動作しますが、並行性とスケーラビリティに制限があります。

### 運用指針
- 単一DB構成ではAuto-incrementを第一候補に
- 分散一意性が要る場合はUUID v7を標準選択肢に
- 既存のUUID v4 PK大規模テーブルは、性能ボトルネックを踏まえ移行検討を推奨
- 高頻度アクセスにはRedisを検討
- スキーマ変更が多い場合はMongoDBを検討
- 軽量・移植性が必要な場合はSQLiteを検討

### 技術的考察
- **B-Treeインデックスの挙動**: UUID v4のランダム性はページ分割を増加させ、断片化を招く。UUID v7の時間順序性はこれを緩和。B-Treeはシーケンシャル挿入を最適化するよう設計されており、ランダム挿入はリバランスコストを高めます。
- **クラスタ化インデックス（InnoDB）**: MySQLのInnoDBではPKがクラスタ化インデックスとなるため、シーケンシャルIDがI/O効率を高める。データとインデックスが一体化し、PK順の物理配置がキャッシュ効率を向上させます。
- **インメモリ vs ディスク**: Redisの高速性はメモリベースによるが、永続性は別途考慮。ディスクベースDBではI/Oがボトルネックとなりますが、RedisはCPU/メモリが支配的です。
- **分散システムでの考慮**: UUID v4は生成の簡易性が高いが、性能トレードオフが大きい。UUID v7やSnowflakeは時間順序性を保ちつつ分散性を確保。クロック同期や衝突回避が重要です。

このベンチマークは特定の環境での結果であり、実際の運用ではワークロード特性に応じたチューニングが必要です。

## まとめ

このベンチマークでは、PostgreSQL, MySQL, Redis, MongoDB, SQLiteを対象に、Auto-increment, UUID v4, UUID v7, SnowflakeのID生成方式の性能を比較しました。結果として、ID方式の選択がデータベースの性能に大きな影響を与えることが明らかになりました。

### 主要な発見
- **UUID v4の課題**: ランダム性によるB-Tree断片化が、挿入性能とレンジクエリ効率を低下させる。既存システムでの使用は慎重に検討すべき。
- **UUID v7の優位性**: 時間順序性を保ちつつ分散性を確保し、UUID v4の欠点を克服。分散システムの標準選択肢として有望。
- **データベース特性の影響**: InnoDBのクラスタ化インデックス（MySQL）ではシーケンシャルIDが特に有効。インメモリDB（Redis）ではID方式の差が小さい。
- **トレードオフの重要性**: 分散性、性能、サイズ効率のバランスをワークロードに応じて調整する必要がある。

### ID選択のガイドライン
- **単一DB/高書き込み**: Auto-increment
- **分散システム/時系列データ**: UUID v7 or Snowflake
- **高速キャッシュ**: Redis（ID方式依存度低）
- **柔軟性重視**: MongoDB（ObjectId推奨）
- **軽量組み込み**: SQLite（Auto-increment）

### 将来の展望
UUID v7の標準化が進む中、既存のUUID v4ベースシステムの移行が課題となるでしょう。また、NewSQLや分散DBの台頭により、ID生成の自動化と最適化がさらに重要になります。このベンチマーク結果を基に、システム設計時の参考として活用してください。
