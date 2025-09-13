-- ============================================
-- データ検証スクリプト (MySQL)
-- ============================================

USE cloudmart_saga;

-- テーブル別レコード数確認
SELECT
    'customers' as table_name, COUNT(*) as record_count, MIN(created_at) as oldest, MAX(created_at) as newest FROM customers
UNION ALL
SELECT 'books', COUNT(*), MIN(created_at), MAX(created_at) FROM books
UNION ALL
SELECT 'orders', COUNT(*), MIN(created_at), MAX(created_at) FROM orders
UNION ALL
SELECT 'events', COUNT(*), MIN(created_at), MAX(created_at) FROM events
UNION ALL
SELECT 'saga_instances', COUNT(*), MIN(created_at), MAX(created_at) FROM saga_instances;

-- 注文状態別集計
SELECT
    status,
    COUNT(*) as order_count,
    SUM(total_amount) as total_revenue
FROM orders
GROUP BY status
ORDER BY status;

-- 在庫状況確認
SELECT
    b.title,
    i.available_stock,
    i.reserved_stock,
    (i.available_stock + i.reserved_stock) as total_stock,
    CASE
        WHEN i.available_stock = 0 THEN '在庫切れ'
        WHEN i.available_stock <= i.reorder_point THEN '要補充'
        ELSE '在庫充分'
    END as stock_status
FROM books b
JOIN inventory i ON b.book_id = i.book_id
ORDER BY i.available_stock;

-- イベント種別集計
SELECT
    event_type,
    COUNT(*) as event_count,
    MIN(created_at) as first_event,
    MAX(created_at) as last_event
FROM events
GROUP BY event_type
ORDER BY event_type;

-- データ整合性チェック
SELECT
    'Order-Payment consistency' as check_name,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE CONCAT('FAIL: ', COUNT(*), ' inconsistencies found')
    END as result
FROM orders o
LEFT JOIN payments p ON o.order_id = p.order_id
WHERE o.status IN ('CONFIRMED', 'SHIPPED', 'DELIVERED')
  AND (p.payment_id IS NULL OR p.status != 'COMPLETED');
