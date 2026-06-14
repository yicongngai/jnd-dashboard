#!/usr/bin/env python3
"""Build launches.json from era_scrape_raw.json — all residential-condo candidates,
in-market (live unsold) vs pre-launch (full size). Best-effort residential filter."""
import json, re

d = json.load(open("era_scrape_raw.json"))

def excl(r):
    s, t = r["slug"], str(r["type_hint"])
    if re.search(r"gls$|gls-", s): return "GLS"
    if re.search(r"cambodia|johor|forest-city|malaysia|thailand|london|australia", s): return "overseas"
    if "exclude" in t or "landed" in t: return "landed"
    if "EC" in t: return "EC"
    if ("commercial" in t or "industrial" in t) and "condo" not in t: return "commercial"
    return None

def titlecase(slug):
    fix = {"gls":"GLS","ec":"EC","bt":"BT","pb":"PB","pa":"PA","w":"W","at":"at","by":"by","the":"The","on":"on","of":"of"}
    return " ".join(fix.get(w, w.capitalize()) for w in slug.split("-"))

def region_of(dist):
    m = re.match(r"D0?(\d+)", dist or ""); n = int(m.group(1)) if m else 0
    if n in (1,2,6,9,10,11): return "CCR"
    if n in (3,4,5,7,8,12,13,14,15,20): return "RCR"
    return "OCR" if n else ""

inm, pre = [], []
for r in d:
    if excl(r): continue
    base = {"name": titlecase(r["slug"]), "district": r.get("district",""),
            "region": region_of(r.get("district","")), "avail": r.get("avail"), "developer": ""}
    if r["status"] == "in_market":
        base["launched"] = "selling"; inm.append(base)
    else:
        base["launch"] = "upcoming"; pre.append(base)

inm.sort(key=lambda x: x["avail"] or 0, reverse=True)
pre.sort(key=lambda x: x["avail"] or 0, reverse=True)

out = {
  "_meta": {
    "metric": "avail = units currently available (in-market = unsold from ERA /units; pre-launch = full size).",
    "scope": "ALL ERA residential-condo candidates. Best-effort filter (ERA exposes no type to curl) — VERIFY: some may be mislabeled; old projects included.",
    "as_of": "2026-06-14",
    "avail_source": "ERA eraprojects.sg /units (scraped)",
    "counts": {"in_market": len(inm), "rest_of_2026": len(pre)}
  },
  "in_market": inm,
  "rest_of_2026": pre
}
json.dump(out, open("launches.json","w"), indent=1)
print(f"in_market={len(inm)} (avail {sum(x['avail'] or 0 for x in inm)}) | rest={len(pre)} (avail {sum(x['avail'] or 0 for x in pre)})")
