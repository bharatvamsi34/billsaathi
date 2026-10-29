# BillSaathi agent design

Design for the verification agent, written on Day 2 (2026-10-28) and built on Day 3. The
verification patterns follow the ideas taught in Meta's *Agents 101* workshop; we learned the
pattern only and copied no code.

**Core idea: the model proposes, the code verifies.** The model decides which tools to call and
how to explain the result, but every safety rule runs inside our code at fixed points the model
cannot skip.

## 1. Where the agent sits

```
capture -> isolate (SAM 3.1) -> extract (Spark 1.3, validated JSON + visible text)
        -> MILESTONE CHECK: every link / UPI ID / mobile number in the text must be a destination
        -> AGENT LOOP: model calls tools (several per turn, run in parallel); every result is recorded
        -> submit_verdict (deterministic checks, then an LLM claims judge; may be refused)
        -> explain in the user's language (facts from app/facts.py only)
        -> USER SIGN-OFF: nothing is paid without the user's explicit confirmation
        -> act (sandbox pay / report & share)
```

Extraction (`app/extract`) only reads. The agent receives the extracted fields, the raw message
text (or the text extraction saw in the image), the destinations to check, and the user's language.

## Verification layers

Each layer can only make the outcome stricter; none can turn a risky request into SAFE.

1. **Deterministic checks** (code, no model): citations exist, every destination checked, never
   below the risk-engine floor, SAFE only if every hard check passed, facts only from the
   constants file.
2. **LLM judge (claims check)**: one Spark 1.3 call checks that each reason is actually supported
   by the evidence it cites. It can only refuse; it cannot change the verdict or the floor.
3. **Milestone check** (code): after extraction, every link, UPI ID and mobile number found in the
   text must be among the destinations, so a model that "forgets" a link cannot skip checking it.
4. **Three tries**: a refused `submit_verdict` comes back to the agent with the reason; it may try
   again up to 3 times.
5. **Forced CAUTION**: after the third refusal, or any limit or outage, the verdict is CAUTION (or
   the risk-engine floor if that is stricter, e.g. SCAM) — never SAFE.
6. **User sign-off**: the final sign-off is the user. No payment ever happens without the user's
   explicit confirmation, even on SAFE.

Meta's guidance in the Agents 102 (verification) session is that finance needs a 100% threshold:
a partial pass is a fail. That is why SAFE requires **every** check to pass, and why every
uncertain path (failed tool, low confidence, judge unavailable, limit reached) ends in CAUTION.

## 2. Building blocks (types already built on Day 2)

| Type | Module | Role |
|---|---|---|
| `ToolResult` | `app/agent/evidence.py` | One tool call: `tool`, `call_id`, `args`, `ok`, `error`, `evidence`, `data`. Tools never raise. |
| `ToolEvidence` | `app/agent/evidence.py` | One finding: stable `evidence_id`, `code` (`EvidenceCode`), `source` (tool), `summary`, `detail`. |
| `EvidenceRecord` | `app/agent/evidence.py` | Append-only log of one run. `evidence(id)` returns only evidence produced in *this* run. |
| `RecordEntry` | `app/agent/evidence.py` | Frozen entry: `seq`, `kind` (`tool_result`, `refusal`, `ask_user`, `user_reply`, `verdict`, `note`), `at`, `payload`. |
| `Tool.spec()` | `app/agent/tools/base.py` | Function-calling definition generated from each tool's typed arguments. |
| `Fact` / `verified_fact()` | `app/facts.py` | Checked facts (e.g. helpline 1930). Unverified facts are unusable. |
| `LLMClient` | `app/models/base.py` | One interface for Meta and (Day 6) Baseten. |

Day 3 adds `AgentRun`, `SubmitVerdictArgs`, `Refusal`, `FinalVerdict`, the risk engine
(`app/risk/`) and the loop (`app/agent/loop.py`).

## 3. The tools the model can call

- **Verification tools (built):** `lookup_biller`, `fetch_bill`, `check_payment_destination`,
  `get_bill_history`, `match_scam_patterns`.
