from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class PlatformAdapter(ABC):
    @property
    @abstractmethod
    def mode(self) -> str:
        """Returns the mode name: 'MOCK', 'LIVE', or 'MANUAL'."""
        pass

    @abstractmethod
    def check_authentication(self) -> Dict[str, Any]:
        """Verifies session credentials and connectivity."""
        pass

    @abstractmethod
    def discover_capabilities(self) -> Dict[str, Any]:
        """Returns available platform capabilities (e.g. self-correlation API, simulation endpoints)."""
        pass

    @abstractmethod
    def submit_simulation(self, expression: str, settings: Dict[str, Any], candidate_id: str) -> Dict[str, Any]:
        """Submits a simulation job to the platform."""
        pass

    @abstractmethod
    def query_simulation_status(self, submission_id: str) -> Dict[str, Any]:
        """Queries the status of an in-flight simulation job."""
        pass

    @abstractmethod
    def fetch_simulation_results(self, submission_id: str) -> Dict[str, Any]:
        """Fetches final simulation metrics and reports."""
        pass

    @abstractmethod
    def check_self_correlation(self, candidate_id: str, expression: str, reference_ids: List[str]) -> Dict[str, Any]:
        """Checks self-correlation against the user's submitted reference alphas."""
        pass

    @abstractmethod
    def reconcile_uncertain_submission(self, submission_id: str, expression: str) -> Dict[str, Any]:
        """Attempts to look up or reconcile an ambiguous network outcome."""
        pass
