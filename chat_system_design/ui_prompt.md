# Next.js SSR UI開発のためのプロンプト

## システム概要
あなたはNext.jsのSSR（Server-Side Rendering）モードを使用して、リアルタイムチャットシステムのUIを作成します。このシステムはSlack風のユーザー体験を重視し、最低限必要な機能をコンパクトにまとめつつ、リアルタイム性を体感できるUIを目指します。バックエンドAPIはDocker Composeで構成されており、以下のエンドポイントを提供します。APIは`http://localhost:8080`（開発環境）でアクセス可能で、`/api`プレフィックスを使用します。

## UI要件
### レイアウト構成
```
───────────────────────────────
 サイドバー          | チャットエリア
───────────────────────────────
- プロフィール        | 上部: チャネル名 or 相手ユーザー名
- チャンネル一覧      | 中央: メッセージ一覧（吹き出しスタイル）
- DM一覧              | 下部: 入力欄 + 送信ボタン
───────────────────────────────
```

### 主要UI要素
- **サイドバー**
  - 「チャンネル」「DM」タブ（タブ切り替えでルーム一覧を表示）
  - オンラインユーザーに緑のインジケータ（プレゼンスAPIで取得、リアルタイム更新）

- **チャットエリア**
  - 吹き出しスタイル（左：相手、右：自分。MessageBubbleコンポーネント使用）
  - メッセージごとにタイムスタンプ（ISO 8601をフォーマット）
  - 「既読」「未読」「送信中」ステータス（メッセージ送信後に更新）
  - 添付ファイル（最初はテキストのみ、拡張で画像対応）

- **入力欄**
  - メッセージ入力ボックス + 送信ボタン（Enter送信、Shift+Enter改行）
  - 送信直後に「時計アイコン → チェック → ダブルチェック」と状態変化（WebSocketで確認）
  - タイピングインジケーター（入力中にWebSocketで送信）

### リアルタイム性を見せる工夫
- 自分が打ったメッセージが即座に表示 → サーバ確認後にステータス更新（WebSocket 'message' イベントで同期）
- 相手が入力中なら「〇〇 is typing...」が出る（WebSocket 'typing' イベントで実現）
- デバイスAで送ったメッセージが即座にデバイスBにも反映（cur_max_message_id をUIで表示、WebSocketで更新）
- プレゼンス更新（WebSocket 'presence' イベントでオンラインユーザー一覧をリアルタイム更新）

### 拡張アイディア
- **絵文字リアクション**（最低限 👍 ❤️）
- **ユーザーアイコン（丸アイコン）** をメッセージ横に表示
- **既読数カウンタ**（「既読3」など） → 少人数チャットで映える
- **スレッド表示**（最小構成では省略可、後で追加）

## 技術的実装要件
- **フロントエンド**: Next.js (Pages Router, SSRモード)
- **スタイリング**: Tailwind CSS
- **UIライブラリ**: shadcn/ui（React向け）でカード/リスト/モーダルを整理
- **アイコン**: Lucide icons で「送信中/既読」アイコンを実装
- **リアルタイム通信**: WebSocket接続（`ws://localhost:8080/ws/{user_id}/{device_id}/{room_id}`）。イベント: 'message' (新規メッセージ), 'presence' (オンラインユーザー更新), 'typing' (タイピングインジケーター)
- **状態管理**: React Context または Zustand。メッセージリスト、プレゼンス、WebSocket接続状態を管理。
- **認証**: 簡易的に user_id と device_id をクエリパラメータから取得（例: `/chat/room1?user_id=alice&device_id=desktop`）。本番ではJWTなど。
- **API接続確認**: 実装前にヘルスチェックエンドポイント `/health` をテスト。WebSocket接続は自動再接続を実装し、接続失敗時はエラーメッセージを表示。
- **エラーハンドリング**: APIエラー時はトースト通知。WebSocket切断時は再接続試行（最大3回）。

