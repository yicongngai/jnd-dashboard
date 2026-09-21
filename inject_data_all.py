#!/usr/bin/env python3
"""Inline all baked data (HDB blocks, URA comps, rates, launches) into the dashboard
as <script type=application/json> blocks, inside re-runnable <!--JND-DATA--> fences."""
import json, os, shutil
F = "index-live-auto.html"
html = open(F, encoding="utf-8").read()

# SKIP_FETCH=1 (deploy-only.yml, added 4 Sep 2026): inline the data files exactly as
# committed, without re-pulling anything. The committed index-live-auto.html carries
# EMPTY data fences, so publishing it without this step ships a page with no map, no
# comps and no fundamentals. That is what happened 3-4 Sep (deploy-only ran the raw
# file for ~10 hours). The daily 07:00 refresh still re-bakes everything fresh.
SKIP_FETCH = os.environ.get("SKIP_FETCH") == "1"

def load(p):
    s = open(p, encoding="utf-8").read()
    assert "</script" not in s.lower(), f"{p} contains </script>!"
    return s

# Refresh the Market Pulse fundamentals BEFORE inlining them. This lives here rather
# than in refresh.yml for the same reason the decoupling staging does: the deploy token
# has no `workflow` scope, so a push that edits the workflow file is rejected outright.
# Failure is non-fatal — a SingStat outage keeps the last good file and the charts stay
# on the previous quarter, which is honest, rather than failing the whole deploy.
try:
    if SKIP_FETCH: raise RuntimeError("SKIP_FETCH")
    import subprocess as _sp
    _r = _sp.run(["python3", "singstat_fetch.py"], capture_output=True, text=True, timeout=300)
    print(_r.stdout.strip() or "singstat_fetch: no output")
    if _r.returncode != 0:
        print("singstat_fetch FAILED — keeping last-good market-pulse-series.json")
except Exception as _e:
    print(f"singstat_fetch skipped: {_e}")

# MOP pipeline. Re-pulls data.gov.sg every run, so blocks completing and whole new
# towns (Tengah arrived this way) appear without anyone touching this. It also geocodes
# a slice of any blocks still missing coordinates, capped so one slow OneMap day cannot
# stall the deploy — the rest are picked up tomorrow. Non-fatal for the same reason as
# above: a stale map beats a failed build.
try:
    if SKIP_FETCH: raise RuntimeError("SKIP_FETCH")
    import subprocess as _sp2
    _r2 = _sp2.run(["python3", "mop_build.py", "--max-geocode", "400"],
                   capture_output=True, text=True, timeout=900)
    print(_r2.stdout.strip() or "mop_build: no output")
    if _r2.returncode != 0:
        print("mop_build FAILED — keeping last-good mop-data.json")
except Exception as _e:
    print(f"mop_build skipped: {_e}")

# Map layers depend on mop-data.json, so this runs after it.
try:
    if SKIP_FETCH: raise RuntimeError("SKIP_FETCH")
    import subprocess as _sp3
    _r3 = _sp3.run(["python3", "map_build.py"], capture_output=True, text=True, timeout=600)
    print(_r3.stdout.strip() or "map_build: no output")
    if _r3.returncode != 0:
        print("map_build FAILED — keeping last-good map-layers.json")
except Exception as _e:
    print(f"map_build skipped: {_e}")

# NEVER PUBLISH A LAUNCH BOARD OLDER THAN THE ONE ALREADY LIVE (21 Sep 2026).
# launches.json is not tracked, so on a CI runner it only exists if era_scrape.py just
# succeeded. When the ERA portal times out, the workflows fall back to build_board.py,
# which rebuilds from the tracked raw scrape of 14 Jun 2026 and shipped a 99 day old
# board twice (6 Sep, 21 Sep). The live site is the real last-good copy, refreshed daily,
# so compare the two and keep whichever is newer. Lives here, not in the workflow files,
# because the deploy token cannot push workflow edits, and because both workflows run
# this script. Any failure in here leaves the local file untouched.
def _launch_asof(text):
    try:
        return (json.loads(text).get("_meta") or {}).get("as_of") or ""
    except Exception:
        return ""

