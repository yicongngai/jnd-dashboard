#!/usr/bin/env python3
"""
era_scrape.py v3 — FULLY AUTOMATED ERA new-launch board. No manual list, no ticking.

Pipeline (re-run anytime / on a schedule):
  1. refresh slug list from the gallery (catches NEW launches)
  2. for each slug: GET /units (stack) + /fact-sheet (server meta/body)
  3. classify deterministically and WRITE launches.json (the board's data file)

Classification (validated signals):
  overseas  : fact-sheet text names a foreign country         -> exclude
  EC        : 'executive condominium' in fact-sheet           -> exclude
  slug type : industrial/food/tech/plot/shoppes/xchange       -> commercial (exclude)
              villa/collection/cluster/greenbank              -> landed     (exclude)
  LAUNCHED (has /units stack):
      house-type cells & no bedrooms -> landed (exclude)
      bedroom cells                  -> residential IN-MARKET (avail = unsold)
      cells but no bedrooms          -> commercial (exclude)
  PRE-LAUNCH (no stack):
      completion year < this year    -> completed/old (exclude)
      else                           -> residential UPCOMING (avail = full size)
Output: launches.json (board) + era_classified.json (audit) + summary.
"""
import re, json, urllib.request, concurrent.futures
UA={"User-Agent":"Mozilla/5.0 (JND-Tools)"}; TIMEOUT=30; THIS_YEAR=2026

