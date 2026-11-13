# Alpha Research Pilot: Capability Matrix

This matrix distinguishes verified capabilities, unverified assumptions, and unsupported operations.

| Feature / Domain | Implementation Status | Integration Verification | Operational Notes |
|---|---|---|---|
| **Fast Expression AST Parser** | **Implemented & Tested** | Verified Local | Full recursive descent AST parsing, defined-before-use checking, operator counting, field counting. |
| **Unit Consistency Validator** | **Implemented & Tested** | Verified Local | Rejects constants added to currency/turnover (e.g. `volume*close+1`); allows price-range denominators (`high-low+0.001*close`). |
| **Profile Precedence (Account vs Sprint)** | **Implemented & Tested** | Verified Local | Enforces <= 8 ops & <= 4 fields for Low-Corr Sprint; <= 64 ops for Account profile. Strictest active profile takes precedence. |
| **Deterministic MOCK Platform Adapter** | **Implemented & Tested** | Verified Local | Deterministic metrics (Sharpe, fitness, turnover, moving cutoff, PnL series) keyed on expression hash. Clearly labeled MOCK everywhere. |
| **Durable SQLite Queue** | **Implemented & Tested** | Verified Local | 10-state state machine; crash recovery; atomic budget enforcement up to 1,500 simulations. |
| **1,500-Job Software Load Test** | **Implemented & Tested** | Verified Local | Automated test proving queue stability, exact 1,500 cap, zero duplicates, pause/resume interruption handling. |
| **Google Gemini Structured Output** | **Implemented & Tested** | Verified Local & SDK | Uses official `google-genai` Python SDK (`gemini-3.8-flash`) with Pydantic JSON schemas, backoff on 429 quota, and deterministic fallback. |
| **Reference Library (S1 - S7)** | **Implemented & Tested** | User-Reported Specs | Pre-loaded with user's S1-S7 alpha families. Library updates trigger `STALE / RECHECK REQUIRED` on candidate self-correlations. |
| **Local PnL Correlation Screener** | **Implemented & Tested** | Verified Local | Aligned date Pearson correlation. Explicitly labeled `LOCAL ESTIMATE — NOT THE PLATFORM SELF-CORRELATION CHECK`. |
| **Manifest V3 Browser Extension** | **Implemented & Tested** | Verified Chrome / Opera GX | Built unpacked extension (`extension/dist`) with popup controls and full standalone dashboard (`dashboard.html`). |
| **Pairing & Security Protection** | **Implemented & Tested** | Verified Local | Loopback-only binding (127.0.0.1), Host header DNS rebinding defense, 64-char pairing token, recursive secret redaction. |
| **Real WorldQuant BRAIN Simulation API** | **Implemented (Guarded Shell)** | **Unverified / Guarded** | Live network calls blocked by default. Requires valid credentials, explicit user session approval, and live smoke test. |
| **Programmatic Production Correlation API** | **Stubbed / Guarded** | **Unverified** | WorldQuant BRAIN does not publish a confirmed public API for real-time production correlation; manual import provided. |
| **Automated Final Alpha Submission** | **Unsupported by Design** | **Unsupported (Policy)** | Strictly disabled in autonomous engine. All final submissions require explicit manual user action to avoid accidental platform quota loss. |
| **Current-Tab Observation** | **Implemented behind Flag** | Optional Feature | Controlled by `FEATURE_FLAG_TAB_OBSERVATION` with domain allowlist and prompt-injection filtering. |
