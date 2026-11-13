# Alpha Research Pilot

**Alpha Research Pilot** is a local-first, autonomous quantitative alpha research platform built for **WorldQuant BRAIN Fast Expression** formulation, static AST validation, durable simulation scheduling, and self-correlation control.

It pairs a **Manifest V3 browser extension** (compatible with **Opera GX** and **Chrome**) with a hardened **FastAPI / SQLite** local daemon.

---

## Key Features

- **AST Fast Expression Parser**: Recursive-descent validator enforcing ≤ 8 operators, ≤ 3 data fields (grouping fields exempt), statement scoping, and defined-before-use variables.
- **Autonomous Research Loop**: Generate → Validate → Simulate → Evaluate → Revise — runs unattended within a budget cap.
- **Durable Queue Engine**: SQLite WAL persistence, atomic 1,500-job budget reservation, `submission_uncertain` safeguards, and full crash recovery on restart.
- **Mandatory Self-Correlation Control**: Tracks status per-candidate (`NOT CHECKED`, `LOCAL ESTIMATE ONLY`, `PLATFORM VERIFIED PASS/FAIL`, `STALE / RECHECK REQUIRED`). Reference library changes automatically flag stale checks.
- **BRAIN Live Adapter**: ALTCHA challenge-response auth, `POST /simulations`, polling, official `self/prod` correlation endpoints. Final submission is always manual.
- **Gemini AI Integration**: `gemini-3.8-flash` via Interactions API for candidate generation with deterministic fallback when offline.
- **10 Correlation-Breaking Recipes**: Verified perturbation strategies with variable prelude wrapping.
- **Security**: Loopback only (`127.0.0.1`), DNS rebinding protection, 64-char `X-Pilot-Token` pairing, recursive secret redaction on all exports.

---

## Directory Structure

```
quant/
├── backend/
│   └── app/
│       ├── api/           # FastAPI routers (campaigns, candidates, correlations, settings, pairing, export/import, reference library)
│       ├── core/          # Config, security, pairing token
│       ├── db/            # SQLite connection (WAL mode), migrations (9 tables)
│       ├── engine/        # AST parser, queue engine, correlation checker/breaker, research loop
│       ├── adapters/      # MOCK, LIVE (BRAIN), MANUAL adapters + manager
│       ├── gemini/        # Google Gemini SDK client
│       ├── observation/   # Tab observer (feature-flagged)
│       └── main.py        # FastAPI entry point with lifespan hooks
├── extension/
│   ├── src/               # TypeScript React (popup, dashboard, background service worker)
│   ├── dist/              # Built unpacked extension
│   └── vite.config.ts     # Multi-page build config
├── tests/                 # 36 pytest tests (parser, queue, correlations, profiles, load test, Gemini, security)
├── scripts/               # run_backend.sh, run_tests.sh, build_extension.sh, live_smoke_test.py, dry_run_demo.py
├── docs/                  # architecture.md, security.md, capability_matrix.md, test_report.md, limitations_and_roadmap.md
├── data/                  # Gemini tuning datasets (JSON/JSONL)
└── .env.example           # Safe config template (no real secrets)
```

---

## Quick Start (macOS)

### Prerequisites
- Python 3.10+
- Node.js v18+ and npm
- Opera GX or Google Chrome

### 1. Clone and install

```bash
git clone https://github.com/yusufcodes-india/worldquant.git
cd worldquant

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Install alpha-harness (editable, for shared utilities)
pip install -e alpha-harness/backend
```

### 2. Configure environment

```bash
cp .env.example .env
chmod 600 .env
```

Edit `.env` and add your keys:
```env
BRAIN_USERNAME=your_email
BRAIN_PASSWORD=your_password
GEMINI_API_KEY=your_gemini_key       # optional — falls back to deterministic generation
INTEGRATION_MODE=MOCK                 # set to LIVE for real BRAIN integration
```

### 3. Build the browser extension

```bash
cd extension && npm install && npm run build && cd ..
```

### 4. Start the backend

```bash
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Or use the script:
```bash
./scripts/run_backend.sh
```

The daemon prints a pairing token on startup:
```
Secure Pairing Token: <64-character-hex>
```

### 5. Load the extension

**Opera GX**: `opera://extensions` → Developer mode → Load unpacked → select `extension/dist/`

**Chrome**: `chrome://extensions` → Developer mode → Load unpacked → select `extension/dist/`

Paste the pairing token when prompted.

---

## Running Tests

```bash
PYTHONPATH=backend .venv/bin/pytest tests/ -q
```

Expected: **36 passed** (~6s). Includes AST parser, queue state machine, 1,500-job load test, correlation breaker, Gemini integration, and security guard tests.

### End-to-end mock demo (2 autonomous cycles)

```bash
PYTHONPATH=backend .venv/bin/python tests/demonstrate_e2e_cycles.py
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness check (DB, adapter status) |
| `/docs` | GET | Interactive Swagger UI |
| `/settings` | GET | Full system status |
| `/settings/approve_live` | POST | Approve/revoke live simulation session |
| `/settings/live_approval` | GET | Check live approval status |
| `/settings/platform_simulation` | GET | Fetch BRAIN platform settings |
| `/campaigns` | GET/POST | List or create research campaigns |
| `/campaigns/{id}/step` | POST | Execute one research cycle |
| `/campaigns/{id}/run_batch` | POST | Run N cycles (1–50) |
| `/campaigns/{id}/stats` | GET | Detailed campaign statistics |
| `/candidates` | GET | List candidates for a campaign |
| `/correlations/self/{id}` | GET | Check self-correlation status |
| `/reference_library` | GET/POST | Manage reference alpha library |
| `/reference_library/sync_brain` | POST | Paginated sync of all BRAIN alphas |
| `/export` | GET | Export campaign data (secrets redacted) |
| `/import` | POST | Import campaign data |
| `/pairing/token` | POST | Generate new pairing token |

---

## Safety Guarantees

- **MOCK by default**: All simulations start against a deterministic mock platform. Mock data is never labeled as live.
- **Explicit approval required**: Live BRAIN simulations need `POST /settings/approve_live {"approve": true}`. Approval persists across restarts (stored in SQLite).
- **Final submission is ALWAYS manual**: The system never automates `POST /alphas/{id}/submit`.
- **Budget enforcement**: Atomic simulation budget checks before every dispatch. Hard cap: 1,500 jobs.
- **Zero telemetry**: No secrets in AI prompts, exports, or logs. Recursive redaction on all output.

---

## License

MIT
