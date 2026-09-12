from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "llm_model": settings.GROQ_MODEL,
        "database_url_configured": settings.DATABASE_URL.split("://")[0]
    }
