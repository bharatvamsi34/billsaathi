# BillSaathi demo video script (3:00)

Updated for the Nov 4 interface. Live app: https://zealous-coast-09279dd00.1.azurestaticapps.net

**Record at** `https://zealous-coast-09279dd00.1.azurestaticapps.net/?demo=1`: bigger type, no first-visit hint, same behaviour. Silent raw footage of the web scenes is in `docs/screenshots/demo/` on BV's machine (gitignored), one file per scene, each starting at the click.

**Rules for every take**
- Say only what the screen shows. Biller records are simulated; never say or imply a connection to the live BBPS network.
- Checks took 15 to 30 seconds overnight (median to verdict below), and speed varies by time of day. Speed up the waiting in the edit, label it **"sped up"**, and leave the real timers readable.
- Never show a real bill, name or phone number other than the test number. Hide notifications.

## At a glance

| # | Time | Scene | Screen | Input | Raw footage |
|---|---|---|---|---|---|
| 0 | 0:00–0:07 | Built-during-hackathon line | Title card | — | — |
| 1 | 0:07–0:20 | The problem | Phone, then hero | Message A, stat | — |
| 2 | 0:20–0:50 | Scam blocked; comparison | Laptop | **Watch a scam get blocked** | `a_scam_blocked` |
| 3 | 0:50–1:05 | The judge catches an over-claim | Laptop | **See the judge catch an over-claim** | `d_judge_replay` |
| 4 | 1:05–1:30 | Genuine bill, SAM crop, simulated payment | Laptop | **Try a genuine demo bill** | `c_genuine_pay_receipt` |
| 5 | 1:30–1:42 | One changed amount | Laptop | **Tampered bill** sample | `b_tampered_caution` |
| 6 | 1:42–1:58 | Voice in Telugu | Phone browser | Line V, spoken | `e_voice_sample` is a fallback |
| 7 | 1:58–2:18 | WhatsApp | Phone WhatsApp | W1, P1, Line V | — |
| 8 | 2:18–2:32 | Privacy Mode on open weights | Laptop | Toggle, then Scam SMS | `f_privacy_mode` |
| 9 | 2:32–2:47 | How well it works | Laptop | `/eval` | `g_eval_scroll` |
| 10 | 2:47–3:00 | Impact and close | End card | — | — |

## The script

Voiceover is written for about 2.3 words a second. Trim the voiceover before you trim a scene's on-screen action.

### Scene 0, 0:00–0:07: the required line
**On screen:** plain title card with the same words.

> "Everything you'll see was built during the hackathon, October 26 to November 4. Nothing here existed before."

### Scene 1, 0:07–0:20: the problem
**On screen:** Message A on the phone for 4 seconds. Cut to the laptop hero; zoom on **₹22,845 crore (~US$2.7 billion)** and its source line.

> "Messages like this reach Indian families. 'Pay now, or your power gets cut.' Indians lost over twenty-two thousand crore rupees to cyber fraud in 2024, and it's hard to tell which bill is real."

**Say "cyber fraud", not "bill scams":** the figure covers all cyber fraud.

### Scene 2, 0:20–0:50: scam blocked
**Clicks**
1. Click **Watch a scam get blocked**. The input appears as a chat bubble with the UPI ID and threat marked.
2. Hold on the amber **"Possible fraud found — running final checks…"** and the fixed checks, with their **Code** badges and timers.
3. The red **SCAM** arrives, with **Do not pay**, **Report fraud: call 1930**, **Warn my family** and the card preview.
4. Scroll to **Does it match the biller's record?** Zoom: the UPI ID is **"On the known-scam list"**, and the biller is **"not in registry"**.
5. Show **Why**: the two real values.

> "This isn't a bill scanner. It's an agent that verifies. Code runs fixed checks first, so you see an early warning, in amber, not a verdict. Then the agent reviews the evidence, and only then is it called a scam. Here's what the message says, next to what the biller's record says. No model can turn a risk into SAFE."

### Scene 3, 0:50–1:05: the judge catches an over-claim
**Clicks:** in **Try a sample**, click **See the judge catch an over-claim**. Hold on the label **"Replay of a real run (recorded 2026-10-29)"**, then the amber row: **"Evidence shows cut threat and urgency but does not mention tonight."** Then **After correction**.

> "A second Muse Spark call checks every claim against the evidence. In this real recorded run, the agent said 'tonight', and the evidence didn't. The judge sent it back, and the agent corrected itself."

### Scene 4, 1:05–1:30: genuine bill and simulated payment
**Clicks**
1. Scroll up, click **Try a genuine demo bill**.
2. Hold on **Finding the bill in the photo**, badge **SAM 3.1 · photo cropping**: the photo, the box, the cropped bill.
3. The green **SAFE**: **"Verified against the demo biller record"**, every comparison row ticked at ₹1,240.00.
4. Click **Simulate payment (sandbox — no real money)**, then **Yes, pay in the sandbox**.
5. Hold on the receipt: `SBX-…`, audit entry, "Sandbox: no real money moves".

