# Alpha Research Pilot: Security & Threat Model

Alpha Research Pilot implements defense-in-depth to protect user credentials, prevent arbitrary execution, and ensure zero unintended platform calls:

## 1. Network & Transport Isolation

- **Loopback Binding**: The backend binds exclusively to `127.0.0.1` (`PILOT_HOST`). It will never bind to `0.0.0.0`.
- **DNS Rebinding Protection**: The application enforces `HostHeaderMiddleware`, validating that all incoming HTTP `Host` headers originate from `127.0.0.1`, `localhost`, or `testserver`. Any request with an unauthorized Host header is rejected immediately with HTTP 400.
- **Strict CORS Policy**: CORS credentials are only allowed for explicit loopback and extension origins (`chrome-extension://.*`, `http://127.0.0.1:*`, `http://localhost:*`). Wildcard origins (`*`) with credentials are fully prohibited.

## 2. High-Entropy Pairing Token (`X-Pilot-Token`)

- A cryptographically secure 32-byte (64 hex characters) pairing token is generated on startup and saved with `0600` POSIX permissions in `data/.pairing_token`.
- Every protected API endpoint requires the `X-Pilot-Token` header.
- Unauthenticated requests fail with HTTP 401.

## 3. Credential Redaction & Zero Leakage

- **Logging & Export Sanitization**: The `redact_secrets` recursive engine scans all outgoing JSON exports and log payloads. Keys named `token`, `key`, `password`, `secret`, `auth`, `credential`, or strings matching Google API key patterns and Bearer tokens are replaced with `[REDACTED_SECRET]`.
- **Zero Prompt Leakage**: Platform credentials, pairing tokens, and session secrets are never passed into Google Gemini prompts or candidate contexts.

## 4. Extension Sandbox & Content Security Policy (CSP)

- The browser extension complies with Manifest V3.
- **CSP**: `extension_pages: script-src 'self'; object-src 'self';` strictly blocks remotely hosted executable scripts.
- No eval or dynamic script injection is used.

## 5. Live Platform Guardrails

- The `BrainPlatformAdapter` is locked by default.
- Even if credentials (`BRAIN_USERNAME`, `BRAIN_PASSWORD`) are present in `.env`, the adapter refuses simulation submissions unless the user explicitly grants session approval via `POST /settings/approve_live`.
- Final alpha submission is intentionally omitted from the autonomous engine; only human review and manual submission are permitted.

## 6. Prompt Injection Defense (Tab Observation)

- Current-tab observation is disabled by default behind the `FEATURE_FLAG_TAB_OBSERVATION` feature flag.
- When enabled, it strictly matches an approved domain regex (`*.worldquantbrain.com`).
- Extracted DOM content is treated as untrusted text and filtered against prompt-injection instructions before being passed into model contexts.
