# テーマ
機械学習システムトレーディングのためのシンプルなプロトタイプ構成

## awsのシステム構成

| 要素         | サービス                                             |
| ---------- | ------------------------------------------------ |
| 学習環境       | SageMaker Notebook + SageMaker Training Job（GPU） |
| ストレージ      | S3（データ/モデル保存）                                    |
| ログ監視       | CloudWatch                                       |
| アクセス制御     | IAM（ロールごとのアクセス権設定）                               |
| 可視化        | Amazon QuickSight or ローカルNotebook                |
| 自動化（オプション） | Step Functions + EventBridge（スケジュール実験）           |

### 特徴
- SageMakerはプロトタイピングに最適なマネージド環境。
- 必要な時だけTraining Jobを起動 → GPU課金時間を短縮。
- 実験ログやモデルをS3で一元管理。
- IAMロールで細かいアクセス管理が可能。

## Azureのシステム構成

| 要素         | サービス                                                |
| ---------- | --------------------------------------------------- |
| 学習環境       | Azure Machine Learning（Compute Instance + Pipeline） |
| ストレージ      | Azure Blob Storage                                  |
| ログ監視       | Azure Monitor + Application Insights                |
| アクセス制御     | Azure RBAC（リソースごと）                                  |
| 可視化        | Azure ML Studio（UIベースのログ分析）                         |
| 自動化（オプション） | Azure ML Pipeline + Scheduled Job                   |

### 特徴
- Azure ML StudioのGUIベースで少人数でも扱いやすい。
- Compute InstanceとPipelineで分離 → コスト効率のよい実行。
- シンプルなJupyter/VSCodeベースの環境あり。
- Azure DevOpsとの連携も可能。

## GoogleCloudのシステム構成

| 要素         | サービス                                                       |
| ---------- | ---------------------------------------------------------- |
| 学習環境       | Vertex AI Notebooks + Vertex AI Training（Custom Container） |
| ストレージ      | Cloud Storage（GCS）                                         |
| ログ監視       | Cloud Logging（旧Stackdriver）                                |
| アクセス制御     | IAM（プロジェクト/サービス単位）                                         |
| 可視化        | BigQuery + Looker Studio or Notebook内                      |
| 自動化（オプション） | Vertex Pipelines（Kubeflowベース）                              |

### 特徴
- Vertex AIはNotebook + Training + Pipelineが統合されており、柔軟。
- GPUインスタンスのオンデマンド利用が容易。
- Cloud StorageとBigQueryによる大規模データ処理が可能。
- ログ/監視系が他社に比べても整備されている。

## 比較と選定の視点

| 観点         | AWS                   | Azure       | GCP                  |
| ---------- | --------------------- | ----------- | -------------------- |
| 開発体験       | ◎（Jupyter統合）          | ○（GUI重視）    | ◎（統合度高い）             |
| GPU起動コスト制御 | ◎（SageMaker Training） | ○（VM停止が必要）  | ◎（Training Job単位）    |
| データ分析・可視化  | ○（QuickSight）         | ○（Studio内）  | ◎（BigQuery + Looker） |
| 自動化容易性     | ◎（Step Functions）     | ○（Pipeline） | ◎（Vertex Pipelines）  |
| 初学者向け      | ○                     | ◎           | ○                    |

## 結論と選定例（状況別）
- 社内にAWS利用者が多く、細かな制御が必要な場合 → AWS
- GUI中心で管理・可視化が楽な方がいい場合 → Azure
- 最新AI機能・スケーラブルで統合性の高いML環境が欲しい場合 → GCP



