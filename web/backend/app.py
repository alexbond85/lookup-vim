import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from web.backend.routes import router

app = FastAPI(title="nvim-lookup")

# CORS for Tauri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes (must be registered before static file mounts to take priority)
app.include_router(router)

# Serve frontend only in development mode (when directory exists)
# In production, Tauri serves the frontend from embedded assets
frontend_dir = Path("web/frontend")
if frontend_dir.exists():
    # Keep /static/* for backward compatibility
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
    
    # Serve at root for relative paths (Tauri production bundle compatibility)
    # This allows ./app.js to work when index.html is served from root
    @app.get("/")
    async def root():
        return FileResponse("web/frontend/index.html")
    
    # Mount frontend files at root for relative path support
    # Note: This must come after @app.get("/") to avoid conflicts
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend_root")
