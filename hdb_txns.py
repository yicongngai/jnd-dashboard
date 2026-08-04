#!/usr/bin/env python3
"""
hdb_txns.py — HDB resale transactions (last 12 months) for Market Pulse
"Recent Transactions", geolocated per block.

Sources (both keyless):
  - data.gov.sg resale dataset d_8b84c4ee58e3cfc0ece0d773c8ca6abc (live, ~2.1k/mo)
  - OneMap search for block coordinates ("466 HOUGANG AVE 8" style — strip 'BLK';
    HDB street abbreviations resolve fine). Cache: hdb-block-coords.json
    {"BLOCK|STREET": [x,y] | null}; incremental (cap per run) like onemap-blocks.

Output hdb-txns.json:
  {"as_of","months",N blocks:[{"n":"466 HOUGANG AVE 8","tn":"HOUGANG","x":..,"y":..,
   "r":[[MMYY, flatType, storeyLo, sqm, price, flatModel], ...]}]}
  flatType : 1..5 rooms, "E"=Executive, "M"=Multi-gen. MMYY matches ura-comps.
  flatModel: "A"=Apartment "P"=Premium Apartment "M"=Maisonette "L"=Premium Apt
             Loft "Q"/"I"/"J"=other maisonettes "G"/"3"=multi-gen, lowercase for
             the ordinary models, "?"=unrecognised. Needed because flat_type
             "EXECUTIVE" mixes Apartment, Premium Apartment and Maisonette.
Called daily from build_hdb_blocks.py (never breaks that build).
"""
import json, os, re, sys, time, urllib.error, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "hdb-block-coords.json")
OUT = os.path.join(HERE, "hdb-txns.json")
DS = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"
SGT_NOW = datetime.now(timezone.utc) + timedelta(hours=8)
UA = {"User-Agent": "Mozilla/5.0 (JND-Tools)"}
FT = {"1 ROOM": 1, "2 ROOM": 2, "3 ROOM": 3, "4 ROOM": 4, "5 ROOM": 5,
      "EXECUTIVE": "E", "MULTI-GENERATION": "M"}

# flat_type alone is NOT enough. "EXECUTIVE" covers the Executive Apartment, the
# Executive Maisonette and the Premium Apartment, which are different products at
# different prices — around Pioneer the maisonettes run ~$60 psf under the
# apartments. Quoting them together overstated the EA median by $16,500. Keep the
# model, one letter, so a caller can split them.
FM = {"apartment": "A", "premium apartment": "P", "premium apartment loft": "L",
      "maisonette": "M", "premium maisonette": "Q", "improved-maisonette": "I",
      "model a-maisonette": "J", "multi generation": "G", "3gen": "3",
      "improved": "i", "new generation": "n", "model a": "a", "model a2": "b",
      "standard": "s", "simplified": "z", "adjoined flat": "j", "terrace": "t",
      "dbss": "d", "type s1": "1", "type s2": "2"}


def fm(model):
    """flat_model -> one letter. Unknown models keep a '?' rather than being
    silently folded into a neighbour."""
    return FM.get((model or "").strip().lower(), "?")


def _get(url, tries=5):
    """data.gov.sg returns 429 under a tight loop. Back off rather than lose the
    month, otherwise a rate limit silently truncates the dataset."""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < tries - 1:
                time.sleep(3 * (i + 1))
                continue
            raise


def months_back(n=12):
    y, m = SGT_NOW.year, SGT_NOW.month
    out = [f"{y}-{m:02d}"]                      # include the current partial month
    for _ in range(n):
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        out.append(f"{y}-{m:02d}")
    return out


def fetch_month(month):
    rows, offset = [], 0
    while True:
        filt = urllib.parse.quote(json.dumps({"month": month}))
        u = (f"https://data.gov.sg/api/action/datastore_search?resource_id={DS}"
             f"&filters={filt}&limit=5000&offset={offset}")
        d = _get(u)
        rec = d.get("result", {}).get("records", [])
        rows += rec
        if len(rec) < 5000:
            return rows
        offset += 5000


