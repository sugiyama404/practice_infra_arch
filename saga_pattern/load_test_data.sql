-- ============================================
-- テストデータ投入スクリプト (MySQL)
-- ============================================

USE cloudmart_saga;

-- 正常ケース: 成功した注文
INSERT INTO orders (order_id, customer_id, status, total_amount, tax_amount, shipping_fee, confirmed_at) VALUES
('order-success-001', 'customer-001', 'DELIVERED', 3850.00, 350.00, 0.00, DATE_SUB(NOW(), INTERVAL 3 DAY));

INSERT INTO order_items (order_id, book_id, quantity, unit_price) VALUES
('order-success-001', 'book-123', 1, 3500.00);

UPDATE inventory SET available_stock = available_stock - 1 WHERE book_id = 'book-123';

INSERT INTO payments (payment_id, order_id, amount, payment_method, status, transaction_id, processed_at) VALUES
('pay-success-001', 'order-success-001', 3850.00, 'CREDIT_CARD', 'COMPLETED', 'txn-12345678', DATE_SUB(NOW(), INTERVAL 3 DAY));

INSERT INTO shipments (shipment_id, order_id, carrier, tracking_number, status, shipping_address, estimated_delivery, actual_delivery_date, shipped_at, delivered_at) VALUES
('ship-success-001', 'order-success-001', 'ヤマト運輸', 'YMT123456789', 'DELIVERED',
 JSON_OBJECT('postcode', '150-0041', 'address', '東京都渋谷区神南1-1-1', 'name', '田中太郎', 'phone', '090-1234-5678'),
 DATE_SUB(CURDATE(), INTERVAL 1 DAY), CURDATE(), DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY));

-- 異常ケース1: 在庫不足による失敗
INSERT INTO orders (order_id, customer_id, status, total_amount, tax_amount, cancelled_at) VALUES
('order-fail-stock', 'customer-003', 'CANCELLED', 8800.00, 800.00, DATE_SUB(NOW(), INTERVAL 2 HOUR));

INSERT INTO order_items (order_id, book_id, quantity, unit_price) VALUES
('order-fail-stock', 'book-456', 1, 8000.00);

-- 異常ケース2: 決済失敗による失敗
INSERT INTO orders (order_id, customer_id, status, total_amount, tax_amount, cancelled_at) VALUES
('order-fail-payment', 'customer-004', 'CANCELLED', 4620.00, 420.00, DATE_SUB(NOW(), INTERVAL 1 HOUR));

INSERT INTO order_items (order_id, book_id, quantity, unit_price) VALUES
('order-fail-payment', 'book-101', 1, 4200.00);

INSERT INTO payments (payment_id, order_id, amount, payment_method, status, failed_reason) VALUES
('pay-fail-001', 'order-fail-payment', 4620.00, 'CREDIT_CARD', 'FAILED', 'Insufficient funds');

-- Choreographyパターン用イベントデータ
INSERT INTO events (event_type, aggregate_id, aggregate_type, version, payload, processed_at) VALUES
('ORDER_CREATED', 'order-success-001', 'order', 1,
 JSON_OBJECT('order_id', 'order-success-001', 'customer_id', 'customer-001', 'book_id', 'book-123', 'quantity', 1, 'amount', 3850.00),
 DATE_SUB(NOW(), INTERVAL 3 DAY)),
('STOCK_RESERVED', 'order-success-001', 'inventory', 1,
 JSON_OBJECT('order_id', 'order-success-001', 'book_id', 'book-123', 'quantity', 1, 'available_stock', 4),
 DATE_SUB(NOW(), INTERVAL 3 DAY)),
('PAYMENT_COMPLETED', 'order-success-001', 'payment', 1,
 JSON_OBJECT('order_id', 'order-success-001', 'payment_id', 'pay-success-001', 'amount', 3850.00, 'method', 'CREDIT_CARD'),
 DATE_SUB(NOW(), INTERVAL 3 DAY)),
('SHIPPING_DELIVERED', 'order-success-001', 'shipment', 2,
 JSON_OBJECT('order_id', 'order-success-001', 'delivered_at', DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 DAY), '%Y-%m-%d %H:%i:%s'), 'status', 'DELIVERED'),
 DATE_SUB(NOW(), INTERVAL 1 DAY));

