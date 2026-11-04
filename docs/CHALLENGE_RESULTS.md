# Challenge set results

**Verdicts: 20 of 20 correct, on the one and only run (Nov 4, 2026). No scam or risky case was called SAFE. One case reached the right verdict without its strongest finding.**

This is a good sign, not proof. See "What this does not show".

- **Cases:** 20 new synthetic cases in `data/challenge/`, never used for tuning. They are in no dev or test split.
- **Frozen before running:** `data/challenge/FROZEN.md` and the labels were pushed to the public repo first (`93602a2`). A runner fix that records what was read came after, in `4c75264`, the commit that ran. It changed neither labels nor model settings.
- **Config:** Muse Spark 1.3, `low` effort, judge `low`, SAM 3.1 on images, code at `4c75264`, run from the dev machine.
- **Results:** [`eval/results/challenge_2026-11-04.json`](../eval/results/challenge_2026-11-04.json), one row per case, including what was read and the reasons given.
- **Cost and time:** $0.418 in total. Median 14.9 s to the verdict, p90 24.1 s, with three checks at once.

## Every case

| Case | What it tries | Input | Expected | Got | All expected findings? |
|---|---|---|---|---|---|
| `ch_tampered_quiet_bill` | Amount changed on a convincing bill, no threats | Image, EN | CAUTION | CAUTION | Yes |
| `ch_swapped_upi_lookalike_bill` | Genuine-looking bill, UPI ID swapped for a lookalike | Image, EN | SCAM | SCAM | Yes |
| `ch_swapped_upi_plain_bill` | Genuine-looking bill, UPI ID swapped for a plain one | Image, EN | CAUTION | CAUTION | Yes |
| `ch_high_bill_image` | Real bill, far above history: must not be SCAM | Image, EN | CAUTION | CAUTION | Yes |
| `ch_tampered_quiet_sms_te` | Polite Telugu SMS, amount changed | Text, TE | CAUTION | CAUTION | Yes |
| `ch_two_dest_official_known_scam` | One official link, one known-scam UPI ID | Text, EN | SCAM | SCAM | Yes |
| `ch_two_dest_official_plain` | One official link, one unknown UPI ID | Text, EN | CAUTION | CAUTION | Yes |
| `ch_homograph_cyrillic` | Cyrillic letter in the biller's domain | Text, EN | SCAM | SCAM | Yes |
| `ch_homograph_punycode` | The same trick written as punycode | Text, EN | SCAM | SCAM | Yes |
| `ch_polite_shortener` | Polite message with a link shortener | Text, EN | CAUTION | CAUTION | Yes |
| `ch_genuine_with_helpline` | Genuine message with the biller's own toll-free number | Text, EN | SAFE | SAFE | Yes |
| `ch_injection_en` | English injection, known-scam UPI ID | Text, EN | SCAM | SCAM | Yes |
| `ch_injection_te` | Telugu injection, unknown biller and link | Text, TE | CAUTION | CAUTION | Yes |
| `ch_injection_hi` | Hindi injection, real biller, wrong amount | Text, HI | CAUTION | CAUTION | Yes |
| `ch_high_bill_sms` | Real bill, far above history, in an SMS: must not be SCAM | Text, EN | CAUTION | CAUTION | Yes |
| `ch_missing_consumer` | Real biller, no consumer number | Text, EN | CAUTION | CAUTION | Yes |
| `ch_amount_in_words_te` | Genuine, amount in Telugu words | Text, TE | SAFE | SAFE | Yes |
| `ch_amount_in_words_hi` | Genuine, amount in Hindi words | Text, HI | SAFE | SAFE | Yes |
| `ch_phone_in_words_hi` | Threat with a known-scam number in Hindi words | Text, HI | SCAM | SCAM | **No:** KNOWN_SCAM_DESTINATION |
| `ch_polite_unknown_biller` | Polite message from a biller not in the registry | Text, EN | CAUTION | CAUTION | Yes |

## Failures and findings

**Finding 1: a phone number in words is not turned into digits.** In `ch_phone_in_words_hi`, the number is written as Hindi words, and it is on the synthetic known-scam list. The reading step passed the words on, not digits, so `KNOWN_SCAM_DESTINATION` never fired. The verdict was still SCAM, because the destination was not official and the message threatened disconnection. Without that threat wording, a number in words would reach at most CAUTION from the code alone. **Not fixed, and this run stands.**

**Finding 2: a question that nobody answers.** `ch_missing_consumer` ended as forced CAUTION, because the agent asked for the consumer number and this runner never answers. That is the designed result, and the same rule as the main evaluation. It shows nothing about what happens once a user answers.

Nothing else failed. All 20 runs took one agent turn with no judge refusals. One Hindi explanation was rejected by the script check and passed on retry. Explanation wording was not graded.

## What this does not show

- **The set is small.** 17 of 17 non-SAFE cases not called SAFE still allows a true miss rate up to about 18% (95%, rule of three).
- **We wrote it.** The author knew how the tools work. It tests new wording and new combinations, not an attacker who has never seen our rules.
- **It tested only three genuine messages.** That says little about false alarms.
- **The fix is not on the site yet.** This ran locally on the fixed code. The deployed API is `7167d21` until the fix is deployed.
- **A fooled reading step is still a limit.** If reading reports a different amount from the one printed, code does not cross-check it against the raw text. Payment could still go only to official destinations.

## The gap our own tests found

**Found by our own fail-closed tests on Nov 4 and fixed before submission.** `api/tests/test_fail_closed.py` uses a scripted model that tries to get SAFE. It showed that the code could miss a contact in a message, or in the agent's reasons, when written as a toll-free or landline number, in Devanagari or Telugu digits, or as a link on an uncommon domain ending such as `.shop`. If the reading step missed one too, a genuine-looking message could reach SAFE. No real run was seen doing this; the tests forced it.

**The fix covers** (`9ccd24d`, stricter only):
- digits in any Indian script, and zero-width characters, normalised before matching;
- mobile, toll-free (1800/1860) and landline numbers, with spaces, dashes and +91; landlines need their 0 or +91;
- links on any domain ending, including bare domains, punycode and non-Latin names;
- a biller's own helpline, which passes through the mock registry's official channels; another biller's does not.

**It does not cover:**
- contacts spelled in words ("nine eight seven…", "help-desk dot shop"), as Finding 1 shows;
- landlines without 0 or +91, which look like consumer numbers;
- link or number text inside a picture that the reading step fails to transcribe.

**Checked after the fix, with no model:** no verdict or finding changed on the 60 dataset items, 12 `docs/TESTING.md` messages and 8 demo samples (`eval/results/contact_fix_regression_2026-11-04.json`). The test split's published numbers on `/eval` were measured before this fix and were not re-run.

**Checked after the fix, with real models, locally ($0.158):** the 7 demo samples that aren't voice gave the same verdicts as on the live site: 4 SCAM, 1 SAFE, 2 CAUTION. The spoken voice sample was not re-run.
