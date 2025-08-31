from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# データベース設定
DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://search_user:password123@localhost:3306/search_db')

def create_db_engine():
    """データベースエンジンを作成（再試行ロジック付き）"""
    max_retries = 30
    retry_interval = 2
    
    for attempt in range(max_retries):
        try:
            engine = create_engine(DATABASE_URL)
            # 接続テスト
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("データベース接続成功")
            return engine
        except OperationalError as e:
            logger.warning(f"データベース接続失敗 (試行 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
            else:
                raise

engine = create_db_engine()

@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return jsonify({"status": "healthy", "database": "connected"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_autocomplete():
    """検索オートコンプリートAPI"""
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 10))
    
    if not query:
        return jsonify({"suggestions": []})
    
    try:
        with engine.connect() as conn:
            # LIKE検索でオートコンプリート候補を取得
            sql = text("""
                SELECT term, category, popularity_score
                FROM search_terms 
                WHERE term LIKE :query 
                ORDER BY popularity_score DESC, term ASC 
                LIMIT :limit
            """)
            
            result = conn.execute(sql, {
                'query': f'{query}%',
                'limit': limit
            })
            
            suggestions = []
            for row in result:
                suggestions.append({
                    'term': row.term,
                    'category': row.category,
                    'popularity': row.popularity_score
                })
            
            return jsonify({"suggestions": suggestions})
            
    except Exception as e:
        logger.error(f"検索エラー: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/popular', methods=['GET'])
def get_popular_terms():
    """人気の検索ワードを取得"""
    limit = int(request.args.get('limit', 10))
    
    try:
        with engine.connect() as conn:
            sql = text("""
                SELECT term, category, popularity_score
                FROM search_terms 
                ORDER BY popularity_score DESC 
                LIMIT :limit
            """)
            
            result = conn.execute(sql, {'limit': limit})
            
            popular_terms = []
            for row in result:
                popular_terms.append({
                    'term': row.term,
                    'category': row.category,
                    'popularity': row.popularity_score
                })
            
            return jsonify({"popular_terms": popular_terms})
            
    except Exception as e:
        logger.error(f"人気ワード取得エラー: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/history', methods=['POST'])
def save_search_history():
    """検索履歴を保存"""
    data = request.get_json()
    search_term = data.get('term')
    user_session = data.get('session', 'anonymous')
    
    if not search_term:
        return jsonify({"error": "検索ワードが必要です"}), 400
    
    try:
        with engine.connect() as conn:
            # 既存の履歴があるかチェック
            check_sql = text("""
                SELECT id, search_count 
                FROM search_history 
                WHERE search_term = :term AND user_session = :session
            """)
            
            result = conn.execute(check_sql, {
                'term': search_term,
                'session': user_session
            })
            
            existing = result.fetchone()
            
            if existing:
                # 既存レコードのカウントを更新
                update_sql = text("""
                    UPDATE search_history 
                    SET search_count = search_count + 1, last_searched = CURRENT_TIMESTAMP
                    WHERE id = :id
                """)
                conn.execute(update_sql, {'id': existing.id})
            else:
                # 新しいレコードを挿入
                insert_sql = text("""
                    INSERT INTO search_history (search_term, user_session, search_count)
                    VALUES (:term, :session, 1)
                """)
                conn.execute(insert_sql, {
                    'term': search_term,
                    'session': user_session
                })
            
            conn.commit()
            return jsonify({"status": "success"})
            
    except Exception as e:
        logger.error(f"履歴保存エラー: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
