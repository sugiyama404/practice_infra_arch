USE user_service;

CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(80) UNIQUE NOT NULL,
    balance DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    reserved_balance DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS balance_transactions (
    id VARCHAR(36) PRIMARY KEY,
    user_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'reserved',
    transaction_id VARCHAR(36) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

INSERT IGNORE INTO users (id, username, balance) VALUES
(1, 'alice', 1000.00),
(2, 'bob', 500.00),
(3, 'charlie', 2000.00);
