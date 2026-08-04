#!/usr/bin/env python3
"""
ura_build_comps.py — Build a COMPACT project-level private-comps file for the
JND Advisory auto-valuation (same-project / size / recency / radius matching).

Distinct from ura_fetch.py (which makes district aggregates for the NL framework).
Output: ura-comps.json  +  prints size & coverage.

Key via env: URA_ACCESS_KEY
"""
import os, json, sys, re, time
from datetime import datetime, timezone, timedelta
import requests

def _load_key():
    """URA_ACCESS_KEY from env, else the gitignored .ura_key file next to this script."""
    k = os.environ.get("URA_ACCESS_KEY", "").strip()
    if k:
        return k
    kf = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ura_key")
    try:
        return open(kf, encoding="utf-8").read().strip()
    except OSError:
        sys.exit("No URA key — set URA_ACCESS_KEY or write it to jnd-tools-dashboard/.ura_key")


KEY = _load_key()
UA  = "Mozilla/5.0 (JND-Tools DataPrep)"
BASE = "https://eservice.ura.gov.sg/uraDataService"

# URA's bot protection blocks datacentre IPs. Proven 1 Aug 2026: the SAME key
# returns 200 from Justin's home connection and 403 from every GitHub runner —
# and a *wrong* key does NOT 403, it returns 200 with "Invalid Access Key". So the
# 403 is the WAF, never the credential, and rotating the key cannot fix it.
#
# If a Zyte key is present we route through a Singapore residential IP, which is
# the only way the cloud can reach URA. Without one we go direct, which still
# works from the station. Either way a failure keeps the last-good file.
UNLOCKER = os.environ.get("UNLOCKER_API_KEY", "").strip()
ZYTE = "https://api.zyte.com/v1/extract"


def _via_zyte(url, headers):
    body = {"url": url, "httpResponseBody": True,
            "geolocation": "SG",
            "customHttpRequestHeaders":
                [{"name": k, "value": v} for k, v in headers.items()]}
    r = requests.post(ZYTE, auth=(UNLOCKER, ""), json=body, timeout=180)
    r.raise_for_status()
    import base64
    return json.loads(base64.b64decode(r.json()["httpResponseBody"]))


def _get(url, headers, tries=3):
    for i in range(tries):
        try:
            if UNLOCKER:
                return _via_zyte(url, headers)
            r = requests.get(url, headers=headers, timeout=120)
            r.raise_for_status()
            # URA mixes latin-1 bytes into an otherwise utf-8 stream (accented
            # project names), which makes a strict decode raise mid-payload and
            # lose the whole batch. Replace the bad bytes rather than fail.
            r.encoding = r.apparent_encoding or "utf-8"
            try:
                return r.json()
            except (UnicodeDecodeError, ValueError):
                return json.loads(r.content.decode("utf-8", "replace"))
        except Exception:
            if i == tries - 1:
                raise
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
            # URA sends landed caveats as ONE record PER STREET (own street/x/y),
            # all named "LANDED HOUSING DEVELOPMENT". Keying by name collapsed
            # ~5.4k landed txns into 3 island-wide buckets — key landed by street
            # so "around me" distances work in landed enclaves.
            if name == "LANDED HOUSING DEVELOPMENT":
                key = name + "|" + (p.get("street") or "") + "|" + (p.get("marketSegment") or "")
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
                    t.get("district",""),
                    # floorRange, e.g. "06-10". URA bands floors in fives and never
                    # publishes the exact level, but the band is the difference
                    # between a rough comp and a usable one — two 990 sqft caveats
                    # at Tembusu Grand only compared honestly once the band showed
                    # both were 06-10. APPENDED, never inserted: the dashboard reads
                    # these rows positionally (t[0]..t[5]), so a new trailing field
                    # is invisible to it and an inserted one would corrupt every read.
                    t.get("floorRange") or "",
                ])
                total_txn += 1
    # drop empty
    # as_of = BUILD date (this script runs daily; freshness monitors pull recency).
    # latest_month = newest contract month in the data (URA caveats lodge with weeks
    # of lag, so this trails ~4-6 weeks; monitored separately with a wider limit).
    mmyy = [t[2] for v in projects.values() for t in v["t"] if t[2] and len(str(t[2])) == 4]
    latest = max(mmyy, key=lambda m: (int(m[2:]), int(m[:2]))) if mmyy else None
    out = {"as_of": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
           "latest_month": f"20{latest[2:]}-{latest[:2]}" if latest else None,
           "source":"URA Data Service · PMI_Resi_Transaction (private caveats, ~3yr)",
           "fields":"t=[sqft,price,contractMMYY,remLeaseYrs(0=FH,-1=na),propType,saleType(1new/2sub/3resale),district,floorRange]",
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
    # OneMap block footprints for Near Me (keyless; incremental top-up for new
    # projects, then embeds "b" into ura-comps.json). Never breaks the comps build.
    try:
        import onemap_blocks
        onemap_blocks.run(cap=120)
    except Exception as e:
        print("onemap blocks skipped:", e)

if __name__ == "__main__":
    main()
