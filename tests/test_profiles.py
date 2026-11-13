import pytest
from app.engine.fast_expression import ExpressionValidator

def test_sprint_mode_rejects_greater_than_8_operators():
    # Seed expression has 13 operators
    seed = """
    iv_c = ts_backfill(implied_volatility_call_120, 10);
    iv_p = ts_backfill(implied_volatility_put_120, 10);
    skew = (iv_p - iv_c) / (iv_p + iv_c);
    skew_smooth = ts_mean(skew, 5);
    signal = -group_zscore(skew_smooth, industry);
    ts_decay_linear(trade_when(volume > 0.7 * adv20, signal, -1), 8);
    """
    v_sprint = ExpressionValidator(max_operators=8, max_fields=4)
    rep = v_sprint.validate(seed)
    assert rep.is_valid is False
    assert rep.estimated_operators == 13
    assert any("Operator limit exceeded" in e for e in rep.errors)

def test_account_mode_accepts_seed_alpha():
    seed = """
    iv_c = ts_backfill(implied_volatility_call_120, 10);
    iv_p = ts_backfill(implied_volatility_put_120, 10);
    skew = (iv_p - iv_c) / (iv_p + iv_c);
    skew_smooth = ts_mean(skew, 5);
    signal = -group_zscore(skew_smooth, industry);
    ts_decay_linear(trade_when(volume > 0.7 * adv20, signal, -1), 8);
    """
    v_account = ExpressionValidator(max_operators=64, max_fields=20)
    rep = v_account.validate(seed)
    assert rep.is_valid is True
    assert rep.estimated_operators == 13

def test_sprint_mode_rejects_greater_than_4_fields():
    # 5 fields: open, high, low, close, volume
    code = "(close - open + high - low) / volume;"
    v_sprint = ExpressionValidator(max_operators=8, max_fields=4)
    rep = v_sprint.validate(code)
    assert rep.is_valid is False
    assert rep.estimated_fields == 5
    assert any("Field limit exceeded" in e for e in rep.errors)

def test_account_mode_rejects_greater_than_64_operators():
    # Chain of 65 additions
    code = " + ".join(["close"] * 66) + ";"
    v_account = ExpressionValidator(max_operators=64, max_fields=20)
    rep = v_account.validate(code)
    assert rep.is_valid is False
    assert rep.estimated_operators == 65
    assert any("Operator limit exceeded" in e for e in rep.errors)
