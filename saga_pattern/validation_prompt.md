# Sagaパターン実装 包括的検証プロンプト

## 🎯 検証目的
このプロンプトは、ChoreographyパターンとOrchestrationパターンの実装が想定通りの挙動をしているか、エラーが存在するか、HTTPレスポンスが正しく返ってくるか、ファイル構成がベストプラクティスに則っているかを包括的に検証します。

## 📋 検証項目一覧

### 1. ファイル構成検証
```bash
# 全体構造確認
find saga_pattern -type f -name "*.py" -o -name "*.yaml" -o -name "*.yml" -o -name "Dockerfile" -o -name "*.md" | sort

# 各パターンの構造比較
tree saga_pattern/choreography_pattern -I '__pycache__'
tree saga_pattern/orchestration_pattern -I '__pycache__'

# 共有モジュールの確認
ls -la saga_pattern/shared/
```

### 2. 依存関係検証
```bash
# Python依存関係確認
cat saga_pattern/requirements.txt
cat saga_pattern/choreography_pattern/*/requirements.txt
cat saga_pattern/orchestration_pattern/*/requirements.txt

# 循環依存関係チェック
python -c "
import sys
sys.path.append('saga_pattern/shared')
try:
    from models import *
    from config import *
    from utils import *
    print('✅ 共有モジュールインポート成功')
except Exception as e:
    print(f'❌ 共有モジュールインポート失敗: {e}')
"
```

### 3. Docker設定検証
```bash
# Docker Compose設定確認
docker-compose -f saga_pattern/choreography_pattern/compose.yaml config
docker-compose -f saga_pattern/orchestration_pattern/compose.yaml config

# イメージビルドテスト
docker-compose -f saga_pattern/choreography_pattern/compose.yaml build --no-cache
docker-compose -f saga_pattern/orchestration_pattern/compose.yaml build --no-cache

# コンテナ起動テスト
docker-compose -f saga_pattern/choreography_pattern/compose.yaml up -d
docker-compose -f saga_pattern/orchestration_pattern/compose.yaml up -d

# ヘルスチェック確認
docker-compose -f saga_pattern/choreography_pattern/compose.yaml ps
docker-compose -f saga_pattern/orchestration_pattern/compose.yaml ps
```

### 4. データベース初期化検証
```bash
# MySQLコンテナ接続テスト
docker exec -it cloudmart-mysql-choreography mysql -u cloudmart_user -pcloudmart_pass -e "SHOW DATABASES;"

# スキーマ確認
docker exec -it cloudmart-mysql-choreography mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga -e "SHOW TABLES;"

# マスタデータ投入テスト
docker exec -i cloudmart-mysql-choreography mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga < saga_pattern/master_data.sql

# テストデータ投入テスト
docker exec -i cloudmart-mysql-choreography mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga < saga_pattern/load_test_data.sql
```

### 5. HTTPエンドポイント検証
```bash
# サービス起動確認
curl -s http://localhost:8001/docs || echo "Order Service not responding"
curl -s http://localhost:8002/docs || echo "Inventory Service not responding"
curl -s http://localhost:8003/docs || echo "Payment Service not responding"
curl -s http://localhost:8004/docs || echo "Shipping Service not responding"
curl -s http://localhost:8005/docs || echo "Saga Orchestrator not responding"

# ヘルスチェックエンドポイントテスト
curl -X GET http://localhost:8001/health
curl -X GET http://localhost:8002/health
curl -X GET http://localhost:8003/health
curl -X GET http://localhost:8004/health
curl -X GET http://localhost:8005/health

# 正常ケーステスト - 注文作成
curl -X POST http://localhost:8001/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "customer-001",
    "items": [
      {
        "book_id": "book-123",
        "quantity": 1,
        "unit_price": 3500.00
      }
    ]
  }'

# 在庫確認
curl -X GET http://localhost:8002/inventory/book-123

# 決済処理テスト
curl -X POST http://localhost:8003/payments \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "order-test-001",
    "amount": 3850.00,
    "payment_method": "CREDIT_CARD"
  }'

# 配送作成テスト
curl -X POST http://localhost:8004/shipments \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "order-test-001",
    "carrier": "ヤマト運輸",
    "shipping_address": {
      "name": "テストユーザー",
      "address": "東京都渋谷区テスト1-1-1"
    }
  }'
```

### 6. エラーハンドリング検証
```bash
# 在庫不足ケーステスト
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

# 決済失敗ケーステスト
curl -X POST http://localhost:8003/payments \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "order-fail-test",
    "amount": 999999.00,
    "payment_method": "CREDIT_CARD"
  }'

# 無効なリクエストテスト
curl -X POST http://localhost:8001/orders \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 7. イベント駆動検証 (Choreography)
```bash
# Redis接続確認
docker exec -it cloudmart-redis-choreography redis-cli ping

# イベントパブリッシュ確認
curl -X POST http://localhost:8001/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "customer-001",
    "items": [
      {
        "book_id": "book-123",
        "quantity": 1,
        "unit_price": 3500.00
      }
    ]
  }'

# Redisイベント確認
docker exec -it cloudmart-redis-choreography redis-cli KEYS "*"

