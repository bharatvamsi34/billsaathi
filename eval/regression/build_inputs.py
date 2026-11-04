"""Build the inputs once, from data only: 60 labels + the exact text printed on image items,
12 TESTING.md messages, every demo sample. Run from the repo root."""
import html
import json
import re
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from string import Template

ROOT = Path.cwd()
sys.path[:0] = [str(ROOT / "api"), str(ROOT / "data/generators")]
sys.stdout.reconfigure(encoding="utf-8")
import make_dataset
from app.bbps_mock.registry import BILLERS

texts = {}
TEMPLATES = ROOT / "data/generators/templates"


def capture(template, values, size, out):
    page = Template((TEMPLATES / template).read_text(encoding="utf8")).substitute(values)
    page = re.sub(r"<(style|script).*?</\1>", " ", page, flags=re.DOTALL)
    page = re.sub(r"<br\s*/?>|</(div|tr|p|td|th)>", "\n", page)
    texts[Path(out).stem] = re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page))).strip()
    return defaultdict(lambda: [0, 0, 1, 1])


make_dataset.render_html = capture
make_dataset.make_photo = lambda *a, **k: [(0, 0), (1, 0), (1, 1), (0, 1)]
tmp = Path(tempfile.mkdtemp())
make_dataset.IMAGES = tmp
real_unlink = Path.unlink
Path.unlink = lambda self, missing_ok=False: None  # nothing was written
make_dataset.build()
make_dataset.bill_item("demo_tampered_same_account", "tampered_amount", "DEMO00000MAH01", 0, "CAUTION", amount=4240.0, photo_seed=11)  # fmt: skip
Path.unlink = real_unlink
shutil.rmtree(tmp, ignore_errors=True)

items = []
labels = [json.loads(x) for x in open("data/synthetic/labels.jsonl", encoding="utf8")]
for lab in labels:
    f = lab["expected"]["extracted"]
    items.append({"group": "dataset", "id": lab["id"], "expected": lab["expected"]["verdict"], "fields": f, "text": lab["input"]["text"], "visible": texts.get(lab["id"]) if lab["input"]["kind"] == "image" else None})
missing = [x["id"] for x in items if x["group"] == "dataset" and not x["text"] and not x["visible"]]
print("image items with no captured text:", missing)


def derive(text):
    """Ground-truth-like fields from the message, without any detection code under test."""
    biller = next((b for b in BILLERS for n in (b.name, *b.aliases) if n.lower() in text.lower()), None)
    consumer = None
    if biller:
        for tok in re.findall(r"[A-Za-z0-9-]+", text):
            if biller.valid_consumer(tok):
                consumer = tok
    amt = re.search(r"(?:₹|Rs\.?\s?|रु\.?\s?)\s?([\d,]+(?:\.\d+)?)", text)
    dests = [{"kind": "upi", "value": v} for v in re.findall(r"[A-Za-z0-9._-]+@[A-Za-z]+", text)]
    dests += [{"kind": "url", "value": v.rstrip(".,")} for v in re.findall(r"(?:https?://)?[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:example|ly|gl|in|com)(?:/\S*)?", text) if "@" not in v]
    dests += [{"kind": "phone", "value": v} for v in re.findall(r"(?<!\d)[6-9]\d{9}(?!\d)", text)]
    return {"biller_name": biller.name if biller else None, "biller_category": str(biller.category.value) if biller else None, "consumer_number": consumer, "amount": float(amt.group(1).replace(",", "")) if amt else None, "due_date": None, "bill_date": None, "payment_destinations": dests, "languages": ["en"], "urgency_language": False}


md = Path("docs/TESTING.md").read_text(encoding="utf8")
for m in re.finditer(r"^\*\*(\d+)\. (.+?)\*\* — expected \*\*(\w+)\*\*.*?\n\n```\n(.+?)\n```", md, re.DOTALL | re.MULTILINE):
    items.append({"group": "testing", "id": f"testing_{m.group(1)}", "expected": m.group(3), "fields": derive(m.group(4)), "text": m.group(4), "visible": None})

samples = json.load(open("web/src/samples.generated.json", encoding="utf8"))
by = {x["id"]: x for x in items}
voice = re.search(r'VOICE_TEXT\s*=\s*\(?\s*"(.+?)"', Path("data/generators/make_demo_samples.py").read_text(encoding="utf8"), re.DOTALL)
for s in samples:
    i = s["id"]
    if i in by:
        items.append({**by[i], "group": "demo", "id": i})
    elif i == "demo_tampered_same_account":
        g = by["photo_genuine_demo"]
        f = {**g["fields"], "amount": 4240.0}
        items.append({"group": "demo", "id": i, "expected": "CAUTION", "fields": f, "text": None, "visible": texts[i]})
    elif s.get("text"):
        items.append({"group": "demo", "id": i, "expected": None, "fields": derive(s["text"]), "text": s["text"], "visible": None})
    elif i == "demo_voice_note":
        t = voice.group(1) if voice else "power will be cut"
        items.append({"group": "demo", "id": i, "expected": "SCAM", "fields": derive(t), "text": t, "visible": None})
json.dump(items, open(sys.argv[1], "w", encoding="utf8"), ensure_ascii=False, indent=0)
print({g: sum(x["group"] == g for x in items) for g in ("dataset", "testing", "demo")})
print([x["id"] for x in items if x["group"] == "demo"])
print(next(x["visible"] for x in items if x["id"] == "photo_genuine_demo")[:500])
