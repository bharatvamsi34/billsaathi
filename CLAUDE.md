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

> Day-1 spike (§8) verifies each model ID, input type, latency and output quality before we commit. Update this table with real findings.

| Model | Access | Job in BillSaathi |
|---|---|---|
| **Muse Spark** (Meta Model API) | `META_API_*` | Primary agent brain: vision extraction from bill images/screenshots → structured JSON; tool-calling verification agent; verdict reasoning |
| **Muse Wonder** (`muse-wonder-1.0`, seen in playground) | `META_API_*` | Compare vs Spark in spike; use whichever is better for extraction or for multilingual explanations |
| **SAM 3.1** (Meta Model API, "Segment") | `META_API_*` | Isolate the bill/document from a cluttered phone photo before extraction; also highlight suspicious regions (e.g. payment link, QR) on the image in the UI |
| **Muse Voice Transcribe** (Meta Model API, "Audio") | `META_API_*` | Voice input: user asks "kya ye bill sahi hai?" or forwards a voice note |
| **Muse Image** (Meta Model API) | `META_API_*` | Optional / low priority: generate an explainer visual of the scam pattern for the share card. Only if time allows. |
| **Muse Spark Open** (open weights via Baseten, `meta-models/muse-spark-open-1026`) | `BASETEN_API_KEY` | **Privacy Mode**: full pipeline on the open-weight model (supports vision + audio, always reasons). Targets *Best Build on Open-Weight Models* ($10k). |
| Modal (if credits granted) | `MODAL_*` | Run the evaluation harness at scale in Sandboxes; optional self-hosted open-weight endpoint |

Baseten: OpenAI-compatible, `base_url="https://inference.baseten.co/v1"`, model **exactly** `meta-models/muse-spark-open-1026`. Output includes reasoning — parse the final answer separately from reasoning content.
Meta Model API: copy base URL + request format from dev.meta.ai → Chat → **Get code**. Do not guess endpoints.

## 5. Product scope

### 5.1 Core flow (MUST ship — this alone must be demo-worthy)

1. **Capture** — camera photo / upload of a bill, screenshot of SMS/WhatsApp, pasted text, or voice note.
2. **Isolate** — SAM 3.1 crops the document from the photo (fallback: use original image).
3. **Extract** — vision model → validated JSON: biller name, biller category, consumer/account no., amount, due date, bill date, payment destination (UPI VPA, URL, phone, QR text), language, urgency language, and **per-field confidence**.
4. **Verify (agent with tools)** — the agent decides which tools to call:
   - `lookup_biller(name, category)` → mock BBPS biller registry (fuzzy match, official biller ID)
   - `fetch_bill(biller_id, consumer_no)` → mock BBPS bill fetch (amount/due date the biller actually has)
   - `check_payment_destination(vpa|url|phone)` → official-channel allowlist + known-scam list + lookalike-domain detection
   - `get_bill_history(biller_id, consumer_no)` → last 6 bills for spike detection
   - `match_scam_patterns(text)` → library of known Indian bill-scam patterns (disconnection threats, "update KYC", personal mobile numbers, APK links, short URLs)
5. **Decide** — two-layer risk engine:
   - **Hard rules (deterministic, cannot be overridden by the LLM):** unknown biller, payment destination not official, amount mismatch vs biller fetch, known scam domain/VPA → minimum verdict CAUTION or SCAM.
   - **LLM reasoning layer** adds context and soft signals; may raise risk, may **never lower** a hard-rule verdict.
   - Verdict: **SAFE / CAUTION / SCAM**, with evidence list (each reason cites the tool result it came from).
6. **Explain** — plain-language verdict in the user's language (English, Hindi, Marathi at minimum; add Telugu/Tamil if spike shows quality). Browser speech synthesis reads it aloud.
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

| Day | Date | Goal | Done when |
|---|---|---|---|
| 1 | Tue Oct 27 | Repo + **model spike** + skeleton deploy | Public repo created; each Meta model called from Python with a sample bill/voice clip; findings recorded in §4; FastAPI "hello" deployed to Azure Central India |
| 2 | Wed Oct 28 | **Data + mock BBPS + extraction** | 60–80 labelled synthetic items (genuine bills, scam SMS/WhatsApp, tampered bills) across 6–8 billers & 3 languages; mock BBPS endpoints live; extraction returns validated JSON with confidences |
| 3 | Thu Oct 29 | **Agent + risk engine** | Agent calls tools autonomously; hard rules + LLM layer merged; safety invariants tested; CLI run over full dataset |
| 4 | Fri Oct 30 | **Web app core flow** | Capture → progress steps (show agent's tool calls live) → verdict card with evidence → explanation, on a phone |
| 5 | Sat Oct 31 | **Languages, voice, act** | Hindi/Marathi/English explanations; voice question via Muse Voice Transcribe; sandbox pay with confirmation + audit; SAM 3.1 crop + highlight |
| 6 | Sun Nov 1 | **Prod deploy + eval + privacy mode** | Full stack live on Azure; eval harness produces metrics page; Privacy Mode on Baseten end-to-end |
| 7 | Mon Nov 2 | **WhatsApp bot (stretch) + polish** | Forward → verdict reply works on test number. **Feature freeze at midnight.** |
| 8 | Tue Nov 3 | **Harden + story** | Edge cases, error states, README with architecture + metrics, demo script rehearsed, draft video recorded |
| 9 | Wed Nov 4 | **Ship** | Final 3-min video, submission done by 9 PM IST, X post for Most Viral, all links verified in an incognito window |

**Rule:** if a day slips, cut from §5.2 bottom-up (Family protect → WhatsApp → Privacy Mode). Never cut deployment, tests on safety invariants, or demo quality.

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

## 12. How to work with BV (the builder)

- Diagnose first, propose, and get explicit approval before implementing anything non-trivial.
- One step at a time; explain what a command does before asking BV to run it.
- Windows + PowerShell commands. Never print, log or commit secret values.
- Production-grade, fintech-level quality over shortcuts — but respect the schedule in §8.
