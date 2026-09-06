#!/usr/bin/env python3
"""Rebuild launch/index.json (the Launches tab on the toolkit reads it). Run after adding a launch."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
HERO = {"lucerne-grand": "hero-river-dusk", "thomson-reserve": "towers-pool"}
items = []
for slug in sorted(os.listdir(HERE)):
    lj = os.path.join(HERE, slug, "launch.json")
    if not os.path.exists(lj):
        continue
    D = json.load(open(lj, encoding="utf-8"))
    hero = HERO.get(slug) or (D.get("gallery") or [["", ""]])[0][0]
    items.append({"slug": slug, "name": D["name"], "district": D.get("district", ""), "preview": D.get("preview", ""),
                  "booking": D.get("booking", ""), "thesis": D.get("thesis", ""), "hero": f"launch/{slug}/assets/img/{hero}.jpg"})
json.dump({"launches": items}, open(os.path.join(HERE, "index.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("launch/index.json:", ", ".join(i["name"] for i in items))
