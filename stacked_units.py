#!/usr/bin/env python3
"""Stacked Homes floor-plan unit mappings, gated before anything can quote them.

    python3 stacked_units.py                 # coverage + what is quarantined
    python3 stacked_units.py --project ZEDGE # one project in detail
    python3 stacked_units.py --write-queue   # queue the rejects for a human read

WHY THE GATE EXISTS
    These mappings were OCR'd off developer floor-plan artwork, not handed over
    by an API. The reader already refuses to guess when a plan's two statements
    of a unit range disagree. What it cannot catch is a plan whose single
    statement is confidently wrong: The Sorrento's `floor-plan_37.jpg` yields
    units #41-25 through #60-25 in a building URA has never seen transact above
    floor 5. Read alone, that plan is self-consistent. It is still nonsense.

    So each project is checked against evidence from OUTSIDE the artwork — the
    top floor band URA has ever recorded a caveat in. A caveat at floor band
    21-25 is proof the building reaches at least 25. It is never proof of the
    roof, so a full band of slack (+5) is allowed before anything is doubted.
    On the current data this doubts 0.94% of units across 64 of 527 projects,
    and it leaves mixed-height developments alone — THE RESERVE RESIDENCES keeps
    its tall stack, which a median-across-stacks rule wrongly stripped.

WHAT IT DOES NOT DO
    It does not delete. A doubted unit is returned with `_unverified` set so the
    caller can say UNCONFIRMED, which is the house rule for this whole file:
    a wrong answer is worse to a client than no answer. Justin reads the
    rejects himself — same standing arrangement as the review queue.
"""
import argparse
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
UNITS = os.path.join(HERE, "stacked-units.json")
URA = os.path.join(HERE, "ura-comps.json")
QUEUE = os.path.join(HERE, "stacked-quarantine.json")

BAND_SLACK = 5      # one full URA floor band of benefit-of-the-doubt
HARD_MAX = 70       # nothing residential in SG is this tall; 0 is never a floor


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def floor_of(unit):
    try:
        return int((unit or "").lstrip("#").split("-")[0])
    except (ValueError, IndexError):
        return None


def _ura_tops():
    """Project -> highest floor URA has ever recorded a caveat in."""
    if not os.path.exists(URA):
        return {}
    tops = {}
    for r in json.load(open(URA, encoding="utf-8"))["projects"]:
        hi = None
        for row in r["t"]:
            band = row[7]
            if not band or band == "-":
                continue
            top = band.split("-")[-1]
            if top.isdigit():
                hi = max(hi or 0, int(top))
        if hi:
            tops[norm(r["p"])] = hi
    return tops


class Store:
    def __init__(self):
        self.by_project = {}
        self.ceilings = {}
        if not os.path.exists(UNITS):
            return
        raw = json.load(open(UNITS, encoding="utf-8"))
        tops = _ura_tops()
        for name, d in raw.items():
            key = norm(name)
            top = tops.get(key)
            # No URA evidence -> no ceiling -> nothing is doubted on height.
            # Silence is not evidence of a short building.
            self.ceilings[key] = (top + BAND_SLACK) if top else None
            self.by_project[key] = (name, d)

    def _flag(self, key, unit):
        f = floor_of(unit)
        if f is None:
            return "unit number not parseable"
        if f == 0 or f > HARD_MAX:
            return f"floor {f} is not a real floor"
        ceil = self.ceilings.get(key)
        if ceil and f > ceil:
            return (f"floor {f} is above anything URA has recorded here "
                    f"(top caveat band {ceil - BAND_SLACK})")
        return None

    def lookup(self, project, unit):
        """ERA-PRO-shaped record for a unit, or None. Never raises."""
        key = norm(project)
        if key not in self.by_project:
            return None
        name, d = self.by_project[key]
        want = (unit or "").lstrip("#")
        for u in d["units"]:
            if u["unit"].lstrip("#") != want:
                continue
            bad = self._flag(key, u["unit"])
            return {
                "project": name,
                "unit": u["unit"],
                "area": u.get("sqft"),
                "plan": u.get("plan"),
                "block": u.get("tower"),
                "type": None,
                "_source": "Stacked Homes floor plan (OCR)",
                "_plan_image": u.get("src"),
                "_unverified": bad,
            }
        return {"project": name, "_no_unit": True,
                "_source": "Stacked Homes floor plan (OCR)"}

    def audit(self):
        rows = []
        for key, (name, d) in self.by_project.items():
            bad = [(u["unit"], u.get("src"), self._flag(key, u["unit"]))
                   for u in d["units"]]
            bad = [b for b in bad if b[2]]
            if bad:
                rows.append((name, len(d["units"]), bad))
        rows.sort(key=lambda r: -len(r[2]))
        return rows


_store = None


def store():
    global _store
    if _store is None:
        _store = Store()
    return _store


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project")
    ap.add_argument("--unit")
    ap.add_argument("--write-queue", action="store_true")
    a = ap.parse_args()
    s = store()

    if a.project and a.unit:
        print(json.dumps(s.lookup(a.project, a.unit), indent=1))
        return
    if a.project:
        key = norm(a.project)
        if key not in s.by_project:
            raise SystemExit(f"{a.project!r} not in the Stacked mappings")
        name, d = s.by_project[key]
        ceil = s.ceilings.get(key)
        bad = [b for b in s.audit() if b[0] == name]
        print(f"{name}: {len(d['units'])} units, ceiling "
              f"{ceil if ceil else 'none (no URA evidence)'}")
        if bad:
            print(f"  doubted: {len(bad[0][2])}")
            for u, src, why in bad[0][2][:20]:
                print(f"    {u:<10} {why}   [{src}]")
        return

    rows = s.audit()
    tot = sum(len(d["units"]) for _, d in s.by_project.values())
    dropped = sum(len(r[2]) for r in rows)
    withura = sum(1 for v in s.ceilings.values() if v)
    print(f"projects {len(s.by_project)} | with URA height evidence {withura}")
    print(f"units {tot:,} | doubted {dropped:,} ({dropped / tot * 100:.2f}%) "
          f"across {len(rows)} projects\n")
    for name, n, bad in rows[:15]:
        print(f"  {name[:32]:<34} units={n:<5} doubted={len(bad):<4} "
              f"e.g. {bad[0][0]} — {bad[0][2]}")

    if a.write_queue:
        out = [{"project": name, "unit": u, "plan_image": src, "reason": why}
               for name, _, bad in rows for u, src, why in bad]
        json.dump(out, open(QUEUE, "w"), indent=1)
        print(f"\n-> {os.path.basename(QUEUE)} ({len(out):,} units for a human read)")


if __name__ == "__main__":
    main()
