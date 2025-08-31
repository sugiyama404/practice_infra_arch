## テーマ
高速 & 低コストな検索オートコンプリート (目標: P95 < 200ms / 月額 < $150)

## 全体概要
AWSマネージドサービス + 多層キャッシュ (Browser / CloudFront / Redis / OpenSearch) により最小構成でスケール可能な検索 API を提供。Redis を第一応答層、OpenSearch を候補生成、RDS を正本データ & ログ蓄積に限定し責務を明確化。

## アーキテクチャ
```
User
  │
  ├─→ CloudFront ──→ S3 (静的配信)
  │
  └─→ ALB ──→ ECS (Fargate: API)
                   │
                   ├─→ Redis (キャッシュ)
                   ├─→ OpenSearch (検索エンジン)
                   └─→ RDS (MySQL: データベース)
```

## コンポーネント要約
| 層 | サービス | 主要役割 | 最小構成 | 主なスケール指標 |
|----|----------|----------|----------|------------------|
| 配信 | CloudFront + S3 | 静的配信 & エッジキャッシュ | S3 + デフォルトディストリ | キャッシュヒット率 |
| 入口 | ALB | ルーティング / TLS | 1 ALB | TargetResponseTime |
| アプリ | ECS Fargate | Flask API | 2タスク (0.25vCPU/0.5GB) | CPU 70% / RPS |
| キャッシュ | Redis (ElastiCache) | 検索候補/人気語キャッシュ | t3.micro 1ノード | CacheHitRate / Evictions |
| 検索 | OpenSearch | 補完 / 重い検索 | t3.small 1ノード | SearchLatency |
| 永続 | RDS MySQL | ログ & メタ | db.t3.micro 20GB | CPU / 接続数 |

概算コスト合計: 約 $110〜150/月 (低負荷想定)

## キャッシュ戦略 (要点)
1. Browser: 検索結果 60s / 人気ワード 300s
2. CloudFront: /api/popular を 300s Edge キャッシュ, /api/search はパススルー
3. Redis: search:{query} 10分 / popular:all 60分 / user:history:* 5分
4. OpenSearch: 内部クエリキャッシュ (同一クエリ <10分)
5. TTL短 + 冪等再生成可能データのみキャッシュ

失効: 人気ワード再計算時 popular:* 削除 → (必要なら) CloudFront invalidation /api/popular*

## 性能指標 (SLO)
| API | 目標 P95 | 根拠 |
|-----|---------|------|
| /api/search | < 200ms | 80% Redis Hit, Miss時 ~120–180ms |
| /api/popular | < 100ms | ほぼ 100% キャッシュヒット |
| /api/history | < 150ms | 単純 KV / SQL 1回 |

最適化手段: キャッシュプリフェッチ (人気語 Cron 1h), 接続プール, gzip & JSON最小化, バッチインデックス更新 (夜間)

## スケール戦略
水平: ECS タスク 2→10 (CPU 70% しきい値), OpenSearch 1→3 ノード (RPS/Latency), Redis 1ノード→大きいクラス
垂直: t3.* → t3.small / medium へ段階増強
データ: OpenSearch レプリカ 0→1 (可用性要求上昇時)

## セキュリティ / 運用
- VPC: Public(Alb) / Private(ECS, Redis, OpenSearch, RDS) 分離
- IAM: 最小権限制御 + Secrets Manager で DSN 管理
- 暗号化: at-rest (RDS/Redis/OpenSearch) & in-transit (TLS)
- WAF: 基本ルール (SQLi / XSS) 適用

## DR / 可用性
- RDS: 自動バックアップ 7日 / PITR
- OpenSearch: 日次スナップショット (S3)
- Redis: AOF 有効 / 再構築スクリプト (人気語再集計)
- RPO: 24h (検索候補再生成可) / RTO: < 4h 目標

## キーポイントまとめ
- キャッシュ段階的フォールバック: Redis → OpenSearch → RDS
- コスト最適: シングル AZ / 単一ノード開始 → 指標連動で段階拡張
- シンプルな TTL & 失効ポリシーで一貫性よりレイテンシ最適化
- 最小メトリクス & アラートで早期劣化検知
