#!/usr/bin/env python3
"""
era_scrape.py v4 — ERA new-launch board from the ERA Property Portal API.

SOURCE MIGRATED (2026-07-02): eraprojects.sg (per-project subdomains, HTML unit
stacks) now 301-redirects — replaced by propertyportal.era.com.sg, whose
`POST /api/salesplus/new-launches/search` returns the whole board as JSON
(headless-friendly: no cookies/auth; verified from plain curl).

Classification (from validated API semantics):
  country != SG                                   -> overseas   (exclude)
  propertyType != Condo                           -> commercial/landed/industrial (exclude)
  unitSummary.propertySubTypes has EC/landed/comm -> exclude    (ECs hide under Condo)
  name looks commercial/landed (shoppes/villa…)   -> exclude    (no-summary strays)
  UPCOMING  : launchDate in the future OR no unitSummary (= no live sales stack;
              e.g. Thomson Reserve carries a placeholder launchDate but no stack).
              Old completed strays (TOP year < this year) excluded.
              avail = full project size (numberOfUnits).
  IN-MARKET : live stack with numberOfAvailableUnits > 0. avail = unsold count.
              stale flag = TOP year already past.

Output: launches.json (board — SCHEMA UNCHANGED from v3) + era_classified.json
(audit) + summary line. On a short/failed API read it exits non-zero WITHOUT
writing, so the workflow's keep-last-good fallback + the command centre's
freshness monitor do their jobs.
"""
import json, re, sys, urllib.request
from datetime import datetime, timezone, timedelta, date

_SCRAPE_DATE = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d")  # SGT run date
THIS_YEAR = int(_SCRAPE_DATE[:4])
API = "https://propertyportal.era.com.sg/api/salesplus/new-launches/search"
UA = {"User-Agent": "Mozilla/5.0 (JND-Tools)", "Content-Type": "application/json"}
TIMEOUT = 40
MIN_SANE = 50          # fewer SG condos than this = broken read -> keep last-good

EXCLUDE_SUBTYPES = {"Executive Condominium", "Semi-Detached House", "Terrace House",
                    "Office", "Multiple-user Factory", "Retail"}
NAME_COMM = re.compile(r"shoppes|xchange|industrial|factory|foodworks|warehouse|\bplot\b|gourmet", re.I)
NAME_LANDED = re.compile(r"villa|bungalow|cluster house", re.I)
SMALL = {"gls": "GLS", "at": "at", "by": "by", "the": "The", "of": "of", "on": "on",
         "d'leedon": "d'Leedon", "ii": "II", "iii": "III"}


