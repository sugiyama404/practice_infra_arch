import uuid
import json
import time
import logging
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime
import redis
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, MetaData, Table
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"

class ActivityStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"

@dataclass
class Activity:
    name: str
    handler: Callable
    compensation_handler: Optional[Callable] = None
    params: Dict[str, Any] = None
    max_retries: int = 3
    retry_count: int = 0
    status: ActivityStatus = ActivityStatus.PENDING
    result: Any = None
    error: str = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}

@dataclass
class WorkflowExecution:
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.RUNNING
    activities: List[Activity] = None
    current_activity_index: int = 0
    created_at: datetime = None
    updated_at: datetime = None
    error: str = None
    result: Any = None
    
    def __post_init__(self):
        if self.activities is None:
            self.activities = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

class SagaWorkflowManager:
    """
    メルカリの記事を参考にしたSagaパターンベースのワークフロー管理システム
    """
    
    def __init__(self, db_url: str, redis_url: str):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.redis_client = redis.from_url(redis_url)
        
        # ワークフロー実行状態を保存するテーブル定義
        self.metadata = MetaData()
        self.workflows_table = Table(
            'workflows',
            self.metadata,
            Column('workflow_id', String(36), primary_key=True),
            Column('status', String(20), nullable=False),
            Column('activities', Text, nullable=False),  # JSON string
            Column('current_activity_index', Integer, default=0),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow),
            Column('error', Text, nullable=True),
            Column('result', Text, nullable=True)
        )
        
        self.metadata.create_all(self.engine)
    
    def create_workflow(self, workflow_id: str = None) -> str:
        """新しいワークフローを作成"""
        if workflow_id is None:
            workflow_id = str(uuid.uuid4())
        
        execution = WorkflowExecution(workflow_id=workflow_id)
        self._save_workflow_execution(execution)
        
        logger.info(f"Created workflow: {workflow_id}")
        return workflow_id
    
    def add_activity(self, workflow_id: str, activity: Activity):
        """ワークフローにアクティビティを追加"""
        execution = self._load_workflow_execution(workflow_id)
        if not execution:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        execution.activities.append(activity)
        self._save_workflow_execution(execution)
        
        logger.info(f"Added activity '{activity.name}' to workflow {workflow_id}")
    
    def execute_workflow(self, workflow_id: str) -> Any:
        """
        ワークフローを実行
        メルカリの記事のexecuteAuthorizeActivities的な処理
        """
        execution = self._load_workflow_execution(workflow_id)
        if not execution:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        logger.info(f"Starting workflow execution: {workflow_id}")
        
        try:
            # 各アクティビティを順次実行
            while execution.current_activity_index < len(execution.activities):
                activity = execution.activities[execution.current_activity_index]
                
                logger.info(f"Executing activity: {activity.name}")
                
                # アクティビティ実行
                success = self._execute_activity(execution, activity)
                
                if success:
                    execution.current_activity_index += 1
                    self._save_workflow_execution(execution)
                else:
                    # アクティビティが失敗した場合、補償トランザクションを実行
                    logger.error(f"Activity {activity.name} failed, starting compensation")
                    self._compensate_workflow(execution)
                    return None
            
            # すべてのアクティビティが成功
            execution.status = WorkflowStatus.COMPLETED
            self._save_workflow_execution(execution)
            
            logger.info(f"Workflow {workflow_id} completed successfully")
            return execution.result
            
        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed with error: {str(e)}")
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            self._save_workflow_execution(execution)
            raise
    
    def _execute_activity(self, execution: WorkflowExecution, activity: Activity) -> bool:
        """
        単一アクティビティを実行（リトライ機能付き）
        メルカリの記事のActivity実行部分
        """
        activity.status = ActivityStatus.RUNNING
        
        for attempt in range(activity.max_retries + 1):
            try:
                # アクティビティハンドラーを実行
                result = activity.handler(**activity.params)
                
                activity.status = ActivityStatus.COMPLETED
                activity.result = result
                
                logger.info(f"Activity {activity.name} completed successfully")
                return True
                
            except Exception as e:
                activity.retry_count = attempt + 1
                activity.error = str(e)
                
                if self._is_completable_error(e):
                    # 完了可能エラー（残高不足など）の場合、リトライせずに失敗
                    logger.error(f"Activity {activity.name} failed with completable error: {str(e)}")
                    activity.status = ActivityStatus.FAILED
                    return False
                elif attempt < activity.max_retries:
                    # 一時的エラーの場合、リトライ
                    logger.warning(f"Activity {activity.name} failed (attempt {attempt + 1}), retrying: {str(e)}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    # リトライ回数上限
                    logger.error(f"Activity {activity.name} failed after {activity.max_retries + 1} attempts: {str(e)}")
                    activity.status = ActivityStatus.FAILED
                    return False
        
        return False
    
    def _compensate_workflow(self, execution: WorkflowExecution):
        """
        補償トランザクションを実行
        メルカリの記事の補償処理部分
        """
        logger.info(f"Starting compensation for workflow {execution.workflow_id}")
        execution.status = WorkflowStatus.COMPENSATING
        
        # 実行済みアクティビティを逆順で補償
        for i in range(execution.current_activity_index - 1, -1, -1):
            activity = execution.activities[i]
            
            if activity.status == ActivityStatus.COMPLETED and activity.compensation_handler:
                logger.info(f"Compensating activity: {activity.name}")
                
                try:
                    # 補償ハンドラーを実行（成功するまでリトライ）
                    max_compensation_retries = 5
                    for attempt in range(max_compensation_retries):
                        try:
                            activity.compensation_handler(**activity.params)
                            activity.status = ActivityStatus.COMPENSATED
                            logger.info(f"Activity {activity.name} compensated successfully")
                            break
                        except Exception as e:
                            if attempt < max_compensation_retries - 1:
                                logger.warning(f"Compensation for {activity.name} failed (attempt {attempt + 1}), retrying: {str(e)}")
                                time.sleep(2 ** attempt)
                            else:
                                logger.error(f"Compensation for {activity.name} failed after {max_compensation_retries} attempts: {str(e)}")
                                raise
                                
                except Exception as e:
                    execution.status = WorkflowStatus.FAILED
                    execution.error = f"Compensation failed for activity {activity.name}: {str(e)}"
                    self._save_workflow_execution(execution)
                    raise
        
        execution.status = WorkflowStatus.COMPENSATED
        self._save_workflow_execution(execution)
        logger.info(f"Workflow {execution.workflow_id} compensation completed")
    
    def _is_completable_error(self, error: Exception) -> bool:
        """
        完了可能エラーかどうかを判定
        メルカリの記事の「完了可能エラー」の概念
        """
        error_msg = str(error).lower()
        completable_errors = [
            'insufficient balance',
            'invalid payment method',
            'out of stock',
            'user not found',
            'authorization failed'
        ]
        
        return any(completable_error in error_msg for completable_error in completable_errors)
    
    def _save_workflow_execution(self, execution: WorkflowExecution):
        """ワークフロー実行状態をデータベースに保存"""
        with self.SessionLocal() as session:
            # アクティビティをJSONに変換（関数は保存できないので除外）
            activities_data = []
            for activity in execution.activities:
                activity_data = {
                    'name': activity.name,
                    'params': activity.params,
                    'max_retries': activity.max_retries,
                    'retry_count': activity.retry_count,
                    'status': activity.status.value,
                    'result': activity.result,
                    'error': activity.error
                }
                activities_data.append(activity_data)
            
            # データベースに保存
            stmt = self.workflows_table.insert().values(
                workflow_id=execution.workflow_id,
                status=execution.status.value,
                activities=json.dumps(activities_data),
                current_activity_index=execution.current_activity_index,
                created_at=execution.created_at,
                updated_at=datetime.utcnow(),
                error=execution.error,
                result=json.dumps(execution.result) if execution.result else None
            ).prefix_with("REPLACE")
            
            session.execute(stmt)
            session.commit()
    
    def _load_workflow_execution(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """データベースからワークフロー実行状態を読み込み"""
        with self.SessionLocal() as session:
            stmt = self.workflows_table.select().where(
                self.workflows_table.c.workflow_id == workflow_id
            )
            result = session.execute(stmt).first()
            
            if not result:
                return None
            
            # JSONデータを復元（ハンドラー関数は別途登録が必要）
            activities_data = json.loads(result.activities)
            activities = []
            for activity_data in activities_data:
                # ハンドラー関数はレジストリから取得する必要がある
                activity = Activity(
                    name=activity_data['name'],
                    handler=lambda: None,  # プレースホルダー
                    params=activity_data['params'],
                    max_retries=activity_data['max_retries'],
                    retry_count=activity_data['retry_count'],
                    status=ActivityStatus(activity_data['status']),
                    result=activity_data['result'],
                    error=activity_data['error']
                )
                activities.append(activity)
            
            execution = WorkflowExecution(
                workflow_id=result.workflow_id,
                status=WorkflowStatus(result.status),
                activities=activities,
                current_activity_index=result.current_activity_index,
                created_at=result.created_at,
                updated_at=result.updated_at,
                error=result.error,
                result=json.loads(result.result) if result.result else None
            )
            
            return execution
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """ワークフローの実行状態を取得"""
        execution = self._load_workflow_execution(workflow_id)
        if not execution:
            return None
        
        return {
            'workflow_id': execution.workflow_id,
            'status': execution.status.value,
            'current_activity_index': execution.current_activity_index,
            'total_activities': len(execution.activities),
            'activities': [
                {
                    'name': activity.name,
                    'status': activity.status.value,
                    'retry_count': activity.retry_count,
                    'error': activity.error
                }
                for activity in execution.activities
            ],
            'created_at': execution.created_at.isoformat(),
            'updated_at': execution.updated_at.isoformat(),
            'error': execution.error
        }