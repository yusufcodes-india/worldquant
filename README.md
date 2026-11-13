# Alpha Research Pilot

**Alpha Research Pilot** is a local-first, autonomous quantitative alpha research platform built specifically for **WorldQuant BRAIN Fast Expression** formulation, static AST validation, durable simulation scheduling, and self-correlation control.

It pairs a **Manifest V3 browser extension** (and full-page dashboard compatible with **macOS Opera GX** and **Google Chrome**) with a hardened, persistent local **FastAPI / SQLite** daemon.

---

## 1. Key Features

- **AST Fast Expression Parser & Unit Validator**: Recursive-descent compiler front-end enforcing statement scoping, defined-before-use variables, field/operator allowlists, vector reduction rules (e.g. `vec_avg(nws12_afterhsz_sl)`), and unit consistency (rejecting constant offsets on dollar/volume terms such as `volume * close + 1`).
- **Low-Corr Sprint & Account Rule Profiles**: Enforces strict constraints (Low-Corr Sprint: &le; 8 operators, &le; 4 data fields, Sharpe &ge; 1.25, Self-Corr &lt; 0.70; Account: &le; 64 operators). Strictest active profile takes precedence.
- **Mandatory Self-Correlation Control**:
  - Pre-seeded with user reference library (S1 to S7).
  - Explicit tracking: `NOT CHECKED`, `LOCAL ESTIMATE ONLY`, `PLATFORM VERIFIED PASS`, `PLATFORM VERIFIED FAIL`, `STALE / RECHECK REQUIRED`.
  - Reference library updates flag affected candidate checks as `STALE / RECHECK REQUIRED`.
  - Missing checks are **NEVER** marked as `PASS`.
- **Durable Queue State Machine**:
  - SQLite WAL persistence: Survives browser popup closure and backend process restarts.
  - Atomic simulation budget reservation (up to 1,500 simulation slots enforced transactionally before dispatch).
  - Ambiguous network outcomes transition to `submission_uncertain` to prevent duplicate submissions.
- **Official Google Gemini Integration**: Uses `google-genai` Python SDK (`gemini-3.8-flash`) with structured JSON outputs and automated fallback to deterministic candidate generation when offline or unconfigured.
- **Security & Sandbox Isolation**: Loopback only (`127.0.0.1`), DNS rebinding protection via `HostHeaderMiddleware`, 64-character pairing tokens (`X-Pilot-Token`), and guaranteed recursive secret redaction on all exports and logs.

---

## 2. Directory Structure

```
quant/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (campaigns, candidates, pairing, correlations, etc.)
│   │   ├── core/         # Config, security, pairing token, redaction
│   │   ├── db/           # SQLite connection, WAL mode, migrations
│   │   ├── engine/       # AST parser, unit checker, queue engine, research loop
│   │   ├── adapters/     # MOCK adapter, guarded LIVE adapter, MANUAL import adapter
│   │   ├── gemini/       # Google Gemini SDK structured output client
│   │   ├── observation/  # Guarded current-tab observation service (behind feature flag)
│   │   └── main.py       # FastAPI daemon entry point
│   ├── requirements.txt  # Pinned backend dependencies
│   └── requirements.lock # Dependency lockfile
├── extension/
│   ├── src/              # TypeScript React source (Popup, Full Dashboard, Background MV3)
│   ├── public/           # manifest.json (Manifest V3)
│   ├── dist/             # Built unpacked extension ready to load in Opera GX / Chrome
│   ├── package.json      # Extension npm configuration
│   └── vite.config.ts    # Multi-page build configuration
├── tests/                # 32 pytest automated tests including 1,500-job software load test
├── scripts/              # run_backend.sh, build_extension.sh, run_tests.sh, dry_run_demo.py
├── docs/                 # architecture.md, security.md, capability_matrix.md, test_report.md
└── .env.example          # Safe configuration template (zero real secrets)
```

---

## 3. Installation & Setup (macOS)

### Prerequisites
- macOS (Apple Silicon or Intel)
- Python 3.10+
- Node.js v18+ and npm
- Opera GX or Google Chrome

### Step 1: Clone & Set Up Backend Environment
```bash
cd /Users/yusuftarwala/quant

# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install backend dependencies
pip install -r backend/requirements.txt
```

### Step 2: Configure Environment
Copy `.env.example` to `.env` (optional, sane defaults are auto-configured):
```bash
cp .env.example .env
```
*(Optional)* Add your Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step 3: Build the Browser Extension
```bash
cd extension
npm install
npm run build
cd ..
```
The built, unpacked extension is located in `extension/dist/`.

---

## 4. Loading the Extension in Opera GX & Google Chrome

### In Opera GX:
1. Open Opera GX and navigate to `opera://extensions`.
2. Toggle on **Developer mode** in the top right corner.
3. Click **Load unpacked**.
4. Select the directory: `/Users/yusuftarwala/quant/extension/dist`.
5. The **Alpha Research Pilot** icon will appear in your extension toolbar.

### In Google Chrome:
1. Open Chrome and navigate to `chrome://extensions`.
2. Enable **Developer mode** (toggle in top right).
3. Click **Load unpacked** and choose `/Users/yusuftarwala/quant/extension/dist`.

---

## 5. Running the Application

### 1. Start the Backend Daemon
Run the startup script:
```bash
./scripts/run_backend.sh
```
The daemon starts on `http://127.0.0.1:8765`. On initial startup, it generates a secure 64-character pairing token and outputs:
```
Secure Pairing Token: <64-character-hex-token>
```

### 2. Pair the Browser Extension
1. Click the **Alpha Research Pilot** extension icon in your browser toolbar.
2. If prompted, paste the pairing token (from terminal output or `data/.pairing_token`).
3. Click **Pair with Local Backend**.
4. Click **Open Full Research Dashboard** to launch the comprehensive control panel (`dashboard.html`).

---

## 6. Running Automated Tests

Run the complete 32-test automated suite (including AST parser, unit checker, profile precedence, queue state machine, and the 1,500-job software load test):
```bash
./scripts/run_tests.sh
```

To run the full end-to-end dry-run demonstration:
```bash
python3 scripts/dry_run_demo.py
```

---

## 7. Safety, Verification & Zero-Leak Guarantees

- **MOCK Platform First**: All simulations run by default against a deterministic mock platform clearly labeled `MOCK` with synthetic metrics and realistic 252-day PnL series. Mock data is never represented as live platform data.
- **Strict Submission Safety**: The real BRAIN adapter requires verified credentials, explicit user session approval, and blocks autonomous final alpha submissions.
- **Zero Telemetry & Zero Leakage**: All keys, passwords, and pairing tokens are redacted recursively before export. No secrets are passed to AI prompts or extension storage.
