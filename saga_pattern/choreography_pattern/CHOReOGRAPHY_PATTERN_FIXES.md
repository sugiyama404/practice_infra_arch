# Choreography Pattern 修正適用チェックリスト

## 1. データベース初期化スクリプト修正

### ✅ 確認項目: init.sqlファイルのタイムスタンプ精度
**確認方法:**
```bash
grep -n "TIMESTAMP\|DATETIME" /Users/codefox/workspace/practice_infra_arch/saga_pattern/choreography_pattern/dbconf/init_scripts/init.sql
```

**期待される状態:**
- すべてのテーブルで `DATETIME(6)` を使用
- `CURRENT_TIMESTAMP(6)` と `CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)` を使用

**修正が必要な場合:**
shipmentsテーブルでまだTIMESTAMPを使用している場合、以下の修正を適用してください：

```sql
-- shipmentsテーブルの修正
CREATE TABLE shipments (
    shipment_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    carrier VARCHAR(50) NOT NULL,
    tracking_number VARCHAR(100),
    status ENUM('PENDING', 'ARRANGED', 'PICKED_UP', 'IN_TRANSIT', 'OUT_FOR_DELIVERY', 'DELIVERED', 'FAILED', 'RETURNED') NOT NULL DEFAULT 'PENDING',
    shipping_address JSON NOT NULL,
    estimated_delivery DATE,
    actual_delivery_date DATE,
    shipping_cost DECIMAL(10,2) DEFAULT 0,
    notes TEXT,
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    shipped_at DATETIME(6) NULL,
    delivered_at DATETIME(6) NULL,

    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    INDEX idx_shipments_order_id (order_id),
    INDEX idx_shipments_tracking_number (tracking_number),
    INDEX idx_shipments_status (status),
    INDEX idx_shipments_estimated_delivery (estimated_delivery)
);
```

## 2. Sharedモジュール作成

### ✅ 確認項目: sharedディレクトリの存在確認
**確認方法:**
```bash
ls -la /Users/codefox/workspace/practice_infra_arch/saga_pattern/choreography_pattern/shared/
```

**期待される状態:**
- sharedディレクトリが存在し、以下のファイルを含む：
  - `__init__.py`
  - `models.py`
  - `utils.py`
  - `config.py`

**修正が必要な場合:**
sharedディレクトリが存在しない場合、orchestration_patternからコピーしてください：

```bash
# orchestration_patternのsharedディレクトリをchoreography_patternにコピー
cp -r /Users/codefox/workspace/practice_infra_arch/saga_pattern/orchestration_pattern/shared \
      /Users/codefox/workspace/practice_infra_arch/saga_pattern/choreography_pattern/
```

## 3. Order Service修正

### ✅ 確認項目: Order Confirmationエンドポイント
**確認方法:**
```bash
grep -n "PUT.*confirm\|confirm.*order" /Users/codefox/workspace/practice_infra_arch/saga_pattern/choreography_pattern/order_service/app.py
```

**期待される状態:**
- `PUT /orders/{order_id}/confirm` エンドポイントが存在
- confirmed_atタイムスタンプを設定
- イベント発行機能を含む

**修正が必要な場合:**
order_service/app.pyに以下のエンドポイントを追加してください：

```python
@app.put("/orders/{order_id}/confirm")
async def confirm_order(order_id: str, db: Session = Depends(get_db)):
    """Confirm an order and update its status"""
    try:
        # Get order
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status != OrderStatus.PENDING:
            raise HTTPException(status_code=400, detail=f"Order is already {order.status}")

        # Update order status and confirmed timestamp
        order.status = OrderStatus.CONFIRMED
        order.confirmed_at = datetime.now()
        order.updated_at = datetime.now()

        db.commit()

        # Publish order confirmed event
        event_data = {
            "order_id": order_id,
            "customer_id": order.customer_id,
            "total_amount": float(order.total_amount),
            "confirmed_at": order.confirmed_at.isoformat()
        }

        await create_event(
            aggregate_id=order_id,
            aggregate_type="Order",
            event_type="OrderConfirmed",
            event_data=event_data,
            db_session=db
        )

        return {"message": "Order confirmed successfully", "order_id": order_id}

    except Exception as e:
        logger.error(f"Error confirming order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

## 4. Inventory Service修正

### ✅ 確認項目: イベント記録有効化
**確認方法:**
```bash
grep -n "create_event\|publish.*event" /Users/codefox/workspace/practice_infra_arch/saga_pattern/choreography_pattern/inventory_service/app.py
```

**期待される状態:**
- 在庫操作（予約・解放）でイベントを発行
- create_event関数を適切に呼び出し

**修正が必要な場合:**
inventory_service/app.pyの在庫操作部分にイベント発行を追加してください：

```python
# 在庫予約時のイベント発行例
async def reserve_stock(order_id: str, book_id: str, quantity: int, db: Session):
    """Reserve stock for an order"""
    try:
        # ... existing stock reservation logic ...

        # Publish stock reserved event
        event_data = {
            "order_id": order_id,
            "book_id": book_id,
            "quantity": quantity,
            "reserved_at": datetime.now().isoformat()
        }

        await create_event(
            aggregate_id=order_id,
            aggregate_type="Order",
            event_type="StockReserved",
            event_data=event_data,
            db_session=db
        )

        return True
    except Exception as e:
        logger.error(f"Error reserving stock: {e}")
        return False
```

## 5. Docker Compose設定

### ✅ 確認項目: MySQLポート設定
**確認方法:**
```bash
grep -n "3306\|3307" /Users/codefox/workspace/practice_infra_arch/saga_pattern/choreography_pattern/compose.yaml
```

**期待される状態:**
- MySQLポートが3306に設定されている
- コンテナ間通信が正しく設定されている

**修正が必要な場合:**
ポートが3307の場合、3306に修正してください：

```yaml
services:
  mysql:
    ports:
      - "3306:3306"  # 修正: 3307 → 3306
```

## 6. 修正適用後の検証

### ✅ 検証項目: サービス起動確認
**検証方法:**
```bash
cd /Users/codefox/workspace/practice_infra_arch/saga_pattern/choreography_pattern
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# サービス起動確認
docker-compose ps
```

### ✅ 検証項目: データベース接続確認
**検証方法:**
```bash
docker-compose exec mysql mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga -e "SHOW TABLES;"
```

### ✅ 検証項目: イベント記録確認
**検証方法:**
```bash
# テスト注文作成後
docker-compose exec mysql mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga -e "SELECT COUNT(*) FROM events; SELECT * FROM events LIMIT 5;"
```

### ✅ 検証項目: Order Confirmation機能確認
**検証方法:**
```bash
# Order作成後
curl -X PUT http://localhost:8001/orders/{order_id}/confirm

# confirmed_atが設定されていることを確認
docker-compose exec mysql mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga -e "SELECT order_id, status, confirmed_at FROM orders WHERE confirmed_at IS NOT NULL;"
```

## 修正完了チェックリスト

- [ ] init.sqlファイルのTIMESTAMP → DATETIME(6)修正
- [ ] sharedディレクトリの作成とファイルコピー
- [ ] Order Serviceのconfirmエンドポイント追加
- [ ] Inventory Serviceのイベント記録有効化
- [ ] Docker Compose設定の確認
- [ ] サービス起動テスト
- [ ] データベース接続テスト
- [ ] イベント記録機能テスト
- [ ] Order Confirmation機能テスト

各項目を確認し、未完了のものがあれば上記の修正を適用してください。修正後は必ずサービスを再構築（`docker-compose build --no-cache`）してからテストを実行してください。
