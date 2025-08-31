CREATE DATABASE IF NOT EXISTS search_db;
USE search_db;

-- 検索候補用のテーブル
CREATE TABLE search_terms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    term VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    popularity_score INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_term (term),
    INDEX idx_category (category),
    INDEX idx_popularity (popularity_score DESC)
);

-- 検索履歴テーブル
CREATE TABLE search_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    search_term VARCHAR(255) NOT NULL,
    user_session VARCHAR(255),
    search_count INT DEFAULT 1,
    last_searched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (user_session),
    INDEX idx_term_history (search_term),
    INDEX idx_last_searched (last_searched DESC)
);

-- サンプルデータの挿入
INSERT INTO search_terms (term, category, popularity_score) VALUES
-- プログラミング関連
('JavaScript', 'Programming', 95),
('Python', 'Programming', 92),
('React', 'Framework', 88),
('Next.js', 'Framework', 85),
('TypeScript', 'Programming', 82),
('Node.js', 'Runtime', 80),
('Vue.js', 'Framework', 78),
('Angular', 'Framework', 75),
('Express.js', 'Framework', 72),
('Flask', 'Framework', 70),

-- データベース関連
('MySQL', 'Database', 85),
('PostgreSQL', 'Database', 80),
('MongoDB', 'Database', 75),
('Redis', 'Database', 70),
('SQLite', 'Database', 65),

-- クラウド関連
('AWS', 'Cloud', 90),
('Docker', 'DevOps', 85),
('Kubernetes', 'DevOps', 80),
('Azure', 'Cloud', 75),
('GCP', 'Cloud', 70),

-- ツール関連
('Git', 'Tool', 95),
('VS Code', 'Editor', 90),
('Webpack', 'Tool', 75),
('ESLint', 'Tool', 70),
('Jest', 'Testing', 68),

-- 日本語の検索語も追加
('検索', 'Japanese', 60),
('オートコンプリート', 'Japanese', 55),
('データベース', 'Japanese', 50),
('ウェブ開発', 'Japanese', 45),
('プログラミング', 'Japanese', 40);

-- 検索履歴のサンプルデータ
INSERT INTO search_history (search_term, user_session, search_count) VALUES
('JavaScript', 'session_001', 5),
('React', 'session_001', 3),
('Python', 'session_002', 7),
('MySQL', 'session_002', 2),
('Next.js', 'session_003', 4);
