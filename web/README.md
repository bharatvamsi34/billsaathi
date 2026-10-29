# BillSaathi web app

Mobile-first Next.js app (static export) for the BillSaathi checks API: capture a bill photo,
screenshot or pasted message, watch the agent's checks live, and get a SAFE / CAUTION / SCAM
verdict with the evidence behind it. **Sandbox demo — no real payments; all data is synthetic.**

```
npm ci
npm run dev                      # http://localhost:3000, API at http://localhost:8000
npm test && npm run typecheck && npm run lint
NEXT_PUBLIC_API_BASE=https://<api-host> npm run build   # static site in out/
```

- `scripts/build-samples.mjs` builds the "Try a sample" gallery from `data/synthetic`
  (dev-split items only; it refuses test-split items). Runs before every build.
- Interface text is in `src/lib/i18n.ts` (English, Telugu, Hindi).
- Hosted on Azure Static Web Apps; see `infra/deploy.ps1` steps 11–12.
