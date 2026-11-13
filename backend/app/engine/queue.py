import json
import logging
import time
from typing import Any, Dict, List, Optional
from app.db.connection import get_db
from app.adapters.manager import adapter_manager

logger = logging.getLogger("alpha_pilot.queue")

class DurableQueueEngine:
    def __init__(self):
        pass

    def reserve_and_dispatch_next(self, campaign_id: str) -> Optional[str]:
        """
        Atomically reserves budget and advances candidate from 'ready' to 'reserved'.
        Enforces transactional concurrency so no duplicate submissions or budget overruns happen.
        """
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 1. Check campaign status
            cursor.execute("SELECT status, budget_simulations, submitted_simulations_count FROM campaigns WHERE id = ?", (campaign_id,))
            camp = cursor.fetchone()
            if not camp:
                return None
            
            status, budget_sims, submitted_sims = camp["status"], camp["budget_simulations"], camp["submitted_simulations_count"]
            if status != "running":
                # Paused, completed, or cancelled
                return None

            if submitted_sims >= budget_sims:
                # Budget exhausted
                cursor.execute("UPDATE campaigns SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (campaign_id,))
                return None

            # 2. Find next ready candidate in this campaign
            cursor.execute(
                "SELECT id, expression FROM candidates WHERE campaign_id = ? AND queue_status = 'ready' ORDER BY created_at ASC LIMIT 1",
                (campaign_id,)
            )
            candidate = cursor.fetchone()
            if not candidate:
                return None

            candidate_id = candidate["id"]

            # 3. Atomically increment submitted_simulations_count if below budget
            cursor.execute(
                """
                UPDATE campaigns
                SET submitted_simulations_count = submitted_simulations_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND submitted_simulations_count < budget_simulations AND status = 'running'
                """,
                (campaign_id,)
            )
            if cursor.rowcount == 0:
                # Race condition or budget filled
                return None

            # 4. Mark candidate as reserved
            cursor.execute(
                "UPDATE candidates SET queue_status = 'reserved', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (candidate_id,)
            )

            return candidate_id

    def process_reserved_candidate(self, candidate_id: str):
        """
        Dispatches simulation to adapter, updates status to 'running' or 'submission_uncertain',
        fetches result, and handles self-correlation.
        """
        adapter = adapter_manager.get_adapter()
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
            cand = cursor.fetchone()
            if not cand:
                return

            campaign_id = cand["campaign_id"]
            expression = cand["expression"]

            cursor.execute("SELECT profile_snapshot FROM campaigns WHERE id = ?", (campaign_id,))
            camp_row = cursor.fetchone()
            profile_snapshot = json.loads(camp_row["profile_snapshot"]) if camp_row else {}
            settings = profile_snapshot.get("simulation_settings", {})

            # Transition to submitting
            cursor.execute("UPDATE candidates SET queue_status = 'submitting', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (candidate_id,))
            conn.commit()

        # Call adapter
        try:
            submit_resp = adapter.submit_simulation(expression, settings, candidate_id)
            submission_id = submit_resp.get("submission_id")
            
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE candidates SET queue_status = 'running', submission_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (submission_id, candidate_id)
                )
                conn.commit()

            # In mock or fast mode, poll or fetch result immediately
            status_resp = adapter.query_simulation_status(submission_id)
            if status_resp.get("status") == "COMPLETED":
                sim_result = adapter.fetch_simulation_results(submission_id)
                self._record_simulation_result(candidate_id, campaign_id, sim_result)
                
                # Check self-correlation if supported
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM reference_library")
                    ref_ids = [row["id"] for row in cursor.fetchall()]
                
                corr_resp = adapter.check_self_correlation(candidate_id, expression, ref_ids)
                self._record_correlation(candidate_id, corr_resp)

                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE candidates SET queue_status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (candidate_id,))
                    conn.commit()

        except Exception as e:
            logger.error(f"Error submitting/processing simulation for {candidate_id}: {str(e)}")
            with get_db() as conn:
                cursor = conn.cursor()
                # Mark as submission_uncertain if network error during POST
                cursor.execute(
                    """
                    UPDATE candidates 
                    SET queue_status = 'submission_uncertain',
                        retry_history = json_insert(coalesce(retry_history, '[]'), '$[#]', ?),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (str(e), candidate_id)
                )
                conn.commit()

    def _record_simulation_result(self, candidate_id: str, campaign_id: str, result: Dict[str, Any]):
        import uuid
        res_id = str(uuid.uuid4())
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO simulation_results (
                    id, candidate_id, campaign_id, is_mock, platform_status,
                    main_sharpe, fitness, turnover, subuniverse_sharpe,
                    subuniverse_cutoff, subuniverse_pass_margin, weight_distribution_pass,
                    platform_reported_field_count, platform_reported_op_count, counts_verified,
                    raw_response, pnl_series
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    res_id,
                    candidate_id,
                    campaign_id,
                    1 if result.get("is_mock") else 0,
                    result.get("platform_status", "UNKNOWN"),
                    result.get("main_sharpe"),
                    result.get("fitness"),
                    result.get("turnover"),
                    result.get("subuniverse_sharpe"),
                    result.get("subuniverse_cutoff"),
                    result.get("subuniverse_pass_margin"),
                    1 if result.get("weight_distribution_pass") else 0,
                    result.get("platform_reported_field_count"),
                    result.get("platform_reported_op_count"),
                    1 if result.get("counts_verified") else 0,
                    json.dumps(result.get("raw_response", {})),
                    json.dumps(result.get("pnl_series", []))
                )
            )

    def _record_correlation(self, candidate_id: str, corr: Dict[str, Any]):
        import uuid
        c_id = str(uuid.uuid4())
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO correlation_records (
                    id, candidate_id, check_type, status, measured_value,
                    target_value, official_threshold, official_pass,
                    comparison_alphas, is_local_estimate, provenance_source, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c_id,
                    candidate_id,
                    corr.get("check_type", "self_correlation"),
                    corr.get("status", "NOT CHECKED"),
                    corr.get("measured_value"),
                    corr.get("target_value", 0.60),
                    corr.get("official_threshold", 0.70),
                    1 if corr.get("official_pass") else (0 if corr.get("official_pass") is False else None),
                    json.dumps(corr.get("comparison_alphas", [])),
                    1 if corr.get("is_local_estimate") else 0,
                    corr.get("provenance_source", "mock"),
                    corr.get("notes", "")
                )
            )

    def recover_on_startup(self):
        """
        Recovers in-flight queue items when the backend restarts.
        No items are lost; 'submitting' or 'reserved' are reconciled.
        """
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, submission_id, queue_status, expression FROM candidates WHERE queue_status IN ('submitting', 'reserved')")
            stuck_items = cursor.fetchall()
            
            for item in stuck_items:
                c_id = item["id"]
                sub_id = item["submission_id"]
                if sub_id:
                    cursor.execute("UPDATE candidates SET queue_status = 'submission_uncertain', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (c_id,))
                else:
                    cursor.execute("UPDATE candidates SET queue_status = 'ready', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (c_id,))
            conn.commit()

queue_engine = DurableQueueEngine()
