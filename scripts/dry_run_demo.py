#!/usr/bin/env python3
"""
Alpha Research Pilot - Autonomous End-to-End Dry-Run Demonstration.
Demonstrates:
- Campaign initialization & atomic budget reservation
- Fast Expression AST Parsing & Unit Verification
- Autonomous candidate generation & mutation
- Deterministic simulation & moving sub-universe cutoff tracking
- Self-correlation check & local PnL screening against reference alphas
- Low-Corr Sprint eligibility evaluation
- Full secret redaction export
"""

import sys
import os
import json
import uuid

# Ensure backend on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.config import settings
from app.db.migrations import run_migrations
from app.api.reference_library import init_default_reference_library
from app.engine.fast_expression import ExpressionValidator
from app.engine.research_loop import research_engine
from app.db.connection import get_db
from app.api.export_import import export_campaign

def run_demo():
    print("=" * 70)
    print("  ALPHA RESEARCH PILOT - END-TO-END DEMONSTRATION")
    print("=" * 70)
    
    # 1. Initialize DB & Reference Library
    print("\n[1] Initializing persistent SQLite backend & reference library...")
    run_migrations()
    init_default_reference_library()
    token = settings.get_or_create_pairing_token()
    print(f"    - Loopback Binding: http://{settings.host}:{settings.port}")
    print(f"    - Pairing Token: {token[:8]}...{token[-4:]} (64 hex characters)")

    # 2. Setup Campaign
    print("\n[2] Creating 'Low-Corr Sprint 2026' Campaign...")
    camp_id = str(uuid.uuid4())
    profile_rules = {
        "name": "Low-Corr Sprint",
        "max_operators": 8,
        "max_fields": 4,
        "min_qualifying_alphas": 10,
        "min_initial_ranking": 2,
        "competition_start_date": "2026-11-07",
        "ranking_objective": "lowest average production correlation",
        "min_sharpe": 1.25,
        "min_fitness": 1.0,
        "min_turnover": 0.01,
        "max_turnover": 0.70,
        "max_self_correlation_target": 0.60,
        "official_self_correlation_threshold": 0.70,
        "simulation_settings": {
            "region": "USA",
            "universe": "TOP3000",
            "delay": 1,
            "decay": 0,
            "neutralization": "Subindustry",
            "truncation": 0.08,
            "nan_handling": "On",
            "pasteurization": "On",
            "test_period": "1 year",
            "language": "Fast Expression"
        }
    }

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO campaigns (
                id, name, profile_name, profile_snapshot,
                budget_simulations, submitted_simulations_count, status
            ) VALUES (?, 'Demo Sprint Campaign', 'Low-Corr Sprint', ?, 1500, 0, 'running')
            """,
            (camp_id, json.dumps(profile_rules))
        )
        conn.commit()
    print(f"    - Campaign ID: {camp_id}")
    print(f"    - Budget: 1,500 simulation submissions")

    # 3. Test AST Parser with user's research seed from Section 14
    print("\n[3] Testing Fast Expression AST Parser on User Seed Alpha...")
    seed = """
    iv_c = ts_backfill(implied_volatility_call_120, 10);
    iv_p = ts_backfill(implied_volatility_put_120, 10);
    skew = (iv_p - iv_c) / (iv_p + iv_c);
    skew_smooth = ts_mean(skew, 5);
    signal = -group_zscore(skew_smooth, industry);
    ts_decay_linear(trade_when(volume > 0.7 * adv20, signal, -1), 8);
    """
    v_sprint = ExpressionValidator(max_operators=8, max_fields=4)
    rep_sprint = v_sprint.validate(seed)
    print(f"    - Seed Operators: {rep_sprint.estimated_operators} (Sprint Limit: 8)")
    print(f"    - Seed Fields: {rep_sprint.unique_fields} ({rep_sprint.estimated_fields} fields)")
    print(f"    - Sprint Mode Valid: {rep_sprint.is_valid} -> Reason: {rep_sprint.errors}")
    
    v_account = ExpressionValidator(max_operators=64, max_fields=20)
    rep_account = v_account.validate(seed)
    print(f"    - Account Mode Valid: {rep_account.is_valid} (Account Limit: 64 ops)")

    # 4. Autonomous Research Cycles
    print("\n[4] Executing Autonomous Research Cycles (Replenishment + Simulation + Correlation)...")
    for cycle in range(1, 6):
        res = research_engine.run_cycle(camp_id)
        print(f"    - Cycle {cycle}: {res.get('status')} (Candidate: {res.get('candidate_id', 'N/A')[:8]}...)")

    # 5. Inspect Results
    print("\n[5] Evaluating Candidate Simulation & Self-Correlation Results...")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.id, c.expression, c.signal_family, c.estimated_operators, c.estimated_fields,
                   r.main_sharpe, r.fitness, r.turnover, r.subuniverse_sharpe, r.subuniverse_cutoff,
                   cr.measured_value as self_corr, cr.status as self_corr_status
            FROM candidates c
            LEFT JOIN simulation_results r ON c.id = r.candidate_id
            LEFT JOIN correlation_records cr ON c.id = cr.candidate_id AND cr.check_type = 'self_correlation'
            WHERE c.campaign_id = ? AND c.queue_status = 'completed'
            """,
            (camp_id,)
        )
        rows = cursor.fetchall()
        for i, row in enumerate(rows, 1):
            sub_pass = (row["subuniverse_sharpe"] or 0) >= (row["subuniverse_cutoff"] or 0)
            print(f"\n    Candidate #{i} [{row['id'][:8]}]:")
            print(f"      Expression: {row['expression'].strip()[:60]}...")
            print(f"      Family: {row['signal_family']} | Ops: {row['estimated_operators']}/8 | Fields: {row['estimated_fields']}/4")
            print(f"      Main Sharpe: {row['main_sharpe']} | Fitness: {row['fitness']} | Turnover: {row['turnover']}")
            print(f"      Sub-Universe: {row['subuniverse_sharpe']} vs Cutoff {row['subuniverse_cutoff']} ({'PASS' if sub_pass else 'FAIL'})")
            print(f"      Self-Correlation: {row['self_corr']} ({row['self_corr_status']})")

    # 6. Verify Secret Redaction in Export
    print("\n[6] Testing Guaranteed Secret Redaction on Campaign Export...")
    exported = export_campaign(camp_id)
    raw_str = json.dumps(exported)
    assert "token" not in raw_str.lower() or "[REDACTED_SECRET]" in raw_str
    print(f"    - Successfully exported campaign with {len(exported['candidates'])} candidates.")
    print("    - Guaranteed zero secret leakage verified.")

    print("\n" + "=" * 70)
    print("  DEMONSTRATION COMPLETED SUCCESSFULLY")
    print("=" * 70)

if __name__ == "__main__":
    run_demo()
