from fastapi import APIRouter
from app.api.endpoints import prices, predictions, health, scraping, holidays, models, news, admin

router = APIRouter()

router.include_router(health.router, tags=["health"])
router.include_router(prices.router, prefix="/prices", tags=["prices"])
router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
router.include_router(scraping.router, prefix="/scraping", tags=["scraping"])
router.include_router(holidays.router, prefix="/holidays", tags=["holidays"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(models.router, prefix="/models", tags=["models"])
router.include_router(news.router, prefix="/news", tags=["news"])
