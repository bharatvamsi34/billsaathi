# BillSaathi — Project Brief & Build Plan

> Meta Global AI Developer Hackathon · Startup Track · Theme: **Build for Your World**
> Builder: Bharat Vamsi Chillimunta (Ireesha Infosol Pvt Ltd) · Solo
> Hacking window: Oct 26 – Nov 4, 2026 · **Hard deadline: Nov 4, 9:00 PM ET = Thu Nov 5, 7:30 AM IST**
> Our internal deadline: **Wed Nov 4, 9:00 PM IST** (10.5 h buffer)

---

## 1. One-liner

**BillSaathi is an AI agent that reads any Indian bill or payment request — paper bill, SMS, WhatsApp forward or voice note — verifies it against biller data, catches scams before money moves, and explains the verdict in the user's own language.**

## 2. Why this wins (keep every decision pointed at these)

Judges score four things equally: **Impact · Use of Meta AI tooling · Technical depth & execution · Demo quality.** Startup track also asks: *does it hold up in production?*

| Criterion | How BillSaathi scores |
|---|---|
| Impact | Bill-payment and "power will be cut tonight" scams are a mass, daily problem in India. Real users, real money, real languages. |
| Meta AI tooling | Every Meta model has a distinct, visible job (see §4). Open-weight model via Baseten powers a privacy mode. |
| Technical depth | Real tool-using agent + deterministic risk engine + measured evaluation harness with published precision/recall. |
| Production-readiness | Fintech-grade guardrails: LLM can never override a failed hard check, PII masking, idempotent payments, audit log, tests, CI, deployed in Azure Central India. |
| Demo | A scam message gets caught live, a genuine bill gets paid safely, a Hindi voice question gets answered, a WhatsApp forward gets a verdict. |

**Banned-category warning:** the rules ban "simple image analyzers". BillSaathi must never look like a bill scanner. The agent's *verification and reasoning* is the product; extraction is only step one. Every screen and the demo must show this.

## 3. Hackathon rules we must obey (non-negotiable)

1. **New work only.** Fresh public repo, created during the event. No code from the handwriting-OCR project, Ashrith Pay, or anything pre-existing.
2. **Demo opens with one line** stating what was pre-existing (nothing) vs built this week.
3. **No data/code/assets we lack rights to.** No Ashrith Pay code, credentials, APIs or customer data. **Synthetic data only.** BBPS is a **mock service we build**; we never claim to be connected to the real BBPS network.
4. **Free Meta credits may use our content for product improvement** → never send real personal data to any API.
5. **Public repo**, 3-minute demo video, working live product, all contributors listed. One project, Startup track only.
6. Must **meaningfully use Meta Model API and/or Meta open-weight models.**

## 4. Meta models — who does what

> Day-1 spike (2026-10-27) results below; raw data and report in `api/spike/results/`.

| Model | Access | Job in BillSaathi | Day-1 spike result |
|---|---|---|---|
| **Muse Spark 1.3** (`muse-spark-1.3`) | `META_API_*` | **Primary**: verdicts, tool-calling agent, explanations, bill reading | Verdicts 4/4 at `low` effort (~3 s); native tool calling PASS; key bill fields 100%; te/hi/ta explanations complete at 4096 tokens, `low` (~3–4 s); BV ratings Telugu 4/5, Hindi ≈4/5. $1.25 in / $4.25 out per 1M tokens |
| Muse Spark 1.1 (`muse-spark-1.1`) | `META_API_*` | Fallback for bill reading | Key fields 100%, fastest at reading (~4.6 s); tool calling PASS |
| Muse Wonder (`muse-wonder-1.0`) | `META_API_*` | Not used in the product (comparison only) | Correct, but 2–4× slower and ~4× the cost; Indian-language explanations ~15 s |
| SAM 3.1 (`sam-3.1`) | `META_API_*`, file upload | Crop the bill out of a phone photo with concept "document" | "document" box IoU 0.98 vs true bill area; "bill" and "link" find nothing; QR negative control correct. **Not usable for link highlighting.** Output is text tokens `<\|box;x1..y2;w;h\|><\|mask;…\|>`; mask decoding still to do. $2.50 per 1,000 images |
| Muse Voice Transcribe (`muse-voice-transcribe-1.0`) | `POST /v1/asr/transcribe`, multipart | Voice input | English exact; Telugu-English exact **with** `languageBias`, one word wrong and English letters without it. ~3 s, $0.18 per hour of audio |
| Muse Image (`muse-image-1.0`) | `META_API_*` | Optional / low priority. If used: `enable_shell`, `enable_web_search`, `enable_image_search` all false | Not tested |
| **Muse Spark Open** (open weights via Baseten, `meta-models/muse-spark-open-1026`) | `BASETEN_API_KEY` | **Privacy Mode**. Targets *Best Build on Open-Weight Models* ($10k). | Verdicts 4/4; tool calling PASS (3 steps); key fields 100% (data URL); Telugu audio near-exact; reasoning returned separately. Explanations use less native script (Ta 0.81, Hi 0.88) — needs rating. Price not known yet |
| `*-contributor` variants | — | **Never used** — they train on inputs. The spike runner refuses them | — |
| Muse Glimmer (open-weight 30B, Apache-2.0) | Modal (later) | Possible second open-weight option, not before Day 6 | — |
| Modal (if credits granted) | `MODAL_*` | Run the evaluation harness at scale in Sandboxes; optional self-hosted open-weight endpoint | — |

