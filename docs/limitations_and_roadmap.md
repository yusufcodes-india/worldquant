# Alpha Research Pilot: Limitations & Future Roadmap

## 1. Current Limitations

1. **Uncalibrated Platform Operator Counting**:
   - Local AST counting computes `named_functions + arithmetic_and_comparison_operators`.
   - Platform-side compiler variations may differ slightly. Alphas are conservatively held to ≤ 8 operators until more live calibration data is collected.
   - 1 live simulation has been run; operator count matched platform's report.

2. **Local PnL Correlation vs Platform Self-Correlation**:
   - The platform calculates self-correlation against an internal proprietary portfolio.
   - Local date-aligned Pearson correlation is strictly labeled `LOCAL ESTIMATE ONLY — NOT THE PLATFORM SELF-CORRELATION CHECK`.
   - Official self-correlation endpoint (`GET /alphas/{id}/correlations/self`) is integrated and confirmed working.

3. **No Automated Final Submission**:
   - Final alpha submission (`POST /alphas/{id}/submit`) is never automated — always requires manual action on the BRAIN platform.

4. **Offline Laptop State**:
   - The queue engine runs locally. If the computer sleeps or powers off, campaigns halt until the daemon restarts. In-flight jobs recover automatically on restart.

5. **Gemini Availability**:
   - `gemini-3.8-flash` via Interactions API works but can return 503 under load. Automatic fallback to deterministic generation ensures campaigns never stall.

## 2. Completed Milestones

- ✅ Live ALTCHA authentication (14–63ms solve times)
- ✅ 1 approved live simulation executed and results persisted
- ✅ Official self-correlation endpoint verified (max=0.2947, PASS)
- ✅ 529 BRAIN portfolio alphas synced to local reference library
- ✅ Paginated sync endpoint for full portfolio import
- ✅ Live-session approval persists across restarts (SQLite `app_config`)
- ✅ 36/36 automated tests passing
- ✅ 2-cycle autonomous mock research loop demonstrated end-to-end
- ✅ Rich `/health` endpoint with DB + adapter status

## 3. Future Roadmap

- **Multi-Period Robustness Testing**: Run candidates across multi-year out-of-sample slices (2-year, 5-year) to detect regime fragility.
- **Custom Factor Exporter**: Export shortlisted expressions to Python backtest harnesses or QuantConnect/Zipline formats.
- **Parallel Simulation Dispatch**: Support `simulation_concurrency > 1` for faster campaign throughput (pending BRAIN rate limit characterization).
- **Extension Dashboard Enhancements**: Real-time campaign progress charts, correlation heatmaps, and candidate genealogy trees.
- **Gemini Fine-Tuning**: Use curated `data/gemini_tuning_dataset.jsonl` to fine-tune candidate generation quality.
