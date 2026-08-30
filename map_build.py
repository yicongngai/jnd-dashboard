#!/usr/bin/env python3
"""map_build.py — every layer the Market Pulse map draws, in one file.

    python3 map_build.py

WHAT THIS IS FOR
----------------
A buyer's real question is rarely "where is Tampines". It is "which homes sit inside
1 km of Ai Tong AND inside 1 km of another school we would accept" — because Primary 1
registration gives priority inside 1 km, then 1-2 km, then beyond. The overlap of two
rings is a genuinely small, genuinely searchable area, and nothing on the market draws
it for you.

So this bakes four layers that can be intersected in the browser:

  hdb      every HDB block, with the year its flats reach MOP (completion + 5)
  private  every private project from the URA caveats, condo and landed, tagged
  schools  primary and secondary, the anchors for the 1 km and 2 km rings
  towns    HDB town centres, for the MOP heat view

COORDINATES
-----------
URA publishes SVY21, Singapore's own projection. The converter lives in mop_build and
was checked against OneMap at 1 metre. HDB block coordinates come from mop_build's
cache, which is OneMap-derived and already in WGS84.
"""
import collections
import json
import time
import urllib.parse
import urllib.request
import os
import re

from mop_build import svy21_to_wgs84, TOWNS, fetch_blocks, SOLD_COLS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "map-layers.json")
SCHOOL_RES = "d_688b934f82c1059ed0a6993d2a829089"   # MOE School Directory, all 337
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"}


def _onemap_page(term, pg):
    u = "https://www.onemap.gov.sg/api/common/elastic/search?" + urllib.parse.urlencode(
        {"searchVal": term, "returnGeom": "Y", "getAddrDetails": "Y", "pageNum": pg})
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 + 3 * i)
    return {}


def onemap_name(name):
    """Locate a private project by name. The URA caveat x/y is a representative point
    for the project and sits 57 to 71 m off the building on the projects checked, which
    is enough to put a dot beside the wrong condo and enough to matter at a ring edge.
    OneMap knows where the development actually is, so ask it and keep the answer."""
    q = urllib.parse.urlencode({"searchVal": name, "returnGeom": "Y",
                                "getAddrDetails": "Y", "pageNum": 1})
    u = "https://www.onemap.gov.sg/api/common/elastic/search?" + q
    want = re.sub(r"[^a-z0-9]", "", name.lower())
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25) as r:
                d = json.load(r)
            for x in d.get("results", [])[:4]:
                got = re.sub(r"[^a-z0-9]", "", str(x.get("SEARCHVAL", "")).lower())
                # insist the name really matches; OneMap ranks by relevance, so a loose
                # accept would silently move a project to a similarly-named one
                if got == want or (len(want) > 8 and got.startswith(want)):
                    time.sleep(0.3)
                    return [round(float(x["LATITUDE"]), 6), round(float(x["LONGITUDE"]), 6)]
            time.sleep(0.3)
            return None
        except Exception:
            time.sleep(2 + 3 * i)
    return None


def onemap_postal(pc):
    """Exact postal-code lookup. Backs off on 429 rather than reporting a throttle as
    a missing school, which is the mistake the block geocoder made first time."""
    q = urllib.parse.urlencode({"searchVal": pc, "returnGeom": "Y",
                                "getAddrDetails": "Y", "pageNum": 1})
    u = "https://www.onemap.gov.sg/api/common/elastic/search?" + q
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25) as r:
                d = json.load(r)
            for x in d.get("results", []):
                if str(x.get("POSTAL", "")).strip() == str(pc).strip():
                    time.sleep(0.3)
                    return [round(float(x["LATITUDE"]), 6), round(float(x["LONGITUDE"]), 6)]
            time.sleep(0.3)
            return None
        except Exception:
            time.sleep(2 + 3 * i)
    return None

# URA property-type codes. SD/T/D are individually titled houses; SSD/ST are strata,
# i.e. cluster housing that behaves like a condo. Keeping them apart matters because a
# buyer asking for "landed" means the first group.
LANDED = {"T": "Terrace", "SD": "Semi-detached", "D": "Detached"}
STRATA_LANDED = {"ST": "Strata terrace", "SSD": "Strata semi-detached", "SD-S": "Strata"}


