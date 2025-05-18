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

| レイヤー         | サービス・設計                                | 詳細                                                                                                                      |
| ------------ | -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **推論・サービス**  | ECS Fargate + ALB + Auto Scaling         | - トレーディング実行環境: ECS Fargate (Multi-AZ) + ALB<br>- 操作画面: ECS Fargate (Multi-AZ) + CloudFront<br>- 高可用性: Service Auto Scaling + ヘルスチェック |
| **学習環境**     | ECS on EC2 + Auto Scaling                | - GPU対応EC2インスタンス (g4dn/g5) + Auto Scaling<br>- スポットインスタンス活用でコスト削減<br>- 複数AZにまたがるクラスタ構成                                      |
| **フェイルオーバー** | Route 53 + Global Accelerator          | - Route 53 + ヘルスチェックで複数リージョン切替<br>- Global Acceleratorで低遅延・障害時切替<br>- 異常時: CloudWatch Alarm + Lambdaで再起動 or スケールアウト       |
| **バックアップ冗長** | マルチリージョンECSクラスタ + S3レプリケーション           | - セカンダリリージョンのECS Fargateクラスタをスタンバイ状態で維持<br>- S3クロスリージョンレプリケーションでモデルとデータを同期<br>- Auto Scaling EventsでCloudWatch Alarmsトリガー      |
| **モデル更新**    | CodePipeline + ECR + CodeDeploy        | - CodePipelineで自動CI/CD<br>- Blue/Green Deploymentによる無停止更新<br>- ECRでコンテナイメージ管理とバージョニング                                      |
| **監視・監査**    | CloudWatch + Container Insights + X-Ray | - Container Insightsでコンテナレベル監視<br>- X-Rayでサービス間トレーシング<br>- GuardDuty + CloudTrail + Security Hubで攻撃検知                     |


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





