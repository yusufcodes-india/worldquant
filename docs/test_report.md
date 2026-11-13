# Alpha Research Pilot: Automated Test Report

**Last Run**: 2026-11-13 12:56 IST  
**Platform**: macOS Darwin (Apple Silicon arm64)  
**Python**: 3.15.0  
**Pytest**: 9.2.0  

## Test Summary
```
============================== 36 passed in 6.72s ==============================
```

## Detailed Test Breakdown

| # | Test File | Test Name | Status | Verified Capability |
|---|-----------|-----------|--------|---------------------|
| 1 | `test_parser.py` | `test_valid_basic_expression` | **PASSED** | Lexer, parser, statement visitor, operator & field counting |
| 2 | `test_parser.py` | `test_defined_before_use_variable` | **PASSED** | Defined-before-use variable scoping |
| 3 | `test_parser.py` | `test_undefined_variable_or_unknown_field` | **PASSED** | Blocks unconfirmed fields & undefined symbols |
| 4 | `test_parser.py` | `test_forbidden_fields` | **PASSED** | Strictly blocks `scl15_sentiment` and `fam_est_eps_rank` |
| 5 | `test_parser.py` | `test_forbidden_operators` | **PASSED** | Strictly blocks `regression_neut` and `ts_max` |
| 6 | `test_parser.py` | `test_vector_field_reduction_requirement` | **PASSED** | Enforces `vec_avg(nws12_afterhsz_sl)` for vector fields |
| 7 | `test_parser.py` | `test_grouping_identifiers_tracked_separately` | **PASSED** | Separates grouping IDs (`subindustry`, `industry`) from data fields |
| 8 | `test_parser.py` | `test_duplicate_detection_normalized_hash` | **PASSED** | Whitespace-invariant AST normalization & SHA-256 hash matching |
| 9 | `test_unit_checker.py` | `test_reject_constant_added_to_dollar_turnover` | **PASSED** | Rejects `volume * close + 1` (currency + constant) |
| 10 | `test_unit_checker.py` | `test_reject_constant_added_to_fundamental_currency` | **PASSED** | Rejects `cashflow_op + 0.000001` (currency + constant) |
| 11 | `test_unit_checker.py` | `test_accept_price_range_denominator_pattern` | **PASSED** | Accepts `high - low + 0.001 * close` (price range denominator) |
| 12 | `test_unit_checker.py` | `test_accept_dimensionless_ratio_with_constant_offset` | **PASSED** | Accepts `(high - low) / close + 0.05` (dimensionless offset) |
| 13 | `test_profiles.py` | `test_sprint_mode_rejects_greater_than_8_operators` | **PASSED** | Rejects 13-operator seed alpha in Sprint mode |
| 14 | `test_profiles.py` | `test_account_mode_accepts_seed_alpha` | **PASSED** | Accepts 13-operator seed alpha in Account mode (limit 64) |
| 15 | `test_profiles.py` | `test_sprint_mode_rejects_greater_than_4_fields` | **PASSED** | Rejects expressions with 5 data fields in Sprint mode |
| 16 | `test_profiles.py` | `test_account_mode_rejects_greater_than_64_operators` | **PASSED** | Rejects expressions with > 64 operators in Account mode |
| 17 | `test_correlation.py` | `test_unchecked_correlation_blocks_readiness` | **PASSED** | Missing correlation check NEVER marks candidate as qualified |
| 18 | `test_correlation.py` | `test_stale_self_correlation_blocks_readiness` | **PASSED** | Stale correlation status blocks qualification |
| 19 | `test_correlation.py` | `test_local_estimate_cannot_replace_official_check` | **PASSED** | Local PnL estimate cannot satisfy official self-correlation requirement |
| 20 | `test_correlation.py` | `test_production_correlation_cannot_satisfy_self_correlation` | **PASSED** | Production correlation cannot substitute for self-correlation |
| 21 | `test_correlation.py` | `test_failed_subuniverse_blocks_qualification` | **PASSED** | Failing sub-universe cutoff blocks qualification despite Sharpe 2.10 |
| 22 | `test_correlation.py` | `test_fully_verified_qualifying_candidate` | **PASSED** | All baseline & self-corr checks pass = fully qualified |
| 23 | `test_queue_and_recovery.py` | `test_atomic_budget_enforcement` | **PASSED** | Atomic reservation stops exactly at campaign budget |
| 24 | `test_queue_and_recovery.py` | `test_pause_stops_dispatch_immediately` | **PASSED** | Pausing campaign halts queue reservations immediately |
| 25 | `test_queue_and_recovery.py` | `test_restart_recovery_of_in_flight_items` | **PASSED** | Crashed daemon recovery: no loss or duplicate dispatch |
| 26 | `test_gemini_and_security.py` | `test_secret_redaction_utility` | **PASSED** | Zero secret leakage across exports and logs |
| 27 | `test_gemini_and_security.py` | `test_host_header_dns_rebinding_defense` | **PASSED** | Host header validation against DNS rebinding |
| 28 | `test_gemini_and_security.py` | `test_pairing_token_authentication_enforcement` | **PASSED** | `X-Pilot-Token` enforcement on protected endpoints |
| 29 | `test_gemini_and_security.py` | `test_live_brain_adapter_safety_guards` | **PASSED** | Refuses live simulations without explicit session approval |
| 30 | `test_gemini_and_security.py` | `test_tab_observation_prompt_injection_sanitization` | **PASSED** | Strips prompt-injection directives from page content |
| 31 | `test_gemini_and_security.py` | `test_tab_observation_blocks_unauthorized_domains` | **PASSED** | Blocks non-whitelisted URLs in tab observation |
| 32 | `test_load_mock_campaign.py` | `test_1500_job_mock_campaign_software_load_test` | **PASSED** | Full 1,500-job load test: exact cap, pause/resume, no duplicates |
| 33 | `test_correlation_breaker.py` | `test_correlation_breaker_recipes_all_produce_valid_output` | **PASSED** | All 10 perturbation recipes produce parseable expressions |
| 34 | `test_correlation_breaker.py` | `test_correlation_breaker_recipes_produce_different_output` | **PASSED** | Each recipe produces a distinct mutation |
| 35 | `test_correlation_breaker.py` | `test_correlation_breaker_with_variable_prelude` | **PASSED** | Variable prelude wrapping works with breaker recipes |
| 36 | `test_correlation_breaker.py` | `test_correlation_breaker_preserves_original` | **PASSED** | Original expression is never mutated |

## Live Integration Verification (1 approved simulation)

| Metric | Value | Platform Check |
|--------|-------|----------------|
| Simulation ID | `2iC3WW4T64Lr8Ys5vSHuxfj` | — |
| Alpha ID | `gJapQ2xv` | — |
| Sharpe | -0.98 | FAIL (LOW_SHARPE) |
| Fitness | -0.56 | FAIL (LOW_FITNESS) |
| Turnover | 36.48% | PASS |
| Self-Correlation (max) | 0.2947 | PASS (< 0.70) |
| ALTCHA Auth | 39ms solve | PASS |
