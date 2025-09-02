import os
import logging
import uvicorn
from pathlib import Path
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.util.db.database import init_db
from src.api.router import (
    fichiers, adresses, utilisateurs, centres_formations, formations,
    sessions_formations, modules, ressources, dossiers_candidatures,
    pieces_jointes, reclamations, paiements, informations_descriptives,
    evaluations, resultats_evaluations, certificats, questions_evaluation, reponses_candidats
)
from src.util.db.setting import settings

# -----------------------
# Configure logging
# -----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# -----------------------
# Initialize FastAPI app
# -----------------------
app = FastAPI(
    title="LFM API",
    description="API pour la gestion des utilisateurs, formations, aides financières, et campagnes de financement.",
    version="1.0.0"
)

# -----------------------
# Configure CORS middleware
# -----------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajuster en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# Configure upload directory
# -----------------------
# Utiliser le répertoire de travail actuel pour l'upload
UPLOAD_DIR = "upload"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static files for upload directory - use absolute path
app.mount("/upload", StaticFiles(directory=UPLOAD_DIR), name="upload")

# Create main API router
# -----------------------
api_router = APIRouter()

# Include all sub-routers from the updated router.py
api_router.include_router(fichiers)
api_router.include_router(utilisateurs)
api_router.include_router(adresses)
api_router.include_router(centres_formations)
api_router.include_router(formations)
api_router.include_router(informations_descriptives)
api_router.include_router(sessions_formations)
api_router.include_router(modules)
api_router.include_router(ressources)
api_router.include_router(dossiers_candidatures)
api_router.include_router(pieces_jointes)
api_router.include_router(reclamations)
api_router.include_router(paiements)
api_router.include_router(evaluations)
api_router.include_router(questions_evaluation)
api_router.include_router(reponses_candidats)
api_router.include_router(resultats_evaluations)
api_router.include_router(certificats)

# Include the main router with a global prefix
app.include_router(api_router, prefix="/api/v1")

# -----------------------
# Event handlers
# -----------------------
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up the application...")
    await init_db()
    logger.info("Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down the application...")
    logger.info("Application shutdown complete.")

# -----------------------
# Root endpoint
# -----------------------
@app.get("/")
async def root():
    return {"message": "Welcome to the LFM API. Refer to /docs for API documentation."}

# -----------------------
# Run the application with Uvicorn if executed directly
# -----------------------
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )