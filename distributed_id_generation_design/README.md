# 分散ID生成システム設計 学習プロジェクト

> Snowflake アルゴリズムとチケットサーバー方式を実装・比較し、分散システムにおける一意ID生成の仕組みを学習するためのプロジェクト

---

## 📋 概要

このプロジェクトは、大規模分散システムでよく使われる2つのID生成手法を実装し、それぞれの特性を理解するための学習用リポジトリです。

### 実装されているID生成手法

1. **Snowflake アルゴリズム** - Twitter社が開発した時刻ベースの分散ID生成
2. **チケットサーバー方式** - 中央集権的なカウンター管理による連番ID生成

---

## 🏗️ システム構成

```
┌─────────────┐    ┌───────────────────┐    ┌─────────────────┐
│             │    │                   │    │                 │
│   Client    │◄──►│  Snowflake Server │    │  Ticket Server  │
│             │    │   (Port: 9001)    │    │   (Port: 9002)  │
│             │    │                   │    │                 │
└─────────────┘    └───────────────────┘    └─────────────────┘
```

### コンポーネント

| サービス | ポート | 責務 | 実装言語 |
|---------|--------|------|----------|
| **Client** | - | 両サーバーからIDを取得して結果を比較表示 | Python |
| **Snowflake** | 9001→8080 | Twitter Snowflake アルゴリズムによるID生成 | Python + Flask |
| **Ticket Server** | 9002→8080 | 中央管理カウンターによる連番ID生成 | Python + Flask |

---

## 🔧 Snowflake アルゴリズム詳細

### ビット構成
```
┌─────────────────────────────────────────────────────────────┐
│ 1bit │      41bits      │  10bits  │     12bits              │
│unused│    timestamp     │machine_id│     sequence            │
└─────────────────────────────────────────────────────────────┘
```

### パラメータ
- **Epoch**: 2021-01-01 00:00:00 UTC (`1609459200000`)
- **Machine ID**: `1` (単一ノード構成)
- **Sequence**: 同一ミリ秒内での連番 (0-4095)

### 特徴
✅ **分散対応**: 複数マシンで同時実行可能  
✅ **時系列ソート**: 生成順序が時刻順と一致  
✅ **高性能**: 1ミリ秒あたり最大4096個のID生成  
❌ **時刻依存**: システム時刻の逆行で重複リスク  

---

## 🎫 チケットサーバー方式詳細

### 仕組み
- 中央の単一サーバーでカウンターを管理
- リクエストごとにカウンターをインクリメント
- スレッドセーフなロック機構で同期制御

### 特徴
✅ **完全一意性**: 重複の可能性がゼロ  
✅ **連番保証**: 欠番のない連続したID  
✅ **実装簡単**: シンプルなロジック  
❌ **単一障害点**: サーバーダウンでサービス停止  
❌ **スケーラビリティ**: 1台のサーバーがボトルネック  

---

## 🚀 実行方法

### 前提条件
- Docker
- Docker Compose

### 起動手順

1. **全サービス起動**
   ```bash
   cd distributed_id_generation_design
   docker compose up --build
   ```

2. **動作確認**
   - クライアントが自動的に両サーバーからIDを取得
   - コンソールに生成されたIDが表示される

### 個別サービステスト

```bash
# Snowflake サーバー単体テスト
curl http://localhost:9001/generate

# Ticket サーバー単体テスト  
curl http://localhost:9002/generate
```

### 期待される出力例
```
Starting ID generation client...
Generating IDs from Snowflake and Ticket Server:
Snowflake ID: 123456789012345678, Ticket ID: 100001
Snowflake ID: 123456789012345679, Ticket ID: 100002
Snowflake ID: 123456789012345680, Ticket ID: 100003
...
ID generation completed.
```

---

## 📊 パフォーマンス比較

### 負荷テスト例

```bash
# Snowflakeサーバーへの連続リクエスト
for i in {1..100}; do
  curl -s http://localhost:9001/generate | jq .id
done

# Ticketサーバーへの連続リクエスト  
for i in {1..100}; do
  curl -s http://localhost:9002/generate | jq .id
done
```

