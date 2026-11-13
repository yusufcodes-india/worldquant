from typing import Any, Dict, List, Optional
from app.adapters.base import PlatformAdapter

class ManualImportAdapter(PlatformAdapter):
    """
    Manual fallback adapter: allows user to import simulation outputs and
    correlation results directly from platform copy-paste or JSON.
    """
    @property
    def mode(self) -> str:
        return "MANUAL"

    def check_authentication(self) -> Dict[str, Any]:
        return {
            "authenticated": True,
            "mode": "MANUAL",
            "message": "Manual import mode ready. No outbound platform requests will be dispatched."
        }

    def discover_capabilities(self) -> Dict[str, Any]:
        return {
            "mode": "MANUAL",
            "supported_inputs": ["raw_simulation_json", "clipboard_metrics_text", "pnl_csv_json"],
            "disclaimer": "All metrics are marked as MANUALLY REPORTED."
        }

    def submit_simulation(self, expression: str, settings: Dict[str, Any], candidate_id: str) -> Dict[str, Any]:
        return {
            "submission_id": f"manual-pending-{candidate_id[:8]}",
            "candidate_id": candidate_id,
            "status": "AWAITING_MANUAL_INPUT",
            "is_mock": False,
            "message": "Awaiting manual result import."
        }

    def query_simulation_status(self, submission_id: str) -> Dict[str, Any]:
        return {"submission_id": submission_id, "status": "AWAITING_MANUAL_INPUT"}

    def fetch_simulation_results(self, submission_id: str) -> Dict[str, Any]:
        raise NotImplementedError("Manual adapter requires explicit user input via the import endpoint.")

    def check_self_correlation(self, candidate_id: str, expression: str, reference_ids: List[str]) -> Dict[str, Any]:
        return {
            "candidate_id": candidate_id,
            "status": "NOT CHECKED",
            "is_local_estimate": False,
            "provenance_source": "manual_import",
            "notes": "Awaiting manual self-correlation report input."
        }

    def reconcile_uncertain_submission(self, submission_id: str, expression: str) -> Dict[str, Any]:
        return {"submission_id": submission_id, "reconciled": True, "status": "MANUAL_RESOLVED"}