def fetch_board():
    body = json.dumps({"page": 1, "pageSize": 500}).encode()
    req = urllib.request.Request(API, data=body, headers=UA, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    rows = d.get("data") or []
    total = d.get("totalCount") or 0
    if total > len(rows):   # paginate if the board ever outgrows one page
        page = 2
        while len(rows) < total and page < 20:
            body = json.dumps({"page": page, "pageSize": 500}).encode()
            req = urllib.request.Request(API, data=body, headers=UA, method="POST")
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                more = (json.loads(r.read().decode("utf-8", "replace")).get("data")) or []
            if not more:
                break
            rows += more
            page += 1
    return rows


def titlecase(name):
    out = []
    for w in (name or "").strip().lower().split():
        out.append(SMALL.get(w, w.capitalize()))
    return " ".join(out)


def region_of(d):
    m = re.match(r"D0?(\d+)", d or "")
    n = int(m.group(1)) if m else 0
    return "CCR" if n in (1, 2, 6, 9, 10, 11) else \
           "RCR" if n in (3, 4, 5, 7, 8, 12, 13, 14, 15, 20) else ("OCR" if n else "")


def year_of(s):
    m = re.match(r"(\d{4})", str(s or ""))
    return int(m.group(1)) if m else None


def classify(r):
    """-> dict(status, type, keep, ...) mirroring the v3 audit shape."""
    us = r.get("unitSummary") or {}
    subs = set(us.get("propertySubTypes") or [])
    name = r.get("name") or ""
    top_year = year_of(r.get("top"))
    try:
        ldate = date.fromisoformat((r.get("launchDate") or "")[:10])
    except ValueError:
        ldate = None
    today = date.fromisoformat(_SCRAPE_DATE)

    keep, typ = False, "residential"
    if r.get("country") != "SG":
        typ = "overseas"
    elif (r.get("propertyType") or "") != "Condo":
        typ = (r.get("propertyType") or "?").lower() or "unknown"
    elif "Executive Condominium" in subs:
        typ = "EC"
    elif subs & {"Semi-Detached House", "Terrace House"} or NAME_LANDED.search(name):
        typ = "landed"
    elif subs & {"Office", "Multiple-user Factory", "Retail"} or NAME_COMM.search(name):
        typ = "commercial"
    elif r.get("isSoldOut"):
        typ = "sold_out"
    else:
        keep = True

    upcoming = (ldate and ldate > today) or not us
    if keep and upcoming and not (ldate and ldate > today):
        # no live stack AND no future launch date: drop old completed strays
        if top_year and top_year < THIS_YEAR:
            keep, typ = False, "completed"
    avail = (r.get("numberOfUnits") if upcoming else us.get("numberOfAvailableUnits")) or 0
    if keep and not upcoming and avail <= 0:
        keep, typ = False, "sold_out"

    return {"name": name, "status": "pre_launch" if upcoming else "in_market",
            "type": typ, "keep": keep, "district": (r.get("district") or "").upper(),
            "country": r.get("country"), "top_year": top_year, "avail": avail,
            "launch_date": (r.get("launchDate") or "")[:10],
            "developer": re.sub(r"\s+", " ", (r.get("developer") or "")).strip(),
            "total_units": r.get("numberOfUnits")}


def main():
    try:
        rows = fetch_board()
    except Exception as e:  # noqa: BLE001
        print(f"ERA portal API unreadable ({e}) — keeping last-good launches.json", file=sys.stderr)
        return 1
    out = [classify(r) for r in rows]
    json.dump(out, open("era_classified.json", "w"), indent=1)

    keep = [r for r in out if r["keep"]]
    if len(keep) < MIN_SANE:
        print(f"Only {len(keep)} keepable SG condos (< {MIN_SANE}) — suspicious read, "
              "keeping last-good launches.json", file=sys.stderr)
        return 1

    im = sorted([r for r in keep if r["status"] == "in_market"],
                key=lambda x: (x.get("top_year") or 0), reverse=True)
    pl = sorted([r for r in keep if r["status"] == "pre_launch" and r["avail"]],
                key=lambda x: -(x["avail"] or 0))

    def ent(r, k):
        o = {"name": titlecase(r["name"]), "district": r["district"],
             "region": region_of(r["district"]), "avail": r["avail"],
             "developer": r["developer"]}
        if k == "in":
            o["top"] = ("TOP " + str(r["top_year"])) if r.get("top_year") else "TOP n/a"
            o["stale"] = not (r.get("top_year") and r["top_year"] >= THIS_YEAR)
        else:
            o["launch"] = "upcoming"
        return o

    launches = {"_meta": {"metric": "avail = units available (in-market unsold / upcoming full size)",
                "scope": "SG residential condos — AUTO from ERA Property Portal API (propertyportal.era.com.sg)",
                "as_of": _SCRAPE_DATE, "auto": True,
                "counts": {"in_market": len(im), "rest_of_2026": len(pl)}},
                "in_market": [ent(r, "in") for r in im],
                "rest_of_2026": [ent(r, "up") for r in pl]}
    json.dump(launches, open("launches.json", "w"), indent=2)

    from collections import Counter
    print("types:", dict(Counter(r["type"] for r in out)))
    print(f"BOARD -> in-market {len(im)} ({sum(r['avail'] or 0 for r in im):,} units) | "
          f"upcoming {len(pl)} ({sum(r['avail'] or 0 for r in pl):,} units)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
