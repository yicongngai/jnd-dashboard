#!/usr/bin/env python3
"""singstat_fetch.py — the fundamentals behind the Market Pulse charts.

    python3 singstat_fetch.py            # refresh, write market-pulse-series.json
    python3 singstat_fetch.py --check    # report freshness without writing

Three series, one keyless API. No account, no token, no daily-token dance like URA's
own service, which is why this is the source even for the URA index.

    M810001   Population, annual (June)      total / citizens / PRs / non-residents
    M014871   Nominal GDP, quarterly         GDP at current market prices
    M212261   URA private residential price index, quarterly, back to 1975 Q1

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
It does not pull daily and call that live. None of these move daily: the URA flash
estimate lands on the first working day after a quarter closes, the full index about
four weeks later, GDP's advance estimate about two weeks after quarter end, and
population once a year in late September. So the file records WHEN each series last
changed, and the dashboard shows that, because "as at 2026 Q2" is honest where a
today's-date stamp on a quarterly number is not.

The fourth series, PR and citizenship GRANTS, is not in any API. It lives in ICA's
Population in Brief, published as a PDF each September, and is refreshed by
`grants_fetch.py` once a year.
"""
import argparse
import datetime
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "market-pulse-series.json")
API = "https://tablebuilder.singstat.gov.sg/api/table/tabledata"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"}

TABLES = {
    "population": ("M810001", ["Total Population", "Singapore Citizen Population",
                               "Permanent Resident Population", "Non-Resident Population"]),
    "gdp":        ("M014871", ["GDP At Current Market Prices"]),
    "ppi":        ("M212261", ["Residential Properties", "Landed", "Non-Landed"]),
    # Household income. M810361 carries the DOS headline medians INCLUDING employer CPF
    # — the basis the newspapers quote — and 17906 the per-decile averages EXCLUDING
    # employer CPF, which is the basis a bank actually assesses TDSR on. Both are kept
    # because they answer different questions and mixing them overstates borrowing power
    # by about 14%.
    "income":     ("M810361", ["Median Monthly Household Employment Income Including "
                               "Employer CPF Contributions",
                               "Median Monthly Household Employment Income Per Household "
                               "Member (Including Employer CPF Contributions)"]),
    "deciles":    ("17906", ["Total", "1st (Lowest)", "2nd", "3rd", "4th", "5th",
                             "6th", "7th", "8th", "9th", "10th (Highest)"]),
}

# 17896 nests its columns two deep — year -> household type -> Average/Median — so the
# flat rowText extractor cannot read it. It is the only source for the MEDIAN household
# income excluding employer CPF, which is what the loan figures are built on.
MEDIAN_EXCL = "17896"


def fetch(table_id, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(f"{API}/{table_id}", headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)["Data"]
        except Exception as e:                       # SingStat 429s under load
            last = e
            import time
            time.sleep(3 + 4 * i)
    raise SystemExit(f"{table_id}: {last}")


def qkey(s):
    """'2026 2Q' -> sortable. Annual keys ('2025') sort on their own."""
    p = s.split()
    return (int(p[0]), int(p[1][0])) if len(p) == 2 else (int(p[0]), 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    prev = {}
    if os.path.exists(OUT):
        try:
            prev = json.load(open(OUT, encoding="utf-8"))
        except ValueError:
            prev = {}

    out = {"fetched": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "series": {}}
    for name, (tid, wanted) in TABLES.items():
        d = fetch(tid)
        rows = {r["rowText"]: {c["key"]: c["value"] for c in r.get("columns", [])}
                for r in d.get("row", [])}
        keep = {w: rows[w] for w in wanted if w in rows}
        missing = [w for w in wanted if w not in rows]
        periods = sorted({k for v in keep.values() for k in v}, key=qkey)
        out["series"][name] = {
            "table": tid, "title": d.get("title"), "frequency": d.get("frequency"),
            "source": d.get("datasource"), "latest_period": periods[-1] if periods else None,
            "rows": keep,
        }
        if missing:
            print(f"  WARNING {tid}: series missing from the response: {missing}")
        # "changed" is what the dashboard should key its freshness label on, not the
        # fetch time. A daily fetch of a quarterly number is not a daily update.
        old = (prev.get("series", {}).get(name) or {}).get("latest_period")
        new = out["series"][name]["latest_period"]
        out["series"][name]["changed"] = (old != new)
        flag = "  NEW PERIOD" if old and old != new else ""
        print(f"  {name:<11}{tid}  {d.get('frequency'):<10}latest {new}{flag}")

    # --- the nested table, fetched on its own terms ---------------------------
    d = fetch(MEDIAN_EXCL)
    med = {}
    for r in d.get("row", []):
        yr = r.get("rowText")
        for c in r.get("columns", []):
            if c.get("key") != "Resident Employed Households":
                continue
            for sub in c.get("columns", []):
                if str(sub.get("key", "")).startswith("Median"):
                    med[yr] = sub.get("value")
    yrs = sorted(med)
    out["series"]["median_excl_cpf"] = {
        "table": MEDIAN_EXCL, "title": d.get("title"), "frequency": d.get("frequency"),
        "latest_period": yrs[-1] if yrs else None,
        "rows": {"Median Monthly Household Employment Income Excluding Employer CPF "
                 "(Resident Employed Households)": med},
    }
    old = (prev.get("series", {}).get("median_excl_cpf") or {}).get("latest_period")
    out["series"]["median_excl_cpf"]["changed"] = (old != (yrs[-1] if yrs else None))
    print(f"  {'medianExcl':<11}{MEDIAN_EXCL}  {d.get('frequency'):<10}latest {yrs[-1] if yrs else '—'}")

    if a.check:
        print("  --check, nothing written")
        return 0
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"  -> {os.path.basename(OUT)}  ({os.path.getsize(OUT)/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
