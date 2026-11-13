import math
from typing import Any, Dict, List, Optional, Tuple

class CorrelationEngine:
    @staticmethod
    def calculate_pnl_correlation(
        series_a: List[Dict[str, Any]], 
        series_b: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Computes aligned Pearson correlation between two daily PnL series.
        Strictly labeled: LOCAL ESTIMATE — NOT THE PLATFORM SELF-CORRELATION CHECK.
        """
        dict_a = {item["date"]: float(item["pnl"]) for item in series_a if "date" in item and "pnl" in item}
        dict_b = {item["date"]: float(item["pnl"]) for item in series_b if "date" in item and "pnl" in item}

        common_dates = sorted(list(set(dict_a.keys()) & set(dict_b.keys())))
        obs_count = len(common_dates)

        warnings = []
        if obs_count < 30:
            warnings.append(f"Low overlap period: only {obs_count} common trading days.")

        if obs_count < 5:
            return {
                "signed_correlation": 0.0,
                "absolute_correlation": 0.0,
                "overlap_period": f"{common_dates[0]} to {common_dates[-1]}" if common_dates else "None",
                "observation_count": obs_count,
                "disclaimer": "LOCAL ESTIMATE — NOT THE PLATFORM SELF-CORRELATION CHECK.",
                "warnings": warnings + ["Insufficient overlapping points to calculate correlation."]
            }

        vals_a = [dict_a[d] for d in common_dates]
        vals_b = [dict_b[d] for d in common_dates]

        mean_a = sum(vals_a) / obs_count
        mean_b = sum(vals_b) / obs_count

        var_a = sum((x - mean_a) ** 2 for x in vals_a)
        var_b = sum((y - mean_b) ** 2 for y in vals_b)

        if var_a <= 1e-12 or var_b <= 1e-12:
            return {
                "signed_correlation": 0.0,
                "absolute_correlation": 0.0,
                "overlap_period": f"{common_dates[0]} to {common_dates[-1]}",
                "observation_count": obs_count,
                "disclaimer": "LOCAL ESTIMATE — NOT THE PLATFORM SELF-CORRELATION CHECK.",
                "warnings": warnings + ["Zero variance in one or both PnL series."]
            }

        cov = sum((vals_a[i] - mean_a) * (vals_b[i] - mean_b) for i in range(obs_count))
        r = cov / math.sqrt(var_a * var_b)
        r = max(-1.0, min(1.0, r))

        return {
            "signed_correlation": round(r, 4),
            "absolute_correlation": round(abs(r), 4),
            "overlap_period": f"{common_dates[0]} to {common_dates[-1]}",
            "observation_count": obs_count,
            "disclaimer": "LOCAL ESTIMATE — NOT THE PLATFORM SELF-CORRELATION CHECK.",
            "warnings": warnings
        }

    @staticmethod
    def evaluate_readiness(
        profile_name: str,
        validation_passed: bool,
        operator_count: int,
        field_count: int,
        simulation_result: Optional[Dict[str, Any]],
        self_correlation_record: Optional[Dict[str, Any]],
        profile_rules: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Determines if a candidate is fully verified and ready for review/submission.
        Rules:
        - Never marks ready if self_correlation is NOT CHECKED, STALE, or FAILED.
        - Checks operator and field limits strictly based on active profile.
        - Checks performance metrics (Sharpe, fitness, turnover, sub-universe Sharpe vs moving cutoff).
        """
        checks_detail = {
            "validation": False,
            "complexity": False,
            "performance": False,
            "subuniverse": False,
            "self_correlation": False
        }

        if not validation_passed:
            return False, "Validation failed (syntax, unit, or forbidden terms)", checks_detail

        checks_detail["validation"] = True

        max_ops = profile_rules.get("max_operators", 8)
        max_flds = profile_rules.get("max_fields", 4)
        if operator_count > max_ops or field_count > max_flds:
            return False, f"Complexity constraints exceeded ({operator_count} ops > {max_ops} or {field_count} fields > {max_flds})", checks_detail

        checks_detail["complexity"] = True

        if not simulation_result:
            return False, "Simulation not run or incomplete", checks_detail

        min_sharpe = profile_rules.get("min_sharpe", 1.25)
        min_fitness = profile_rules.get("min_fitness", 1.0)
        min_to = profile_rules.get("min_turnover", 0.01)
        max_to = profile_rules.get("max_turnover", 0.70)

        main_sharpe = simulation_result.get("main_sharpe")
        fitness = simulation_result.get("fitness")
        turnover = simulation_result.get("turnover")
        sub_sharpe = simulation_result.get("subuniverse_sharpe")
        sub_cutoff = simulation_result.get("subuniverse_cutoff")

        if main_sharpe is None or main_sharpe < min_sharpe:
            return False, f"Main Sharpe ({main_sharpe}) below threshold ({min_sharpe})", checks_detail

        if fitness is None or fitness < min_fitness:
            return False, f"Fitness ({fitness}) below threshold ({min_fitness})", checks_detail

        if turnover is None or turnover < min_to or turnover > max_to:
            return False, f"Turnover ({turnover}) outside required bounds ({min_to} to {max_to})", checks_detail

        checks_detail["performance"] = True

        # Sub-universe check
        if sub_sharpe is None or sub_cutoff is None or sub_sharpe < sub_cutoff:
            return False, f"Sub-universe Sharpe ({sub_sharpe}) failed moving cutoff ({sub_cutoff})", checks_detail

        checks_detail["subuniverse"] = True

        # Self-correlation check
        if not self_correlation_record:
            return False, "Self-correlation NOT CHECKED", checks_detail

        status = self_correlation_record.get("status")
        norm_status = status.replace("_", " ") if status else ""
        if norm_status in ("NOT CHECKED", "CHECK IN PROGRESS", "CHECK UNAVAILABLE"):
            return False, f"Self-correlation incomplete: {status}", checks_detail

        if norm_status == "STALE / RECHECK REQUIRED":
            return False, "Self-correlation check is STALE (reference library changed)", checks_detail

        if norm_status == "LOCAL ESTIMATE ONLY":
            return False, "Local PnL estimate cannot replace official platform self-correlation check", checks_detail

        if norm_status == "PLATFORM VERIFIED FAIL":
            return False, "Failed official platform self-correlation check", checks_detail

        if norm_status not in ("PLATFORM VERIFIED PASS", "MANUALLY REPORTED"):
            return False, f"Invalid self-correlation status: {status}", checks_detail

        # Check research target (< 0.6 preference if configured)
        measured_val = self_correlation_record.get("measured_value")
        target_val = profile_rules.get("max_self_correlation_target", 0.60)
        if measured_val is not None and measured_val > target_val:
            # Passes platform official 0.7, but note warning for research preference
            pass

        checks_detail["self_correlation"] = True
        return True, "QUALIFIED_READY_FOR_REVIEW", checks_detail
