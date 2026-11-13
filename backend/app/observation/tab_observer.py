import re
from typing import Any, Dict, List, Optional
from app.core.config import settings

class TabObserver:
    """
    Optional current-tab observation service.
    Guarded by feature flag, domain allowlist, and prompt-injection defenses.
    """
    ALLOWED_DOMAINS = [
        re.compile(r"^https://([a-zA-Z0-9-]+\.)*worldquantbrain\.com(/.*)?$"),
        re.compile(r"^https://([a-zA-Z0-9-]+\.)*brain\.worldquant\.com(/.*)?$"),
    ]

    def __init__(self):
        self.enabled = settings.feature_flag_tab_observation

    def is_domain_permitted(self, url: str) -> bool:
        if not url:
            return False
        return any(pattern.match(url) for pattern in self.ALLOWED_DOMAINS)

    def parse_dom_extract(self, raw_html_or_text: str, current_url: str) -> Dict[str, Any]:
        """
        Parses untrusted page content.
        Treats page text strictly as data, never as system instructions.
        """
        if not self.enabled:
            raise PermissionError("Tab observation is disabled. Enable FEATURE_FLAG_TAB_OBSERVATION first.")

        if not self.is_domain_permitted(current_url):
            raise PermissionError(f"URL '{current_url}' is not on the permitted observation domain allowlist.")

        # Sanitize against prompt injection: strip directive markers
        sanitized = re.sub(r"(?i)(ignore previous instructions|system prompt|api_key|token)", "[FILTERED]", raw_html_or_text)
        
        return {
            "status": "OBSERVED",
            "url": current_url,
            "sanitized_length": len(sanitized),
            "content_snippet": sanitized[:500],
            "indicator": "OBSERVING_TAB_ACTIVE"
        }

tab_observer = TabObserver()
