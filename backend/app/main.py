import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import os
from pathlib import Path
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.core.security import ALLOWED_HOSTS
from app.db.migrations import run_migrations
from app.engine.queue import queue_engine
from app.api.reference_library import init_default_reference_library
from app.api.pairing import router as pairing_router
from app.api.campaigns import router as campaigns_router
from app.api.candidates import router as candidates_router
from app.api.correlations import router as correlations_router
from app.api.reference_library import router as ref_lib_router
from app.api.settings_api import router as settings_router
from app.api.export_import import router as export_import_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("alpha_pilot")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Alpha Research Pilot Backend...")
    # 1. Run migrations
    run_migrations()
    # 2. Recover in-flight queue state
    queue_engine.recover_on_startup()
    # 3. Init default reference library
    init_default_reference_library()

    # 4. Restore persisted live-session approval
    try:
        from app.api.settings_api import _get_app_config
        from app.adapters.manager import adapter_manager
        if _get_app_config("live_session_approved", "0") == "1":
            adapter = adapter_manager.get_adapter()
            if hasattr(adapter, "approve_live_session"):
                adapter.approve_live_session(True)
                logger.info("Restored persisted live-session approval from app_config.")
    except Exception as e:
        logger.warning(f"Could not restore live-session approval: {e}")
    
    token = settings.get_or_create_pairing_token()
    logger.info(f"Pilot Daemon listening on http://{settings.host}:{settings.port}")
    logger.info(f"Secure Pairing Token: {token}")
    yield
    logger.info("Pilot Daemon shutting down.")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Autonomous local-first quantitative research pilot for WorldQuant BRAIN Fast Expressions.",
    lifespan=lifespan
)

class HostHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        host = request.headers.get("host", "").split(":")[0]
        if host not in ALLOWED_HOSTS:
            return JSONResponse(
                status_code=400,
                content={"detail": f"Security violation: Invalid host header '{host}'. Direct loopback access only."}
            )
        return await call_next(request)

app.add_middleware(HostHeaderMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DIST_DIR = Path(__file__).resolve().parent.parent.parent / "extension" / "dist"

# Mount API Routers
app.include_router(pairing_router)
app.include_router(campaigns_router)
app.include_router(candidates_router)
app.include_router(correlations_router)
app.include_router(ref_lib_router)
app.include_router(settings_router)
app.include_router(export_import_router)

@app.get("/health")
def health_check():
    from app.db.connection import get_db
    from app.adapters.manager import adapter_manager

    # DB liveness check
    db_ok = False
    db_tables = 0
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
            db_tables = cursor.fetchone()[0]
            db_ok = db_tables > 0
    except Exception:
        pass

    # Adapter status
    adapter = adapter_manager.get_adapter()
    adapter_mode = adapter.mode
    live_approved = getattr(adapter, "_user_approved_live_session", False)

    overall = "healthy" if db_ok else "degraded"

    return {
        "status": overall,
        "app": settings.app_name,
        "version": settings.version,
        "mode": settings.integration_mode,
        "db_ok": db_ok,
        "db_tables": db_tables,
        "adapter_mode": adapter_mode,
        "live_session_approved": live_approved,
    }

# Serve Dashboard and Extension assets if built
if (DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="static_assets")

@app.get("/")
@app.get("/dashboard")
def serve_dashboard():
    dashboard_file = DIST_DIR / "dashboard.html"
    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    return JSONResponse(
        {"status": "ready", "message": "Alpha Research Pilot backend running. Build extension with npm run build in extension/"}
    )

@app.get("/popup")
def serve_popup():
    popup_file = DIST_DIR / "popup.html"
    if popup_file.exists():
        return FileResponse(popup_file)
    return JSONResponse({"status": "ready"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
