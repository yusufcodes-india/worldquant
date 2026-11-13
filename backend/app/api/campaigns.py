import json
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.security import verify_pairing_token, verify_host_header
from app.db.connection import get_db
from app.models.schemas import CampaignCreate, CampaignResponse
from app.engine.research_loop import research_engine

router = APIRouter(prefix="/campaigns", tags=["Campaigns"], dependencies=[Depends(verify_host_header), Depends(verify_pairing_token)])

@router.get("", response_model=List[CampaignResponse])
def list_campaigns():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append(
                CampaignResponse(
                    id=r["id"],
                    name=r["name"],
                    profile_name=r["profile_name"],
                    profile_snapshot=json.loads(r["profile_snapshot"]),
                    budget_simulations=r["budget_simulations"],
                    submitted_simulations_count=r["submitted_simulations_count"],
                    budget_gemini_calls=r["budget_gemini_calls"],
                    gemini_calls_count=r["gemini_calls_count"],
                    budget_tokens=r["budget_tokens"],
                    tokens_used_count=r["tokens_used_count"],
                    simulation_concurrency=r["simulation_concurrency"],
                    stop_on_first_qualifying=bool(r["stop_on_first_qualifying"]),
                    status=r["status"],
                    created_at=str(r["created_at"]),
                    updated_at=str(r["updated_at"])
                )
            )
        return result

@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(req: CampaignCreate):
    camp_id = str(uuid.uuid4())
    snapshot_json = req.profile.model_dump_json()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO campaigns (
                id, name, profile_name, profile_snapshot,
                budget_simulations, submitted_simulations_count,
                budget_gemini_calls, gemini_calls_count,
                budget_tokens, tokens_used_count,
                simulation_concurrency, stop_on_first_qualifying,
                status
            ) VALUES (?, ?, ?, ?, ?, 0, ?, 0, ?, 0, ?, ?, 'running')
            """,
            (
                camp_id,
                req.name,
                req.profile.name,
                snapshot_json,
                req.budget_simulations,
                req.budget_gemini_calls,
                req.budget_tokens,
                req.simulation_concurrency,
                1 if req.stop_on_first_qualifying else 0
            )
        )
        conn.commit()

        cursor.execute("SELECT * FROM campaigns WHERE id = ?", (camp_id,))
        r = cursor.fetchone()
        return CampaignResponse(
            id=r["id"],
            name=r["name"],
            profile_name=r["profile_name"],
            profile_snapshot=json.loads(r["profile_snapshot"]),
            budget_simulations=r["budget_simulations"],
            submitted_simulations_count=r["submitted_simulations_count"],
            budget_gemini_calls=r["budget_gemini_calls"],
            gemini_calls_count=r["gemini_calls_count"],
            budget_tokens=r["budget_tokens"],
            tokens_used_count=r["tokens_used_count"],
            simulation_concurrency=r["simulation_concurrency"],
            stop_on_first_qualifying=bool(r["stop_on_first_qualifying"]),
            status=r["status"],
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"])
        )

@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return CampaignResponse(
            id=r["id"],
            name=r["name"],
            profile_name=r["profile_name"],
            profile_snapshot=json.loads(r["profile_snapshot"]),
            budget_simulations=r["budget_simulations"],
            submitted_simulations_count=r["submitted_simulations_count"],
            budget_gemini_calls=r["budget_gemini_calls"],
            gemini_calls_count=r["gemini_calls_count"],
            budget_tokens=r["budget_tokens"],
            tokens_used_count=r["tokens_used_count"],
            simulation_concurrency=r["simulation_concurrency"],
            stop_on_first_qualifying=bool(r["stop_on_first_qualifying"]),
            status=r["status"],
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"])
        )

@router.post("/{campaign_id}/pause")
def pause_campaign(campaign_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE campaigns SET status = 'paused', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (campaign_id,))
        conn.commit()
    return {"success": True, "status": "paused"}

@router.post("/{campaign_id}/resume")
def resume_campaign(campaign_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE campaigns SET status = 'running', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (campaign_id,))
        conn.commit()
    return {"success": True, "status": "running"}

@router.post("/{campaign_id}/step")
def step_campaign(campaign_id: str):
    result = research_engine.run_cycle(campaign_id)
    return result

@router.post("/{campaign_id}/run_batch")
def run_batch_cycles(campaign_id: str, cycles: int = Query(5, ge=1, le=50)):
    results = []
    for _ in range(cycles):
        res = research_engine.run_cycle(campaign_id)
        results.append(res)
        if res.get("status") in ("completed", "paused_or_stopped"):
            break
    return {"cycles_requested": cycles, "cycles_executed": len(results), "last_result": results[-1] if results else {}}

@router.get("/{campaign_id}/stats")
def get_campaign_stats(campaign_id: str):
    """Detailed campaign statistics with candidate and qualification breakdowns."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, budget_simulations, submitted_simulations_count FROM campaigns WHERE id = ?", (campaign_id,))
        camp = cursor.fetchone()
        if not camp:
            raise HTTPException(status_code=404, detail="Campaign not found")

        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_candidates,
                SUM(CASE WHEN validation_status = 'passed' THEN 1 ELSE 0 END) as validation_passed,
                SUM(CASE WHEN validation_status = 'failed' THEN 1 ELSE 0 END) as validation_failed,
                SUM(CASE WHEN queue_status = 'ready' THEN 1 ELSE 0 END) as queue_ready,
                SUM(CASE WHEN queue_status = 'running' THEN 1 ELSE 0 END) as queue_running,
                SUM(CASE WHEN queue_status = 'completed' THEN 1 ELSE 0 END) as queue_completed,
                SUM(CASE WHEN queue_status = 'failed' THEN 1 ELSE 0 END) as queue_failed,
                SUM(CASE WHEN queue_status = 'submission_uncertain' THEN 1 ELSE 0 END) as queue_uncertain
            FROM candidates WHERE campaign_id = ?
            """,
            (campaign_id,)
        )
        cand_counts = dict(cursor.fetchone())

        cursor.execute(
            """
            SELECT COUNT(*) FROM simulation_results r
            JOIN correlation_records c ON r.candidate_id = c.candidate_id
            WHERE r.campaign_id = ? 
              AND r.main_sharpe >= 1.25 
              AND r.fitness >= 1.0 
              AND r.turnover >= 0.01 AND r.turnover <= 0.70
              AND r.subuniverse_sharpe >= r.subuniverse_cutoff
              AND c.check_type = 'self_correlation'
              AND c.status = 'PLATFORM_VERIFIED_PASS'
            """,
            (campaign_id,)
        )
        qualifying_count = cursor.fetchone()[0]

    return {
        "campaign_id": campaign_id,
        "status": camp["status"],
        "budget_simulations": camp["budget_simulations"],
        "submitted_simulations_count": camp["submitted_simulations_count"],
        "candidates": cand_counts,
        "fully_verified_qualifying_alphas": qualifying_count
    }
