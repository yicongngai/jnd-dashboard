#!/usr/bin/env python3
"""
ura_build_comps.py — Build a COMPACT project-level private-comps file for the
JND Advisory auto-valuation (same-project / size / recency / radius matching).

Distinct from ura_fetch.py (which makes district aggregates for the NL framework).
Output: ura-comps.json  +  prints size & coverage.

Key via env: URA_ACCESS_KEY
"""
import os, json, sys, re, time
import requests

KEY = os.environ["URA_ACCESS_KEY"]
UA  = "Mozilla/5.0 (JND-Tools DataPrep)"
BASE = "https://eservice.ura.gov.sg/uraDataService"

def _get(url, headers, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, headers=headers, timeout=120)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            return r.json()
        except Exception as e:
            if i == tries-1: raise
            time.sleep(2)

def token():
    j = _get(BASE+"/insertNewToken/v1", {"AccessKey": KEY, "User-Agent": UA})
    t = j.get("Result")
    if not t: sys.exit(f"No token: {j}")
    return t

def tenure_to_remyears(s, contract_yymm):
    """'Freehold' -> 0 (sentinel). '99 yrs lease commencing from 2018' -> remaining yrs from now-ish."""
    if not s: return None
    if "freehold" in s.lower(): return 0  # 0 == freehold sentinel
    m = re.search(r"(\d+)\s*yr.*from\s*(\d{4})", s)
    if m:
        dur, start = int(m.group(1)), int(m.group(2))
        # remaining as of 2026
        return max(0, dur - (2026 - start))
    m2 = re.search(r"(\d+)\s*yr", s)
    return int(m2.group(1)) if m2 else None

PT = {"Condominium":"C","Apartment":"A","Executive Condominium":"EC","Terrace":"T",
      "Semi-detached":"SD","Detached":"D","Strata Terrace":"ST","Strata Semi-detached":"SSD",
      "Strata Detached":"SD2"}

def main():
    tok = token()
    hdr = {"AccessKey": KEY, "Token": tok, "User-Agent": UA}
    projects = {}
    total_txn = 0
    for b in (1,2,3,4):
        url = BASE+f"/invokeUraDS/v1?service=PMI_Resi_Transaction&batch={b}"
        j = _get(url, hdr)
        res = j.get("Result", [])
        print(f"batch {b}: {len(res)} projects, status={j.get('Status')}")
        for p in res:
            name = p.get("project","?")
            key = name + "|" + (p.get("marketSegment") or "")
            entry = projects.setdefault(key, {
                "p": name, "st": p.get("street",""), "seg": p.get("marketSegment",""),
                "x": p.get("x"), "y": p.get("y"), "t": []
            })
            for t in p.get("transaction", []):
                try:
                    area_sqm = float(t["area"]); price = int(float(t["price"]))
                except Exception:
                    continue
                sqft = round(area_sqm*10.7639)
                rem = tenure_to_remyears(t.get("tenure",""), t.get("contractDate"))
                entry["t"].append([
                    sqft, price, t.get("contractDate"),
                    rem if rem is not None else -1,
                    PT.get(t.get("propertyType",""), t.get("propertyType","")[:2]),
                    int(t.get("typeOfSale","0") or 0),
                    t.get("district","")
                ])
                total_txn += 1
    # drop empty
    out = {"as_of":"2026-06",
           "source":"URA Data Service · PMI_Resi_Transaction (private caveats, ~3yr)",
           "fields":"t=[sqft,price,contractMMYY,remLeaseYrs(0=FH,-1=na),propType,saleType(1new/2sub/3resale),district]",
           "projects":[v for v in projects.values() if v["t"]]}
    with open("ura-comps.json","w") as f:
        json.dump(out, f, separators=(",",":"))
    sz = os.path.getsize("ura-comps.json")
    print(f"\nWROTE ura-comps.json: {len(out['projects'])} projects, {total_txn} txns, {sz/1e6:.2f} MB")
    # quick coverage peek
    segs = {}
    for v in out["projects"]:
        segs[v["seg"]] = segs.get(v["seg"],0)+1
    print("segments:", segs)

if __name__ == "__main__":
    main()
