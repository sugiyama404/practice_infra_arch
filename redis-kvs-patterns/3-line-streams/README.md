# 3-line-streams

## 概要
LINE風のRedis Streams永続化メッセージングシステム実装例。Consumer Groupによる並列処理、順序保証、障害復旧・フェイルオーバー・重複検知・容量制限を備えています。

## 構成
- Redis（docker-composeで起動）
- Python/Flask APIサーバ（app.py/stream_server.py）

## 機能
- Redis Streamsによる永続化メッセージキュー
- Consumer Groupによる並列メッセージ処理
- メッセージの順序保証とIDベース管理
- 未処理メッセージの自動再配信
- Consumer障害時の自動フェイルオーバー
- メッセージの重複処理検知
- ストリーム容量制限とトリミング

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
- `/produce` メッセージ送信
- `/consume` Consumer Groupで並列取得
- `/pending` 未処理一覧
- `/replay` 未処理再配信
- `/trim` 容量制限
- `/group_info` Consumer Group情報
- `/stream_info` ストリーム情報

## テスト手順
1. `/produce`で複数メッセージ送信
2. `/consume`で複数Consumer並列取得・順序保証確認
3. `/pending`・`/replay`で未処理・再配信挙動確認
4. Consumer停止時の自動フェイルオーバー（ログ出力）確認
5. `/trim`で容量制限・トリミング確認

## Streamsアーキテクチャ解説
- Redis StreamsはIDベースで順序・永続性を保証
- Consumer Groupで高スループット・障害復旧
- 未処理・重複・容量制限もAPIで管理可能
