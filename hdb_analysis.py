#!/usr/bin/env python3
"""Demonstrate age-blending in HDB town-level medians, and test an age-banded fix."""
import json, urllib.request, urllib.parse, statistics, re
from collections import defaultdict

RES = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"

def fetch(town, ft, limit=5000):
    q = {"resource_id": RES,
         "filters": json.dumps({"town": town, "flat_type": ft}),
         "sort": "month desc", "limit": limit}
    url = "https://data.gov.sg/api/action/datastore_search?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)["result"]["records"]

def rem_years(rec):
    s = rec.get("remaining_lease", "")
    m = re.match(r"(\d+)\s*year", str(s))
    if m: return int(m.group(1))
    lc = rec.get("lease_commence_date")
    if lc:
        yr = int(rec["month"][:4]); return 99 - (yr - int(lc))
    return None

def psf(rec):
    sqm = float(rec["floor_area_sqm"]);
    return float(rec["resale_price"]) / (sqm * 10.7639) if sqm else None

def med(xs): return statistics.median(xs) if xs else 0

for TOWN, FT in [("QUEENSTOWN","4 ROOM"), ("BUKIT MERAH","4 ROOM"), ("ANG MO KIO","4 ROOM")]:
    recs = fetch(TOWN, FT)
    # last 12 months window
    latest = recs[0]["month"]; ly, lm = int(latest[:4]), int(latest[5:7])
    cutoff = ly*12+lm - 11
    win = [r for r in recs if int(r["month"][:4])*12+int(r["month"][5:7]) >= cutoff]
    prices = [float(r["resale_price"]) for r in win]
    print(f"\n===== {TOWN} {FT}  (last 12mo: {len(win)} txns) =====")
    print(f"  NAIVE town-wide median price: ${med(prices):,.0f}   psf ${med([p for p in (psf(r) for r in win) if p]):,.0f}")
    # bucket by remaining-lease decade
    buckets = defaultdict(list)
    for r in win:
        ry = rem_years(r)
        if ry is None: continue
        buckets[(ry//10)*10].append((float(r["resale_price"]), psf(r)))
    print("  By remaining-lease band:")
    for band in sorted(buckets, reverse=True):
        rows = buckets[band]
        mp = med([x[0] for x in rows]); mpsf = med([x[1] for x in rows if x[1]])
        print(f"    {band}-{band+9} yrs left: n={len(rows):3d}  med ${mp:>9,.0f}  psf ${mpsf:,.0f}")
    # demonstrate the spread: youngest vs oldest band median price
    bands = sorted(buckets)
    if len(bands) >= 2:
        old = med([x[0] for x in buckets[bands[0]]])
        new = med([x[0] for x in buckets[bands[-1]]])
        if old:
            print(f"  >> SPREAD oldest vs newest band: ${old:,.0f} -> ${new:,.0f}  ({(new-old)/old*100:+.0f}%)")