> "Now a phone photo of a genuine demo bill. SAM 3.1 finds the bill. Muse Spark reads it. Every value matches the simulated biller record, so it's SAFE, and you still decide. One confirmation, a sandbox receipt, and an audit entry the database won't let anyone change. No real money moves."

### Scene 5, 1:30–1:42: one changed amount
**Clicks:** click **Tampered bill: one amount changed**. Zoom on the comparison: only the Amount row is marked: **₹4,240.00** against **₹1,240.00**.

> "Same account, one digit changed. Exactly one row differs: the bill says four thousand, the record says one thousand. Caution. Do not pay yet."

### Scene 6, 1:42–1:58: Telugu voice (phone browser)
**Clicks**
1. Tap **తెలుగు**, tab **మీది తనిఖీ చేయండి**, then **మాట్లాడండి** (Speak).
2. Say Line V, tap stop.
3. Show **మేము విన్నది** (what we heard) with the **Muse Voice Transcribe** badge, then **మోసం** (SCAM) and the Telugu explanation.
4. Tap **వినండి** (Listen) for about 4 seconds.

**Add English subtitles.** If the phone or the Telugu line misbehaves, `e_voice_sample` is a synthetic **English** voice note through the same model; say so if you use it.

> "Many people are more comfortable speaking, in their own language. Muse Voice Transcribe hears Telugu, the same agent checks it, and the answer comes back in Telugu, read aloud."

### Scene 7, 1:58–2:18: WhatsApp (phone)
**Actions**, sped up between messages:
1. **Text:** paste W1 → "Checking now… please don't pay while I check." → "⚠️ Scam signals found…" → **⛔ SCAM — do not pay** with two reasons and the helpline.
2. Send **DETAILS** → full evidence.
3. **Photo:** send P1 → verdict.
4. **Voice note:** Line V → "🎤 నేను విన్నది…" → **⛔ మోసం (SCAM) — డబ్బు చెల్లించవద్దు**.

> "And no app to install. Forward it on WhatsApp: text, a photo, or a voice note in Telugu. Same agent, same checks. A short answer in your language, with the national fraud helpline."

### Scene 8, 2:18–2:32: Privacy Mode
**Clicks:** **Check another**. Turn on **Privacy Mode** in the top bar, click the Scam SMS sample. Show the dark bar **"Privacy Mode: Muse Spark Open · open weights (hosted on Baseten / Fireworks)"** and the badges switching.

> "Privacy Mode runs the whole pipeline on open weights: Muse Spark Open on an external host, with no call to Meta's Model API. Same tools, same rules."

**Don't say "offline" or "on your device".** About 1 run in 4 tonight, Spark Open stopped without submitting, which ends safely but shows "Some checks could not be completed". Just retake.

### Scene 9, 2:32–2:47: how well it works
**Clicks:** open `/eval`. Hold on the headline, the tiles, then the sweep and the Spark 1.3 vs Spark Open tables.

> "We measured it on twenty-one synthetic test items we never tuned on. All correct, zero of thirteen risky requests called SAFE. A small set, and the page says so. Results and graders are public."

### Scene 10, 2:47–3:00: impact and close
**On screen:** end card with the live URL and repo URL.

> "A family should be able to ask, before money moves: is this real? In their own language, on the phone they already have. That's BillSaathi. Ireesha Infosol will keep building it."

## Exact inputs

All inputs are synthetic. The samples and the text of W1, H1 and Line V gave the expected verdict on the live API on Nov 2–3. **Not yet run:** Line V spoken aloud, and P1 through a phone camera, so rehearse those two.

| Scene | Input | Exactly what | Expected |
|---|---|---|---|
| 1 | **Message A** (shown only, not checked) | The text below | — |
| 2 | Sample `scam_en_known_vpa`, via **Watch a scam get blocked** in the English UI | Electricity Office, ₹3,150, `electricityofficer@okdemo` | SCAM |
| 3 | The replay sample, `eval/results/agent_live_2026-10-29_2355.jsonl` | Telugu scam SMS; "tonight" refused | SCAM (recorded) |
| 4 | Sample `photo_genuine_demo`, via **Try a genuine demo bill** | Demo Power, consumer ending 2761, ₹1,240.00 | SAFE |
| 5 | Sample `demo_tampered_same_account`, tile "Tampered bill" | Same account, biller ₹1,240.00, bill ₹4,240.00 | CAUTION |
| 6 | **Line V**, spoken in the Telugu UI | Below | SCAM |
| 7 | **W1**, then **DETAILS**, **P1** (`bill_swapped_vpa_dgas`), **Line V** as a voice note | Below | SCAM |
| 8 | Scam SMS sample with Privacy Mode on (or **H1** in the Hindi UI) | Below | SCAM |
| 9 | https://zealous-coast-09279dd00.1.azurestaticapps.net/eval | 21/21, 19/21 findings, 13/13, 8/8, 10.9 s | — |

