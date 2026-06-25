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

parts = [
    ("jnd-hdb-blocks",  load("hdb-blocks.json")),
    ("jnd-ura-comps",   load("ura-comps.json")),
    ("jnd-rates",       load("market-tab/rates.json")),
    ("jnd-launches",    load("market-tab/launches.json")),
]
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
