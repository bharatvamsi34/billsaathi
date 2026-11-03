# BillSaathi demo video script (3:00)

Follows `CLAUDE.md` §9, updated with what was actually built. Live app:
https://zealous-coast-09279dd00.1.azurestaticapps.net

**Rules for every take**
- Say only what the screen shows. BBPS is a mock; never say or imply a real connection.
- Checks take about 10 to 25 seconds. Speed up the waiting in the edit, put a small **"sped up"** label on it,
  and leave the real "Checked in … s" and step timers readable.
- Never show a real bill, a real name or a real phone number other than the test number. Hide notifications.

## At a glance

| # | Time | Scene | Screen | Input |
|---|---|---|---|---|
| 0 | 0:00–0:07 | Built-during-hackathon line | Laptop, title card | — |
| 1 | 0:07–0:22 | The problem | Phone, then laptop hero | Hook message, stat |
| 2 | 0:22–0:52 | Scam caught live | Laptop 1440 | **Try a scam sample** |
| 3 | 0:52–1:20 | Genuine bill, SAM crop, sandbox pay | Laptop 1440 | **Try a genuine bill** |
| 4 | 1:20–1:32 | Changed amount | Laptop 1440 | Sample tile |
| 5 | 1:32–1:52 | Telugu voice | Phone browser | Spoken line |
| 6 | 1:52–2:17 | WhatsApp: text, photo, voice note | Phone WhatsApp | Three messages |
| 7 | 2:17–2:32 | Privacy Mode on open weights | Laptop 1440 | Pasted Hindi message |
| 8 | 2:32–2:47 | How well it works | Laptop 1440 | `/eval` |
| 9 | 2:47–3:00 | Impact and close | Laptop hero or card | — |

## The script

Voiceover is written for about 2.3 words a second. Trim the voiceover before you trim a scene's on-screen action.

### Scene 0, 0:00–0:07: the required line (laptop)
**On screen:** plain title card with the same words.

> "Everything you'll see was built during the hackathon, October 26 to November 4. Nothing here existed before."

### Scene 1, 0:07–0:22: the problem (phone, then laptop)
**On screen:** the hook message (Message A) as a text on the phone, held for 4 seconds. Cut to the laptop hero and zoom on **₹22,845 crore** and its source line.

> "Messages like this reach Indian families. 'Pay now, or your power gets cut.' Indians lost twenty-two thousand crore rupees to cyber fraud in 2024. And it's hard to tell which bill is real."

**Say "cyber fraud", not "bill scams":** the figure covers all cyber fraud.

### Scene 2, 0:22–0:52: scam caught live (laptop)
**Actions**
1. On the hero, click **Try a scam sample** (English UI). The page scrolls to the workspace.
2. Hold on the **"Scam signals found — confirming…"** banner and the fixed-check cards. Zoom on a **Muse Spark 1.3** badge, the **Code** badge and a running timer.
3. The red **SCAM** card arrives. Show the explanation, then the reasons with evidence pills.
4. Scroll to **Warn my family** and show the card with the **Muse Image** badge.

> "This isn't a bill scanner. It's an agent that verifies. Fixed checks run in code first: is the biller real, is this UPI ID official, is this scam wording? So you see scam signals early. Then the agent reviews the evidence, and an independent check tests every reason against it. No model can turn a risk into SAFE. Muse Image paints a warning card to send your family."

### Scene 3, 0:52–1:20: genuine bill and sandbox pay (laptop)
**Actions**
1. Scroll up, click **Try a genuine bill**.
2. Hold on **Finding the bill in the photo** with the **SAM 3.1** badge and the saffron box over the photo.
3. Show the fields read, then the **green SAFE** card: amount ₹1,240.00.
4. Click **Pay ₹1,240.00 via BBPS (sandbox)**, then **Yes, pay in the sandbox**.
5. Hold on the receipt: `SBX-…`, audit entry, "Sandbox: no real money moves".

