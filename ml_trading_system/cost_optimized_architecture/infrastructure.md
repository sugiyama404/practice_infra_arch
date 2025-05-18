# テーマ
機械学習システムトレーディングのためのコスト最適化システム構成

## 共通の設計方針

| 機能          | 方針                                 |
| ----------- | ---------------------------------- |
| **IaC**     | 全クラウドでTerraform利用                  |
| **GPUリソース** | スポットインスタンス/割引インスタンス活用              |
| **学習ジョブ**   | バッチ型でスケーラブルに、Preemptible/Spot を活用  |
| **推論**      | サーバレス or オートスケーリング構成、最大500ms以下を目指す |
| **データ**     | オブジェクトストレージ＋Cold/Archive Tier活用    |
| **監視・可視化**  | モニタリングツールでコスト・性能を可視化               |
| **セキュリティ**  | IAM、VPC、KMS等を使ったゼロトラスト構成           |

## awsのシステム構成

| レイヤー                    | 使用サービス                                                     |
| ----------------------- | ---------------------------------------------------------- |
| **操作画面（フロントエンド）**       | Amazon ECS Fargate（SPAまたはUIアプリのホスティング）                     |
| **API / バックエンド**        | Amazon API Gateway（HTTP API） + AWS Lambda（軽量でスケーラブルなAPI処理） |
| **トレーディング実行環境**         | AWS Lambda（イベント駆動・従量課金でコスト効率よくトレード実行）                      |
| **学習環境**                | ローカル環境（学習） + Amazon S3（h5モデルファイルのアップロード先）                  |
| **学習用データ保存**            | Amazon S3（構造化または非構造化のデータ保存）                                |
| **学習済みモデル保存**           | Amazon S3（h5ファイルなどのモデルアーティファクト保存）                          |
| **CI/CD（API・UIデプロイ）**   | AWS CodePipeline + CodeBuild + Fargate / Lambda デプロイ       |
| **認証・認可（UIやAPIアクセス制御）** | Amazon Cognito（ユーザー管理） または IAM（Lambda/APIへのアクセス制御）         |
| **監視・ロギング**             | Amazon CloudWatch（ログ収集、アラーム） + AWS X-Ray（トレース）             |
| **ネットワーク・セキュリティ**       | AWS VPC（Fargate用） + Security Groups + IAM Roles（最小権限の付与）   |



### コスト最適化ポイント
+ ローカル学習によるSageMakerコスト削減
+ ECS Fargateは使用時のみ課金（オートスケーリング設定）
+ API Gateway HTTP APIはREST APIより約70%コスト削減
+ Lambdaによるサーバレス実行で使用分のみ課金
+ S3 Intelligent Tieringでデータ保存コスト削減
+ EC2インスタンスはSavings Plan/Spot活用

## Azureのシステム構成
| レイヤー        | サービス                                                   |
| --------- | ------------------------------------------------------ |
| データ保存     | Azure Blob Storage (Hot + Archive Tier)                |
| モデル学習     | Azure Machine Learning + Azure Batch (低優先度VM)          |
| 推論API     | Azure Functions + API Management（軽量モデル） or AKS（重たいモデル） |
| モデル管理     | Azure ML Model Registry + Container Registry           |
| パイプライン自動化 | Azure Data Factory or Azure ML Pipelines               |
| コスト可視化    | Azure Cost Management + Monitor                        |
| セキュリティ    | Azure RBAC、Private Endpoint、Key Vault、Policy           |

### コスト最適化ポイント
+ Spot相当の「低優先度VM」利用
+ Blob Storageの自動階層化
+ Azure Functionsでサーバレス推論
+ Azure ReservationsやSavings Plan活用

## GoogleCloudのシステム構成
| レイヤー        | サービス                                                       |
| --------- | ---------------------------------------------------------- |
| データ保存     | Cloud Storage + Autoclass                                  |
| モデル学習     | Vertex AI Training (Preemptible GPU) or AI Platform on GKE |
| 推論API     | Cloud Run（軽量モデル） or Vertex AI Endpoint（Auto-scaling）       |
| モデル管理     | Vertex AI Model Registry + Artifact Registry               |
| パイプライン自動化 | Vertex AI Pipelines（Kubeflowベース）                           |
| コスト可視化    | Cloud Billing + Cost Table + BigQuery Billing Export       |
| セキュリティ    | IAM、VPC Service Controls、Cloud KMS、Org Policy              |

### コスト最適化ポイント
+ Preemptible GPU（最大80%オフ）
+ Cloud Run（秒単位課金、Auto-scaling）
+ Autoclassによるストレージ階層管理
+ BigQueryで予算分析 & アラート自動化

## 推奨構成（コスト重視 + 強化学習）
| クラウド      | 選定理由                                                              |
| --------- | ----------------------------------------------------------------- |
| **AWS**   | SageMaker + Spot + Lambda構成が豊富。学習・推論ともにオプティマイズしやすい。金融機関との実績も多数。   |
| **GCP**   | Preemptible GPUとCloud Runの相性が良く、Vertex AIで全体統合できる。Kubeflowとの親和性も◎ |
| **Azure** | 他よりコスト面で少し劣る印象（機能は揃っている）。企業契約/ライセンスがあれば有力候補。                      |

