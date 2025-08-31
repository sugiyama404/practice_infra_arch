import { useState, useRef, useEffect } from 'react';
import { useDebounce } from '../hooks/useDebounce';

interface Suggestion {
    term: string;
    category: string;
    popularity: number;
}

interface SearchBoxProps {
    onSearch: (searchTerm: string) => void;
}

const SearchBox: React.FC<SearchBoxProps> = ({ onSearch }) => {
    const [query, setQuery] = useState('');
    const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const [loading, setLoading] = useState(false);

    const inputRef = useRef<HTMLInputElement>(null);
    const suggestionRefs = useRef<(HTMLLIElement | null)[]>([]);

    // デバウンス処理
    const debouncedQuery = useDebounce(query, 300);

    // 検索候補を取得
    useEffect(() => {
        const fetchSuggestions = async () => {
            if (!debouncedQuery.trim()) {
                setSuggestions([]);
                setShowSuggestions(false);
                return;
            }

            try {
                setLoading(true);
                const response = await fetch(
                    `${process.env.NEXT_PUBLIC_API_URL}/api/search?q=${encodeURIComponent(debouncedQuery)}&limit=8`
                );
                const data = await response.json();
                setSuggestions(data.suggestions || []);
                setShowSuggestions(true);
                setSelectedIndex(-1);
            } catch (error) {
                console.error('検索候補の取得に失敗:', error);
                setSuggestions([]);
            } finally {
                setLoading(false);
            }
        };

        fetchSuggestions();
    }, [debouncedQuery]);

    // キーボード操作
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (!showSuggestions) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setSelectedIndex(prev =>
                    prev < suggestions.length - 1 ? prev + 1 : prev
                );
                break;
            case 'ArrowUp':
                e.preventDefault();
                setSelectedIndex(prev => prev > -1 ? prev - 1 : -1);
                break;
            case 'Enter':
                e.preventDefault();
                if (selectedIndex >= 0) {
                    handleSuggestionClick(suggestions[selectedIndex].term);
                } else if (query.trim()) {
                    handleSearch();
                }
                break;
            case 'Escape':
                setShowSuggestions(false);
                setSelectedIndex(-1);
                inputRef.current?.blur();
                break;
        }
    };

    // 検索実行
    const handleSearch = () => {
        if (query.trim()) {
            onSearch(query.trim());
            setShowSuggestions(false);
            setSelectedIndex(-1);
        }
    };

    // 候補クリック時
    const handleSuggestionClick = (term: string) => {
        setQuery(term);
        onSearch(term);
        setShowSuggestions(false);
        setSelectedIndex(-1);
    };

    // 入力フィールドの変更
    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setQuery(e.target.value);
    };

    // フォーカス時
    const handleFocus = () => {
        if (suggestions.length > 0) {
            setShowSuggestions(true);
        }
    };

    // ブラー時（遅延してhide）
    const handleBlur = () => {
        setTimeout(() => {
            setShowSuggestions(false);
            setSelectedIndex(-1);
        }, 150);
    };

    return (
        <div className="search-container">
            <div className="search-box">
                <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    onFocus={handleFocus}
                    onBlur={handleBlur}
                    placeholder="検索ワードを入力..."
                    className="search-input"
                />
                <button
                    onClick={handleSearch}
                    className="search-button"
                    disabled={!query.trim()}
                >
                    🔍
                </button>
            </div>

            {showSuggestions && (
                <div className="suggestions-container">
                    {loading ? (
                        <div className="loading-suggestion">
                            検索中...
                        </div>
                    ) : suggestions.length > 0 ? (
                        <ul className="suggestions-list">
                            {suggestions.map((suggestion, index) => (
                                <li
                                    key={`${suggestion.term}-${index}`}
                                    ref={el => suggestionRefs.current[index] = el}
                                    className={`suggestion-item ${index === selectedIndex ? 'selected' : ''
                                        }`}
                                    onClick={() => handleSuggestionClick(suggestion.term)}
                                >
                                    <span className="suggestion-term">{suggestion.term}</span>
                                    <span className="suggestion-category">{suggestion.category}</span>
                                </li>
                            ))}
                        </ul>
                    ) : debouncedQuery.trim() && (
                        <div className="no-suggestions">
                            検索結果が見つかりません
                        </div>
                    )}
                </div>
            )}

            <style jsx>{`
        .search-container {
          position: relative;
          width: 100%;
        }

        .search-box {
          display: flex;
          background: white;
          border-radius: 24px;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
          overflow: hidden;
          transition: box-shadow 0.2s ease;
        }

        .search-box:focus-within {
          box-shadow: 0 4px 30px rgba(0, 0, 0, 0.15);
        }

        .search-input {
          flex: 1;
          padding: 16px 20px;
          border: none;
          outline: none;
          font-size: 16px;
          background: transparent;
        }

        .search-input::placeholder {
          color: #999;
        }

        .search-button {
          padding: 16px 20px;
          border: none;
          background: transparent;
          cursor: pointer;
          font-size: 18px;
          transition: background-color 0.2s ease;
        }

        .search-button:hover:not(:disabled) {
          background: rgba(0, 0, 0, 0.05);
        }

        .search-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .suggestions-container {
          position: absolute;
          top: 100%;
          left: 0;
          right: 0;
          background: white;
          border-radius: 12px;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
          z-index: 1000;
          margin-top: 8px;
          overflow: hidden;
        }

        .suggestions-list {
          list-style: none;
          padding: 0;
          margin: 0;
          max-height: 300px;
          overflow-y: auto;
        }

        .suggestion-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 20px;
          cursor: pointer;
          transition: background-color 0.2s ease;
          border-bottom: 1px solid #f0f0f0;
        }

        .suggestion-item:last-child {
          border-bottom: none;
        }

        .suggestion-item:hover,
        .suggestion-item.selected {
          background: #f8f9ff;
        }

        .suggestion-term {
          font-weight: 500;
          color: #333;
        }

        .suggestion-category {
          font-size: 12px;
          color: #666;
          background: #f0f0f0;
          padding: 4px 8px;
          border-radius: 12px;
        }

        .loading-suggestion,
        .no-suggestions {
          padding: 16px 20px;
          text-align: center;
          color: #666;
          font-style: italic;
        }

        @media (max-width: 600px) {
          .search-input {
            font-size: 16px; /* iOS zoom防止 */
          }
        }
      `}</style>
        </div>
    );
};

export default SearchBox;
