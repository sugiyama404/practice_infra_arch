# Sagaパターン テストデータ構成

## 📊 概要

このドキュメントでは、Sagaパターン（Choreography/Orchestration）のテスト環境を構築するためのデータ構成を説明します。

### データ構成の全体像

```
マスタデータ (5顧客 + 5書籍 + 在庫)
├── 顧客: 田中太郎, 佐藤花子, 鈴木次郎, 高橋美咲, 伊藤健太
├── 書籍: マイクロサービスアーキテクチャ, 分散システム設計, etc.
└── 在庫: 現実的な在庫数（在庫切れパターン含む）

テストデータ
├── 正常ケース: 成功注文 (order-success-001)
├── 異常ケース1: 在庫不足 (order-fail-stock)
├── 異常ケース2: 決済失敗 (order-fail-payment)
├── イベントデータ: Choreographyパターンフロー
└── Sagaデータ: Orchestrationパターンフロー
```

## 🚀 テストデータ投入手順

### 1. マスタデータ投入
```bash
mysql -u root -p cloudmart_saga < master_data.sql
```

**投入されるマスタデータ:**
- **顧客 (5名)**: 基本情報（名前、メール、住所）
- **書籍 (5冊)**: IT技術書中心の商品データ
- **在庫**: 現実的な在庫数（在庫切れパターン含む）

### 2. テストデータ投入
```bash
mysql -u root -p cloudmart_saga < load_test_data.sql
```

**投入されるテストデータ:**

#### ✅ 正常ケース: 成功した注文
- **注文ID**: `order-success-001`
- **顧客**: 田中太郎
- **商品**: マイクロサービスアーキテクチャ (¥3,500)
- **状態**: 配送完了
- **決済**: クレジットカード (完了)
- **配送**: ヤマト運輸 (完了)

#### ❌ 異常ケース1: 在庫不足
- **注文ID**: `order-fail-stock`
- **顧客**: 鈴木次郎
- **商品**: 分散システム設計 (在庫切れ)
- **状態**: キャンセル
- **理由**: 在庫不足

#### ❌ 異常ケース2: 決済失敗
- **注文ID**: `order-fail-payment`
- **顧客**: 高橋美咲
- **商品**: データベース設計の極意 (¥4,200)
- **状態**: キャンセル
- **理由**: 残高不足

### 3. Choreographyパターン用イベントデータ
```sql
-- 正常フローイベント
ORDER_CREATED → STOCK_RESERVED → PAYMENT_COMPLETED → SHIPPING_DELIVERED

-- 異常フローイベント
ORDER_CREATED → STOCK_UNAVAILABLE → ORDER_CANCELLED
```

### 4. Orchestrationパターン用Sagaデータ
```sql
-- Sagaインスタンス: saga-success-001
ステップ1: CreateOrder (完了)
ステップ2: ReserveStock (完了)
ステップ3: ProcessPayment (完了)
ステップ4: CreateShipment (完了)
```

## 🔍 データ検証

投入後のデータ検証:
```bash
mysql -u root -p cloudmart_saga < validate_data.sql
```

**検証内容:**
- テーブル別レコード数確認
- 注文状態別集計
- 在庫状況確認（在庫切れ/要補充/充分）
- イベント種別集計
- データ整合性チェック

## 🧹 データクリーンアップ

テスト後のデータクリーンアップ:
```bash
mysql -u root -p cloudmart_saga < cleanup.sql
```

**クリーンアップ内容:**
- テストデータの削除（注文、決済、配送、イベント、Saga）
- 在庫数の初期化（マスタデータ保持）

## 📋 テストシナリオ

### Choreographyパターン
1. **正常フロー**: 注文作成 → 在庫確保 → 決済処理 → 配送手配
2. **異常フロー**: 在庫不足時の自動キャンセル

### Orchestrationパターン
1. **正常フロー**: Saga Orchestratorによる一元管理
2. **異常フロー**: 決済失敗時の補償トランザクション

## 🎯 期待されるテスト結果

- **正常ケース**: 全ステップ成功、データ整合性維持
- **異常ケース**: 適切なロールバック、補償処理実行
- **パフォーマンス**: 各パターンの応答時間比較
- **信頼性**: エラー発生時のデータ整合性維持

## 📁 ファイル構成

```
saga_pattern/
├── master_data.sql      # マスタデータ投入
├── load_test_data.sql   # テストデータ投入
├── validate_data.sql    # データ検証
├── cleanup.sql          # データクリーンアップ
└── README.md           # このドキュメント
```
