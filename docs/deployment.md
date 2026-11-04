# Deploying the demo-only app on Render

The public demo runs the Docker image with **live AI disabled**. It has no AI credentials and cannot call an AI provider.

## Why it cannot trigger paid AI calls (each point is tested or verified)

1. `Dockerfile` sets `ENABLE_LIVE_REVIEW=false` and `render.yaml` sets it again. A test (`test_deployment_safety.py`) fails if either is removed.
2. With that flag off, `POST /api/review` with `mode: "live"` returns HTTP 403 **before** any AI client is created. A test uses a client factory that raises if called, with both a server key and a request key present.
3. No API key variable is declared in `Dockerfile` or `render.yaml` (also tested). **Do not add `LLM_API_KEY` or `OPENROUTER_API_KEY` in the Render dashboard.**
4. The UI disables the "Live AI" option when `/api/config` says live reviews are off.
5. Verified in a locally built container started with a fake server key: `/api/config` reported `live_review_enabled: false`, and a live request with an extra header key returned 403.

## Connect Render (about 10 minutes)

1. Create a free account at https://render.com. Sign up with GitHub (`asaldhghn`) to make connecting easy.
2. In the Render dashboard choose **New > Blueprint**.
3. Click **Connect GitHub** (or "Configure account") and grant Render access to **only** the `ai-code-review-assistant` repository. Render can read private repositories, so the repo does **not** need to be public.
4. Select the repository and branch `main`. Render reads `render.yaml` and shows one web service, `ai-code-review-assistant`, plan **Free**, with `ENABLE_LIVE_REVIEW=false`. Click **Apply**.
5. Wait for the first build (a few minutes). When the status is **Live**, open the service URL shown at the top of the page.
6. Verify: `https://<your-service>.onrender.com/api/health` returns `{"status":"ok",...}`; load a sample in the UI, run a review, and confirm the "Demo mode" badge; the Live AI option should be disabled.
7. Tell me the URL. I will verify it, add it to the README and repository description, and commit.

## Things to expect

- **Cold starts.** Free web services sleep after about 15 minutes without traffic, and the first request afterwards can take about a minute. Open the URL before an interview or a recruiter call.
- **Auto-deploys.** Every push to `main` redeploys, so push only after CI is green.
- **Cost.** The free plan costs nothing; Render may change free-tier limits, so check the pricing page.
- **Public means public.** Anyone with the URL can use the demo, but the demo only runs the rule-based scanner and processes pasted text in memory; nothing is stored.

## Rolling back

Dashboard > the service > **Suspend** to take it offline, or delete the service. Nothing else is created.
