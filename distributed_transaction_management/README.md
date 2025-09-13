# メルカリ風 分散トランザクション実装

メルカリのエンジニアブログ「[メルコイン決済基盤における分散トランザクション管理](https://engineering.mercari.com/blog/entry/20230614-distributed-transaction/)」を参考にした、Sagaパターンベースの分散トランザクション管理システムのローカル実装です。

## 特徴

* **Sagaパターン**: 複数マイクロサービス間のデータ整合性を保つ
* **オーケストレーション**: 中央集権的なワークフロー管理
* **TCC (Try-Confirm-Cancel)**: 二段階コミットパターン
* **補償トランザクション**: 失敗時の自動ロールバック
* **冪等性とリトライ**: 一時的エラーに対して自動リトライ、Exponential Backoff対応
* **段階的負荷テスト**: light / medium / heavy の3段階テスト
* **Docker構成**: マイクロサービス環境を再現
* **Notebook対応**: リトライ挙動・負荷テスト結果を matplotlib で可視化可能

## アーキテクチャ

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ User Service│    │Payment Svc  │    │Order Service│
│   (MySQL)   │    │  (MySQL)    │    │  (MySQL)    │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                  ┌─────────────┐
                  │Saga Manager │
                  │  (MySQL)    │
                  │  (Redis)    │
                  └─────────────┘
```

### サービス構成

1. **User Service**: ユーザー残高管理（残高予約・確定・キャンセル）
2. **Payment Service**: 決済処理（決済予約・実行・キャンセル）
3. **Order Service**: 注文処理（在庫予約・確定・キャンセル）
4. **Saga Orchestrator**: ワークフロー調整（状態管理・補償処理）

## セットアップ

### 必要な環境

* Docker & Docker Compose
* Python 3.9+
* Jupyter Notebook（負荷テスト・可視化用）

### プロジェクト構造

```
distributed-transaction/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── README.md
├── init_scripts/
│   ├── user_db.sql
│   ├── payment_db.sql
│   ├── order_db.sql
│   └── saga_db.sql
└── src/
    ├── main.py
    ├── workflow/
    │   └── manager.py
    └── services/
        ├── user_service.py
        ├── payment_service.py
        └── order_service.py
└── notebooks/
    └── purchase_test.ipynb   # リトライ・負荷テスト・グラフ化用
```

### 実行手順

1. **リポジトリクローン（または手動作成）**

```bash
mkdir distributed-transaction && cd distributed-transaction
```

2. **ファイル配置**
   各ファイルを上記構造に従って配置してください。

3. **Docker環境起動**

```bash
docker-compose up -d
```

4. **アプリケーション実行**

```bash
docker-compose exec distributed_transaction_app python -m src.main
```

5. **Notebook で負荷テスト・リトライ挙動確認**

```bash
jupyter notebook notebooks/purchase_test.ipynb
```

* 正常 / 残高不足 / 在庫不足の各ケースを実行
* light / medium / heavy の段階的負荷テスト
* 成功率・応答時間を matplotlib グラフで確認

## 使用例

### 成功ケース

```python
# ユーザー alice (残高1000) が Bitcoin (価格100) を1つ購入
purchase_request = {
    'user_id': 1,
    'product_id': 1, 
    'quantity': 1,
    'payment_method_id': 1
}
```

### 失敗ケース (残高不足)

```python
# ユーザー bob (残高500) が Bitcoin を10個購入 → 残高不足で失敗
purchase_request = {
    'user_id': 2,
    'product_id': 1,
    'quantity': 10,
    'payment_method_id': 2
}
```

### 失敗ケース (在庫不足)

```python
# ユーザー charlie が Bitcoin を15個購入 → 在庫不足で失敗
purchase_request = {
    'user_id': 3,
    'product_id': 1,
    'quantity': 15,
    'payment_method_id': 3
}
```

## ワークフロー詳細

### 購入フロー（6段階）

1. **残高予約 (Try)**: ユーザー残高を予約
2. **決済予約 (Try)**: 決済方法を予約
3. **商品予約 (Try)**: 商品在庫を予約
4. **残高確定 (Confirm)**: 予約残高を実際に減額
5. **決済実行 (Confirm)**: 決済を実行
6. **注文確定 (Confirm)**: 在庫を実際に減少

### 補償フロー（失敗時）

失敗した場合、実行済みの操作を逆順で補償：

* 商品予約キャンセル
* 決済予約キャンセル
* 残高予約キャンセル

### エラー分類

**完了可能エラー（即座に失敗）**:

* 残高不足 (Insufficient balance)
* 在庫不足 (Out of stock)
* 無効な決済方法 (Invalid payment method)

**一時的エラー（リトライ）**:

* ネットワークタイムアウト
* 一時的なDB接続エラー
* 予期しないエラー
* **自動リトライ**: 最大3回、Exponential Backoff (1秒, 2秒, 4秒)

## データベーススキーマ

### User Service

```sql
users: id, username, balance, reserved_balance
balance_reservations: id, user_id, amount, status, transaction_id
```

### Payment Service

```sql
payment_methods: id, user_id, method_type, method_details
payment_transactions: id, user_id, payment_method_id, amount, status
```

### Order Service

```sql
products: id, name, price, stock_quantity, reserved_quantity
orders: id, user_id, product_id, quantity, total_amount, status
```

### Saga Orchestrator

```sql
workflows: workflow_id, status, activities, current_activity_index, error
```

## 監視・デバッグ

### ログ確認

```bash
docker-compose logs -f distributed_transaction_app
```

### データベース接続

```bash
# User DB
mysql -h localhost -P 3306 -u user -puser123 user_service

# Payment DB  
mysql -h localhost -P 3307 -u payment -ppayment123 payment_service

# Order DB
mysql -h localhost -P 3308 -u order -porder123 order_service

# Saga DB
mysql -h localhost -P 3309 -u saga -psaga123 saga_orchestrator
```

### Redis接続

```bash
redis-cli -h localhost -p 6379
```

## トラブルシューティング

### よくある問題

1. **ポート競合**

   * MySQL (3306-3309) やRedis (6379) のポートが使用中
   * docker-compose.ymlのポート設定を変更

2. **データベース接続エラー**

   * コンテナの起動順序を確認
   * `docker-compose logs [service_name]` でログ確認

3. **権限エラー**

   * SQLファイルの権限を確認
   * `chmod 644 init_scripts/*.sql`

## 拡張可能性

* **リトライポリシー**: Exponential backoff, Circuit breaker
* **監視**: メトリクス


収集、アラート

* **スケーリング**: Kafka, gRPC通信
* **セキュリティ**: JWT認証、API暗号化
* **パフォーマンス**: Connection pooling, Caching
* **負荷テスト**: light / medium / heavy での段階的テストと可視化

## 参考資料

* [メルコイン決済基盤における分散トランザクション管理](https://engineering.mercari.com/blog/entry/20230614-distributed-transaction/)
* [Saga Pattern](https://microservices.io/patterns/data/saga.html)
* [TCC Pattern](https://www.enterpriseintegrationpatterns.com/TryConfirmCancel.html)
* [matplotlib](https://matplotlib.org/) で可視化可能
* [Jupyter Notebook](https://jupyter.org/) でリトライ・負荷テスト実行可能
