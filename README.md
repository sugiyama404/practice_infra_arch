# Practice Infrastructure Architecture

**実務レベルのインフラ設計・システム設計を検証するための設計演習プロジェクト集**

---

## 概要

このリポジトリは、**実務で通用するインフラ設計・システム設計力の習得と検証**を目的とした設計演習プロジェクト集です。

単なる構築手順の学習ではなく、以下を重視しています。

* 要件・前提条件の整理
* アーキテクチャ選定の理由とトレードオフ
* スケーラビリティ / 可用性 / コストのバランス
* 実装・ベンチマークによる設計仮説の検証

各プロジェクトは **「想定ユースケース → 設計 → 実装 → 学び」** の流れで構成されており、
**設計思考そのものを成果物として残す** ことを目的としています。

---

## このリポジトリで示したいこと

* 単一クラウド・単一構成に依存しない設計思考
* スモールスタートからスケールまでの設計判断
* 分散システムにおける失敗パターンと回避策
* 実務では検証しづらい設計案の比較・検証

👉 **「なぜこの構成なのか」を説明できること** を最重要視しています。

---

## 📁 プロジェクト一覧（設計事例）

### 1. ML Trading System

`ml_trading_system/`

機械学習（強化学習）を用いたトレーディングシステムを題材に、
**MLOps 観点を含む複数のインフラ構成パターン** を設計・比較します。

#### 設計テーマ

* 学習・推論・評価を分離したアーキテクチャ
* 再現性・コスト・障害耐性のバランス
* 実運用を想定した MLOps パイプライン設計

#### 提供する構成パターン

* Simple Architecture（プロトタイプ向け）
* Cost Optimized Architecture
* High Availability Architecture
* Resilient by Design Architecture
* MLOps Pipeline Architecture

**対応クラウド**: AWS / Azure / GCP

---

### 2. Search Autocomplete System

`search_autocomplete_system/`

高速検索オートコンプリート機能を題材に、
**レイテンシ要件とコスト制約を満たす設計** を検証します。

* **目標要件**

  * P95 レイテンシ < 200ms
  * 月額コスト < $150

#### 設計ポイント

* 多層キャッシュ戦略（Browser / CDN / Redis / OpenSearch）
* スケール時のボトルネック分析
* 実運用を想定した構成のシンプル化

#### 技術スタック

* Frontend: Next.js, TypeScript, React
* Backend: Python, Flask
* Database: PostgreSQL, Redis, OpenSearch
* Infrastructure: AWS（CloudFront, ALB, ECS, RDS, ElastiCache）

Docker Compose により **ローカルで動作確認可能**。

---

### 3. Cache Strategy

`cache_strategy/`

動画配信サービスを題材に、
**CDN・アプリケーションキャッシュの設計判断** を学習・検証します。

#### 主な検証内容

* CDN キャッシュとオリジン負荷の関係
* 静的 / 動的コンテンツのキャッシュ戦略
* Cache-Control ヘッダー設計の実践

---

### 4. Distributed ID Generation

`distributed_id_generation_design/`

分散システムにおける **ID生成方式の設計と実装比較** を行います。

#### 実装・検証内容

* Snowflake アルゴリズム
* Ticket Server パターン
* スケール・衝突・運用面の比較

Docker Compose による動作確認・検証環境を含みます。

---

## 🛠️ 実行方法（例）

### 前提条件

* Docker / Docker Compose
* Node.js（フロントエンド実行時）
* Python 3.x（バックエンド実行時）

```bash
git clone https://github.com/sugiyama404/practice_infra_arch.git
cd practice_infra_arch
```

### Search Autocomplete System

```bash
cd search_autocomplete_system
docker-compose up -d
```

### Distributed ID Generation

```bash
cd distributed_id_generation_design
docker-compose up -d
```

---

## 📖 設計ドキュメント構成

各プロジェクトには以下の設計資料を含みます。

* `initial_assumptions.md`

  * 想定ユースケース / 要件 / 制約条件
* `infrastructure.md`

  * アーキテクチャ構成と設計意図
* `README.md`

  * プロジェクト固有の説明と検証方法

---

## 🎨 アーキテクチャ図

* Draw.io（`.drawio`）
* PNG / SVG

を含め、**視覚的に設計判断を追える構成**になっています。

---

## 📚 カバーする技術領域

* **クラウド**: AWS / Azure / GCP
* **コンテナ**: Docker, ECS, Kubernetes
* **データストア**: RDS, DynamoDB, Redis, OpenSearch
* **キャッシュ**: CDN, Application Cache
* **可観測性**: CloudWatch, APM
* **セキュリティ**: IAM, VPC, Security Group
* **トラフィック制御**: ALB, CloudFront, Route53

---

## 🎯 このリポジトリのゴール

* 実務で「なぜその設計にしたか」を説明できる状態になること
* スケーラブル・可用性・コストを意識した設計判断ができること
* クラウド / 分散システム設計の引き出しを増やすこと
