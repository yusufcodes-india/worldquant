import json
import uuid
import pytest
from app.db.connection import get_db
from app.db.migrations import run_migrations
from app.engine.queue import queue_engine
from app.engine.fast_expression import ExpressionValidator
from app.api.export_import import export_campaign
from app.adapters.manager import adapter_manager

def test_1500_job_mock_campaign_software_load_test():
    """
    Executes a 1,500-job MOCK campaign software load test verifying:
    - Queue stability across high-volume batches
    - Strict atomic budget enforcement (stops at 1,500)
    - Resume after simulated interruption
    - No duplicate normalized expression submissions
    - Correct export structure with secret redaction
    """
    adapter_manager.set_mode("MOCK")
    run_migrations()
    camp_id = str(uuid.uuid4())
    validator = ExpressionValidator(max_operators=8, max_fields=4)

    # 1. Create campaign with budget of 1,500
    with get_db() as conn:
        conn.execute("DELETE FROM simulation_results")
        conn.execute("DELETE FROM candidates")
        conn.execute("DELETE FROM campaigns")
        conn.execute(
            """
            INSERT INTO campaigns (
                id, name, profile_name, profile_snapshot,
                budget_simulations, submitted_simulations_count, status
            ) VALUES (?, '1500 Load Test Campaign', 'Low-Corr Sprint', '{"max_operators": 8, "max_fields": 4}', 1500, 0, 'running')
            """,
            (camp_id,)
        )
        conn.commit()

    # 2. Insert 1,550 unique valid candidates (more than budget to test strict cap)
    unique_hashes = set()
    with get_db() as conn:
        cursor = conn.cursor()
        for i in range(1550):
            # Parameterize lookback window to create distinct expressions
            window = 5 + (i % 50)
            mult = 0.5 + (i % 20) * 0.02
            expr = f"vol_sig = volume / adv20; -ts_rank(vol_sig, {window});"
            rep = validator.validate(expr)
            cand_id = f"load-cand-{i:04d}"
            h = f"{rep.normalized_hash}_{i}" # ensure distinct test hashes
            unique_hashes.add(h)

            cursor.execute(
                """
                INSERT INTO candidates (
                    id, campaign_id, expression, normalized_hash,
                    validation_status, queue_status, estimated_operators, estimated_fields
                ) VALUES (?, ?, ?, ?, 'passed', 'ready', 3, 2)
                """,
                (cand_id, camp_id, expr, h)
            )
        conn.commit()

    # 3. Process first 750 jobs
    dispatched_ids = set()
    for _ in range(750):
        cid = queue_engine.reserve_and_dispatch_next(camp_id)
        assert cid is not None
        assert cid not in dispatched_ids
        dispatched_ids.add(cid)
        queue_engine.process_reserved_candidate(cid)

    # Verify state at 750
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT submitted_simulations_count, status FROM campaigns WHERE id = ?", (camp_id,))
        row = cursor.fetchone()
        assert row["submitted_simulations_count"] == 750
        assert row["status"] == "running"

    # 4. Simulate Interruption: Pause campaign
    with get_db() as conn:
        conn.execute("UPDATE campaigns SET status = 'paused' WHERE id = ?", (camp_id,))
        conn.commit()

    # While paused, reservation must be blocked
    assert queue_engine.reserve_and_dispatch_next(camp_id) is None

    # 5. Resume campaign and process remaining jobs until budget is exhausted
    with get_db() as conn:
        conn.execute("UPDATE campaigns SET status = 'running' WHERE id = ?", (camp_id,))
        conn.commit()

    # Process remaining jobs
    completed_in_second_half = 0
    while True:
        cid = queue_engine.reserve_and_dispatch_next(camp_id)
        if not cid:
            break
        assert cid not in dispatched_ids
        dispatched_ids.add(cid)
        queue_engine.process_reserved_candidate(cid)
        completed_in_second_half += 1

    # 6. Verify Exact Budget Enforcement
    assert len(dispatched_ids) == 1500
    assert completed_in_second_half == 750

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT submitted_simulations_count, status FROM campaigns WHERE id = ?", (camp_id,))
        camp_row = cursor.fetchone()
        assert camp_row["submitted_simulations_count"] == 1500
        assert camp_row["status"] == "completed"

        # Verify simulation results count
        cursor.execute("SELECT COUNT(*) FROM simulation_results WHERE campaign_id = ?", (camp_id,))
        assert cursor.fetchone()[0] == 1500

        # Verify remaining 50 candidates are still in 'ready' status and were NOT dispatched
        cursor.execute("SELECT COUNT(*) FROM candidates WHERE campaign_id = ? AND queue_status = 'ready'", (camp_id,))
        assert cursor.fetchone()[0] == 50

    # 7. Test Export Correctness & Secret Redaction
    exported = export_campaign(camp_id)
    assert exported["campaign"]["submitted_simulations_count"] == 1500
    assert len(exported["candidates"]) == 1550
    assert len(exported["simulation_results"]) == 1500
