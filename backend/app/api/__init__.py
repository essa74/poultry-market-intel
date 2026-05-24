from fastapi import APIRouter
from app.api.endpoints import prices, predictions, health

router = APIRouter()

router.include_router(health.router, tags=["health"])
router.include_router(prices.router, prefix="/prices", tags=["prices"])
router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
