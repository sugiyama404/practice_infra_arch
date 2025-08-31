from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time
import json
import redis
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import logging
from pytrie import StringTrie
from typing import List, Dict, Tuple

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 設定
DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://search_user:password123@localhost:3306/search_db')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# グローバル変数
trie = StringTrie()
redis_client = None
engine = None

class TrieNode:
    """カスタムTrieノード（人気度スコア付き）"""
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False
        self.term_data = None  # {'term': str, 'category': str, 'popularity': int}

class SearchTrie:
    """カスタム検索用Trie実装"""
    def __init__(self):
        self.root = TrieNode()
    
    def insert(self, term: str, category: str, popularity: int):
        """用語をTrieに挿入"""
        node = self.root
        for char in term.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        
        node.is_end_of_word = True
        node.term_data = {
            'term': term,
            'category': category,
            'popularity': popularity
        }
    
    def search_prefix(self, prefix: str, limit: int = 10) -> List[Dict]:
        """プレフィックス検索（人気度順）"""
        if not prefix:
            return []
        
        # プレフィックスのノードを見つける
        node = self.root
        for char in prefix.lower():
            if char not in node.children:
                return []
            node = node.children[char]
        
        # DFSでマッチする全用語を収集
        results = []
        self._collect_words(node, results)
        
        # 人気度順でソート
        results.sort(key=lambda x: (-x['popularity'], x['term']))
        
        return results[:limit]
    
    def _collect_words(self, node: TrieNode, results: List[Dict]):
        """DFSで単語を収集"""
        if node.is_end_of_word and node.term_data:
            results.append(node.term_data)
        
        for child in node.children.values():
            self._collect_words(child, results)

# グローバルインスタンス
search_trie = SearchTrie()

