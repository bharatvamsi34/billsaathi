# Testing BillSaathi by hand

A plain-language guide for trying the live app: https://zealous-coast-09279dd00.1.azurestaticapps.net

> **Everything here is made up.** The 8 billers, their websites, UPI IDs and consumer numbers are
> fictional (websites end in `.example`, UPI IDs in `@demobank`). BBPS is a mock we built. No real
> money moves.

## 1. How a check works, in 5 steps

1. **Read.** Muse Spark reads your photo, screenshot or pasted message and picks out the biller,
   consumer number, amount, due date and every place it asks you to pay (link, UPI ID, phone number).
   A second pass copies all visible text, so no link can be "forgotten".
2. **Fixed checks (always run, by code, not the AI).** Is the biller in the registry? Is every link,
   UPI ID and phone number an official channel of that biller, a known scam, or a lookalike? Does the
   text use known scam wording ("power will be cut tonight", "update KYC", "refund")? If the biller
   and consumer number are known, the mock BBPS is asked for the real bill amount and the last 6 bills.
3. **Agent review.** The agent reads that evidence, may run more checks or ask you **one** question
   (usually the consumer number), and proposes a verdict with reasons, each citing the evidence.
4. **Independent check.** Code checks the citations and the rules (the AI can never turn a risk into
   SAFE); then a second model call checks that each reason says only what its evidence says.
5. **Verdict.** **SAFE** only if *every* check passed. **SCAM** for clear scam signals.
   **CAUTION** for everything else, including anything we could not verify. Then: pay (sandbox, coming)
   or warn your family.

## 2. The mock billers

Each biller has one official website, one UPI ID and one toll-free helpline. Amounts are the
current (October 2026) bill in the mock BBPS. A message is SAFE only with a matching consumer number
**and** amount, paid to the official website or UPI ID.

| Biller (short name) | Category | Official website | Official UPI ID | Helpline | Consumer no. → current bill |
|---|---|---|---|---|---|
| Demo Power Distribution Co. Ltd (Demo Power) | Electricity, Maharashtra | `demopower.example` | `demopower.bill@demobank` | 1800-000-1001 | `DP-4410-882761` → ₹1,240 · `DP-8306-855427` → ₹878 |
| Sample Vidyut Seva Ltd (Sample Vidyut) | Electricity, Telangana | `samplevidyut.example` | `samplevidyut@demobank` | 1800-000-1002 | `SVS905403060` → ₹941 · `SVS518355582` → ₹1,372 |
| Example Bijli Nigam Ltd (Example Bijli) | Electricity, Uttar Pradesh | `examplebijli.example` | `examplebijli.pay@demobank` | 1800-000-1003 | `2774392066` → ₹1,476 · `1205880911` → ₹5,814 ⚠️ |
| Example Jal Board | Water, Delhi | `examplejal.example` | `examplejal@demobank` | 1800-000-1004 | `EJB49787225` → ₹464 · `EJB80004604` → ₹330 |
| DemoGas Ltd | Gas, Gujarat | `demogas.example` | `demogas.bill@demobank` | 1800-000-1005 | `BP24994833` → ₹537 · `BP30503478` → ₹1,421 ⚠️ |
| Demo Mobile Postpaid | Mobile postpaid, all India | `demomobile.example` | `demomobile@demobank` | 1800-000-1006 | `DM816336795` → ₹599 · `DM376104981` → ₹599 |
| SkyDemo DTH | DTH, all India | `skydemo.example` | `skydemo.recharge@demobank` | 1800-000-1007 | `SD592425240` → ₹599 · `SD225873808` → ₹299 |
| FiberDemo Broadband | Broadband, Karnataka | `fiberdemo.example` | `fiberdemo@demobank` | 1800-000-1008 | `FD33274624` → ₹999 · `FD11369303` → ₹999 |

⚠️ These two consumers have a current bill about 3× their usual amount, on purpose: the biller's
own amount matches, but the jump from their history makes the verdict **CAUTION** (amount spike).

## 3. Twelve messages to paste

Open the app, paste a message into **"Or paste the SMS / WhatsApp message"**, tap **Check this
message**. Choose the app language first if you want the result in Telugu or Hindi.

Every expected verdict below was reproduced by running the real tools and risk engine on the
message's fields. The AI's reading can still vary slightly between runs; the verdict should not.

### SAFE — official reminder, amount matches the biller

**1. English, Demo Power** — expected **SAFE**

```
VK-DEMOPW: Dear customer, your Demo Power bill for consumer no. DP-4410-882761 is Rs 1,240.00, due on 05-Nov-2026. Pay at demopower.example/pay or UPI demopower.bill@demobank. Ignore if already paid.
```

Why: biller verified, both payment channels official, ₹1,240 matches the biller's own bill and is in
line with the last 6 bills.

**2. Telugu, Sample Vidyut** — expected **SAFE**

```
VM-SVSLTD: శాంపిల్ విద్యుత్ సేవ: సర్వీస్ నంబర్ SVS905403060 కు ఈ నెల బిల్లు ₹941. గడువు తేదీ 27-10-2026. samplevidyut.example/pay లో చెల్లించండి. ఇప్పటికే చెల్లించి ఉంటే పట్టించుకోవద్దు.
```

Why: same as above — official website, ₹941 matches, normal for this consumer.

**3. Hindi, Example Jal Board** — expected **SAFE**

