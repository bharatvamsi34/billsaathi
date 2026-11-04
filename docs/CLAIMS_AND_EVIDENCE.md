# Claims and evidence

Every factual claim in `README.md`, `docs/SUBMISSION.md` and `docs/DEMO_SCRIPT.md`, with what proves it. Checked on Nov 4, 2026. Where the three documents repeat a claim, it appears once.

- **Verified:** a test, results file, code or dated record shows it.
- **Partial:** true as far as shown, with a stated limit.
- **Unverified:** nothing here proves it. Don't lean on it.

"Docs" says where the claim appears: **R** README, **S** SUBMISSION, **D** DEMO_SCRIPT.

## Corrected while building this table

| Was | Now | Why |
|---|---|---|
| "638 API tests" (S) | 748 | Count was out of date |
| "zero of thirteen risky requests called SAFE" (D, voiceover) | "thirteen of thirteen risky requests not called SAFE" | Matches what `/eval` now shows |
| "About 1 run in 4, Spark Open stopped without submitting" (D) | Fixed on Nov 4; 0 of 29 | Out of date |
| "Any link, UPI ID or mobile number" (R) | "phone number" | Wider since the Nov 4 fix |
| "Checks took 15 to 30 seconds overnight" (D) | Today's measured figures | More precise |
| One line said "the biller's records" (S) | "simulated biller records in this demo" | The records are simulated |

The README's opening line still says "the biller's records". The next section there states exactly what is simulated.

## Origin and data

| # | Claim | Docs | Evidence | Status |
|---|---|---|---|---|
| 1 | Built during the event in a public repo | R S D | `git log`: first commit Oct 27, 2026 | Verified |
| 2 | Nothing pre-existing apart from public libraries | R S D | The history starts from an empty repo. A history cannot prove a negative | Partial |
| 3 | Written with Claude Code as a coding assistant | S | Commit trailers | Verified |
| 4 | All billers, bills and test data are synthetic | R S D | `data/synthetic/README.md`; `Label.synthetic` is always true; `.example` domains | Verified |
| 5 | Not connected to real BBPS; no real money moves | R S D | `api/app/bbps_mock/`; `api/app/payments.py` calls no payment network | Verified |
| 6 | ₹22,845 crore lost in 2024, up 206%, MHA, Lok Sabha, July 2025 | R S D | Source re-read Nov 4: Rs 22,845.73 crore, nearly 206%, written reply, July 22, 2025 | Verified |
| 7 | About US$2.7 billion | D, cards | Our conversion at about ₹85 per dollar, not in the source | Partial |
| 8 | The figure is all cyber fraud, not bill scams alone | R S D | Same source | Verified |
| 9 | "Fake bills are one common route" | R S | Our framing. The source does not break losses down | Unverified |
| 10 | "Messages like this reach Indian families" | S D | General knowledge. No study cited | Unverified |

## Measured results