## プロジェクト構造
```
src/
├── pages/                     # Next.js Pages Router (SSR)
│   ├── index.tsx              # トップページ（チャンネル一覧）
│   ├── _app.tsx               # 全ページ共通処理 (グローバル状態, CSSなど)
│   ├── _document.tsx          # HTMLタグ直下の設定
│   ├── layout.tsx             # 全ページ共通レイアウト
│   │
│   └── chat/                  # chat機能モジュール
│       ├── [roomId].tsx       # SSRページ（チャットルーム）
│       ├── chat_usecase.ts    # ビジネスロジック
│       ├── chat_api.ts        # APIクライアント
│       ├── chat_utils.ts      # chat専用ユーティリティ
│       ├── chat_type.ts       # ドメイン型定義
│       └── components/        # chat専用UI
│           └── MessageBubble.tsx
│
├── components/                # グローバルUIコンポーネント
│   ├── ui/                    # shadcn/ui コンポーネント
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   └── Card.tsx
│   ├── Sidebar.tsx            # サイドバーコンポーネント
│   ├── ChatArea.tsx           # チャットエリアコンポーネント
│   ├── MessageList.tsx        # メッセージリスト
│   ├── MessageInput.tsx       # メッセージ入力
│   └── PresenceIndicator.tsx  # プレゼンスインジケーター
│
├── lib/                       # 共通処理（infra寄り）
│   ├── api.ts                 # APIクライアント
│   ├── websocket.ts           # WebSocketクライアント
│   └── client.ts              # axios/fetch wrapper
│
├── types/                     # 共通の型
│   ├── api.ts                 # APIレスポンス型
│   ├── message.ts             # メッセージ型
│   └── user.ts                # ユーザー型
│
├── hooks/                     # カスタムフック
│   ├── useMessages.ts         # メッセージ管理
│   ├── usePresence.ts         # プレゼンス管理
│   └── useWebSocket.ts        # WebSocket管理
│
└── styles/
    └── globals.css            # Tailwind CSS
```

## APIエンドポイント一覧

### 1. メッセージ送信
- **Endpoint**: `POST /api/messages/send`
- **Description**: 新しいメッセージを送信し、メッセージIDを生成。RabbitMQ経由で非同期処理。
- **Request Body**:
  ```typescript
  {
    user_id: string,      // 送信者ユーザーID (必須, 1-255文字)
    device_id: string,    // 送信者デバイスID (必須, 1-255文字)
    room_id: string,      // ルームID (必須, 1-255文字)
    content: string       // メッセージ内容 (必須, 1-4000文字)
  }
  ```
- **Response**:
  ```typescript
  {
    message_id: number,   // 生成されたメッセージID
    status: string,       // 送信ステータス ("sent")
    timestamp: string     // 送信タイムスタンプ (ISO 8601)
  }
  ```

### 2. メッセージ同期
- **Endpoint**: `GET /api/messages/sync`
- **Description**: 指定ルームの新しいメッセージを取得し、デバイスの同期状態を更新。
- **Query Parameters**:
  - `user_id` (string, 必須): リクエストユーザーID
  - `device_id` (string, 必須): リクエストデバイスID
  - `room_id` (string, 必須): 対象ルームID
  - `last_message_id` (number, オプション, デフォルト: 0): 最後に受信したメッセージID
  - `limit` (number, オプション, デフォルト: 50, 範囲: 1-100): 最大取得メッセージ数
- **Response**:
  ```typescript
  {
    messages: Array<{
      message_id: number,    // メッセージID
      user_id: string,       // 送信者ユーザーID
      room_id: string,       // ルームID
      content: string,       // メッセージ内容
      timestamp: string,     // メッセージタイムスタンプ (ISO 8601)
      message_type: string   // メッセージタイプ (デフォルト: "text")
    }>,
    cur_max_message_id: number,  // デバイスの現在の最大メッセージID
    has_more: boolean           // さらにメッセージがあるかどうか
  }
  ```

### 3. プレゼンス取得
- **Endpoint**: `GET /api/users/{user_id}/presence`
- **Description**: 指定ユーザーのオンライン状態を取得。
- **Path Parameters**:
  - `user_id` (string): 対象ユーザーID
- **Response**:
  ```typescript
  {
    user_id: string,           // ユーザーID
    status: string,            // ステータス ("online" | "offline")
    last_seen: string,         // 最後に見た時刻 (ISO 8601)
    ws_server: string | null  // 接続中のWebSocketサーバー
  }
  ```

