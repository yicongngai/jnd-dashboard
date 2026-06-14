#!/usr/bin/env python3
"""
ura_fetch.py — Pull URA private residential transactions and aggregate them into
ura-comps.json for the JND Tools dashboard (NL Selection Framework).

STATUS: ready for your URA Access Key. NOT yet run (no key, and to avoid hitting URA
without one). Once you have the key, set URA_ACCESS_KEY (env var or below) and run.

URA Data Service flow:
  1. GET .../insertNewToken/v1   with header AccessKey            -> daily Token
  2. GET .../invokeUraDS/v1?service=PMI_Resi_Transaction&batch=N  with AccessKey + Token
     (batches 1..4 cover roughly the last 5 years)

NOTE: endpoint paths + response field names follow the documented v1 service but MUST be
confirmed against the current URA docs once you have access — URA versions this API.
The HTTP/token logic is solid; only the parse step (marked CONFIRM) may need a tweak.
"""

import os
import json
import sys
import statistics
from collections import defaultdict
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    sys.exit("pip install requests first.")

# --- 1. credentials -----------------------------------------------------------
URA_ACCESS_KEY = os.environ.get("URA_ACCESS_KEY", "PASTE_YOUR_URA_ACCESS_KEY_HERE")

TOKEN_URL  = "https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1"
DATA_URL   = "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1"
SERVICE    = "PMI_Resi_Transaction"
BATCHES    = [1, 2, 3, 4]
OUT_JSON   = "ura-comps.json"
UA         = "JND-Tools-DataPrep/1.0"


def get_token():
    r = requests.get(TOKEN_URL, headers={"AccessKey": URA_ACCESS_KEY, "User-Agent": UA}, timeout=30)
    r.raise_for_status()
    j = r.json()
    tok = j.get("Result")
    if not tok:
        sys.exit(f"No token returned: {j}")
    return tok


def fetch_batch(token, batch):
    r = requests.get(
        DATA_URL,
        params={"service": SERVICE, "batch": batch},
        headers={"AccessKey": URA_ACCESS_KEY, "Token": token, "User-Agent": UA},
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("Result", [])


def parse_contract_date(s):
    """URA contractDate is 'MMYY' e.g. '0526' = May 2026.  CONFIRM against live data."""
    try:
        mm, yy = int(s[:2]), int(s[2:])
        return 2000 + yy, mm
    except Exception:
        return None


def aggregate(projects):
    """Aggregate transactions into per-district stats. CONFIRM field names below."""
    now = datetime.now(timezone.utc)
    cutoff_12 = (now.year * 12 + now.month) - 12
    cutoff_24 = (now.year * 12 + now.month) - 24

    psf_12 = defaultdict(list)      # district -> [psf] last 12 mo
    psf_prev = defaultdict(list)    # district -> [psf] 12-24 mo ago
    count_12 = defaultdict(int)     # district -> txn count last 12 mo (turnover proxy)

    for proj in projects:
        district = str(proj.get("street") and proj.get("district") or proj.get("district", "NA"))
        for t in proj.get("transaction", []):          # CONFIRM: key 'transaction'
            d = parse_contract_date(t.get("contractDate", ""))
            if not d:
                continue
            ym = d[0] * 12 + d[1]
            try:
                price = float(t.get("price"))
                area_sqm = float(t.get("area"))         # CONFIRM: sqm vs sqft (typeOfArea)
            except (TypeError, ValueError):
                continue
            if area_sqm <= 0:
                continue
            psf = price / (area_sqm * 10.7639)
            dist = str(t.get("district", district))
            if ym > cutoff_12:
                psf_12[dist].append(psf)
                count_12[dist] += int(t.get("noOfUnits", 1) or 1)
            elif ym > cutoff_24:
                psf_prev[dist].append(psf)

    out = {}
    for dist in sorted(set(list(psf_12) + list(psf_prev))):
        med_now = statistics.median(psf_12[dist]) if psf_12[dist] else None
        med_prev = statistics.median(psf_prev[dist]) if psf_prev[dist] else None
        yoy = ((med_now - med_prev) / med_prev * 100) if (med_now and med_prev) else None
        out[dist] = {
            "median_psf": round(med_now) if med_now else None,
            "yoy_pct": round(yoy, 1) if yoy is not None else None,
            "txn_count_12m": count_12.get(dist, 0),
        }
    return out


def main():
    if "PASTE_YOUR" in URA_ACCESS_KEY:
        sys.exit("Set URA_ACCESS_KEY (env var or edit the script) before running.")
    token = get_token()
    projects = []
    for b in BATCHES:
        projects += fetch_batch(token, b)
        print(f"  batch {b}: {len(projects)} projects so far")
    districts = aggregate(projects)
    payload = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "URA Data Service — PMI_Resi_Transaction",
        "districts": districts,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {OUT_JSON}: {len(districts)} districts.")


if __name__ == "__main__":
    main()
