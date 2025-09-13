# Sagaパターン - ストーリーと要件定義

## 全体ストーリー概要

### ビジネスコンテキスト
**「CloudMart」オンライン書店システム**

CloudMartは中規模のオンライン書店で、以下のような特徴があります：
- 在庫管理が重要（限定版書籍など希少な商品を扱う）
- 複数の支払い方法対応（クレジットカード、電子マネー）
- 迅速な配送サービス
- 高い顧客満足度が求められる

### 基本フロー：書籍注文処理
1. **注文作成**: 顧客が書籍を注文
2. **在庫確認**: 指定された書籍の在庫を確認・予約
3. **支払い処理**: 顧客の支払い方法で決済実行
4. **配送手配**: 配送業者への出荷依頼

### 参加サービス
- **Order Service**: 注文管理
- **Inventory Service**: 在庫管理
- **Payment Service**: 決済処理
- **Shipping Service**: 配送管理

---

## Choreographyパターン詳細

### ストーリー: 分散協調による注文処理

**「各サービスが踊るように連携する自律的な注文システム」**

#### 正常フロー（成功ケース）
1. **顧客注文**: 田中さんが『クラウド設計パターン集』（在庫3冊）を注文
   ```
   POST /orders
   { "customerId": "customer-001", "bookId": "book-123", "quantity": 1, "price": 3500 }
   ```

2. **Order Service**: `OrderCreated`イベント発行
   ```json
   {
     "eventType": "OrderCreated",
     "orderId": "order-001",
     "bookId": "book-123",
     "quantity": 1,
     "customerId": "customer-001",
     "totalAmount": 3500,
     "timestamp": "2025-09-13T10:00:00Z"
   }
   ```

3. **Inventory Service**: イベント受信 → 在庫確認 → `StockReserved`発行
4. **Payment Service**: `OrderCreated`受信 → 決済処理 → `PaymentCompleted`発行
5. **Shipping Service**: 両イベント受信 → 配送手配 → `ShippingArranged`発行
6. **Order Service**: 完了イベント受信 → 注文ステータス更新

#### 異常フロー（失敗・ロールバックケース）

**シナリオ1: 在庫不足**
1. 佐藤さんが『限定版アートブック』（在庫0冊）を注文
2. Inventory Service → `StockUnavailable`発行
3. Payment Service → 決済処理を停止
4. Order Service → `OrderCancelled`発行、顧客に通知

**シナリオ2: 決済失敗**
1. 山田さんのクレジットカード残高不足で決済失敗
2. Payment Service → `PaymentFailed`発行
3. Inventory Service → `StockReleased`発行（予約解除）
4. Order Service → `OrderCancelled`発行

**シナリオ3: 配送業者エラー**
1. 配送業者システム障害で配送手配失敗
2. Shipping Service → `ShippingFailed`発行
3. Payment Service → `PaymentRefunded`発行（返金処理）
4. Inventory Service → `StockReleased`発行
5. Order Service → `OrderCancelled`発行

#### 特徴
- 各サービスが**自律的**にイベントを監視・発行
- **中央制御者なし**
- イベントバス（Redis Pub/Sub）を通じた**非同期通信**
- 補償処理も各サービスが**自発的**に実行

---

## Orchestrationパターン詳細

### ストーリー: 指揮者による統制された注文処理

**「Saga Orchestratorが指揮する協調的な注文システム」**

#### 正常フロー（成功ケース）
1. **顧客注文**: 田中さんが同じ書籍を注文
2. **Saga Orchestrator**: 注文ワークフロー開始
   ```
   Workflow State: STARTED
   ```

3. **Step 1 - 注文作成**:
   ```
   Command: CreateOrder → Order Service
   Response: OrderCreated (Success)
   Workflow State: ORDER_CREATED
   ```

4. **Step 2 - 在庫確認**:
   ```
   Command: ReserveStock → Inventory Service
   Response: StockReserved (Success)
   Workflow State: STOCK_RESERVED
   ```

5. **Step 3 - 決済処理**:
   ```
   Command: ProcessPayment → Payment Service
   Response: PaymentCompleted (Success)
   Workflow State: PAYMENT_COMPLETED
   ```

6. **Step 4 - 配送手配**:
   ```
   Command: ArrangeShipping → Shipping Service
   Response: ShippingArranged (Success)
   Workflow State: COMPLETED
   ```

#### 異常フロー（失敗・ロールバックケース）

**シナリオ1: 決済失敗時の補償処理**
1. Step 3で決済失敗: `PaymentFailed`
2. **Orchestrator判断**: 補償処理開始
   ```
   Workflow State: COMPENSATION_STARTED
   ```