> "Now a phone photo of a genuine bill. SAM 3.1 finds the bill. Muse Spark reads it. Our mock biller confirms the amount and the UPI ID. Only then is it SAFE, and you still decide. One confirmation, a sandbox receipt, and an audit entry the database won't let anyone change. No real money moves."

### Scene 4, 1:20–1:32: changed amount (laptop)
**Actions:** **Check another**, then the sample **Electricity bill with a changed amount**. Zoom on the amounts in the reason: **₹1,243.00 from the biller, ₹4,243.00 on the bill**. The agent words the sentence itself, so it can vary slightly per take.

> "Change one digit on that bill. Same biller, same official UPI ID, but the biller says one thousand two hundred, not four thousand. Caution. Do not pay yet."

### Scene 5, 1:32–1:52: Telugu voice (phone browser)
**Actions**
1. Tap **తెలుగు**, then **సందేశాన్ని చెప్పండి** ("Speak the message").
2. Say Line V (below), then tap the red stop button.
3. Show **"మేము విన్నది"** (what we heard) with the **Voice Transcribe** badge, then **మోసం** (SCAM) and the Telugu explanation.
4. Tap **వినండి** (Listen) and let about 4 seconds play.

**Add English subtitles** for the spoken line and the explanation.

> "Many people are more comfortable speaking, in their own language. Muse Voice Transcribe hears Telugu, the same agent checks it, and the answer comes back in Telugu, read aloud."

### Scene 6, 1:52–2:17: WhatsApp (phone)
**Actions**, in this order, sped up between "Checking…" and the verdict:
1. **Text:** paste Message W1 → "Checking… ⏳" → ⛔ **SCAM** with "Report fraud: call 1930".
2. **Photo:** send photo P1 → ⛔ **SCAM**.
3. **Voice note:** record Line V as a WhatsApp voice note → "🎤 నేను విన్నది…" → ⛔ **మోసం**.

> "And no app to install. Forward it on WhatsApp, where people already are. Text, a photo of a bill, or a voice note in Telugu. The same agent, the same checks, the same pipeline as the web app. The reply comes in your language, with the national fraud helpline."

### Scene 7, 2:17–2:32: Privacy Mode (laptop)
**Actions**
1. **Check another**, switch to **हिंदी**. Tick **प्राइवेसी मोड**.
2. Paste Message H1, click **यह संदेश जाँचें**.
3. Show the bar **"प्राइवेसी मोड: ओपन-वेट मॉडल (Muse Spark Open)"** and the **Muse Spark Open** badges, then **धोखा** (SCAM).

> "Privacy Mode runs the whole pipeline on open weights: Muse Spark Open, through Baseten, with no call to Meta's Model API. Same tools, same checks, same safety rules."

### Scene 8, 2:32–2:47: how well it works (laptop)
**Actions:** open `/eval`. Hold on the four tiles, then the amber "Read this before trusting the numbers" box, then the Spark 1.3 vs Spark Open table.

> "We measured it on twenty-one made-up test items we never tuned on. All correct. Zero of thirteen risky requests called SAFE. A small set, and the page says so. Results and graders are public."

### Scene 9, 2:47–3:00: impact and close (laptop)
**On screen:** hero, or an end card with the live URL and repo URL.

> "A family should be able to ask, before money moves: is this real? In their own language, on the phone they already have. That's BillSaathi. Ireesha Infosol will keep building it."

## Exact inputs

All inputs are synthetic. The samples and the text of W1, H1 and Line V gave the expected verdict on the live API on Nov 2–3. **Not yet run:** Line V spoken aloud, and P1 through a phone camera, so rehearse those two.