- **`ask_user`** — pause and ask the user for ONE missing item (section 6).
- **`submit_verdict`** — the only way to finish a run (section 4).

Every tool result, including failures, is appended to the evidence record before the model sees it.

- **Parallel calls:** the model may request several tools in one turn; verification tools are pure
  functions, so they run in parallel and are recorded in the order the model requested them. The
  system prompt asks for all independent checks in the first turn (`lookup_biller`,
  `check_payment_destination` for every destination, `match_scam_patterns`), then `fetch_bill` and
  `get_bill_history` once the biller is known, then `submit_verdict`.
- **Tool allowlist:** a call to any name outside the registry is refused, recorded
  (`kind="refusal"`, rule `unknown_tool`) and sent back to the model as feedback. It counts toward
  the tool-call limit.

## 3b. Milestone check after extraction

Deterministic, no model. The raw text (or extraction's transcription of the image) is scanned with
regular expressions for every URL, UPI ID and Indian mobile number. Any one that is not among the
extracted destinations is added to the destinations and recorded as a `MISSED_BY_EXTRACTION`
evidence item (source `milestone_check`), so check 2 forces the agent to check it.

## 4. `submit_verdict`: verification at a fixed point

Arguments:

```json
{
  "verdict": "SAFE | CAUTION | SCAM",
  "reasons": [{"text": "The link imitates the official site.", "evidence_ids": ["ev_3f2a9c1d07"]}],
  "facts": ["cybercrime_helpline"]
}
```

The code runs these checks in order. The first one that fails produces a **refusal**:

1. **Citations exist in this run.** Every reason has at least one `evidence_id`, and every id is
   found by `record.evidence(id)`. Invented or reused-from-another-run ids are refused.
2. **Every destination was checked.** Each payment destination from extraction has a
   `check_payment_destination` result in the record. The model cannot skip a link.
3. **The hard-rule floor holds.** The risk engine computes a floor verdict from *all* evidence in
   the record (policy below). The submitted verdict may be equal or stricter
   (SAFE < CAUTION < SCAM), never weaker. The LLM may raise risk, never lower it.
4. **SAFE needs every hard check passed.** SAFE is accepted only if the record contains
   `BILLER_VERIFIED`, `AMOUNT_MATCHES_BILLER`, `AMOUNT_WITHIN_HISTORY`, an official result for
   every destination, no failed tool call, and extraction confidence ≥ 0.8 for amount and
   destinations.
5. **Facts come from the constants file.** `facts` may only list keys whose `verified_fact(key)`
   exists. Reasons may not contain phone numbers or links other than ones present in cited
   evidence; user-facing numbers like 1930 are inserted by our renderer from `app/facts.py`,
   never typed by the model.

6. **Claims check (LLM judge)** — runs only after checks 1–5 all pass. One Spark 1.3 call at
   `low` effort receives only the proposed reasons and the detail of each evidence item they cite,
   and returns `{supported: bool, why}` per reason. Any unsupported reason is a refusal carrying
   the judge's feedback. The judge can only refuse; it never changes the verdict or the floor. Its
   JSON is validated strictly (one answer per reason); if the call fails or the output is invalid,
   the submission is refused (fail closed).

A refusal is appended to the record (`kind="refusal"`) and returned to the model as the tool's
result, with the rule that failed and what to fix, for example:

```json
{"accepted": false, "rule": "citations_exist",
 "message": "Reason 2 cites ev_9a1b2c3d4e, which no tool produced in this run. Cite an evidence_id from a tool result."}
```

### Refused three times
After the third refusal the loop stops and the final verdict is **CAUTION — "could not verify, do
not pay yet"**, never SAFE (or the risk-engine floor if that is stricter, so a run with lookalike
evidence still ends as SCAM). The record gets a `verdict` entry with `forced: true` and the list of
refusals, so the UI and audit log show why.

### Verdict policy (the risk engine's floor)
Same policy as the labelled dataset (`data/synthetic/README.md`):

