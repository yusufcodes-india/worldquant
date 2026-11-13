# Alpha Research Pilot: Limitations & Future Roadmap

## 1. Current Limitations

1. **Uncalibrated Platform Operator Counting**:
   - Local AST counting computes `named_functions + arithmetic_and_comparison_operators`.
   - While conservative and aligned with standard compiler AST conventions, platform-side compiler variations (e.g. counting constant offsets or parenthesis nesting) may differ slightly until calibrated with live platform submission results.
   - For Low-Corr Sprint eligibility, alphas are conservatively held to <= 8 local operators until live feedback is received.
2. **Local PnL Correlation vs Platform Self-Correlation**:
   - The platform calculates self-correlation against an internal proprietary portfolio of submitted alphas across specific dates and weighting schemas.
   - Local date-aligned Pearson correlation provides diagnostic insight, but is explicitly marked `LOCAL ESTIMATE ONLY — NOT THE PLATFORM SELF-CORRELATION CHECK`.
3. **No Automated Live Bulk Campaign Without Platform Approval**:
   - In accordance with safety constraints, live bulk simulation campaigns and final alpha submissions are disabled to prevent quota exhaustion or account penalties.
4. **Offline Laptop State**:
   - The queue engine runs locally on the user's workstation. If the computer is closed, put to sleep, or powered off, campaign progression halts until the daemon is resumed.

## 2. Next Steps & Roadmap

- **Live Session Smoke Test**: Run a single user-approved live simulation on WorldQuant BRAIN to calibrate local AST operator counts against platform-reported metrics.
- **Custom Factor Exporter**: Support exporting shortlisted expressions directly into standard Python backtest harnesses or QuantConnect/Zipline formats.
- **Multi-Period Robustness Testing**: Run candidate alphas across multi-year out-of-sample slices (e.g. 2-year, 5-year) to detect regime fragility.
