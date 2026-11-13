from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import verify_pairing_token, verify_host_header, redact_secrets
from app.core.config import settings
from app.adapters.manager import adapter_manager
from app.gemini.client import gemini_client
from app.db.connection import get_db

router = APIRouter(prefix="/settings", tags=["Settings"], dependencies=[Depends(verify_host_header), Depends(verify_pairing_token)])

def _get_app_config(key: str, default: str = "") -> str:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM app_config WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

def _set_app_config(key: str, value: str):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO app_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value)
        )
        conn.commit()

class SettingsUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    integration_mode: Optional[str] = None
    feature_flag_tab_observation: Optional[bool] = None

class LiveApprovalRequest(BaseModel):
    approve: bool

@router.get("")
def get_settings():
    adapter = adapter_manager.get_adapter()
    auth_info = adapter.check_authentication()
    capabilities = adapter.discover_capabilities()

    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "host": settings.host,
        "port": settings.port,
        "integration_mode": adapter_manager.current_mode,
        "adapter_mode": adapter.mode,
        "gemini_configured": bool(gemini_client.api_key),
        "gemini_model": gemini_client.model,
        "gemini_calls_count": gemini_client.calls_count,
        "gemini_tokens_used": gemini_client.tokens_used,
        "gemini_is_paused": gemini_client.is_paused,
        "feature_flag_tab_observation": settings.feature_flag_tab_observation,
        "auth_info": auth_info,
        "capabilities": capabilities
    }

@router.post("")
def update_settings(req: SettingsUpdateRequest):
    if req.gemini_api_key is not None:
        gemini_client.set_api_key(req.gemini_api_key)
        settings.gemini_api_key = req.gemini_api_key

    if req.gemini_model is not None:
        gemini_client.model = req.gemini_model
        settings.gemini_model = req.gemini_model

    if req.integration_mode is not None:
        adapter_manager.set_mode(req.integration_mode)
        settings.integration_mode = req.integration_mode

    if req.feature_flag_tab_observation is not None:
        settings.feature_flag_tab_observation = req.feature_flag_tab_observation

    return {"success": True, "message": "Settings updated successfully."}

@router.post("/approve_live")
def approve_live(req: LiveApprovalRequest):
    adapter = adapter_manager.get_adapter()
    if hasattr(adapter, "approve_live_session"):
        adapter.approve_live_session(req.approve)
        # Persist to SQLite so approval survives restarts
        _set_app_config("live_session_approved", "1" if req.approve else "0")
        return {"success": True, "live_approved": req.approve}
    return {"success": False, "message": "Current adapter does not require live approval."}

@router.get("/platform_simulation")
def get_platform_simulation_settings():
    adapter = adapter_manager.get_adapter()
    if hasattr(adapter, "fetch_user_simulation_settings"):
        return adapter.fetch_user_simulation_settings()
    return {}

@router.get("/live_approval")
def get_live_approval_status():
    persisted = _get_app_config("live_session_approved", "0")
    adapter = adapter_manager.get_adapter()
    in_memory = getattr(adapter, "_user_approved_live_session", False)
    return {"live_session_approved": persisted == "1", "in_memory": in_memory}

