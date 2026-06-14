#!/usr/bin/env bash
# refresh_all.sh — one-command refresh of every BAKED data source, then re-bake
# everything into index-live-auto.html (the deploy file). Live sources (HDB resale
# comps, HDB/URA price indices) need no refresh — they fetch fresh in the browser.
#
# Run manually:   URA_ACCESS_KEY=xxxx ./refresh_all.sh
# Or on a schedule (launchd/cron) — see AUTOMATION.md.
#
# Robust by design: if any single fetcher fails (network/site change), it keeps the
# last-good JSON and continues, so the dashboard never ends up with missing data.

set -uo pipefail
cd "$(dirname "$0")"
DASH="$(pwd)"
LOG="$DASH/refresh.log"
echo "================ refresh $(date '+%Y-%m-%d %H:%M:%S') ================" | tee -a "$LOG"

run(){ echo "-> $*" | tee -a "$LOG"; if "$@" >>"$LOG" 2>&1; then echo "   ok" | tee -a "$LOG"; else echo "   FAILED — keeping last-good data" | tee -a "$LOG"; fi; }

# 1. 3M-SORA (daily on business days) -> market-tab/rates.json
( cd market-tab && run python3 sora_verify.py )

# 2. New-launch board scraped from ERA -> market-tab/launches.json
( cd market-tab && run python3 era_scrape.py )

# 3. URA private caveats (weekly) -> ura-comps.json   [needs URA_ACCESS_KEY]
if [ -n "${URA_ACCESS_KEY:-}" ]; then
  run python3 ura_build_comps.py
else
  echo "   URA_ACCESS_KEY not set — skipping URA refresh (keeping last-good ura-comps.json)" | tee -a "$LOG"
fi

# 4. HDB block index (rarely changes — new BTOs complete) -> hdb-blocks.json
run python3 build_hdb_blocks.py

# 5. Re-bake all four JSON blocks into the deploy file
run python3 inject_data_all.py

echo "================ done $(date '+%H:%M:%S') — deploy: index-live-auto.html ================" | tee -a "$LOG"

# 6. (optional) auto-deploy to Netlify — uncomment after `netlify login` + `netlify link` once:
# command -v netlify >/dev/null && run netlify deploy --prod --dir="$DASH" --filter index-live-auto.html