**Message A (the hook, on the phone)**
```
Electricity Office: Pending bill Rs 3,150. Pay immediately to UPI electricityofficer@okdemo or your power supply will be cut.
```
Send it to yourself or show it in a notes app. It's the same text as the Scam SMS sample, so the hook pays off in Scene 2.

**Line V (Telugu, spoken; say the digits slowly)**
```
విద్యుత్ ఆఫీసర్ అని ఒకరు మెసేజ్ పంపారు. ఈ రాత్రి మా కరెంట్ కట్ చేస్తామని, వెంటనే 9000000003 కు కాల్ చేయమని చెప్పారు.
```
Subtitle: "Someone claiming to be an electricity officer sent a message. They said our power will be cut tonight, and to call 9000000003 at once."

**Rehearse this first.** It was tested as text, not spoken. Tonight an English synthetic voice saying digits came back as words ("nine zero zero…"), so the number may not be read as a number; that clip still ended SCAM on the other findings, but if yours ends CAUTION, check "what we heard" and retake.

**Message W1 (WhatsApp text)**
```
Dear consumer, your electricity power will be cut tonight at 9:30 PM because last month's bill was not updated. Call electricity officer immediately on 9000000003.
```

**Photo P1 (WhatsApp photo).** Open this on the laptop, fill the screen, and photograph it straight on with the WhatsApp camera:
https://zealous-coast-09279dd00.1.azurestaticapps.net/samples/bill_swapped_vpa_dgas.png

It's a DemoGas bill with UPI ID `demogas.billing@okdemo` instead of the official one. Labelled SCAM, but through a camera the reading can vary, so rehearse it.

**Message H1 (Privacy Mode, Hindi)**
```
प्रिय ग्राहक, आपका बिजली बिल रुका हुआ है। तुरंत केवाईसी अपडेट करने के लिए यह ऐप डाउनलोड करें: bijli-seva-app.example/BijliKYC.apk वरना आज रात कनेक्शन काट दिया जाएगा।
```

## Before recording

1. **API awake:** https://ca-billsaathi-api.orangeocean-70e70440.centralindia.azurecontainerapps.io/api/v1/health returns `ok` (min replicas is 1).
2. **Laptop browser:** open the `?demo=1` address at 1440 px or larger. It hides the first-visit hint and enlarges the type.
3. **Warm the warning card:** the first picture per verdict takes about 15 seconds and is then cached until the API restarts. Run one SCAM and one CAUTION check before the real take. **Do not deploy after this.** The card preview is 120 px beside **Warn my family**.
4. **SAM box:** the blue box and cropped thumbnail were reviewed on a recorded live run. Expand **View trace** after a genuine-bill check to see them again; during the check they appear in the live steps.
5. **Listen:** test it on the phone in Telugu. Audio playback has not been tested by me and depends on the device having a Telugu voice; if it says there is none, install one or record this moment on another device.
6. **Microphone:** tap Speak once on the phone beforehand, so the permission prompt isn't in the take.
7. **WhatsApp language:** the reply language sticks once you choose one, and it overrides what you say.
   - Before the text and photo, send `English`. Cut this from the video.
   - Before the voice note, send `తెలుగు`. Cut this too.
   - **The new short replies and DETAILS were tested only with a mocked Graph API tonight.** Send one test message first.
8. **Limits:** 10 web checks a minute per address, 5 WhatsApp checks a minute per sender. If you see "Too many checks", wait a minute. The daily spend cap is $5 of estimated spend per UTC day (resets at 5:30 AM IST); that's about 150 takes at about $0.03 each.
9. **Capture:** laptop screen at 1440×900 or larger; phone screen recording with internal audio on for Listen. Turn on Do Not Disturb on both.
10. **Backup:** record each scene twice. A model can word things differently per take, and rarely asks its one question or gets a reason sent back, adding a few seconds. Verdicts have been stable, but don't script the exact explanation text.

## Where this differs from `CLAUDE.md` §9

- **Amounts:** the tampered sample is now ₹1,240 vs ₹4,240, as §9 says, on the same account as the genuine bill.
- **Dropped "India's next 500 million digital payers":** we have no source for that number.
- **Hindi read-aloud moved:** the scam scene is in English for judges, and read-aloud is shown in Telugu in Scene 6.
- **"Kya ye payment safe hai?" replaced:** a bare question has no bill or message to check, so it ends as CAUTION or the agent's question. Line V gives a clear result.
- **No "Report & block" button exists:** the product has **Warn my family** and **Report fraud: call 1930**, so the script shows those.
