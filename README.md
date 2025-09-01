# インフラ設計練習プロジェクト

このリポジトリは、様々なシステムのインフラ設計を学習・練習するためのプロジェクトです。実際のユースケースを想定したアーキテクチャ設計と実装例を提供します。

## 📁 プロジェクト構成

### 🎯 システム設計事例

#### 1. ML Trading System (`ml_trading_system/`)
機械学習を活用したトレーディングシステムの設計パターン

- **Simple Architecture**: プロトタイプ向けの最小構成
- **Cost Optimized Architecture**: コスト最適化重視の構成
- **High Availability Architecture**: 高可用性重視の構成
- **Resilient by Design Architecture**: 障害耐性重視の構成
- **MLOps Pipeline Architecture**: MLOps パイプライン構成

対応クラウド: AWS, Azure, GCP

#### 2. Search Autocomplete System (`search_autocomplete_system/`)
高速検索オートコンプリート機能の実装

**目標**: P95 < 200ms / 月額 < $150

**特徴**:
- 多層キャッシュ戦略 (Browser/CloudFront/Redis/OpenSearch)
- 実際に動作するDocker構成付き
- フロントエンド (Next.js) + バックエンド (Python/Flask) の完全な実装

**技術スタック**:
- Frontend: Next.js, TypeScript, React
- Backend: Python, Flask
- Database: PostgreSQL, Redis, OpenSearch
- Infrastructure: AWS (CloudFront, ALB, ECS, RDS, ElastiCache)

#### 3. Cache Strategy (`cache_strategy/`)
動画配信サイトを題材にしたキャッシュ戦略の学習

**学習ポイント**:
- CloudFront を活用した CDN キャッシュ
- 静的/動的コンテンツの適切なキャッシュ設定
- Cache-Control ヘッダーの実践的な使い方

#### 4. Distributed ID Generation (`distributed_id_generation_design/`)
分散システムでのID生成システム設計

**実装内容**:
- Snowflake アルゴリズムの実装
- Ticket Server パターンの実装
- Docker Compose による動作確認環境

## 🛠️ 使用方法

### 前提条件
- Docker & Docker Compose
- Node.js (フロントエンド開発時)
- Python 3.x (バックエンド開発時)

### クイックスタート

1. **リポジトリのクローン**
```bash
git clone https://github.com/sugiyama404/practice_infra_arch.git
cd practice_infra_arch
```

2. **検索オートコンプリートシステムの起動例**
```bash
cd search_autocomplete_system
docker-compose up -d
```

3. **分散ID生成システムの起動例**
```bash
cd distributed_id_generation_design
docker-compose up -d
```

## 📖 設計ドキュメント

各プロジェクトには以下のドキュメントが含まれています：

- `infrastructure.md`: システム構成とアーキテクチャの詳細
- `initial_assumptions.md`: 設計の前提条件と要件
- `README.md`: プロジェクト固有の説明とセットアップ手順

## 🎨 アーキテクチャ図

各プロジェクトにはDraw.ioファイル（`.drawio`）と画像ファイル（`.png`, `.svg`）が含まれており、視覚的にアーキテクチャを理解できます。

## 📚 学習リソース

### 設計テンプレート
`infra_design_template.md` - インフラ設計時に使用できる統一テンプレート

### カバーする技術領域
- **クラウドサービス**: AWS, Azure, GCP
- **コンテナ技術**: Docker, ECS, Kubernetes
- **データベース**: RDS, DynamoDB, Redis, OpenSearch
- **キャッシュ戦略**: CDN, アプリケーションレベルキャッシュ
- **監視・ログ**: CloudWatch, Application Performance Monitoring
- **セキュリティ**: IAM, VPC, セキュリティグループ
- **負荷分散**: ALB, CloudFront, Route53

## 🤝 コントリビューション

新しいシステム設計例や改善案は歓迎します！

1. Issue で提案内容を議論
2. Fork & ブランチ作成
3. 設計ドキュメント & 実装を追加
4. Pull Request を作成

## 📄 ライセンス

This project is open source and available under the [MIT License](LICENSE).

---

**🎯 学習目標**: 実践的なインフラ設計スキルの習得と、スケーラブル・コスト効率的・可用性の高いシステム構築の理解