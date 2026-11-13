import pytest
from app.engine.correlation_breaker import CorrelationBreaker, RECIPES, GROUPING_FIELDS
from app.engine.fast_expression import ExpressionValidator

def test_correlation_breaker_recipes_completeness():
    """Verify all 10 calibrated platform recipes exist and are configured."""
    assert len(RECIPES) == 10
    recipe_ids = {r.id for r in RECIPES}
    expected = {
        "resid_returns",
        "resid_size",
        "neut_momentum",
        "neut_size",
        "neut_both",
        "fast_innovation",
        "event_gate",
        "cluster_country",
        "cluster_zscore",
        "cluster_volatility",
    }
    assert recipe_ids == expected

def test_wrap_expression_variable_binding():
    """Verify clean variable binding prepending and setup statement chaining."""
    base = "rank(ts_delta(close, 5))"
    recipe = next(r for r in RECIPES if r.id == "fast_innovation")
    wrapped = CorrelationBreaker.wrap_expression(base, recipe)
    
    assert "alpha = rank(ts_delta(close, 5));" in wrapped
    assert "ts_av_diff(alpha, 20)" in wrapped

def test_wrapped_variants_validate_in_account_mode():
    """Verify that wrapped candidate variants validate under Account profile rules."""
    base = "rank(ts_delta(close, 5))"
    variants = CorrelationBreaker.generate_candidate_variants(base)
    assert len(variants) == 10
    
    validator = ExpressionValidator(max_operators=64, max_fields=10)
    for v in variants:
        code = v["expression"]
        report = validator.validate(code)
        assert report.is_valid, f"Recipe {v['recipe_id']} failed validation: {report.errors}"

def test_grouping_fields_recognized_in_breaker():
    """Verify platform grouping fields are accurately categorized."""
    assert "country" in GROUPING_FIELDS
    assert "sector" in GROUPING_FIELDS
    assert "industry" in GROUPING_FIELDS
    assert "subindustry" in GROUPING_FIELDS
    assert "market" in GROUPING_FIELDS
    assert "exchange" in GROUPING_FIELDS
    assert "currency" in GROUPING_FIELDS