### 4. システム統計
- **Endpoint**: `GET /api/stats`
- **Description**: システムの統計情報を取得。
- **Response**:
  ```typescript
  {
    service: string,           // サービス名 ("chat-api")
    total_messages: number,    // 総メッセージ数
    active_rooms: number,      // アクティブなルーム数
    current_message_id: number, // 現在のメッセージIDカウンター
    timestamp: string          // レスポンスタイムスタンプ (ISO 8601)
  }
  ```

### 5. ヘルスチェック
- **Endpoint**: `GET /health`
- **Description**: APIサービスのヘルスチェック。
- **Response**:
  ```typescript
  {
    status: string,     // ステータス ("healthy")
    service: string,    // サービス名 ("chat-api")
    version: string,    // バージョン ("1.0.0")
    timestamp: string   // タイムスタンプ (ISO 8601)
  }
  ```

## Next.jsでの実装タスク (TODO形式)
- [ ] **プロジェクトセットアップ**: `chat_system_design/ui` ディレクトリを作成。Dockerfileを作成（Node.jsベース、ポート3000公開）。コンテナの中でNext.jsプロジェクトを作成し、Tailwind CSS、shadcn/uiをインストール。package.jsonとtsconfig.jsonを設定。
- [ ] **Docker Compose設定**: `chat_system_design/compose.yaml` に ui service を追加。Next.jsアプリをコンテナ化し、ポート3000で公開。nginxに依存。
- [ ] **APIクライアントの作成**: 上記のエンドポイントを呼び出すためのTypeScript関数を作成（`lib/api.ts`）。axiosまたはfetchを使用。
- [ ] **WebSocketクライアントの作成**: WebSocket接続を管理するクラスまたはフックを作成（`lib/websocket.ts`）。メッセージ受信時のイベントハンドリングを実装。
- [ ] **SSRページの実装**: `getServerSideProps`を使用してサーバーサイドでデータをフェッチし、初期レンダリングを行う（`pages/chat/[roomId].tsx`）。user_id, device_id, room_idをクエリパラメータから取得。
- [ ] **リアルタイム更新**: クライアントサイドでWebSocket接続を確立し、メッセージ同期をリアルタイムで行う。useEffectで接続管理。
- [ ] **UIコンポーネントの実装**: Sidebar, ChatArea, MessageList, MessageInputなどのコンポーネントを作成。Tailwindでスタイリング。
- [ ] **状態管理**: メッセージ、プレゼンス、WebSocket状態をContextまたはZustandで管理。
- [ ] **エラーハンドリング**: APIエラーを適切に処理し、ユーザー体験を向上させる。トースト通知などでエラーを表示。
- [ ] **コード品質チェック**: ESLintでlinting（`yarn lint`）、Prettierでフォーマット（`yarn format`）、TypeScriptで型チェック（`yarn tsc`）を実行。コードのリファクタリング時にこれらのコマンドを使用。
- [ ] **テスト**: コンポーネントとAPIクライアントのユニットテストを作成（Jest + React Testing Library）。
- [ ] **デプロイ**: VercelやNetlifyでデプロイ。本番環境でのCORSと認証を考慮。
- [ ] **最終品質チェック**: コードの実装が終わったら、`yarn format`、`yarn lint`、`yarn tsc` を実行して品質を確認。

## 注意事項
- Docker Composeでサービスを起動し、nginxがポート8080でリバースプロキシしていることを確認。UIはポート3000でアクセス。
- CORSは開発環境で許可されているが、本番では適切に設定。
- レート制限は無効だが、将来有効化される可能性あり。
- ユーザー認証は簡易的に実装。本番ではJWTやOAuthを検討。
- WebSocket接続は自動再接続を実装（接続失敗時は3秒待機して再試行、最大5回）。
- メッセージの既読ステータスはAPIで取得可能だが、UIでは簡易的に実装。
- API接続確認: 実装前に `GET /health` でバックエンドが稼働しているかテスト。WebSocket接続はブラウザコンソールで確認。

AIが迷ったら、このファイルを参照してください。このプロンプトを基に、Next.jsアプリケーションを開発してください。追加の詳細が必要でしたらお知らせください。

---

## 💬 Slack風チャット UI アイディア

### 1. **レイアウト構成**

```
───────────────────────────────
 サイドバー          | チャットエリア
───────────────────────────────
- プロフィール        | 上部: チャネル名 or 相手ユーザー名
- チャンネル一覧      | 中央: メッセージ一覧（吹き出しスタイル）
- DM一覧              | 下部: 入力欄 + 送信ボタン
───────────────────────────────
```

### 2. **主要UI要素**

* **サイドバー**

  * 「チャンネル」「DM」タブ
  * オンラインユーザーに緑のインジケータ（Redis presence と連動）

* **チャットエリア**

  * 吹き出しスタイル（左：相手、右：自分）
  * メッセージごとにタイムスタンプ
  * 「既読」「未読」「送信中」ステータス（DB/Redis と連動）
  * 添付ファイル（最初はテキストだけでもOK）

* **入力欄**

  * メッセージ入力ボックス + 送信ボタン
  * 「Enter で送信 / Shift+Enter で改行」対応
  * 送信直後に「時計アイコン → チェック → ダブルチェック」と状態が変わる

---

### 3. **リアルタイム性を見せる工夫**

* 自分が打ったメッセージが **即座に表示 → サーバ確認後にステータス更新**
* 相手が入力中なら「〇〇 is typing...」が出る（WS通知で実現）
* デバイスAで送ったメッセージが即座にデバイスBにも反映（cur\_max\_message\_id をUIで表示しても良い）

---

### 4. **拡張アイディア**

* **絵文字リアクション**（最低限 👍 ❤️）
* **ユーザーアイコン（丸アイコン）** をメッセージ横に表示
* **既読数カウンタ**（「既読3」など） → 少人数チャットで映える
* **スレッド表示**（最小構成では省略可、後で追加）

---

### 5. **技術的実装ポイント**

* **フロントエンド**

  * React or Vue (Next.jsでも可)
  * Tailwind でシンプルにスタイリング
  * WebSocket 接続で双方向通信
* **UIライブラリ**

  * shadcn/ui（React向け）でカード/リスト/モーダルを整理すると Slack感が出る
  * Lucide icons で「送信中/既読」アイコンを実装

---

## ✨ デモとして効果的な構成

* 最初は「**シンプルSlack風 UI**」に絞る
* その後「**管理者向けダッシュボード**」を別タブに追加すると就活的に映える

---

👉 質問：
UIは **Webアプリ（React/Tailwind）** として作りたいですか？
それとも **デスクトップアプリ（Go+Fyne）** みたいにネイティブ感あるものを狙いますか？






src/
├── pages/                     # Next.js Pages Router (SSR)
│   ├── index.tsx
│   ├── _app.tsx               # 全ページ共通処理 (グローバル状態, CSSなど)
│   ├── _document.tsx          # HTMLタグ直下の設定
│   ├── layout.tsx             # 全ページ共通レイアウト
│   │
│   └── users/                 # users機能モジュール
│       ├── [id].tsx           # SSRページ
│       ├── users_usecase.ts   # ビジネスロジック
│       ├── users_api.ts       # APIクライアント
│       ├── users_utils.ts     # users専用ユーティリティ
│       ├── users_type.ts      # ドメイン型定義
│       └── components/        # users専用UI
│           └── UserCard.tsx
│
├── components/                # グローバルUIコンポーネント
│   └── ui/
│       └── Button.tsx
│
├── lib/                       # 共通処理（infra寄り）
│   └── client.ts              # axios/fetch wrapper
│
├── types/                     # 共通の型
│   ├── react.d.ts             # React用型 (FC, PropsWithChildrenなど)
│   ├── api.ts                 # 汎用APIレスポンス型
│   └── global.ts              # 共通ユーティリティ型
│
└── styles/
    └── globals.css





Next.jsのSSRモードのファイルを作って、pageコンポーネントをつ

以下は、Next.jsのSSRモードでUIを作成するためのAPIエンドポイント情報。Next.jsアプリケーションの開発を進めてください。

## プロンプト: Next.js SSR UI開発のためのAPIエンドポイント情報

### システム概要
あなたはNext.jsのSSR（Server-Side Rendering）モードを使用して、リアルタイムチャットシステムのUIを作成します。バックエンドAPIはDocker Composeで構成されており、以下のエンドポイントを提供します。APIは`http://localhost:8080`（開発環境）でアクセス可能で、`/api`プレフィックスを使用します。

### APIエンドポイント一覧

