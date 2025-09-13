import os
import uuid
import logging
from typing import Dict, Any
from workflow.manager import SagaWorkflowManager, Activity
from services.user_service import UserService
from services.payment_service import PaymentService
from services.order_service import OrderService
from utils import wait_for_database, wait_for_redis

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PurchaseWorkflowService:
    """
    メルカリの記事を参考にした購入ワークフローサービス
    複数マイクロサービス間の分散トランザクションを管理
    """

    def __init__(self):
        # データベース接続URL
        # Use the PyMySQL driver via the mysql+pymysql scheme (PyMySQL is
        # installed in requirements). Using plain `mysql://` can trigger
        # `No module named 'MySQLdb'` if the MySQL-Python driver is missing.
        self.user_db_url = os.getenv(
            "USER_DB_URL", "mysql+pymysql://user:user123@localhost:3306/user_service"
        )
        self.payment_db_url = os.getenv(
            "PAYMENT_DB_URL",
            "mysql+pymysql://payment:payment123@localhost:3307/payment_service",
        )
        self.order_db_url = os.getenv(
            "ORDER_DB_URL",
            "mysql+pymysql://order:order123@localhost:3308/order_service",
        )
        self.saga_db_url = os.getenv(
            "SAGA_DB_URL",
            "mysql+pymysql://saga:saga123@localhost:3309/saga_orchestrator",
        )
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        # Wait for dependent services (DBs / Redis) to be reachable before
        # creating SQLAlchemy engines. This avoids immediate connection refused
        # errors when containers start at the same time.
        wait_for_database(self.user_db_url, timeout=60)
        wait_for_database(self.payment_db_url, timeout=60)
        wait_for_database(self.order_db_url, timeout=60)
        wait_for_database(self.saga_db_url, timeout=60)
        wait_for_redis(self.redis_url, timeout=30)

        # サービス初期化
        self.user_service = UserService(self.user_db_url)
        self.payment_service = PaymentService(self.payment_db_url)
        self.order_service = OrderService(self.order_db_url)
        self.workflow_manager = SagaWorkflowManager(self.saga_db_url, self.redis_url)

        logger.info("PurchaseWorkflowService initialized")

    def create_purchase_workflow(self, purchase_request: Dict[str, Any]) -> str:
        """
        購入ワークフローを作成・実行
        メルカリの記事のcreateExchangeWorkflow相当
        """
        user_id = purchase_request["user_id"]
        product_id = purchase_request["product_id"]
        quantity = purchase_request["quantity"]
        payment_method_id = purchase_request["payment_method_id"]
        transaction_id = str(uuid.uuid4())

        logger.info(
            f"Creating purchase workflow for user {user_id}, product {product_id}, quantity {quantity}"
        )

        # ワークフロー作成
        workflow_id = self.workflow_manager.create_workflow(transaction_id)

        # 商品価格取得（簡略化）
        amount = 100.0 * quantity  # 仮の計算

        # アクティビティを定義（メルカリの記事のexecuteAuthorizeActivities相当）

        # 1. 残高予約アクティビティ
        balance_reserve_activity = Activity(
            name="reserve_balance",
            handler=self.user_service.reserve_balance,
            compensation_handler=self.user_service.cancel_balance,
            params={
                "user_id": user_id,
                "amount": amount,
                "transaction_id": transaction_id,
            },
        )

        # 2. 決済予約アクティビティ
        payment_reserve_activity = Activity(
            name="reserve_payment",
            handler=self.payment_service.reserve_payment,
            compensation_handler=self.payment_service.cancel_payment,
            params={
                "user_id": user_id,
                "payment_method_id": payment_method_id,
                "amount": amount,
                "transaction_id": transaction_id,
            },
        )

        # 3. 商品予約アクティビティ
        product_reserve_activity = Activity(
            name="reserve_product",
            handler=self.order_service.reserve_product,
            compensation_handler=self.order_service.cancel_order,
            params={
                "user_id": user_id,
                "product_id": product_id,
                "quantity": quantity,
                "transaction_id": transaction_id,
            },
        )

        # 4. 残高確定アクティビティ
        balance_confirm_activity = Activity(
            name="confirm_balance",
            handler=self.user_service.confirm_balance,
            params={"user_id": user_id, "transaction_id": transaction_id},
        )

        # 5. 決済実行アクティビティ
        payment_charge_activity = Activity(
            name="charge_payment",
            handler=self.payment_service.charge_payment,
            params={"user_id": user_id, "transaction_id": transaction_id},
        )

        # 6. 注文確定アクティビティ
        order_confirm_activity = Activity(
            name="confirm_order",
            handler=self.order_service.confirm_order,
            params={"user_id": user_id, "transaction_id": transaction_id},
        )

        # ワークフローにアクティビティを追加
        activities = [
            balance_reserve_activity,
            payment_reserve_activity,
            product_reserve_activity,
            balance_confirm_activity,
            payment_charge_activity,
            order_confirm_activity,
        ]

        for activity in activities:
            self.workflow_manager.add_activity(workflow_id, activity)

        return workflow_id

    def execute_purchase(self, workflow_id: str) -> Dict[str, Any]:
        """購入ワークフローを実行"""
        try:
            result = self.workflow_manager.execute_workflow(workflow_id)

            if result is not None:
                return {
                    "success": True,
                    "workflow_id": workflow_id,
                    "message": "Purchase completed successfully",
                }
            else:
                return {
                    "success": False,
                    "workflow_id": workflow_id,
                    "message": "Purchase failed and compensated",
                }

        except Exception as e:
            logger.error(f"Purchase workflow {workflow_id} failed: {str(e)}")
            return {
                "success": False,
                "workflow_id": workflow_id,
                "message": f"Purchase failed: {str(e)}",
            }

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """ワークフロー実行状態を取得"""
        return self.workflow_manager.get_workflow_status(workflow_id)


