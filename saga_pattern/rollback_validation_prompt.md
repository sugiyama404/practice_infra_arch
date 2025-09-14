# Sagaパターン ロールバックロジック検証プロンプト

## 🎯 検証目的
このプロンプトは、Sagaパターン（Choreography/Orchestration）のロールバックロジック（補償トランザクション）が正しく実装されているかを包括的に検証します。

## 📋 検証項目一覧

### 1. Orchestrationパターン補償トランザクション定義検証
```bash
# Saga Orchestratorのワークフロー定義確認
grep -A 20 "ORDER_WORKFLOW" saga_pattern/orchestration_pattern/saga_orchestrator/app.py

# 補償コマンド定義確認
grep -n "compensation" saga_pattern/orchestration_pattern/saga_orchestrator/app.py

# execute_compensation関数実装確認
grep -A 50 "async def execute_compensation" saga_pattern/orchestration_pattern/saga_orchestrator/app.py
```

### 2. 各サービス補償エンドポイント実装検証
```bash
# 在庫サービス補償エンドポイント確認
grep -n "release_stock" saga_pattern/orchestration_pattern/inventory_service/app.py || echo "❌ release_stock endpoint not found"

# 決済サービス補償エンドポイント確認
grep -n "cancel_payment" saga_pattern/orchestration_pattern/payment_service/app.py || echo "❌ cancel_payment endpoint not found"

# 配送サービス補償エンドポイント確認
grep -n "cancel_shipping" saga_pattern/orchestration_pattern/shipping_service/app.py || echo "❌ cancel_shipping endpoint not found"

# 全サービスのエンドポイント一覧
find saga_pattern/orchestration_pattern -name "app.py" -exec grep -H "@app.post" {} \;
```

### 3. Choreographyパターンイベント駆動ロールバック検証
```bash
# OrderCancelledイベント処理確認
grep -A 20 "handle_order_cancelled" saga_pattern/choreography_pattern/inventory_service/app.py

# PaymentFailedイベント処理確認
grep -A 20 "handle_payment_failed" saga_pattern/choreography_pattern/payment_service/app.py

# イベント処理ループ確認
grep -A 30 "while True:" saga_pattern/choreography_pattern/*/app.py
```

### 4. ロールバック実行テスト
```bash
# Orchestrationパターン - 正常Saga実行
curl -X POST http://localhost:8005/sagas \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "rollback-test-001",
    "customer_id": "customer-001",
    "items": [
      {
        "book_id": "book-123",
        "quantity": 1,
        "unit_price": 3500.00
      }
    ]
  }'

# Saga状態確認
curl -X GET http://localhost:8005/sagas/rollback-test-001

# Orchestrationパターン - 失敗Saga実行（在庫不足）
curl -X POST http://localhost:8005/sagas \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "rollback-test-002",
    "customer_id": "customer-003",
    "items": [
      {
        "book_id": "book-456",
        "quantity": 1,
        "unit_price": 8000.00
      }
    ]
  }'

# 失敗Sagaの補償実行確認
curl -X GET http://localhost:8005/sagas/rollback-test-002
curl -X GET http://localhost:8005/sagas/rollback-test-002/logs
```

### 5. Choreographyパターン失敗ケーステスト
```bash
# 在庫不足ケース - OrderCreatedイベント発行
curl -X POST http://localhost:8001/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "customer-003",
    "items": [
      {
        "book_id": "book-456",
        "quantity": 1,
        "unit_price": 8000.00
      }
    ]
  }'

# 決済失敗ケース - 手動PaymentFailedイベント発行
curl -X POST http://localhost:8003/payments \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "choreography-fail-test",
    "amount": 999999.00,
    "payment_method": "CREDIT_CARD"
  }'
```

