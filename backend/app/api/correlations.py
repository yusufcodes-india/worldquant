import json
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_pairing_token, verify_host_header
from app.db.connection import get_db
from app.engine.correlation import CorrelationEngine
from app.models.schemas import LocalCorrelationRequest, LocalCorrelationResponse

router = APIRouter(prefix="/correlations", tags=["Correlations"], dependencies=[Depends(verify_host_header), Depends(verify_pairing_token)])

@router.post("/local_screen", response_model=LocalCorrelationResponse)
def calculate_local_pnl_correlation(req: LocalCorrelationRequest):
    """
    Computes aligned Pearson correlation between candidate and reference alpha PnL.
    Clearly labeled with mandatory disclaimer: LOCAL ESTIMATE — NOT THE PLATFORM SELF-CORRELATION CHECK.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Fetch candidate PnL
        cursor.execute("SELECT pnl_series FROM simulation_results WHERE candidate_id = ?", (req.candidate_id,))
        cand_row = cursor.fetchone()
        if not cand_row or not cand_row["pnl_series"]:
            raise HTTPException(status_code=400, detail="Candidate simulation PnL series not available.")
        cand_pnl = json.loads(cand_row["pnl_series"])

        # 2. Fetch reference alpha PnL
        cursor.execute("SELECT pnl_series FROM reference_library WHERE id = ?", (req.reference_alpha_id,))
        ref_row = cursor.fetchone()
        if not ref_row or not ref_row["pnl_series"]:
            # Check if reference is another candidate
            cursor.execute("SELECT pnl_series FROM simulation_results WHERE candidate_id = ?", (req.reference_alpha_id,))
            alt_row = cursor.fetchone()
            if not alt_row or not alt_row["pnl_series"]:
                raise HTTPException(status_code=400, detail="Reference PnL series not available.")
            ref_pnl = json.loads(alt_row["pnl_series"])
        else:
            ref_pnl = json.loads(ref_row["pnl_series"])

    res = CorrelationEngine.calculate_pnl_correlation(cand_pnl, ref_pnl)
    return LocalCorrelationResponse(
        candidate_id=req.candidate_id,
        reference_alpha_id=req.reference_alpha_id,
        signed_correlation=res["signed_correlation"],
        absolute_correlation=res["absolute_correlation"],
        overlap_period=res["overlap_period"],
        observation_count=res["observation_count"],
        disclaimer=res["disclaimer"],
        warnings=res["warnings"]
    )

@router.get("/pairwise_matrix")
def get_pairwise_matrix(campaign_id: str, limit: int = 10):
    """
    Calculates pairwise local correlation matrix among the top N simulated candidates in a campaign.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.id, c.expression, c.signal_family, r.pnl_series, r.main_sharpe
            FROM candidates c
            JOIN simulation_results r ON c.id = r.candidate_id
            WHERE c.campaign_id = ? AND r.pnl_series IS NOT NULL
            ORDER BY r.main_sharpe DESC LIMIT ?
            """,
            (campaign_id, limit)
        )
        cands = cursor.fetchall()

    items = []
    for c in cands:
        items.append({
            "id": c["id"],
            "expression": c["expression"][:40] + "...",
            "signal_family": c["signal_family"],
            "pnl": json.loads(c["pnl_series"])
        })

    matrix = []
    for i, a in enumerate(items):
        row = []
        for j, b in enumerate(items):
            if i == j:
                row.append(1.0)
            else:
                corr_res = CorrelationEngine.calculate_pnl_correlation(a["pnl"], b["pnl"])
                row.append(corr_res["signed_correlation"])
        matrix.append(row)

    return {
        "disclaimer": "LOCAL ESTIMATE — NOT THE PLATFORM SELF-CORRELATION CHECK.",
        "candidates": [{"id": c["id"], "family": c["signal_family"]} for c in items],
        "matrix": matrix
    }
