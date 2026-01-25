# キャッシュ戦略学習用 動画配信サイト README

> キャッシュ制御ヘッダーと AWS（CloudFront / S3 / Lambda / API Gateway 等）を実践的に組み合わせ、静的・準動的・動的コンテンツそれぞれに最適な戦略を適用するための学習リポジトリ。

---
## 1. ゴール / 学習観点
- 異種コンテンツ（動画・サムネイル・お知らせ・コメント・個別ユーザーデータ）毎に **異なる TTL / 再検証 / 可視性スコープ** を設計できる
- `Cache-Control`, `ETag`, `Age`, `X-Cache`, `Vary` などを DevTools / curl で読み解ける
- CloudFront の **複数ビヘイビア / オリジン構成 / 署名URL or OAC / Invalidation / バージョニング** の意思決定根拠を説明できる
- コスト / パフォーマンス / セキュリティ / 運用容易性 のバランスを取る設計判断が言語化できる

---
## 2. 想定利用規模（検証用）
| 項目 | 想定値 |
| ---- | ------ |
| 月間ユニークユーザー | ~1,000 |
| 同時接続 | 10〜50 |
| 動画本数 | 50〜100（数 GB） |
| 目的 | 技術検証 / ポートフォリオ |

---
## 3. 全体アーキテクチャ概要
```
[User]
  │ HTTPS (CloudFront)
  ▼
+ CloudFront (複数ビヘイビア)
  ├─ /videos/*      -> S3 (動画バケット, Versioned)
  ├─ /thumbnails/*  -> S3 (画像バケット, SWR戦略)
  ├─ /notice        -> S3 or Lambda@Edge (一度表示 / no-store)
  ├─ /api/comments  -> API Gateway -> Lambda -> DynamoDB (ETag/再検証)
  ├─ /api/recommend -> API Gateway -> Lambda (準動的: SWR)
  └─ /api/favorites -> API Gateway -> Lambda -> DynamoDB (private)
```
図: `aws.png` / `aws.drawio` を参照

---
## 4. コンテンツ種別とキャッシュ戦略マトリクス
| 種別 | 性質 | 配信元 | 目的 | 推奨 `Cache-Control` | 補助ヘッダ / メモ |
| ---- | ---- | ------ | ---- | -------------------- | ------------------ |
| 動画 (.mp4) | 大容量 / ほぼ不変 | S3 | 帯域節約 / 高速配信 | `public, max-age=31536000, immutable` | ファイル名にハッシュ (`video-<digest>.mp4`) |
| サムネイル | 中頻度更新 | S3 | 即時表示 + 背景更新 | `public, max-age=600, stale-while-revalidate=60` | 差し替えはオブジェクト上書き or バージョンパス |
| お知らせ (初回のみ) | 小容量 / セッション依存 | S3 or Lambda@Edge | 一度のみ表示制御 | `private, no-store` | Cookie / localStorage フラグ管理 |
| コメントAPI | 高頻度更新 | API Gateway + Lambda | データ整合性重視 | `no-cache, must-revalidate` | `ETag` (response hash) / 条件付き GET |
| レコメンドAPI | 準動的生成 | API Gateway + Lambda | 適度な遅延許容 | `public, max-age=3600, stale-while-revalidate=300` | 背景で再計算・キャッシュ更新 |
| お気に入り / 視聴履歴 | 個人データ / 機密 | API Gateway + Lambda | プライバシー保護 | `private, no-store` | 認証必須 / CDN素通し設定 |

---
## 5. HTTP キャッシュ制御詳細
### 5.1 基本指針
- **変更頻度 × 取得コスト × ユーザー体験 × 整合性要求** の組み合わせで TTL / SWR / Revalidation を決定
- 破壊的変更は **ファイル名バージョニング（content-hash）** 前提で `immutable` を付与
- プライベートデータは `private` または `no-store` で CDN キャッシュを回避
- API は ETag + 条件付きリクエストで帯域削減と整合性を両立