### 6. データ整合性ロールバック検証
```bash
# ロールバック前後のデータ状態比較
echo "=== ロールバック前 ==="
docker exec -it cloudmart-mysql-orchestration mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga -e "
SELECT book_id, available_stock, reserved_stock FROM inventory WHERE book_id = 'book-123';
SELECT status, COUNT(*) FROM orders GROUP BY status;
SELECT saga_id, status FROM saga_instances WHERE saga_id LIKE 'rollback-test%';
"

# ロールバック実行後のデータ状態
echo "=== ロールバック後 ==="
docker exec -it cloudmart-mysql-orchestration mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga -e "
SELECT book_id, available_stock, reserved_stock FROM inventory WHERE book_id = 'book-123';
SELECT status, COUNT(*) FROM orders GROUP BY status;
SELECT saga_id, status FROM saga_instances WHERE saga_id LIKE 'rollback-test%';
SELECT saga_id, step_name, status FROM saga_step_logs WHERE saga_id LIKE 'rollback-test%' ORDER BY saga_id, step_number;
"
```

### 7. 部分ロールバック検証
```bash
# ステップ2（決済）で失敗するSaga実行
curl -X POST http://localhost:8005/sagas \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "partial-rollback-test",
    "customer_id": "customer-004",
    "items": [
      {
        "book_id": "book-101",
        "quantity": 1,
        "unit_price": 4200.00
      }
    ]
  }'

# 部分ロールバック確認（ステップ1のみ補償実行）
curl -X GET http://localhost:8005/sagas/partial-rollback-test/logs

# データベース状態確認
docker exec -it cloudmart-mysql-orchestration mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga -e "
SELECT saga_id, step_name, status FROM saga_step_logs
WHERE saga_id = 'partial-rollback-test'
ORDER BY step_number;
"
```

### 8. ロールバック失敗時の処理検証
```bash
# 補償処理が失敗するケースのテスト
# （例: 既にリリースされた在庫を再度リリースしようとする）

# ログで補償失敗を確認
docker logs orchestration-saga-orchestrator --tail 50 | grep -i "compensation failed"

# Saga状態が適切に更新されているか確認
docker exec -it cloudmart-mysql-orchestration mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga -e "
SELECT saga_id, status, failure_reason FROM saga_instances
WHERE status = 'FAILED' OR status LIKE '%COMPENSATION%';
"
```

### 9. ログ分析によるロールバック検証
```bash
# Orchestrationパターンロールバックログ
docker-compose -f saga_pattern/orchestration_pattern/compose.yaml logs saga-orchestrator | grep -i compensation

# Choreographyパターンロールバックログ
docker-compose -f saga_pattern/choreography_pattern/compose.yaml logs | grep -E "(OrderCancelled|PaymentFailed|StockReleased)"

# 全サービスのロールバック関連ログ
for service in order-service inventory-service payment-service shipping-service; do
  echo "=== $service rollback logs ==="
  docker logs orchestration-$service --tail 20 | grep -i -E "(cancel|release|rollback|compensation)"
done
```

### 10. ロールバックパフォーマンス検証
```bash
# ロールバック実行時間測定
time curl -X POST http://localhost:8005/sagas \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "performance-test-001",
    "customer_id": "customer-003",
    "items": [
      {
        "book_id": "book-456",
        "quantity": 1,
        "unit_price": 8000.00
      }
    ]
  }'

# 複数Sagaの並行ロールバックテスト
for i in {1..5}; do
  curl -X POST http://localhost:8005/sagas \
    -H "Content-Type: application/json" \
    -d '{
      "order_id": "concurrent-fail-test-'$i'",
      "customer_id": "customer-003",
      "items": [
        {
          "book_id": "book-456",
          "quantity": 1,
          "unit_price": 8000.00
        }
      ]
    }' &
done
wait

# ロールバック処理の並行性確認
docker exec -it cloudmart-mysql-orchestration mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga -e "
SELECT status, COUNT(*) FROM saga_instances
WHERE saga_id LIKE 'concurrent-fail-test%'
GROUP BY status;
"
```

