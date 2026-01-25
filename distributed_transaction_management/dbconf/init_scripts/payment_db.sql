USE payment_service;

CREATE TABLE IF NOT EXISTS payment_methods (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    method_type VARCHAR(50) NOT NULL,
    method_details TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_transactions (
    id VARCHAR(36) PRIMARY KEY,
    user_id INT NOT NULL,
    payment_method_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'reserved',
    transaction_id VARCHAR(36) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (payment_method_id) REFERENCES payment_methods(id)
);

INSERT IGNORE INTO payment_methods (id, user_id, method_type, method_details) VALUES
(1, 1, 'credit_card', '{"last4": "1234", "brand": "visa"}'),
(2, 2, 'credit_card', '{"last4": "5678", "brand": "mastercard"}'),
(3, 3, 'paypal', '{"email": "charlie@example.com"}');