### 5.2 代表ヘッダ例
```
# 動画
Cache-Control: public, max-age=31536000, immutable

# サムネイル（SWR）
Cache-Control: public, max-age=600, stale-while-revalidate=60

# お知らせ（一度のみ）
Cache-Control: private, no-store

# コメントAPI（整合性）
Cache-Control: no-cache, must-revalidate
ETag: "<sha256-body>"

# レコメンドAPI（準動的）
Cache-Control: public, max-age=3600, stale-while-revalidate=300

# 個人データ
Cache-Control: private, no-store
```

### 5.3 ETag 運用戦略
- **Strong ETag**: Lambda レスポンス生成後にレスポンス body の SHA-256 ハッシュ（先頭12桁）を計算
- **Weak ETag**: 大容量コンテンツでは最終更新時刻ベース（`W/"timestamp"`）も選択肢
- **クライアント動作**: 次回リクエスト時に `If-None-Match: "<etag-value>"` ヘッダーを送信
- **サーバー判定**: ETag 一致時は `304 Not Modified` + 空body、不一致時は `200 OK` + 新ETag を返却

### 5.4 Conditional Requests / Revalidation
| シナリオ | メソッド | 判定 | 戻り値 |
| -------- | -------- | ---- | ------ |
| コメント読み込み | GET + If-None-Match | ETag一致 | 304 / 空body |
| コメント変更後 | 次回GET | ETag不一致 | 200 / 新ETag |

---
## 6. CloudFront 設計ポイント
| 項目 | 方針 |
| ---- | ---- |
| オリジン | S3(静的), API Gateway(動的) 分離 |
| ビヘイビア | パスプレフィックス毎（/videos/, /thumbnails/, /api/...）|
| キャッシュポリシー | 動画専用LongTTL, 画像SWR, API最小TTL=0| 
| オリジンリクエストポリシー | API系のみ `Authorization`, `Origin`, `Accept`, `If-None-Match` をフォワード |
| Lambda@Edge / Function | お知らせ初回制御やセキュアヘッダ付与で拡張余地 |
| Invalidation | 長期TTLは **ファイル名ハッシュ** で極小化 / 緊急時のみパス無効化 |
| Logging / 分析 | CloudFront Standard Logs + CloudWatch Metrics + Athena 解析 |

---
## 7. ディレクトリ / ファイル
| ファイル | 役割 |
| -------- | ---- |
| `initial_assumptions.md` | 想定規模・要件・学習目的・成功基準 |
| `infrastructure.md` | コンテンツ分類とキャッシュ戦略概要表 |
| `aws.drawio` / `aws.png` | アーキテクチャ図 |
| `README.md` | 本ドキュメント（統合サマリ） |

---
## 8. 運用フロー例
1. 動画アップロード: `build -> hash -> s3://video-bucket/video-<hash>.mp4`
2. メタ / サムネイル生成: Lambda かバッチで生成 → S3配置（同名上書き許容）
3. デプロイ後テスト: curl / DevTools でヘッダ確認
4. コメント増加時: ETag 変化→ クライアント差分取得
5. レコメンド改善: バックグラウンド再計算後 キャッシュ再構築

---
## 9. 検証手順（実践例）
```bash
# 1. サムネイル初回取得（キャッシュステータス確認）
curl -I https://<cloudfront-domain>/thumbnails/sample.jpg
# → Cache-Control, Age, X-Cache, X-Cache-Hits を確認

# 2. 直後再取得（Age増加、キャッシュヒット確認）  
curl -I https://<cloudfront-domain>/thumbnails/sample.jpg
# → Age値増加、X-Cache: Hit from cloudfront を期待

# 3. コメントAPI の ETag 取得
RESPONSE=$(curl -sI https://<cloudfront-domain>/api/comments?video=sample123)
ETAG=$(echo "$RESPONSE" | grep -i etag | sed 's/.*: //' | tr -d '\r\n')
echo "ETag: $ETAG"

# 4. 条件付きリクエスト（304期待）
curl -I -H "If-None-Match: $ETAG" https://<cloudfront-domain>/api/comments?video=sample123
# → HTTP/1.1 304 Not Modified を期待

# 5. SWR動作確認（stale-while-revalidate）
# TTL期限切れ後にリクエスト → 古いコンテンツ即返却 + 背景更新
curl -I https://<cloudfront-domain>/thumbnails/sample.jpg
# → X-Cache: Hit from cloudfront, Age > max-age を確認

# 6. プライベートデータのキャッシュ回避確認
curl -I -H "Authorization: Bearer <token>" https://<cloudfront-domain>/api/favorites
# → X-Cache: Miss from cloudfront が継続することを確認
```