### 11. 補償トランザクションの冪等性検証
```bash
# 同じSaga IDで複数回補償実行テスト
curl -X POST http://localhost:8005/sagas \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "idempotent-test",
    "customer_id": "customer-001",
    "items": [
      {
        "book_id": "book-123",
        "quantity": 1,
        "unit_price": 3500.00
      }
    ]
  }'

# 補償処理の冪等性確認（同じリクエストを複数回実行）
for i in {1..3}; do
  echo "=== 補償実行 $i 回目 ==="
  # 補償を手動実行（実際のAPIがあれば使用）
  curl -X POST http://localhost:8002/inventory/release \
    -H "Content-Type: application/json" \
    -d '{"order_id": "idempotent-test", "book_id": "book-123", "quantity": 1}'
done

# 在庫状態が適切に維持されているか確認
docker exec -it cloudmart-mysql-orchestration mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga -e "
SELECT book_id, available_stock, reserved_stock FROM inventory WHERE book_id = 'book-123';
"
```

## 📊 検証結果評価基準

### ✅ 成功基準
- [ ] Orchestration: 補償トランザクションが定義されている
- [ ] Orchestration: 各サービスに補償エンドポイントが実装されている
- [ ] Orchestration: 失敗時に逆順で補償が実行される
- [ ] Choreography: 失敗イベントが適切に処理される
- [ ] ロールバック後、データ整合性が維持される
- [ ] 部分ロールバックが正しく動作する
- [ ] 補償処理の冪等性が保証される
- [ ] ロールバック失敗時の適切なエラーハンドリング

### ❌ 失敗基準
- [ ] 補償トランザクションが定義されていない
- [ ] 補償エンドポイントが実装されていない
- [ ] ロールバック実行時にデータ不整合が発生
- [ ] 補償処理が順序通り実行されない
- [ ] 同じ補償が複数回実行されて副作用が発生
- [ ] ロールバック失敗時のリカバリー処理がない

## 🔧 問題発見時の対応

### Orchestrationパターン補償エンドポイント実装確認
```bash
# 各サービスの補償エンドポイント実装状況
echo "=== Inventory Service ==="
grep -n "release_stock\|cancel" saga_pattern/orchestration_pattern/inventory_service/app.py || echo "補償エンドポイント未実装"

echo "=== Payment Service ==="
grep -n "cancel_payment\|refund" saga_pattern/orchestration_pattern/payment_service/app.py || echo "補償エンドポイント未実装"

echo "=== Shipping Service ==="
grep -n "cancel_shipping\|cancel" saga_pattern/orchestration_pattern/shipping_service/app.py || echo "補償エンドポイント未実装"
```

### 補償処理実装例
```python
# 在庫サービス - release_stockエンドポイント実装例
@app.post("/inventory/release")
async def release_stock(request: Dict[str, Any], db: Session = Depends(get_db)):
    """Release reserved stock (compensation)"""
    order_id = request.get("order_id")
    book_id = request.get("book_id")
    quantity = request.get("quantity")

    # 在庫リリース処理
    inventory = db.query(Inventory).filter(Inventory.book_id == book_id).first()
    if inventory and inventory.reserved_stock >= quantity:
        inventory.reserved_stock -= quantity
        inventory.available_stock += quantity
        db.commit()
        return {"message": "Stock released successfully"}

    return {"message": "No stock to release or already released"}
```

## 📈 ロールバックロジック品質評価

### 高品質基準
- ✅ 補償トランザクションが全て実装されている
- ✅ 逆順補償実行が保証されている
- ✅ データ整合性が維持される
- ✅ 冪等性と安全性が確保されている
- ✅ 詳細なログと監視が実装されている

### 要改善項目
- ❌ 補償エンドポイントが未実装
- ❌ ロールバック順序が不正
- ❌ データ不整合が発生
- ❌ エラーハンドリングが不十分
- ❌ ログが不十分

このプロンプトを実行することで、Sagaパターンのロールバックロジックの実装品質を包括的に評価できます。
