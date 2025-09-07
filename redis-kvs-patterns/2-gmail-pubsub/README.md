# 2-gmail-pubsub

## 概要
GmailライクなPub/Subリアルタイム通知システムの実装例。Redis Pub/SubとWebSocketを活用し、複数トピック・購読者管理・メッセージフィルタ・バックプレッシャー対応を備えています。

## 構成
- Redis（docker-composeで起動）
- Python/Flask + Flask-SocketIO APIサーバ（app.py/pubsub_server.py）

## 機能
- Redis Pub/Subによるリアルタイム通知
- 複数トピック管理（email, calendar, drive等）
- 購読者の動的登録・解除
- メッセージフィルタリング
- 購読者別の配信状況追跡
- WebSocketによるリアルタイム配信
- バックプレッシャー対応（配信遅延処理）

## 起動方法
1. Redis起動
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
- WebSocket: `subscribe`, `unsubscribe`, `set_filter`, `status` イベント
- REST: `/publish`, `/topics`, `/subscribers`, `/delivery_status`

## テスト手順
1. WebSocketクライアントでトピック購読・解除
2. `/publish`でメッセージ送信、フィルタ・バックプレッシャー挙動確認
3. `/delivery_status`で配信状況追跡

## 設計思想
- Redis Pub/Subで高スループット・低遅延通知
- WebSocketでリアルタイム配信
- 購読者ごとにフィルタ・配信状況・遅延処理を管理
- 動的な購読・解除・トピック追加が容易
