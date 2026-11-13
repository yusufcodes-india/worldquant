import json
import uuid
import pytest
from app.db.connection import get_db
from app.db.migrations import run_migrations
from app.engine.queue import queue_engine

@pytest.fixture(autouse=True)
def setup_db():
    run_migrations()
    with get_db() as conn:
        conn.execute("DELETE FROM candidates")
        conn.execute("DELETE FROM campaigns")
        conn.commit()

def test_atomic_budget_enforcement():
    camp_id = str(uuid.uuid4())
    # Create campaign with budget of 2 simulations
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO campaigns (
                id, name, profile_name, profile_snapshot,
                budget_simulations, submitted_simulations_count, status
            ) VALUES (?, 'Test Budget', 'Sprint', '{}', 2, 0, 'running')
            """,
            (camp_id,)
        )
        # Insert 3 ready candidates
        for i in range(3):
            conn.execute(
                """
                INSERT INTO candidates (
                    id, campaign_id, expression, normalized_hash,
                    validation_status, queue_status
                ) VALUES (?, ?, 'close;', ?, 'passed', 'ready')
                """,
                (f"cand-{i}", camp_id, f"hash-{i}")
            )
        conn.commit()

    # Reserve 1st candidate
    r1 = queue_engine.reserve_and_dispatch_next(camp_id)
    assert r1 == "cand-0"

    # Reserve 2nd candidate
    r2 = queue_engine.reserve_and_dispatch_next(camp_id)
    assert r2 == "cand-1"

    # Attempt 3rd reservation -> Budget is 2, so must be BLOCKED!
    r3 = queue_engine.reserve_and_dispatch_next(camp_id)
    assert r3 is None

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT submitted_simulations_count, status FROM campaigns WHERE id = ?", (camp_id,))
        row = c.fetchone()
        assert row["submitted_simulations_count"] == 2
        assert row["status"] == "completed"

def test_pause_stops_dispatch_immediately():
    camp_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO campaigns (
                id, name, profile_name, profile_snapshot,
                budget_simulations, submitted_simulations_count, status
            ) VALUES (?, 'Paused Camp', 'Sprint', '{}', 10, 0, 'paused')
            """,
            (camp_id,)
        )
        conn.execute(
            """
            INSERT INTO candidates (
                id, campaign_id, expression, normalized_hash,
                validation_status, queue_status
            ) VALUES ('c1', ?, 'close;', 'h1', 'passed', 'ready')
            """,
            (camp_id,)
        )
        conn.commit()

    # When paused, reservation must return None
    r = queue_engine.reserve_and_dispatch_next(camp_id)
    assert r is None

def test_restart_recovery_of_in_flight_items():
    camp_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO campaigns (id, name, profile_name, profile_snapshot, status)
            VALUES (?, 'Crash Recovery Camp', 'Sprint', '{}', 'running')
            """,
            (camp_id,)
        )
        # Candidate 1: in-flight with submission_id (crashed during network run)
        conn.execute(
            """
            INSERT INTO candidates (
                id, campaign_id, expression, normalized_hash,
                validation_status, queue_status, submission_id
            ) VALUES ('crash-cand-1', ?, 'close;', 'h-crash-1', 'passed', 'submitting', 'sub-12345')
            """,
            (camp_id,)
        )
        # Candidate 2: reserved before network call dispatched
        conn.execute(
            """
            INSERT INTO candidates (
                id, campaign_id, expression, normalized_hash,
                validation_status, queue_status
            ) VALUES ('crash-cand-2', ?, 'close;', 'h-crash-2', 'passed', 'reserved')
            """,
            (camp_id,)
        )
        conn.commit()

    # Simulate daemon crash recovery on startup
    queue_engine.recover_on_startup()

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT queue_status FROM candidates WHERE id = 'crash-cand-1'")
        # Must be recovered to submission_uncertain so it can be reconciled without duplicate dispatch
        assert c.fetchone()[0] == "submission_uncertain"

        c.execute("SELECT queue_status FROM candidates WHERE id = 'crash-cand-2'")
        # Must be restored to ready so it can be safely re-dispatched
        assert c.fetchone()[0] == "ready"