Baseten: OpenAI-compatible, `base_url="https://inference.baseten.co/v1"`, model **exactly** `meta-models/muse-spark-open-1026`. Output includes reasoning — parse the final answer separately from reasoning content.

Integration rules (from the spike):
- Meta Model API uses the OpenAI Responses format at `https://api.meta.ai/v1`. Use the official `openai` SDK (non-streaming) for agent steps; raw httpx only for `/files`, SAM and ASR. `GET /v1/models` lists available model IDs.
- Send images as inline data URLs, so no file is stored on Meta's servers (the image is still sent to Meta for processing). `/v1/files` + `file_id` also works; if used, delete with `DELETE /v1/files/{id}` (returns 200).
- Reasoning is 60–85% of output tokens: use `low` effort for verdicts and explanations, and `max_output_tokens` ≥ 4096 for Indian-language explanations.
- Model self-reported confidence is not reliable (0.9+ on wrong fields). Hard rules verify amount and destination with tools; low confidence can only push towards CAUTION.
- Facts shown to users (e.g. helpline numbers) come from a vetted list in code, never from model output.
- Speech-to-text always sends the user's chosen language as `languageBias`.

## 5. Product scope

### 5.1 Core flow (MUST ship — this alone must be demo-worthy)

1. **Capture** — camera photo / upload of a bill, screenshot of SMS/WhatsApp, pasted text, or voice note.
2. **Isolate** — SAM 3.1 crops the document from the photo (fallback: use original image).
3. **Extract** — vision model → validated JSON: biller name, biller category, consumer/account no., amount, due date, bill date, payment destination (UPI VPA, URL, phone, QR text), language, urgency language, and **per-field confidence**.
4. **Verify (agent with tools)** — mandatory checks run at fixed points (Meta Agents 102 guidance); the agent investigates further and decides. Code runs `lookup_biller`, `check_payment_destination` for every destination, `match_scam_patterns`, then `fetch_bill` and `get_bill_history` once the biller is known, before the agent's first turn (recorded with origin `mandatory`); the agent reviews that evidence, may call any tool again or `ask_user`, and must `submit_verdict` with citations. Tools:
   - `lookup_biller(name, category)` → mock BBPS biller registry (fuzzy match, official biller ID)
   - `fetch_bill(biller_id, consumer_no)` → mock BBPS bill fetch (amount/due date the biller actually has)
   - `check_payment_destination(vpa|url|phone)` → official-channel allowlist + known-scam list + lookalike-domain detection
   - `get_bill_history(biller_id, consumer_no)` → last 6 bills for spike detection
   - `match_scam_patterns(text)` → library of known Indian bill-scam patterns (disconnection threats, "update KYC", personal mobile numbers, APK links, short URLs)
5. **Decide** — two-layer risk engine:
   - **Hard rules (deterministic, cannot be overridden by the LLM):** unknown biller, payment destination not official, amount mismatch vs biller fetch, known scam domain/VPA → minimum verdict CAUTION or SCAM.
   - **LLM reasoning layer** adds context and soft signals; may raise risk, may **never lower** a hard-rule verdict.
   - Verdict: **SAFE / CAUTION / SCAM**, with evidence list (each reason cites the tool result it came from).
6. **Explain** — plain-language verdict in the user's language. Launch languages: **English, Telugu, Hindi** (Telugu verified by BV, a native speaker). **Marathi and Tamil are "beta"** (shown with a beta label) until BV-rated quality is clearly good. Browser speech synthesis reads it aloud.
7. **Act** — SAFE bills: "Pay via BBPS (sandbox)" with explicit confirmation, idempotency key, mock receipt, audit-log entry. SCAM: "Report & block" + shareable warning card to forward to family.

### 5.2 Differentiators (SHOULD ship, in this order)

1. **Privacy Mode toggle** — whole pipeline on Muse Spark Open via Baseten; PII masked before any cloud call in normal mode.
2. **Evaluation dashboard** — public page showing precision/recall/false-safe rate on our labelled synthetic test set, per category. "False SAFE" (a scam we called safe) is the metric we optimise hardest.
3. **WhatsApp bot** — forward a suspicious message/photo to BillSaathi on WhatsApp (Meta WhatsApp Cloud API test number) → verdict in reply, in your language. Start only when core flow is deployed and green.
4. **Family protect** — one-tap share of the warning card.

