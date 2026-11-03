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

## Build log, final batch (Nov 2)

- (a) Verdict explanation + Listen: **done**, commit `185818f`, https://zealous-coast-09279dd00.1.azurestaticapps.net (live checks: TE and HI SCAM, EN CAUTION, all `source=model`).
- (b) Voice input (web + WhatsApp voice notes): **done**, commit `6e68f26`, same URL (real browser with fake mic, live: heard → verdict). WhatsApp voice notes tested offline only.
- (c) Sandbox pay + audit log: **done**, commit `4ed1bc2`, same URL (live browser: SAFE → confirm → receipt `SBX-…`, audit entry #1). The live test also found and fixed a 409 when paying during the explanation.
- (d) SAM 3.1 crop + box in the timeline: **done**, commit `9e0bf7e`, same URL (live: phone-photo sample → SAFE). Fields read the crop; transcription reads the original.
- (e) Privacy Mode: **done**, commit `7a8c905`, same URL (3/3 dev items correct on real Baseten; no Meta call on that path).
- (i) /privacy + app icon: **done**, commit `bbcfcc3`, https://zealous-coast-09279dd00.1.azurestaticapps.net/privacy and /icon-1024.png.
- (g) Muse Image warning card: **done**, commit `3c94f42`+, same URL (live: Telugu card over the generated background; all model tools off).
- (f) Evaluation page from real test-split runs: **done**, https://zealous-coast-09279dd00.1.azurestaticapps.net/eval (21/21, 0/13 false SAFE, p50 10.9 s; sweep and Spark Open included; caveats on the page).
- (j) Speed: **done**. 6 live checks, median before -> after: verdict 12.4 -> 12.1 s (no real change), first signal none -> 6.8 s, explanation shown 17.0 -> 15.7 s. Early event, judge at minimal, prompt cache keys, live step timers.
- (k) Desktop redesign: **done**, 3 review passes, same URL. Hero with cited stat, Meta models at work, guide, badges, Motion, reduced-motion respected.
- (h) README: **done**, https://github.com/bharatvamsi34/billsaathi
- WhatsApp end to end: **working** after subscribing the Business Account to our app (POST subscribed_apps); text tested from BV's phone. Effort test on dev: all-minimal 38/39, not faster; product stays at low.
- WhatsApp live test by BV: text, photo and Telugu voice note all **working**; nothing to fix.
- Demo video prep: `docs/DEMO_SCRIPT.md`, `docs/SUBMISSION.md`. No feature changes.

## Latest status (Nov 4)

Read this section first; the sections above describe Oct 30 unless a build-log line says otherwise.

- **Live:** API image `32357ac`; web app deployed after `7e326c4`. Later commits only touch docs. Rollback tag: `demo-ready-v1` (`7cecfef`).
- **WhatsApp subscription fix:** no reply came because the WhatsApp Business Account (`1802037777798003`) was not subscribed to our app (`BillSaathi`, `1839271813880516`); only Meta's "WA DevX Webhook Events 1P App" was. Verifying the webhook and ticking "messages" does not do this. Fixed with `POST /{waba-id}/subscribed_apps`; no code change. If replies stop, `GET` that endpoint first.
- **WhatsApp status:** BV's live tests of text, a sample bill photo and a Telugu voice note all worked. Numbers other than BV's are untested.
- **Effort test (dev split, 39 items):** reading, agent and judge all at `minimal` scored 38/39 (one false alarm, one question asked), p50 13.8 s, $0.016 per check. The product (`low`, judge `minimal`) scored 39/39, p50 10.6 s, $0.020. **The product stays at `low`.** The runs were hours apart, so the speed gap is weak evidence. Results: `eval/results/dev_*.jsonl`.
- **Design review set:** `docs/screenshots/review/` on BV's machine, gitignored, not in the repo: 111 PNGs (16 states at 1440x900, 1280x800 and 390x844, above the fold and full page), `desktop_full_check.webm` (30 s) and `INDEX.md`. Costs about $0.70 per full capture; the scripts were in the session scratchpad and are not in the repo.
- **Open UI bug (not fixed):** on the phone pay-confirm and receipt screens, the biller name breaks mid-word ("Demo Power Distributio / n Co. Ltd"). The cause is `break-all` on the row value in `web/src/components/SandboxPay.tsx`.
- **Demo and submission:** `docs/DEMO_SCRIPT.md`, `docs/SUBMISSION.md` (its `[BV: …]` items are open). Still to rehearse: the Telugu line spoken aloud, the sample photo through a camera, and Listen in Telugu. Do not deploy between warming the warning card and recording.
- **Other open items:** BV's review of Telugu and Hindi text; user tests (none recorded in §11); `docs/TESTING.md` still uses the plausible number `9123456780`, while the demo uses `9000000003`; Fireworks fallback untested live; set min replicas to 0 after Nov 8.

## Overnight build log (Nov 4, unattended)

One line per item: item, status, commit.

- 0 Orient: **done**. 614 API + 19 web tests green, live healthy. Tag `pre-overnight` pushed at `062565b`.
- API evidence values in live events: **done**, `1375aae`.
- 1, 2 Visual system and results panel: **done**, `297bc0d`. Live smoke: SCAM 18.9 s, SAFE 26.7 s.
- 3 Phone, 4 WhatsApp, 5 /eval and docs, 6.1 early explanation, 6.3 stalled-stream watchdog: **done**, `b42d3df`. Live smoke passed. WhatsApp tested with the mocked Graph API only.
- 6.1 result, 6 live scam checks, same items, before -> after: verdict median 19.3 -> 21.1 s, p90 25.0 -> 26.9 s (no real change); explanation shown median 33.3 -> 21.1 s, p90 35.8 -> 26.9 s. It now appears with the verdict. SCAM only; other verdicts unchanged.

## Overnight decisions

- The pending `.gitignore` change was already committed (`062565b`). I also ignored `docs/screenshots/testing/` and `docs/screenshots/demo/`, because an untracked file marks every image tag `-dirty`.
- I grouped sub-items into deploy batches rather than deploying each of 2.1-2.14 alone: they share one screen and each deploy restarts the API. Tests, screenshots and a live smoke check ran per batch.
- Screens were reviewed against recorded real event streams replayed in the browser, to save model spend. Live smoke checks ran on the deployed site.
- **Voice sample (2.11) is English, not Telugu.** This machine has only English Windows voices. `api/spike/inputs/voice_te.*` is BV's real voice and is deliberately kept out of git, so I did not publish it. Online voices would mean new Azure terms or a service whose output rights are unclear (rules §3), so I did neither. The sample is labelled "synthetic English voice" and runs through Muse Voice Transcribe. Telugu voice stays in the demo as BV speaking live.
- **Spoken digits come back as words** ("nine zero zero…"), so the voice sample's number is not read as a number; its verdict is still SCAM from the unknown biller, non-official channel and threat. **Scene 5's Telugu line may do the same: rehearse it.**
- Same-account tampered bill (2.11): `labels.jsonl` may not change, so I added demo-only samples that are in no split (`data/generators/make_demo_samples.py`): the genuine photo's account and framing with only the amount changed to ₹4,240 (biller ₹1,240). The old `bill_tampered_demo` sample remains in the dataset.
- Judge-catch replay (2.13) replays `eval/results/agent_live_2026-10-29_2355.jsonl`, item `scam_te_known_vpa`: a real refusal ("tonight" not in the evidence). It is copied at build time and a test checks it against the file. Nothing fabricated.
- Comparison order (2.4): actions, comparison, explanation, reasons, trace. The explanation sits below the comparison so the centrepiece stays near the first screen.
- Early explanation (6.1) is written from the code's findings only, never from the agent's unjudged reasons, and shown only after the verdict. That keeps judge-refused wording off the screen.
- Privacy Mode no longer requests the Muse Image picture: the card is a plain gradient on that path, because the picture is on Meta's API. The old flow contradicted "no call to Meta's Model API".
- New Telugu and Hindi strings tonight were written by me, not reviewed by a native speaker. **BV should read them** (`web/src/lib/i18n.ts`, `api/app/whatsapp/texts.py`, `web/src/lib/reasons.ts`).
- WhatsApp changes were tested with the mocked Graph API only; I sent nothing to any real number.