3. **補償 Step 2**: `ReleaseStock` → Inventory Service
4. **補償 Step 1**: `CancelOrder` → Order Service
5. **最終状態**: `FAILED`

**シナリオ2: 配送手配失敗時の完全ロールバック**
1. Step 4で配送手配失敗
2. **段階的補償処理**:
   ```
   補償 Step 3: RefundPayment → Payment Service
   補償 Step 2: ReleaseStock → Inventory Service
   補償 Step 1: CancelOrder → Order Service
   ```
3. **状態履歴**:
   ```
   STARTED → ORDER_CREATED → STOCK_RESERVED → PAYMENT_COMPLETED → COMPENSATION_STARTED → FAILED
   ```

#### 特徴
- **Saga Orchestrator**が全体フローを制御
- **同期的**なコマンド/レスポンス通信
- **明確な状態管理**とワークフロー定義
- **確定的な補償処理**順序

---

## 共通要件

### 機能要件

#### 基本機能
- **注文処理**: CRUD操作、状態管理
- **在庫管理**: 予約/解除、可用性チェック
- **決済処理**: 課金/返金、複数決済方法対応
- **配送管理**: 配送先情報、配送業者API連携

#### Sagaパターン固有機能
- **補償トランザクション**: 各サービスでの取り消し操作
- **幂等性保証**: 重複処理の防止
- **イベント順序保証**: メッセージの順序性
- **タイムアウト処理**: 長時間応答なしの処理

### 非機能要件

#### パフォーマンス
- **レスポンス時間**: API応答 < 500ms
- **スループット**: 100 注文/分 処理可能
- **同時接続**: 50 concurrent requests

#### 信頼性
- **可用性**: 99.9%（ローカル環境での目標値）
- **データ整合性**: 結果整合性の保証
- **障害回復**: 自動retry機能（最大3回）

#### スケーラビリティ
- **水平スケール**: Docker Composeでのレプリカ対応
- **リソース制限**: 各コンテナ CPU 0.5core, Memory 512MB

### データ要件

#### データベース構成
- **PostgreSQL**: 主データストア（注文、在庫、決済情報）
- **Redis**: イベントストア、キャッシュ（Choreography用）
- **RabbitMQ**: メッセージキュー（Orchestration用）

#### 主要テーブル
```sql
-- 注文テーブル
orders (id, customer_id, status, total_amount, created_at, updated_at)

-- 在庫テーブル
inventory (book_id, title, available_stock, reserved_stock, price)

-- 決済テーブル
payments (id, order_id, amount, payment_method, status, transaction_id)

-- 配送テーブル
shipments (id, order_id, shipping_address, tracking_number, status)

-- イベントログテーブル（Choreography用）
events (id, event_type, aggregate_id, payload, timestamp)

-- Sagaログテーブル（Orchestration用）
saga_instances (id, saga_type, status, current_step, payload, created_at)
```

#### 初期データ
```json
// 書籍在庫
[
  {"book_id": "book-123", "title": "クラウド設計パターン集", "stock": 5, "price": 3500},
  {"book_id": "book-456", "title": "限定版アートブック", "stock": 0, "price": 8000},
  {"book_id": "book-789", "title": "プログラミング入門", "stock": 10, "price": 2800}
]

// 顧客データ
[
  {"customer_id": "customer-001", "name": "田中太郎", "email": "tanaka@example.com"},
  {"customer_id": "customer-002", "name": "佐藤花子", "email": "sato@example.com"}
]
```

### 技術スタック

#### 開発言語・フレームワーク
- **Python 3.11+**: メインプログラミング言語
- **FastAPI**: RESTful API フレームワーク
- **SQLAlchemy**: ORM
- **Pydantic**: データバリデーション

#### インフラ・ミドルウェア
- **Docker & Docker Compose**: コンテナ化
- **PostgreSQL 15**: リレーショナルデータベース
- **Redis 7**: インメモリデータストア、Pub/Sub
- **RabbitMQ 3.12**: メッセージブローカー
- **Nginx**: リバースプロキシ（オプション）

#### 開発・運用ツール
- **pytest**: テストフレームワーク
- **Black & isort**: コードフォーマッター
- **Prometheus & Grafana**: メトリクス監視（オプション）

### 制約・前提条件

#### 開発制約
- **ローカル実行**: Docker Desktop環境での動作
- **シンプル性**: 本番レベルの複雑性は避ける
- **学習目的**: Sagaパターンの理解に焦点
- **リソース制限**: 一般的な開発マシンで実行可能

#### 技術制約
- **外部サービス依存最小化**: 実際の決済・配送API は使わずモック
- **セキュリティ簡略化**: 認証・認可は基本的なもの
- **ログ・監視**: 標準出力ベース
