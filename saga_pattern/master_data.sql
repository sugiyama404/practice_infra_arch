-- ============================================
-- マスタデータ投入スクリプト (MySQL)
-- ============================================

USE cloudmart_saga;

-- 顧客マスタデータ（5名）
INSERT INTO customers (customer_id, name, email, phone, address, created_at) VALUES
('customer-001', '田中太郎', 'tanaka@example.com', '090-1234-5678',
 JSON_OBJECT('postcode', '150-0041', 'address', '東京都渋谷区神南1-1-1'),
 CURRENT_TIMESTAMP),
('customer-002', '佐藤花子', 'sato@example.com', '090-2345-6789',
 JSON_OBJECT('postcode', '100-0005', 'address', '東京都千代田区丸の内1-1-1'),
 CURRENT_TIMESTAMP),
('customer-003', '鈴木次郎', 'suzuki@example.com', '090-3456-7890',
 JSON_OBJECT('postcode', '220-0012', 'address', '神奈川県横浜市西区みなとみらい1-1-1'),
 CURRENT_TIMESTAMP),
('customer-004', '高橋美咲', 'takahashi@example.com', '090-4567-8901',
 JSON_OBJECT('postcode', '530-0001', 'address', '大阪府大阪市北区梅田1-1-1'),
 CURRENT_TIMESTAMP),
('customer-005', '伊藤健太', 'ito@example.com', '090-5678-9012',
 JSON_OBJECT('postcode', '450-0002', 'address', '愛知県名古屋市中村区名駅1-1-1'),
 CURRENT_TIMESTAMP);

-- 書籍マスタデータ（5冊 - IT技術書中心）
INSERT INTO books (book_id, title, author, isbn, price, category, description, created_at) VALUES
('book-123', 'マイクロサービスアーキテクチャ', 'Martin Fowler', '978-4621303251', 3500.00, '技術書',
 'マイクロサービスアーキテクチャの設計原則と実践的なパターンを解説', CURRENT_TIMESTAMP),
('book-456', '分散システム設計', 'Kyle Kingsbury', '978-4873119946', 8000.00, '技術書',
 '分散システムの設計と実装における課題と解決策', CURRENT_TIMESTAMP),
('book-789', 'クラウドネイティブ開発', 'John Arundel', '978-4873119038', 4200.00, '技術書',
 'クラウドネイティブアプリケーションの開発手法とベストプラクティス', CURRENT_TIMESTAMP),
('book-101', 'データベース設計の極意', 'Michael Hernandez', '978-4798155092', 4200.00, '技術書',
 'リレーショナルデータベースの設計原則と実践テクニック', CURRENT_TIMESTAMP),
('book-202', 'Kubernetes完全ガイド', 'Brendan Burns', '978-4873118406', 4800.00, '技術書',
 'Kubernetesの概念から実践的な運用までを網羅したガイドブック', CURRENT_TIMESTAMP);

-- 在庫マスタデータ（現実的な在庫数設定）
INSERT INTO inventory (book_id, available_stock, reserved_stock, reorder_point, location, updated_at) VALUES
('book-123', 5, 0, 2, '倉庫A-1', CURRENT_TIMESTAMP),
('book-456', 0, 0, 1, '倉庫A-2', CURRENT_TIMESTAMP),  -- 在庫切れパターン
('book-789', 10, 0, 3, '倉庫B-1', CURRENT_TIMESTAMP),
('book-101', 3, 0, 2, '倉庫B-2', CURRENT_TIMESTAMP),
('book-202', 7, 0, 2, '倉庫C-1', CURRENT_TIMESTAMP);

SELECT 'マスタデータ投入完了' as status;
