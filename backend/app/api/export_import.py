import json
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_pairing_token, verify_host_header, redact_secrets
from app.db.connection import get_db

router = APIRouter(prefix="/data", tags=["Data Export / Import"], dependencies=[Depends(verify_host_header), Depends(verify_pairing_token)])

@router.get("/export/{campaign_id}")
def export_campaign(campaign_id: str):
    """
    Exports a campaign with its candidates, simulation results, and correlation checks.
    Guarantees full secret redaction.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        camp = cursor.fetchone()
        if not camp:
            raise HTTPException(status_code=404, detail="Campaign not found")

        cursor.execute("SELECT * FROM candidates WHERE campaign_id = ?", (campaign_id,))
        cands = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT * FROM simulation_results WHERE campaign_id = ?", (campaign_id,))
        sims = [dict(r) for r in cursor.fetchall()]

        cand_ids = [c["id"] for c in cands]
        corrs = []
        if cand_ids:
            placeholders = ",".join("?" for _ in cand_ids)
            cursor.execute(f"SELECT * FROM correlation_records WHERE candidate_id IN ({placeholders})", cand_ids)
            corrs = [dict(r) for r in cursor.fetchall()]

    raw_payload = {
        "campaign": dict(camp),
        "candidates": cands,
        "simulation_results": sims,
        "correlations": corrs
    }

    # Redact any sensitive tokens, keys, passwords
    safe_export = redact_secrets(raw_payload)
    return safe_export

@router.post("/reset")
def reset_database():
    """Wipes campaign and candidate data for testing/reset."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM correlation_records")
        cursor.execute("DELETE FROM simulation_results")
        cursor.execute("DELETE FROM candidates")
        cursor.execute("DELETE FROM campaigns")
        conn.commit()
    return {"success": True, "message": "All campaigns and candidates safely reset."}
