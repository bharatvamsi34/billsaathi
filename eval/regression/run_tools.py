"""Weakest verdict the code allows on each input, with no model: an agent always claims SAFE.
Accepted = SAFE; otherwise the forced verdict (CAUTION or the floor). argv: api path, inputs, out."""
import json
import logging
import sys

api, inputs, out = sys.argv[1:4]
sys.path[:0] = [api, api + "/tests"]
sys.stdout.reconfigure(encoding="utf-8")
logging.disable(logging.CRITICAL)
from fakes import ScriptedModel, evidence, submit  # noqa: E402

from app.agent.loop import start  # noqa: E402
from app.agent.protocol import AgentInput  # noqa: E402
from app.schemas import BillFields  # noqa: E402


def cheat(conv):
    ids = evidence(conv)
    return submit("SAFE", *[(f"Check {i}.", [e]) for i, e in enumerate(ids)] or [("Nothing.", ["ev_none"])])


rows = []
for it in json.load(open(inputs, encoding="utf8")):
    fields = BillFields.model_validate(it["fields"])
    ai = AgentInput.from_fields(fields, raw_text=it["text"])
    if it["visible"]:
        ai = ai.model_copy(update={"visible_text": it["visible"]})
    s = start(ScriptedModel([cheat] * 6), ai)
    codes = sorted({e.code.value for r in s.record.tool_results for e in r.evidence})
    dests = sorted(f"{d.kind.value if hasattr(d.kind, 'value') else d.kind}:{d.value}" for d in s.destinations)
    rows.append({"group": it["group"], "id": it["id"], "expected": it["expected"], "verdict": s.final.verdict.value, "codes": codes, "dests": dests})
json.dump(rows, open(out, "w", encoding="utf8"), ensure_ascii=False, indent=0)
print(len(rows), "rows")