### 5.3 Explicitly OUT of scope

Real BBPS/NPCI integration, real payments, user accounts/auth beyond a demo session, native mobile apps, fine-tuning, any real customer data.

## 6. Architecture

```
[Next.js mobile-first web app]  [WhatsApp Cloud API webhook]
            \                        /
             \                      /
          [FastAPI backend — /api/v1]
             |  orchestrator (agent loop, max N tool steps, timeouts)
             |-- vision/isolate  -> SAM 3.1
             |-- extract         -> Muse Spark | Muse Spark Open (privacy)
             |-- transcribe      -> Muse Voice Transcribe
             |-- tools           -> mock BBPS svc, destination checker, scam patterns, history
             |-- risk engine     -> hard rules + LLM layer
             |-- explain         -> Muse Spark/Wonder (target language)
             |-- payments(mock)  -> idempotent, audit log
          [Mock BBPS service (FastAPI module, synthetic data)]
          [Postgres or SQLite -> audit log, eval results]
Hosting: Azure Container Apps (API) + Azure Static Web Apps (web), region Central India.
Secrets: .env locally, Azure Key Vault / Container Apps secrets in cloud.
```

### Repo layout

```
billsaathi/
  CLAUDE.md
  README.md                # judges read this: problem, demo GIF, architecture, eval results, how to run
  .env.example             # names only, never values
  api/                     # FastAPI app
    app/main.py
    app/agent/             # orchestrator, tool registry, prompts
    app/models/            # Meta API + Baseten clients behind one interface
    app/risk/              # hard rules + verdict merge
    app/bbps_mock/         # biller registry, bill fetch, history (synthetic)
    app/schemas.py         # Pydantic models for every input/output
    tests/
  web/                     # Next.js app
  data/
    synthetic/             # generated bills, SMS, WhatsApp texts + labels.jsonl
    generators/            # scripts that create the synthetic set
  eval/                    # harness, metrics, report output
  infra/                   # Azure deployment (Bicep or az CLI scripts), Dockerfile
  .github/workflows/ci.yml
```

## 7. Engineering standards (fintech-grade)

- **Typed everything:** Pydantic schemas for all model outputs; reject and retry (max 2) on invalid JSON; never pass unvalidated model output downstream.
- **Model client abstraction:** one interface, two providers (Meta API, Baseten). Timeouts, retries with backoff, token/cost logging per request.
- **Safety invariants (unit-tested):** LLM cannot lower a hard-rule verdict; low extraction confidence on amount/destination ⇒ CAUTION, never SAFE; any tool failure ⇒ CAUTION with "could not verify".
- **PII:** mask consumer numbers/phones in logs; no raw images stored beyond the session unless the user opts in.
- **Payments (mock):** explicit confirmation step, idempotency key, immutable audit log row per action.
- **Secrets:** never in code or git. `.env` is gitignored. Check before every commit.
- **Tests:** pytest for risk engine, tools, schemas; one end-to-end test per demo scenario. CI runs on every push.
- **Commits:** small, descriptive. Public repo from day 1 so history proves everything was built during the event.

## 8. Day-by-day schedule (IST)

Live sessions (9:30–10:30 PM IST): Oct 27 Agents 101 · Oct 28 Agents 102 · Oct 30 Fireworks inference & training.
Office hours: weekdays 7:30–8:30 PM IST (from Nov 2: 8:30–9:30 PM IST) in #office-hours.

Re-planned 2026-10-29 after the Agents 102 session: nothing is cut. Each day has a **core**
(listed first) and **extras** (after "then"). Feature freeze stays **Mon Nov 2, midnight**.

