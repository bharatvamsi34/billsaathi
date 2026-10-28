"""Rendering helpers for the synthetic dataset.

Documents are HTML rendered by headless Edge (correct Devanagari/Telugu shaping); phone
photos are composited with Pillow so the document's exact corners are known.
"""

import html
import json
import math
import random
import re
import subprocess
import tempfile
from pathlib import Path
from string import Template

from PIL import Image, ImageDraw, ImageFilter

EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
TEMPLATES = Path(__file__).parent / "templates"


def esc(value: object) -> str:
    return html.escape(str(value))


def render_html(template: str, values: dict[str, str], size: tuple[int, int], out: Path) -> dict:
    """Render a template (values must already be HTML-safe) and return measured regions."""
    page = Template((TEMPLATES / template).read_text(encoding="utf-8")).substitute(values)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "page.html"
        src.write_text(page, encoding="utf-8")
        common = [
            str(EDGE),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            f"--window-size={size[0]},{size[1]}",
            f"--user-data-dir={Path(tmp) / 'profile'}",
        ]
        subprocess.run([*common, f"--screenshot={out}", src.as_uri()], check=True, capture_output=True, timeout=60)
        dom = subprocess.run(
            [*common, "--dump-dom", src.as_uri()],
            check=True,
            capture_output=True,
            timeout=60,
            text=True,
            encoding="utf-8",
        ).stdout
    match = re.search(r'data-regions="([^"]*)"', dom)
    if not match:
        raise RuntimeError(f"no regions found rendering {template}")
    if Image.open(out).size != size:
        raise RuntimeError(f"{out.name}: Edge produced the wrong size")
    return json.loads(html.unescape(match.group(1)))


def box_to_polygon(box: list[float]) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = box
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def make_photo(doc: Path, out: Path, seed: int) -> list[tuple[float, float]]:
    """Place the document, tilted and skewed, on a cluttered table; return its corners."""
    rng = random.Random(seed)
    W, H = 1600, 1200
    wood = rng.choice([(150, 108, 72), (120, 86, 60), (170, 140, 105)])
    bg = Image.new("RGB", (W, H), wood)
    d = ImageDraw.Draw(bg)
    for x in range(0, W, 3):
        s = rng.randint(-18, 18)
        d.line([(x, 0), (x + rng.randint(-40, 40), H)], fill=tuple(c + s for c in wood))
    cx, cy = rng.choice([(1390, 240), (210, 230), (1400, 980)])
    d.ellipse([cx - 125, cy - 125, cx + 125, cy + 125], fill=(235, 235, 230))
    d.ellipse([cx - 90, cy - 90, cx + 90, cy + 90], fill=(92, 58, 35))
    d.polygon([(90, 980), (560, 1120), (552, 1145), (82, 1004)], fill=(25, 60, 160))
    bg = bg.filter(ImageFilter.GaussianBlur(1.2))

    src = Image.open(doc).convert("RGB")
    w, h = src.size
    scale = rng.uniform(0.9, 1.0)
    angle = math.radians(rng.uniform(-9, 9))
    shear = rng.uniform(-0.06, 0.06)
    ca, sa = math.cos(angle), math.sin(angle)
    a, b = scale * ca, scale * (ca * shear - sa)
    c, e = scale * sa, scale * (sa * shear + ca)
    xs = [a * x + b * y for x, y in [(0, 0), (w, 0), (w, h), (0, h)]]
    ys = [c * x + e * y for x, y in [(0, 0), (w, 0), (w, h), (0, h)]]
    tx = (W - (max(xs) - min(xs))) / 2 - min(xs) + rng.uniform(-60, 60)
    ty = (H - (max(ys) - min(ys))) / 2 - min(ys) + rng.uniform(-30, 30)
    corners = [(a * x + b * y + tx, c * x + e * y + ty) for x, y in [(0, 0), (w, 0), (w, h), (0, h)]]
    det = a * e - b * c
    inv = (e / det, -b / det, (b * ty - e * tx) / det, -c / det, a / det, (c * tx - a * ty) / det)

    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).polygon([(x + 14, y + 16) for x, y in corners], fill=110)
    bg.paste((20, 14, 8), mask=shadow.filter(ImageFilter.GaussianBlur(14)))
    warped = src.transform((W, H), Image.Transform.AFFINE, inv, resample=Image.Resampling.BICUBIC)
    mask = Image.new("L", (w, h), 255).transform(
        (W, H), Image.Transform.AFFINE, inv, resample=Image.Resampling.BILINEAR
    )
    bg.paste(warped, mask=mask)
    light = Image.radial_gradient("L").resize((W, H)).point(lambda v: int(v * 0.35))
    bg.paste((0, 0, 0), mask=light)
    bg.save(out, quality=82)
    return corners
