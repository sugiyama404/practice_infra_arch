# Leaderboard (Ranking System) Pattern

## 概要
RedisのSorted Setを活用したリアルタイムランキングシステムの実装。
スコアの更新、ランキングの取得、特定ユーザーの順位確認などを学習。

## アーキテクチャ
- Redis Sorted Set: メンバー（ユーザーID）とスコアを効率的に管理
- キー設計: `leaderboard:{game_id}`

## 学習ポイント
- Sorted Setの`ZADD`, `ZREVRANGE`, `ZRANK`コマンドの活用
- 同点スコアの処理
- 大規模ランキングのパフォーマンス最適化（ページネーション）
- 複数ランキングの管理
