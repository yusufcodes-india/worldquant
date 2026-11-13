import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from app.db.connection import get_db
from app.engine.fast_expression import ExpressionValidator
from app.engine.queue import queue_engine
from app.gemini.client import gemini_client
from app.engine.correlation import CorrelationEngine

logger = logging.getLogger("alpha_pilot.research")

class ResearchLoopEngine:
    def __init__(self):
        pass

    def run_cycle(self, campaign_id: str) -> Dict[str, Any]:
        """
        Executes one step in the autonomous research loop:
        1. Check campaign state & budgets.
        2. Replenish candidate queue if needed via Gemini / mutation.
        3. Dispatch next reserved candidate to simulation.
        4. Check completion criteria.
        """
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
            camp = cursor.fetchone()
            if not camp:
                return {"status": "error", "message": f"Campaign {campaign_id} not found."}

            camp_status = camp["status"]
            if camp_status != "running":
                return {"status": "paused_or_stopped", "campaign_status": camp_status}

            budget_sims = camp["budget_simulations"]
            submitted_sims = camp["submitted_simulations_count"]
            if submitted_sims >= budget_sims:
                cursor.execute("UPDATE campaigns SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (campaign_id,))
                conn.commit()
                return {"status": "completed", "message": "Simulation submission budget exhausted."}

            profile_snapshot = json.loads(camp["profile_snapshot"])
            max_ops = profile_snapshot.get("max_operators", 8)
            max_fields = profile_snapshot.get("max_fields", 4)
            stop_on_first_qualifying = bool(camp["stop_on_first_qualifying"])

            # Check ready queue count
            cursor.execute("SELECT COUNT(*) FROM candidates WHERE campaign_id = ? AND queue_status = 'ready'", (campaign_id,))
            ready_count = cursor.fetchone()[0]

        # Replenish candidates if ready count is low
        if ready_count < 3:
            self._replenish_candidates(campaign_id, profile_snapshot)

        # Dispatch next ready candidate
        cand_id = queue_engine.reserve_and_dispatch_next(campaign_id)
        if cand_id:
            queue_engine.process_reserved_candidate(cand_id)
            
            # Check if this candidate is qualified
            if stop_on_first_qualifying:
                is_qual, reason = self.check_candidate_qualification(cand_id, profile_snapshot)
                if is_qual:
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE campaigns SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (campaign_id,))
                        conn.commit()
                    return {"status": "completed", "message": f"Found qualifying alpha: {cand_id}"}

            return {"status": "processed", "candidate_id": cand_id}

        return {"status": "idle", "message": "No candidates ready to dispatch."}

    def _replenish_candidates(self, campaign_id: str, profile_snapshot: Dict[str, Any]):
        validator = ExpressionValidator(
            max_operators=profile_snapshot.get("max_operators", 8),
            max_fields=profile_snapshot.get("max_fields", 4)
        )

        with get_db() as conn:
            cursor = conn.cursor()
            # Fetch existing hashes to prevent duplicates
            cursor.execute("SELECT normalized_hash FROM candidates WHERE campaign_id = ?", (campaign_id,))
            existing_hashes = {row["normalized_hash"] for row in cursor.fetchall()}

            # Fetch reference library
            cursor.execute("SELECT id, signal_family, description FROM reference_library LIMIT 10")
            refs = [dict(row) for row in cursor.fetchall()]

            # Fetch top performing candidate as parent seed if available
            cursor.execute(
                """
                SELECT c.id, c.expression, c.signal_family, r.main_sharpe, r.fitness 
                FROM candidates c
                JOIN simulation_results r ON c.id = r.candidate_id
                WHERE c.campaign_id = ? AND r.main_sharpe IS NOT NULL
                ORDER BY r.main_sharpe DESC LIMIT 1
                """,
                (campaign_id,)
            )
            top_parent = cursor.fetchone()
            parent_seed = dict(top_parent) if top_parent else None

        generated_payloads = gemini_client.generate_candidates(
            profile_rules=profile_snapshot,
            parent_seed=parent_seed,
            reference_alphas=refs,
            batch_size=5
        )

        with get_db() as conn:
            cursor = conn.cursor()
            for p in generated_payloads:
                report = validator.validate(p.expression)
                c_id = str(uuid.uuid4())
                
                # Check for duplicate
                if report.normalized_hash in existing_hashes:
                    continue
                existing_hashes.add(report.normalized_hash)

                if report.is_valid:
                    q_status = "ready"
                    v_status = "passed"
                else:
                    q_status = "validation_failed"
                    v_status = "failed"

                cursor.execute(
                    """
                    INSERT INTO candidates (
                        id, campaign_id, expression, normalized_hash,
                        hypothesis, signal_family, parent_candidate_id, design_change,
                        expected_risks, estimated_fields, estimated_operators,
                        validation_status, validation_errors, queue_status, retry_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        c_id,
                        campaign_id,
                        p.expression,
                        report.normalized_hash,
                        p.economic_hypothesis,
                        p.signal_family,
                        p.parent_experiment_id or (parent_seed.get("id") if parent_seed else None),
                        p.exact_changed_design_choice,
                        p.expected_risks,
                        report.estimated_fields,
                        report.estimated_operators,
                        v_status,
                        json.dumps(report.errors),
                        q_status
                    )
                )
            conn.commit()

    def check_candidate_qualification(self, candidate_id: str, profile_snapshot: Dict[str, Any]) -> Tuple[bool, str]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
            cand = cursor.fetchone()
            if not cand:
                return False, "Candidate not found"

            cursor.execute("SELECT * FROM simulation_results WHERE candidate_id = ?", (candidate_id,))
            sim_res = cursor.fetchone()
            sim_dict = dict(sim_res) if sim_res else None

            cursor.execute("SELECT * FROM correlation_records WHERE candidate_id = ? AND check_type = 'self_correlation'", (candidate_id,))
            corr_res = cursor.fetchone()
            corr_dict = dict(corr_res) if corr_res else None

            is_qual, reason, _ = CorrelationEngine.evaluate_readiness(
                profile_name=profile_snapshot.get("name", "Low-Corr Sprint"),
                validation_passed=(cand["validation_status"] == "passed"),
                operator_count=cand["estimated_operators"],
                field_count=cand["estimated_fields"],
                simulation_result=sim_dict,
                self_correlation_record=corr_dict,
                profile_rules=profile_snapshot
            )
            return is_qual, reason

research_engine = ResearchLoopEngine()
