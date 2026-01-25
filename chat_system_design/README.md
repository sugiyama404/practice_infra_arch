# Chat System Design

## 📌 プロジェクト概要

このプロジェクトは、リアルタイムチャットシステムの **参考実装** です。
`docker-compose` を用いて、複数サービスを起動し、メッセージの送受信・配信・同期を行うアーキテクチャを再現します。

本構成は以下の特徴を持ちます：

* **リアルタイム通信**: WebSocket を利用
* **スケーラブル設計**: API サーバは stateless、WebSocket サーバは stateful
* **非同期処理**: メッセージはキューに送信 → Worker が処理
* **マルチデバイス同期**: 各デバイスごとにメッセージ ID を管理
* **高可用性**: Redis, RabbitMQ, Postgres による耐障害設計
* **モジュール化**: Push通知サーバはモックで差し替え可能

---

## 🏗️ システムアーキテクチャ

```
 ┌───────────┐      ┌───────────┐
 │  Client A │      │  Client B │
 └─────┬─────┘      └─────┬─────┘
       │ WebSocket / HTTP        │
       ▼                         ▼
 ┌─────────────┐     ┌─────────────┐
 │ UI Server   │  ...│ UI Server   │
 │ (Next.js)   │     │ (Next.js)   │
 └─────┬───────┘     └─────┬───────┘
       │                         │
 ┌─────────────┐     ┌─────────────┐
 │   Nginx LB   │  ...│   Nginx LB   │
 └─────┬────────┘     └─────┬───────┘
       │                         │
 ┌─────────────┐       ┌─────────────┐
 │  API Server │       │  WS Server  │ (複数)
 │  (FastAPI)  │       │ (FastAPI+WS)│
 └─────┬───────┘       └─────┬───────┘
       │  HTTP REST           │  WS Pub/Sub
       ▼                      ▼
 ┌─────────────┐       ┌─────────────┐
 │  RabbitMQ    │◀────▶│   Worker     │
 └─────┬───────┘       └─────┬───────┘
       │                      │
 ┌─────────────┐       ┌─────────────┐
 │   Redis      │       │  Postgres    │
 │  (Session,   │       │ (Message DB) │
 │  Presence,   │       └─────────────┘
 │  ID管理)     │
 └─────────────┘
       │
 ┌─────────────┐
 │ Push Server │ (Mock: ログ出力)
 └─────────────┘
```

---

## 🔑 コンポーネント解説

### 1. **UI Server (Next.js)**

* クライアントにチャットUIを提供（SSRモード）
* APIサーバーへのHTTPリクエスト、WebSocket接続を仲介
* リアルタイムチャットインターフェースを実装

### 2. **Nginx (Load Balancer)**

* クライアントからの接続を WebSocket サーバへ振り分ける
* API サーバへのリクエストもプロキシ

### 3. **API Server (FastAPI)**

* ユーザー登録、認証、履歴取得 API を提供
* デバイスごとの `cur_max_message_id` を管理

### 4. **WebSocket Server (FastAPI + WS)**

* クライアントと常時接続
* メッセージ送信を RabbitMQ に流し、Worker からの配信を待つ
* Redis でセッション管理

### 5. **Worker (Python, aio\_pika)**

* RabbitMQ からメッセージを受信
* Postgres に保存
* Redis を更新（`message_id`, プレゼンス情報）
* WebSocket サーバへ配信

### 6. **Redis**

* プレゼンス（オンライン/オフライン状態）
* セッション管理（`user_id:device_id → ws_server`）
* ID 発行（`INCR message_id`）
* デバイスごとの `cur_max_message_id`

### 7. **Postgres**

* メッセージ履歴、ユーザー情報を永続化

### 8. **RabbitMQ**

* 非同期メッセージ処理のためのキュー

### 9. **Push Notification Server (Mock)**

* Worker から通知を受け取り、ログに出力（実サービスに置き換え可能）

---

## 🚀 起動方法

```bash
cd chat_system_design
docker compose up --build
```

---

## 📂 ディレクトリ構成

```
chat_system_design/
├── compose.yaml
├── init.sql
├── Makefile
├── nginx.conf
├── README.md
├── requirements_local.txt
├── test_client.py
├── ui_prompt.md
├── api/
│   ├── config.py
│   ├── Dockerfile
│   ├── main.py
│   ├── models.py
│   └── requirements.txt
├── pn/
│   ├── config.py
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── ui/
│   ├── Dockerfile
│   ├── jest.config.js
│   └── ...
├── worker/
│   └── ws/
```

---

## 🔄 メッセージの流れ

1. ユーザーが WebSocket でメッセージ送信
2. WS サーバが RabbitMQ に publish
3. Worker が RabbitMQ から consume
4. Worker が Postgres 保存 + Redis 更新
5. Worker が各 WS サーバへ配信
6. WS サーバが対象クライアントへ送信
7. Push Server が通知をログ出力

---

## ✨ 特徴まとめ

* **リアルタイム性**: WS による即時通信
* **信頼性**: Redis + Postgres によるデータ保持
* **スケーラブル**: WS サーバの水平スケール
* **マルチデバイス対応**: `cur_max_message_id` による同期
