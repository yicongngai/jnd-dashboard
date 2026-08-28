#!/usr/bin/env python3
"""Inline all baked data (HDB blocks, URA comps, rates, launches) into the dashboard
as <script type=application/json> blocks, inside re-runnable <!--JND-DATA--> fences."""
import json, os, shutil
F = "index-live-auto.html"
html = open(F, encoding="utf-8").read()

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
    import subprocess as _sp
    _r = _sp.run(["python3", "singstat_fetch.py"], capture_output=True, text=True, timeout=300)
    print(_r.stdout.strip() or "singstat_fetch: no output")
    if _r.returncode != 0:
        print("singstat_fetch FAILED — keeping last-good market-pulse-series.json")
except Exception as _e:
    print(f"singstat_fetch skipped: {_e}")

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
                ("grants.json", "jnd-grants")):
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

# Stage the embedded Decoupling Toolkit alongside the dashboard for the Pages deploy.
# (Done here, not in refresh.yml, so the deploy token doesn't need `workflow` scope.)
if os.path.exists("decoupling.html"):
    os.makedirs("publish", exist_ok=True)
    shutil.copy("decoupling.html", "publish/decoupling.html")
    print("staged decoupling.html -> publish/")