OVERSEAS=re.compile(r"cambodia|phnom|malaysia|johor|bangkok|thailand|vietnam|hanoi|\blondon\b|australia|indonesia|batam|bintan|forest city",re.I)
SLUG_COMM=re.compile(r"industrial|factory|foodworks|foodnex|gourmet|ecofood|technolink|techpark|techpoint|enterprise|warehouse|shoppes|xchange|\bplot\b",re.I)
SLUG_LANDED=re.compile(r"villa|collection|cluster|greenbank|bungalow",re.I)
HOUSE=re.compile(r"terrace|semi-?d\b|bungalow|strata house|cluster house",re.I)
BR=re.compile(r"[0-9]\s?br\b|bedroom",re.I)
EC=re.compile(r"executive condominium",re.I)
SLUG_DROP=re.compile(r"space-18|visioncrest",re.I)   # user-excluded edge cases
MONTHS={'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
STATUS_OVERRIDE={"lentor-gardens-residences":"pre_launch"}   # known preview-only projects
FRESH_CUTOFF=202412   # launched on/after Dec 2024 counts as "fresh" (~18 months)
MON3=["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def fetch(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=TIMEOUT) as r:
            return r.read().decode("utf-8","replace")
    except Exception: return ""

def refresh_slugs():
    h=fetch("https://www.eraprojects.sg/")
    slugs=sorted(set(re.findall(r"https?://([a-z0-9-]+)\.eraprojects\.sg",h)))
    slugs=[s for s in slugs if s!="www"]
    if slugs: open("era_slugs.txt","w").write("\n".join(slugs))
    return slugs or open("era_slugs.txt").read().split()

def parse_units(html):
    tot=sold=resv=avail=br=house=0; dates=[]
    for c in re.split(r"<td\b",html):
        t=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",c)).strip().lower()
        if "sqft" not in t: continue
        tot+=1
        if "sold" in t: sold+=1
        elif re.search(r"reserv|hold|book",t): resv+=1
        else: avail+=1
        if BR.search(t): br+=1
        if HOUSE.search(t): house+=1
        dm=re.search(r"(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})",t)
        if dm: dates.append(int(dm.group(3))*10000+MONTHS[dm.group(2)]*100+int(dm.group(1)))
    return dict(cells=tot,sold=sold,avail=avail,br=br,house=house,launch=(min(dates) if dates else None))

def factsheet(html):
    m=re.search(r"<meta[^>]+(?:description|og:description)[^>]+content=\"([^\"]+)\"",html,re.I)
    desc=(m.group(1) if m else "")+" "+re.sub(r"<[^>]+>"," ",html)[:6000]
    country="overseas" if OVERSEAS.search(desc) else ("SG" if re.search(r"singapore",desc,re.I) else "?")
    dm=re.search(r"\bD([0-2]?\d)\b\s*[-–]",desc)
    tot=re.search(r"total of ([0-9][0-9,]{1,5})\s*units?",desc,re.I)
    yr=re.search(r"completed in[^\d]*(?:\d{1,2}/\d{1,2}/)?(\d{4})",desc,re.I)
    return dict(country=country, district=("D%02d"%int(dm.group(1)) if dm else ""),
                total=(int(tot.group(1).replace(",","")) if tot else None),
                top_year=(int(yr.group(1)) if yr else None), ec=bool(EC.search(html)))

def classify(slug):
    base=f"https://{slug}.eraprojects.sg"
    u=parse_units(fetch(base+"/units")); fs=factsheet(fetch(base+"/fact-sheet"))
    launched=u["cells"]>0
    status="in_market" if launched else "pre_launch"
    keep=False
    if SLUG_DROP.search(slug):               typ="excluded"
    elif fs["country"]=="overseas":          typ="overseas"
    elif fs["ec"]:                           typ="EC"
    elif SLUG_LANDED.search(slug):           typ="landed"
    elif SLUG_COMM.search(slug):             typ="commercial"
    elif launched and u["house"]>0 and u["br"]==0: typ="landed"
    elif launched and u["br"]>0:             typ="residential"; keep=True
    elif launched and u["cells"]>0:          typ="commercial"
    elif fs["top_year"] and fs["top_year"]<THIS_YEAR: typ="completed"
    else:                                    typ="residential"; keep=True   # pre-launch residential
    avail=u["avail"] if launched else fs["total"]
    ov=STATUS_OVERRIDE.get(slug)
    if ov=="pre_launch" and keep: status="pre_launch"; avail=fs["total"] or u["cells"] or avail
    elif ov=="in_market" and keep: status="in_market"
    return dict(slug=slug,status=status,type=typ,keep=keep,district=fs["district"],
                country=fs["country"],top_year=fs["top_year"],avail=avail,
                br=u["br"],house=u["house"],cells=u["cells"],launch=u["launch"])

def titlecase(s):
    f={"gls":"GLS","ec":"EC","bt":"BT","w":"W","at":"at","by":"by","the":"The","on":"on","of":"of"}
    return " ".join(f.get(w,w.capitalize()) for w in s.split("-"))
def region_of(d):
    m=re.match(r"D0?(\d+)",d or ""); n=int(m.group(1)) if m else 0
    return "CCR" if n in (1,2,6,9,10,11) else "RCR" if n in (3,4,5,7,8,12,13,14,15,20) else ("OCR" if n else "")

def main():
    slugs=refresh_slugs(); print(f"{len(slugs)} projects from gallery")
    out=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(classify,slugs): out.append(r)
    json.dump(out,open("era_classified.json","w"),indent=1)
    keep=[r for r in out if r["keep"]]
    im=sorted([r for r in keep if r["status"]=="in_market" and (r["avail"] or 0)>0],key=lambda x:(x.get("top_year") or 0),reverse=True)
    pl=sorted([r for r in keep if r["status"]=="pre_launch" and r["avail"]],key=lambda x:-(x["avail"] or 0))
    def fmtlaunch(v): return (MON3[(v//100)%100]+" "+str(v//10000)) if v else ""
    def ent(r,k):
        o={"name":titlecase(r["slug"]),"district":r["district"],"region":region_of(r["district"]),"avail":r["avail"],"developer":""}
        if k=="in":
            o["top"]=("TOP "+str(r["top_year"])) if r.get("top_year") else "TOP n/a"
            o["stale"]=not (r.get("top_year") and r["top_year"]>=THIS_YEAR)
        else: o["launch"]="upcoming"
        return o
    launches={"_meta":{"metric":"avail = units available (in-market unsold / upcoming full size)",
              "scope":"SG residential condos — FULLY AUTO-CLASSIFIED from ERA gallery, no manual list",
              "as_of":"2026-06-14","auto":True,"counts":{"in_market":len(im),"rest_of_2026":len(pl)}},
              "in_market":[ent(r,"in") for r in im],"rest_of_2026":[ent(r,"up") for r in pl]}
    json.dump(launches,open("launches.json","w"),indent=2)
    from collections import Counter
    print("types:",dict(Counter(r["type"] for r in out)))
    print(f"BOARD -> in-market {len(im)} ({sum(r['avail'] or 0 for r in im):,} units) | upcoming {len(pl)} ({sum(r['avail'] or 0 for r in pl):,} units)")
    nullav=[r["slug"] for r in keep if not r["avail"]]
    if nullav: print(f"  ({len(nullav)} kept with no unit count: {nullav[:10]})")

if __name__=="__main__": main()