-- 在庫不足失敗イベント
INSERT INTO events (event_type, aggregate_id, aggregate_type, version, payload, processed_at) VALUES
('ORDER_CREATED', 'order-fail-stock', 'order', 1,
 JSON_OBJECT('order_id', 'order-fail-stock', 'customer_id', 'customer-003', 'book_id', 'book-456', 'quantity', 1),
 DATE_SUB(NOW(), INTERVAL 2 HOUR)),
('STOCK_UNAVAILABLE', 'order-fail-stock', 'inventory', 1,
 JSON_OBJECT('order_id', 'order-fail-stock', 'book_id', 'book-456', 'reason', 'out_of_stock'),
 DATE_SUB(NOW(), INTERVAL 2 HOUR)),
('ORDER_CANCELLED', 'order-fail-stock', 'order', 2,
 JSON_OBJECT('order_id', 'order-fail-stock', 'reason', 'insufficient_stock'),
 DATE_SUB(NOW(), INTERVAL 2 HOUR));

-- Orchestrationパターン用Sagaデータ
INSERT INTO saga_instances (saga_id, order_id, status, current_step, payload, completed_at) VALUES
('saga-success-001', 'order-success-001', 'COMPLETED', 4,
 JSON_OBJECT('order_id', 'order-success-001', 'customer_id', 'customer-001', 'total_amount', 3850.00),
 DATE_SUB(NOW(), INTERVAL 1 DAY));

INSERT INTO saga_step_logs (saga_id, step_number, step_name, service_name, command_type, status, request_payload, response_payload, started_at, completed_at, duration_ms) VALUES
('saga-success-001', 1, 'CreateOrder', 'order-service', 'CREATE_ORDER', 'COMPLETED',
 JSON_OBJECT('order_id', 'order-success-001', 'customer_id', 'customer-001'),
 JSON_OBJECT('success', true, 'order_id', 'order-success-001', 'status', 'CREATED'),
 DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_ADD(DATE_SUB(NOW(), INTERVAL 3 DAY), INTERVAL 150 MICROSECOND), 150),
('saga-success-001', 2, 'ReserveStock', 'inventory-service', 'RESERVE_STOCK', 'COMPLETED',
 JSON_OBJECT('order_id', 'order-success-001', 'book_id', 'book-123', 'quantity', 1),
 JSON_OBJECT('success', true, 'reserved', true, 'available_stock', 4),
 DATE_ADD(DATE_SUB(NOW(), INTERVAL 3 DAY), INTERVAL 200 MICROSECOND), DATE_ADD(DATE_SUB(NOW(), INTERVAL 3 DAY), INTERVAL 380 MICROSECOND), 180),
('saga-success-001', 3, 'ProcessPayment', 'payment-service', 'PROCESS_PAYMENT', 'COMPLETED',
 JSON_OBJECT('order_id', 'order-success-001', 'amount', 3850.00, 'payment_method', 'CREDIT_CARD'),
 JSON_OBJECT('success', true, 'payment_id', 'pay-success-001', 'transaction_id', 'txn-12345678'),
 DATE_ADD(DATE_SUB(NOW(), INTERVAL 3 DAY), INTERVAL 400 MICROSECOND), DATE_ADD(DATE_SUB(NOW(), INTERVAL 3 DAY), INTERVAL 650 MICROSECOND), 250),
('saga-success-001', 4, 'CreateShipment', 'shipping-service', 'CREATE_SHIPMENT', 'COMPLETED',
 JSON_OBJECT('order_id', 'order-success-001', 'carrier', 'ヤマト運輸', 'shipping_address', JSON_OBJECT('name', '田中太郎', 'address', '東京都渋谷区神南1-1-1')),
 JSON_OBJECT('success', true, 'shipment_id', 'ship-success-001', 'tracking_number', 'YMT123456789'),
 DATE_ADD(DATE_SUB(NOW(), INTERVAL 3 DAY), INTERVAL 700 MICROSECOND), DATE_ADD(DATE_SUB(NOW(), INTERVAL 3 DAY), INTERVAL 850 MICROSECOND), 150);

-- 決済失敗ケースのイベントデータ
INSERT INTO events (event_type, aggregate_id, aggregate_type, version, payload, processed_at) VALUES
('ORDER_CREATED', 'order-fail-payment', 'order', 1,
 JSON_OBJECT('order_id', 'order-fail-payment', 'customer_id', 'customer-004', 'book_id', 'book-101', 'quantity', 1),
 DATE_SUB(NOW(), INTERVAL 1 HOUR)),