def create_redis_connection():
    """Redis接続を作成（再試行ロジック付き）"""
    max_retries = 10
    retry_interval = 2
    
    for attempt in range(max_retries):
        try:
            client = redis.from_url(REDIS_URL, decode_responses=True)
            # 接続テスト
            client.ping()
            logger.info("Redis接続成功")
            return client
        except redis.ConnectionError as e:
            logger.warning(f"Redis接続失敗 (試行 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
            else:
                logger.error("Redis接続に失敗しました。キャッシュ機能は無効になります。")
                return None

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

def load_data_to_trie():
    """データベースからデータを読み込んでTrieに格納"""
    global search_trie
    
    try:
        with engine.connect() as conn:
            sql = text("""
                SELECT term, category, popularity_score
                FROM search_terms 
                ORDER BY term
            """)
            
            result = conn.execute(sql)
            count = 0
            
            for row in result:
                search_trie.insert(row.term, row.category, row.popularity_score)
                count += 1
            
            logger.info(f"Trieに{count}個の検索用語をロードしました")
            
    except Exception as e:
        logger.error(f"Trieデータロードエラー: {e}")
        raise

def get_cache_key(endpoint: str, **params) -> str:
    """キャッシュキーを生成"""
    if params:
        param_str = "_".join([f"{k}:{v}" for k, v in sorted(params.items())])
        return f"{endpoint}:{param_str}"
    return endpoint

def get_from_cache(key: str):
    """Redisキャッシュから取得"""
    if not redis_client:
        return None
    
    try:
        cached_data = redis_client.get(key)
        if cached_data:
            return json.loads(cached_data)
        return None
    except Exception as e:
        logger.warning(f"キャッシュ取得エラー: {e}")
        return None

def set_cache(key: str, data: dict, ttl: int = 300):
    """Redisキャッシュに保存（デフォルト5分）"""
    if not redis_client:
        return
    
    try:
        redis_client.setex(key, ttl, json.dumps(data))
    except Exception as e:
        logger.warning(f"キャッシュ保存エラー: {e}")

def init_app():
    """アプリケーション初期化"""
    global engine, redis_client
    
    # データベース接続
    engine = create_db_engine()
    
    # Redis接続
    redis_client = create_redis_connection()
    
    # Trieデータロード
    load_data_to_trie()

# アプリケーション初期化
init_app()

@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    status = {"status": "healthy"}
    
    # データベース接続チェック
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["database"] = "connected"
    except Exception as e:
        status["database"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    # Redis接続チェック
    if redis_client:
        try:
            redis_client.ping()
            status["redis"] = "connected"
        except Exception as e:
            status["redis"] = f"error: {str(e)}"
            status["status"] = "degraded"
    else:
        status["redis"] = "not available"
        status["status"] = "degraded"
    
    # Trie状態チェック
    status["trie"] = "loaded"
    
    return jsonify(status), 200 if status["status"] == "healthy" else 503

@app.route('/api/search', methods=['GET'])
def search_autocomplete():
    """検索オートコンプリートAPI（Trie + Redisキャッシュ）"""
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 10))
    
    if not query:
        return jsonify({"suggestions": []})
    
    # キャッシュキーを生成
    cache_key = get_cache_key("search", q=query, limit=limit)
    
    # まずキャッシュから取得を試行
    cached_result = get_from_cache(cache_key)
    if cached_result:
        logger.info(f"キャッシュヒット: {cache_key}")
        return jsonify(cached_result)
    
    try:
        # Trieで検索
        suggestions = search_trie.search_prefix(query, limit)
        
        result = {"suggestions": suggestions}
        
        # 結果をキャッシュに保存（1分間）
        set_cache(cache_key, result, ttl=60)
        
        logger.info(f"Trie検索完了: query='{query}', results={len(suggestions)}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"検索エラー: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/popular', methods=['GET'])
def get_popular_terms():
    """人気の検索ワードを取得（Redisキャッシュ対応）"""
    limit = int(request.args.get('limit', 10))
    
    # キャッシュキーを生成
    cache_key = get_cache_key("popular", limit=limit)
    
    # まずキャッシュから取得を試行
    cached_result = get_from_cache(cache_key)
    if cached_result:
        logger.info(f"キャッシュヒット: {cache_key}")
        return jsonify(cached_result)
    
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
            
            response_data = {"popular_terms": popular_terms}
            
            # 結果をキャッシュに保存（5分間）
            set_cache(cache_key, response_data, ttl=300)
            
            return jsonify(response_data)
            
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

@app.route('/api/admin/rebuild-trie', methods=['POST'])
def rebuild_trie():
    """Trieを再構築する管理用エンドポイント"""
    try:
        global search_trie
        search_trie = SearchTrie()
        load_data_to_trie()
        
        # キャッシュもクリア
        if redis_client:
            try:
                redis_client.flushdb()
                logger.info("キャッシュをクリアしました")
            except Exception as e:
                logger.warning(f"キャッシュクリアエラー: {e}")
        
        return jsonify({"status": "success", "message": "Trieを再構築しました"})
        
    except Exception as e:
        logger.error(f"Trie再構築エラー: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/clear-cache', methods=['POST'])
def clear_cache():
    """キャッシュをクリアする管理用エンドポイント"""
    if not redis_client:
        return jsonify({"error": "Redisが利用できません"}), 503
    
    try:
        redis_client.flushdb()
        return jsonify({"status": "success", "message": "キャッシュをクリアしました"})
        
    except Exception as e:
        logger.error(f"キャッシュクリアエラー: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
def get_stats():
    """システム統計情報を取得"""
    stats = {}
    
    # データベース統計
    try:
        with engine.connect() as conn:
            # 検索用語数
            result = conn.execute(text("SELECT COUNT(*) as count FROM search_terms"))
            stats["total_search_terms"] = result.fetchone().count
            
            # 検索履歴数
            result = conn.execute(text("SELECT COUNT(*) as count FROM search_history"))
            stats["total_search_history"] = result.fetchone().count
            
    except Exception as e:
        stats["database_error"] = str(e)
    
    # Redis統計
    if redis_client:
        try:
            info = redis_client.info()
            stats["redis"] = {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "N/A"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            stats["redis_error"] = str(e)
    else:
        stats["redis"] = "not available"
    
    return jsonify(stats)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
