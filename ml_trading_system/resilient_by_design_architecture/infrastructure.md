# テーマ
機械学習システムトレーディングのためのレジリエント・バイ・デザイン構成

## 共通アーキテクチャ要素（各クラウド共通思想）

| 機能       | 要素                                   | 解説                                             |
| -------- | ------------------------------------ | ---------------------------------------------- |
| 推論API    | 高可用性なGPU推論エンドポイント                    | 各クラウドのマネージドKubernetesまたはサーバレスGPU               |
| 学習ジョブ    | スポット＋オンデマンド混在の分散トレーニング               | スケジューラ＋耐障害ワーカー群                                |
| モニタリング   | Prometheus + Grafana + アラート連携（Slack） | コンテナレベル／ジョブレベルの監視                              |
| フェイルオーバー | リージョン間DNS + ヘルスチェック                  | Route 53 / Azure Traffic Manager / Cloud DNS 等 |
| IaC管理    | Terraform + GitHub Actions           | コードベースの環境定義と変更管理                               |
| ログ管理     | 永続化＋監査対応可能なストレージ                     | ログの署名・バージョン管理（規制対応）                            |


## AWSのシステム構成
| レイヤー          | 使用サービス                                            |
| ------------- | ------------------------------------------------- |
| **操作画面**      | ECS Fargate + ALB + Auto Scaling + CloudFront     |
| **推論エンドポイント** | ECS Fargate + ALB + Auto Scaling          |
| **学習基盤**      | SageMaker Training + Pipelines             |
| **スケジューラー**   | EventBridge + Lambda                              |
| **フェイルオーバー**  | Route 53 + ALB Health Check |
| **モニタリング**    | CloudWatch                         |
| **ストレージ**     | S3（バージョニング + KMS暗号化 + Intelligent-Tiering）        |
| **自己回復設計**    | ECS Auto Recovery                    |
| **ログ・監査**     | CloudTrail + CloudWatch Logs + S3                 |



## Azureのシステム構成
| レイヤー                    | 使用サービス                                                          |
| ----------------------- | --------------------------------------------------------------- |
| **操作画面（フロントエンド）**       | Amazon ECS Fargate（ALB配下、マルチAZ構成、Auto Scaling対応）                |
| **API / バックエンド**        | Amazon ECS Fargate + ALB（ヘルスチェックと自動復旧設定付き）                      |
| **トレーディング実行環境**         | Amazon ECS Fargate（マルチAZ対応、Circuit Breaker有効化、Auto Recovery）    |
| **学習環境**                | Amazon SageMaker Training + SageMaker Pipelines（ステップ失敗時のリカバリ対応） |
| **学習用データ保存**            | Amazon S3（高耐久・バージョニング・クロスリージョンレプリケーション）                         |
| **学習済みモデル保存**           | Amazon S3（ライフサイクル管理・バージョニング・冗長構成）                               |
| **CI/CD（アプリ・MLパイプライン）** | AWS CodePipeline + CodeBuild（再実行可能・段階的デプロイ）                     |
| **モニタリング・アラート**         | Amazon CloudWatch（アラーム、メトリクス）、AWS X-Ray（障害の可視化）                 |
| **ログ・障害分析**             | Amazon CloudWatch Logs + AWS S3（長期保存、Athenaによる障害解析）             |
| **認証・認可**               | AWS IAM（きめ細かいアクセス制御）、Amazon Cognito（UI/APIアクセス制御）               |
| **ネットワーク・セキュリティ**       | Amazon VPC（マルチAZ構成） + Security Groups + WAF + Shield + NACL     |
| **フェイルオーバー / 冗長化**      | ALB + ECSのAuto Recovery、SageMaker retry、S3クロスリージョンレプリケーション      |


## GoogleCloudのシステム構成
| レイヤー       | サービス                                                           |
| ---------- | -------------------------------------------------------------- |
| 推論エンドポイント  | **GKE（GPUノード付き）+ Load Balancer + HPA**                         |
| 学習基盤       | **Vertex AI（Custom Training Job + Spot）**                      |
| 分散学習スケジューラ | **Vertex AI Pipelines or Composer (Airflow)**                  |
| フェイルオーバー   | **Cloud DNS + ネガティブキャッシュ制御 + Load Balancerヘルスチェック**            |
| モニタリング     | **Cloud Monitoring + Alerting（Slack webhook）**                 |
| ストレージ      | **Cloud Storage（バージョニング＋KMS暗号化）**                              |
| 障害検知/復旧    | GKE Node Auto Repair + Multi-Zone Cluster                      |
| ログ・監査      | **Cloud Audit Logs + Cloud Logging + Bucket Retention Policy** |


## 各クラウド比較まとめ（レジリエンス視点）

| 観点              | AWS                        | Azure                 | GCP                           |
| --------------- | -------------------------- | --------------------- | ----------------------------- |
| 高可用性EKS/AKS/GKE | ◎（成熟）                      | ◎（統合性高）               | ◎（高速かつ自動復旧）                   |
| GPU推論基盤         | ◎（SageMaker + EKS）         | ◯（AKS + VMSS）         | ◎（GKE + Vertex AI）            |
| 自動復旧とフェイルオーバー   | ◎（Route53 + Auto Recovery） | ◎（Traffic Manager）    | ◎（GKE Multi-Zone）             |
| コスト効率（スポット等）    | ◎（SageMaker Spot）          | ◎（AzureML + 優先VM）     | ◎（Vertex AI Spot）             |
| 運用通知・監査対応       | ◎（CloudWatch + SNS）        | ◎（Monitor + Sentinel） | ◎（Cloud Logging + Monitoring） |


