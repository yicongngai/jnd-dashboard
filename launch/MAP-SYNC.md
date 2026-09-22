# JND Launches → sun map

Both Pages deployment workflows run `python3 sync_launch_map.py` in their clean
checkout before staging the map. The daily refresh reconciles again at 07:00 SGT.
Commits to the published launch/map files also trigger deployment directly.
The existing approved-launch publisher dispatches `deploy-only.yml`; its approval
and notification behaviour is unchanged. No separate scheduler or credentials.

## Inputs and behaviour

- Only folders with **both** committed `launch.json` and `index.html` are included.
  `launch.preview.json`, `index.preview.html`, `preview.json` and `drops/` are ignored.
- Project IDs use the launch slug, matching existing catalogue names if needed.
  Existing verified coordinates are retained. New locations use an exact OneMap
  building-name match at a single location; ambiguity/failure stays in the review list.
- Address and completion facts update automatically. Geometry hashes cover the
  actual bytes of site plans, schematics, elevations, orientation/massing images,
  and address/storey/site-area/plot-ratio facts. Replacing a file under the same name
  is detected. Price fields and price-slide replacements don't invalidate geometry.
- Geometry assets are detected from filenames and image/link captions (`alt`,
  `title`, `data-cap`). For opaque filenames or slide-only geometry information,
  add `map-source.json` as below. Keep this declaration current when publishing
  slides; there is no OCR or automatic drawing of towers in this compiler.
- `sun-map/data/launch-updates.json` and the catalogue are build outputs. Their
  `checkedAt` records the reconciliation time, not the age of the source/model.
  Source dates come from the committed launch history. The source-status page
  exposes actual asset hashes and the geometry fingerprint.
- Prior geometry remains visible with an explicit review notice. Missing models
  produce markers only. The initial Thomson/Lucerne models are deliberately
  marked for review against the JND slides, not silently certified as current.

## Optional published source declaration

Create `launch/<slug>/map-source.json`:

```json
{
  "geometryAssets": ["assets/pages/slide-17.jpg", "assets/pages/slide-18.jpg"],
  "location": {
    "center": [103.8005, 1.3005],
    "source": "https://www.onemap.gov.sg/",
    "verifiedAt": "2026-09-22"
  }
}
```

Use actual checked coordinates and source URLs. The example is illustrative.
Geometry asset paths must stay inside published `assets/`. Missing declared
assets block acceptance of an updated model. The location declaration is optional.

## Updating a building model

1. Publish the revised slides through the normal launch approval workflow.
2. Read the map's Launch updates page or `data/launch-updates.json` for the exact
   geometry source fingerprint and files. Compare the plan, north orientation,
   block labels, site boundary and storey/elevation schedule.
3. Create/update `launch/<slug>/map-model.json` with `sourceFingerprint`,
   `reviewedAt`, `reviewNote`, `center`, `site` (closed longitude/latitude ring),
   and `towers` (named sections with `floors` and GeoJSON Polygon `geometry`).
   Copy the existing curated model as a starting point only after inspecting it.
   `excludeExistingOsmIds` may list individually checked future-only footprints.
4. Include the reviewed model file in the publishing commit and deploy. The
   compiler checks its shape, coordinates and source fingerprint, then applies
   it automatically. It never changes a fingerprint to approve a model itself.
   A mismatched fingerprint retains the last reviewed model and flags it.

Reviewed model files are persistent inputs in Git, so daily builds retain the
last checked geometry even if a source changes. Do not use only generated
catalogue edits for new JND models. Model acceptance certifies source comparison,
not surveyed heights: the existing storeys × 3 m approximation remains.

## Checks

`python3 -m unittest discover -s tests -p 'test_launch_map_sync.py'`

For a local check run in an isolated checkout: `python3 sync_launch_map.py --offline`.
Never run a production build against unapproved local launch edits. A malformed
published input fails the deployment before overwriting the live Pages artifact.
