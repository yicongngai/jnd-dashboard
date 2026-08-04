#!/usr/bin/env python3
"""Resolve a project name to the other vault notes about the same project.

The four feeds name the same development differently — ERA PRO says "LIV@MB",
the PG tracker says "Liv Mb", URA shouts "PARC ESTA". Punctuation and case are
the only difference in almost every case, so the key drops both.

Matching is UNIQUE-MATCH-ONLY. Loose matching has produced a confident wrong
answer three separate times on this data (an availability merge that marked a
whole block sold, a missed launch, "The M" matched to "THE MYST"). A key that
resolves to two candidates is skipped, not guessed — a missing link is a
non-event, a wrong one is a false statement about a client's asset.

Every link is also conditional on the target note existing. Unconditional
cross-links previously created 5,729 broken links in one pass.
"""
import os
import re
import unicodedata
from collections import defaultdict

VAULT = os.path.expanduser("~/Desktop/justin vault")
MI = os.path.join(VAULT, "04 Market Intelligence")

# label -> (folder, filename suffix)
FAMILIES = [
    ("Transacted history", os.path.join(MI, "URA Transactions", "projects"), " — transactions"),
    ("On the market", os.path.join(MI, "PG Listings", "projects"), " — listings"),
    ("Launch board", os.path.join(MI, "New Launches", "projects"), " — launch"),
    ("Full dossier", os.path.join(MI, "New Launches", "dossiers"), " — dossier"),
    ("Full dossier", os.path.join(MI, "Past Launches", "dossiers"), " — dossier"),
    # Deliberately a DIFFERENT label from the two above. Sharing "Full dossier"
    # would give a project in both sets two candidates under one label, and the
    # unique-match rule would then skip BOTH, silently breaking links that work
    # today. A separate label keeps them independent.
    ("Condo directory", os.path.join(MI, "Condo Directory", "dossiers"), " — dossier"),
]

# Names that differ by more than punctuation, so no normaliser can join them.
# CURATED, never inferred — each one verified against an independent fact before
# being added, because a wrong alias attaches another project's prices.
#   Enchanté  -> URA "ENCHANT": both 25 units, both Evelyn Road D11
#   Pullman Residence -> "Pullman Residences Newton": 338 units, Dunearn Road D11
ALIASES = {
    "enchante": "enchant",
    "pullmanresidence": "pullmanresidences",
    "pullmanresidences": "pullmanresidencesnewton",
}

_INDEX = None


def key(name):
    """Punctuation- and case-insensitive. 'LIV@MB' and 'Liv Mb' both -> 'livmb'.

    Accents must be FOLDED, not stripped. Deleting them made "Rivière" key to
    'rivire' while URA's "RIVIERE" keyed to 'riviere', so the two notes about the
    same project never matched. Same for OLÁ and Enchanté.
    """
    n = re.sub(r"[一-鿿]+", "", name or "")
    n = unicodedata.normalize("NFD", n)
    n = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", n.lower())


def _index():
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    idx = defaultdict(lambda: defaultdict(list))
    for label, folder, suffix in FAMILIES:
        if not os.path.isdir(folder):
            continue
        for f in os.listdir(folder):
            if not f.endswith(".md") or not f[:-3].endswith(suffix):
                continue
            stem = f[:-3]
            idx[key(stem[: -len(suffix)])][label].append(stem)
    _INDEX = idx
    return idx


def related(project_name, exclude=None):
    """[(label, note-name)] for every other note about this project.

    `exclude` is the note being written, so a dossier never links to itself.
    """
    idx = _index()
    # Aliases are SYMMETRIC and transitive: the dossier must reach the URA note
    # and the URA note must reach the dossier, so walk the whole alias group
    # rather than following the map one way.
    group, frontier = set(), [key(project_name)]
    while frontier:
        k = frontier.pop()
        if k in group:
            continue
        group.add(k)
        frontier += [v for a, v in ALIASES.items() if a == k]
        frontier += [a for a, v in ALIASES.items() if v == k]

    fams = {}
    for k in group:
        for lab, ns in idx.get(k, {}).items():
            fams.setdefault(lab, []).extend(ns)

    out = []
    for label, names in sorted(fams.items()):
        names = [n for n in names if n != exclude]
        if len(names) == 1:                  # unique match only — see module docstring
            out.append((label, names[0]))
    return out


def block(project_name, exclude=None, heading=True):
    """The markdown to drop into a note. Empty string when nothing matched, so
    the caller can append it unconditionally."""
    rel = related(project_name, exclude)
    if not rel:
        return ""
    line = " · ".join(f"{lab}: [[{n}]]" for lab, n in rel)
    return (("## Related\n\n" if heading else "") + line + "\n")


if __name__ == "__main__":
    import sys
    idx = _index()
    amb = {k: v for k, v in idx.items()
           for lab, ns in v.items() if len(ns) > 1}
    print(f"indexed {len(idx)} project keys across {len(FAMILIES)} note families")
    print(f"ambiguous keys (skipped, never guessed): {len(amb)}")
    for n in sys.argv[1:] or ["LIV@MB", "Parc Esta", "Tembusu Grand", "Affinity at Serangoon"]:
        print(f"  {n:<26} -> {related(n) or '(no matches)'}")
