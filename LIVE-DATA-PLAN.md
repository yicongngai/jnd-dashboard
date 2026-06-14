# JND Tools — Live Data Plan

_Built on `index-live.html` (a duplicate). The production `index.html` is untouched._

---

## Part B — Live HDB comps  ✅ BUILT & VERIFIED

**Source:** data.gov.sg HDB resale dataset (`d_8b84c4ee58e3cfc0ece0d773c8ca6abc`).
**Why it works client-side:** the API returns `access-control-allow-origin: *` and needs no key,
so the dashboard fetches it directly in the browser. No backend, no proxy — fits the
drag-and-drop single-file workflow exactly.

**What was added (JND Advisory tool, current-property = HDB):**
- A "Live market check" row: town picker (defaults to SENGKANG) + "📡 Fetch comps".
- On click → pulls the latest transactions for that town + flat type, computes the median,
  range, ~$/sqft, transaction count, and date span, then offers **Use median → fill valuation**.
- Verified live: Sengkang 4-room median **$645,000** (range $520k–$900k, ~$646/sqft) pulled in real time.

**Note / honest limitation:** for high-volume town+type combos the fetch caps at 400 most-recent
records, so the window can be ~7 months rather than a full 12. The displayed date span is always
truthful, so you can see exactly what the median is based on.

**Deploy:** drag `index-live.html` onto Netlify (rename to `index.html` on drop, or replace).
Nothing else needed — it's still one self-contained file.

---

## Part A — Live URA private (condo / landed) comps  ⏳ READY FOR YOUR KEY

This powers the **NL Selection Framework** (district stock turnover, YoY price growth, PSF gap)
and quantum comparisons — the bulk of your deals. It is the authoritative, transaction-level
private-property feed, direct from URA.

### Why it cannot be pure client-side (unlike HDB)
1. **Auth:** URA requires a developer **Access Key**, then a daily **Token**. Putting either in
   the HTML would expose it publicly — not acceptable.
2. **CORS:** URA's endpoints are not open to browser cross-origin calls.

So URA runs as a **data-prep step**, not a live browser fetch.

### Step 1 — Register (you do this; I can't create the account)
1. Go to the **URA Data Service** registration page (URA website → Digital Services → Data Service).
2. Register for an **Access Key** (free for the public data service). Accept their terms yourself.
3. Send me the Access Key (or paste it into the script — see Step 2). Keep it out of the HTML.

### Step 2 — Generate the data (I run `ura_fetch.py` on a schedule)
`ura_fetch.py`:
- exchanges your Access Key for a daily Token,
- pulls the private residential transaction batches (`PMI_Resi_Transaction`),
- aggregates per **district** and **market segment** into: median PSF, 12-month transaction
  count (turnover proxy), and YoY price growth,
- writes `ura-comps.json` with an `as_of` date and source note.

> The exact URA endpoint paths and field names are based on the documented v1 Data Service and
> **must be confirmed against the current URA docs once the key is in hand** — URA versions this
> service. The script is structured so only the parse step may need a small tweak.

### Step 3 — Feed it into the dashboard (keeps single-file workflow)
**Recommended:** bake `ura-comps.json` inline into the HTML as `window.JND_URA_DATA = {…}` (a second
injector, same pattern as the HDB one). On each refresh I regenerate and you re-drop the one file.
No folder, no fetch, no CORS.

_(Alternative if you ever move to a git-connected Netlify deploy: ship `ura-comps.json` as a sibling
file and `fetch()` it — same-origin, so no CORS issue. Bigger change to your workflow; not needed now.)_

### Step 4 — Refresh cadence
URA caveat data updates roughly weekly. A scheduled task can regenerate `ura-comps.json` weekly
and hand you the updated file to drop. (You already use scheduled tasks.)

---

## Source tiers (reference)
| Tier | Source | Use | Access |
|------|--------|-----|--------|
| 1 | data.gov.sg | HDB resale + rental | Open, keyless, CORS-open → live in browser |
| 1 | URA Data Service | Private condo/landed caveats, rental, price index | Free key + token → server-side prep |
| 1 | MAS / data.gov.sg | SORA, rates | Open |
| 2 | EdgeProp / PropertyGuru / 99.co | Listings (asking), inventory | Scrape — fragile, ToS grey area |
| 3 | IRAS / CPF / MAS tables | ABSD/BSD/tax/FRS constants | Static, refresh ~yearly at Budget |

**Transacted (URA, data.gov.sg) = trust for advice. Asking (PG, 99) = sentiment/inventory only.**