```
VK-EXMJAL: एग्ज़ाम्पल जल बोर्ड: उपभोक्ता संख्या EJB49787225 का पानी का बिल ₹464 है, अंतिम तिथि 29-10-2026. UPI examplejal@demobank से भुगतान करें। धन्यवाद।
```

Why: official UPI ID, ₹464 matches the biller and the history.

### CAUTION — something does not add up, so do not pay yet

**4. English, amount changed** — expected **CAUTION**

```
Demo Power: Bill for consumer no. DP-8306-855427 is Rs 2,878, due 26-Oct-2026. Pay via UPI demopower.bill@demobank.
```

Why: the UPI ID is official, but the biller says this consumer owes ₹878, not ₹2,878
(amount mismatch; also far above their history).

**5. Hindi, amount spike** — expected **CAUTION**

```
VK-EBNLTD: एग्ज़ाम्पल बिजली निगम: खाता संख्या 1205880911 का बिजली बिल ₹5,814 है, अंतिम तिथि 28-10-2026. भुगतान examplebijli.example/pay पर करें।
```

Why: everything matches the biller, but ₹5,814 is about 3.4× this consumer's usual bill (₹1,710).
A real jump like this deserves a call to the biller before paying.

**6. English, unknown biller** — expected **CAUTION**

```
Metro City Power: Your bill for account MCP-22018 is Rs 1,180, due 10-Nov-2026. Pay at metrocitypower.example/pay.
```

Why: "Metro City Power" is not in the biller registry, so the website cannot be official and the
amount cannot be checked. No scam wording, so CAUTION rather than SCAM.

**7. English, consumer number missing** — expected **CAUTION** (or **SAFE** after you answer)

```
SkyDemo: Your DTH recharge of Rs 599 is due on 01-Nov-2026. Recharge at skydemo.example/pay or UPI skydemo.recharge@demobank.
```

Why: channels are official, but without a consumer number the amount cannot be checked with the
biller. The agent may ask you **one question** for the number: answer `SD592425240` and it should
become SAFE; tap **I don't know** and it stays CAUTION.

### SCAM — clear scam signals

**8. Telugu, lookalike website** — expected **SCAM**

```
శాంపిల్ విద్యుత్: మీ బిల్లు బకాయి ఉంది. ఈ రాత్రి 9:30 కి మీ కరెంట్ కట్ చేయబడుతుంది. వెంటనే samplevidyut-billpay.example లో చెల్లించండి.
```

Why: `samplevidyut-billpay.example` imitates the official `samplevidyut.example`, plus a
"power cut tonight" threat.

**9. Hindi, .apk link** — expected **SCAM**

```
प्रिय ग्राहक, आपका बिजली बिल रुका हुआ है। तुरंत केवाईसी अपडेट करने के लिए यह ऐप डाउनलोड करें: bijli-seva-app.example/BijliKYC.apk वरना आज रात कनेक्शन काट दिया जाएगा।
```

Why: the link installs an Android app (`.apk`) — a classic way to take over a phone — together with a
KYC lure and a disconnection threat.

**10. English, link shortener** — expected **SCAM**

```
DemoGas: Your gas connection will be stopped today due to pending payment. Pay Rs 735 immediately: tinyurl.com/demogas-pay
```

Why: the payment link is hidden behind a link shortener (not DemoGas's site) and the message
threatens to stop the connection.

**11. English, personal mobile number + disconnection threat** — expected **SCAM**

```
Dear consumer, your electricity power will be cut tonight at 9:30 PM because last month's bill was not updated. Call electricity officer immediately on 9123456780.
```

Why: a personal mobile number is never an official biller channel, combined with a "cut tonight"
threat. (`9123456780` is a made-up number.)

**12. Telugu, known scam UPI ID** — expected **SCAM**

```
విద్యుత్ శాఖ: మీరు ఎక్కువ బిల్లు కట్టారు. ₹1,450 రీఫండ్ కోసం వెంటనే UPI billupdate.refund@okdemo కు ₹10 పంపండి.
```

Why: `billupdate.refund@okdemo` is on the known-scam list, and "pay ₹10 to get a refund" is a
refund lure.

## 4. What happens with a REAL bill

Expect **CAUTION — "biller not in registry"**. This is by design: the registry only has the 8 mock
billers above, so a real electricity or phone bill cannot be verified against its biller. BillSaathi
never says SAFE when it cannot verify.

**Do not upload real bills, real SMS or anything with personal details.** Images and text are sent to
Meta's Model API for reading. Use the samples in the app, or the messages above.

## 5. Camera test (phone)

1. On the laptop, open one of the sample bill images, for example
   https://zealous-coast-09279dd00.1.azurestaticapps.net/samples/bill_tampered_demo.png
   (or a file from `data/synthetic/images/`, e.g. `bill_genuine_demo.png`). Make it fill the screen.
2. On the phone, open the app (scan the QR code shown on the desktop page), tap
   **Take a photo of the bill**, and photograph the laptop screen straight on, with the whole bill in
   the frame and no glare.
3. Expected: `bill_genuine_demo.png` → **SAFE**; `bill_tampered_demo.png` → **CAUTION** (the
   biller says ₹1,243, the bill says ₹4,243). A blurry or cut-off photo should end in CAUTION or a
   question for the consumer number — never SAFE.

## 6. Where to look if something seems wrong

- The **How we checked** list under the verdict shows every check and its result; tap a reason in the
  verdict to jump to the evidence it cites.
- Note the time, the message and the verdict, and add it to the findings log in `CLAUDE.md` §11.
