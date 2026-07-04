#!/usr/bin/env python3
"""
onemap_blocks.py — per-project block footprints from OneMap (SLA), keyless search API.

WHY: URA gives ONE survey point per project. That point IS building-accurate
(verified 0m from a OneMap block), but large estates span many blocks —
d'Leedon 289m, Normanton Park 247m, Treasure 264m across — so distance-to-point
misleads when you stand at a far block. Market Pulse "Near Me" measures to the
NEAREST BLOCK when a footprint exists.

Cache: onemap-blocks.json {PROJECT NAME: {"b": [[x,y],...], "d": "YYYY-MM-DD"}}
(SVY21 ints, deduped ~20m, max 40 blocks). Incremental: only missing projects
are fetched (cap per run), so the daily build adds new launches cheaply.
run(cap) is called at the end of ura_build_comps.py — never breaks that build.

OneMap /api/common/elastic/search is public + keyless (no token, nothing
client-side). ~250 req/min allowed; we sleep 0.12s between calls.
"""
import json, os, re, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "onemap-blocks.json")
COMPS = os.path.join(HERE, "ura-comps.json")
TODAY = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d")
UA = {"User-Agent": "Mozilla/5.0 (JND-Tools)"}
SKIP = re.compile(r"^landed housing development$|^\d+$", re.I)


def _load(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _search_page(name, page):
    q = urllib.parse.quote(name)
    url = (f"https://www.onemap.gov.sg/api/common/elastic/search"
           f"?searchVal={q}&returnGeom=Y&getAddrDetails=Y&pageNum={page}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_blocks(name):
    """-> list of deduped [x,y] ints for blocks whose SEARCHVAL mentions the project."""
    key = re.sub(r"[^A-Z0-9 ]", "", name.upper()).strip()
    if len(key) < 4:
        return []
    blocks, seen = [], set()
    for page in (1, 2, 3):
        try:
            j = _search_page(name, page)
        except Exception:  # noqa: BLE001 — one retry, then give up this page
            time.sleep(1.0)
            try:
                j = _search_page(name, page)
            except Exception:  # noqa: BLE001
                break
        res = j.get("results") or []
        for r in res:
            sv = re.sub(r"[^A-Z0-9 ]", "", str(r.get("SEARCHVAL", "")).upper())
            if key not in sv or not r.get("X"):
                continue
            try:
                x, y = int(float(r["X"])), int(float(r["Y"]))
            except (ValueError, TypeError):
                continue
            g = (x // 20, y // 20)          # ~20m dedupe grid
            if g not in seen:
                seen.add(g)
                blocks.append([x, y])
        if page >= int(j.get("totalNumPages") or 1) or len(blocks) >= 40:
            break
        time.sleep(0.12)
    return blocks[:40]


def run(cap=120):
    comps = _load(COMPS, None)
    if not comps or not comps.get("projects"):
        print("onemap_blocks: no ura-comps.json — skipped")
        return
    cache = _load(CACHE, {})
    names = [p["p"] for p in comps["projects"] if p.get("p") and not SKIP.match(p["p"])]
    missing = [n for n in names if n not in cache]
    todo = missing[:cap]
    for i, n in enumerate(todo, 1):
        cache[n] = {"b": fetch_blocks(n), "d": TODAY}
        if i % 100 == 0:
            print(f"  onemap blocks {i}/{len(todo)}")
            json.dump(cache, open(CACHE, "w"))     # checkpoint
        time.sleep(0.12)
    json.dump(cache, open(CACHE, "w"))

    # Embed footprints into ura-comps.json — only where they ADD information
    # (≥2 blocks; a single block duplicates the URA point).
    added = 0
    for p in comps["projects"]:
        c = cache.get(p.get("p") or "")
        if c and len(c.get("b", [])) >= 2:
            p["b"] = c["b"]
            added += 1
        else:
            p.pop("b", None)
    json.dump(comps, open(COMPS, "w"), separators=(",", ":"))
    sz = os.path.getsize(COMPS) / 1e6
    print(f"onemap_blocks: fetched {len(todo)} new, {len(missing)-len(todo)} still pending; "
          f"{added} projects carry multi-block footprints; ura-comps.json {sz:.2f} MB")


if __name__ == "__main__":
    run(cap=5000 if "--backfill" in sys.argv else 120)
