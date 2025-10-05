# Rate Limiter System

## 📋 Overview

**固定ウィンドウカウンター方式（Fixed Window Counter）**を採用した分散レートリミッターシステムです。

Flask × Redis × Docker Composeを使用し、一定時間内のAPIリクエスト数を制限することで、システムの過負荷・不正アクセス・スパイクトラフィックを防止します。

### Key Features

- ✅ **シンプルな実装**: RedisのINCRとEXPIREのみ
- ✅ **高速処理**: O(1)の時間計算量
- ✅ **分散対応**: Redis共有でマルチインスタンス対応
- ✅ **自動クリーンアップ**: TTLで古いデータ自動削除
- ✅ **標準準拠**: HTTP 429とRate Limit Headers

## 🏗 Architecture

```
Client → Flask API (:8000) → Redis (:6379)
           ↓
    Rate Limit Check
    (INCR + EXPIRE)
           ↓
    200 OK / 429 Too Many Requests
```

詳細なアーキテクチャ図は [docs/architecture.md](docs/architecture.md) を参照してください。

## 📁 Project Structure

```
rate_limiter_design/
├── app/
│   ├── Dockerfile              # Flaskアプリ用Dockerfile
│   ├── main.py                 # Flask API実装
│   └── requirements.txt        # Python依存関係
├── docs/
│   └── architecture.md         # システムアーキテクチャ詳細
├── compose.yaml                # Docker Compose設定
├── rate_limiter_test.ipynb     # テスト・検証Notebook
└── README.md                   # このファイル
```

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (macOS)
- Python 3.10以上
- Jupyter Notebook

### 1. Start Services

```bash
# リポジトリのrate_limiter_designディレクトリに移動
cd rate_limiter_design

# Docker Composeでサービスを起動
docker compose up --build
```

起動後、以下のサービスが利用可能になります:
- Flask API: `http://localhost:8000`
- Redis: `localhost:6379`

### 2. Health Check

ブラウザまたはcurlでヘルスチェック:

```bash
curl http://localhost:8000/health
```

期待されるレスポンス:
```json
{
  "status": "healthy",
  "redis": "connected"
}
```

### 3. Test Rate Limiter

#### Manual Test (curl)

```bash
# 5回まで成功
curl -i http://localhost:8000/api/test

# 6回目で429エラー
curl -i http://localhost:8000/api/test
```

#### Automated Test (Jupyter Notebook)

```bash
# Jupyter Notebook起動
jupyter notebook rate_limiter_test.ipynb
```

Notebook内で以下を実行:
1. セルを順番に実行
2. 自動的に10回のリクエストを送信
3. 結果をグラフで可視化

## 🎯 API Endpoints

### `GET /health`
ヘルスチェックエンドポイント（レート制限対象外）

**Response:**
```json
{
  "status": "healthy",
  "redis": "connected"
}
```

### `GET /api/test`
テスト用エンドポイント（レート制限対象）

**Success Response (200 OK):**
```json
{
  "message": "Request successful",
  "client_ip": "172.18.0.1",
  "timestamp": 1696500045
}
```

**Rate Limited Response (429 Too Many Requests):**
```json
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded. Try again in 30 seconds."
}
```

**Response Headers:**
- `X-RateLimit-Limit`: 5
- `X-RateLimit-Remaining`: 0
- `X-RateLimit-Reset`: 1696500060
- `Retry-After`: 30

### `POST /api/reset`
レート制限リセット（テスト用）

**Response:**
```json
{
  "message": "Rate limit reset successfully",
  "deleted_keys": 1
}
```

## ⚙️ Configuration

環境変数でレート制限設定をカスタマイズ可能（`compose.yaml`）:

```yaml
environment:
  - REDIS_HOST=redis
  - REDIS_PORT=6379
  - RATE_LIMIT=5          # 制限リクエスト数
  - WINDOW_SECONDS=60     # ウィンドウ時間（秒）
```

## 🔧 Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Framework | Flask 3.0 | 軽量APIサーバー |
| Data Store | Redis 5.0 | インメモリKVS |
| Container | Docker Compose | オーケストレーション |
| Language | Python 3.10 | アプリケーション実装 |
| Testing | Jupyter Notebook | 検証・可視化 |

### Why These Technologies?

#### Flask
- 軽量でシンプル
- Pythonエコシステム
- 高速なプロトタイピング

#### Redis
- アトミック操作（INCR）保証
- TTL自動管理（EXPIRE）
- 高速（インメモリ）
- 分散環境対応

#### Fixed Window Counter
- 実装が最もシンプル
- 低レイテンシ
- メモリ効率が良い

## 📊 Test Results

Jupyter Notebookでの検証結果例:

| Request | Status | Remaining | Response Time |
|---------|--------|-----------|---------------|
| 1 | 200 | 4 | 12ms |
| 2 | 200 | 3 | 8ms |
| 3 | 200 | 2 | 9ms |
| 4 | 200 | 1 | 10ms |
| 5 | 200 | 0 | 11ms |
| 6 | 429 | 0 | 7ms |
| 7 | 429 | 0 | 6ms |

## 🛠 Troubleshooting

### Docker起動エラー

```bash
# コンテナとボリュームを削除して再起動
docker compose down -v
docker compose up --build
```

### Redis接続エラー

```bash
# Redisコンテナの状態確認
docker compose ps

# Redisログ確認
docker compose logs redis
```

### ポート8000が使用中

```bash
# ポート使用状況確認
lsof -i :8000

# compose.yamlでポート変更
ports:
  - "8001:8000"  # 8001に変更
```

## 🔒 Security Considerations

### Development Environment
✅ 現在の設定（開発用）

### Production Environment
本番環境では以下を実装してください:

1. **Redis認証**
   ```yaml
   command: redis-server --requirepass <strong_password>
   ```

2. **TLS/SSL**
   - HTTPS通信の有効化
   - Redis TLS接続

3. **IP検証強化**
   - プロキシヘッダー検証
   - 信頼できるIPレンジ制限

4. **監視・ログ**
   - Prometheus/Grafanaメトリクス
   - ELKスタックログ集約
   - アラート設定

## 📈 Scaling Strategy

### Horizontal Scaling

```yaml
app:
  deploy:
    replicas: 3  # Flask複数インスタンス
```

全インスタンスが同じRedisを共有するため、レート制限は統一されます。

### Redis High Availability

- **Redis Sentinel**: 自動フェイルオーバー
- **Redis Cluster**: シャーディング
- **Redis Enterprise**: マネージドサービス

## 🎓 Learning Resources

### Fixed Window Counter Algorithm

詳細は [docs/architecture.md](docs/architecture.md) の「Fixed Window Counter - Deep Dive」セクションを参照。

### Alternative Algorithms

| Algorithm | Pros | Cons |
|-----------|------|------|
| Fixed Window | シンプル、高速 | バースト発生 |
| Sliding Window Log | 正確 | メモリ消費大 |
| Token Bucket | 柔軟 | 複雑 |

## 🧪 Development

### Run Tests

```bash
# Notebook形式でテスト
jupyter notebook rate_limiter_test.ipynb

# または手動テスト
for i in {1..10}; do
  curl -i http://localhost:8000/api/test
  sleep 1
done
```

### Add New Features

1. `app/main.py`を編集
2. `docker compose up --build`で再ビルド
3. Notebookで検証

## 📝 License

MIT License

## 👥 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📧 Contact

質問・バグ報告は Issues にて受け付けています。

---

**🎉 Enjoy Rate Limiting with Flask & Redis!**