- **SCAM** — `LOOKALIKE_DOMAIN`, `LOOKALIKE_VPA`, `KNOWN_SCAM_DESTINATION` or `APK_LINK`; or
  `DESTINATION_NOT_OFFICIAL` together with scam phrasing (`DISCONNECTION_THREAT`,
  `KYC_UPDATE_LURE`, `REFUND_LURE`).
- **SAFE** — only as in check 4.
- **CAUTION** — everything else, including any failed tool call (`ok=false`) and any check that
  was not done.

## 5. Loop limits

- At most 8 tool calls per run, plus at most 1 `ask_user` and 3 `submit_verdict` attempts.
- Per-call timeouts come from the model client; a model outage ends the run as CAUTION.
- Hitting a limit ends the run as CAUTION ("could not verify"), recorded with the reason.
- Every run records model turns, judge calls, tool calls, refusals, latency and cost.
  **Target on Spark 1.3 at `low` effort: ≤ 3 agent model turns and ≤ 10 s per run** (image
  extraction excluded).

## 6. `ask_user`: one question, then resume

When a check needs a value extraction could not read (typically the consumer number on a
blurred photo), the model calls:

```json
{"field": "consumer_number", "question": "బిల్లుపై ఉన్న సర్వీస్ నంబర్ ఏమిటి?"}
```

- `field` must be one of `consumer_number`, `amount`, `biller_name`, `payment_destination`.
- The run pauses with status `needs_user_input`; the record (`kind="ask_user"`) and the model
  conversation are saved under the run id.
- The user's reply is appended (`kind="user_reply"`), validated (e.g. consumer-number format for
  the biller), and the loop resumes. The model then calls the normal tools with the new value.
- Only one question per run. A second `ask_user` is refused; if the user does not answer, the
  run ends as CAUTION.

## 7. The evidence record powers the UI and the audit log

- **Live step-by-step UI:** each new `RecordEntry` is streamed to the web app (server-sent
  events), so users see "Checked biller → Checked link → Found lookalike…" as it happens.
- **Audit log:** entries are written as append-only rows with consumer numbers and phone numbers
  masked (`app/pii.py`). The verdict row stores the cited `evidence_id`s, so every decision can be
  traced back to the tool result behind it.

## 8. Testing with a scripted fake model (zero API calls)

A `ScriptedModel` implements the same client interface and returns a fixed sequence of steps
(tool calls or a `submit_verdict`). Every safety rule is tested without network access:

| Scenario | Expected |
|---|---|
| Genuine bill, all checks pass, SAFE with valid citations | accepted SAFE |
| Reason cites an invented `evidence_id` | refused (`citations_exist`) |
| SAFE submitted after `AMOUNT_MISMATCH` | refused (`hard_rule_floor`) |
| SAFE submitted with a destination never checked | refused (`destinations_checked`) |
| CAUTION submitted when evidence says SCAM | refused (`hard_rule_floor`) |
| Unknown fact key, or a phone number typed into a reason | refused (`facts_verified`) |
| Three refusals in a row | final CAUTION, `forced: true` |
| A tool returns `ok=false` | SAFE impossible; floor is CAUTION |
| `ask_user` then reply | pauses, resumes, verdict uses the new value |
| Second `ask_user` | refused |
| More than 8 tool calls | run ends as CAUTION |
| Several tools in one turn | all run; recorded in requested order |
| Call to a tool not in the registry | refused (`unknown_tool`), recorded, fed back |
| Judge says a reason is unsupported | refused (`claims_check`) with the judge's feedback |
| Judge call fails or returns invalid JSON | refused (fail closed) |
| Scam SMS where extraction "forgets" the link | milestone check adds it; SAFE impossible until checked |

The same 60-item dataset then runs end to end with scripted models that call the tools on each
item's ground-truth fields, and the final verdicts must equal the labels before any live model
evaluation.

## 9. Privacy Mode

The loop is provider-neutral. Privacy Mode swaps the Meta client for the Baseten client
(Muse Spark Open, open weights); tools, checks, refusals and the evidence record are unchanged.
