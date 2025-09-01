# テーマ
キャッシュ戦略を実践的に学ぶための動画配信サイト構築

## awsのシステム構成

### 概要
動画、サムネイル、お知らせ、動的API（コメント・視聴履歴等）に対して異なるキャッシュ戦略を適用し、CloudFrontを中心としたマルチキャッシュ制御構成を構築。


### 静的コンテンツ（S3 + CloudFront）

| 対象         | オリジン         | CloudFrontキャッシュ設定           | Cache-Control例                                   |
| ---------- | ------------ | --------------------------- | ------------------------------------------------ |
| 動画（.mp4など） | S3           | 長期キャッシュ、バージョン付与             | `public, max-age=31536000, immutable`            |
| サムネイル画像    | S3           | `stale-while-revalidate` 設定 | `public, max-age=600, stale-while-revalidate=60` |
| お知らせHTML   | S3 or Lambda | キャッシュなし（初回表示）               | `private, no-store`                              |

### 動的コンテンツ（API Gateway + Lambda）

| API      | 内容       | キャッシュ戦略 | Cache-Control例                                     |
| -------- | -------- | ------- | -------------------------------------------------- |
| コメントAPI  | 投稿/取得    | 毎回検証あり  | `no-cache, must-revalidate` + `ETag`               |
| レコメンドAPI | ユーザー向け推薦 | 準動的     | `public, max-age=3600, stale-while-revalidate=300` |
| お気に入り履歴  | 個人データ    | キャッシュ不可 | `private, no-store`                                |

### CloudFront設定

| 設定項目 | 値 | 備考 |
| ---- | -- | ---- |
| Price Class | Price_Class_100 | 日本・北米・欧州のみでコスト削減 |
| 最小TTL | 0 | API系は必ずオリジンに問い合わせ |
| デフォルトTTL | 86400 | 静的コンテンツの標準設定 |
| 最大TTL | 31536000 | immutableアセット用 |

### オリジン設定

#### S3オリジン（静的コンテンツ）
- **動画用S3バケット**: 長期保持、バージョニング有効
- **画像用S3バケット**: サムネイル等、適度な更新頻度
- **Origin Access Control (OAC)**: CloudFront経由のみアクセス許可

#### API Gateway オリジン（動的コンテンツ）
- **エンドポイント**: 地域別エンドポイント（ap-northeast-1）
- **カスタムヘッダー**: 認証・CORS設定
- **タイムアウト**: 30秒

### Lambda関数設計

| 関数名 | 機能 | メモリ | タイムアウト | ランタイム |
| ---- | ---- | ---- | ---- | ---- |
| comment-handler | コメント取得・投稿 | 256MB | 10秒 | Python 3.11 |
| recommend-handler | レコメンデーション | 512MB | 15秒 | Python 3.11 |
| user-profile-handler | ユーザー個人データ | 256MB | 5秒 | Python 3.11 |

### セキュリティ設定

#### HTTPS設定
- **SSL証明書**: AWS Certificate Manager使用
- **セキュリティポリシー**: TLSv1.2以上
- **HSTS**: `Strict-Transport-Security: max-age=31536000; includeSubDomains`

#### CORS設定
```json
{
  "AllowedOrigins": ["https://your-domain.com"],
  "AllowedMethods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  "AllowedHeaders": ["Content-Type", "Authorization", "If-None-Match"],
  "ExposeHeaders": ["ETag", "Cache-Control"]
}
```

### 監視・ログ設定

#### CloudWatch設定
- **メトリクス**: キャッシュヒット率、エラー率、レスポンス時間
- **アラーム**: エラー率5%超過、レスポンス時間2秒超過
- **ダッシュボード**: リアルタイムパフォーマンス監視

#### アクセスログ
- **CloudFront**: Standard Logging → S3保存
- **API Gateway**: CloudWatch Logs出力
- **Lambda**: CloudWatch Logs出力

### コスト最適化

#### S3設定
- **ストレージクラス**: 
  - 動画: Standard（アクセス頻度高）
  - 古いサムネイル: IA（30日後自動移行）
- **ライフサイクルポリシー**: 90日後に削除

#### Lambda最適化
- **Provisioned Concurrency**: 本番環境でのみ使用
- **メモリ調整**: パフォーマンステストに基づく最適化
- **実行時間短縮**: 軽量ライブラリ使用

### 災害復旧・可用性

#### マルチAZ構成
- **S3**: クロスリージョンレプリケーション
- **CloudFront**: グローバル配信で自動冗長化
- **Lambda**: マルチAZで自動実行

#### バックアップ戦略
- **S3データ**: バージョニング + クロスリージョンバックアップ
- **DynamoDB**: ポイントインタイムリカバリ有効
- **設定情報**: Infrastructure as Code（Terraform/CDK）

### デプロイメント戦略

#### CI/CD パイプライン
- **GitHub Actions**: コード変更時の自動デプロイ
- **Blue-Green デプロイ**: API Gateway エイリアス使用
- **カナリアリリース**: Lambda バージョニング活用

#### 環境分離
- **dev**: 開発・テスト用（最小構成）
- **staging**: 本番相当環境でのテスト
- **prod**: 本番環境（フルスペック）

### キャッシュ戦略詳細

#### 動画配信戦略
```
動画ファイル命名: video-{content-hash}.mp4
├─ CloudFront: max-age=31536000, immutable
├─ ブラウザ: 1年間キャッシュ
└─ 更新時: 新ファイル名で配信
```

#### サムネイル戦略  
```
サムネイル更新フロー:
1. 新画像をS3にアップロード
2. CloudFrontでstale-while-revalidate
3. ユーザーは古い画像を即座に表示
4. 背景で新画像を取得・キャッシュ更新
```

#### API キャッシュ戦略
```
ETag ベースの条件付きリクエスト:
1. 初回: 200 + ETag レスポンス
2. 再取得: If-None-Match ヘッダー送信
3. 同じ内容: 304 Not Modified
4. 内容変更: 200 + 新ETag
```

### パフォーマンス目標

| メトリクス | 目標値 | 測定方法 |
| ---- | ---- | ---- |
| 動画初期表示 | < 1秒 | CloudWatch RUM |
| サムネイル表示 | < 0.5秒 | Browser DevTools |
| API レスポンス | < 300ms | API Gateway メトリクス |
| キャッシュヒット率 | > 80% | CloudFront メトリクス |