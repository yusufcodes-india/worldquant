# Alpha Research Pilot: Automated Test Report

**Execution Date**: 2026-11-12
**Platform**: macOS Darwin (Apple Silicon arm64)
**Python**: 3.15.0
**Pytest**: 9.2.0

## Test Summary
```
============================== 32 passed in 5.74s ==============================
```

## Detailed Test Breakdown

| Test File | Test Name | Status | Verified Capability |
|---|---|---|---|
| `test_parser.py` | `test_valid_basic_expression` | **PASSED** | Lexer, parser, statement visitor, operator & field counting |
| `test_parser.py` | `test_defined_before_use_variable` | **PASSED** | Defined-before-use variable scoping |
| `test_parser.py` | `test_undefined_variable_or_unknown_field` | **PASSED** | Blocks unconfirmed fields & undefined symbols |
| `test_parser.py` | `test_forbidden_fields` | **PASSED** | Strictly blocks `scl15_sentiment` and `fam_est_eps_rank` |
| `test_parser.py` | `test_forbidden_operators` | **PASSED** | Strictly blocks `regression_neut` and `ts_max` |
| `test_parser.py` | `test_vector_field_reduction_requirement` | **PASSED** | Enforces `vec_avg(nws12_afterhsz_sl)` for vector fields |
| `test_parser.py` | `test_grouping_identifiers_tracked_separately` | **PASSED** | Separates grouping IDs (`subindustry`, `industry`) from data fields |
| `test_parser.py` | `test_duplicate_detection_normalized_hash` | **PASSED** | Whitespace-invariant AST normalization & SHA-256 hash matching |
| `test_unit_checker.py` | `test_reject_constant_added_to_dollar_turnover` | **PASSED** | Rejects `volume * close + 1` (currency + constant) |
| `test_unit_checker.py` | `test_reject_constant_added_to_fundamental_currency` | **PASSED** | Rejects `cashflow_op + 0.000001` (currency + constant) |
| `test_unit_checker.py` | `test_accept_price_range_denominator_pattern` | **PASSED** | Accepts `high - low + 0.001 * close` (price range denominator) |
| `test_unit_checker.py` | `test_accept_dimensionless_ratio_with_constant_offset`| **PASSED** | Accepts `(high - low) / close + 0.05` (dimensionless offset) |
| `test_profiles.py` | `test_sprint_mode_rejects_greater_than_8_operators` | **PASSED** | Rejects 13-operator seed alpha in Low-Corr Sprint mode |
| `test_profiles.py` | `test_account_mode_accepts_seed_alpha` | **PASSED** | Accepts 13-operator seed alpha in Account mode (limit 64) |
| `test_profiles.py` | `test_sprint_mode_rejects_greater_than_4_fields` | **PASSED** | Rejects expressions with 5 data fields in Sprint mode |
| `test_profiles.py` | `test_account_mode_rejects_greater_than_64_operators` | **PASSED** | Rejects expressions with > 64 operators in Account mode |
| `test_correlation.py` | `test_unchecked_correlation_blocks_readiness` | **PASSED** | Missing correlation check NEVER marks candidate as qualified |
| `test_correlation.py` | `test_stale_self_correlation_blocks_readiness` | **PASSED** | Stale correlation status blocks qualification |
| `test_correlation.py` | `test_local_estimate_cannot_replace_official_check` | **PASSED** | Local PnL estimate cannot satisfy official self-correlation requirement |
| `test_correlation.py` | `test_production_correlation_cannot_satisfy_self_correlation` | **PASSED** | Production correlation cannot substitute for self-correlation |
| `test_correlation.py` | `test_failed_subuniverse_blocks_qualification` | **PASSED** | Failing dynamic sub-universe cutoff blocks qualification despite Sharpe 2.10 |
| `test_correlation.py` | `test_fully_verified_qualifying_candidate` | **PASSED** | Validates fully qualified status when all baseline & self-corr checks pass |
| `test_queue_and_recovery.py` | `test_atomic_budget_enforcement` | **PASSED** | Atomic reservation stops exactly at campaign budget |
| `test_queue_and_recovery.py` | `test_pause_stops_dispatch_immediately` | **PASSED** | Pausing campaign halts queue reservations immediately |
| `test_queue_and_recovery.py` | `test_restart_recovery_of_in_flight_items` | **PASSED** | Crashed daemon restarts recover in-flight jobs without loss or duplicate dispatch |
| `test_gemini_and_security.py` | `test_secret_redaction_utility` | **PASSED** | Guaranteed zero secret leakage across exports and logs |
| `test_gemini_and_security.py` | `test_host_header_dns_rebinding_defense` | **PASSED** | Enforces Host header validation to guard against DNS rebinding |
| `test_gemini_and_security.py` | `test_pairing_token_authentication_enforcement` | **PASSED** | Enforces `X-Pilot-Token` pairing header on protected endpoints |
| `test_gemini_and_security.py` | `test_live_brain_adapter_safety_guards` | **PASSED** | Refuses live simulations without explicit user session confirmation |
| `test_gemini_and_security.py` | `test_tab_observation_prompt_injection_sanitization` | **PASSED** | Strips prompt-injection directives from extracted page content |
| `test_gemini_and_security.py` | `test_tab_observation_blocks_unauthorized_domains` | **PASSED** | Blocks non-whitelisted URLs in tab observation |
| `test_load_mock_campaign.py` | `test_1500_job_mock_campaign_software_load_test` | **PASSED** | Full 1,500-job software load test: queue stability, exact 1,500 cap, pause/resume, no duplicates |
