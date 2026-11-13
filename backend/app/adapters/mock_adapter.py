import hashlib
import math
import time
from typing import Any, Dict, List, Optional
from app.adapters.base import PlatformAdapter

class MockPlatformAdapter(PlatformAdapter):
    """
    Deterministic Mock Platform Adapter for WorldQuant BRAIN simulation.
    All outputs are explicitly marked as MOCK and deterministically computed
    from the candidate's normalized expression hash.
    """
    @property
    def mode(self) -> str:
        return "MOCK"

    def check_authentication(self) -> Dict[str, Any]:
        return {
            "authenticated": True,
            "mode": "MOCK",
            "username": "mock_pilot_user@brain.local",
            "permissions": ["simulate", "check_correlation", "view_results"],
            "message": "Deterministic Mock Platform active. No external network requests will be made."
        }

    def discover_capabilities(self) -> Dict[str, Any]:
        return {
            "mode": "MOCK",
            "supported_languages": ["Fast Expression"],
            "supported_regions": ["USA"],
            "supported_universes": ["TOP3000"],
            "max_simulations_per_day": 1500,
            "supports_programmatic_self_correlation": True,
            "supports_production_correlation": True,
            "disclaimer": "MOCK MODE - NOT OFFICIAL PLATFORM CAPABILITIES."
        }

    def submit_simulation(self, expression: str, settings: Dict[str, Any], candidate_id: str) -> Dict[str, Any]:
        expr_hash = hashlib.sha256(expression.strip().encode("utf-8")).hexdigest()
        submission_id = f"mock-sim-{expr_hash[:12]}"
        return {
            "submission_id": submission_id,
            "candidate_id": candidate_id,
            "status": "QUEUED",
            "is_mock": True,
            "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "settings": settings,
        }

    def query_simulation_status(self, submission_id: str) -> Dict[str, Any]:
        return {
            "submission_id": submission_id,
            "status": "COMPLETED",
            "progress": 1.0,
            "is_mock": True
        }

    def fetch_simulation_results(self, submission_id: str) -> Dict[str, Any]:
        # Generate deterministic metrics based on hash
        val = int(hashlib.md5(submission_id.encode("utf-8")).hexdigest(), 16)
        
        # main Sharpe between 1.10 and 2.30
        main_sharpe = round(1.10 + (val % 120) * 0.01, 2)
        # fitness between 0.80 and 2.10
        fitness = round(0.80 + ((val >> 4) % 130) * 0.01, 2)
        # turnover between 0.05 (5%) and 0.45 (45%)
        turnover = round(0.05 + ((val >> 8) % 40) * 0.01, 4)
        
        # Sub-universe Sharpe & dynamic cutoff
        # Cutoff usually ranges between 0.70 and 0.90
        subuniverse_cutoff = round(0.70 + ((val >> 12) % 21) * 0.01, 2)
        # Sub-universe sharpe can pass or fail
        subuniverse_sharpe = round(0.55 + ((val >> 16) % 45) * 0.01, 2)
        subuniverse_pass_margin = round(subuniverse_sharpe - subuniverse_cutoff, 2)
        
        weight_distribution_pass = (val % 7) != 0 # passes most of the time

        # Generate synthetic 252-day PnL series for local correlation calculations
        pnl_series = []
        seed = val
        for day in range(252):
            seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            norm_ret = ((seed % 10000) / 5000.0 - 1.0) * 0.015 + (main_sharpe / 252.0)
            date_str = f"2026-{1 + (day // 22):02d}-{(day % 22) + 1:02d}"
            pnl_series.append({"date": date_str, "pnl": round(norm_ret, 6)})

        return {
            "submission_id": submission_id,
            "is_mock": True,
            "platform_status": "COMPLETE",
            "main_sharpe": main_sharpe,
            "fitness": fitness,
            "turnover": turnover,
            "subuniverse_sharpe": subuniverse_sharpe,
            "subuniverse_cutoff": subuniverse_cutoff,
            "subuniverse_pass_margin": subuniverse_pass_margin,
            "weight_distribution_pass": weight_distribution_pass,
            "platform_reported_field_count": 2 + (val % 3),
            "platform_reported_op_count": 5 + (val % 5),
            "counts_verified": True,
            "raw_response": {
                "source": "MOCK_SIMULATION_ENGINE",
                "message": "Synthetic deterministic output for local testing.",
                "sharpe": main_sharpe,
                "fitness": fitness,
                "turnover": turnover,
                "subuniverse_sharpe": subuniverse_sharpe,
                "subuniverse_cutoff": subuniverse_cutoff,
            },
            "pnl_series": pnl_series
        }

    def check_self_correlation(self, candidate_id: str, expression: str, reference_ids: List[str]) -> Dict[str, Any]:
        val = int(hashlib.md5((candidate_id + expression).encode("utf-8")).hexdigest(), 16)
        # Measured self correlation between 0.35 and 0.85
        measured_corr = round(0.35 + (val % 51) * 0.01, 2)
        official_threshold = 0.70
        official_pass = measured_corr < official_threshold

        matched_alphas = []
        if reference_ids:
            pick = reference_ids[val % len(reference_ids)]
            matched_alphas.append(pick)

        return {
            "candidate_id": candidate_id,
            "is_mock": True,
            "check_type": "self_correlation",
            "status": "PLATFORM_VERIFIED_PASS" if official_pass else "PLATFORM_VERIFIED_FAIL",
            "measured_value": measured_corr,
            "official_threshold": official_threshold,
            "official_pass": official_pass,
            "comparison_alphas": matched_alphas,
            "provenance_source": "mock",
            "notes": "MOCK check result: deterministic calculation.",
        }

    def reconcile_uncertain_submission(self, submission_id: str, expression: str) -> Dict[str, Any]:
        return {
            "submission_id": submission_id,
            "reconciled": True,
            "status": "COMPLETED",
            "is_mock": True,
            "message": "Mock submission safely reconciled."
        }
