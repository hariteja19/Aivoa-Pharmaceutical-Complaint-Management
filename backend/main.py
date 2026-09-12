import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.core.database import engine, Base
from app.api.v1 import health, complaints, copilot

from sqlalchemy import text, inspect

# Create database tables automatically on startup
Base.metadata.create_all(bind=engine)

# Ensure complaint_reference column exists on existing DB instances
try:
    with engine.connect() as conn:
        inspector = inspect(engine)
        if "complaints" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("complaints")]
            if "complaint_reference" not in columns:
                conn.execute(text("ALTER TABLE complaints ADD COLUMN complaint_reference VARCHAR"))
                conn.commit()
except Exception as e:
    logger.warning(f"DB schema migration check: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AIVOA AI-Powered Pharmaceutical Customer Complaint Management System API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers (mounted under /api and /api/v1 for robust client resolution)
app.include_router(health.router)
app.include_router(complaints.router, prefix="/api")
app.include_router(copilot.router, prefix="/api")
app.include_router(complaints.router, prefix="/api/v1")
app.include_router(copilot.router, prefix="/api/v1")

@app.get("/")
def root():
    return {
        "message": "Welcome to AIVOA Pharmaceutical Complaint Management System API",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
