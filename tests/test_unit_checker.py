import pytest
from app.engine.fast_expression import ExpressionValidator

def test_reject_constant_added_to_dollar_turnover():
    # volume * close is dollar turnover. + 1 is invalid!
    code = "volume * close + 1;"
    v = ExpressionValidator(max_operators=64, max_fields=20)
    rep = v.validate(code)
    assert rep.is_valid is False
    assert rep.unit_status == "REJECTED"
    assert any("Constant offset cannot be added directly to unit-bearing term" in e for e in rep.errors)

def test_reject_constant_added_to_fundamental_currency():
    # cashflow_op is currency. + 0.000001 is invalid!
    code = "cashflow_op + 0.000001;"
    v = ExpressionValidator(max_operators=64, max_fields=20)
    rep = v.validate(code)
    assert rep.is_valid is False
    assert rep.unit_status == "REJECTED"
    assert any("Constant offset cannot be added directly to unit-bearing term" in e for e in rep.errors)

def test_accept_price_range_denominator_pattern():
    # User's price-range denominator pattern: high - low + 0.001 * close
    code = "denom = high - low + 0.001 * close; (close - open) / denom;"
    v = ExpressionValidator(max_operators=64, max_fields=20)
    rep = v.validate(code)
    assert rep.is_valid is True
    assert rep.unit_status == "VERIFIED_PASS"

def test_accept_dimensionless_ratio_with_constant_offset():
    # (high - low) / close is dimensionless. Adding constant offset is allowed.
    code = "ratio = (high - low) / close; ratio + 0.05;"
    v = ExpressionValidator(max_operators=64, max_fields=20)
    rep = v.validate(code)
    assert rep.is_valid is True
    assert rep.unit_status == "VERIFIED_PASS"
