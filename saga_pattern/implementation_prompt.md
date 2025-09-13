# Sagaパターン実装プロンプト

## 概要
CloudMartオンライン書店システムのSagaパターン（ChoreographyとOrchestration）をPython + FastAPIで実装してください。

## 技術スタック
- **言語**: Python 3.11+
- **フレームワーク**: FastAPI
- **ORM**: SQLAlchemy
- **DB**: MySQL 8.0
- **メッセージング**:
  - Choreography: Redis (Pub/Sub)
  - Orchestration: RabbitMQ
- **コンテナ化**: Docker + Docker Compose

## システム構成

### 共通サービス
1. **Order Service** (Port: 8001)
2. **Inventory Service** (Port: 8002)
3. **Payment Service** (Port: 8003)
4. **Shipping Service** (Port: 8004)

### Choreography専用
5. **Event Bus** (Redis: 6379)

### Orchestration専用
6. **Saga Orchestrator** (Port: 8005)
7. **Message Broker** (RabbitMQ: 5672)

## データベーススキーマ
以下のテーブルを実装（init.sql参照）：
- customers, books, inventory, orders, order_items, payments, shipments
- saga_instances, saga_step_logs (Orchestration用)

## Choreographyパターン実装

### イベントフロー
1. OrderCreated → Inventory Service (StockReserved/StockUnavailable)
2. OrderCreated → Payment Service (PaymentCompleted/PaymentFailed)
3. StockReserved + PaymentCompleted → Shipping Service (ShippingArranged/ShippingFailed)

### 補償イベント
- StockUnavailable → Payment Service (PaymentCancelled)
- PaymentFailed → Inventory Service (StockReleased)
- ShippingFailed → Payment Service (PaymentRefunded) + Inventory Service (StockReleased)

### 実装要件
- Redis Pub/Subを使用した非同期イベント処理
- 各サービスが自律的にイベントをpublish/subscribe
- イベントの順序保証と重複処理防止
- 補償処理の自動実行

## Orchestrationパターン実装

### ワークフロー定義
```python
ORDER_WORKFLOW = {
    "steps": [
        {"service": "order", "command": "create_order", "compensation": "cancel_order"},
        {"service": "inventory", "command": "reserve_stock", "compensation": "release_stock"},
        {"service": "payment", "command": "process_payment", "compensation": "cancel_payment"},
        {"service": "shipping", "command": "arrange_shipping", "compensation": "cancel_shipping"}
    ]
}
```

### Saga状態管理
- STARTED → ORDER_CREATED → STOCK_RESERVED → PAYMENT_COMPLETED → SHIPPING_ARRANGED → COMPLETED
- 失敗時: COMPENSATION_STARTED → 逆順補償 → FAILED

### 実装要件
- RabbitMQを使用した同期コマンド/レスポンス
- Saga Orchestratorがワークフロー全体を制御
- ステップごとのログ記録（saga_step_logs）
- 自動補償処理とリトライ機能

## 各サービスのAPI仕様

### Order Service
- POST /orders - 注文作成
- GET /orders/{order_id} - 注文取得
- PUT /orders/{order_id}/cancel - 注文キャンセル

### Inventory Service
- POST /inventory/reserve - 在庫予約
- POST /inventory/release - 在庫解放
- GET /inventory/{book_id} - 在庫確認

### Payment Service
- POST /payments/process - 決済処理
- POST /payments/cancel - 決済キャンセル
- POST /payments/refund - 返金処理

### Shipping Service
- POST /shipping/arrange - 配送手配
- POST /shipping/cancel - 配送キャンセル
- GET /shipping/{order_id} - 配送状態確認

### Saga Orchestrator (Orchestrationのみ)
- POST /saga/start - Saga開始
- GET /saga/{order_id}/status - Saga状態確認
- POST /saga/{order_id}/cancel - Saga手動キャンセル

## テストケース実装

### 正常フロー
1. 在庫あり、決済成功、配送成功
2. 複数商品の注文処理

### 異常フロー
1. 在庫不足時のロールバック
2. 決済失敗時のロールバック
3. 配送失敗時のロールバック
4. 部分的な失敗と補償

### 同時実行テスト
1. 複数注文の同時処理
2. 在庫競合時の処理
3. 決済同時実行時の整合性

## 実装のポイント

### 1. エラーハンドリング
- ネットワークエラー時のリトライ
- タイムアウト処理
- デッドロック防止

### 2. トランザクション管理
- サービス内でのACID保証
- 分散トランザクションの結果整合性
- 補償トランザクションの原子性

### 3. 監視・ログ
- 各サービスの詳細ログ
- パフォーマンスメトリクス
- エラートレース

### 4. 設定管理
- 環境別設定（dev/prod）
- 接続情報の一元管理
- タイムアウト値の調整

## ディレクトリ構造
```
saga_pattern/
├── choreography_pattern/
│   ├── docker-compose.yml
│   ├── order_service/
│   │   ├── app.py, requirements.txt, Dockerfile
│   ├── inventory_service/
│   ├── payment_service/
│   ├── shipping_service/
│   └── event_bus/
├── orchestration_pattern/
│   ├── docker-compose.yml
│   ├── saga_orchestrator/
│   ├── order_service/
│   ├── inventory_service/
│   ├── payment_service/
│   ├── shipping_service/
│   └── message_broker/
└── shared/
    ├── models.py (共通DBモデル)
    ├── config.py (設定)
    └── utils.py (共通ユーティリティ)
```

## 実行方法
1. Docker Composeで全サービス起動
2. テストスクリプトで各パターンの検証
3. Jupyter Notebookでパフォーマンス分析

## 品質基準
- ユニットテストカバレッジ80%以上
- レスポンス時間 < 500ms
- エラー率 < 1%
- ロールバック成功率 100%</content>
<parameter name="filePath">/Users/codefox/workspace/practice_infra_arch/saga_pattern/implementation_prompt.md
