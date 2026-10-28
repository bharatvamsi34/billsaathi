# Feedback on Meta AI products and partners

Concrete feedback from building BillSaathi during the Meta Global AI Developer Hackathon
(Oct 26 – Nov 4, 2026). Each item: what happened, how to reproduce, impact, suggestion.
Measured numbers come from our Day 1 model spike (`api/spike/results/`). Items marked
**(reported by BV)** were hit by the builder in the web console; the rest were measured in code.

## Meta developer platform (dev.meta.ai)

### 1. Billing popup hides the Continue button (reported by BV)
- **What happened:** in the billing popup, after selecting India / Indian Rupee, no Continue button was visible. It appeared only after zooming the browser out to about 67%.
- **Reproduce:** dev.meta.ai → Billing → choose country India and currency Indian Rupee at normal (100%) browser zoom.
- **Impact:** blocks onboarding at the step that unlocks paid usage; most people will not think of zooming out.
- **Suggestion:** make the billing dialog scrollable / responsive so its primary action is always reachable at 100% zoom.

### 2. The $20 card authorisation hold fails on Indian cards (reported by BV)
- **What happened:** the Billing page showed: *"Your account is restricted. We weren't able to place a temporary hold on your payment method."* This happened with an Indian Mastercard even after enabling international transactions on the card. The account was unblocked only after the free hackathon credits were applied.
- **Impact:** Indian developers — exactly the audience for India-focused builds — can be locked out of paid usage, and the "account is restricted" wording reads like a policy problem rather than a payment one.
- **Suggestion:** offer a payment path that works for Indian cards (or UPI), let credit-funded accounts skip the hold, and say in the message that the card hold failed and what to try next.

### 3. "Get code" is missing for some modalities
- **Audio (Muse Voice Transcribe) page has no "Get code"** (reported by BV). We had to obtain the multipart format separately.
- **Chat has no snippet for image input.** We tested both options ourselves: an inline `input_image` with a data URL and `/v1/files` + `file_id` both work. Only the data URL keeps nothing on Meta's servers, which matters for privacy-sensitive apps.
- **Suggestion:** a "Get code" button on every playground page, with image and audio examples, and a note on which input path stores files.

### 4. `/v1/models` lists Contributor variants next to normal models
- **What happened:** `GET /v1/models` returns `muse-spark-1.3` and `muse-spark-1.3-contributor` side by side with nothing in the response saying the Contributor variant trains on inputs.
- **Impact:** an easy, silent mistake for anyone choosing a model ID from the list; unacceptable for regulated use cases. We added a hard refusal in our client.
- **Suggestion:** a field such as `"trains_on_inputs": true` in the models list, and a warning in the playground.

### 5. Zero Data Retention: availability unclear
- **What happened:** the speech-to-text pricing page mentions a ZDR mode at the same price as standard, but we could not find how to tell whether it is available or enabled for our account.
- **Suggestion:** show ZDR status per account/key in the console, and document how to request it.

## Muse Spark / Muse Wonder (Responses API)

### 6. Reasoning can consume the whole output budget
- **Reproduce:** Muse Spark 1.3, `reasoning.effort = "medium"`, `max_output_tokens = 2048`, ask for a 3–5 sentence explanation in Tamil.
- **Result:** response `incomplete` (`max_output_tokens`), 2048 output tokens used, only 134 characters of answer text. With `effort = "low"` and 4096 tokens the same request finished in ~3 s.
- **Impact:** silent truncation for Indian-language output, where scripts already need more tokens.
- **Suggestion:** a separate reasoning budget, or documentation recommending headroom for non-Latin scripts.

### 7. First text token arrives only when the answer is nearly done
- **What happened:** with streaming on, time to first text token was ~90% of total latency (Spark 1.3: 3.7 s of 4.2 s) because reasoning happens first and no reasoning-summary deltas were streamed to us.
- **Impact:** streaming does not improve perceived latency for short answers.
- **Suggestion:** stream reasoning summaries (or progress events) so apps can show activity.

### 8. Self-reported confidence is not calibrated
- **What happened:** asked for per-field confidence while reading bills, the models gave 0.90–0.98 on fields they got wrong.
- **Impact:** confidence cannot gate decisions on its own; we verify amounts and destinations with tools instead.
- **Suggestion:** guidance (or a logprob-based option) for field-level confidence in structured extraction.

### What worked well
- The official `openai` Python SDK works against `https://api.meta.ai/v1` unchanged, streaming and non-streaming.
- **Native tool calling passed** on Spark 1.3, Spark 1.1 and Wonder (3 correct tool calls, correct final answer).
- Reading synthetic Indian bills: every key field correct on all models, including a tilted phone photo and a tampered amount; Spark at ~4–7 s and ~$0.005–0.008 per image.

## SAM 3.1

### 9. Concept wording matters a lot, and the output format is undocumented
- **Reproduce:** a phone photo of a bill on a table, concept `"document"` vs `"bill"`; an SMS screenshot, concept `"link"`.
- **Result:** `"document"` found the bill (box IoU 0.98 against the true bill area); `"bill"` returned nothing; `"link"` returned nothing on the SMS screenshot; `"QR code"` correctly returned nothing on an image without one.
- **Output:** the answer is text tokens like `<|box;x1=…;y1=…;x2=…;y2=…;w=…;h=…|><|mask;x=…;y=…;data=W,H,<encoded>|>` (~70 KB for one mask) with no documentation of the grammar or the mask encoding.
- **Suggestion:** document the output grammar, provide a mask decoder snippet, and list recommended concept words (or accept synonyms).

## Muse Voice Transcribe

### 10. Code-mixed Telugu–English needs `languageBias`
- **Reproduce:** a 7 s clip, "ఈ కరెంట్ బిల్లు సరైనదేనా? నేను దీన్ని కట్టొచ్చా?", WAV 24 kHz mono.
- **Result:** with `languageBias: ["Telugu", "English"]` the transcript was exact; without it, "కరెంట్ బిల్లు" came back as "current bill" in Latin letters and one word was misheard. ~3 s, about $0.0004 for the clip.
- **Suggestion:** recommend `languageBias` in the docs for Indian languages, and consider auto-detecting code-mixed speech.

## Baseten (Muse Spark Open)

### 11. No price listed for `meta-models/muse-spark-open-1026`
- **Impact:** we cannot budget Privacy Mode; our cost meter uses a deliberately high placeholder.
- **Suggestion:** list per-token pricing on the model page.

### 12. Indian-language output uses less native script than Spark 1.3
- **Measured:** share of native-script letters in 3–5 sentence explanations — Tamil 0.81, Hindi 0.88 for Spark Open vs 0.99 for Spark 1.3 (domain names counted against both).
- **What worked well:** OpenAI-compatible endpoint, native tool calling passed, image input by data URL, Telugu–English audio transcribed almost exactly, reasoning returned separately from the answer.
