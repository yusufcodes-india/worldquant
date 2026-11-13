from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from app.core.config import settings
from app.core.security import verify_pairing_token, verify_host_header

router = APIRouter(prefix="/pairing", tags=["Pairing"])

class PairingStatusResponse(BaseModel):
    is_paired: bool
    app_name: str
    version: str
    host: str
    port: int
    pairing_token_preview: str

class VerifyPairingRequest(BaseModel):
    token: str

@router.get("/status", response_model=PairingStatusResponse, dependencies=[Depends(verify_host_header)])
def get_pairing_status(x_pilot_token: str = Header(None, alias="X-Pilot-Token")):
    expected = settings.get_or_create_pairing_token()
    is_paired = bool(x_pilot_token and x_pilot_token == expected)
    return PairingStatusResponse(
        is_paired=is_paired,
        app_name=settings.app_name,
        version=settings.version,
        host=settings.host,
        port=settings.port,
        pairing_token_preview=expected[:8] + "..." if expected else ""
    )

@router.post("/verify", dependencies=[Depends(verify_host_header)])
def verify_pairing(req: VerifyPairingRequest):
    expected = settings.get_or_create_pairing_token()
    if req.token == expected:
        return {"success": True, "message": "Extension pairing successful."}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid pairing token."
    )
