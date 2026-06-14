# JND Tools Dashboard

**The dashboard is ONE file: [`index-live-auto.html`](index-live-auto.html)** — open it in any browser.
Live, auto-updating version: **https://jnd-tools-dashboard.netlify.app** (refreshes daily, 7am SGT).

---

## What you actually use
| | |
|---|---|
| ⭐ **`index-live-auto.html`** | **THE dashboard.** Advisory valuations (HDB + condo) and Market Pulse, all baked into this one file. This is the only file you ever open. |
| 🌐 **https://jnd-tools-dashboard.netlify.app** | The deployed, self-updating copy. Bookmark this. |

## How it stays up to date (you don't touch any of this)
The cloud (GitHub Actions → Netlify) re-runs the pipeline every morning and redeploys.

| File | Role |
|---|---|
| `.github/workflows/refresh.yml` | The daily cloud refresh + deploy |
| `refresh_all.sh` | The same pipeline as a one-command **local** fallback |
| `AUTOMATION-SETUP.md` | How the cloud automation is wired (secrets, etc.) |

## Under the hood (only matters if data ever needs a manual refresh)
| File | Builds |
|---|---|
| `build_hdb_blocks.py` → `hdb-blocks.json` | HDB block index (towns, year built, flat types) |
| `ura_build_comps.py` → `ura-comps.json` | URA private caveats (needs `URA_ACCESS_KEY`) |
| `market-tab/sora_verify.py` → `market-tab/rates.json` | 3M-SORA (multi-source consensus) |
| `market-tab/era_scrape.py` → `market-tab/launches.json` | New-launch board |
| `inject_data_all.py` | Bakes all four data files into `index-live-auto.html` |

Live data (HDB resale comps, HDB/URA price indices) is fetched fresh in the browser — no file needed.

## Manual refresh (rarely needed)
```bash
URA_ACCESS_KEY=<your key> ./refresh_all.sh
```
The cloud then auto-deploys on its next run, or drag `index-live-auto.html` onto Netlify.

## Links
- Live site: https://jnd-tools-dashboard.netlify.app
- Repo: https://github.com/yicongngai/jnd-dashboard
