# 実行手順書

## 1. 環境セットアップ

```bash
# プロジェクトディレクトリに移動
cd /Users/codefox/workspace/practice_infra_arch/search_autocomplete_system

# Docker Composeでサービスを起動
docker-compose up --build
```

## 2. アクセス確認

起動後、以下のURLにアクセスできます：

- **Frontend (Next.js)**: http://localhost:3000
- **Backend API (Flask)**: http://localhost:5000
- **MySQL**: localhost:3306

## 3. 動作確認

### 3.1 ヘルスチェック
```bash
curl http://localhost:5000/api/health
```

### 3.2 検索API
```bash
curl "http://localhost:5000/api/search?q=Ja"
```

### 3.3 人気ワードAPI
```bash
curl "http://localhost:5000/api/popular?limit=5"
```

## 4. 開発モード（個別起動）

### 4.1 MySQL起動
```bash
docker-compose up mysql -d
```

### 4.2 Backend開発
```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL="mysql+pymysql://search_user:password123@localhost:3306/search_db"
python app.py
```

### 4.3 Frontend開発
```bash
cd frontend
npm install
npm run dev
```

## 5. トラブルシューティング

### 5.1 ポート競合
```bash
# 使用中のポートを確認
lsof -i :3000
lsof -i :5000
lsof -i :3306

# プロセス終了
kill -9 <PID>
```

### 5.2 Docker問題
```bash
# コンテナとボリュームのクリーンアップ
docker-compose down -v
docker system prune -f

# 再ビルド
docker-compose up --build
```

### 5.3 データベース問題
```bash
# MySQLコンテナに接続
docker exec -it search_mysql mysql -u search_user -p

# データベース確認
USE search_db;
SHOW TABLES;
SELECT COUNT(*) FROM search_terms;
```

## 6. カスタマイズ方法

### 6.1 検索データ追加
`database/init.sql` を編集して検索データを追加

### 6.2 UI変更
`frontend/src/` 内のコンポーネントを編集

### 6.3 API拡張
`backend/app.py` にエンドポイントを追加
