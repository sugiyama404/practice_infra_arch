import React from 'react';

interface PopularTerm {
    term: string;
    category: string;
    popularity: number;
}

interface PopularTermsProps {
    terms: PopularTerm[];
    onTermClick: (term: string) => void;
}

const PopularTerms: React.FC<PopularTermsProps> = ({ terms, onTermClick }) => {
    const getCategoryColor = (category: string): string => {
        const colors: { [key: string]: string } = {
            'Programming': '#4CAF50',
            'Framework': '#2196F3',
            'Database': '#FF9800',
            'Cloud': '#9C27B0',
            'DevOps': '#607D8B',
            'Tool': '#795548',
            'Editor': '#3F51B5',
            'Testing': '#E91E63',
            'Runtime': '#00BCD4',
            'Japanese': '#FF5722',
        };
        return colors[category] || '#666';
    };

    return (
        <div className="popular-terms">
            {terms.length === 0 ? (
                <p className="no-terms">人気ワードがありません</p>
            ) : (
                <div className="terms-grid">
                    {terms.map((term, index) => (
                        <div
                            key={`${term.term}-${index}`}
                            className="term-card"
                            onClick={() => onTermClick(term.term)}
                        >
                            <span className="term-text">{term.term}</span>
                            <span
                                className="term-category"
                                style={{ backgroundColor: getCategoryColor(term.category) }}
                            >
                                {term.category}
                            </span>
                            <div className="popularity-bar">
                                <div
                                    className="popularity-fill"
                                    style={{ width: `${(term.popularity / 100) * 100}%` }}
                                />
                            </div>
                            <span className="popularity-score">{term.popularity}</span>
                        </div>
                    ))}
                </div>
            )}

            <style jsx>{`
        .popular-terms {
          width: 100%;
        }

        .no-terms {
          text-align: center;
          color: #666;
          font-style: italic;
          padding: 2rem;
        }

        .terms-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 1rem;
        }

        .term-card {
          background: white;
          border: 1px solid #e0e0e0;
          border-radius: 12px;
          padding: 1rem;
          cursor: pointer;
          transition: all 0.2s ease;
          position: relative;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .term-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
          border-color: #ccc;
        }

        .term-text {
          font-size: 1.1rem;
          font-weight: 600;
          color: #333;
        }

        .term-category {
          color: white;
          padding: 4px 8px;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 500;
          align-self: flex-start;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .popularity-bar {
          height: 4px;
          background: #f0f0f0;
          border-radius: 2px;
          overflow: hidden;
          margin: 0.25rem 0;
        }

        .popularity-fill {
          height: 100%;
          background: linear-gradient(90deg, #4CAF50, #8BC34A);
          transition: width 0.3s ease;
        }

        .popularity-score {
          font-size: 0.85rem;
          color: #666;
          font-weight: 500;
          text-align: right;
        }

        @media (max-width: 768px) {
          .terms-grid {
            grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
            gap: 0.75rem;
          }

          .term-card {
            padding: 0.75rem;
          }
        }

        @media (max-width: 480px) {
          .terms-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
        </div>
    );
};

export default PopularTerms;
