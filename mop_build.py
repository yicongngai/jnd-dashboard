#!/usr/bin/env python3
"""mop_build.py — the MOP pipeline: which HDB flats become sellable, when and where.

    python3 mop_build.py            # refresh mop-data.json
    python3 mop_build.py --check    # report what would change, write nothing

WHAT MOP IS AND WHAT THIS CAN HONESTLY SAY
------------------------------------------
An HDB flat cannot be sold until its owners have lived in it for the Minimum
Occupation Period, five years for a BTO, counted from KEY COLLECTION. HDB does not
publish key-collection dates per block. What it does publish, in HDB Property
Information, is the year each block was COMPLETED. Keys follow completion closely, so

    MOP year  =  year_completed + 5

is the standard approximation and it is what this uses. It is an estimate to the year,
never to the month, and the file says so wherever it is displayed. A block completed
late in a year can sit either side of the line.

Two other honest limits. Resale buyers serve their own five years from THEIR purchase,
so a block past its BTO wave still produces sellers this file cannot see. And flats
completed before 2010 were sold under earlier occupation rules; they are long past MOP
either way, so the approximation only ever matters for the forward pipeline.

WHY IT MATTERS TO A PROPERTY AGENT
----------------------------------
A flat reaching MOP is a household that can suddenly sell, and the ones who do are
overwhelmingly upgraders. The pipeline is therefore a map of where next year's sellers
and next year's condo buyers will physically be.

DATA
----
  data.gov.sg  HDB Property Information (d_17f5382f...) — blocks, completion year,
               dwelling units per flat type. Refreshed by HDB, so re-pulling keeps
               this current as new blocks complete and as new towns appear.
  OneMap       coordinates for blocks the local cache has never seen. The cache was
               built from resale transactions, so brand-new BTO blocks — exactly the
               pipeline this file is about — are missing from it and must be looked up.
"""
import argparse
import collections
import datetime
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "mop-data.json")
GEO_CACHE = os.path.join(HERE, "mop-geocache.json")
COORDS = os.path.join(HERE, "hdb-block-coords.json")
RES = "d_17f5382f26140b1fdae0ba2ef6239d2f"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"}

TOWNS = {
    "AMK": "Ang Mo Kio", "BB": "Bukit Batok", "BD": "Bedok", "BH": "Bishan",
    "BM": "Bukit Merah", "BP": "Bukit Panjang", "BT": "Bukit Timah",
    "CCK": "Choa Chu Kang", "CL": "Clementi", "CT": "Central Area",
    "GL": "Geylang", "HG": "Hougang", "JE": "Jurong East", "JW": "Jurong West",
    "KWN": "Kallang/Whampoa", "MP": "Marine Parade", "PG": "Punggol",
    "PRC": "Pasir Ris", "QT": "Queenstown", "SB": "Sembawang",
    "SGN": "Serangoon", "SK": "Sengkang", "TAP": "Tampines", "TG": "Tengah",
    "TP": "Toa Payoh", "WL": "Woodlands", "YS": "Yishun",
}
# SOLD flats only. A rental flat is never sold, so it has no Minimum Occupation
# Period and can never become resale supply — counting it as "reaching MOP" is simply
# wrong. 465A Bukit Batok West Ave 8 is the clean case: 144 one-room and 128 two-room
# RENTAL units, nothing sold, and the first version put all 272 into the 2026 wave.
# Across the pipeline this over-counted by 1,662 flats. 1-room sold is in the list too;
# leaving it out silently blanked the flat mix on the few blocks that have them.
TYPES = [("1room_sold", "1R"), ("2room_sold", "2R"), ("3room_sold", "3R"),
         ("4room_sold", "4R"), ("5room_sold", "5R"), ("exec_sold", "Exec"),
         ("multigen_sold", "Multi-gen"), ("studio_apartment_sold", "Studio")]
SOLD_COLS = [c for c, _ in TYPES]

