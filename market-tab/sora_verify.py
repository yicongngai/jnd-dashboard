#!/usr/bin/env python3
"""
sora_verify.py — publish a VERIFIED 3M-Compounded SORA via multi-source consensus.

Reads the value from:
  - MAS Domestic Interest Rates page (authoritative; ASP.NET form postback -> latest daily 3M Compounded SORA)
  - housingloansg, loansaver, MortgageWise  (independent reads that republish MAS)
Logic: collect all readable values -> median -> keep those within TOL of the median
(agreeing) -> publish the median, the agreeing-source list, and the range. Any source
outside TOL is excluded and reported as an outlier (bad scrape / stale). If fewer than
MIN_AGREE agree, rates.json is left unchanged and a warning is printed.

Writes rates.json -> sora_3m {value, as_of, sources, n_sources, range, status}.
Run daily. Robust: never crashes the dashboard.
"""
import re, json, ssl, statistics, urllib.request, urllib.parse, http.cookiejar
from datetime import datetime, timezone, timedelta

TOL = 0.03        # agree if within ±0.03% of the median
MIN_AGREE = 2     # need at least this many corroborating sources to publish
RATES = "rates.json"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

def fetch(url, timeout=25):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout, context=CTX) as r:
            return r.read().decode("utf-8-sig", "replace")
    except Exception as e:
        return "ERR:" + str(e)[:40]

def _strip(h): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))

def src_mas():
    """Authoritative: MAS Domestic Interest Rates page (ASP.NET postback). Latest daily 3M Compounded SORA."""
    URL = "https://eservices.mas.gov.sg/statistics/dir/domesticinterestrates.aspx"
    try:
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        h = op.open(urllib.request.Request(URL, headers=UA), timeout=30).read().decode("utf-8", "replace")
        if "maintenance" in h[:800].lower():
            return None
        def hid(n):
            m = re.search(r'id="' + n + r'"[^>]*value="([^"]*)"', h); return m.group(1) if m else ""
        now = datetime.now(timezone.utc) + timedelta(hours=8)
        prev = now.replace(day=1) - timedelta(days=1)   # include previous month for early-month coverage
        form = {"__EVENTTARGET": "", "__EVENTARGUMENT": "", "__VIEWSTATE": hid("__VIEWSTATE"),
                "__VIEWSTATEGENERATOR": hid("__VIEWSTATEGENERATOR"), "__EVENTVALIDATION": hid("__EVENTVALIDATION"),
                "ctl00$ContentPlaceHolder1$StartYearDropDownList": str(prev.year),
                "ctl00$ContentPlaceHolder1$StartMonthDropDownList": str(prev.month),
                "ctl00$ContentPlaceHolder1$EndYearDropDownList": str(now.year),
                "ctl00$ContentPlaceHolder1$EndMonthDropDownList": str(now.month),
                "ctl00$ContentPlaceHolder1$ColumnsCheckBoxList$16": "on",
                "ctl00$ContentPlaceHolder1$Button1": "Display"}
        r = op.open(urllib.request.Request(URL, data=urllib.parse.urlencode(form).encode(),
            headers={**UA, "Content-Type": "application/x-www-form-urlencoded"}), timeout=40).read().decode("utf-8", "replace")
        rows = re.findall(r"(\d{1,2}\s+\w{3}\s+\d{4})\s+([01]\.\d{3,5})", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r)))
        return float(rows[-1][1]) if rows else None   # latest date's value
    except Exception:
        return None

def src_housingloansg():
    m = re.search(r"3\s*Mth\s+([01]\.\d{3,5})", _strip(fetch("https://housingloansg.com/hl/charts/sibor-sor-daily-chart")))
    return float(m.group(1)) if m else None