| # | Claim | Docs | Evidence | Status |
|---|---|---|---|---|
| 11 | Test split: 21/21 correct, 13/13 risky not called SAFE, 8/8 genuine passed | R S D | `eval/results/test_spark-low_2026-11-03_0021.jsonl`, `eval/metrics.py`, `api/tests/test_eval_metrics.py` | Verified, before the Nov 4 fix |
| 12 | 19/21 had every expected finding; the 2 named | R D | Same file; `/eval` | Verified |
| 13 | 13/13 allows a true miss rate up to about 23% | R S | Rule of three: 3/13 | Verified |
| 14 | Median 10.9 s, p90 17.2 s, $0.024 per check | R S D | Same file | Partial: true for that run. Live on Nov 4: median 16.8 and 21.4 s, p90 23.0 and 26.1 s, same code |
| 15 | Effort sweep and Spark Open rows | R S | `eval/results/test_*` | Verified. The Spark Open row predates the Nov 4 retry fix |
| 16 | Judge at `low` in every published row | R | `Clients.judge_effort` was never connected until `a08282e` | Verified |
| 17 | `minimal` not adopted: 38/39 each, no faster | S | `dev_all-minimal_2026-11-03_2302.jsonl`, `dev_judge-minimal_2026-11-04_0832.jsonl` | Verified. Runs were hours apart, so the speed gap is weak evidence |
| 18 | Prompts and rules tuned on dev only | R S | `CLAUDE.md` §11; no prompt change cites a test item | Partial: a process record. The Nov 4 fix came from fail-closed tests, not from test items |
| 19 | Challenge set: 20/20 verdicts, 19/20 with every expected finding | S | `eval/results/challenge_2026-11-04.json`, `docs/CHALLENGE_RESULTS.md`, `data/challenge/FROZEN.md` | Verified, on the fixed code locally |
| 20 | Fail-closed tests: 73 | S | `api/tests/test_fail_closed.py` | Verified |
| 21 | No verdict changed from the fix on 80 inputs | S | `eval/results/contact_fix_regression_2026-11-04.json`, `eval/regression/` | Verified, with no model |
| 22 | 748 API tests | S | `pytest` | Verified |
| 23 | "Cheap enough": about $0.024 per check is close to viable | S | The cost is measured. "Viable" is our judgment | Partial |

## Verification and safety

| # | Claim | Docs | Evidence | Status |
|---|---|---|---|---|
| 24 | Fixed checks run before the agent's first turn, and cannot be skipped | R S | `test_mandatory_checks_cannot_be_skipped` | Verified |
| 25 | A link or number reading missed is still checked | R S | `test_milestones.py`, `test_contact_the_reading_step_missed_blocks_safe` | Verified, except contacts in words |
| 26 | Cropping cannot hide a link | R S | `test_fields_read_the_crop_but_transcription_reads_the_original` | Verified |
| 27 | Citations must exist in this run | R S | `test_invented_evidence_id_is_refused_then_fixed` | Verified |
| 28 | No model can turn a risk into SAFE | R S D | `test_safe_after_amount_mismatch_is_refused`, `test_fail_closed.py`, `test_risk.py` | Verified for evidence the checks found. A fooled reading step can change what they see: `docs/CHALLENGE_RESULTS.md` |
| 29 | SAFE needs every check to pass | R S | `safe_requirements`, `test_failed_tool_makes_safe_impossible` | Verified |
| 30 | Judge can only refuse, and fails closed | R S | `test_judge_fails_closed` | Verified |
| 31 | Judge catches bad reasons | S D | `eval/results/judge_adversarial.json`: 0 of 24 bad reasons accepted, 1 good one refused | Partial: small set |
| 32 | Three refusals, outage or limit ends CAUTION or the floor | R S | `test_three_refusals_force_caution_never_safe`, `test_model_outage_ends_as_caution` | Verified |
| 33 | Registry failure is never SAFE | S | `test_registry_failure_is_never_safe` | Verified, simulated by errors. The mock registry runs in-process, so a real network hang was not tested |
| 34 | Prompt injection is treated as data | S | `test_injected_wording_never_reaches_the_agent_or_the_judge`, 3 live challenge cases | Partial: the agent and judge never see the wording, but the reading step does |
| 35 | Explanations: code rejects numbers and links not in evidence | R | `test_invented_details_are_rejected`, `test_invented_contact_in_an_explanation_is_rejected` | Verified |
| 36 | Helpline numbers come only from a vetted list | R | `api/app/facts.py`, verified by BV; `test_unverified_facts_and_typed_numbers_are_refused` | Verified |
| 37 | Replay of a real run where "tonight" was refused | S D | `eval/results/agent_live_2026-10-29_2355.jsonl`, `web/src/replay.generated.json` | Verified |
| 38 | Append-only audit table with triggers | R S | `test_the_database_refuses_changes_to_the_audit_log` | Verified |
| 39 | Idempotent simulated payment with confirmation | R S | `test_same_key_returns_the_same_receipt_and_never_pays_twice`, `test_confirmation_and_key_are_required` | Verified |
| 40 | Audit log survives restarts | R | `test_audit_history_survives_a_restart`; live restart, Nov 4 | Verified |
| 41 | Contributor models are refused | R | `test_contributor_models_are_refused` | Verified |