# --- SVY21 -> WGS84 -------------------------------------------------------------
# The local coordinate cache is in SVY21, Singapore's own projection, because that is
# what OneMap returned when it was built. Converting is exact, so 8,450 blocks come
# back for free rather than being re-looked-up one HTTP request at a time.
_A, _F = 6378137.0, 1 / 298.257223563
_ORIG_LAT, _ORIG_LON = math.radians(1.366666), math.radians(103.833333)
_FE, _FN, _K = 28001.642, 38744.572, 1.0


def _calcM(lat, n_):
    """Meridian distance. Canonical SVY21 series — the first version of this used a
    different expansion from memory and put every block 660 m too far south, which the
    OneMap check below caught."""
    A0 = 1 - n_ + (5 * n_ ** 2 / 4) * (1 - n_) + (81 * n_ ** 4 / 64) * (1 - n_)
    A2 = 1.5 * (n_ - n_ ** 2 + (7 * n_ ** 3 / 8) * (1 - n_) + (55 * n_ ** 4 / 64))
    A4 = (15 / 16) * (n_ ** 2 - n_ ** 3 + (3 * n_ ** 4 / 4) * (1 - n_))
    A6 = (35 / 48) * (n_ ** 3 - n_ ** 4)
    A8 = (315 / 512) * n_ ** 4
    return _A * (A0 * lat - A2 * math.sin(2 * lat) + A4 * math.sin(4 * lat)
                 - A6 * math.sin(6 * lat) + A8 * math.sin(8 * lat))


def svy21_to_wgs84(e, n):
    b = _A * (1 - _F)
    e2 = (2 * _F) - (_F * _F)
    n_ = (_A - b) / (_A + b)
    G = _A * (1 - n_) * (1 - n_ ** 2) * (1 + 2.25 * n_ ** 2 + (225 / 64) * n_ ** 4) * (math.pi / 180)

    Nprime = (n - _FN) / _K
    Mprime = _calcM(_ORIG_LAT, n_) + Nprime
    sigma = (Mprime * math.pi) / (180 * G)
    latP = (sigma
            + ((3 * n_ / 2) - (27 * n_ ** 3 / 32)) * math.sin(2 * sigma)
            + ((21 * n_ ** 2 / 16) - (55 * n_ ** 4 / 32)) * math.sin(4 * sigma)
            + (151 * n_ ** 3 / 96) * math.sin(6 * sigma)
            + (1097 * n_ ** 4 / 512) * math.sin(8 * sigma))

    s, c, t = math.sin(latP), math.cos(latP), math.tan(latP)
    rho = _A * (1 - e2) / ((1 - e2 * s * s) ** 1.5)
    v = _A / math.sqrt(1 - e2 * s * s)
    psi = v / rho
    E = (e - _FE) / _K
    x = E / (_K * v)
    x2 = x * x

    lat = latP + (-t / (_K * rho)) * (E * x / 2) \
        + (t / (_K * rho)) * ((E * x2 * x) / 24) * (-4 * psi ** 2 + 9 * psi * (1 - t * t) + 12 * t * t) \
        - (t / (_K * rho)) * ((E * x2 * x2 * x) / 720) * (
            8 * psi ** 4 * (11 - 24 * t * t) - 12 * psi ** 3 * (21 - 71 * t * t)
            + 15 * psi ** 2 * (15 - 98 * t * t + 15 * t ** 4)
            + 180 * psi * (5 * t * t - 3 * t ** 4) + 360 * t ** 4)
    lon = _ORIG_LON + x / c - (x2 * x / (6 * c)) * (psi + 2 * t * t) \
        + (x2 * x2 * x / (120 * c)) * (
            -4 * psi ** 3 * (1 - 6 * t * t) + psi ** 2 * (9 - 68 * t * t)
            + 72 * psi * t * t + 24 * t ** 4)
    return round(math.degrees(lat), 6), round(math.degrees(lon), 6)


