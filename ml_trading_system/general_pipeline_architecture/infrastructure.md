# テーマ
機械学習システムトレーディングのためのMLOpsパイプライン構成

## 共通設計ポリシー
| 機能        | 内容                                  |
| --------- | ----------------------------------- |
| IaC       | Terraformによる完全な管理（CI/CD含む）          |
| コンテナ      | Dockerを前提としたMLワークフロー構築              |
| モデル管理     | MLflow or 各クラウドネイティブのモデルレジストリ活用     |
| データパイプライン | バッチ + ストリーム対応、スケジュール学習              |
| モニタリング    | Prometheus/Grafana or クラウドネイティブ監視基盤 |

## awsのシステム構成

| 段階             | コンポーネント                                               | 詳細                                                                                                                                                                                             |
| -------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **モデル開発・実験**   | SageMaker Studio / SageMaker Experiments / CodeCommit | - S3でデータ・モデル・ログ管理（バージョニング + KMS暗号化）<br>- Experimentsでメタデータ/トライアル管理<br>- IaC: Terraform + SageMaker SDK<br>- Git: CodeCommit/CodeCatalyst連携で再現性担保                                               |
| **学習パイプライン**   | SageMaker Pipelines / Spot Instances                  | - `SageMaker Pipelines`で再学習・前処理・登録を一元化<br>- Spotインスタンスでコスト最適化（失敗時オンデマンドにフォールバック）<br>- Step Functions + EventBridge: 精度劣化・日次・週次再学習トリガー<br>- CloudWatch Logs + S3（Glacier/Intelligent Tiering）保管 |
| **デプロイ & 推論**  | SageMaker Endpoint + ALB/API Gateway + Lambda         | - GPU対応（ml.g5/inf1） + AutoScaling<br>- Canary/ブルーグリーン対応: Model Registry + Approval Workflow + CodeDeploy<br>- 通信: ALB (VPC) or API Gateway + Lambda（外部連携用）                                     |
| **モニタリング・再学習** | Model Monitor + CloudWatch + Lambda                   | - データ・コンセプトドリフト監視（Model Monitor）<br>- CloudWatch Anomaly Detectionで精度監視<br>- SNS + Slack通知 + Lambdaで再学習 or 承認依頼                                                                                |
| **セキュリティ・監査**  | IAM + KMS + VPC + CloudTrail                          | - IAM最小権限（ABAC/SCP制御）<br>- KMS暗号化 + S3バージョニング + VPCエンドポイント<br>- CloudTrail + GuardDuty + Security Hub連携                                                                                        |


## Azureのシステム構成

| 段階 | コンポーネント | 詳細 |
|------|------------|------|
| **モデル開発・実験** | Azure Machine Learning Studio + MLflow統合 | データ管理: Azure Data Lake Gen2 + Datasetオブジェクト |
| **学習パイプライン** | 低優先ノードでコスト削減 | Compute: Azure ML Compute Instance/Cluster<br>パイプライン管理: Azure ML Pipelines + GitHub Actions<br>データ転送: Azure Data Factory（スケジュール学習） |
| **デプロイ & 推論** | 本番環境 | Azure Kubernetes Service（AKS）+ Azure ML Inference Server<br>CI/CD: Azure DevOps + ML登録〜AKS反映自動化 |
| **モニタリング・再学習** | Azure Monitor + Application Insights | Data Drift Monitor + Custom Alert<br>Logic Appsで再学習フロー起動 |
| **セキュリティ & 監査** | RBAC最小権限 | Private Endpoint, Customer-Managed Keys<br>Azure Purview + Azure Monitor Logsによる追跡 |

## GoogleCloudのシステム構成

| 段階 | コンポーネント | 詳細 |
|------|------------|------|
| **モデル開発・実験** | Vertex AI Workbench（JupyterLab環境） | データ管理: BigQuery / Cloud Storage（gsutilバージョニング活用） |
| **学習パイプライン** | Vertex AI Pipelines（Kubeflow Pipelinesベース） | 学習: Vertex AI Training + Preemptible GPU（コスト削減）<br>オーケストレーション: Cloud Scheduler + Cloud Functions or Workflows |
| **デプロイ & 推論** | Vertex AI Endpoint | 推論: オンライン推論、Auto Scaling<br>Canary対応: Endpoint traffic split機能<br>バックアップ: Cloud Functions + Cloud Run経由のトリガー式切替 |
| **モニタリング・再学習** | Vertex AI Model Monitoring | データ/予測品質の監視<br>Cloud Logging + Error Reporting + Slack通知 or PagerDuty連携<br>再学習: BigQuery trigger → Pub/Sub → Vertex Pipeline再実行 |
| **セキュリティ & 監査** | IAM条件付きポリシー | CMEK, VPC Service Controls<br>Cloud Audit Logs + Data Loss Prevention APIで監査/匿名化 |

## 比較表
| 項目       | AWS                          | Azure             | GCP                    |
| -------- | ---------------------------- | ----------------- | ---------------------- |
| MLOps統合度 | ◎（SageMaker中心に統合）            | ○（サービス多岐に渡るが連携可能） | ◎（Vertex AIに統合）        |
| コスト最適化   | ◎（スポット/AutoML柔軟）             | ○（低優先ノードは効果的）     | ◎（Preemptible + BQ活用）  |
| 再学習自動化   | ◎（Step Functions/CloudWatch） | ○（Logic Apps連携）   | ◎（Pipelines + Pub/Sub） |
| 金融監査対応   | ◎（CloudTrail/KMS/制御粒度細かい）    | ◎（Purview、RBAC）   | ○（DLP活用で拡張）            |
| MLflow統合 | ◎（BYO）                       | ◎（公式統合）           | ○（カスタム統合）              |