## Meta products and partners

| # | Claim | Docs | Evidence | Status |
|---|---|---|---|---|
| 42 | Spark 1.3 reads, runs the agent, judges, explains | R S | `api/app/pipeline.py`; results files | Verified |
| 43 | SAM 3.1 crops with concept "document", IoU 0.98 | R S | `test_vision.py`; `api/spike/results/` | Verified |
| 44 | Voice Transcribe always sends `languageBias` | R S | `test_language_bias_is_always_sent` | Verified |
| 45 | Code-mixed Telugu clip exact with `languageBias` | S | `api/spike/results/`; `FEEDBACK.md` | Verified, one clip |
| 46 | Telugu rated 4/5, Hindi about 4/5 on early samples | R S | BV's rating, `CLAUDE.md` §4 | Verified as a record. The Hindi is not a native rating. Newer UI text unreviewed |
| 47 | Muse Image: fixed prompt, no user data, tools off | R S | `test_every_model_tool_is_off_and_the_prompt_has_no_user_data` | Verified |
| 48 | Privacy Mode makes no call to Meta's Model API | R S D | `test_privacy_mode_never_touches_the_normal_clients` | Verified in tests |
| 49 | Refused rather than sent to Meta if no provider | S | `test_privacy_mode_without_a_provider_is_refused_not_downgraded` | Verified |
| 50 | Fireworks fallback built, untested live | R S | `test_failover_uses_the_second_provider_when_the_first_fails` | Verified as stated |
| 51 | Baseten: 21/21; native script Tamil 0.81, Hindi 0.88 | S | `test_open_*.jsonl`; `FEEDBACK.md`; spike results | Verified |
| 52 | Each step has a model badge | S D | `web/src/components/ModelBadge.tsx`; screenshots | Verified |
| 53 | Platform feedback items | S | `FEEDBACK.md`, with steps | Verified as reported; some were reported by BV and not re-run |

## Channels and interface

| # | Claim | Docs | Evidence | Status |
|---|---|---|---|---|
| 54 | Web app and API deployed | R S | Health endpoint; live smoke, Nov 4 | Verified |
| 55 | WhatsApp text, photo, voice note work end to end | R S D | BV's live test, Nov 3, `CLAUDE.md` §11 | Partial: BV's number only. A test number accepts only allow-listed numbers |
| 56 | Short WhatsApp replies and DETAILS | S D | `test_whatsapp.py`, mocked Graph API | Partial: not recorded on a real phone |
| 57 | Explanations and UI in English, Telugu, Hindi | R S | `test_explain.py`; live flows | Verified. New Telugu and Hindi text unreviewed |
| 58 | "which it can read aloud" (Listen) | S D | Button exists | Unverified: audio output never tested by us |
| 59 | Spoken Telugu voice check ends SCAM | D | Tested as text only | Unverified: rehearse it |
| 60 | Rate limits: 10 a minute, 5 on WhatsApp; $5 daily cap | D | `test_rate_limit_per_ip`, `test_rate_limit_per_sender`, `test_daily_spend_cap_returns_service_busy` | Verified |
| 61 | Questions expire after 10 minutes | S | `whatsapp_question_ttl_seconds`, `check_ttl_seconds` | Verified |
| 62 | Works on a phone | R S | Chrome's phone emulation only | Partial: no real-phone run recorded by us |
| 63 | Real bill ends CAUTION | R S | Design: unknown biller is a hard fail | Verified for a biller not in the registry. No real bill was used, by rule |
| 64 | Ireesha Infosol will keep building it | D | BV's statement of intent | Unverified: BV's to make |
| 65 | User testing | — | **None recorded.** No document claims any | — |
