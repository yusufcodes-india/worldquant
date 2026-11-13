import os
import secrets
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BASE_DIR = PROJECT_ROOT / "backend"
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Auto-load .env from project root if present
for env_path in [PROJECT_ROOT / ".env", BASE_DIR / ".env"]:
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k not in os.environ:
                    os.environ[k] = v

class Settings(BaseModel):
    app_name: str = "Alpha Research Pilot"
    version: str = "1.0.0"
    host: str = os.getenv("PILOT_HOST", "127.0.0.1")
    port: int = int(os.getenv("PILOT_PORT", "8765"))
    db_path: str = os.getenv("PILOT_DB_PATH", str(DATA_DIR / "pilot.db"))
    
    # Security: pairing token
    pairing_token: str = os.getenv("PILOT_PAIRING_TOKEN", "")
    
    # Gemini
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    
    # Integration Mode: MOCK, LIVE, MANUAL
    integration_mode: str = os.getenv("INTEGRATION_MODE", "MOCK").upper()
    brain_username: Optional[str] = os.getenv("BRAIN_USERNAME", None)
    brain_password: Optional[str] = os.getenv("BRAIN_PASSWORD", None)
    brain_base_url: str = os.getenv("BRAIN_BASE_URL", "https://api.worldquantbrain.com")
    
    # Feature flags
    feature_flag_tab_observation: bool = os.getenv("FEATURE_FLAG_TAB_OBSERVATION", "false").lower() == "true"
    
    # CORS: Allowed origins for extensions & local testing
    allowed_origin_regex: str = r"^(chrome-extension://.*|http://127\.0\.0\.1:.*|http://localhost:.*)$"

    def get_or_create_pairing_token(self) -> str:
        if self.pairing_token:
            return self.pairing_token
        
        token_file = DATA_DIR / ".pairing_token"
        if token_file.exists():
            token = token_file.read_text().strip()
            if token:
                self.pairing_token = token
                return token
        
        # Generate new 32-byte secure token
        token = secrets.token_hex(32)
        token_file.write_text(token)
        # secure permissions on unix
        try:
            token_file.chmod(0o600)
        except Exception:
            pass
        self.pairing_token = token
        return token

settings = Settings()
# Initialize pairing token
settings.get_or_create_pairing_token()
