# Saga Choreography Pattern Demo

## 概要
Choreographyパターンは、各サービスが独立してイベントを発行し、他のサービスがそのイベントを監視して次のアクションを実行する分散型のSagaパターンです。中央集権的なコーディネーターは存在せず、各サービスが自律的に動作します。

## ディレクトリ構造
```
saga-choreography-demo/
├── docker-compose.yml
├── README.md
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
└── event-bus/
    └── redis.conf
```

## システム構成図

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Saga Choreography Pattern                           │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │  Event Bus  │
                              │   (Redis)   │
                              └─────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌──────────────┐            ┌──────────────┐            ┌──────────────┐
│Order Service │            │Payment       │            │Inventory     │
│              │            │Service       │            │Service       │
│Events:       │            │              │            │              │
│- OrderCreated│            │Events:       │            │Events:       │
│- OrderFailed │            │- PaymentOK   │            │- StockReserved│
│              │            │- PaymentFail │            │- StockFailed  │
└──────────────┘            └──────────────┘            └──────────────┘
        │                            │                            │
        └────────────────────────────┼────────────────────────────┘
                                     │
                              ┌──────────────┐
                              │Shipping      │
                              │Service       │
                              │              │
                              │Events:       │
                              │- ShipmentOK  │
                              │- ShipmentFail│
                              └──────────────┘

イベントフロー:
1. OrderCreated → PaymentService & InventoryService
2. PaymentOK & StockReserved → ShippingService
3. ShipmentOK → 完了
4. 任意の段階でFail → 補償処理開始
```

## 特徴

### メリット
- **疎結合**: 各サービスは他のサービスの存在を直接知る必要がない
- **スケーラビリティ**: 個別にスケールアウト可能
- **自律性**: 各サービスが独立して意思決定可能

### デメリット
- **複雑性**: イベントフローの追跡が困難
- **デバッグの難しさ**: 分散したログからの問題特定
- **循環依存のリスク**: イベント設計を誤ると無限ループの可能性

## セットアップ

1. Dockerコンテナ起動
```bash
docker-compose up -d
```

2. 注文処理テスト
```bash
curl -X POST http://localhost:3001/orders \
  -H "Content-Type: application/json" \
  -d '{"productId": "item-001", "quantity": 2, "amount": 1000}'
```

3. ログ確認
```bash
docker-compose logs -f
```

## イベント仕様

### OrderCreated
```json
{
  "eventType": "OrderCreated",
  "orderId": "uuid",
  "productId": "string",
  "quantity": "number",
  "amount": "number",
  "timestamp": "iso-date"
}
```

### PaymentOK/PaymentFail
```json
{
  "eventType": "PaymentOK|PaymentFail",
  "orderId": "uuid",
  "amount": "number",
  "timestamp": "iso-date"
}
```

### StockReserved/StockFailed
```json
{
  "eventType": "StockReserved|StockFailed",
  "orderId": "uuid",
  "productId": "string",
  "quantity": "number",
  "timestamp": "iso-date"
}
```

## 補償処理

失敗時は逆順で補償イベントが発行されます：
- ShipmentFail → PaymentCancel & StockRelease
- PaymentFail → StockRelease
- StockFailed → PaymentCancel
