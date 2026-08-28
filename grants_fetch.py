#!/usr/bin/env python3
"""grants_fetch.py — PR and citizenship grants, the one series with no API.

    python3 grants_fetch.py --check     # is a newer Population in Brief out?

ICA publishes these once a year in Population in Brief, as a PDF, each September.
There is no API and no CSV. So this script does the part a machine can do reliably,
which is NOTICING that a new edition exists, and leaves the extraction to a person
with the PDF open.

That split is deliberate. The numbers live in a chart image, and an OCR guess at a
data label is exactly the kind of confidently-wrong figure that should never reach a
client-facing dashboard. When the 2026 edition lands this September, run --check, open
the PDF, and add the year to grants.json by hand. It is two numbers a year.

VERIFY THE READING. The report states five-year averages beside the chart; recompute
them from the numbers entered and they must match. That check caught nothing in 2025
because the reading was right, and it is the only reason we know it was right.
"""
import argparse
import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "grants.json")
PAGE = "https://www.population.gov.sg/media-centre/publications/population-in-brief/"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"}


def editions():
    """Every Population in Brief PDF the site links, newest first.

    The URL shape changes between years ('/files/Population_in_Brief_2025.pdf' against
    '/files/media-centre/publications/Population_in_Brief_2024.pdf'), so the links are
    scraped rather than constructed.
    """
    req = urllib.request.Request(PAGE, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        html = r.read().decode("utf-8", "replace")
    out = {}
    for href in re.findall(r'href="([^"]+\.pdf)"', html, re.I):
        m = re.search(r"(20\d\d)", href)
        if m and "population" in href.lower() or (m and "pib" in href.lower()):
            out[int(m.group(1))] = ("https://www.population.gov.sg" + href
                                    if href.startswith("/") else href)
    return dict(sorted(out.items(), reverse=True))


def check_averages(data):
    """The report prints five-year averages. Recompute and compare, or the reading of
    a chart label is just a guess with a decimal point on it."""
    yrs, pr, cit = data["years"], data["pr"], data["citizen"]
    def avg(v, a, b):
        s = [x for y, x in zip(yrs, v) if a <= y <= b]
        return sum(s) / len(s) if s else 0
    return [("citizenships 2015-2019", avg(cit, 2015, 2019), 20500),
            ("PRs 2015-2019", avg(pr, 2015, 2019), 31700),
            ("citizenships 2020-2024", avg(cit, 2020, 2024), 21300),
            ("PRs 2020-2024", avg(pr, 2020, 2024), 33000)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    data = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else None
    if data:
        print(f"  have: {data['years'][0]} to {data['years'][-1]}, "
              f"latest {data['pr'][-1]:,} PRs and {data['citizen'][-1]:,} citizenships")
        bad = [(n, got, want) for n, got, want in check_averages(data)
               if abs(got - want) > 60]
        for n, got, want in bad:
            print(f"  MISMATCH {n}: computed {got:,.0f}, report states {want:,}")
        if not bad:
            print("  all four stated five-year averages reconcile")

    try:
        eds = editions()
    except Exception as e:
        print(f"  could not read the publications page: {e}")
        return 0
    if not eds:
        print("  no PDFs found on the publications page — the layout may have changed")
        return 0
    newest = max(eds)
    print(f"  newest edition published: Population in Brief {newest}")
    print(f"    {eds[newest]}")
    if data and newest > data["years"][-1] + 1:
        print(f"  ACTION: {newest} is out and grants.json stops at {data['years'][-1]}. "
              f"Open the PDF, find the Citizenships and Permanent Residencies chart, "
              f"add the new year, then re-run this to confirm the averages still reconcile.")
    else:
        print("  nothing to add")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
