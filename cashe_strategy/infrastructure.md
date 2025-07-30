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





