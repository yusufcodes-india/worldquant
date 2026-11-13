import pytest
from app.engine.correlation import CorrelationEngine

@pytest.fixture
def base_rules():
    return {
        "name": "Low-Corr Sprint",
        "max_operators": 8,
        "max_fields": 4,
        "min_sharpe": 1.25,
        "min_fitness": 1.0,
        "min_turnover": 0.01,
        "max_turnover": 0.70,
        "max_self_correlation_target": 0.60
    }

@pytest.fixture
def passing_sim_result():
    return {
        "main_sharpe": 1.85,
        "fitness": 1.45,
        "turnover": 0.15,
        "subuniverse_sharpe": 0.82,
        "subuniverse_cutoff": 0.75,
        "subuniverse_pass_margin": 0.07,
        "weight_distribution_pass": True
    }

def test_unchecked_correlation_blocks_readiness(base_rules, passing_sim_result):
    # Missing self_correlation record
    is_qual, reason, _ = CorrelationEngine.evaluate_readiness(
        profile_name="Low-Corr Sprint",
        validation_passed=True,
        operator_count=5,
        field_count=2,
        simulation_result=passing_sim_result,
        self_correlation_record=None, # NOT CHECKED
        profile_rules=base_rules
    )
    assert is_qual is False
    assert "Self-correlation NOT CHECKED" in reason

def test_stale_self_correlation_blocks_readiness(base_rules, passing_sim_result):
    stale_record = {
        "check_type": "self_correlation",
        "status": "STALE / RECHECK REQUIRED",
        "measured_value": 0.45
    }
    is_qual, reason, _ = CorrelationEngine.evaluate_readiness(
        profile_name="Low-Corr Sprint",
        validation_passed=True,
        operator_count=5,
        field_count=2,
        simulation_result=passing_sim_result,
        self_correlation_record=stale_record,
        profile_rules=base_rules
    )
    assert is_qual is False
    assert "STALE" in reason

def test_local_estimate_cannot_replace_official_check(base_rules, passing_sim_result):
    local_record = {
        "check_type": "self_correlation",
        "status": "LOCAL ESTIMATE ONLY",
        "measured_value": 0.35,
        "is_local_estimate": True
    }
    is_qual, reason, _ = CorrelationEngine.evaluate_readiness(
        profile_name="Low-Corr Sprint",
        validation_passed=True,
        operator_count=5,
        field_count=2,
        simulation_result=passing_sim_result,
        self_correlation_record=local_record,
        profile_rules=base_rules
    )
    assert is_qual is False
    assert "Local PnL estimate cannot replace official platform self-correlation check" in reason

def test_production_correlation_cannot_satisfy_self_correlation(base_rules, passing_sim_result):
    # Wrong check type passed
    prod_record = {
        "check_type": "production_correlation",
        "status": "PLATFORM_VERIFIED_PASS",
        "measured_value": 0.20
    }
    # When evaluated without a self-correlation record:
    is_qual, reason, _ = CorrelationEngine.evaluate_readiness(
        profile_name="Low-Corr Sprint",
        validation_passed=True,
        operator_count=5,
        field_count=2,
        simulation_result=passing_sim_result,
        self_correlation_record=None,
        profile_rules=base_rules
    )
    assert is_qual is False
    assert "Self-correlation NOT CHECKED" in reason

def test_failed_subuniverse_blocks_qualification(base_rules):
    # Main Sharpe is 2.10 (very high), but subuniverse Sharpe fails cutoff
    failing_subuniv_result = {
        "main_sharpe": 2.10,
        "fitness": 1.70,
        "turnover": 0.12,
        "subuniverse_sharpe": 0.65,
        "subuniverse_cutoff": 0.85, # Failed!
        "subuniverse_pass_margin": -0.20
    }
    valid_corr = {
        "check_type": "self_correlation",
        "status": "PLATFORM_VERIFIED_PASS",
        "measured_value": 0.50
    }
    is_qual, reason, _ = CorrelationEngine.evaluate_readiness(
        profile_name="Low-Corr Sprint",
        validation_passed=True,
        operator_count=5,
        field_count=2,
        simulation_result=failing_subuniv_result,
        self_correlation_record=valid_corr,
        profile_rules=base_rules
    )
    assert is_qual is False
    assert "Sub-universe Sharpe" in reason and "failed moving cutoff" in reason

def test_fully_verified_qualifying_candidate(base_rules, passing_sim_result):
    valid_corr = {
        "check_type": "self_correlation",
        "status": "PLATFORM_VERIFIED_PASS",
        "measured_value": 0.55
    }
    is_qual, reason, checks = CorrelationEngine.evaluate_readiness(
        profile_name="Low-Corr Sprint",
        validation_passed=True,
        operator_count=5,
        field_count=2,
        simulation_result=passing_sim_result,
        self_correlation_record=valid_corr,
        profile_rules=base_rules
    )
    assert is_qual is True
    assert reason == "QUALIFIED_READY_FOR_REVIEW"
    assert all(checks.values())
