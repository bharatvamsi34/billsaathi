# BillSaathi synthetic evaluation set

**Everything here is synthetic.** Billers, consumers, bills, domains (`*.example`), UPI IDs
(`@demobank`, `@okdemo`) and phone numbers are fictional. The biller data comes from our
**mock** BBPS service (`api/app/bbps_mock`), which is not connected to BBPS/NPCI.

## Contents

60 labelled items in `labels.jsonl` (format: `app.schemas.Label`), 27 of them images in `images/`.

| Group | Items | Notes |
|---|---|---|
| Genuine bills | 12 | 8 billers, 2 layouts, English / Hindi / Telugu headings; 4 as tilted phone photos |
| Tampered bills | 8 | 6 amount changes (3 large, 3 subtle), 2 swapped UPI IDs (one lookalike, one plain) |
| Scam messages | 24 | 8 each in English, Telugu, Hindi (incl. Hinglish); disconnection, KYC/APK, refund, fake bill, short link, known-scam UPI, personal number; 6 as SMS/WhatsApp screenshots |
| Genuine reminders | 12 | 4 per language; 3 politely mention disconnection but are SAFE |
| Edge cases | 4 | Real bill that spiked 3.4×, spiked reminder, unknown consumer number, unknown biller |

Verdicts: 24 SAFE, 25 SCAM, 11 CAUTION. Split: 39 `dev`, 21 `test`, stratified by scenario.
**Tune prompts on `dev` only; report metrics on `test`.**

## How labels are made

Each item is defined by its *intent*: which biller it names, whether its amount is genuine,
tampered or for an unknown consumer, what each payment destination is meant to be (official,
lookalike, known scam, short link, personal number, other), and which scam phrasings it uses.
`expected.evidence` comes from that intent through a fixed table in the generator, **not from
running the tools**. `api/tests/test_dataset.py` then runs the real tools on each item's
ground-truth fields and requires an exact match, so label mistakes and tool bugs both surface.

## Verdict policy

The Day 3 risk engine must reproduce these hand-assigned verdicts:

- **SCAM** — any strong scam signal: `LOOKALIKE_DOMAIN`, `LOOKALIKE_VPA`,
  `KNOWN_SCAM_DESTINATION`, `APK_LINK`; or a non-official destination together with scam
  phrasing (`DISCONNECTION_THREAT`, `KYC_UPDATE_LURE`, `REFUND_LURE`).
- **SAFE** — only when the biller is verified, the biller's own amount matches, and nothing is
  off (no unknown biller/consumer, mismatch, spike, non-official destination, short link or
  personal number). Polite "pay by the due date to avoid disconnection" wording alone does not
  block SAFE.
- **CAUTION** — everything else, including any check that could not be done.

## Regenerate

```
api\.venv\Scripts\python data\generators\make_dataset.py
```

Output is deterministic (fixed seeds, same mock data). Requires Microsoft Edge for rendering.
Telugu and Hindi texts were written for this set; Telugu reviewed by BV.
