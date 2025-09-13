# 1-coordinator-ring

## 概要
分散KVSのリーダー選出モデルの実装例。各ノードはリーダーとフォロワーで構成され、リーダーが全ての読み書きを処理します。リーダー選出・障害検知・ベクトルクロックによるバージョン管理を行い、CAP定理のCP特性（強一貫性・可用性）を重視しています。

## 構成
- Redis 3ノード（docker-composeで起動）
- Python/Flask APIサーバ（app.py） - リーダー選出、障害検知、ベクトルクロック、強一貫性APIを管理するコーディネーターとして機能
- ノード管理・リーダー選出・障害検知・ベクトルクロック・強一貫性API

## 機能
- 円環形ノード管理とコーディネーター選出
- ベクトルクロックによるデータバージョン管理
- 障害ノード検知と自動除外
- 強一貫性を保証する読み書きAPI
- ヘルスチェックとノード状態管理

## 起動方法
1. Redisクラスタ起動

```bash
docker-compose up -d
```

2. Python依存インストール

```bash
pip install -r requirements.txt
```

3. APIサーバ起動

```bash
python app.py
```

## API例
- 書き込み: `POST /write` {"key": "foo", "value": "bar"}
- 読み込み: `GET /read?key=foo`
- ヘルスチェック: `GET /health`
- 障害ノード除外: `POST /exclude_failed`

## テスト手順
1. Redisノードを1つ停止し、`/health`で障害検知を確認
2. `/exclude_failed`で障害ノードを除外
3. `/write`・`/read`で強一貫性を確認
4. ベクトルクロック値でバージョン管理を確認

## 設計思想
- リーダーは常に生存ノードから自動選出
- ベクトルクロックでデータ競合・障害復旧時の整合性を担保
- CP特性（強一貫性・可用性）を優先し、分断時は書き込み拒否

---

### システム構成図

┌─────────────┐
│   Client    │
└─────────────┘
       │
┌─────────────┐
│Python/Flask │
│ API Server  │
└─────────────┘
       │
┌─────────────┐
│Redis Cluster│
│             │
│Redis Node 1 │
│Redis Node 2 │
│Redis Node 3 │
└─────────────┘

**解説:**
ユーザーからのリクエストは、まずPythonで実装されたAPIサーバーに到達します。APIサーバーは、データの永続化と取得のためにRedisクラスタと通信します。このアーキテクチャは、Coordinator Ringパターンを実装しており、APIサーバーがノード管理、リーダー選出、障害検知などの役割を担い、Redisクラスタの各ノードと連携して強一貫性を保証します。

### AWS構成図

┌─────────────┐
│   Client    │
└─────────────┘
       │
┌─────────────┐
│ API Gateway │
└─────────────┘
       │
┌─────────────┐
│ECS on Fargate│
│Flask App Task│
└─────────────┘
       │
┌─────────────┐
│ElastiCache  │
│  for Redis  │
└─────────────┘

**解説:**
このAWS構成では、オンプレミスの各コンポーネントをAWSのマネージドサービスにマッピングしています。

*   **Python/Flask API Server → Amazon ECS on Fargate:**
    コンテナ化されたアプリケーションをサーバーレスで実行するためにECS on Fargateを選択します。これにより、インフラのプロビジョニングや管理の手間が削減され、スケーラビリティが向上します。
*   **Redis Cluster → Amazon ElastiCache for Redis:**
    フルマネージドなRedisサービスであるElastiCacheを利用することで、Redisクラスタのセットアップ、運用、スケーリングが容易になります。高可用性とパフォーマンスを提供します。
*   **Client Access → Amazon API Gateway:**
    API Gatewayをシステムのフロントに配置することで、APIの保護、スロットリング、モニタリングなどの機能を利用できます。

この構成により、可用性、スケーラビリティ、運用効率に優れたシステムをAWS上に構築できます。
