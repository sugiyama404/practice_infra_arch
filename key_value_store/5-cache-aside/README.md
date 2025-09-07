# Cache-Aside Pattern KVS

## 概要
読み取り性能最適化のためのキャッシュサイドパターン実装。
Cache Miss時のDB読み込み、TTL管理、キャッシュ無効化戦略を学習。

## アーキテクチャ
- Redis: キャッシュレイヤー
- PostgreSQL: プライマリDB（シミュレーション）
- キー設計: `cache:{entity_type}:{id}`

## 学習ポイント
- Cache-Aside vs Write-Through の使い分け
- TTL設定とキャッシュ無効化戦略
- Cache Warming と Cache Stampede 対策
- 読み取り負荷軽減とレスポンス時間短縮