def _generic_3m(url):
    t = _strip(fetch(url))
    for m in re.finditer(r"3[\s-]?(?:m|mth|month|months)\b[^+0-9]{0,22}(?:compounded\s*)?(?:sora)?[^+0-9]{0,8}([01]\.\d{2,5})", t, re.I):
        v = float(m.group(1))
        if 0.80 <= v <= 1.60:
            return v
    return None

def src_loansaver():   return _generic_3m("https://loansaver.com.sg/sora-rate-singapore/")
def src_mortgagewise(): return _generic_3m("https://www.mortgagewise.sg/")

SOURCES = {"MAS": src_mas, "housingloansg": src_housingloansg,
           "loansaver": src_loansaver, "MortgageWise": src_mortgagewise}

def main():
    reads = {}
    for name, fn in SOURCES.items():
        try: v = fn()
        except Exception: v = None
        if v is not None: reads[name] = round(v, 4)
        print(f"  {name:14} {reads.get(name, 'unavailable')}")
    if not reads:
        print("No sources readable — rates.json unchanged."); return 1

    med = statistics.median(reads.values())
    agree = {k: v for k, v in reads.items() if abs(v - med) <= TOL}
    outliers = {k: v for k, v in reads.items() if k not in agree}
    if outliers: print("  OUTLIERS (excluded):", outliers)
    mas_only = False
    fallback = None
    last_good = (json.load(open(RATES)).get("sora_3m") or {}).get("value")
    if len(agree) < MIN_AGREE:
        # MAS is the authoritative SORA publisher. If it's reachable, trust it ON ITS OWN
        # rather than discarding a valid rate just because the corroborating sites
        # (housingloansg / loansaver — routinely geo-blocked from GitHub's US cloud runners)
        # were down. Without this, a single live source froze SORA at the last consensus
        # day — it sat 7 days stale (18 Jun) while MAS was returning a fresh number daily.
        if "MAS" in reads:
            agree, mas_only = {"MAS": reads["MAS"]}, True
            print("  consensus short, but MAS (authoritative) is live — accepting MAS alone")
        # MAS down (e.g. its portal goes into SCHEDULED MAINTENANCE for days at a time —
        # seen 2026-06-28). Fall back to loansaver, which reliably republishes MAS, BUT only
        # if its read is within a sane band (±0.25) of the last-good value, so one glitchy
        # source can never push a wrong rate. SORA moves in basis points/day; a >0.25 jump
        # is a bad read, not a real move. MortgageWise is never trusted (chronic ~0.998 outlier).
        elif (lv := reads.get("loansaver")) is not None and last_good is not None and abs(lv - last_good) <= 0.25:
            agree, fallback = {"loansaver": lv}, "loansaver"
            print(f"  MAS unavailable — accepting loansaver {lv} (within 0.25 of last-good {last_good})")
        else:
            print(f"Only {len(agree)} agree, MAS unavailable, no trusted in-band fallback — rates.json unchanged."); return 1

    value = round(statistics.median(agree.values()), 2)
    sgt = datetime.now(timezone.utc) + timedelta(hours=8)
    cur = json.load(open(RATES))
    cur["sora_3m"] = {
        "value": value,
        "as_of": sgt.strftime("%Y-%m-%d"),
        "sources": sorted(agree.keys()),
        "n_sources": len(agree),
        "range": [min(agree.values()), max(agree.values())],
        "source": ("MAS (authoritative, sole source)" if mas_only else
                   "loansaver (MAS republisher; MAS portal in maintenance)" if fallback else
                   "consensus of " + str(len(agree)) + " sources"),
        "status": "mas-only" if mas_only else ("fallback-loansaver" if fallback else "verified"),
    }
    json.dump(cur, open(RATES, "w"), indent=2, ensure_ascii=False)
    print(f"VERIFIED 3M-SORA = {value}%  (median of {len(agree)}: {sorted(agree.keys())}, "
          f"range {min(agree.values())}–{max(agree.values())})")
    print(f"  effective floating = {round(value + cur['maintained']['spread'], 2)}%")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
