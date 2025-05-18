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

| レイヤー          | サービス                                                                           |
| ------------- | ------------------------------------------------------------------------------ |
| **推論エンドポイント** | EKS on Fargate（GPUノード含む）+ ALB + HPA（水平スケーリング）<br>Fargate Spotも併用               |
| **学習基盤**      | SageMaker Training + Spot + Retryロジック（再学習中断対策）                                 |
| **スケジューラー**   | Amazon MWAA or Managed Workflows for Apache Airflow<br>Kubeflow on EKS（リソース管理） |
| **フェイルオーバー**  | Route 53 + ALB Health Check + Global Accelerator                               |
| **モニタリング**    | CloudWatch + Prometheus/Grafana on EKS + SNS（Slack通知）                          |
| **ストレージ**     | S3（バージョニング + KMS暗号化 + Intelligent-Tiering or Glacier Deep Archive）             |
| **自己回復設計**    | EKS Managed Node Groups（Auto Healing）<br>AZ分散 + Spot Diversification           |
| **ログ・監査**     | CloudTrail + CloudWatch Logs + S3 Glacier + AWS Config                         |


## Azureのシステム構成

| レイヤー       | サービス                                                      |
| ---------- | --------------------------------------------------------- |
| 推論エンドポイント  | **Azure Kubernetes Service (AKS) + GPU VMSS**             |
| 学習基盤       | **Azure ML（GPUトレーニング、スポット優先）**                            |
| 分散学習スケジューラ | Azure ML Pipelines or AKS + KubeFlow                      |
| フェイルオーバー   | **Azure Traffic Manager + ヘルスプローブ**                       |
| モニタリング     | **Azure Monitor + Log Analytics + Action Group（Slack連携）** |
| ストレージ      | **Azure Blob（immutable blob + バージョン管理）**                  |
| 障害検知/復旧    | AKS Auto Healing + VMSS自動修復                               |
| ログ・監査      | **Azure Activity Logs + Diagnostic Logs + Sentinel連携**    |


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


