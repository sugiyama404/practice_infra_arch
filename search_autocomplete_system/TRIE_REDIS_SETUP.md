# 検索オートコンプリートシステム（Trie + Redis キャッシュ版）

高性能な検索オートコンプリートシステムです。トライ木（Trie）構造によるインメモリ検索と、Redisキャッシュによる低レイテンシ化を実現しています。

## アーキテクチャ

### 主要コンポーネント
- **フロントエンド**: Next.js (TypeScript)
- **バックエンド**: Flask (Python) + カスタムTrie実装
- **キャッシュ**: Redis
- **データベース**: MySQL

### 検索フロー
1. フロントエンドから検索クエリを送信
2. バックエンドでRedisキャッシュを確認
3. キャッシュヒット時は即座に結果を返却
4. キャッシュミス時はTrieで高速プレフィックス検索を実行
5. 検索結果をキャッシュに保存して返却

## 技術的特徴

### Trie（トライ木）検索
- 起動時にデータベースから全検索用語をメモリ上のTrie構造にロード
- O(m)の時間計算量でプレフィックス検索を実行（mはクエリ長）
- 人気度スコア順で候補をソート
- SQL LIKE検索と比較して大幅な性能向上

### Redisキャッシュ
- 検索結果をキャッシュして応答時間を最小化
- TTL（Time To Live）設定でキャッシュ有効期限を管理
  - 検索結果: 1分
  - 人気ワード: 5分
- キャッシュヒット率の監視機能

### 管理機能
- Trie再構築API（`/api/admin/rebuild-trie`）
- キャッシュクリアAPI（`/api/admin/clear-cache`）
- システム統計情報API（`/api/admin/stats`）

## セットアップ

### 1. システム起動
```bash
# プロジェクトディレクトリに移動
cd search_autocomplete_system

# Docker Composeでサービス一括起動
docker compose up --build
```

### 2. アクセス確認
- フロントエンド: http://localhost:3000
- バックエンドAPI: http://localhost:8000
- MySQL: localhost:3306
- Redis: localhost:6379

### 3. ヘルスチェック
```bash
curl http://localhost:8000/api/health
```

## API仕様

### 検索オートコンプリート
```
GET /api/search?q={query}&limit={limit}
```
**パラメータ:**
- `q`: 検索クエリ（必須）
- `limit`: 取得件数（デフォルト: 10）

**レスポンス:**
```json
{
  "suggestions": [
    {
      "term": "JavaScript",
      "category": "Programming",
      "popularity": 95
    }
  ]
}
```

### 人気検索ワード
```
GET /api/popular?limit={limit}
```
**パラメータ:**
- `limit`: 取得件数（デフォルト: 10）

**レスポンス:**
```json
{
  "popular_terms": [
    {
      "term": "JavaScript",
      "category": "Programming", 
      "popularity": 95
    }
  ]
}
```

### 検索履歴保存
```
POST /api/history
Content-Type: application/json

{
  "term": "JavaScript",
  "session": "user_session_id"
}
```

### 管理用API

#### Trie再構築
```
POST /api/admin/rebuild-trie
```

#### キャッシュクリア
```
POST /api/admin/clear-cache
```

#### システム統計
```
GET /api/admin/stats
```

## 依存パッケージ

### Backend (Python)
- Flask==2.3.3
- flask-cors==4.0.0
- SQLAlchemy==2.0.21
- PyMySQL==1.1.0
- redis==5.0.1
- pytrie==0.4.0

### Frontend (Next.js)
- 既存のNext.jsプロジェクトをそのまま利用

## 監視とメンテナンス

### パフォーマンス監視
```bash
# システム統計確認
curl http://localhost:8000/api/admin/stats

# Redisキャッシュヒット率確認
docker exec search_redis redis-cli info stats
```

### データ更新時の手順
1. データベースに新しい検索用語を追加
2. Trie再構築APIを呼び出し
```bash
curl -X POST http://localhost:8000/api/admin/rebuild-trie
```

### トラブルシューティング
- Redis接続エラー時はキャッシュ機能が無効化され、Trie検索のみで動作
- データベース接続エラー時はアプリケーションが起動しない
- Trie構築エラー時は空のTrieで動作（検索結果なし）

## 性能特性

### 検索性能
- **Trie検索**: O(m) - mはクエリ長
- **結果ソート**: O(n log n) - nは候補数
- **キャッシュヒット時**: O(1)

### メモリ使用量
- Trie構造: 検索用語数 × 平均文字数に比例
- Redis: キャッシュサイズに依存

### 推奨システム要件
- RAM: 最小1GB（10万用語程度の場合）
- Redis: 最小256MB
- CPU: マルチコア推奨（並行リクエスト処理用）
