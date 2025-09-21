# Saga Orchestration Pattern Demo

## 概要
Orchestrationパターンは、中央集権的なオーケストレーター（Saga Manager）が全体のワークフローを制御し、各サービスに対して明示的にコマンドを送信してトランザクションを管理するSagaパターンです。

## ディレクトリ構造
```
saga-orchestration-demo/
├── docker-compose.yml
├── README.md
├── saga-orchestrator/
│   ├── app.js
│   ├── workflows/
│   │   └── orderWorkflow.js
│   ├── package.json
│   └── Dockerfile
├── order-service/
│   ├── app.js
│   ├── package.json
│   └── Dockerfile
├── payment-service/
│   ├── app.js
│   ├── package.json
│   └── Dockerfile
├── inventory-service/
│   ├── app.js
│   ├── package.json
│   └── Dockerfile
├── shipping-service/
│   ├── app.js
│   ├── package.json
│   └── Dockerfile
└── message-broker/
    └── rabbitmq.conf
```

## システム構成図

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Saga Orchestration Pattern                          │
└─────────────────────────────────────────────────────────────────────────────┘

                         ┌─────────────────────┐
                         │ Saga Orchestrator   │
                         │ (Workflow Engine)   │
                         │                     │
                         │ ┌─────────────────┐ │
                         │ │Order Workflow   │ │
                         │ │State Machine    │ │
                         │ └─────────────────┘ │
                         └─────────────────────┘
                                     │
                         ┌─────────────────────┐
                         │   Message Broker    │
                         │    (RabbitMQ)       │
                         └─────────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌──────────────┐            ┌──────────────┐            ┌──────────────┐
│Order Service │            │Payment       │            │Inventory     │
│              │            │Service       │            │Service       │
│Commands:     │            │              │            │              │
│- CreateOrder │            │Commands:     │            │Commands:     │
│- CancelOrder │            │- ProcessPay  │            │- ReserveStock│
│              │            │- CancelPay   │            │- ReleaseStock│
└──────────────┘            └──────────────┘            └──────────────┘
        │                            │                            │
        └────────────────────────────┼────────────────────────────┘
                                     │
                              ┌──────────────┐
                              │Shipping      │
                              │Service       │
                              │              │
                              │Commands:     │
                              │- CreateShip  │
                              │- CancelShip  │
                              └──────────────┘

コマンドフロー (Orchestrator制御):
1. CreateOrder → OrderService
2. ProcessPayment → PaymentService
3. ReserveStock → InventoryService
4. CreateShipment → ShippingService
5. 失敗時: 逆順でCancel系コマンド実行
```

## 特徴

### メリット
- **中央制御**: ワークフロー全体を一箇所で管理
- **明確な流れ**: 実行順序とビジネスロジックが明確
- **デバッグ容易**: 中央のログで全体の流れを追跡可能
- **複雑なロジック対応**: 条件分岐や並行処理が実装しやすい

### デメリット
- **単一障害点**: オーケストレーターがSPOFになる可能性
- **密結合**: オーケストレーターが全サービスを知る必要がある
- **スケールの制約**: オーケストレーターがボトルネックになる可能性

## セットアップ

1. Dockerコンテナ起動
```bash
docker-compose up -d
```

2. 注文処理開始
```bash
curl -X POST http://localhost:3000/saga/start \
  -H "Content-Type: application/json" \
  -d '{"orderId": "order-123", "productId": "item-001", "quantity": 2, "amount": 1000}'
```

3. Saga状態確認
```bash
curl http://localhost:3000/saga/order-123/status
```

4. ログ確認
```bash
docker-compose logs -f saga-orchestrator
```

## ワークフロー定義

### 正常フロー
```javascript
const orderWorkflow = {
  steps: [
    { service: 'order', command: 'createOrder' },
    { service: 'payment', command: 'processPayment' },
    { service: 'inventory', command: 'reserveStock' },
    { service: 'shipping', command: 'createShipment' }
  ],
  compensations: [
    { service: 'shipping', command: 'cancelShipment' },
    { service: 'inventory', command: 'releaseStock' },
    { service: 'payment', command: 'cancelPayment' },
    { service: 'order', command: 'cancelOrder' }
  ]
};
```

### 状態遷移
```
STARTED → ORDER_CREATED → PAYMENT_PROCESSED → STOCK_RESERVED → SHIPPED → COMPLETED
    ↓           ↓                ↓                 ↓              ↓
  FAILED ← ORDER_CANCELLED ← PAYMENT_CANCELLED ← STOCK_RELEASED ← SHIPMENT_CANCELLED
```

## API エンドポイント

### Orchestrator API
- `POST /saga/start` - Saga開始
- `GET /saga/{orderId}/status` - 状態確認
- `POST /saga/{orderId}/cancel` - 手動キャンセル
- `GET /saga/{orderId}/history` - 実行履歴

### サービス間通信
各サービスは以下の形式でレスポンスを返します：
```json
{
  "success": true|false,
  "sagaId": "uuid",
  "stepId": "string",
  "result": "object",
  "error": "string"
}
```

## 補償処理

失敗時は自動的に補償処理が実行されます：
1. 失敗したステップを特定
2. 実行済みステップに対して逆順で補償コマンド実行
3. 最終的にSaga状態を FAILED に更新
