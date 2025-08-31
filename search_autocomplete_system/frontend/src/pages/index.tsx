import { useState, useEffect, useRef } from 'react';
import SearchBox from '../components/SearchBox';
import PopularTerms from '../components/PopularTerms';

interface Suggestion {
    term: string;
    category: string;
    popularity: number;
}

interface PopularTerm {
    term: string;
    category: string;
    popularity: number;
}

export default function Home() {
    const [popularTerms, setPopularTerms] = useState<PopularTerm[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchPopularTerms();
    }, []);

    const fetchPopularTerms = async () => {
        try {
            setLoading(true);
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/popular?limit=10`);
            const data = await response.json();
            setPopularTerms(data.popular_terms || []);
        } catch (error) {
            console.error('人気ワードの取得に失敗:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = async (searchTerm: string) => {
        // 検索履歴を保存
        try {
            await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/history`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    term: searchTerm,
                    session: 'demo-session-' + Date.now()
                }),
            });
        } catch (error) {
            console.error('検索履歴の保存に失敗:', error);
        }

        // 実際の検索処理（ここでは単純にアラート表示）
        alert(`検索: "${searchTerm}"`);
    };

    return (
        <div className="container">
            <header className="header">
                <h1>検索オートコンプリート</h1>
                <p>Next.js + Flask + MySQL構成のデモ</p>
            </header>

            <main className="main">
                <div className="search-section">
                    <SearchBox onSearch={handleSearch} />
                </div>

                <div className="popular-section">
                    <h2>人気の検索ワード</h2>
                    {loading ? (
                        <div className="loading">読み込み中...</div>
                    ) : (
                        <PopularTerms terms={popularTerms} onTermClick={handleSearch} />
                    )}
                </div>
            </main>

            <style jsx>{`
        .container {
          min-height: 100vh;
          padding: 0 0.5rem;
          display: flex;
          flex-direction: column;
          justify-content: flex-start;
          align-items: center;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Oxygen,
            Ubuntu, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;
        }

        .header {
          text-align: center;
          margin: 2rem 0;
          color: white;
        }

        .header h1 {
          font-size: 3rem;
          margin: 0.5rem 0;
          font-weight: 300;
        }

        .header p {
          font-size: 1.2rem;
          opacity: 0.8;
          margin: 0;
        }

        .main {
          flex: 1;
          width: 100%;
          max-width: 800px;
        }

        .search-section {
          margin: 2rem 0;
        }

        .popular-section {
          background: rgba(255, 255, 255, 0.95);
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
          backdrop-filter: blur(4px);
          border: 1px solid rgba(255, 255, 255, 0.18);
        }

        .popular-section h2 {
          color: #333;
          margin: 0 0 1.5rem 0;
          font-size: 1.5rem;
          font-weight: 500;
        }

        .loading {
          text-align: center;
          padding: 2rem;
          color: #666;
          font-size: 1.1rem;
        }

        @media (max-width: 600px) {
          .header h1 {
            font-size: 2rem;
          }
          
          .popular-section {
            margin: 1rem;
            padding: 1.5rem;
          }
        }
      `}</style>
        </div>
    );
}
