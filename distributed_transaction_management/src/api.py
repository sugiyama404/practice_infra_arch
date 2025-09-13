from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from workflow.manager import SagaWorkflowManager
from services.user_service import UserService
from services.payment_service import PaymentService
from services.order_service import OrderService
from utils import wait_for_database, wait_for_redis
import os

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Distributed Transaction API", version="1.0.0")

# CORSミドルウェアを追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PurchaseRequest(BaseModel):
    user_id: int
    product_id: int
    quantity: int
    payment_method_id: int
    idempotency_key: str = None


class PurchaseResponse(BaseModel):
    success: bool
    workflow_id: str = None
    message: str


# サービス初期化
user_db_url = os.getenv(
    "USER_DB_URL", "mysql+pymysql://user:user123@localhost:3306/user_service"
)
payment_db_url = os.getenv(
    "PAYMENT_DB_URL",
    "mysql+pymysql://payment:payment123@localhost:3307/payment_service",
)
order_db_url = os.getenv(
    "ORDER_DB_URL",
    "mysql+pymysql://order:order123@localhost:3308/order_service",
)
saga_db_url = os.getenv(
    "SAGA_DB_URL",
    "mysql+pymysql://saga:saga123@localhost:3309/saga_orchestrator",
)
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

# Wait for services
wait_for_database(user_db_url, timeout=60)
wait_for_database(payment_db_url, timeout=60)
wait_for_database(order_db_url, timeout=60)
wait_for_database(saga_db_url, timeout=60)
wait_for_redis(redis_url, timeout=60)

user_service = UserService(user_db_url)
payment_service = PaymentService(payment_db_url)
order_service = OrderService(order_db_url)
saga_manager = SagaWorkflowManager(saga_db_url, redis_url)


@app.post("/purchase", response_model=PurchaseResponse)
async def purchase(request: PurchaseRequest):
    try:
        # Create workflow
        workflow_id = saga_manager.create_purchase_workflow(
            {
                "user_id": request.user_id,
                "product_id": request.product_id,
                "quantity": request.quantity,
                "payment_method_id": request.payment_method_id,
                "idempotency_key": request.idempotency_key,
            }
        )

        # Execute workflow
        result = saga_manager.execute_purchase(workflow_id)

        return PurchaseResponse(
            success=result.get("success", False),
            workflow_id=workflow_id,
            message=result.get("message", "Purchase completed"),
        )

    except Exception as e:
        logger.error(f"Purchase error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
