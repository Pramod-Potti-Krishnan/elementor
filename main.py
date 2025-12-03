"""
Visual Elements Orchestrator Service v1.0

Coordinates AI content generation for presentation visual elements:
- Charts (via Chart AI Service)
- Diagrams (via Diagram AI Service)
- Text & Tables (via Text Table AI Service)
- Images (via Image AI Service)
- Infographics (via Infographic AI Service)

Architecture:
Frontend -> Orchestrator -> AI Services -> Frontend -> postMessage -> Layout Service
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import (
    chart_router,
    diagram_router,
    text_router,
    table_router,
    image_router,
    infographic_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Visual Elements Orchestrator v1.0")
    logger.info("AI Service URLs:")
    logger.info(f"  Chart:       {settings.CHART_SERVICE_URL}")
    logger.info(f"  Diagram:     {settings.DIAGRAM_SERVICE_URL}")
    logger.info(f"  Text/Table:  {settings.TEXT_TABLE_SERVICE_URL}")
    logger.info(f"  Image:       {settings.IMAGE_SERVICE_URL}")
    logger.info(f"  Infographic: {settings.INFOGRAPHIC_SERVICE_URL}")
    yield
    logger.info("Shutting down Visual Elements Orchestrator")


app = FastAPI(
    title="Visual Elements Orchestrator",
    description="Coordinates AI content generation for presentation visual elements (Charts, Diagrams, Text, Tables, Images, Infographics)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(chart_router.router, prefix="/api/generate", tags=["Chart"])
app.include_router(diagram_router.router, prefix="/api/generate", tags=["Diagram"])
app.include_router(text_router.router, prefix="/api/generate", tags=["Text"])
app.include_router(table_router.router, prefix="/api/generate", tags=["Table"])
app.include_router(image_router.router, prefix="/api/generate", tags=["Image"])
app.include_router(infographic_router.router, prefix="/api/generate", tags=["Infographic"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "visual-elements-orchestrator",
        "version": "1.0.0",
        "services": {
            "chart": settings.CHART_SERVICE_URL,
            "diagram": settings.DIAGRAM_SERVICE_URL,
            "text_table": settings.TEXT_TABLE_SERVICE_URL,
            "image": settings.IMAGE_SERVICE_URL,
            "infographic": settings.INFOGRAPHIC_SERVICE_URL
        }
    }


@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "Visual Elements Orchestrator",
        "version": "1.0.0",
        "description": "Coordinates AI content generation for presentation visual elements",
        "endpoints": {
            "chart": {
                "generate": "POST /api/generate/chart",
                "constraints": "GET /api/generate/chart/constraints",
                "palettes": "GET /api/generate/chart/palettes",
                "validate": "POST /api/generate/chart/validate"
            },
            "diagram": {
                "generate": "POST /api/generate/diagram",
                "status": "GET /api/generate/diagram/status/{job_id}",
                "types": "GET /api/generate/diagram/types"
            },
            "text": {
                "generate": "POST /api/generate/text",
                "transform": "POST /api/generate/text/transform",
                "autofit": "POST /api/generate/text/autofit",
                "constraints": "GET /api/generate/text/constraints/{width}/{height}"
            },
            "table": {
                "generate": "POST /api/generate/table",
                "transform": "POST /api/generate/table/transform",
                "analyze": "POST /api/generate/table/analyze",
                "presets": "GET /api/generate/table/presets"
            },
            "image": {
                "generate": "POST /api/generate/image",
                "styles": "GET /api/generate/image/styles",
                "credits": "GET /api/generate/image/credits/{presentation_id}"
            },
            "infographic": {
                "generate": "POST /api/generate/infographic",
                "types": "GET /api/generate/infographic/types"
            },
            "health": "GET /health"
        },
        "docs": "/docs"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
