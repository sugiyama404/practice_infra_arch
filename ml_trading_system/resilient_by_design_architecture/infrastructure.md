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
| **操作画面**     | ECS Fargate + ALB + Auto Scaling + CloudFront<br>マルチAZ配置 + Blue/Greenデプロイメント   |
| **推論エンドポイント** | ECS Fargate（トレーディング実行環境）+ ALB + Service Auto Scaling<br>Fargate Spotも併用で高コスト効率         |
| **学習基盤**      | SageMaker Training + Pipeline + Spot + Retryロジック（再学習中断対策）                      |
| **スケジューラー**   | SageMaker Pipelines + EventBridge + StepFunctions<br>自動再学習とモデル更新のオーケストレーション    |
| **フェイルオーバー**  | Route 53 + ALB Health Check + Global Accelerator<br>マルチリージョン構成とサーキットブレーカーパターン    |
| **モニタリング**    | CloudWatch + Container Insights + X-Ray + SNS（Slack通知）<br>異常検知と自動スケーリングトリガー      |
| **ストレージ**     | S3（バージョニング + KMS暗号化 + Intelligent-Tiering or Glacier Deep Archive）             |
| **自己回復設計**    | ECS Service Auto Recovery + ヘルスチェックベースの置換<br>AZ分散 + Spot Interruption対応          |
| **ログ・監査**     | CloudTrail + CloudWatch Logs + Firehose + S3 + AWS Config<br>システム全体の変更監査と証跡保存   |


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