def main():
    out = {}

    # --- HDB, with the MOP wave each block belongs to --------------------------
    mop = json.load(open(os.path.join(HERE, "mop-data.json"), encoding="utf-8"))
    cache = json.load(open(os.path.join(HERE, "mop-geocache.json"), encoding="utf-8"))

    # Straight from data.gov.sg, the same source mop_build uses. The baked
    # hdb-blocks.json is an older slice and joining against it silently dropped 45 of
    # the 743 blocks in the MOP pipeline — the exact rows this map is about.
    blocks = fetch_blocks()

    mop_by_block = {}
    for b in mop["blocks"]:
        mop_by_block[(b["blk"].upper(), b["street"].upper())] = b["mop"]

    tx_path = os.path.join(HERE, "hdb-txns.json")
    hdb_tx = {}
    if os.path.exists(tx_path):
        for b in json.load(open(tx_path, encoding="utf-8")).get("blocks", []):
            # r = [MMYY, flatTypeCode, storeyBand, areaSqm, price, modelCode]
            rs = sorted(b.get("r") or [], key=lambda t: str(t[0]).zfill(4)[2:] + str(t[0]).zfill(4)[:2],
                        reverse=True)[:6]
            if rs:
                hdb_tx[str(b.get("n", "")).upper()] = [
                    [str(t[0]).zfill(4), t[3], t[4],
                     round(t[4] / (t[3] * 10.7639)) if t[3] else 0, t[1]] for t in rs]

    hdb, joined = [], 0
    for r in blocks:
        if r.get("residential") != "Y":
            continue
        units = sum(int(r.get(c) or 0) for c in SOLD_COLS)
        if units <= 0:                     # rental-only blocks never reach MOP
            continue
        blk = str(r["blk_no"]).strip()
        street = str(r["street"]).strip()
        ll = cache.get(f"{blk.upper()}|{street.upper()}")
        if not ll:
            continue
        yr = int(r.get("year_completed") or 0)
        m = mop_by_block.get((blk.upper(), street.title().upper()), 0)
        if m:
            joined += 1
        hdb.append([round(ll[0], 5), round(ll[1], 5), blk, street.title(),
                    r["bldg_contract_town"], yr, m or (yr + 5 if yr else 0), units,
                    hdb_tx.get(f"{blk} {street}".upper(), [])])
    out["hdb"] = {"fields": ["lat", "lon", "blk", "street", "town", "completed",
                             "mopYear", "units", "txns"],
                  "txnFields": ["MMYY", "sqm", "price", "psf", "flatType"], "rows": hdb}
    print(f"  hdb resale attached to {sum(1 for h in hdb if h[8]):,} blocks")
    print(f"  hdb join: {joined:,} of {len(mop['blocks']):,} pipeline blocks matched")

    # --- private: condos and landed, from the URA caveats ----------------------
    comps = json.load(open(os.path.join(HERE, "ura-comps.json"), encoding="utf-8"))
    pj_path = os.path.join(HERE, "project-geocache.json")
    pj = json.load(open(pj_path, encoding="utf-8")) if os.path.exists(pj_path) else {}
    priv, exact, approx = [], 0, 0
    # Most recent transactions per project, so clicking a dot answers "what has this
    # actually sold for". Six is enough to show a trend and a spread without the file
    # doubling in size; the full history stays in ura-comps.json for the unit reports.
    def recent(ts, k=6):
        def key(t):
            mm = str(t[2]).zfill(4)
            return mm[2:] + mm[:2]              # MMYY -> YYMM so it sorts by date
        out = []
        for t in sorted(ts, key=key, reverse=True)[:k]:
            mm = str(t[2]).zfill(4)
            sqft, price = t[0], t[1]
            out.append([mm, sqft, price, round(price / sqft) if sqft else 0,
                        t[7] if len(t) > 7 else ""])
        return out
    for p in comps.get("projects", []):
        try:
            lat, lon = svy21_to_wgs84(float(p["x"]), float(p["y"]))
        except Exception:
            continue
        kinds = collections.Counter(t[4] for t in (p.get("t") or []) if len(t) > 4)
        if not kinds:
            continue
        top = kinds.most_common(1)[0][0]
        if top in LANDED:
            kind = "landed"
        elif top in STRATA_LANDED:
            kind = "strata"
        else:
            kind = "condo"
        name = p.get("p") or ""
        if name == "LANDED HOUSING DEVELOPMENT":
            name = (p.get("st") or "").title() + " (landed)"
        else:
            name = name.title()
        # Landed groups are a whole street, so a name lookup is meaningless for them;
        # they keep the URA point. Named developments get located properly.
        if kind != "landed" and name:
            got = pj.get(name, "miss")
            if got == "miss":
                got = onemap_name(name)
                pj[name] = got
            if got:
                lat, lon = got[0], got[1]
                exact += 1
            else:
                approx += 1
        else:
            approx += 1
        priv.append([round(lat, 5), round(lon, 5), name, kind, p.get("seg") or "",
                     len(p.get("t") or []), 1 if kind != "landed" and pj.get(name) else 0,
                     recent(p.get("t") or [])])
    json.dump(pj, open(pj_path, "w"))
    out["private"] = {"fields": ["lat", "lon", "name", "kind", "segment", "caveats",
                                 "exact", "txns"],
                      "txnFields": ["MMYY", "sqft", "price", "psf", "floorBand"],
                      "rows": priv}
    print(f"  private points: {exact:,} located by name, {approx:,} on the URA point")

    # --- schools, from MOE's own directory -------------------------------------
    # NOT from the amenities cache. That was built by searching OneMap and is both
    # incomplete and polluted: Ai Tong, St Nicholas and Rosyth were all missing while
    # "Afterschool @ ..." student-care centres were listed as primary schools. For a
    # tool whose whole purpose is drawing a ring around a named school, the list has to
    # be the official one. MOE publishes all 337 with postal codes; OneMap resolves a
    # postal code exactly, so there is no fuzzy name matching anywhere in this.
    sc_cache_path = os.path.join(HERE, "schools-geocache.json")
    sc_cache = (json.load(open(sc_cache_path, encoding="utf-8"))
                if os.path.exists(sc_cache_path) else {})
    def level_of(code):
        """MOE's codes carry a range suffix — SECONDARY (S1-S5), MIXED LEVEL (P1-S4) —
        so an exact-match lookup filed all 133 secondaries under "other". Match the
        prefix, and treat a P1 mixed level as primary because that is the intake a
        1 km ring is about."""
        c = (code or "").upper()
        if c.startswith("PRIMARY"):
            return "primary"
        if c.startswith("SECONDARY"):
            return "secondary"
        if c.startswith(("JUNIOR COLLEGE", "CENTRALISED")):
            return "jc"
        if c.startswith("MIXED LEVEL"):
            return "primary" if "P1" in c else "secondary"
        return "other"
    recs, off = [], 0
    while True:
        q = {"resource_id": SCHOOL_RES, "limit": 500, "offset": off}
        u = "https://data.gov.sg/api/action/datastore_search?" + urllib.parse.urlencode(q)
        j = json.load(urllib.request.urlopen(u, timeout=90))["result"]
        if not j["records"]:
            break
        recs += j["records"]
        off += len(j["records"])
        if off >= int(j.get("total", 0)):
            break

    schools, missed = [], []
    for r in recs:
        name = re.sub(r"\s+", " ", (r.get("school_name") or "")).strip().title()
        # Singapore postal codes are six digits and this field arrives as a number, so
        # the four schools in districts 08 and 09 lost their leading zero and could not
        # be found. Cantonment Primary is 088256, not 88256.
        pc = str(r.get("postal_code") or "").strip().zfill(6)
        lvl = level_of(r.get("mainlevel_code"))
        if not name or not pc:
            continue
        ll = sc_cache.get(pc)
        if ll is None:
            ll = onemap_postal(pc)
            if ll:
                sc_cache[pc] = ll
            else:
                missed.append(name)
                continue
        schools.append([round(ll[0], 5), round(ll[1], 5), name, lvl])
    json.dump(sc_cache, open(sc_cache_path, "w"))
    schools.sort(key=lambda r: r[2])
    out["schools"] = {"fields": ["lat", "lon", "name", "level"], "rows": schools}
    if missed:
        print(f"  {len(missed)} schools could not be placed: {', '.join(missed[:5])}")

    # --- MRT and LRT stations --------------------------------------------------
    # Rebuilt from OneMap rather than reusing command-centre/sg-stations.json, which
    # listed interchanges up to three times (Ang Mo Kio appeared bare, as NS16 and as
    # CR11) and was missing Tengah entirely — the town with the largest MOP wave on the
    # other view. Exits are dropped; a station is one point, not eight doorways.
    #
    # Unbuilt Jurong Region Line stops are in OneMap with no name at all, only a code:
    # "MRT STATION (JS3)" is Tengah. They are kept, because a station opening next to a
    # new estate is exactly what a buyer is choosing for, but they are labelled by code
    # and flagged rather than given a name this script would be inventing.
    st_path = os.path.join(HERE, "stations.json")
    raw_st = json.load(open(st_path, encoding="utf-8")) if os.path.exists(st_path) else None
    if raw_st is None:
        raw_st = {}
        for term in ("MRT STATION", "LRT STATION"):
            first = _onemap_page(term, 1)
            for pg in range(1, int(first.get("totalNumPages") or 1) + 1):
                j = first if pg == 1 else _onemap_page(term, pg)
                for x in j.get("results", []):
                    nm = str(x.get("SEARCHVAL", "")).upper().strip()
                    if "STATION" not in nm or " EXIT" in nm:
                        continue
                    try:
                        raw_st[nm] = [round(float(x["LATITUDE"]), 6), round(float(x["LONGITUDE"]), 6)]
                    except Exception:
                        pass
                time.sleep(0.25)
        json.dump(raw_st, open(st_path, "w"))

    CODE = re.compile(r"\(([A-Z]{2}\d+[A-Z]?(?:\s*/\s*[A-Z]{2}\d+[A-Z]?)*)\)\s*$")

    def as_pair(v):
        """The cache has been written in two shapes over its life — [lat, lon] and
        {"lat":..,"lon":..}. Accept both rather than depend on which ran last."""
        if isinstance(v, dict):
            return [v.get("lat"), v.get("lon")]
        return list(v)

    merged = {}
    for nm, v in raw_st.items():
        ll = as_pair(v)
        if ll[0] is None or ll[1] is None:
            continue
        m = CODE.search(nm)
        if not m:
            continue                      # no line code: not a platform record
        codes = [c.strip() for c in m.group(1).split("/")]
        base = CODE.sub("", nm).strip()
        kind = "LRT" if "LRT" in nm else "MRT"
        unnamed = base in ("MRT STATION", "LRT STATION")
        key = ",".join(sorted(codes)) if unnamed else base
        e = merged.setdefault(key, {"pts": [], "codes": set(), "kind": kind,
                                    "base": base, "unnamed": unnamed})
        e["pts"].append(ll)
        e["codes"].update(codes)

    stations = []
    for key, e in merged.items():
        # interchange platforms sit within a few hundred metres; one point per station
        lat = sum(p[0] for p in e["pts"]) / len(e["pts"])
        lon = sum(p[1] for p in e["pts"]) / len(e["pts"])
        codes = " / ".join(sorted(e["codes"]))
        if e["unnamed"]:
            # A station with no name yet is unfindable by search, and the biggest MOP
            # wave on the other view is in Tengah, whose stop is exactly one of these.
            # So say where it is, derived from the nearest HDB block rather than from a
            # name this script would be guessing at.
            near, best = None, 1e9
            for h in hdb:
                dd = (h[0] - lat) ** 2 + (h[1] - lon) ** 2
                if dd < best:
                    best, near = dd, h
            where = TOWNS.get(near[4], near[4]) if near else None
            label = (f"{e['kind']} station {codes} (name not yet assigned"
                     + (f", in {where})" if where else ")"))
        else:
            label = re.sub(r"\s+", " ", e["base"].replace(" MRT STATION", "")
                           .replace(" LRT STATION", "")).strip().title() + f" {e['kind']} ({codes})"
        stations.append([round(lat, 5), round(lon, 5), label, e["kind"].lower()])
    stations.sort(key=lambda r: r[2])
    out["stations"] = {"fields": ["lat", "lon", "name", "kind"], "rows": stations}
    print(f"  stations {len(stations):,} "
          f"({sum(1 for x in stations if x[3]=='mrt')} MRT, "
          f"{sum(1 for x in stations if x[3]=='lrt')} LRT, "
          f"{sum(1 for x in stations if 'not yet assigned' in x[2])} unnamed/upcoming)")

    # --- towns, for the MOP view ----------------------------------------------
    out["towns"] = [{"code": t["code"], "name": t["name"], "centre": t["centre"],
                     "byYear": t["byYear"], "pipeline": t["pipeline"]}
                    for t in mop["towns"]]
    out["mopTotals"] = mop["totals"]
    out["generatedAt"] = mop["generatedAt"]
    out["currentYear"] = mop["currentYear"]

    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    kinds = collections.Counter(r[3] for r in priv)
    fut = [r for r in hdb if r[6] >= out["currentYear"]]
    print(f"  hdb      {len(hdb):,} blocks, {sum(r[7] for r in hdb):,} flats "
          f"({len(fut):,} blocks / {sum(r[7] for r in fut):,} flats reaching MOP "
          f"{out['currentYear']}+)")
    print(f"  private  {len(priv):,} projects  {dict(kinds)}")
    lv = collections.Counter(x[3] for x in schools)
    print(f"  schools  {len(schools):,} from MOE  {dict(lv)}")
    print(f"  -> {os.path.basename(OUT)} ({os.path.getsize(OUT)/1024/1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
