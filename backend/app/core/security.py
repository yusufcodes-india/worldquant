import re
from typing import Any, Dict, List, Union
from fastapi import Header, HTTPException, Request, status
from app.core.config import settings

ALLOWED_HOSTS = {"127.0.0.1", "localhost", "testserver"}

def verify_host_header(request: Request):
    """Guards against DNS Rebinding attacks by checking Host header."""
    host = request.headers.get("host", "").split(":")[0]
    if host not in ALLOWED_HOSTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security violation: Invalid host header '{host}'. Direct loopback access only."
        )

def verify_pairing_token(x_pilot_token: str = Header(None, alias="X-Pilot-Token")):
    """Verifies that incoming requests have the valid local pairing token."""
    expected = settings.get_or_create_pairing_token()
    if not x_pilot_token or x_pilot_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing or invalid X-Pilot-Token pairing credential."
        )
    return x_pilot_token

SENSITIVE_PATTERNS = [
    re.compile(r"(AIza[0-9A-Za-z-_]{35})"), # Google API Key
    re.compile(r"(bearer\s+[a-zA-Z0-9\._\-]+)", re.IGNORECASE),
    re.compile(r"([0-9a-fA-F]{64})"), # 32-byte hex token
]

def redact_secrets(data: Union[str, Dict[str, Any], List[Any]]) -> Union[str, Dict[str, Any], List[Any]]:
    """Recursively redacts API keys, tokens, and passwords from logs or export dictionaries."""
    if isinstance(data, str):
        redacted = data
        for pattern in SENSITIVE_PATTERNS:
            redacted = pattern.sub("[REDACTED_SECRET]", redacted)
        return redacted
    elif isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if any(term in k.lower() for term in ["token", "key", "password", "secret", "auth", "credential"]):
                new_dict[k] = "[REDACTED_SECRET]"
            else:
                new_dict[k] = redact_secrets(v)
        return new_dict
    elif isinstance(data, list):
        return [redact_secrets(item) for item in data]
    return data
