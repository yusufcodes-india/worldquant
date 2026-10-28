# BRAIN Alpha Research Assistant

A Chrome MV3 extension built with **React + Vite** and **TypeScript** that provides a sandboxed research assistant for WorldQuant BRAIN Fast Expression.

## Features (Phase 1)
- Popup UI with "Test AI Connection" and "Open Dashboard" buttons.
- Options page that stores a Gemini API key in `chrome.storage.session` (session‑only).
- Dashboard UI with an **Alpha JSON import wizard**.
- Typed **IndexedDB** wrapper (`src/storage/database.ts`) for persisting imported Alpha data and future research runs.
- Mock AI provider for demo mode and a stub for a Gemini BYOK provider.
- Full build pipeline (`npm run build`) producing a loadable `dist/` folder.

## Development
```bash
# Clone the repo (your own copy) and install deps
npm install

# Start Vite dev server (auto‑picks a free port)
npm run dev
```
Open the URLs printed by Vite, e.g. `http://localhost:5182/src/ui/dashboard/index.html`.

### Running Tests
```bash
npm test   # runs Vitest
```
The test suite includes:
- IndexedDB wrapper unit tests (using `fake-indexeddb`).
- Basic React render test for the dashboard import wizard.

## Building the Extension
```bash
npm run build   # outputs to ./dist
```
Load the `dist/` folder in Chrome (`chrome://extensions → Load unpacked`). The manifest points to the built files.

## Project Structure
```
src/
  ai/               # Mock and Gemini providers
  background/       # Service worker and message router
  storage/          # IndexedDB wrapper
  ui/
    popup/          # Popup UI
    dashboard/      # Dashboard UI & import wizard
    options/        # Options page UI
  shared/           # Types shared across UI & background
```

## Next Steps (Phase 2)
- Implement a richer **Alpha JSON schema** and mapping UI.
- Add full research‑run CRUD UI backed by `researchRuns` store.
- Flesh out the Gemini provider with real API calls.
- Add alarms‑based scheduler for periodic improvements.
- Expand unit‑ and integration‑tests.

---
*All code is self‑contained, uses only `chrome.storage.session` for credentials, and does not embed any API keys.*