| Scene | Input | Exactly what | Expected |
|---|---|---|---|
| 1 | **Message A** (shown only, not checked) | The text below | — |
| 2 | Sample `scam_en_known_vpa`, via **Try a scam sample** in the English UI | Electricity Office, ₹3,150, `electricityofficer@okdemo` | SCAM |
| 3 | Sample `photo_genuine_demo`, via **Try a genuine bill** | Demo Power, consumer ending 2761, ₹1,240.00 | SAFE |
| 4 | Sample `bill_tampered_demo`, tile "Electricity bill with a changed amount" | Demo Power, biller ₹1,243.00, bill ₹4,243.00 | CAUTION |
| 5 | **Line V**, spoken in the Telugu UI | Below | SCAM |
| 6.1 | **Message W1**, pasted | Below | SCAM |
| 6.2 | **Photo P1**, sample `bill_swapped_vpa_dgas` | Below | SCAM |
| 6.3 | **Line V** as a voice note | Below | SCAM |
| 7 | **Message H1**, pasted in the Hindi UI with Privacy Mode on | Below | SCAM |
| 8 | https://zealous-coast-09279dd00.1.azurestaticapps.net/eval | 21/21, 0/13, 0/8, 10.9 s | — |

**Message A (the hook, on the phone)**
```
Electricity Office: Pending bill Rs 3,150. Pay immediately to UPI electricityofficer@okdemo or your power supply will be cut.
```
Send it to yourself or show it in a notes app. It's the same text as the scam sample, so the hook pays off in Scene 2.

**Line V (Telugu, spoken; say the digits slowly)**
```
విద్యుత్ ఆఫీసర్ అని ఒకరు మెసేజ్ పంపారు. ఈ రాత్రి మా కరెంట్ కట్ చేస్తామని, వెంటనే 9000000003 కు కాల్ చేయమని చెప్పారు.
```
Subtitle: "Someone claiming to be an electricity officer sent a message. They said our power will be cut tonight, and to call 9000000003 at once."

If the number isn't heard, the verdict can be CAUTION instead of SCAM. Check "what we heard" and retake. This line was tested as text, not spoken, so do a spoken rehearsal first.

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
2. **Laptop browser:** use a fresh profile or incognito at 1440 px, so the first-visit guide shows. It will be visible in Scene 2's start. Press **Got it** first if you prefer a cleaner frame.
3. **Warm the warning card:** the first picture per verdict takes about 15 seconds and is then cached until the API restarts. Run one SCAM and one CAUTION check before the real take. **Do not deploy after this.**
4. **SAM box:** run the genuine bill once and check the saffron box looks right over the photo. I confirmed the verdict live, but never looked at the box itself.
5. **Listen:** test it on the phone in Telugu. Audio playback has not been tested by me and depends on the device having a Telugu voice; if it says there is none, install one or record this moment on another device.
6. **Microphone:** tap Speak once on the phone beforehand, so the permission prompt isn't in the take.
7. **WhatsApp language:** the reply language sticks once you choose one, and it overrides what you say.
   - Before 6.1 and 6.2, send `English`. Cut this from the video.
   - Before 6.3, send `తెలుగు`. Cut this too.
8. **Limits:** 10 web checks a minute per address, 5 WhatsApp checks a minute per sender. If you see "Too many checks", wait a minute. The daily spend cap is $5 of estimated spend per UTC day (resets at 5:30 AM IST); that's about 150 takes at about $0.03 each.
9. **Capture:** laptop screen at 1440×900 or larger; phone screen recording with internal audio on for Listen. Turn on Do Not Disturb on both.
10. **Backup:** record each scene twice. A model can word things differently per take, and rarely asks its one question or gets a reason sent back, adding a few seconds. Verdicts have been stable, but don't script the exact explanation text.

## Where this differs from `CLAUDE.md` §9

- **Amounts:** §9 says ₹1,240 vs ₹4,240. The sample is ₹1,243 vs ₹4,243, so the script uses those.
- **Dropped "India's next 500 million digital payers":** we have no source for that number.
- **Hindi read-aloud moved:** the scam scene is in English for judges, and read-aloud is shown in Telugu in Scene 5.
- **"Kya ye payment safe hai?" replaced:** a bare question has no bill or message to check, so it ends as CAUTION or the agent's question. Line V gives a clear result.
- **No "Report & block" button exists:** the product has **Warn my family** and **Report fraud: call 1930**, so the script shows those.
