# Challenge set: frozen before running

Written and committed on 2026-11-04, before any model saw these 20 cases.

| | |
|---|---|
| Labels and code | commit `6e14ae0` (this file is added in the next commit; nothing else changes) |
| Fix included | wider contact detection (`9ccd24d`) |
| Reading and agent | Muse Spark 1.3 (`muse-spark-1.3`), effort `low` |
| Judge | Muse Spark 1.3, effort `low` |
| Explanation | Muse Spark 1.3, effort `low` |
| Isolation | SAM 3.1 on images |
| Runner | `eval/run_challenge.py`, 3 at a time, from the dev machine |
| Question from the agent | nobody answers, as in the main evaluation |
| Budget | $2 |

**Rules.** Run once. The runner refuses to run again once the results file exists. Every failure is published in `docs/CHALLENGE_RESULTS.md`. No fix-and-rerun: a real bug is reported as a finding, and any later fix does not change this score.

**Labels** follow `data/synthetic/README.md`. They were written from intent. Before freezing, the real tools were run on the ground-truth fields, and all 20 verdicts agreed; this checks the labels, not the model. Regenerate with `data/generators/make_challenge.py`.
