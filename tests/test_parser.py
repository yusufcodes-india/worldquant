import pytest
from app.engine.fast_expression import ExpressionValidator

def test_valid_basic_expression():
    code = "ret = ts_delta(close, 5); -rank(ret);"
    v = ExpressionValidator(max_operators=8, max_fields=4)
    rep = v.validate(code)
    assert rep.is_valid is True
    assert rep.unique_fields == ["close"]
    assert rep.estimated_fields == 1
    assert rep.estimated_operators == 3 # ts_delta, rank, unary -

def test_defined_before_use_variable():
    # 'signal' used before defined
    code = "ret = close + signal; signal = 1; ret;"
    v = ExpressionValidator()
    rep = v.validate(code)
    assert rep.is_valid is False
    assert any("Undefined variable" in e for e in rep.errors)

def test_undefined_variable_or_unknown_field():
    code = "rank(unknown_field_123);"
    v = ExpressionValidator()
    rep = v.validate(code)
    assert rep.is_valid is False
    assert any("unconfirmed field: 'unknown_field_123'" in e for e in rep.errors)

def test_forbidden_fields():
    code1 = "rank(scl15_sentiment);"
    code2 = "rank(fam_est_eps_rank);"
    v = ExpressionValidator()
    assert v.validate(code1).is_valid is False
    assert v.validate(code2).is_valid is False

def test_forbidden_operators():
    code1 = "regression_neut(close, open);"
    code2 = "ts_max(close, 10);"
    v = ExpressionValidator()
    assert v.validate(code1).is_valid is False
    assert v.validate(code2).is_valid is False

def test_vector_field_reduction_requirement():
    v = ExpressionValidator()
    # Raw vector field without vec_avg -> must fail
    rep_raw = v.validate("nws12_afterhsz_sl > 0;")
    assert rep_raw.is_valid is False
    assert any("requires vector reduction" in e for e in rep_raw.errors)

    # With vec_avg -> must pass
    rep_reduced = v.validate("vec_avg(nws12_afterhsz_sl) > 0;")
    assert rep_reduced.is_valid is True

def test_grouping_identifiers_tracked_separately():
    code = "group_zscore(close, subindustry);"
    v = ExpressionValidator()
    rep = v.validate(code)
    assert rep.is_valid is True
    assert rep.unique_fields == ["close"] # subindustry is not counted in unique_fields!
    assert rep.grouping_identifiers == ["subindustry"]

def test_duplicate_detection_normalized_hash():
    code1 = "ret  =  ts_delta(close, 5);  -rank(ret);"
    code2 = "ret = ts_delta(close, 5);\n-rank(ret);"
    v = ExpressionValidator()
    rep1 = v.validate(code1)
    rep2 = v.validate(code2)
    assert rep1.normalized_hash == rep2.normalized_hash
