"""
Single Live Simulation Smoke Test on WorldQuant BRAIN.
Explicitly approved by user.
Budget: Exactly 1 simulation.
"""

import asyncio
import json
import logging
from alpha_harness.brain.client import BrainClient
from alpha_harness.brain.endpoints import BrainEndpoints
from alpha_harness.brain.auth import Authenticator
from alpha_harness.brain.schemas import SimulationRequest, SimulationSettings
from app.db.connection import get_db
from app.db.migrations import run_migrations

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("live_smoke_test")

async def run_live_smoke_test():
    run_migrations()
    client = BrainClient("https://api.worldquantbrain.com")
    endpoints = BrainEndpoints(client)
    auth = Authenticator(endpoints)

    try:
        logger.info("Authenticating with WorldQuant BRAIN...")
        session = await auth.login("e26b07f0603@adypu.edu.in", "Avenger220,")
        if not session.authenticated:
            logger.error("Authentication failed: %s", session.detail)
            return

        logger.info("Authenticated successfully. User ID: %s", session.user_id)

        # Candidate expression: 4 operators, 1 field (close), grouping subindustry
        expression = "group_neutralize(rank(close / ts_mean(close, 20)), subindustry)"
        
        sim_settings = SimulationSettings(
            instrument_type="EQUITY",
            region="USA",
            universe="TOP3000",
            delay=1,
            decay=0,
            neutralization="SUBINDUSTRY",
            truncation=0.08,
            pasteurization="ON",
            unit_handling="VERIFY",
            nan_handling="ON",
            language="FASTEXPR",
            visualization=False
        )

        sim_request = SimulationRequest(
            type="REGULAR",
            settings=sim_settings,
            regular=expression
        )

        logger.info("Dispatching EXACTLY 1 live simulation to POST /simulations...")
        logger.info("Expression: %s", expression)
        logger.info("Settings: USA TOP3000, Delay 1, Decay 0, Subindustry Neutral")

        # 1. POST /simulations
        response = await endpoints.create_simulation(sim_request)
        location = response.location
        logger.info("Simulation POST returned status %s. Location: %s", response.status, location)

        sim_id = location.rstrip("/").split("/")[-1] if location else None
        if not sim_id:
            logger.error("No simulation ID returned in Location header!")
            return

        logger.info("Live Simulation ID: %s. Now polling status...", sim_id)

        # 2. Poll GET /simulations/{id}
        max_polls = 120
        poll_count = 0
        terminal_status = None
        alpha_id = None
        sim_data = None

        while poll_count < max_polls:
            poll_resp = await endpoints.read_simulation(sim_id)
            body = poll_resp.body if isinstance(poll_resp.body, dict) else {}
            status = body.get("status")
            progress = body.get("progress")
            retry_after = poll_resp.retry_after or 2.0

            logger.info("Poll %d: status=%s, progress=%s, retry_after=%.1fs", poll_count + 1, status, progress, retry_after)

            if status in ("COMPLETE", "WARNING", "ERROR", "FAIL", "CANCELLED"):
                terminal_status = status
                alpha_id = body.get("alpha")
                sim_data = body
                break

            await asyncio.sleep(min(max(retry_after, 2.0), 10.0))
            poll_count += 1

        logger.info("Simulation reached terminal state: %s. Alpha ID: %s", terminal_status, alpha_id)

        # 3. If alpha ID generated, fetch full alpha metrics
        alpha_details = None
        if alpha_id:
            logger.info("Fetching real platform alpha metrics from GET /alphas/%s...", alpha_id)
            alpha_details = await endpoints.alpha_body(alpha_id)
            
            summary = alpha_details.get("is", {})
            logger.info("=" * 60)
            logger.info("OFFICIAL WORLDQUANT BRAIN SIMULATION RESULTS:")
            logger.info("Alpha ID    : %s", alpha_id)
            logger.info("Sharpe      : %s", summary.get("sharpe"))
            logger.info("Fitness     : %s", summary.get("fitness"))
            logger.info("Turnover    : %s", summary.get("turnover"))
            logger.info("Returns     : %s", summary.get("returns"))
            logger.info("Margin      : %s", summary.get("margin"))
            logger.info("Checks Count: %d", len(summary.get("checks", [])))
            for chk in summary.get("checks", []):
                logger.info("  Check [%s]: %s (Value=%s, Limit=%s)", chk.get("name"), chk.get("result"), chk.get("value"), chk.get("limit"))
            logger.info("=" * 60)

        # 4. Record into local DB with is_mock = 0
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Ensure campaign exists
            cursor.execute(
                """
                INSERT OR IGNORE INTO campaigns (
                    id, name, profile_name, profile_snapshot, budget_simulations, submitted_simulations_count, status
                ) VALUES (?, ?, ?, ?, ?, 1, 'running')
                """,
                ("live_smoke_campaign", "Live Smoke Test Campaign", "Default FastExpr", "{}", 1)
            )

            # Ensure candidate exists
            cursor.execute(
                """
                INSERT OR IGNORE INTO candidates (
                    id, campaign_id, expression, normalized_hash, validation_status, queue_status, submission_id
                ) VALUES (?, ?, ?, ?, 'passed', 'completed', ?)
                """,
                ("live_test_candidate_1", "live_smoke_campaign", expression, "hash_" + sim_id, sim_id)
            )

            cursor.execute(
                """
                INSERT OR REPLACE INTO simulation_results (
                    id, candidate_id, campaign_id, is_mock, platform_status,
                    main_sharpe, fitness, turnover, counts_verified, raw_response
                ) VALUES (?, ?, ?, 0, ?, ?, ?, ?, 1, ?)
                """,
                (
                    sim_id,
                    "live_test_candidate_1",
                    "live_smoke_campaign",
                    terminal_status or "UNKNOWN",
                    float(alpha_details.get("is", {}).get("sharpe", 0.0)) if alpha_details else None,
                    float(alpha_details.get("is", {}).get("fitness", 0.0)) if alpha_details else None,
                    float(alpha_details.get("is", {}).get("turnover", 0.0)) if alpha_details else None,
                    json.dumps(alpha_details or sim_data or {})
                )
            )
            conn.commit()

        logger.info("Live simulation record successfully persisted to local SQLite database.")

    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(run_live_smoke_test())
