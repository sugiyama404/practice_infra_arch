# テーマ
機械学習システムトレーディングのための高可用性構成

## 設計方針（全クラウド共通）

| 機能        | 方針                                      |
| ----------- | --------------------------------------- |
| **可用性**     | マルチAZ & マルチリージョン対応、ヘルスチェック + 自動フェイルオーバー |
| **推論**      | GPU対応、低レイテンシ、スケーラブルなエンドポイント構成           |
| **モデル更新**   | ローリング or ブルーグリーンデプロイ、サービス無停止            |
| **監視・障害対応** | 24/7モニタリング、Slack/Teams通知、AutoHealing    |
| **インフラ管理**  | Terraformベース、IaCによる再現性と自動復旧性            |
| **セキュリティ**  | VPC内完結、IAM・KMS・WAF連携、DoS対策有り            |

## AWS のシステム構成

| レイヤー                    | 使用サービス                                                               |
| ----------------------- | -------------------------------------------------------------------- |
| **操作画面（フロントエンド）**       | Amazon ECS Fargate（ALB配下、マルチAZ対応）                                    |
| **API / バックエンド**        | Amazon ECS Fargate（API・バッチ処理用） + ALB（高可用なルーティング）                     |
| **トレーディング実行環境**         | Amazon ECS Fargate（マルチAZ配置、Auto Scaling、障害耐性の高い構成）                   |
| **学習環境**                | Amazon SageMaker Training + SageMaker Pipeline（学習の自動化と再現性）           |
| **学習用データ保存（元データ）**      | Amazon RDS（マルチAZ構成、ストレージ自動バックアップ）                                    |
| **ETL（前処理）**            | AWS Glue（RDS→S3へのETL処理、サーバーレスでスケーラブル）                                |
| **学習用データ保存（ETL後）**      | Amazon S3（SageMakerと連携、耐久性・可用性の高いストレージ）                              |
| **学習済みモデル保存**           | Amazon S3（モデルアーティファクト保存、バージョン管理）                                     |
| **CI/CD（アプリ・MLパイプライン）** | AWS CodePipeline + CodeBuild + ECS Fargate & SageMaker Pipelineのトリガー |
| **認証・認可（UI/API/学習）**    | AWS IAM（サービス間アクセス制御） + Amazon Cognito（ユーザー認証）                        |
| **モニタリング・ロギング**         | Amazon CloudWatch（ログ・メトリクス） + AWS X-Ray（分散トレース）                      |
| **ネットワーク・セキュリティ**       | Amazon VPC（マルチAZ構成） + Security Groups + NACLs + WAF + Shield         |
| **障害対応・自動復旧**           | ECS Auto Recovery、ALBヘルスチェック、SageMaker Retry、Glueリトライ設定              |


## Azureのシステム構成

| レイヤー | サービス |
|---------|---------|
| **推論・サービス** | • Azure Kubernetes Service (AKS) + NVIDIA GPUノードプール<br>• 推論API（FastAPIなど）をKubernetes上でスケーリング運用<br>• Azure Front Door or Traffic Manager<br>• グローバルロードバランサ（リージョン切替対応） |
| **可用性設計** | • ゾーン冗長AKS + Availability Zone<br>• Azure Load Balancer (Internal) + Azure Application Gateway (外部)<br>• Azure Monitor Alerts + Logic App → 自動修復 or 通知 |
| **モデル更新** | • Azure ML + AKS Endpoint with Blue/Green Deployment<br>• Azure DevOps Pipelines によるローリングアップデート自動化 |
| **監視・監査** | • Azure Monitor / Log Analytics / Application Insights<br>• Azure Policy + Purview + Activity Logs（監査用） |

## GoogleCloudのシステム構成

| レイヤー | サービス |
|---------|---------|
| **推論・サービス** | • Vertex AI Endpoint (GPU対応 + AutoScaling)<br>• Global Load Balancer + Cloud Armor (WAF)<br>• マルチリージョン構成とヘルスチェック付き |
| **可用性設計** | • Multi-region Endpoint with Regional Failover<br>• Cloud Monitoringの異常検知でCloud Functionsが切替実施<br>• Vertex AI Prediction + GKE backup構成（予備構成をGKE上に置く） |
| **モデル更新** | • Vertex AI Model Registry + Traffic Split<br>• ローリング or カナリア方式のデプロイ対応<br>• Cloud Build + Artifact Registry + Workflows |
| **監視・監査** | • Cloud Monitoring / Logging / Error Reporting<br>• Cloud Audit Logs + BigQuery転送 → 保管・分析対応 |

## クラウド別まとめ表

| 要素          | AWS                          | Azure                        | GCP                                       |
| ----------- | ---------------------------- | ---------------------------- | ----------------------------------------- |
| 推論サービス      | SageMaker Endpoint           | AKS + Azure ML               | Vertex AI Endpoint                        |
| 可用性手段       | Route53 + Multi-AZ & Region  | Azure Front Door + Zonal AKS | Global Load Balancer + Regional Endpoints |
| モデル更新       | Model Registry + Lambda      | Azure DevOps + AKS           | Traffic Split + Workflows                 |
| モニタリング      | CloudWatch + Lambda          | Azure Monitor + Logic App    | Cloud Monitoring + Cloud Functions        |
| フェイルオーバー    | 自動（Route53）                  | 手動 or LogicAppスクリプト          | Cloud Functionトリガー切替                      |
| GPU対応       | G5インスタンス / Elastic Inference | AKS GPU Node Pool            | NVIDIA A100 / T4対応                        |
| Terraform対応 | 全構成対応                        | 全構成対応                        | 全構成対応                                     |





