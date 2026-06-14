# JND Dashboard — Cloud Auto-Refresh Setup (GitHub Actions → Netlify)

Once set up, the dashboard re-fetches all data and redeploys **every day at 7am SGT**,
with no input from you and regardless of whether your Mac is on. There's also a manual
"Run workflow" button.

## What auto-updates, and how reliable it is

| Data | Source | In the cloud run |
|------|--------|------------------|
| HDB resale comps (Advisory) | data.gov.sg | **Live in browser** — always current, nothing to refresh |
| HDB & URA price indices (Market Pulse) | data.gov.sg | **Live in browser** — always current |
| URA private caveats (Advisory condo) | URA Data Service API | ✅ Refreshes reliably (official API + your key) |
| HDB block index (Advisory) | data.gov.sg | ✅ Refreshes reliably |
| 3M-SORA (Market Pulse) | MAS / broker scrape | ⚠️ May fail from cloud IPs → keeps last-good, logs it |
| New launches (Market Pulse) | ERA gallery scrape | ⚠️ May fail from cloud IPs → keeps last-good, logs it |

The two ⚠️ scrapers are fragile (they read third-party sites). If a cloud run can't reach
them, the dashboard simply keeps the last good values — it never breaks. If they get
blocked from cloud consistently, run `./refresh_all.sh` locally once in a while to top
those two up (everything else stays auto).

## One-time setup (≈15 min — you do this once)

### 1. Put this folder in a GitHub repo
```bash
cd "jnd-tools-dashboard"
git init && git add -A && git commit -m "JND dashboard + auto-refresh"
# create a PRIVATE repo on github.com, then:
git remote add origin https://github.com/<you>/jnd-dashboard.git
git push -u origin main
```
(The 70 MB `index-live-auto.html` pushes fine — GitHub's hard limit is 100 MB. The other
big HTML files are git-ignored.)

### 2. Create the Netlify site + get credentials
- On netlify.com: **Add new site → Deploy manually**, drag `index-live-auto.html` once to create it (rename to `index.html` on drop).
- **Site ID:** Site configuration → General → copy the **Site ID** (API ID).
- **Auth token:** User settings → Applications → **New access token** → copy it.

### 3. Add 3 secrets to the GitHub repo
Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name | Value |
|-------------|-------|
| `URA_ACCESS_KEY` | your URA Data Service key |
| `NETLIFY_AUTH_TOKEN` | the Netlify access token from step 2 |
| `NETLIFY_SITE_ID` | the Netlify Site ID from step 2 |

### 4. Done
- The workflow (`.github/workflows/refresh.yml`) now runs daily and on demand.
- Test it: repo → **Actions → Refresh & Deploy → Run workflow**. Watch it go green, then
  check your Netlify URL.

## How a run works (no git bloat)
The Action checks out the repo, regenerates the data files in the runner, re-bakes them
into a fresh `publish/index.html`, and deploys that to Netlify. Nothing is committed back,
so your git history never grows from refreshes.

## Editing the dashboard later
Edit `index-live-auto.html`, commit, push. (For data changes you never touch the HTML —
the Action bakes data in at deploy time.)
