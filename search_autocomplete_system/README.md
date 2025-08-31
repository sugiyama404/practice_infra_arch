# Search Autocomplete System

Next.js + Flask + MySQL構成の検索オートコンプリートシステム

## 構成

- **Frontend**: Next.js (React) - ポート 3000
- **Backend**: Flask API - ポート 5000  
- **Database**: MySQL 8.0 - ポート 3306

## セットアップ

1. プロジェクトのクローン後、このディレクトリに移動
```bash
cd search_autocomplete_system
```

2. Docker Composeでサービスを起動
```bash
docker-compose up --build
```

3. アクセス
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- MySQL: localhost:3306

## 開発

### Backend (Flask)
```bash
cd backend
pip install -r requirements.txt
flask run --host=0.0.0.0
```

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```

## API エンドポイント

- `GET /api/search?q={query}` - 検索候補を取得
- `GET /api/health` - ヘルスチェック

## 機能

- リアルタイム検索オートコンプリート
- デバウンス機能
- キーボードナビゲーション
- 検索履歴
- 人気検索ワード表示
