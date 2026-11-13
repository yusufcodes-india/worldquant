import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import verify_pairing_token, verify_host_header
from app.db.connection import get_db
from app.engine.fast_expression import ExpressionValidator
from app.engine.correlation import CorrelationEngine
from app.models.schemas import CandidateDetailResponse, ValidationResult, SimulationResultResponse, CorrelationRecordResponse

router = APIRouter(prefix="/candidates", tags=["Candidates"], dependencies=[Depends(verify_host_header), Depends(verify_pairing_token)])

@router.get("", response_model=List[CandidateDetailResponse])
def list_candidates(
    campaign_id: str,
    status: Optional[str] = None,
    validation_status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM candidates WHERE campaign_id = ?"
        params: List[Any] = [campaign_id]
        
        if status:
            query += " AND queue_status = ?"
            params.append(status)
        if validation_status:
            query += " AND validation_status = ?"
            params.append(validation_status)
            
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for r in rows:
            c_id = r["id"]
            # Fetch sim result
            cursor.execute("SELECT * FROM simulation_results WHERE candidate_id = ?", (c_id,))
            sim_row = cursor.fetchone()
            sim_resp = None
            if sim_row:
                sim_resp = SimulationResultResponse(
                    id=sim_row["id"],
                    candidate_id=sim_row["candidate_id"],
                    campaign_id=sim_row["campaign_id"],
                    is_mock=bool(sim_row["is_mock"]),
                    platform_status=sim_row["platform_status"],
                    main_sharpe=sim_row["main_sharpe"],
                    fitness=sim_row["fitness"],
                    turnover=sim_row["turnover"],
                    subuniverse_sharpe=sim_row["subuniverse_sharpe"],
                    subuniverse_cutoff=sim_row["subuniverse_cutoff"],
                    subuniverse_pass_margin=sim_row["subuniverse_pass_margin"],
                    weight_distribution_pass=bool(sim_row["weight_distribution_pass"]) if sim_row["weight_distribution_pass"] is not None else None,
                    platform_reported_field_count=sim_row["platform_reported_field_count"],
                    platform_reported_op_count=sim_row["platform_reported_op_count"],
                    counts_verified=bool(sim_row["counts_verified"]),
                    pnl_series=json.loads(sim_row["pnl_series"]) if sim_row["pnl_series"] else None,
                    created_at=str(sim_row["created_at"])
                )

            # Fetch correlations
            cursor.execute("SELECT * FROM correlation_records WHERE candidate_id = ?", (c_id,))
            corr_rows = cursor.fetchall()
            corr_resps = []
            self_corr = None
            for cr in corr_rows:
                crec = CorrelationRecordResponse(
                    id=cr["id"],
                    candidate_id=cr["candidate_id"],
                    check_type=cr["check_type"],
                    status=cr["status"],
                    measured_value=cr["measured_value"],
                    target_value=cr["target_value"],
                    official_threshold=cr["official_threshold"],
                    official_pass=bool(cr["official_pass"]) if cr["official_pass"] is not None else None,
                    comparison_alphas=json.loads(cr["comparison_alphas"]) if cr["comparison_alphas"] else None,
                    is_local_estimate=bool(cr["is_local_estimate"]),
                    provenance_source=cr["provenance_source"],
                    notes=cr["notes"],
                    checked_at=str(cr["checked_at"])
                )
                corr_resps.append(crec)
                if cr["check_type"] == "self_correlation":
                    self_corr = cr

            # Fetch campaign rules for readiness check
            cursor.execute("SELECT profile_snapshot FROM campaigns WHERE id = ?", (campaign_id,))
            camp_row = cursor.fetchone()
            p_rules = json.loads(camp_row["profile_snapshot"]) if camp_row else {}

            is_qual, readiness_summary, _ = CorrelationEngine.evaluate_readiness(
                profile_name=p_rules.get("name", "Low-Corr Sprint"),
                validation_passed=(r["validation_status"] == "passed"),
                operator_count=r["estimated_operators"],
                field_count=r["estimated_fields"],
                simulation_result=dict(sim_row) if sim_row else None,
                self_correlation_record=dict(self_corr) if self_corr else None,
                profile_rules=p_rules
            )

            is_sprint_eligible = (r["estimated_operators"] <= 8 and r["estimated_fields"] <= 4 and is_qual)

            results.append(
                CandidateDetailResponse(
                    id=r["id"],
                    campaign_id=r["campaign_id"],
                    expression=r["expression"],
                    normalized_hash=r["normalized_hash"],
                    hypothesis=r["hypothesis"],
                    signal_family=r["signal_family"],
                    parent_candidate_id=r["parent_candidate_id"],
                    design_change=r["design_change"],
                    expected_risks=r["expected_risks"],
                    estimated_fields=r["estimated_fields"],
                    estimated_operators=r["estimated_operators"],
                    validation_status=r["validation_status"],
                    validation_errors=json.loads(r["validation_errors"]) if r["validation_errors"] else [],
                    queue_status=r["queue_status"],
                    submission_id=r["submission_id"],
                    retry_count=r["retry_count"],
                    created_at=str(r["created_at"]),
                    updated_at=str(r["updated_at"]),
                    simulation_result=sim_resp,
                    correlations=corr_resps,
                    is_sprint_eligible=is_sprint_eligible,
                    readiness_summary=readiness_summary
                )
            )

        return results

@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate(candidate_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Candidate not found")
        # Reuse list logic for single item
        return list_candidates(campaign_id=r["campaign_id"], limit=1)[0]

@router.post("/validate", response_model=ValidationResult)
def validate_expression(payload: Dict[str, Any]):
    expr = payload.get("expression", "")
    max_ops = payload.get("max_operators", 8)
    max_fields = payload.get("max_fields", 4)
    validator = ExpressionValidator(max_operators=max_ops, max_fields=max_fields)
    rep = validator.validate(expr)
    return ValidationResult(
        is_valid=rep.is_valid,
        errors=rep.errors,
        unique_fields=rep.unique_fields,
        grouping_identifiers=rep.grouping_identifiers,
        named_functions=rep.named_functions,
        arithmetic_operators=rep.arithmetic_operators,
        estimated_operators=rep.estimated_operators,
        estimated_fields=rep.estimated_fields,
        unit_status=rep.unit_status,
        normalized_expression=rep.normalized_expression,
        normalized_hash=rep.normalized_hash
    )