def demo_successful_purchase():
    """成功するケースのデモ"""
    service = PurchaseWorkflowService()

    print("=== 成功ケースのデモ ===")

    # 購入リクエスト
    purchase_request = {
        "user_id": 1,  # alice
        "product_id": 1,  # Bitcoin
        "quantity": 1,
        "payment_method_id": 1,
    }

    # ワークフロー作成
    workflow_id = service.create_purchase_workflow(purchase_request)
    print(f"Created workflow: {workflow_id}")

    # ワークフロー実行
    result = service.execute_purchase(workflow_id)
    print(f"Purchase result: {result}")

    # ワークフロー状態確認
    status = service.get_workflow_status(workflow_id)
    print(f"Workflow status: {status}")


def demo_failed_purchase():
    """失敗するケースのデモ（残高不足）"""
    service = PurchaseWorkflowService()

    print("\n=== 失敗ケースのデモ（残高不足） ===")

    # 購入リクエスト（高額商品で残高不足を引き起こす）
    purchase_request = {
        "user_id": 2,  # bob (残高500)
        "product_id": 1,  # Bitcoin (価格100 * quantity 10 = 1000)
        "quantity": 10,  # 残高不足になる
        "payment_method_id": 2,
    }

    # ワークフロー作成
    workflow_id = service.create_purchase_workflow(purchase_request)
    print(f"Created workflow: {workflow_id}")

    # ワークフロー実行
    result = service.execute_purchase(workflow_id)
    print(f"Purchase result: {result}")

    # ワークフロー状態確認
    status = service.get_workflow_status(workflow_id)
    print(f"Workflow status: {status}")


def demo_failed_purchase_stock():
    """失敗するケースのデモ（在庫不足）"""
    service = PurchaseWorkflowService()

    print("\n=== 失敗ケースのデモ（在庫不足） ===")

    # 購入リクエスト（大量注文で在庫不足を引き起こす）
    purchase_request = {
        "user_id": 3,  # charlie (残高2000)
        "product_id": 1,  # Bitcoin (在庫10)
        "quantity": 15,  # 在庫不足になる
        "payment_method_id": 3,
    }

    # ワークフロー作成
    workflow_id = service.create_purchase_workflow(purchase_request)
    print(f"Created workflow: {workflow_id}")

    # ワークフロー実行
    result = service.execute_purchase(workflow_id)
    print(f"Purchase result: {result}")

    # ワークフロー状態確認
    status = service.get_workflow_status(workflow_id)
    print(f"Workflow status: {status}")


def interactive_demo():
    """対話式デモ"""
    service = PurchaseWorkflowService()

    print("\n=== 対話式デモ ===")
    print("利用可能なユーザー:")
    print("1. alice (残高: 1000)")
    print("2. bob (残高: 500)")
    print("3. charlie (残高: 2000)")

    print("\n利用可能な商品:")
    print("1. Bitcoin (価格: 100, 在庫: 10)")
    print("2. Ethereum (価格: 100, 在庫: 20)")
    print("3. Litecoin (価格: 100, 在庫: 50)")

    try:
        user_id = int(input("\nユーザーIDを入力 (1-3): "))
        product_id = int(input("商品IDを入力 (1-3): "))
        quantity = int(input("数量を入力: "))
        payment_method_id = user_id  # 簡略化：ユーザーIDと同じ

        purchase_request = {
            "user_id": user_id,
            "product_id": product_id,
            "quantity": quantity,
            "payment_method_id": payment_method_id,
        }

        # ワークフロー作成・実行
        workflow_id = service.create_purchase_workflow(purchase_request)
        print(f"\nワークフロー作成: {workflow_id}")

        result = service.execute_purchase(workflow_id)
        print(f"購入結果: {result}")

        # 詳細な状態表示
        status = service.get_workflow_status(workflow_id)
        if status:
            print("\nワークフロー詳細:")
            print(f"  ステータス: {status['status']}")
            print(
                f"  進行状況: {status['current_activity_index']}/{status['total_activities']}"
            )
            print("  アクティビティ:")
            for i, activity in enumerate(status["activities"]):
                print(f"    {i + 1}. {activity['name']}: {activity['status']}")
                if activity["error"]:
                    print(f"       エラー: {activity['error']}")

    except KeyboardInterrupt:
        print("\nデモを終了します")
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")


if __name__ == "__main__":
    try:
        print("=== メルカリ風分散トランザクション デモ ===")
        print("Sagaパターンとオーケストレーションベースのワークフロー管理")
        print("")

        # 基本的なデモを実行
        demo_successful_purchase()
        demo_failed_purchase()
        demo_failed_purchase_stock()

        # 対話式デモ
        while True:
            print("\n" + "=" * 50)
            response = input("対話式デモを実行しますか？ (y/n): ").lower()
            if response == "y":
                interactive_demo()
            elif response == "n":
                break
            else:
                print("y または n を入力してください")

        print("\nデモを終了しました")

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        print(f"アプリケーションエラー: {str(e)}")
