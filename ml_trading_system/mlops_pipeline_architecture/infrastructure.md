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

| レイヤー                    | 使用サービス                                             |
| ----------------------- | -------------------------------------------------- |
| **操作画面（フロントエンド）**       | Amazon EKS（Kubernetes上にUIアプリをホスティング）               |
| **API / バックエンド**        | Amazon EKS（APIサーバー、オーケストレーション処理）                   |
| **トレーディング実行環境**         | Amazon EKS（取引アルゴリズムのリアルタイム実行）                      |
| **学習環境**                | Amazon EKS + Kubeflow Pipelines（学習・チューニング）         |
| **学習用データ保存**            | Amazon RDS（PostgreSQLなど、構造化データ保存）                  |
| **学習済みモデル保存**           | Amazon S3（モデルアーティファクトの永続化）                         |
| **MLOpsパイプライン管理**       | Amazon EKS（Kubeflow上のPipeline）                     |
| **CI/CD（アプリ・モデル）**      | AWS CodePipeline + CodeBuild + EKS デプロイ            |
| **モニタリング・ログ管理**         | Amazon CloudWatch, Prometheus + Grafana |
| **認証・認可（UIやAPIアクセス制御）** | AWS IAM, AWS Cognito                               |
| **ネットワーク制御・セキュリティ**     | Amazon VPC, AWS Security Groups, AWS WAF           |


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