# --- sources --------------------------------------------------------------------
def fetch_blocks():
    out, off = [], 0
    while True:
        q = {"resource_id": RES, "limit": 5000, "offset": off}
        u = "https://data.gov.sg/api/action/datastore_search?" + urllib.parse.urlencode(q)
        j = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120))["result"]
        recs = j["records"]
        if not recs:
            break
        out += recs
        off += len(recs)
        if off >= int(j.get("total", 0)):
            break
    return out


# OneMap rate-limits the public search. The first bulk run took 429s on 951 of 1,200
# blocks and, because the lookup swallowed every exception, reported them as "not
# found" — data quality blamed for what was throttling. So: back off and retry, and
# count the throttles separately so a run can say which it actually hit.
THROTTLED = {"n": 0}


def onemap(blk, street, tries=4):
    """Coordinates for one block, or None. Distinguishes throttling from a real miss."""
    q = urllib.parse.urlencode({"searchVal": f"{blk} {street}", "returnGeom": "Y",
                                "getAddrDetails": "Y", "pageNum": 1})
    u = "https://www.onemap.gov.sg/api/common/elastic/search?" + q
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25) as r:
                d = json.load(r)
            for x in d.get("results", []):
                # OneMap ranks by relevance, so insist the block number actually
                # matches rather than taking whatever came first. It resolves HDB's
                # abbreviations itself ("Bedok Sth Rd" -> BEDOK SOUTH ROAD), so the
                # street does not need expanding.
                if str(x.get("BLK_NO", "")).upper() == str(blk).upper():
                    return round(float(x["LATITUDE"]), 6), round(float(x["LONGITUDE"]), 6)
            return None                      # genuine miss: answered, no match
        except urllib.error.HTTPError as e:
            if e.code != 429:
                return None
            THROTTLED["n"] += 1
            time.sleep(2 + 3 * i)            # 2s, 5s, 8s
        except Exception:
            time.sleep(1 + i)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--max-geocode", type=int, default=1200)
    a = ap.parse_args()

    # SGT explicitly, not the machine's clock. GitHub Actions runs in UTC and the
    # refresh fires at 23:00 UTC, which is 07:00 the NEXT day in Singapore — so
    # date.today() there stamped the page "refreshed" with yesterday's date every
    # single run, and would pick the wrong year for a few hours each New Year.
    today = (datetime.datetime.now(datetime.timezone.utc)
             + datetime.timedelta(hours=8)).date()
    year = today.year
    blocks = fetch_blocks()
    def sold_units(r):
        return sum(int(r.get(c) or 0) for c in SOLD_COLS)

    res = [r for r in blocks if r.get("residential") == "Y" and sold_units(r) > 0]
    rental_only = sum(1 for r in blocks if r.get("residential") == "Y"
                      and int(r.get("total_dwelling_units") or 0) > 0 and sold_units(r) == 0)
    print(f"  data.gov.sg: {len(blocks):,} blocks, {len(res):,} with flats that can be sold "
          f"({rental_only:,} rental-only blocks excluded)")

    # coordinates: converted cache first, OneMap only for what is genuinely missing
    cache = json.load(open(GEO_CACHE)) if os.path.exists(GEO_CACHE) else {}
    legacy = json.load(open(COORDS)) if os.path.exists(COORDS) else {}
    converted = 0
    for k, v in legacy.items():
        if k in cache or not isinstance(v, list) or len(v) != 2:
            continue
        try:
            cache[k] = list(svy21_to_wgs84(float(v[0]), float(v[1])))
            converted += 1
        except Exception:
            pass
    print(f"  coords: {converted:,} converted from the SVY21 cache, {len(cache):,} known")

    def key(r):
        return f"{str(r['blk_no']).strip().upper()}|{str(r['street']).strip().upper()}"

    missing = [r for r in res if key(r) not in cache]
    # Newest first: the forward pipeline is the point of this file, so if the run is
    # ever cut short it is the old blocks that go without, not the ones he needs.
    missing.sort(key=lambda r: -int(r.get("year_completed") or 0))
    if missing and not a.check:
        todo = missing[:a.max_geocode]
        print(f"  geocoding {len(todo):,} new blocks via OneMap "
              f"({len(missing) - len(todo):,} deferred to the next run)")
        got = 0
        for i, r in enumerate(todo, 1):
            ll = onemap(r["blk_no"], r["street"])
            if ll:
                cache[key(r)] = list(ll)
                got += 1
            if i % 100 == 0:
                print(f"    {i}/{len(todo)}…", flush=True)
            time.sleep(0.3)      # ~200/min, under OneMap's public ceiling
        json.dump(cache, open(GEO_CACHE, "w"))
        print(f"  geocoded {got:,} of {len(todo):,}"
              + (f"  ({THROTTLED['n']} rate-limit retries)" if THROTTLED["n"] else ""))

    # --- aggregate ---------------------------------------------------------------
    towns = collections.defaultdict(lambda: {"units": collections.Counter(),
                                             "blocks": collections.Counter(),
                                             "pts": []})
    rows, placed, unplaced = [], 0, 0
    all_pts = []
    for r in res:
        y = int(r.get("year_completed") or 0)
        if not y:
            continue
        mop = y + 5
        code = r["bldg_contract_town"]
        units = sold_units(r)
        t = towns[code]
        t["units"][mop] += units
        t["blocks"][mop] += 1
        ll = cache.get(key(r))
        if ll:
            t["pts"].append(ll)
            all_pts.append([round(ll[0], 4), round(ll[1], 4)])
            placed += 1
        else:
            unplaced += 1
        if mop >= year:                      # only the forward pipeline goes in detail
            mix = [f"{n}×{lab}" for col, lab in TYPES
                   if int(r.get(col) or 0) > 0 for n in [int(r[col])]]
            rows.append({
                "blk": str(r["blk_no"]).strip(), "street": str(r["street"]).strip().title(),
                "town": code, "mop": mop, "units": units,
                "mix": ", ".join(mix), "ll": ll,
            })

    out_towns = []
    for code, t in towns.items():
        pts = t["pts"]
        centre = ([round(sum(p[0] for p in pts) / len(pts), 6),
                   round(sum(p[1] for p in pts) / len(pts), 6)] if pts else None)
        out_towns.append({
            "code": code, "name": TOWNS.get(code, code), "centre": centre,
            "byYear": {str(k): v for k, v in sorted(t["units"].items())},
            "blocksByYear": {str(k): v for k, v in sorted(t["blocks"].items())},
            "total": sum(t["units"].values()),
            "pipeline": sum(v for k, v in t["units"].items() if k >= year),
        })
    out_towns.sort(key=lambda x: -x["pipeline"])
    rows.sort(key=lambda x: (x["mop"], x["town"], x["blk"]))

    doc = {
        "generatedAt": today.isoformat(),
        "currentYear": year,
        "method": "MOP year estimated as year_completed + 5. HDB does not publish "
                  "key-collection dates, so this is accurate to the year, not the month.",
        "source": "data.gov.sg HDB Property Information; coordinates from OneMap",
        "totals": {
            "units": sum(t["total"] for t in out_towns),
            "pipeline": sum(t["pipeline"] for t in out_towns),
            "blocksPlaced": placed, "blocksUnplaced": unplaced,
        },
        "towns": out_towns,
        # every mapped block, purely so the canvas can draw Singapore's shape behind
        # the town circles. Not read individually, hence the coarse rounding.
        "allPoints": all_pts,
        "blocks": rows,
    }
    if a.check:
        print(f"  --check: {doc['totals']['pipeline']:,} units in the pipeline, nothing written")
        return 0
    json.dump(doc, open(OUT, "w"), separators=(",", ":"))
    print(f"  {doc['totals']['pipeline']:,} units reaching MOP {year}+ "
          f"across {len(rows):,} blocks, {len(out_towns)} towns")
    print(f"  mapped {placed:,} blocks, {unplaced:,} still without coordinates")
    print(f"  -> {os.path.basename(OUT)} ({os.path.getsize(OUT)/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