try:
    import re as _re, urllib.request as _ur
    _LP = "market-tab/launches.json"
    _local = open(_LP, encoding="utf-8").read() if os.path.exists(_LP) else ""
    _req = _ur.Request("https://jndtoolkit.com/", headers={"User-Agent": "jnd-inject"})
    _page = _ur.urlopen(_req, timeout=30).read().decode("utf-8", "replace")
    _m = _re.search(r'id="jnd-launches">(.*?)</script>', _page, _re.S)
    _live = _m.group(1) if _m else ""
    _la, _va = _launch_asof(_local), _launch_asof(_live)
    if _va and _va > _la:
        open(_LP, "w", encoding="utf-8").write(_live)
        print(f"launches: local board {_la or 'missing'} is older than the live site ({_va}), kept the live one")
    else:
        print(f"launches: using local board {_la} (live site {_va or 'unreadable'})")
except Exception as _e:
    print(f"launches guard skipped: {_e}")

parts = [
    ("jnd-hdb-blocks",  load("hdb-blocks.json")),
    ("jnd-ura-comps",   load("ura-comps.json")),
    ("jnd-rates",       load("market-tab/rates.json")),
    ("jnd-launches",    load("market-tab/launches.json")),
]
# HDB resale txns for Recent Transactions — optional until the first geocode
# backfill produces the file; page JS degrades gracefully without the block.
if os.path.exists("hdb-txns.json"):
    parts.append(("jnd-hdb-txns", load("hdb-txns.json")))
# Market Pulse fundamentals: population, GDP, the URA price index (SingStat, refreshed
# daily but only changing quarterly) and the PR/citizenship grants (ICA, annual, hand
# entered). Optional so a SingStat outage degrades the charts rather than the build.
for _f, _id in (("market-pulse-series.json", "jnd-fundamentals"),
                ("grants.json", "jnd-grants"),
                ("mop-data.json", "jnd-mop"),
                ("map-layers.json", "jnd-map")):
    if os.path.exists(_f):
        parts.append((_id, load(_f)))
block = "<!--JND-DATA-->\n" + "".join(
    f'<script type="application/json" id="{i}">{c}</script>\n' for i, c in parts
) + "<!--/JND-DATA-->"

START, END = "<!--JND-DATA-->", "<!--/JND-DATA-->"
if START in html:
    i = html.index(START); j = html.index(END) + len(END)
    html = html[:i] + block + html[j:]; print("replaced JND-DATA block")
else:
    k = html.index("<!--JND-LIVE-HDB-JS-->")
    html = html[:k] + block + "\n" + html[k:]; print("inserted JND-DATA block")

open(F, "w", encoding="utf-8").write(html)
print(f"inlined {len(parts)} data blocks; file {os.path.getsize(F)/1e6:.2f} MB")
print("ids present:", all(f'id="{i}"' in html for i, _ in parts))
assert 'id="jnd-map"' in html and 'id="jnd-ura-comps"' in html, "baked data missing — refusing to produce an empty page"

# Stage the embedded Decoupling Toolkit alongside the dashboard for the Pages deploy.
# (Done here, not in refresh.yml, so the deploy token doesn't need `workflow` scope.)
if os.path.exists("decoupling.html"):
    os.makedirs("publish", exist_ok=True)
    shutil.copy("decoupling.html", "publish/decoupling.html")
    print("staged decoupling.html -> publish/")

# Stage the versioned sun map. Its assets and data are self-contained.
if os.path.isdir("sun-map"):
    shutil.copytree("sun-map", "publish/sun-map", dirs_exist_ok=True)
    print("staged sun-map/ -> publish/sun-map/")