### 想定される特性

| 項目 | Snowflake | Ticket Server |
|------|-----------|---------------|
| **スループット** | 高 (4096 ID/ms理論値) | 中 (HTTP + ロック制約) |
| **一意性保証** | 高 (時刻逆行時のみリスク) | 完全 |
| **順序性** | 時刻順 | 完全な連番 |
| **可用性** | 高 (分散可能) | 低 (SPOF) |
| **実装複雑度** | 中 | 低 |

---

## 🎯 学習ポイント

### 1. 分散システム設計の理解
- **CAP定理**: 一貫性(C)・可用性(A)・分断耐性(P)のトレードオフ
- **SPOF**: Single Point of Failure の回避戦略
- **水平スケーリング**: 負荷分散の考え方

### 2. ID生成戦略の選択基準
```
高可用性 → Snowflake
完全連番 → Ticket Server  
超高性能 → Snowflake + 複数ノード
実装簡単 → Ticket Server
```

### 3. 並行制御とスレッドセーフティ
- Pythonの`threading.Lock()`による排他制御
- 同一ミリ秒内でのsequence番号管理
- レースコンディション対策

---

## 🔍 拡張アイデア

### 実装拡張
- [ ] **Multi-Node Snowflake**: 複数のmachine_idでの分散実行
- [ ] **Redis Ticket Server**: 永続化 + 高可用性対応
- [ ] **ベンチマークツール**: 性能測定の自動化
- [ ] **監視ダッシュボード**: Grafana + Prometheus

### アルゴリズム追加  
- [ ] **UUID v4**: 完全ランダムベース
- [ ] **ULID**: Snowflake + Base32エンコード
- [ ] **Sonyflake**: Snowflakeの改良版

### インフラ拡張
- [ ] **Kubernetes デプロイ**: Pod間通信での分散実行
- [ ] **Database連携**: 生成IDの永続化と重複検証
- [ ] **Load Balancer**: 複数Snowflakeノードの負荷分散

---

## 📚 技術参考資料

### Snowflake Algorithm
- [Twitter Engineering Blog - Snowflake](https://blog.twitter.com/engineering/en_us/a/2010/announcing-snowflake.html)
- [RFC 4122 - UUID](https://tools.ietf.org/html/rfc4122)

### 分散システム理論
- [CAP定理の詳細解説](https://en.wikipedia.org/wiki/CAP_theorem)
- [分散ID生成の実用パターン](https://www.slideshare.net/slideshow/unique-id-generation-in-distributed-systems/250924135)

### 実装リファレンス
- [Instagram Engineering - Sharding & IDs](https://instagram-engineering.com/sharding-ids-at-instagram-1cf5a71e5a5c)
- [Flickr - Ticket Servers](http://code.flickr.net/2010/02/08/ticket-servers-distributed-unique-primary-keys-on-the-cheap/)

---

## 🐛 トラブルシューティング

### よくある問題

**Q: Snowflakeで同じIDが重複生成される**  
A: システム時刻が逆行した可能性。NTPサーバーとの時刻同期を確認。

**Q: Ticket ServerでIDが飛び番になる**  
A: サーバー再起動でカウンターがリセット。永続化（Redis/DB）の導入を検討。

**Q: コンテナ間で通信エラー**  
A: Docker Composeのネットワーク設定確認。`docker-compose logs` でエラー詳細を確認。

**Q: 高負荷時にTicket Serverが遅くなる**  
A: Flask組み込みサーバーの限界。Gunicorn + Redis等の本格的な構成に変更。

---

## 📄 ライセンス

MIT License - 学習・実験目的での自由な利用を想定

---

## 🔄 今後の計画

1. **Phase 1**: 基本実装完成 ✅
2. **Phase 2**: 監視・メトリクス追加
3. **Phase 3**: Kubernetes対応
4. **Phase 4**: 本格的な負荷テスト環境構築

---

### 🏷️ キーワード
`分散システム`, `ID生成`, `Snowflake Algorithm`, `Ticket Server`, `並行制御`, `Docker`, `Flask`, `微服务架构`, `High Availability`