class Transient(Exception):
    """Transport/rate-limit failure — result is UNKNOWN and must NOT be cached
    (a 429 cached as null poisoned 35% of the first backfill attempt)."""


def geocode(block, street):
    """[x,y], or None ONLY on a genuine no-match. Raises Transient otherwise."""
    q = f"{block} {street}"
    u = ("https://www.onemap.gov.sg/api/common/elastic/search?searchVal="
         + urllib.parse.quote(q) + "&returnGeom=Y&getAddrDetails=Y&pageNum=1")
    try:
        d = _get(u)
    except Exception as e:  # noqa: BLE001 — includes HTTP 429
        raise Transient(str(e))
    blku = str(block).upper()
    for r in d.get("results") or []:
        if str(r.get("BLK_NO", "")).upper() == blku and r.get("X"):
            try:
                return [int(float(r["X"])), int(float(r["Y"]))]
            except (ValueError, TypeError):
                continue
    return None


def run(geocode_cap=150):
    months = months_back(12)
    txns = []
    for mo in months:
        try:
            txns += fetch_month(mo)
        except Exception as e:  # noqa: BLE001
            print(f"hdb_txns: month {mo} fetch failed ({e}) — continuing")
    if len(txns) < 5000:
        print(f"hdb_txns: only {len(txns)} txns fetched — suspicious, keeping last-good")
        return 1

    try:
        cache = json.load(open(CACHE, encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}

    # group per block
    blocks = {}
    for t in txns:
        key = f"{t.get('block','').strip()}|{t.get('street_name','').strip()}".upper()
        b = blocks.setdefault(key, {"n": f"{t.get('block','').strip()} {t.get('street_name','').strip()}".upper(),
                                    "tn": t.get("town", ""), "r": []})
        mo = t.get("month", "")           # "2026-06" -> MMYY "0626"
        mmyy = mo[5:7] + mo[2:4] if len(mo) == 7 else ""
        storey = re.match(r"(\d+)", t.get("storey_range", "") or "")
        try:
            b["r"].append([mmyy, FT.get(t.get("flat_type", ""), 0),
                           int(storey.group(1)) if storey else 0,
                           round(float(t.get("floor_area_sqm", 0))),
                           int(float(t.get("resale_price", 0))),
                           # APPENDED, never inserted — consumers read these rows
                           # positionally, so a new trailing field is invisible
                           # to them and an inserted one corrupts every read.
                           fm(t.get("flat_model", ""))])
        except (ValueError, TypeError):
            continue

    # geocode missing blocks (incremental)
    missing = [k for k in blocks if k not in cache]
    todo = missing[:geocode_cap]
    strikes = 0
    for i, k in enumerate(todo, 1):
        blk, street = k.split("|", 1)
        try:
            cache[k] = geocode(blk, street)
            strikes = 0
        except Transient:
            strikes += 1
            wait = min(60, 5 * strikes)
            print(f"  rate-limited/err on {k} — pausing {wait}s (not cached)")
            time.sleep(wait)
            if strikes >= 5:
                print("  repeated transport failures — stopping this run's geocoding early")
                break
        if i % 100 == 0:
            print(f"  hdb geocode {i}/{len(todo)}")
            json.dump(cache, open(CACHE, "w"))
        time.sleep(0.22)
    json.dump(cache, open(CACHE, "w"))

    placed, skipped = [], 0
    for k, b in blocks.items():
        xy = cache.get(k)
        if xy:
            b["x"], b["y"] = xy
            b["r"].sort(key=lambda r: (r[0][2:4], r[0][0:2]), reverse=True)
            placed.append(b)
        else:
            skipped += 1
    out = {"as_of": SGT_NOW.strftime("%Y-%m-%d"), "months": 12,
           "source": "data.gov.sg HDB resale (registration) · coords via OneMap",
           "blocks": placed}
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    sz = os.path.getsize(OUT) / 1e6
    print(f"hdb_txns: {len(txns):,} txns · {len(placed):,} blocks placed, "
          f"{skipped} awaiting geocode ({len(missing)-len(todo)} still queued) · {sz:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(run(geocode_cap=20000 if "--backfill" in sys.argv else 150))
