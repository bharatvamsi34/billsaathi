"""Demo-only samples for the web gallery. They are NOT part of the labelled dataset: labels.jsonl,
the dev and test splits and the evaluation are untouched.

- demo_tampered_same_account: the genuine demo photo's account (same biller, same consumer number,
  same photo framing) with only the amount changed, so the comparison shows exactly one difference.
- demo_voice_note: a synthetic spoken message from the local Windows English voice. No personal
  data and no real person's voice. (This machine has no Telugu or Hindi voice installed.)

Run from the repo root: api/.venv/Scripts/python data/generators/make_demo_samples.py
"""

import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / "api"))

import make_dataset
from render import EDGE, TEMPLATES

OUT = ROOT / "web" / "public" / "samples"
VOICE_TEXT = (
    "Electricity office message. Your power will be cut tonight. "
    "Call the electricity officer immediately on 9 0 0 0 0 0 0 0 0 3."
)


def screenshot_only(
    template: str, values: dict, size: tuple[int, int], out: Path
) -> dict:
    """make_dataset's renderer without its region measurement: this sample has no label to fill."""
    page = Template((TEMPLATES / template).read_text(encoding="utf-8")).substitute(
        values
    )
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        src = Path(tmp) / "page.html"
        src.write_text(page, encoding="utf-8")
        subprocess.run(
            [
                str(EDGE),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
                f"--window-size={size[0]},{size[1]}",
                f"--user-data-dir={Path(tmp) / 'profile'}",
                f"--screenshot={out}",
                src.as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        for _ in range(100):  # Edge can return before the file is written
            if out.exists() and out.stat().st_size > 0:
                break
            time.sleep(0.2)
        time.sleep(0.5)
    return {"amount": [0, 0, 1, 1]}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    make_dataset.IMAGES = OUT
    make_dataset.render_html = screenshot_only
    make_dataset.bill_item(
        "demo_tampered_same_account",
        "tampered_amount",
        "DEMO00000MAH01",
        0,  # same consumer as photo_genuine_demo
        "CAUTION",  # unused here: this sample has no label
        amount=4240.0,
        photo_seed=11,  # same framing as photo_genuine_demo
    )
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        raw = Path(tmp) / "voice.wav"
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$s.SelectVoice('Microsoft Zira Desktop');"
            "$s.Rate = -1;"
            "$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, 16, 1);"
            f"$s.SetOutputToWaveFile('{raw}', $f);"
            f"$s.Speak('{VOICE_TEXT}');"
            "$s.Dispose()"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)
        target = OUT / "demo_voice_note.wav"
        target.write_bytes(raw.read_bytes())
    with wave.open(str(target)) as w:
        print(
            "voice:",
            w.getframerate(),
            "Hz",
            w.getnchannels(),
            "ch",
            w.getnframes() / w.getframerate(),
            "s",
        )


if __name__ == "__main__":
    main()
