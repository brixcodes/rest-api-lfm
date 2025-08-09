from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import time
import os

# Supposons que router est défini dans src/api/router.py
from src.api.router import router
from src.util.database.database import init_db, close_db
from src.util.helper.logger import log_error, log_info

@asynccontextmanager
async def lifespan(app: FastAPI):
    log_info("🚀 Starting FastAPI application")
    try:
        await init_db()
        log_info("✅ Database initialized")
    except Exception as e:
        log_error(f"❌ Database initialization error: {e}")
        raise
    yield
    log_info("🛑 Stopping FastAPI application")
    try:
        await close_db()
        log_info("✅ Database connection closed")
    except Exception as e:
        log_error(f"❌ Database closure error: {e}")

app = FastAPI(
    title="Education Management API",
    description="API for managing educational resources, users, and data",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://lafaom-mao.vercel.app/",
        ""
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    log_info(f"📥 {request.method} {request.url.path}", client_ip=request.client.host, user_agent=request.headers.get("user-agent"))
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        log_info(f"📤 {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)", status_code=response.status_code)
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        process_time = time.time() - start_time
        log_error(f"❌ Error processing {request.method} {request.url.path}: {e}", process_time=process_time)
        raise

app.include_router(router)

# Configuration des fichiers statiques pour correspondre aux chemins d'upload
static_dirs = [
    ("/static/documents", "static/documents"),
    ("/static/images", "static/images"),
    ("/static/audios", "static/audios"),
    ("/static/videos", "static/videos")
]

for url_path, disk_path in static_dirs:
    try:
        # Créer le répertoire s'il n'existe pas
        os.makedirs(disk_path, exist_ok=True)
        app.mount(url_path, StaticFiles(directory=disk_path), name=f"static_{url_path.replace('/', '_')}")
        log_info(f"✅ Répertoire statique monté: {url_path} -> {disk_path}")
    except PermissionError as e:
        log_error(f"❌ Impossible de créer le répertoire {disk_path}: {e}")
        # Monter quand même si le répertoire existe
        if os.path.exists(disk_path):
            app.mount(url_path, StaticFiles(directory=disk_path), name=f"static_{url_path.replace('/', '_')}")
            log_info(f"⚠️ Répertoire statique monté (existant): {url_path} -> {disk_path}")
    except Exception as e:
        log_error(f"❌ Erreur lors de la configuration du répertoire statique {disk_path}: {e}")

@app.get("/")
async def root():
    return {"message": "Welcome to the Education Management API"}
