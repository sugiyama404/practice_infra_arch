# Session Store Pattern

## 概要
Redisを高速なセッションストアとして利用する実装。
セッションデータの保存、取得、更新、削除、および有効期限管理を学習。

## アーキテクチャ
- Redis: セッションデータをJSON形式で保存
- キー設計: `session:{session_id}`

## 学習ポイント
- Cookieベースのセッション管理との連携
- セッションの有効期限（TTL）と自動延長
- セキュリティ（セッションIDの推測困難性）
- スケーラビリティと高可用性の確保

---

### システム構成図

```mermaid
graph TD
    subgraph "User"
        Browser[User's Browser]
    end

    subgraph "Application Layer"
        LoadBalancer[Load Balancer]
        WebApp1[Web App Server 1]
        WebApp2[Web App Server 2]
        WebAppN[Web App Server N]
        LoadBalancer --> WebApp1
        LoadBalancer --> WebApp2
        LoadBalancer --> WebAppN
    end

    subgraph "Session Store"
        Redis[Redis Session Store]
    end

    Browser -- "1. Request with Session ID (Cookie)" --> LoadBalancer
    WebApp1 -- "2. Read/Write Session Data" --> Redis
    WebApp2 -- "2. Read/Write Session Data" --> Redis
    WebAppN -- "2. Read/Write Session Data" --> Redis
    Redis -- "3. Return Session Data" --> WebApp1
    WebApp1 -- "4. Response" --> Browser
```

**解説:**
このシステムは、ステートレスなWebアプリケーションでセッション情報を管理するために、外部のセッションストアを利用する構成です。
1.  ユーザーのブラウザは、リクエスト時にセッションIDをクッキーに含めて送信します。
2.  ロードバランサーはリクエストをいずれかのWebアプリケーションサーバーに転送します。
3.  Webアプリケーションサーバーは、受け取ったセッションIDをキーとして、Redisセッションストアからユーザーのセッションデータを読み書きします。
4.  セッションデータを処理に利用し、レスポンスをブラウザに返します。

このアーキテクチャにより、特定のサーバーにセッションが依存しない（セッションアフィニティが不要）ため、Webアプリケーション層を自由にスケールアウトできます。

### AWS構成図

```mermaid
graph TD
    subgraph "User"
        Browser[User's Browser]
    end

    subgraph "AWS Cloud"
        subgraph "Network & Scaling"
            ALB[fa:fa-sitemap Application Load Balancer]
            ASG[fa:fa-clone Auto Scaling Group]
        end

        subgraph "Application Layer"
            EC2_1[fa:fa-desktop EC2 Instance 1]
            EC2_2[fa:fa-desktop EC2 Instance 2]
            EC2_N[fa:fa-desktop EC2 Instance N]
            ASG -- manages --> EC2_1
            ASG -- manages --> EC2_2
            ASG -- manages --> EC2_N
        end

        subgraph "Session Store"
            ElastiCache[fa:fa-database Amazon ElastiCache for Redis]
        end

        subgraph "VPC"
            ALB --> EC2_1
            ALB --> EC2_2
            ALB --> EC2_N
            EC2_1 --> ElastiCache
            EC2_2 --> ElastiCache
            EC2_N --> ElastiCache
        end
    end

    Browser -- "Request" --> ALB
```

**解説:**
このAWS構成は、スケーラブルで高可用なWebアプリケーションのための一般的なアーキテクチャです。

*   **Web App Servers → Amazon EC2 in Auto Scaling Group:**
    Webアプリケーションサーバーは、Amazon EC2インスタンス上で実行されます。これらのインスタンスはAuto Scaling Groupによって管理され、トラフィックの増減に応じてインスタンス数が自動的に調整されます。
*   **Load Balancer → Application Load Balancer (ALB):**
    ALBは、受信トラフィックを複数のEC2インスタンスに分散します。ALBはレイヤー7ロードバランサーであり、HTTP/HTTPSのヘッダーやパスに基づいてルーティングを行うことができます。
*   **Redis Session Store → Amazon ElastiCache for Redis:**
    セッションデータは、フルマネージドなインメモリデータストアであるAmazon ElastiCache for Redisに保存されます。これにより、アプリケーションサーバーはステートレスになり、どのインスタンスでもユーザーリクエストを処理できるようになります。ElastiCacheは高可用性と低レイテンシを提供し、セッション管理に最適です。

この構成により、アプリケーション層を独立してスケールさせることができ、単一障害点のない、堅牢でパフォーマンスの高いシステムを構築できます。