# イベント処理確認
docker logs choreography-order-service --tail 20
docker logs choreography-inventory-service --tail 20
docker logs choreography-payment-service --tail 20
docker logs choreography-shipping-service --tail 20
```

### 8. Saga Orchestrator検証 (Orchestration)
```bash
# Saga開始テスト
curl -X POST http://localhost:8005/sagas \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "saga-test-001",
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
curl -X GET http://localhost:8005/sagas/saga-test-001

# Sagaステップログ確認
curl -X GET http://localhost:8005/sagas/saga-test-001/logs

# Saga失敗ケーステスト
curl -X POST http://localhost:8005/sagas \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "saga-fail-test",
    "customer_id": "customer-003",
    "items": [
      {
        "book_id": "book-456",
        "quantity": 1,
        "unit_price": 8000.00
      }
    ]
  }'
```

### 9. ログ分析検証
```bash
# 全サービスのログ確認
docker-compose -f saga_pattern/choreography_pattern/compose.yaml logs --tail=50
docker-compose -f saga_pattern/orchestration_pattern/compose.yaml logs --tail=50

# エラーログ検索
docker-compose -f saga_pattern/choreography_pattern/compose.yaml logs | grep -i error
docker-compose -f saga_pattern/orchestration_pattern/compose.yaml logs | grep -i error

# イベントログ確認
docker-compose -f saga_pattern/choreography_pattern/compose.yaml logs | grep -i event
docker-compose -f saga_pattern/orchestration_pattern/compose.yaml logs | grep -i saga
```

### 10. パフォーマンス検証
```bash
# 負荷テスト (正常ケース)
for i in {1..10}; do
  curl -X POST http://localhost:8001/orders \
    -H "Content-Type: application/json" \
    -d '{
      "customer_id": "customer-001",
      "items": [
        {
          "book_id": "book-123",
          "quantity": 1,
          "unit_price": 3500.00
        }
      ]
    }' &
done
wait

# レスポンスタイム測定
time curl -X GET http://localhost:8002/inventory/book-123

# データベース接続プール確認
docker exec -it cloudmart-mysql-choreography mysql -u cloudmart_user -pcloudmart_pass -e "SHOW PROCESSLIST;"
```

### 11. データ整合性検証
```bash
# データベース状態確認
docker exec -it cloudmart-mysql-choreography mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga -e "
SELECT status, COUNT(*) as count FROM orders GROUP BY status;
SELECT book_id, available_stock, reserved_stock FROM inventory;
SELECT event_type, COUNT(*) as count FROM events GROUP BY event_type;
"

# Saga状態確認
docker exec -it cloudmart-mysql-choreography mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga -e "
SELECT saga_id, status, current_step FROM saga_instances;
SELECT saga_id, step_name, status FROM saga_step_logs ORDER BY saga_id, step_number;
"
```

### 12. セキュリティ検証
```bash
# 環境変数確認
docker exec choreography-order-service env | grep -E "(PASSWORD|SECRET|KEY)"

# ネットワーク分離確認
docker network ls
docker network inspect saga_pattern_default

# ポート露出確認
netstat -tlnp | grep -E "(800[1-5]|3306|6379)"
```

### 13. クリーンアップ検証
```bash
# テストデータクリーンアップ
docker exec -i cloudmart-mysql-choreography mysql -u cloudmart_user -pcloudmart_pass cloudmart_saga < saga_pattern/cleanup.sql

# コンテナ停止
docker-compose -f saga_pattern/choreography_pattern/compose.yaml down -v
docker-compose -f saga_pattern/orchestration_pattern/compose.yaml down -v

# イメージクリーンアップ
docker image prune -f
```

## 📊 検証結果評価基準

### ✅ 成功基準
- [ ] 全サービスが正常起動 (HTTP 200)
- [ ] データベース接続正常
- [ ] Redis接続正常
- [ ] 正常ケースで注文完了
- [ ] 異常ケースで適切なエラーハンドリング
- [ ] イベント駆動処理正常 (Choreography)
- [ ] Saga Orchestrator正常 (Orchestration)
- [ ] データ整合性維持
- [ ] ログにエラーがない

### ❌ 失敗基準
- [ ] HTTP 500エラー発生
- [ ] データベース接続失敗
- [ ] Redis接続失敗
- [ ] サービス間通信失敗
- [ ] データ不整合発生
- [ ] メモリリーク
- [ ] ログにERROR/FATAL

## 🔧 トラブルシューティング

### よくある問題と解決法
1. **ポート競合**: `docker-compose down` で既存コンテナ停止
2. **データベース接続失敗**: MySQLヘルスチェック待機
3. **Redis接続失敗**: Redisコンテナ起動順序確認
4. **共有モジュールインポート失敗**: PYTHONPATH設定確認
5. **メモリ不足**: Docker Desktopメモリ割り当て増加

### ログ確認コマンド
```bash
# リアルタイムログ監視
docker-compose -f saga_pattern/choreography_pattern/compose.yaml logs -f

# 特定のサービスログ
docker logs choreography-order-service -f --tail 100
```

## 📈 パフォーマンス指標

- **レスポンスタイム**: < 500ms (正常ケース)
- **スループット**: > 10 req/sec
- **エラー率**: < 1%
- **メモリ使用量**: < 512MB per service
- **CPU使用率**: < 50%

このプロンプトを実行することで、Sagaパターン実装の包括的な検証が可能になります。