| Day | Date | Goal (core; then extras) | Done when |
|---|---|---|---|
| 1 | Tue Oct 27 – Wed Oct 28 AM | Repo + **model spike** + skeleton deploy | **Done.** Public repo; every Meta model called from Python; findings in §4; FastAPI app live on Azure Central India; CI green |
| 2 | Wed Oct 28 | **Mock BBPS + tools + data + extraction** | **Done.** 8 mock billers with endpoints; 5 verification tools with stable evidence ids; 60 labelled synthetic items (EN/TE/HI) whose evidence the tools reproduce; extraction on Spark 1.3 returns validated JSON (5/5 live); FEEDBACK.md and docs/AGENT_DESIGN.md started |
| 3 | Thu Oct 29 | **Risk engine + agent design update** | Risk engine reproduces all 60 dataset verdicts (**done**); AGENT_DESIGN.md updated with Agents 102 verification layers; agent loop build under way |
| 4 | Fri Oct 30 | **Agent loop + claims check + live run + API endpoint** | Loop per docs/AGENT_DESIGN.md (parallel tool calls, allowlist, milestone check, `ask_user`, 3-refusal → forced CAUTION, LLM claims judge) tested with a scripted model; live sample on dev items within ≤ 3 turns / ≤ 10 s; agent exposed at `/api/v1`. *In parallel: BV sets up the WhatsApp Cloud API test app.* |
| 5 | Sat Oct 31 | **Web app core flow**; then WhatsApp webhook | Capture → live agent steps from the evidence record → verdict card with evidence, on a phone; then the WhatsApp webhook using the same agent API |
| 6 | Sun Nov 1 | **Telugu/Hindi explanations, voice, sandbox pay, deploy, eval page, first user tests**; then Muse Image share card | EN/TE/HI explanations (MR/TA beta); voice via Muse Voice Transcribe; sandbox pay with confirmation + audit; full stack deployed; eval metrics page (test split); **3–5 real people** try it, findings in §11; then the Muse Image scam-warning share card (`enable_shell`, `enable_web_search`, `enable_image_search` all false) |
| 7 | Mon Nov 2 | **Privacy Mode (Baseten), polish, user tests**; then WhatsApp polish | Privacy Mode end to end; fixes from testing; **second round of user tests**; README with architecture and metrics. **Feature freeze at midnight.** |
| 8 | Tue Nov 3 | **Demo video (full day)** | Script rehearsed, 3-minute video recorded, edited and uploaded; links tested |
| 9 | Wed Nov 4 | **Ship** | Submission done by 9 PM IST, X post for Most Viral, all links verified in an incognito window |

**Rule:** extras never start on a day until that day's core is committed, tested and deployed.
If a day still slips, cut from §5.2 bottom-up (Family protect → WhatsApp → Privacy Mode). Never cut
deployment, tests on safety invariants, user testing, or demo quality.

## 9. Demo video plan (3:00)

1. **0:00–0:10** — Required line: "Everything shown was built during the hackathon, Oct 26–Nov 4." Hook: a real-looking SMS on screen — "Your electricity will be disconnected tonight at 9:30 PM. Pay now: [link]".
2. **0:10–0:45** — Forward it to BillSaathi → agent's steps appear live (biller lookup → destination check → pattern match) → **SCAM** verdict with evidence, in Hindi, read aloud.
3. **0:45–1:25** — Phone photo of a genuine bill → SAM isolates it → extraction → BBPS fetch matches → **SAFE** → confirm → sandbox payment + receipt.
4. **1:25–1:50** — Tampered bill (amount changed) → **CAUTION**: "Biller says ₹1,240, this bill says ₹4,240".
5. **1:50–2:15** — Voice: "Kya ye payment safe hai?" → answer. WhatsApp forward → reply (if shipped).
6. **2:15–2:40** — Under the hood: architecture, which Meta model does what, Privacy Mode on open weights, eval numbers (false-SAFE rate).
7. **2:40–3:00** — Impact + vision: built for India's next 500 million digital payers; Ireesha Infosol continues building it.

## 10. Submission checklist

- [ ] Public GitHub repo, README complete, `.env.example`, no secrets in history
- [ ] Live URL works on mobile, in incognito
- [ ] 3-minute video uploaded (unlisted YouTube or as required), link tested
- [ ] Submitted at https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit — Startup track, all fields
- [ ] X post with demo + link submitted through the platform (Most Viral, counts until Nov 8 EOD)
- [ ] Credits/spend checked on dev.meta.ai, Baseten, Modal

## 11. Open decisions / findings log

Record every decision and spike result here with a date, so the README and demo stay truthful.

