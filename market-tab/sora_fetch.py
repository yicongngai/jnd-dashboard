#!/usr/bin/env python3
"""
sora_fetch.py v3 — update 3M Compounded SORA in rates.json from the MAS OFFICIAL API only.

No scraping (the fragile housingloansg fallback was removed for robustness). Behaviour:
  - MAS API reachable  -> update value, status='live'  (auto-fresh)
  - MAS API unavailable -> HOLD the existing maintained value, status='maintained'
                           (nothing breaks; value changes only when MAS returns or you edit it)

SORA moves a few bps/day and the dashboard already says "confirm with banker", so a held
value is fine. When MAS is back online this auto-switches to live with no code change.
"""
import json, urllib.request
from datetime import datetime, timezone, timedelta

RATES = "rates.json"
UA = {"User-Agent": "Mozilla/5.0 (JND-Tools)"}
MAS = ("https://eservices.mas.gov.sg/api/action/datastore/search.json"
       "?resource_id=9a0bf149-308c-4bb2-af51-37affd1ac6bb&sort=end_of_day%20desc&limit=1")

def sgt_today():
    return (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d")

def from_mas():
    try:
        with urllib.request.urlopen(urllib.request.Request(MAS, headers=UA), timeout=30) as r:
            raw = r.read().decode("utf-8-sig", "replace")
        if not raw or "<html" in raw[:200].lower() or "maintenance" in raw[:400].lower():
            return None
        rec = json.loads(raw)["result"]["records"][0]
        for k, v in rec.items():
            if "sora" in k.lower() and "3" in k and v not in (None, ""):
                return round(float(v), 4), rec.get("end_of_day", "")
    except Exception as e:
        print("  MAS API unavailable:", e)
    return None

def main():
    data = json.load(open(RATES))
    s = data.setdefault("sora_3m", {})
    for k in ("sources", "n_sources", "range"):  # drop legacy multi-scrape fields
        s.pop(k, None)
    hit = from_mas()
    if hit:
        val, asof = hit
        s.update({"value": val, "as_of": asof or sgt_today(),
                  "source": "MAS official API", "status": "live"})
        print(f"  SORA live from MAS: {val}% ({s['as_of']})")
    else:
        s.update({"status": "maintained", "checked": sgt_today(),
                  "source": "maintained (MAS API in maintenance)"})
        print(f"  MAS unavailable — holding maintained SORA {s.get('value')}% (set {s.get('as_of')})")
    json.dump(data, open(RATES, "w"), indent=2)

if __name__ == "__main__":
    main()