---
## 10. コスト・最適化視点
| 項目 | 低コスト方針 |
| ---- | ------------- |
| 動画配信 | 可能なら解像度多段 + Edgeキャッシュ最大活用 |
| API | Lambda 実行時間短縮（軽量ランタイム / メモリ調整） |
| ストレージ | 不要バージョンのライフサイクルルール |
| ログ | Athena 分析前提で S3 へ集約（保持期間90日→集約） |

---
## 11. よくある失敗パターンと対処法
| 事象 | 原因 | 対処法 |
| ---- | ---- | ---- |
| サムネイル更新が反映されない | TTL設定過長 / SWRの誤解 | TTL短縮、または content-hash ベースファイル名採用 |
| APIレスポンスが古いままキャッシュされる | CloudFront最小TTL > 0設定 | キャッシュポリシーで最小TTL=0に修正 |
| Invalidation コスト増大 | 頻繁な手動無効化実行 | immutable assets + content-hash 導入で無効化回避 |
| ETag による 304 が機能しない | ETag生成アルゴリズム非一貫 | レスポンス正規化（UTF-8、JSON key sort、圧縮前後統一） |
| プライベートデータが他ユーザーに漏洩 | `public` キャッシュ設定ミス | 認証系APIは必ず `private` または `no-store` 設定 |
| SWR で古いデータが長時間表示される | stale-while-revalidate 値設定過大 | SWR期間を適切な値（60-300秒程度）に調整 |

---
## 12. 拡張アイデア
- Lambda@Edge でデバイス判定し画質最適化 (UA / Client Hints)
- Signed URL / Origin Access Control で私有動画アクセス
- Real-Time Logs + Kinesis Firehose でヒートマップ分析
- Tiered Cache (Regional Edge Cache) 有効化
- CloudFront Functions で軽量リダイレクト / Header 注入

---
## 13. 成功判定チェックリスト
- [ ] **動画配信**: 長期TTL + immutable 設定でInvalidation不要、content-hash ファイル名
- [ ] **サムネイル**: SWR正常動作（2回目でAge増加確認、期限切れ後の背景更新動作）
- [ ] **コメントAPI**: `If-None-Match`送信時に適切な304応答、ETag変更時は200応答
- [ ] **レコメンドAPI**: 古い値の短期表示後、一定時間経過で新データに自動更新
- [ ] **個人データ**: CDNキャッシュ完全回避（`X-Cache: Miss from cloudfront`継続確認）
- [ ] **セキュリティ**: HTTPS強制、認証APIでの適切なCORS設定
- [ ] **パフォーマンス**: 動画1秒以内、サムネイル0.5秒以内、API 300ms以内
- [ ] **コスト**: 月額予算内での運用、不要Invalidation回避

---
## 14. 参考コマンド（任意）
```bash
# 動画オブジェクトヘッダ確認
aws s3api head-object --bucket <video-bucket> --key video-<hash>.mp4 \
  --query '{CacheControl:CacheControl, ETag:ETag}'

# CloudFront Invalidation (緊急時のみ)
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/thumbnails/abc.jpg"
```

---
## 15. ライセンス / 利用
学習・検証目的の想定。商用利用時はログ/個人情報/DR/コスト設計を強化してください。

---
## 16. 今後
Terraform / CDK で IaC 化し、GitHub Actions でヘッダ・動作自動検証（integration test）を追加予定。

---
### Appendix: 設計キーワード
`SWR`, `Immutable Assets`, `ETag`, `Conditional Request`, `Private Data`, `Versioned File Naming`, `Edge Functions`, `Tiered Cache`, `Cost Optimization`.
