CREATE TABLE customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    payment_method_default ENUM('CREDIT_CARD', 'DEBIT_CARD', 'BANK_TRANSFER', 'ELECTRONIC_MONEY', 'COD') DEFAULT 'CREDIT_CARD',
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    INDEX idx_customers_email (email),
    INDEX idx_customers_created_at (created_at)
);

CREATE TABLE books (
    book_id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    author VARCHAR(100),
    isbn VARCHAR(20) UNIQUE,
    category VARCHAR(50),
    price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    publisher VARCHAR(100),
    publication_date DATE,
    description TEXT,
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    INDEX idx_books_title (title),
    INDEX idx_books_category (category),
    INDEX idx_books_isbn (isbn)
);

CREATE TABLE inventory (
    book_id VARCHAR(50) PRIMARY KEY,
    available_stock INT NOT NULL DEFAULT 0 CHECK (available_stock >= 0),
    reserved_stock INT NOT NULL DEFAULT 0 CHECK (reserved_stock >= 0),
    reorder_point INT DEFAULT 5,
    max_stock INT DEFAULT 100,
    last_restocked_at DATETIME(6) NULL,
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    FOREIGN KEY (book_id) REFERENCES books(book_id),
    INDEX idx_inventory_available_stock (available_stock),
    INDEX idx_inventory_updated_at (updated_at)
);

CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    status ENUM('PENDING', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'FAILED') NOT NULL DEFAULT 'PENDING',
    total_amount DECIMAL(10,2) NOT NULL CHECK (total_amount >= 0),
    tax_amount DECIMAL(10,2) DEFAULT 0 CHECK (tax_amount >= 0),
    shipping_fee DECIMAL(10,2) DEFAULT 0 CHECK (shipping_fee >= 0),
    notes TEXT,
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    confirmed_at DATETIME(6) NULL,
    cancelled_at DATETIME(6) NULL,

    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    INDEX idx_orders_customer_id (customer_id),
    INDEX idx_orders_status (status),
    INDEX idx_orders_created_at (created_at)
);

CREATE TABLE order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    book_id VARCHAR(50) NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL CHECK (unit_price >= 0),
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),

    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books(book_id),
    UNIQUE KEY uk_order_book (order_id, book_id),
    INDEX idx_order_items_order_id (order_id),
    INDEX idx_order_items_book_id (book_id)
);

CREATE TABLE payments (
    payment_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL CHECK (amount >= 0),
    payment_method ENUM('CREDIT_CARD', 'DEBIT_CARD', 'BANK_TRANSFER', 'ELECTRONIC_MONEY', 'COD') NOT NULL,
    status ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', 'REFUNDED') NOT NULL DEFAULT 'PENDING',
    transaction_id VARCHAR(100),
    gateway_response JSON,
    processed_at DATETIME(6) NULL,
    failed_reason TEXT,
    refunded_amount DECIMAL(10,2) DEFAULT 0,
    refunded_at DATETIME(6) NULL,
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    INDEX idx_payments_order_id (order_id),
    INDEX idx_payments_status (status),
    INDEX idx_payments_transaction_id (transaction_id),
    INDEX idx_payments_created_at (created_at)
);

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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    shipped_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,

    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    INDEX idx_shipments_order_id (order_id),
    INDEX idx_shipments_tracking_number (tracking_number),
    INDEX idx_shipments_status (status),
    INDEX idx_shipments_estimated_delivery (estimated_delivery)
);

CREATE TABLE events (
    event_id VARCHAR(36) PRIMARY KEY,
    aggregate_id VARCHAR(50) NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_data JSON,
    version INT NOT NULL DEFAULT 1,
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uk_aggregate_version (aggregate_id, version),
    INDEX idx_events_aggregate_id (aggregate_id),
    INDEX idx_events_event_type (event_type),
    INDEX idx_events_created_at (created_at),
    INDEX idx_events_aggregate_type (aggregate_type)
);

INSERT INTO customers (customer_id, name, email, phone, address, payment_method_default) VALUES
('customer-001', '田中太郎', 'tanaka@example.com', '090-1234-5678', '東京都渋谷区神南1-1-1', 'CREDIT_CARD'),
('customer-002', '佐藤花子', 'sato@example.com', '080-9876-5432', '大阪府大阪市北区梅田2-2-2', 'ELECTRONIC_MONEY'),
('customer-003', '山田次郎', 'yamada@example.com', '070-1111-2222', '愛知県名古屋市中区栄3-3-3', 'CREDIT_CARD'),
('customer-004', '鈴木三郎', 'suzuki@example.com', '090-3333-4444', '福岡県福岡市中央区天神4-4-4', 'BANK_TRANSFER'),
('customer-005', '高橋美香', 'takahashi@example.com', '080-5555-6666', '北海道札幌市中央区大通5-5-5', 'DEBIT_CARD');


INSERT INTO books (book_id, title, author, isbn, category, price, publisher, publication_date, description) VALUES
('book-123', 'クラウド設計パターン集', '山田クラウド', '978-1234567890', 'IT技術書', 3500.00, 'テック出版', '2024-01-15', 'クラウドアーキテクチャの実践的パターン集'),
('book-456', '限定版アートブック', 'アート太郎', '978-2345678901', 'アート', 8000.00, 'アート出版社', '2024-06-01', '数量限定のプレミアムアートブック'),
('book-789', 'プログラミング入門', '初心者先生', '978-3456789012', 'IT技術書', 2800.00, 'ビギナー出版', '2024-03-10', 'プログラミング初心者向けの入門書'),
('book-101', 'データベース設計の極意', 'DB博士', '978-4567890123', 'IT技術書', 4200.00, 'データ出版', '2024-02-20', 'データベース設計の実践的ガイド'),
('book-202', 'マイクロサービス実践', 'サービス職人', '978-5678901234', 'IT技術書', 3800.00, 'マイクロ出版', '2024-04-05', 'マイクロサービスアーキテクチャの実装方法');

INSERT INTO inventory (book_id, available_stock, reserved_stock, reorder_point, max_stock, last_restocked_at) VALUES
('book-123', 5, 0, 5, 50, '2024-09-01 09:00:00'),
('book-456', 0, 0, 2, 10, '2024-08-15 14:00:00'),  -- 在庫切れ
('book-789', 10, 0, 8, 100, '2024-09-10 11:00:00'),
('book-101', 3, 0, 3, 30, '2024-09-05 16:00:00'),
('book-202', 7, 0, 5, 40, '2024-09-08 10:30:00');
