#!/usr/bin/env python3
"""Bake a compact HDB block index from data.gov.sg HDB Property Information.
Record: [blk_no, street, townCode, year_completed, typesStr]  (typesStr e.g. '45E')."""
import json, urllib.request, urllib.parse

RES = "d_17f5382f26140b1fdae0ba2ef6239d2f"
TYPECOL = [("2room_sold","2"),("3room_sold","3"),("4room_sold","4"),
           ("5room_sold","5"),("exec_sold","E"),("multigen_sold","M"),
           ("studio_apartment_sold","S")]

def fetch_all():
    out, off = [], 0
    while True:
        q = {"resource_id": RES, "limit": 5000, "offset": off}
        url = "https://data.gov.sg/api/action/datastore_search?" + urllib.parse.urlencode(q)
        j = json.load(urllib.request.urlopen(url, timeout=90))["result"]
        recs = j["records"]
        if not recs: break
        out += recs; off += len(recs)
        if off >= int(j.get("total", 0)): break
    return out

def main():
    recs = fetch_all()
    blocks = []
    for r in recs:
        if r.get("residential") != "Y": continue
        types = "".join(ch for col, ch in TYPECOL if int(r.get(col, 0) or 0) > 0)
        if not types: continue
        try: yr = int(r.get("year_completed") or 0)
        except: yr = 0
        blocks.append([r["blk_no"], r["street"], r["bldg_contract_town"], yr, types])
    out = {"source": "data.gov.sg HDB Property Information (d_17f5382f...)",
           "fields": "[blk_no, street, townCode, year_completed, typesStr]",
           "blocks": blocks}
    with open("hdb-blocks.json", "w") as f:
        json.dump(out, f, separators=(",", ":"))
    import os
    print(f"WROTE hdb-blocks.json: {len(blocks)} residential blocks, {os.path.getsize('hdb-blocks.json')/1e6:.2f} MB")

if __name__ == "__main__":
    main()
