from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api import router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Poultry Market Intelligence Platform API — track fertilized egg prices, day-old chick prices, analyze trends, and predict future prices using AI.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.app_name}
