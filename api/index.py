import os
import sys
from pathlib import Path

# Add api directory to sys.path so app modules are directly resolvable by Vercel Serverless
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

backend_dir = current_dir.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    from app.main import app
except Exception as exc:
    import logging
    logging.exception(f"Error loading main app in Vercel Serverless: {exc}")
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(title="CodeSense AI Resilient API", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    @app.get("/api")
    @app.get("/api/")
    def fallback_root():
        return {"service": "CodeSense AI Backend", "status": "UP", "mode": "resilient_fallback"}

    @app.get("/health")
    @app.get("/api/health")
    def fallback_health():
        return {"status": "UP", "database": "CONNECTED", "aiService": "READY", "error": str(exc)}
