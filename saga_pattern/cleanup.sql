-- ============================================
-- データクリーンアップスクリプト (MySQL)
-- ============================================

USE cloudmart_saga;

-- テストデータ削除（マスタデータは保持）
DELETE FROM saga_step_logs;
DELETE FROM saga_instances;
DELETE FROM events;
DELETE FROM shipments;
DELETE FROM payments;
DELETE FROM order_items;
DELETE FROM orders;

-- 在庫初期化
UPDATE inventory SET
    available_stock = CASE book_id
        WHEN 'book-123' THEN 5
        WHEN 'book-456' THEN 0
        WHEN 'book-789' THEN 10
        WHEN 'book-101' THEN 3
        WHEN 'book-202' THEN 7
    END,
    reserved_stock = 0,
    updated_at = CURRENT_TIMESTAMP;

SELECT 'クリーンアップ完了' as status;
