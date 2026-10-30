# BillSaathi — handoff (2026-10-30)

Read with `CLAUDE.md` (brief, schedule §8, decisions §11) and `docs/AGENT_DESIGN.md` (agent design).

## What is built and deployed

| Piece | Where | State |
|---|---|---|
| API (FastAPI) | https://ca-billsaathi-api.orangeocean-70e70440.centralindia.azurecontainerapps.io | Live, image `a6acf3e`, min 1 / max 1 replica, keys as Container Apps secrets |
| Web app (Next.js static) | https://zealous-coast-09279dd00.1.azurestaticapps.net | Live (Azure Static Web Apps, Free), built from `9634317`+ |
| Repo | https://github.com/bharatvamsi34/billsaathi | Latest commit before this handoff: `9399b63`; CI runs `api` and `web` jobs |

**API endpoints:** `GET /api/v1/health` · `POST /api/v1/checks` (image or text, `language` en/te/hi; `audio` returns 501) ·
`GET /api/v1/checks/{id}/events` (Server-Sent Events, resumable with `Last-Event-ID`) · `GET /api/v1/checks/{id}` ·
`POST /api/v1/checks/{id}/answer` · `GET /api/v1/bbps-mock/...` (mock, synthetic).

**Pipeline (one for every channel):** extraction (image: fields + verbatim transcription in parallel) → milestone check →
mandatory checks at fixed points (code, before the agent) → agent (Muse Spark 1.3, `low`) → `submit_verdict`
(5 deterministic checks, then LLM claims judge; 3 refusals → forced CAUTION, or the floor if stricter) → verdict.
Every step is an `EvidenceRecord` entry and a masked live event.

**Measured:** agent-only live run on 10 dev items: 10/10 correct, false SAFE 0, median 5.6 s. Deployed end to end
(5 dev images): median 12.7 s, p90 16.0 s. Web URL check (Hindi KYC/APK sample): SCAM, 17.7 s.
Tests: 482 API (pytest) + 10 web (vitest), all green. Screenshots: `docs/screenshots/`.

**Spend so far:** Meta model API ≈ $2 in total; Azure ≈ ₹30 this month (budget ₹1,000, alert at 80%).

## Working mode (agreed with BV)

- If all tests and lint pass: commit and push each block, then continue to the next block without waiting.
- **Stop and ask** only for: (a) any live API run expected to cost **more than $1**, (b) **design decisions** not covered
  by `CLAUDE.md` or `docs/AGENT_DESIGN.md`, (c) **failures not fixed in two attempts**.
- Plans for new features are proposed first and approved by BV. Never print, log or commit secret values.
- Windows + PowerShell. Commit messages with quotes: write them to a file and use `git commit -F` (PowerShell 5.1 breaks
  quoted text in native-command arguments). Don't pipe `deploy.ps1` through `2>&1` (CLI warnings become fatal).

## Schedule position (§8)

- Done: Day 1–2, Day 3 (risk engine), **Fri Oct 30 core** (agent loop, claims judge, live run, checks API), and
  **Sat Oct 31 core pulled forward** (web app live on a phone).
- **Next: Sat extras — WhatsApp webhook** on the same `/api/v1/checks` pipeline.
- **Sun Nov 1 core:** Telugu/Hindi explanations (verdict explained in the user's language; facts from `app/facts.py`
  only), voice question via Muse Voice Transcribe (`languageBias` always), sandbox pay (explicit confirmation,
  idempotency key, mock receipt, immutable audit row), eval metrics page on the **test split**, deploy, first user
  tests with 3–5 people (findings in §11); then the Muse Image share card.
- Mon Nov 2: Privacy Mode (Baseten), polish, second user tests, README; feature freeze at midnight.
  Tue Nov 3: demo video. Wed Nov 4: submit by 9 PM IST.

## Open items

1. **BV:** review the Telugu and Hindi interface text on a phone — `web/src/lib/i18n.ts`, `web/src/lib/codes.ts`,
   `web/src/lib/share.ts`, and the sample titles in `web/scripts/build-samples.mjs`.
2. **WhatsApp webhook** (Sat extra): Meta WhatsApp Cloud API test number → same pipeline → reply in the user's language.
3. **BV:** create a WhatsApp **permanent (system-user) access token** and get the **App Secret** (for webhook signature
   checks). They go into `api/.env` and Container Apps secrets like the model keys — never into chat or git.
4. Sunday core list (above).
5. **Set API min replicas back to 0 after Nov 8** (a full month at 1 replica ≈ ₹1,600 exceeds the budget):
   `az containerapp update -n ca-billsaathi-api -g rg-billsaathi-cin --min-replicas 0`
6. Still open from earlier: decode SAM mask format (SAM crop not yet in the pipeline), Baseten pricing, ZDR availability
   for the Meta account, the 2-way judge refusal that occasionally adds ~4 s.
7. Minor UI polish: the timeline box has no inner padding; English agent reasons are hidden in TE/HI until Sunday's
   explanations land.

## Known limits

- Checks, paused runs, rate-limit counters and the daily spend total are **in memory** in one process (10-minute
  expiry): lost on restart, not shared between replicas → the API must stay at **max 1 replica**.
- `CORS_ORIGINS` is set to the Static Web App origin + `http://localhost:3000`; a new web origin needs deploy step 12.
- Spend cap is per UTC day and checked before a check starts (one in-flight check can go slightly over).
- Voice input returns 501 until Sunday. SAM 3.1 crop is not wired in yet (fallback: original image).
- All data is synthetic; BBPS is a mock; payments are not implemented (pay button disabled).

## Exact deploy commands (PowerShell, repo root, after `az login`)

```powershell
# API: build image in Azure (tag = git sha), switch the app to it, check health
.\infra\deploy.ps1 -Step 5
.\infra\deploy.ps1 -Step 8
.\infra\deploy.ps1 -Step 9          # traffic can take ~1 min to move to the new revision

# Model API keys -> Container Apps secrets (reads api\.env, never prints values)
.\infra\deploy.ps1 -Step 10

# Web app: build against the live API and deploy to Static Web Apps; then API CORS for its origin
.\infra\deploy.ps1 -Step 11
.\infra\deploy.ps1 -Step 12

# End-to-end checks against the deployed API (median / p90), from api\
.venv\Scripts\python scripts\e2e_check.py https://ca-billsaathi-api.orangeocean-70e70440.centralindia.azurecontainerapps.io ..\data\synthetic\images\bill_genuine_ebnl.png ..\data\synthetic\images\scam_en_disconnect_lookalike.png

# Agent-only live run on 10 dev items (~$0.10), from api\
.venv\Scripts\python -m app.agent.cli --budget 0.3

# Local checks before every commit
cd api;  .venv\Scripts\python -m ruff check .; .venv\Scripts\python -m ruff format --check .; .venv\Scripts\python -m pytest -q
cd web;  npm run lint; npm run typecheck; npm test
```