#### 1. メッセージ送信
- **Endpoint**: `POST /api/messages/send`
- **Description**: 新しいメッセージを送信し、メッセージIDを生成。RabbitMQ経由で非同期処理。
- **Request Body**:
  ```typescript
  {
    user_id: string,      // 送信者ユーザーID (必須, 1-255文字)
    device_id: string,    // 送信者デバイスID (必須, 1-255文字)
    room_id: string,      // ルームID (必須, 1-255文字)
    content: string       // メッセージ内容 (必須, 1-4000文字)
  }
  ```
- **Response**:
  ```typescript
  {
    message_id: number,   // 生成されたメッセージID
    status: string,       // 送信ステータス ("sent")
    timestamp: string     // 送信タイムスタンプ (ISO 8601)
  }
  ```

#### 2. メッセージ同期
- **Endpoint**: `GET /api/messages/sync`
- **Description**: 指定ルームの新しいメッセージを取得し、デバイスの同期状態を更新。
- **Query Parameters**:
  - `user_id` (string, 必須): リクエストユーザーID
  - `device_id` (string, 必須): リクエストデバイスID
  - `room_id` (string, 必須): 対象ルームID
  - `last_message_id` (number, オプション, デフォルト: 0): 最後に受信したメッセージID
  - `limit` (number, オプション, デフォルト: 50, 範囲: 1-100): 最大取得メッセージ数
- **Response**:
  ```typescript
  {
    messages: Array<{
      message_id: number,    // メッセージID
      user_id: string,       // 送信者ユーザーID
      room_id: string,       // ルームID
      content: string,       // メッセージ内容
      timestamp: string,     // メッセージタイムスタンプ (ISO 8601)
      message_type: string   // メッセージタイプ (デフォルト: "text")
    }>,
    cur_max_message_id: number,  // デバイスの現在の最大メッセージID
    has_more: boolean           // さらにメッセージがあるかどうか
  }
  ```

#### 3. プレゼンス取得
- **Endpoint**: `GET /api/users/{user_id}/presence`
- **Description**: 指定ユーザーのオンライン状態を取得。
- **Path Parameters**:
  - `user_id` (string): 対象ユーザーID
- **Response**:
  ```typescript
  {
    user_id: string,           // ユーザーID
    status: string,            // ステータス ("online" | "offline")
    last_seen: string,         // 最後に見た時刻 (ISO 8601)
    ws_server: string | null  // 接続中のWebSocketサーバー
  }
  ```

#### 4. システム統計
- **Endpoint**: `GET /api/stats`
- **Description**: システムの統計情報を取得。
- **Response**:
  ```typescript
  {
    service: string,           // サービス名 ("chat-api")
    total_messages: number,    // 総メッセージ数
    active_rooms: number,      // アクティブなルーム数
    current_message_id: number, // 現在のメッセージIDカウンター
    timestamp: string          // レスポンスタイムスタンプ (ISO 8601)
  }
  ```

#### 5. ヘルスチェック
- **Endpoint**: `GET /health`
- **Description**: APIサービスのヘルスチェック。
- **Response**:
  ```typescript
  {
    status: string,     // ステータス ("healthy")
    service: string,    // サービス名 ("chat-api")
    version: string,    // バージョン ("1.0.0")
    timestamp: string   // タイムスタンプ (ISO 8601)
  }
  ```

### Next.jsでの実装タスク
1. **APIクライアントの作成**: 上記のエンドポイントを呼び出すためのTypeScript関数を作成（例: `lib/api.ts`）。
2. **SSRページの実装**: `getServerSideProps`を使用してサーバーサイドでデータをフェッチし、初期レンダリングを行う（例: `pages/chat/[roomId].tsx`）。
3. **リアルタイム更新**: WebSocket接続（`ws://localhost:8080/ws/{user_id}/{device_id}/{room_id}`）をクライアントサイドで実装し、メッセージ同期をリアルタイムで行う。
4. **エラーハンドリング**: APIエラーを適切に処理し、ユーザー体験を向上させる。
5. **UIコンポーネント**: チャットルーム、メッセージリスト、プレゼンスインジケーターなどのコンポーネントを作成。

### 注意事項
- Docker Composeでサービスを起動し、nginxがポート8080でリバースプロキシしていることを確認。
- CORSは開発環境で許可されているが、本番では適切に設定。
- レート制限は無効だが、将来有効化される可能性あり。

このプロンプトを基に、Next.jsアプリケーションを開発してください。追加の詳細が必要でしたらお知らせください。