('STOCK_RESERVED', 'order-fail-payment', 'inventory', 1,
 JSON_OBJECT('order_id', 'order-fail-payment', 'book_id', 'book-101', 'quantity', 1, 'available_stock', 2),
 DATE_SUB(NOW(), INTERVAL 1 HOUR)),
('PAYMENT_FAILED', 'order-fail-payment', 'payment', 1,
 JSON_OBJECT('order_id', 'order-fail-payment', 'amount', 4620.00, 'reason', 'Insufficient funds'),
 DATE_SUB(NOW(), INTERVAL 1 HOUR)),
('STOCK_RELEASED', 'order-fail-payment', 'inventory', 2,
 JSON_OBJECT('order_id', 'order-fail-payment', 'book_id', 'book-101', 'quantity', 1, 'available_stock', 3),
 DATE_SUB(NOW(), INTERVAL 1 HOUR)),
('ORDER_CANCELLED', 'order-fail-payment', 'order', 2,
 JSON_OBJECT('order_id', 'order-fail-payment', 'reason', 'payment_failed'),
 DATE_SUB(NOW(), INTERVAL 1 HOUR));

-- 決済失敗ケースのSagaデータ
INSERT INTO saga_instances (saga_id, order_id, status, current_step, payload, failed_at, failure_reason) VALUES
('saga-fail-payment', 'order-fail-payment', 'FAILED', 3,
 JSON_OBJECT('order_id', 'order-fail-payment', 'customer_id', 'customer-004', 'total_amount', 4620.00),
 DATE_SUB(NOW(), INTERVAL 1 HOUR), 'PAYMENT_FAILED');

INSERT INTO saga_step_logs (saga_id, step_number, step_name, service_name, command_type, status, request_payload, response_payload, started_at, completed_at, duration_ms) VALUES
('saga-fail-payment', 1, 'CreateOrder', 'order-service', 'CREATE_ORDER', 'COMPLETED',
 JSON_OBJECT('order_id', 'order-fail-payment', 'customer_id', 'customer-004'),
 JSON_OBJECT('success', true, 'order_id', 'order-fail-payment', 'status', 'CREATED'),
 DATE_SUB(NOW(), INTERVAL 1 HOUR), DATE_ADD(DATE_SUB(NOW(), INTERVAL 1 HOUR), INTERVAL 120 MICROSECOND), 120),
('saga-fail-payment', 2, 'ReserveStock', 'inventory-service', 'RESERVE_STOCK', 'COMPLETED',
 JSON_OBJECT('order_id', 'order-fail-payment', 'book_id', 'book-101', 'quantity', 1),
 JSON_OBJECT('success', true, 'reserved', true, 'available_stock', 2),
 DATE_ADD(DATE_SUB(NOW(), INTERVAL 1 HOUR), INTERVAL 150 MICROSECOND), DATE_ADD(DATE_SUB(NOW(), INTERVAL 1 HOUR), INTERVAL 300 MICROSECOND), 150),
('saga-fail-payment', 3, 'ProcessPayment', 'payment-service', 'PROCESS_PAYMENT', 'FAILED',
 JSON_OBJECT('order_id', 'order-fail-payment', 'amount', 4620.00, 'payment_method', 'CREDIT_CARD'),
 JSON_OBJECT('success', false, 'error', 'Insufficient funds'),
 DATE_ADD(DATE_SUB(NOW(), INTERVAL 1 HOUR), INTERVAL 350 MICROSECOND), DATE_ADD(DATE_SUB(NOW(), INTERVAL 1 HOUR), INTERVAL 600 MICROSECOND), 250),
('saga-fail-payment', 4, 'ReleaseStock', 'inventory-service', 'RELEASE_STOCK', 'COMPLETED',
 JSON_OBJECT('order_id', 'order-fail-payment', 'book_id', 'book-101', 'quantity', 1),
 JSON_OBJECT('success', true, 'released', true, 'available_stock', 3),
 DATE_ADD(DATE_SUB(NOW(), INTERVAL 1 HOUR), INTERVAL 650 MICROSECOND), DATE_ADD(DATE_SUB(NOW(), INTERVAL 1 HOUR), INTERVAL 750 MICROSECOND), 100);
