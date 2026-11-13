import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from app.adapters.base import PlatformAdapter
from app.core.config import settings

logger = logging.getLogger("brain_adapter")

class BrainPlatformAdapter(PlatformAdapter):
    """
    WorldQuant BRAIN Real Platform Adapter.
    Strictly guarded:
    - Never fabricates endpoints or results.
    - Uses verified ALTCHA solver + JWT authentication.
    - Simulation submission is strictly gated by approved campaign budget.
    - Programmatic self-correlation queries GET /alphas/{alpha_id}/correlations/self.
    - Final alpha submission is never automated.
    """
    def __init__(self):
        self.username = settings.brain_username
        self.password = settings.brain_password
        self.base_url = settings.brain_base_url.rstrip("/")
        self.user_id: Optional[str] = None
        self._user_approved_live_session = False

    @property
    def mode(self) -> str:
        return "LIVE"

    def approve_live_session(self, approved: bool = True):
        self._user_approved_live_session = approved

    def _run_async(self, coro):
        """Helper to run async calls synchronously across worker contexts."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        else:
            return asyncio.run(coro)

    async def _get_authenticated_client(self):
        from alpha_harness.brain.client import BrainClient
        from alpha_harness.brain.endpoints import BrainEndpoints
        from alpha_harness.brain.auth import Authenticator

        client = BrainClient(self.base_url)
        endpoints = BrainEndpoints(client)
        auth = Authenticator(endpoints)
        session = await auth.login(self.username, self.password)
        if not session.authenticated:
            await client.aclose()
            raise PermissionError(f"WorldQuant BRAIN authentication failed: {session.detail}")
        self.user_id = session.user_id
        return client, endpoints

    def check_authentication(self) -> Dict[str, Any]:
        if not self.username or not self.password:
            return {
                "authenticated": False,
                "mode": "LIVE",
                "error": "Missing BRAIN credentials in environment."
            }

        async def _check():
            client, endpoints = await self._get_authenticated_client()
            try:
                user_info = await endpoints.get_user(self.user_id)
                return {
                    "authenticated": True,
                    "mode": "LIVE",
                    "user_id": self.user_id,
                    "name": f"{user_info.get('firstName', '')} {user_info.get('lastName', '')}".strip(),
                    "email": user_info.get("email"),
                    "permissions": user_info.get("permissions", [])
                }
            finally:
                await client.aclose()

        try:
            return self._run_async(_check())
        except Exception as e:
            logger.error("Authentication check failed: %s", e)
            return {"authenticated": False, "mode": "LIVE", "error": str(e)}

    def discover_capabilities(self) -> Dict[str, Any]:
        return {
            "mode": "LIVE",
            "verified_capabilities": [
                "Fast Expression Language (FASTEXPR)",
                "Region USA / Universe TOP3000",
                "Delay 1 / Decay 0-4",
                "Subindustry Neutralization",
                "Automated Simulation Dispatch & Polling",
                "GET /users/{user_id}/alphas Portfolio Sync",
                "GET /users/{user_id}/settings/simulation Profile Sync",
                "Official Self-Correlation: GET /alphas/{alpha_id}/correlations/self",
                "Production Correlation: GET /alphas/{alpha_id}/correlations/prod",
                "Official Checks (Sharpe, Fitness, Turnover, Sub-Universe, Pasteurization)"
            ],
            "unverified_capabilities": [
                "Pre-simulation offline correlation without running simulation"
            ],
            "strict_safeguards": [
                "Final alpha submission is strictly manual (autonomous alpha submission prohibited)",
                "Campaign budgets are enforced atomically in SQLite before any simulation dispatch",
                "Local candidate-to-candidate correlation is strictly labeled as LOCAL ESTIMATE"
            ]
        }

    def fetch_user_simulation_settings(self) -> Dict[str, Any]:
        """Fetches the user's simulation settings from /users/{user_id}/settings/simulation."""
        async def _fetch():
            client, _ = await self._get_authenticated_client()
            try:
                resp = await client.request("GET", f"/users/{self.user_id}/settings/simulation")
                return resp.body if isinstance(resp.body, dict) else {}
            finally:
                await client.aclose()
        return self._run_async(_fetch())

    def fetch_user_alphas(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Fetches the user's alphas from /users/{user_id}/alphas."""
        async def _fetch():
            client, _ = await self._get_authenticated_client()
            try:
                resp = await client.request("GET", f"/users/{self.user_id}/alphas?limit={limit}&offset={offset}")
                return resp.body if isinstance(resp.body, dict) else {}
            finally:
                await client.aclose()
        return self._run_async(_fetch())

    def submit_simulation(self, expression: str, settings_dict: Dict[str, Any], candidate_id: str) -> Dict[str, Any]:
        if not self._user_approved_live_session:
            raise PermissionError(
                "Safety Guard: Live simulation submission rejected because explicit user approval was not granted."
            )

        from alpha_harness.brain.schemas import SimulationRequest, SimulationSettings

        async def _submit():
            client, endpoints = await self._get_authenticated_client()
            try:
                sim_settings = SimulationSettings(
                    instrument_type=settings_dict.get("instrument_type", "EQUITY"),
                    region=settings_dict.get("region", "USA"),
                    universe=settings_dict.get("universe", "TOP3000"),
                    delay=int(settings_dict.get("delay", 1)),
                    decay=int(settings_dict.get("decay", 0)),
                    neutralization=settings_dict.get("neutralization", "SUBINDUSTRY"),
                    truncation=float(settings_dict.get("truncation", 0.08)),
                    pasteurization=settings_dict.get("pasteurization", "ON"),
                    unit_handling=settings_dict.get("unit_handling", "VERIFY"),
                    nan_handling=settings_dict.get("nan_handling", "ON"),
                    language=settings_dict.get("language", "FASTEXPR"),
                    visualization=False
                )
                sim_req = SimulationRequest(type="REGULAR", settings=sim_settings, regular=expression)
                resp = await endpoints.create_simulation(sim_req)
                location = resp.location or ""
                sim_id = location.rstrip("/").split("/")[-1] if location else None
                return {
                    "submission_id": sim_id,
                    "location": location,
                    "status": "submitting" if sim_id else "failed",
                    "http_status": resp.status
                }
            finally:
                await client.aclose()

        return self._run_async(_submit())

    def query_simulation_status(self, submission_id: str) -> Dict[str, Any]:
        async def _query():
            client, endpoints = await self._get_authenticated_client()
            try:
                resp = await endpoints.read_simulation(submission_id)
                body = resp.body if isinstance(resp.body, dict) else {}
                return {
                    "submission_id": submission_id,
                    "status": body.get("status", "running"),
                    "progress": body.get("progress"),
                    "retry_after": resp.retry_after or 2.0,
                    "alpha_id": body.get("alpha"),
                    "raw": body
                }
            finally:
                await client.aclose()

        return self._run_async(_query())

    def fetch_simulation_results(self, submission_id: str, alpha_id: Optional[str] = None) -> Dict[str, Any]:
        async def _fetch():
            client, endpoints = await self._get_authenticated_client()
            try:
                target_alpha_id = alpha_id
                if not target_alpha_id:
                    sim_resp = await endpoints.read_simulation(submission_id)
                    target_alpha_id = (sim_resp.body or {}).get("alpha")
                
                if not target_alpha_id:
                    return {"status": "ERROR", "error": "No alpha ID associated with simulation"}

                alpha_body = await endpoints.alpha_body(target_alpha_id)
                summary = alpha_body.get("is", {})
                return {
                    "submission_id": submission_id,
                    "alpha_id": target_alpha_id,
                    "main_sharpe": summary.get("sharpe"),
                    "fitness": summary.get("fitness"),
                    "turnover": summary.get("turnover"),
                    "returns": summary.get("returns"),
                    "margin": summary.get("margin"),
                    "checks": summary.get("checks", []),
                    "self_correlation": summary.get("selfCorrelation"),
                    "prod_correlation": summary.get("prodCorrelation"),
                    "raw": alpha_body
                }
            finally:
                await client.aclose()

        return self._run_async(_fetch())

    def check_self_correlation(self, candidate_id: str, expression: str, reference_ids: List[str], alpha_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves official self-correlation from GET /alphas/{alpha_id}/correlations/self.
        """
        if not alpha_id:
            return {
                "candidate_id": candidate_id,
                "status": "CHECK UNAVAILABLE (REQUIRES ALPHA ID)",
                "is_local_estimate": False,
                "provenance_source": "platform_api",
                "notes": "Alpha ID is required to poll the official platform /alphas/{id}/correlations/self endpoint.",
                "official_pass": None
            }

        async def _check_self():
            client, endpoints = await self._get_authenticated_client()
            try:
                corr_data = await endpoints.correlations(alpha_id, kind="self")
                max_corr = corr_data.get("max")
                min_corr = corr_data.get("min")
                records = corr_data.get("records", [])
                
                # Official threshold for self-correlation pass is max < 0.70
                official_pass = (max_corr < 0.70) if max_corr is not None else None
                return {
                    "candidate_id": candidate_id,
                    "alpha_id": alpha_id,
                    "status": "VERIFIED" if official_pass is not None else "PENDING",
                    "is_local_estimate": False,
                    "provenance_source": "official_platform_endpoint",
                    "max_correlation": max_corr,
                    "min_correlation": min_corr,
                    "correlated_alphas_count": len(records),
                    "official_pass": official_pass,
                    "records": records[:5]  # Top correlated entries
                }
            finally:
                await client.aclose()

        return self._run_async(_check_self())

    def check_prod_correlation(self, alpha_id: str) -> Dict[str, Any]:
        """
        Retrieves production correlation from GET /alphas/{alpha_id}/correlations/prod.
        """
        async def _check_prod():
            client, endpoints = await self._get_authenticated_client()
            try:
                corr_data = await endpoints.correlations(alpha_id, kind="prod")
                return {
                    "alpha_id": alpha_id,
                    "provenance_source": "official_platform_endpoint",
                    "max_correlation": corr_data.get("max"),
                    "min_correlation": corr_data.get("min"),
                    "raw": corr_data
                }
            finally:
                await client.aclose()

        return self._run_async(_check_prod())

    def reconcile_uncertain_submission(self, submission_id: str, expression: str) -> Dict[str, Any]:
        status_info = self.query_simulation_status(submission_id)
        return {
            "submission_id": submission_id,
            "reconciled": status_info.get("status") in ("COMPLETE", "WARNING", "ERROR"),
            "status_info": status_info
        }
