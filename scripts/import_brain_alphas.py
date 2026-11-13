#!/usr/bin/env python3
"""
Imports WorldQuant BRAIN exported alphas from alphas.json and alphas1.json
into Alpha Research Pilot's Reference Library and Database.
"""

import sys
import os
import json

# Ensure backend on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.db.connection import get_db
from app.db.migrations import run_migrations

def import_alphas():
    run_migrations()
    files = [
        "/Users/yusuftarwala/alphas1.json", # Active submitted alphas
        "/Users/yusuftarwala/alphas.json"   # Historical simulation runs
    ]

    total_imported = 0
    active_count = 0

    with get_db() as conn:
        cursor = conn.cursor()

        for fpath in files:
            if not os.path.exists(fpath):
                print(f"File not found: {fpath}")
                continue

            with open(fpath) as f:
                data = json.load(f)

            results = data.get("results", [])
            print(f"Processing {fpath}: {len(results)} records found.")

            for item in results:
                alpha_id = item.get("id")
                regular = item.get("regular") or {}
                code = regular.get("code")
                if not code or not alpha_id:
                    continue

                status = item.get("status", "UNSUBMITTED")
                submitted_date = item.get("dateSubmitted") or item.get("dateCreated")
                settings_dict = item.get("settings") or {}
                
                is_metrics = item.get("is") or {}
                sharpe = is_metrics.get("sharpe")
                fitness = is_metrics.get("fitness")
                turnover = is_metrics.get("turnover")
                category = item.get("category") or "Quantitative Alpha"
                name = item.get("name") or alpha_id

                desc = f"Sharpe: {sharpe}, Fitness: {fitness}, Turnover: {turnover}, Category: {category}, Name: {name}"

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO reference_library (
                        id, expression, signal_family, description, status, submitted_date, settings, raw_metadata, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        alpha_id,
                        code,
                        category,
                        desc,
                        status,
                        submitted_date,
                        json.dumps(settings_dict),
                        json.dumps({
                            "sharpe": sharpe,
                            "fitness": fitness,
                            "turnover": turnover,
                            "operatorCount": regular.get("operatorCount"),
                            "checks": is_metrics.get("checks", [])
                        })
                    )
                )
                total_imported += 1
                if status == "ACTIVE":
                    active_count += 1

        # Also flag existing self-correlation checks as STALE since reference library changed
        cursor.execute(
            """
            UPDATE correlation_records
            SET status = 'STALE / RECHECK REQUIRED',
                notes = 'Reference library updated with 60 real WorldQuant BRAIN alphas.'
            WHERE check_type = 'self_correlation'
            """
        )
        conn.commit()

    print(f"\nImport Completed Successfully:")
    print(f"  - Total Alphas Ingested: {total_imported}")
    print(f"  - Active Submitted Platform Alphas: {active_count}")

if __name__ == "__main__":
    import_alphas()
