import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_pairing_token, verify_host_header
from app.db.connection import get_db
from app.models.schemas import ReferenceAlphaCreate, ReferenceAlphaResponse

logger = logging.getLogger("alpha_pilot.ref_lib")

router = APIRouter(prefix="/reference_library", tags=["Reference Library"], dependencies=[Depends(verify_host_header), Depends(verify_pairing_token)])

DEFAULT_SEEDS = [
    {
        "id": "S1",
        "expression": "to_cap = volume / cap; cf_change = ts_delta(cashflow_op / cap, 20); -rank(to_cap + cf_change - scl12_buzz);",
        "signal_family": "Turnover & Cashflow Quality",
        "description": "Turnover-to-cap attention, cashflow_op/cap change, negative buzz, and negative short-term price-range location.",
        "status": "USER_REPORTED",
        "submitted_date": "2026-10-15"
    },
    {
        "id": "S2",
        "expression": "candle = (close - open) / (high - low + 0.001 * close); -ts_rank(candle * (volume / adv20), 5);",
        "signal_family": "Intraday Candle Range",
        "description": "Volume-weighted intraday candle signal with a range tilt.",
        "status": "USER_REPORTED",
        "submitted_date": "2026-10-18"
    },
    {
        "id": "S3",
        "expression": "ev_yield = ebitda / enterprise_value; sa_imp = ts_delta(sales / assets, 60); rank(ev_yield + sa_imp);",
        "signal_family": "EV Yield & Asset Efficiency",
        "description": "EBITDA/enterprise-value, sales/assets improvement, and short-term close-location component.",
        "status": "USER_REPORTED",
        "submitted_date": "2026-10-22"
    },
    {
        "id": "S4",
        "expression": "on_ret = (open - ts_delay(close, 1)) / ts_delay(close, 1); -rank(on_ret);",
        "signal_family": "Overnight Reversal",
        "description": "Overnight momentum.",
        "status": "USER_REPORTED",
        "submitted_date": "2026-10-25"
    },
    {
        "id": "S5",
        "expression": "vp_corr = ts_corr(volume, close, 10); cf_acc = cashflow_op / assets; rank(cf_acc - vp_corr);",
        "signal_family": "Volume-Price & Accruals",
        "description": "Volume-price correlation, decayed reversal, and cashflow_op/assets quality.",
        "status": "USER_REPORTED",
        "submitted_date": "2026-10-29"
    },
    {
        "id": "S6",
        "expression": "op_yield = operating_income / cap; -ts_decay_linear(rank(op_yield) * rank(returns), 5);",
        "signal_family": "Operating Yield Quality",
        "description": "Operating_income/cap, quality, and decayed reversal.",
        "status": "USER_REPORTED",
        "submitted_date": "2026-11-02"
    },
    {
        "id": "S7",
        "expression": "ret2 = returns + ts_delay(returns, 1); vol20 = ts_std_dev(returns, 20); -rank(ret2 / vol20);",
        "signal_family": "Volatility Normalized Reversal",
        "description": "Two-day return reversal normalized by 20-day return volatility.",
        "status": "USER_REPORTED",
        "submitted_date": "2026-11-05"
    }
]

def init_default_reference_library():
    """Initializes S1 to S7 reference alphas if empty."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM reference_library")
        if cursor.fetchone()[0] == 0:
            for s in DEFAULT_SEEDS:
                # Generate synthetic PnL series for local correlation demo
                pnl = []
                base = sum(ord(c) for c in s["id"])
                for day in range(252):
                    base = (base * 1103515245 + 12345) & 0x7FFFFFFF
                    ret = ((base % 10000) / 5000.0 - 1.0) * 0.012 + 0.0005
                    pnl.append({"date": f"2026-{1 + (day // 22):02d}-{(day % 22) + 1:02d}", "pnl": round(ret, 6)})

                cursor.execute(
                    """
                    INSERT INTO reference_library (
                        id, expression, signal_family, description, status, submitted_date, settings, pnl_series
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        s["id"],
                        s["expression"],
                        s["signal_family"],
                        s["description"],
                        s["status"],
                        s["submitted_date"],
                        json.dumps({"region": "USA", "universe": "TOP3000"}),
                        json.dumps(pnl)
                    )
                )
            conn.commit()

@router.get("", response_model=List[ReferenceAlphaResponse])
def list_reference_alphas():
    init_default_reference_library()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reference_library ORDER BY id ASC")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append(
                ReferenceAlphaResponse(
                    id=r["id"],
                    expression=r["expression"],
                    signal_family=r["signal_family"],
                    description=r["description"],
                    status=r["status"],
                    submitted_date=r["submitted_date"],
                    settings=json.loads(r["settings"]) if r["settings"] else None,
                    pnl_series=json.loads(r["pnl_series"]) if r["pnl_series"] else None,
                    created_at=str(r["created_at"])
                )
            )
        return result

@router.post("", response_model=ReferenceAlphaResponse)
def add_reference_alpha(req: ReferenceAlphaCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO reference_library (
                id, expression, signal_family, description, status, submitted_date, settings, pnl_series, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                req.id,
                req.expression,
                req.signal_family,
                req.description,
                req.status,
                req.submitted_date,
                json.dumps(req.settings or {}),
                json.dumps(req.pnl_series or [])
            )
        )
        
        # Flag all existing self-correlation checks as STALE / RECHECK REQUIRED!
        cursor.execute(
            """
            UPDATE correlation_records
            SET status = 'STALE / RECHECK REQUIRED',
                notes = 'Reference library modified. Re-verification against updated reference set required.'
            WHERE check_type = 'self_correlation'
            """
        )
        conn.commit()

        cursor.execute("SELECT * FROM reference_library WHERE id = ?", (req.id,))
        r = cursor.fetchone()
        return ReferenceAlphaResponse(
            id=r["id"],
            expression=r["expression"],
            signal_family=r["signal_family"],
            description=r["description"],
            status=r["status"],
            submitted_date=r["submitted_date"],
            settings=json.loads(r["settings"]) if r["settings"] else None,
            pnl_series=json.loads(r["pnl_series"]) if r["pnl_series"] else None,
            created_at=str(r["created_at"])
        )

@router.post("/sync_brain")
def sync_brain_alphas(limit: int = 100):
    """
    Syncs user alphas from GET /users/{user_id}/alphas into the local reference library.
    """
    from app.adapters.manager import adapter_manager
    adapter = adapter_manager.get_adapter()
    if not hasattr(adapter, "fetch_user_alphas"):
        raise HTTPException(status_code=400, detail="Active adapter does not support live alpha sync.")

    data = adapter.fetch_user_alphas(limit=limit)
    alphas = data.get("results", [])
    count = 0
    with get_db() as conn:
        cursor = conn.cursor()
        for alpha in alphas:
            aid = alpha.get("id")
            reg = alpha.get("regular", {})
            code = reg.get("code") if isinstance(reg, dict) else str(reg)
            category = alpha.get("category")
            name = alpha.get("name")
            submitted = alpha.get("dateSubmitted")
            status = "SUBMITTED" if submitted else "PLATFORM_VERIFIED"
            cursor.execute(
                """
                INSERT OR REPLACE INTO reference_library (
                    id, expression, signal_family, description, status, submitted_date, settings, raw_metadata, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    aid,
                    code or "",
                    category,
                    name,
                    status,
                    submitted,
                    json.dumps(alpha.get("settings", {})),
                    json.dumps(alpha)
                )
            )
            count += 1
        conn.commit()

    return {"synced_count": count, "total_on_platform": data.get("count", count)}