- 2026-10-27 — Stack approved: Python 3.12+ (dev machine runs 3.14) + FastAPI, Next.js, Azure Central India, Claude Code Desktop for build. WhatsApp bot = stretch.
- 2026-10-27 — Dev environment: Windows, PowerShell, Git 2.55, Node 24, npm 11, Azure CLI 2.91. Repo: https://github.com/bharatvamsi34/billsaathi (public, MIT, Python .gitignore).
- 2026-10-27 — Meta Model API working (playground test on `muse-wonder-1.0`, $150 credits active). Baseten key received for `meta-models/muse-spark-open-1026`.
- 2026-10-27 — Day 1 plan approved. Python 3.14 locally and in the container (fall back to 3.12 only if a dependency actually fails). Order: repo hygiene → api/ setup → model spike → Azure deploy (Azure capped at 2 h; if blocked, moves to Day 2 morning). Keys live in `api/.env` (gitignored). No local Docker → images built with `az acr build`.
- 2026-10-27 — Spike rules: native function/tool calling is an explicit PASS/FAIL for Muse Spark, Muse Wonder and Muse Spark Open (FAIL ⇒ design a JSON-based tool loop). Keep a running approximate API cost; stop and report if spike spend exceeds $5. Hindi voice clip recorded by BV (no personal details).
- 2026-10-27 — Azure: resource group `rg-billsaathi-cin` (Central India) and Basic container registry (~$5/month) approved.
- 2026-10-27 — Model spike complete: 90+ calls, ~$1.00 estimated; results in `api/spike/results/`. Decisions: Muse Spark 1.3 primary, Spark 1.1 fallback for bill reading, Wonder not used; native tool calling (no JSON tool loop); openai SDK for Meta calls; images as data URLs; `low` effort and 4096 output tokens for explanations; speech-to-text always with `languageBias`; SAM with concept "document" for cropping only; Contributor models never used.
- 2026-10-27 — Launch languages EN/TE/HI; MR/TA beta. BV ratings of Spark 1.3 explanations: Telugu 4/5, Hindi ≈4/5.
- 2026-10-27 — Labels: `languages` is a list, main language first. Real voice recordings and their labels stay out of git (`labels.local.jsonl`).
- 2026-10-27 — Open items: decode the SAM mask format; Baseten pricing; a Hindi voice clip (optional); check whether Zero Data Retention (ZDR) mode is available for our Meta account — the speech-to-text pricing page says ZDR costs the same as standard. If yes, enable it for all production calls and mention it in the README.
- 2026-10-28 — Azure live: `ca-billsaathi-api` in `rg-billsaathi-cin` (Central India), image built with `az acr build`, pulled by managed identity (AcrPull only), scales 0–1; budget ₹1,000/month with 80% email alert. Deploy with `infra/deploy.ps1 -Step 5` then `-Step 8`. Raise min replicas to 1 before the demo.
- 2026-10-28 — Day 2 built: mock BBPS (8 fictional billers, 40 consumers, 6-month history, `/api/v1/bbps-mock`), 5 tools returning `ToolResult` with stable `evidence_id`s, append-only `EvidenceRecord`, facts 1930 and cybercrime.gov.in verified by BV.
- 2026-10-28 — Dataset: 60 items in `data/synthetic` (24 SAFE / 25 SCAM / 11 CAUTION; 39 dev / 21 test, stratified by scenario). Labels written from intent; a test requires the real tools to reproduce every label. Verdict policy written in `data/synthetic/README.md`; polite "avoid disconnection" reminders stay SAFE (BV). Tune on dev only; report on test.
- 2026-10-28 — Extraction: Spark 1.3, `low` effort, inline images, validated JSON with up to 2 retries; 5/5 dev images correct live (~$0.006 each, 4–7 s).
- 2026-10-28 — Agent design agreed (`docs/AGENT_DESIGN.md`): verification inside `submit_verdict`, citations must exist in this run, LLM can never lower the risk-engine floor, 3 refusals → CAUTION, one `ask_user` per run, scripted fake model for tests.
- 2026-10-28 — Schedule re-planned (§8): Nov 3 is a full demo-video day; user testing with 3–5 real people on Oct 31 and Nov 1.
- 2026-10-29 — Risk engine done: floor + SAFE checklist reproduce all 60 dataset verdicts. Low extraction confidence only blocks SAFE, never supports it (BV).
- 2026-10-29 — Agents 102 (verification) applied to the design: LLM claims judge inside `submit_verdict` (runs after all deterministic checks, can only refuse, fails closed), milestone check after extraction (`MISSED_BY_EXTRACTION`), tool allowlist, forced verdict = CAUTION or the floor if stricter, user sign-off before any payment. Meta's guidance: finance needs a 100% threshold, so SAFE requires every check to pass.
- 2026-10-29 — Speed: several tool calls per model turn, run in parallel; target ≤ 3 agent turns and ≤ 10 s per run on Spark 1.3 `low` (extraction excluded); turns, latency and cost recorded per run.
- 2026-10-29 — Schedule re-planned again (§8), nothing cut: Oct 30 agent loop + claims check + live run + API; Oct 31 web core, then WhatsApp webhook; Nov 1 explanations/voice/pay/deploy/eval/user tests, then Muse Image share card; Nov 2 Privacy Mode/polish/user tests, then WhatsApp polish; freeze Nov 2 midnight. **Rule: extras never start until that day's core is committed, tested and deployed.**
- 2026-10-29 — Working mode: commit and push each block when tests and lint pass; stop only for live runs over $1, design decisions not covered here or in AGENT_DESIGN.md, or failures not fixed in two attempts.
- 2026-10-29 — First live agent run (agent chose all tools): 10/10 correct, no false SAFE, but median 14.0 s; 4/10 first submissions refused by the judge. BV chose to prefetch mandatory checks in code (fixed points) and to tune the agent's reason-writing; the judge prompt stays unchanged (its one remaining objection — "tonight" not in the cited evidence — was correct).
- 2026-10-29 — Live run after prefetch + reason tuning, same 10 dev items, Spark 1.3 `low`: **10/10 correct, false SAFE 0, every run 1 agent turn + 1 judge call, 0 refusals, median 5.6 s, p90 8.1 s, $0.10 total** (`eval/results/agent_live_2026-10-29_2357.jsonl`). Earlier runs kept for comparison (`…_2344` before, `…_2355` the 4 refused items).
- 2026-10-30 — Checks API (`/api/v1/checks`): one pipeline for web and WhatsApp (extraction → milestone → mandatory checks → agent → verdict); live Server-Sent Events from the evidence record, masked; `ask_user` pauses the check (stream closes; client answers then reconnects with `Last-Event-ID`); image type checked by content; per-IP rate limit, daily spend cap (503 "service busy"), CORS from config. **Known limit:** checks, paused runs, rate-limit counters and the daily spend total live in one process's memory (10-minute expiry) — lost on restart and not shared between replicas, so the app must stay at max 1 replica until this moves to a store.
- 2026-10-30 — Speed tuning (1 h box), 5 deployed end-to-end checks on dev images, before → after (median / p90): extraction 4.6/7.7 s → 5.1/6.1 s; agent 10.6/20.3 s → 7.6/10.9 s; total 15.6/25.6 s → 12.7/16.0 s; all 5 verdicts correct both times; $0.23 spent. Changes: image fields and a verbatim transcription run as two parallel calls (transcription feeds only the milestone check and scam-wording check; failure = failed check, no SAFE); the agent's first message carries only masked fields and masked mandatory evidence (no raw or transcribed text). Remaining: occasional judge refusal adds a turn (~4 s); a cold start from zero adds ~24 s (min replicas 1 before the demo).
- 2026-10-30 — Web app live on Azure Static Web Apps (Free): https://zealous-coast-09279dd00.1.azurestaticapps.net (deploy: `infra/deploy.ps1 -Step 11`; API CORS for it: `-Step 12`). Mobile-first, EN/TE/HI, sample gallery from DEV items only, live fixed-point checks → agent → judge → verdict, "Warn my family", sandbox banner. Live check from the URL (Hindi KYC/APK sample): SCAM, 17.7 s.
- 2026-10-30 — API min replicas set to 1 (no cold starts). Cost at Central India idle rates ≈ ₹39/day; projected Oct ≈ ₹135 and Nov 1–8 ≈ ₹420 incl. registry, under the ₹800 alert. **Set min replicas back to 0 after Nov 8** (a full month at 1 replica ≈ ₹1,600 would exceed the budget).
- 2026-10-30 — **Status at handoff** (`docs/HANDOFF.md`): API (image `a6acf3e`) and web app live; Fri core and Sat core done; next is the WhatsApp webhook (Sat extra), then Sunday core (explanations, voice, sandbox pay, eval page, user tests). Open: BV review of TE/HI UI text, WhatsApp permanent token + App Secret, min replicas → 0 after Nov 8. 482 API + 10 web tests green.

- 2026-10-30 — Desktop layout for judges (≥1024 px): two columns, intro + "How it works" + capture/samples left, live timeline + verdict right (sticky); "Best on your phone" QR in the header; phone layout unchanged. Checked live at 1440/1024/360: no horizontal scroll, no console errors; SCAM 11.9 s, CAUTION 12.6 s (`docs/screenshots/04–06`). Manual test guide `docs/TESTING.md` (12 messages, verdicts reproduced with the real tools). **Fixed:** the Python `.gitignore` rule `lib/` had kept `web/src/lib/` (API client, i18n, timeline, tests) out of git; now tracked.
- 2026-10-30 — Fixed (BV): Telugu "cut" in the scam patterns matched as a bare substring, so కట్టు/కట్టండి/కట్టారు/కట్టవచ్చు ("pay/paid") counted as a disconnection threat. Now "కట్" counts only as a whole word next to connection/power/electricity wording, plus explicit threat phrases (కట్ చేస్తాం, కట్ చేయబడుతుంది, డిస్‌కనెక్ట్, సరఫరా నిలిపివేస్తాం); 17 regression tests. Dataset (60) + TESTING.md (12): no verdict changed; one false positive removed.
- 2026-10-31 — WhatsApp webhook built (`app/whatsapp/`, Sat extra): `GET/POST /api/v1/whatsapp/webhook`; Meta verify-token handshake; `X-Hub-Signature-256` checked on the raw body (401 otherwise); dedupe by message id; 200 at once, work in the background on the same pipeline as the web app (text and images via Graph media download, bytes sniffed); "Checking… ⏳" then ✅/⚠️/⛔ verdict with cited reasons (EN: agent text; TE/HI: evidence labels), 1930 on SCAM, web link, sandbox footer; reply language from the message script, switch with "English"/"తెలుగు"/"हिंदी"; one `ask_user` per check over chat, *skip* or 10 min → CAUTION with no model call; per-sender rate limit 5/min; senders known only by an HMAC (App Secret as key), raw numbers never logged. All state in memory (same max-1-replica limit). 21 tests with a mocked Graph API. Secrets via `deploy.ps1 -Step 10`.
- 2026-10-31 — WhatsApp webhook deployed (image `f774e13`, revision `--0000009`): `https://ca-billsaathi-api.orangeocean-70e70440.centralindia.azurecontainerapps.io/api/v1/whatsapp/webhook`. Live checks: handshake with the right token echoes the challenge, wrong token 403, forged signature 401, signed status-only payload 200. WhatsApp token, App Secret and verify token are Container Apps secrets. Note: right after a deploy the old revision answers for ~1 min (it returned 503 `not_configured` until traffic moved).
- 2026-11-03 — Final batch built (a-k), freeze reached. Live: explanations EN/TE/HI with code-checked numbers and links plus Listen; voice on web and WhatsApp (Transcribe takes WAV only, so notes are decoded with soundfile; WhatsApp voice tested offline only); sandbox pay (SAFE only, confirm, idempotency key, append-only audit table, lost on redeploy); SAM crop for fields, original for transcription; Privacy Mode on Baseten with Fireworks fallback (FIREWORKS_API_KEY not set yet, so the fallback is untested live); Muse Image card background with our text on top (metadata flags are the strings "false"); /eval, /privacy, icon, README, desktop redesign.
- 2026-11-03 — Evaluation on the 21 test items: product (Spark 1.3 low, judge minimal) 21/21, false SAFE 0/13, false alarms 0/8, p50 10.9 s, p90 17.2 s, $0.024 per check; expected evidence on 19/21. All sweep levels and Spark Open also 21/21. Honest limit: 0/13 still allows up to ~23% (rule of three). Sweep varied reading and agent effort, judge stayed low. Minimal looks faster and cheaper but was NOT adopted: that would be tuning on test; needs a dev run first.
- 2026-11-03 — Speed, 6 live checks, median before -> after: verdict 12.4 -> 12.1 s (no real change), first visible signal 6.8 s (new), explanation 17.0 -> 15.7 s. Judge minimal: dev 39/39, 0 false SAFE; adversarial no bad reason accepted, 2.4 -> 1.2 s. Meta caches only with prompt_cache_key (1265 of 1396 tokens). Reading is now the largest step, SAM adds ~3 s on images.
- 2026-11-03 — Hero stat: Rs 22,845 crore lost to cyber fraud in 2024, up 206% (MHA, Lok Sabha, July 2025; all cyber fraud, not bill scams alone). Batch spend about $5 of the $10 approved, by our estimate (includes Baseten at assumed rates); check dev.meta.ai. Open: BV to rate TE/HI explanations and new UI text; WhatsApp end-to-end once the app is published; user tests; min replicas -> 0 after Nov 8.
- 2026-11-03 — WhatsApp works end to end (real text from BV's phone, 17:36 UTC: message received, "Checking…" and verdict both sent, Graph 200; 29 s). Cause of the silence: the WhatsApp Business Account was not subscribed to our app (only Meta's "WA DevX Webhook Events 1P App" was); verifying the webhook and ticking "messages" does not do this. Fixed with POST /{WABA}/subscribed_apps. Token and number were fine. Images and voice notes on WhatsApp not yet tried live.
- 2026-11-03 — Effort test on the dev split, reading + agent + judge all minimal vs the product (low, judge minimal): 38/39 vs 39/39, false SAFE 0 vs 0, false alarm 1 vs 0 (reminder_hi_fibr_polite_disconnect: all checks passed, agent chose CAUTION), one question asked vs none, p50 13.8 vs 10.6 s, p90 21.4 vs 14.8 s, $0.016 vs $0.020 per check. **Product stays at low.** The two runs were hours apart and latency varies by time of day, so the speed gap is weak evidence; the point is that minimal did not show the gain the test-split sweep suggested.
- 2026-11-03 — WhatsApp live test by BV: a text message, a photo of a sample bill and a Telugu voice note all worked end to end ("Checking… ⏳" first, then the correct verdict each time). Nothing to fix. Numbers other than BV's are not yet tested.
- 2026-11-03 — Demo and submission prepared: `docs/DEMO_SCRIPT.md` (3:00, scenes with exact inputs and screens) and `docs/SUBMISSION.md` (form drafts). Script differs from §9 on purpose: amounts ₹1,243/₹4,243 as in the sample; "500 million" dropped (no source); bare voice question replaced by a line that can be checked. Demo uses the obviously fake 9000000003; `docs/TESTING.md` still uses the plausible 9123456780.
- 2026-11-04 — Overnight UI and polish batch, full report at the top of `docs/HANDOFF.md`. Verdict logic, risk rules, judge rules, `facts.py`, eval data and labels unchanged. New: comparison panel, values marked in the input, reasons with real values (evidence details now reach the screen by an allowlist, masked), amber early signal, judge-catch replay of a real recorded refusal, same-account tampered sample (₹1,240 vs ₹4,240, demo-only, in no split), short WhatsApp replies with DETAILS, `?demo=1`.
- 2026-11-04 — Early explanation when the floor is SCAM, from the code's findings only, shown after the verdict. 6 live scam checks, before -> after: verdict median 19.3 -> 21.1 s (no real change), explanation shown 33.3 -> 21.1 s. Checks ran at 15-30 s tonight, slower than the earlier 12 s; cause not established.
- 2026-11-04 — Sandbox audit log is durable: SQLite on Azure Files (`stbillsaathicin`, share `audit`, deploy step 13); survived a live restart. Checks and paused runs stay in memory, so max 1 replica still applies. Delete the account after Nov 8 if unused.
- 2026-11-04 — Open for BV: read the new TE/HI text; try the new WhatsApp replies on a real phone (mocked Graph API only so far); rehearse the spoken Telugu line (digits may come back as words); the voice sample is synthetic English because no Telugu voice was available and BV's own recording stays out of git.
- 2026-11-04 — **Correction: the judge never ran at `minimal`.** `Clients.judge_effort` was not passed to the agent, so every published result, including runs labelled "judge minimal" and the Nov 3 dev runs, used the judge at `low`. Now connected and set to `low`. Tested properly on dev (`dev_judge-minimal_2026-11-04_0832.jsonl`): 38/39, false SAFE 0, one false alarm (`reminder_hi_fibr_polite_disconnect`), no visible speed gain. Stays at `low`. The 11-03 file named `dev_judge-minimal` actually measured `low`; results files left unchanged.
- 2026-11-04 — Speed, 6 live checks by step (3 scam texts, 3 images): verdict median/p90 before 16.8/23.0 s, after 21.4/26.1 s, with no change to live behaviour between them. Same tokens as the Nov 3 eval but reading and agent take about twice as long, from Azure and from the dev machine alike, so the cause is model latency at this hour. Ruled out: cold replica (request accepted in 0.2-0.3 s, min replicas 1), explanation (never holds the verdict), Azure Files (only the pay step writes to it), judge effort. No safe fix applied. Open option: start the explanation early for SAFE and CAUTION too (shown 8-12 s after the verdict today).
- 2026-11-04 — Privacy Mode: all 14 sampled first turns answered in plain text; the existing retry then failed 3 of 14 (verdict written as JSON or leaked tool markup). The retry now requires `submit_verdict` (open-weight client only; judge and floor unchanged): 0 of 29 runs stopped without submitting. `required` for any tool was tried first and was much worse (tool loops). 3 of the 29 gave a stricter verdict than labelled, none false SAFE; 1 of 29 ended on 3 judge refusals (floor verdict). `/eval`'s Spark Open row predates this and was not re-run.
- 2026-11-04 — `/eval`, hero, README, submission show success counts: 13/13 risky not called SAFE, 8/8 genuine bills passed. Same results files. 19/21 kept; the 2 items are named on `/eval`: `scam_hi_cashback` (mainly a labelling expectation: no category hint, reading says "other", lookup is by category) and `scam_hi_mobile_phone` (one-off in that run). New TE/HI hero wording unreviewed. Deploy note: don't commit or run the web build during `deploy.ps1 -Step 5/8`; a tree that turns dirty or a new commit changes the tag between the steps and points the app at an image that doesn't exist (the old revision keeps serving).
- 2026-11-04 — Fail-closed tests (`api/tests/test_fail_closed.py`, 73) found that a toll-free or landline number, Indian-script digits or an uncommon domain ending could pass the reason check and the milestone check; forced with a scripted model, not seen in a real run. Fixed in `9ccd24d`, stricter only (`app/contacts.py`). The mock registry already had official helplines. No verdict or finding changed on 60 dataset items, 12 TESTING.md messages, 8 demo samples. Not covered: contacts in words or "dot", landlines without 0 or +91.
- 2026-11-04 — Challenge set: 20 new cases, frozen (`93602a2` pushed first), run once on local code `4c75264`, Spark 1.3 low, judge low: 20/20 verdicts, 19/20 with every finding, $0.418, p50 14.9 s. Finding: a phone number in Hindi words stayed in words, so the known-scam match did not fire; still SCAM on other evidence. `docs/CHALLENGE_RESULTS.md`, `docs/CLAIMS_AND_EVIDENCE.md`, `docs/SUBMISSION_PASTE.txt`, `docs/YOUTUBE.md`.

## 12. How to work with BV (the builder)

- Diagnose first, propose, and get explicit approval before implementing anything non-trivial.
- One step at a time; explain what a command does before asking BV to run it.
- Windows + PowerShell commands. Never print, log or commit secret values.
- Production-grade, fintech-level quality over shortcuts — but respect the schedule in §8.
