#!/usr/bin/env python3
"""Build the launch presentation page from launch.json and the assets folder.
Re-run after any change to launch.json or the images. One file out: index.html."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "launch.json"), encoding="utf-8"))
money = lambda v: "$" + format(int(v), ",")
mil = lambda v: "$%.2fM" % (v / 1e6)

def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

facts = [("Preview", D["preview"]), ("Homes", format(D["units"], ",")), ("Towers", D["towers"]), ("Site", format(D["site_sqft"], ",") + " sqft, plot ratio 2.1"),
         ("Tenure", D["tenure"]), ("Vacant possession", D["novp"]), ("Land", "$%s psf ppr, %s" % (format(D["land_psf_ppr"], ","), D["land_month"])), ("Developer", D["developer"]),
         ("Architect", D["architect"]), ("Landscape", D["landscape"]), ("Interiors", D["interiors"]), ("Builder", D["builder"]), ("Carpark", format(D["carpark"], ",") + " lots"), ("Address", D["address"])]
facts_html = "".join('<div class="fact"><div class="k">%s</div><div class="v">%s</div></div>' % (esc(k), esc(v)) for k, v in facts)
brief_html = "".join('<div class="bcard"><h3>%s</h3><ul>%s</ul></div>' % (esc(t), "".join("<li>%s</li>" % esc(x) for x in xs)) for t, xs in D["brief"].items())
gallery_html = "".join('<figure class="g"><img src="assets/img/%s.jpg" alt="%s" loading="lazy" decoding="async"><figcaption>%s</figcaption></figure>' % (f, esc(c), esc(c)) for f, c in D["gallery"])
PSFS = [2550, 2600, 2700, 2800, 2900, 3000]
price_rows = "".join('<tr><td><b>%s</b><span>%s sqft</span></td><td class="n from">From %s</td>%s</tr>' % (esc(t), format(sz, ","), esc(fr), "".join('<td class="n%s">%s</td>' % (" kit" if ps in (2700, 2800) else "", mil(sz * ps)) for ps in PSFS)) for t, sz, _, fr in D["prices"])
price_head = '<th class="n from">Starting price</th>' + "".join('<th class="n%s">$%s psf</th>' % (" kit" if ps in (2700, 2800) else "", format(ps, ",")) for ps in PSFS)
neigh_rows = "".join('<tr class="nb" data-psf="%d" data-top="%d" data-asnew="%d"><td><b>%s</b><span>%s, finished %d, %s units</span></td><td>%s<span>%s</span></td><td class="n mid">%d years</td><td class="n">%s</td></tr>' % (
    n["psf"], n["top"], n["asnew"], esc(n["name"]), esc(n["where"]), n["top"], format(n["units"], ","), esc(n["resale"]), esc(n["unit"]), n["yrs"], "$%s psf" % format(n["asnew"], ",")) for n in D["neighbours"])
upside_html = ""
jtx_rows = "".join('<tr class="%s"><td>%s</td><td>%s</td><td class="n">%s sqft</td><td>%s</td><td class="n">%s</td><td class="n">$%s psf</td></tr>' % ("hi" if hi else "", esc(m), esc(f), sz, esc(t), mil(p), format(psf, ",")) for m, f, sz, t, p, psf, hi in D["jadescape_tx"])
sinming_rows = "".join('<tr><td>%s</td><td>%s</td><td>%s</td><td class="n">%s</td></tr>' % (esc(b), esc(t), esc(m), money(p)) for b, t, m, p in D["hdb"])
evidence_html = "".join('<figure class="ev"><img src="assets/slides/%s.jpg" alt="Slide" loading="lazy" decoding="async"><figcaption><span>For Thomson Reserve</span>%s</figcaption></figure>' % (f, esc(c)) for f, c in D["evidence"])
timeline_html = "".join('<div class="tl"><div class="d">%s</div><div class="w">%s</div></div>' % (esc(a), esc(b)) for a, b in D["timeline"])
falsify_html = "".join("<li>%s</li>" % esc(x) for x in D["falsify"])
mix_html = "".join('<div class="mix"><div class="n">%s</div><div class="l">%s, %s</div></div>' % (format(n, ","), esc(t), p) for t, n, p in D["mix"])

HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Thomson Reserve</title>
<meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?{{FONTS}}&display=swap">
<style>
:root{{THEMEVARS}}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--ink);font-family:var(--font-body);font-size:16px;line-height:1.5;-webkit-font-smoothing:antialiased;overflow-x:hidden}
a{color:inherit;text-decoration:none}
img{display:block;max-width:100%}
.wrap{max-width:1280px;margin:0 auto;padding:0 56px}
section{position:relative;padding:120px 0}
.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--g3);margin-bottom:18px}
h2{font-family:var(--font-display);font-size:54px;font-weight:200;letter-spacing:-.03em;line-height:1.06;max-width:900px;text-wrap:balance}
h2 b{font-weight:500}
.lede{font-size:18px;color:var(--g4);max-width:720px;margin-top:22px;line-height:1.6}
.reveal{opacity:0;transform:translateY(26px);transition:opacity 1s cubic-bezier(.2,.7,.2,1),transform 1s cubic-bezier(.2,.7,.2,1)}
.reveal.in{opacity:1;transform:none}
.reveal.d1{transition-delay:.12s}.reveal.d2{transition-delay:.24s}.reveal.d3{transition-delay:.36s}
/* hero */
#hero{height:100vh;min-height:680px;padding:0;background:var(--dark2);color:#FFF;overflow:hidden}
#hero .bg{position:absolute;inset:0;background:url(assets/img/towers-pool.jpg) center/cover;animation:kb 28s ease-in-out infinite alternate;transform-origin:60% 40%}
@keyframes kb{from{transform:scale(1.04) translate(0,0)}to{transform:scale(1.16) translate(-2%,-1.5%)}}
#hero .veil{position:absolute;inset:0;background:linear-gradient(180deg,rgba(var(--dark2rgb),.25) 0%,rgba(var(--dark2rgb),.15) 40%,rgba(var(--dark2rgb),.85) 100%)}
#hero .top{position:absolute;top:34px;left:56px;right:56px;display:flex;justify-content:space-between;align-items:center;font-size:13px;color:rgba(255,255,255,.75);z-index:2}
#hero .top b{font-weight:500;color:#FFF}
#hero .top .jnd span{color:var(--gold)}
#hero .txt{position:absolute;left:56px;right:56px;bottom:92px;z-index:2;max-width:980px}
#hero .eyebrow{color:rgba(255,255,255,.7)}
#hero h1{font-family:var(--font-h1);font-size:88px;font-weight:100;letter-spacing:.08em;line-height:1.04;margin:0 0 22px;text-transform:uppercase}
#hero .thesis{font-size:20px;color:rgba(255,255,255,.88);max-width:760px;line-height:1.5;font-weight:300}
#hero .cue{position:absolute;right:56px;bottom:44px;z-index:2;font-size:12px;color:rgba(255,255,255,.6);display:flex;align-items:center;gap:10px}
#hero .cue i{width:1px;height:38px;background:rgba(255,255,255,.5);display:block;animation:cue 2.2s ease-in-out infinite}
@keyframes cue{0%{transform:scaleY(0);transform-origin:top}50%{transform:scaleY(1);transform-origin:top}51%{transform-origin:bottom}100%{transform:scaleY(0);transform-origin:bottom}}
/* chapters nav */
#nav{position:fixed;right:22px;top:50%;transform:translateY(-50%);z-index:50;display:flex;flex-direction:column;gap:12px}
#nav a{width:8px;height:8px;border-radius:50%;background:rgba(27,29,34,.2);display:block;position:relative;transition:background .3s,transform .3s}
#nav a.on{background:var(--e4);transform:scale(1.35)}
#nav a span{position:absolute;right:18px;top:50%;transform:translateY(-50%);white-space:nowrap;font-size:12px;color:var(--g4);opacity:0;transition:opacity .25s;pointer-events:none}
#nav a:hover span{opacity:1}
body.dark #nav a{background:rgba(255,255,255,.3)} body.dark #nav a.on{background:var(--gold)} body.dark #nav a span{color:rgba(255,255,255,.7)}
/* place */
.three{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:56px}
.stat{background:var(--card);border-radius:22px;padding:30px 32px 28px;border:1px solid rgba(27,29,34,.05);box-shadow:0 12px 40px rgba(27,29,34,.05)}
.stat .n{font-size:44px;font-weight:200;letter-spacing:-.03em;line-height:1}
.stat .l{color:var(--g4);margin-top:10px;font-size:14px}
.maps{display:grid;grid-template-columns:1.2fr .8fr;gap:24px;margin-top:24px}
.maps img{border-radius:22px;width:100%;height:100%;object-fit:cover;box-shadow:0 12px 40px rgba(27,29,34,.08)}
.facts{display:grid;grid-template-columns:repeat(4,1fr);gap:18px 32px;margin-top:56px;border-top:1px solid var(--g1);padding-top:32px}
.fact .k{font-size:12px;color:var(--g3)}.fact .v{font-size:15px;margin-top:2px}
/* product */
#product{background:var(--dark);color:var(--ondark);padding-bottom:0}
#product h2{color:#FFF}#product .lede{color:var(--ondark2)}#product .eyebrow{color:var(--ondark3)}
.bgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:56px}
.bcard{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:22px;padding:26px 28px}
.bcard h3{font-size:15px;font-weight:500;color:#FFF;margin-bottom:12px}
.bcard li{list-style:none;color:var(--ondark4);font-size:14px;padding:5px 0;border-top:1px solid rgba(255,255,255,.06)}
.mixrow{display:flex;gap:56px;margin-top:40px}
.mix .n{font-size:56px;font-weight:200;letter-spacing:-.03em;color:#FFF;line-height:1}.mix .l{color:var(--ondark2);margin-top:8px;font-size:14px}
.gallery{display:flex;gap:18px;overflow-x:auto;scroll-snap-type:x mandatory;padding:56px 56px 72px;scrollbar-width:none;cursor:grab}
.gallery::-webkit-scrollbar{display:none}
.gallery .g{flex:0 0 min(78vw,1040px);scroll-snap-align:center;position:relative;border-radius:26px;overflow:hidden;aspect-ratio:16/9;background:var(--ink)}
.gallery .g img{width:100%;height:100%;object-fit:cover;transform:scale(1.02);transition:transform 1.2s ease}
.gallery .g:hover img{transform:scale(1.06)}
.gallery figcaption{position:absolute;left:26px;bottom:22px;font-size:14px;color:#FFF;text-shadow:0 2px 16px rgba(0,0,0,.6)}
.ghint{color:var(--ondark3);font-size:12.5px;text-align:center;padding-bottom:40px;margin-top:-40px}
/* price */
.ptable{width:100%;border-collapse:collapse;margin-top:40px;background:var(--card);border-radius:22px;overflow:hidden;box-shadow:0 12px 40px rgba(27,29,34,.05)}
.ptable th{font-weight:400;color:var(--g3);font-size:12.5px;text-align:left;padding:16px 22px;border-bottom:1px solid var(--g1)}
.ptable td{padding:14px 22px;border-bottom:1px solid var(--line);font-size:15px}
.ptable tr:last-child td{border-bottom:0}
.ptable .n,.ptable th.n{text-align:right;font-variant-numeric:tabular-nums}
.note{font-size:12.5px;color:var(--g3);margin-top:14px;max-width:820px}
.pairs{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:56px}
.pair{background:var(--card);border-radius:22px;padding:30px 32px;border:1px solid rgba(27,29,34,.05);box-shadow:0 12px 40px rgba(27,29,34,.05);position:relative}
.pair.tr{background:var(--ink);color:#FFF}
.pair .who{font-size:12.5px;color:var(--g3)}.pair.tr .who{color:var(--ondark2)}
.pair .p{font-size:48px;font-weight:200;letter-spacing:-.03em;margin:10px 0 6px;line-height:1}
.pair .d{font-size:14px;color:var(--g4)}.pair.tr .d{color:var(--ondark4)}
.pair .tag{position:absolute;top:26px;right:26px;font-size:11.5px;border-radius:999px;padding:4px 10px;background:var(--g1);color:var(--g5)}
.pair.tr .tag{background:var(--e4);color:#FFF}
.ask{font-size:26px;font-weight:300;margin-top:28px;letter-spacing:-.01em}
.matrix td b{font-weight:500;display:block}.matrix td span{display:block;font-size:12px;color:var(--g3)}
.matrix td.kit,.matrix th.kit{background:var(--tint)}.matrix td.kit{font-weight:500}.matrix th.kit{color:var(--e5)}
.matrix td.from,.matrix th.from{background:var(--tint2);color:var(--e5);white-space:nowrap}.matrix td.from{font-weight:500}
.proof{display:grid;grid-template-columns:1.15fr .85fr;gap:24px;margin-top:40px;align-items:start}
.jtx{width:100%;border-collapse:collapse;background:var(--card);border-radius:22px;overflow:hidden;box-shadow:0 12px 40px rgba(27,29,34,.05)}
.jtx th{font-weight:400;color:var(--g3);font-size:12.5px;text-align:left;padding:14px 18px;border-bottom:1px solid var(--g1)}
.jtx td{padding:13px 18px;border-bottom:1px solid var(--line);font-size:14px}.jtx .n,.jtx th.n{text-align:right;font-variant-numeric:tabular-nums}
.jtx tr.hi td{background:var(--tint);font-weight:500}
.pplan{background:var(--card);border-radius:22px;padding:18px 18px 16px;border:1px solid rgba(27,29,34,.05);box-shadow:0 12px 40px rgba(27,29,34,.05)}
.pplan img{border-radius:12px;width:100%}.pplan figcaption{font-size:13px;color:var(--g4);margin-top:12px;line-height:1.5}.pplan b{color:var(--ink);font-weight:500}
@media (max-width:900px){.proof{grid-template-columns:1fr}}
/* neighbours */
.ntable{width:100%;border-collapse:collapse;margin-top:44px;background:var(--card);border-radius:22px;overflow:hidden;box-shadow:0 12px 40px rgba(27,29,34,.05)}
.ntable th{font-weight:400;color:var(--g3);font-size:12.5px;text-align:left;padding:16px 22px;border-bottom:1px solid var(--g1)}
.ntable td{padding:18px 22px;border-bottom:1px solid var(--line);font-size:15px;vertical-align:top}
.ntable td b{font-weight:500;display:block}.ntable td span{display:block;font-size:12.5px;color:var(--g3);margin-top:2px}
.ntable .n,.ntable th.n{text-align:right;font-variant-numeric:tabular-nums;font-size:22px;font-weight:300}
.ntable tr.nb{cursor:pointer;transition:background .25s}.ntable tr.nb:hover{background:var(--hover)}
.ntable tr:first-child.nb td{background:var(--tint)}
.work{display:none;background:#F7F7F8;font-size:13px;color:var(--g5)}
.work td{padding:14px 22px 18px}
.ntable tr.open + .work{display:table-row}
.band{margin-top:44px;background:var(--card);border-radius:22px;padding:30px 32px 26px;border:1px solid rgba(27,29,34,.05);box-shadow:0 12px 40px rgba(27,29,34,.05)}
.band svg{width:100%;height:auto;display:block}
/* upgrader */
.two{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:44px;align-items:start}
.smtable{width:100%;border-collapse:collapse;background:var(--card);border-radius:22px;overflow:hidden;box-shadow:0 12px 40px rgba(27,29,34,.05)}
.smtable th{font-weight:400;color:var(--g3);font-size:12.5px;text-align:left;padding:14px 20px;border-bottom:1px solid var(--g1)}
.smtable td{padding:12px 20px;border-bottom:1px solid var(--line);font-size:14px}.smtable .n{text-align:right;font-variant-numeric:tabular-nums}
.calc{background:var(--ink);color:#FFF;border-radius:22px;padding:30px 32px}
.calc h3{font-size:15px;font-weight:500;margin-bottom:6px}.calc .sub{font-size:13px;color:var(--ondark2);margin-bottom:22px}
.calc label{display:block;font-size:12.5px;color:var(--ondark2);margin:14px 0 6px}
.calc input[type=range]{width:100%;accent-color:var(--gold)}
.calc .val{font-size:15px;color:#FFF;font-variant-numeric:tabular-nums}
.calc .out{margin-top:24px;border-top:1px solid rgba(255,255,255,.12);padding-top:18px}
.calc .big{font-size:52px;font-weight:200;letter-spacing:-.03em;line-height:1}
.calc .fits{margin-top:10px;font-size:14px;color:var(--ondark4)}
.calc .fits b{color:var(--gold);font-weight:500}
.calc .fine{margin-top:14px;font-size:11.5px;color:var(--ondark3)}
/* evidence */
#evidence{background:var(--dark);color:var(--ondark);padding-bottom:0}
#evidence h2{color:#FFF}#evidence .lede{color:var(--ondark2)}#evidence .eyebrow{color:var(--ondark3)}
.evs{display:flex;gap:22px;overflow-x:auto;scroll-snap-type:x mandatory;padding:56px 56px 72px;scrollbar-width:none;cursor:grab}
.evs::-webkit-scrollbar{display:none}
.ev{flex:0 0 min(70vw,820px);scroll-snap-align:center}
.ev img{border-radius:18px;width:100%;box-shadow:0 20px 60px rgba(0,0,0,.45)}
.ev figcaption{margin-top:16px;font-size:15px;color:var(--ondark);line-height:1.5;max-width:720px}
.ev figcaption span{display:block;font-size:11.5px;color:var(--gold);margin-bottom:4px}
/* upside */
.grow{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:44px}
.gcard{background:var(--card);border-radius:22px;padding:30px 32px;border:1px solid rgba(27,29,34,.05);box-shadow:0 12px 40px rgba(27,29,34,.05)}
.gcard .k{font-size:12.5px;color:var(--g3)}.gcard .n{font-size:56px;font-weight:200;letter-spacing:-.03em;line-height:1;margin:8px 0}.gcard .d{font-size:14px;color:var(--g4)}
.gcard svg{width:100%;height:auto;margin-top:18px}
.tls{margin-top:56px;display:grid;grid-template-columns:repeat(6,1fr);gap:0;position:relative}
.tls::before{content:"";position:absolute;left:0;right:0;top:9px;height:1px;background:var(--g2)}
.tl{padding:0 18px 0 0;position:relative}
.tl::before{content:"";width:10px;height:10px;border-radius:50%;background:var(--ink);display:block;margin-bottom:16px;position:relative;z-index:1}
.tl:nth-child(4)::before{background:var(--e4)}
.tl .d{font-size:13px;font-weight:500}.tl .w{font-size:13px;color:var(--g4);margin-top:4px}
.steps{margin-top:44px;display:grid;grid-template-columns:repeat(5,1fr);gap:20px}
.step{background:var(--card);border-radius:22px;padding:26px 26px 24px;border:1px solid rgba(27,29,34,.05);box-shadow:0 12px 40px rgba(27,29,34,.05)}
.step .sl{font-size:12.5px;color:var(--g3);margin-bottom:10px}.step .st{font-size:15px;line-height:1.5}
.ntable .mid,.ntable th.mid{font-size:15px;font-weight:400;color:var(--g4)}
#development .mixrow{margin-top:40px}#development .mix .n{color:var(--ink)}#development .mix .l{color:var(--g4)}
@media (max-width:900px){.steps{grid-template-columns:1fr}}
.counts{display:grid;grid-template-columns:repeat(6,1fr);gap:18px;margin-top:56px;border-top:1px solid var(--g1);border-bottom:1px solid var(--g1);padding:34px 0}
.counts .n{font-size:52px;font-weight:200;letter-spacing:-.04em;line-height:1;font-variant-numeric:tabular-nums}.counts .l{color:var(--g4);margin-top:8px;font-size:13px}
.fromrow{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:40px}
.from{background:var(--card);border-radius:22px;padding:28px 30px 24px;border:1px solid rgba(27,29,34,.05);box-shadow:0 12px 40px rgba(27,29,34,.05)}
.from .k{font-size:12.5px;color:var(--g3)}.from .n{font-size:56px;font-weight:200;letter-spacing:-.04em;line-height:1.05;margin-top:6px}
.bandimg{height:78vh;min-height:520px;padding:0;overflow:hidden;background:var(--dark2);color:#FFF;display:flex;align-items:flex-end}
.bandimg .pimg{position:absolute;left:0;right:0;top:-12%;height:124%;background-size:cover;background-position:center;will-change:transform}
.bandimg .veil{position:absolute;inset:0;background:linear-gradient(180deg,rgba(var(--dark2rgb),.05) 0%,rgba(var(--dark2rgb),.2) 50%,rgba(var(--dark2rgb),.8) 100%)}
.bandimg .btxt{position:relative;z-index:2;padding:0 56px 72px}
.bandimg .eyebrow{color:rgba(255,255,255,.7)}.bandimg h2{color:#FFF;font-size:72px;max-width:none}
.gallery .g{flex:0 0 min(86vw,1180px);border-radius:30px}
@media (max-width:900px){.counts{grid-template-columns:repeat(3,1fr)}.fromrow{grid-template-columns:1fr}.bandimg h2{font-size:40px}.bandimg .btxt{padding:0 22px 44px}}
/* falsify + close */
#wrong{background:var(--card)}
#wrong ul{margin-top:26px;max-width:720px}#wrong li{list-style:none;padding:16px 0;border-top:1px solid var(--g1);font-size:17px}
#close{background:var(--dark);color:var(--ondark);padding:100px 0}
#close .by{font-size:12.5px;color:var(--ondark3)}#close .name{font-size:40px;font-weight:200;letter-spacing:-.03em;margin:8px 0 4px;color:#FFF}#close .tel{font-size:18px;color:var(--ondark4)}
#close .src{margin-top:48px;font-size:12px;color:var(--ondark3);max-width:820px;line-height:1.6}
#close .jnd{margin-top:40px;font-size:13px;color:var(--ondark2)}#close .jnd span{color:var(--gold)}
.me{margin-top:34px;max-width:620px}.mebtn{font:inherit;font-size:14px;padding:11px 18px;border-radius:999px;border:1px solid rgba(255,255,255,.25);background:var(--gold);color:var(--ink);cursor:pointer}
.mebtn.ghost{background:transparent;color:var(--ondark4)}.mebtn:hover{filter:brightness(1.08)}
#me-form{margin-top:16px;display:grid;gap:12px;max-width:420px}#me-form[hidden],#me-link[hidden],#me-open[hidden]{display:none}#me-form label{display:block;font-size:12.5px;color:var(--ondark2)}
#me-form input{display:block;width:100%;margin-top:6px;font:inherit;font-size:16px;padding:12px 14px;border-radius:12px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.06);color:#FFF}
.merow{display:flex;gap:10px}.melink{display:flex;gap:10px;margin-top:8px}.melink input{flex:1;font:inherit;font-size:14px;padding:11px 14px;border-radius:12px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.06);color:#FFF;min-width:0}
.mefine{font-size:12px;color:var(--ondark3);margin-top:10px}.mefine a{color:var(--ondark2);text-decoration:underline}
@media (max-width:900px){.melink{flex-direction:column}}
@media (max-width:900px){.wrap{padding:0 22px}section{padding:80px 0}h2{font-size:36px}#hero h1{font-size:56px}#hero .top,#hero .txt,#hero .cue{left:22px;right:22px}#hero .txt{bottom:80px}.three,.bgrid,.pairs,.two,.grow{grid-template-columns:1fr}.maps{grid-template-columns:1fr}.facts{grid-template-columns:1fr 1fr}.tls{grid-template-columns:1fr 1fr;gap:22px}.tls::before{display:none}.gallery,.evs{padding:40px 22px 56px}.gallery .g{flex-basis:88vw}#nav{display:none}.ntable .n{font-size:17px}}
@media (prefers-reduced-motion:reduce){#hero .bg{animation:none}.reveal{opacity:1;transform:none;transition:none}}

/* brand wash behind the light chapters, still, shifts with scroll */
body{position:relative}
.wash{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden}
.wash i{position:absolute;border-radius:50%;filter:blur(60px);will-change:transform}
.wash .w1{width:60vw;height:60vw;left:-18vw;top:-10vh;background:radial-gradient(circle at 50% 50%,var(--wash1),transparent 65%)}
.wash .w2{width:55vw;height:55vw;right:-16vw;top:40vh;background:radial-gradient(circle at 50% 50%,var(--wash2),transparent 65%)}
section{z-index:1}
#prog{position:fixed;left:0;top:0;height:2px;width:0;background:var(--e4);z-index:60;transition:width .15s linear}
body.dark #prog{background:var(--gold)}
#hero .hl{position:absolute;inset:0;z-index:1;pointer-events:none;background:radial-gradient(600px circle at var(--mx,50%) var(--my,50%),rgba(255,255,255,.14),transparent 60%);mix-blend-mode:soft-light;transition:background-position .2s}
#hero .bg{transition:transform .6s cubic-bezier(.2,.7,.2,1)}
.tilt{transform-style:preserve-3d;transition:transform .35s cubic-bezier(.2,.7,.2,1),box-shadow .35s}
.tilt:hover{box-shadow:0 26px 70px rgba(var(--dark2rgb),.14)}
.band:not(.in) svg line,.band:not(.in) svg circle,.band:not(.in) svg text{opacity:0}
.band.in svg line,.band.in svg circle,.band.in svg text{animation:bandin .9s cubic-bezier(.2,.7,.2,1) both}
@keyframes bandin{from{opacity:0;transform:translateX(-14px)}to{opacity:1;transform:none}}
.matrix td.hl,.matrix th.hl{background:var(--tint2)}
.ntable tr.nb.open td{background:var(--tint)}
h1,h2{-webkit-font-smoothing:antialiased}
@media (prefers-reduced-motion:reduce){.wash i,.tilt{transition:none}.band svg *{animation:none!important;opacity:1!important}}
</style>
</head>
<body>
<div class="wash"><i class="w1"></i><i class="w2"></i></div><div id="prog"></div>
<nav id="nav"></nav>

<section id="hero" data-title="Thomson Reserve">
  <div class="bg"></div><div class="veil"></div><div class="hl"></div>
  <div class="top"><div class="jnd">JND <span>Launch</span></div><div>New launch, {{DISTRICT}} · Preview <b>{{PREVIEW}}</b></div></div>
  <div class="txt">
    <div class="eyebrow">{{TAGLINE}}</div>
    <h1>Thomson<br>Reserve</h1>
    <p class="thesis">{{THESIS}}</p>
  </div>
  <div class="cue"><span>Scroll, or use the arrow keys</span><i></i></div>
</section>

<section id="development" data-title="The development">
  <div class="wrap">
    <div class="eyebrow reveal">The development</div>
    <h2 class="reveal d1"><b>1,268 homes</b> in six towers, next to Upper Thomson MRT.</h2>
    <p class="lede reveal d2">Two 30-storey towers and four 21-storey towers by UOL, Singapore Land and CapitaLand. Upper Thomson MRT at the doorstep, Ai Tong School within 1 km. Estimated vacant possession, first quarter of 2031.</p>
    <div class="counts reveal">
      <div class="c"><div class="n" data-count="1268">0</div><div class="l">homes</div></div>
      <div class="c"><div class="n" data-count="6">0</div><div class="l">towers</div></div>
      <div class="c"><div class="n" data-count="3">0</div><div class="l">clubs</div></div>
      <div class="c"><div class="n" data-count="80">0</div><div class="l">facilities</div></div>
      <div class="c"><div class="n" data-count="1014">0</div><div class="l">carpark lots</div></div>
      <div class="c"><div class="n">2031</div><div class="l">ready, 1Q</div></div>
    </div>
    <div class="facts reveal">{{FACTS}}</div>
    <div class="mixrow reveal">{{MIX}}</div>
    <div class="maps reveal"><img src="assets/pages/kit-09.jpg" alt="Site plan"><img src="assets/pages/kit-06.jpg" alt="Site overview"></div>
  </div>
</section>

<section class="bandimg" data-title="Two collections" id="band1"><div class="pimg" style="background-image:url(assets/img/towers-lawn.jpg)"></div><div class="veil"></div><div class="btxt"><div class="eyebrow">Inside the estate</div><h2>Three clubs,<br><b>80 facilities.</b></h2></div></section>

<section id="product" data-title="Inside the estate" class="darksec">
  <div class="wrap">
    <div class="eyebrow reveal">From the developer brief of 25 August</div>
    <h2 class="reveal d1">Luxury Collection and <b>Classic Collection</b>.</h2>
    <p class="lede reveal d2">Luxury Collection in the two 30-storey towers furthest from Bright Hill Drive. Classic Collection in the four 21-storey towers around the Grand Clubhouse. Smeg, Miele and Liebherr appliances.</p>
    <div class="bgrid">{{BRIEF}}</div>
  </div>
  <div class="gallery" id="gallery">{{GALLERY}}</div>
  <div class="ghint">Artist's impressions from the developer. Drag or scroll sideways.</div>
</section>

<section id="price" data-title="The price">
  <div class="wrap">
    <div class="eyebrow reveal">The price</div>
    <h2 class="reveal d1">Estimated prices, <b>from $2,550 psf</b>.</h2>
    <p class="lede reveal d2">{{PRICE_BASIS}}</p>
    <div class="fromrow reveal"><div class="from"><div class="k">2-bedroom from</div><div class="n">$1.48M</div></div><div class="from"><div class="k">3-bedroom from</div><div class="n">$2.09M</div></div><div class="from"><div class="k">4-bedroom from</div><div class="n">$2.99M</div></div></div>
    <table class="ptable matrix reveal"><thead><tr><th>Type</th>{{PRICE_HEAD}}</tr></thead><tbody>{{PRICES}}</tbody></table>
    <div class="note">For comparison, starting prices at Zyon Grand were $2.31M for a 2-bedroom, $2.76M for a 3-bedroom and $4.7M for a 4-bedroom. Promenade Peak, Arina East, Union Square and The Continuum are in the same range. ERA info kit, June 2026.</div>
    <div class="eyebrow" style="margin-top:72px">Same money, which will you buy</div>
    <div class="pairs">
      <div class="pair reveal"><span class="tag">Resale, finished 2023</span><div class="who">JadeScape, Shunfu Road</div><div class="p">$3.03M to $3.06M</div><div class="d">3-bedroom, 1,152 sqft, 16th to 20th floor, sold July and August 2026 at $2,630 to $2,650 psf. Completed 2023. Marymount MRT.</div></div>
      <div class="pair tr reveal d1"><span class="tag">Brand new, ready 2031</span><div class="who">Thomson Reserve</div><div class="p">$2.89M</div><div class="d">3-bedroom Premium + Study, 1,033 sqft, at $2,800 psf. Brand new. About $150k less.</div></div>
    </div>
    <div class="proof reveal">
      <div class="ptx">
        <div class="eyebrow">JadeScape 3-bedroom sales, URA caveats, 2026</div>
        <table class="jtx"><thead><tr><th>Sold</th><th>Floor</th><th class="n">Size</th><th>Type</th><th class="n">Price</th><th class="n">psf</th></tr></thead><tbody>{{JTX}}</tbody></table>
        <div class="note">The two 1,152 sqft sales are stack 61 of Block 16, floors 16 to 20. Source: URA Realis via the JND vault, August 2026.</div>
      </div>
      <figure class="pplan"><img src="assets/img/jadescape-c3a-plan.jpg" alt="JadeScape type C3a floor plan"><figcaption><b>JadeScape type C3a, 3-bedroom Premium.</b> 107 sqm, 1,152 sqft. Three bedrooms, two baths, yard and store. Thomson Reserve's 3-bedroom Premium + Study is 1,033 sqft. Its floor plans are released with the price list and go here when they arrive.</figcaption></figure>
    </div>
  </div>
</section>

<section class="bandimg" data-title="Which will you buy" id="band2"><div class="pimg" style="background-image:url(assets/img/pool-aerial.jpg)"></div><div class="veil"></div><div class="btxt"><div class="eyebrow">Same money</div><h2>Which will you buy?</h2></div></section>

<section id="neighbours" data-title="The neighbours">
  <div class="wrap">
    <div class="eyebrow reveal">The resale market next door</div>
    <h2 class="reveal d1">What the condos next door would cost <b>brand new</b>.</h2>
    <p class="lede reveal d2">The age gap method. A condo loses about $50 psf a year as it ages. Take what the neighbour sells for today, add $50 psf for every year it will be older than Thomson Reserve in 2031, then add 6% for harmonised floor area. Tap a row to see the sum.</p>
    <table class="ntable reveal"><thead><tr><th>Project</th><th>Sells for today, URA caveats</th><th class="n mid">Older than TR by 2031</th><th class="n">Brand-new price</th></tr></thead><tbody>{{NEIGH}}</tbody></table>
    <div class="band reveal" id="band"></div>
    <div class="note">Caveats from URA via the JND vault, latest August 2026. Thomson Reserve ready 1Q 2031. JadeScape first because it is the last big launch on this line to go through launch, completion and resale.</div>
  </div>
</section>

<section id="upgrader" data-title="Firepower">
  <div class="wrap">
    <div class="eyebrow reveal">The buyer next door</div>
    <h2 class="reveal d1">4 and 5-room flats around here sell for <b>$600k to $1.6M</b>.</h2>
    <p class="lede reveal d2">Bishan Street 22 and 24, Ang Mo Kio Street 21 and 23, Sin Ming and Shunfu. Sold in the last six months. Move the sliders on the right to see what a sale carries.</p>
    <div class="two">
      <table class="smtable reveal"><thead><tr><th>Block</th><th>Flat</th><th>Sold</th><th class="n">Price</th></tr></thead><tbody>{{SINMING}}</tbody></table>
      <div class="calc reveal d1">
        <h3>Firepower</h3><div class="sub">Sale price, less the loan, legal fees and commission, divided by 0.29.</div>
        <label>Flat sells for <span class="val" id="v-sale"></span></label><input type="range" id="i-sale" min="700000" max="1700000" step="10000" value="1000000">
        <label>Outstanding loan <span class="val" id="v-loan"></span></label><input type="range" id="i-loan" min="0" max="800000" step="10000" value="150000">
        <div class="out"><div class="sub" style="margin:0 0 6px">Carries a purchase up to</div><div class="big" id="v-max"></div><div class="fits" id="v-fits"></div><div class="fine">Assumes 2% commission and $3,000 legal fees. The 0.29 covers the 25% downpayment and stamp duties. Indicative, confirm with a banker.</div></div>
      </div>
    </div>
  </div>
</section>

<section class="bandimg" data-title="Sell high, buy low" id="band3"><div class="pimg" style="background-image:url(assets/img/wellness-pavilion.jpg)"></div><div class="veil"></div><div class="btxt"><div class="eyebrow">The bigger story</div><h2>Sell high, buy low.</h2></div></section>

<section id="evidence" data-title="The bigger story">
  <div class="wrap">
    <div class="eyebrow reveal">The bigger story, in the slides the team has been using all year</div>
    <h2 class="reveal d1">Sell high, buy low.</h2>
    <p class="lede reveal d2">From the JND Thomson Reserve client deck, August 2026. Drag sideways.</p>
  </div>
  <div class="evs" id="evs">{{EVIDENCE}}</div>
</section>

<section id="close" data-title="Presented by">
  <div class="wrap">
    <div class="by">Presented by</div>
    <div class="name" id="agent-name">Justin Ngai</div>
    <div class="tel" id="agent-tel">+65 9661 5511 · ERA Realty Network</div>
    <div class="me" id="me">
      <button type="button" class="mebtn" id="me-open">Present as me</button>
      <form id="me-form" hidden>
        <label>Your name<input type="text" id="me-name" autocomplete="name" placeholder="Name as clients know you" required></label>
        <label>Mobile<input type="tel" id="me-tel" autocomplete="tel" placeholder="+65 9xxx xxxx" required></label>
        <div class="merow"><button type="submit" class="mebtn">Save</button><button type="button" class="mebtn ghost" id="me-cancel">Cancel</button></div>
      </form>
      <div id="me-link" hidden><div class="by">Your link, send this to clients</div><div class="melink"><input type="text" id="me-url" readonly><button type="button" class="mebtn" id="me-copy">Copy</button></div><div class="mefine">Saved on this device. Open your link on any device and it presents as you. <a href="#" id="me-edit">Change</a></div></div>
    </div>
    <div class="src"><b style="color:#9EA2AA;font-weight:500">Sources.</b> {{SOURCES}}</div>
    <div class="jnd">JND <span>Launch</span> · Preview {{PREVIEW}} · All information subject to change without notice. Estimated prices are not the developer's and are for comparison only.</div>
  </div>
</section>

<script>
(function(){
  // chapters
  var secs=[].slice.call(document.querySelectorAll('section[data-title]')), nav=document.getElementById('nav');
  secs.forEach(function(s){ var a=document.createElement('a'); a.href='#'+s.id; a.innerHTML='<span>'+s.dataset.title+'</span>'; nav.appendChild(a); });
  var links=[].slice.call(nav.children);
  function cur(){ var y=window.scrollY+window.innerHeight*0.45, i=0; secs.forEach(function(s,k){ if(s.offsetTop<=y) i=k; }); return i; }
  function sync(){ var i=cur(); links.forEach(function(a,k){ a.classList.toggle('on',k===i); }); document.body.classList.toggle('dark', secs[i].id==='hero'||secs[i].classList.contains('darksec')||secs[i].classList.contains('bandimg')||secs[i].id==='evidence'||secs[i].id==='close'); }
  window.addEventListener('scroll',sync,{passive:true}); sync();
  document.addEventListener('keydown',function(e){ if(e.target.tagName==='INPUT') return; var i=cur(); if(e.key==='ArrowDown'||e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'){ e.preventDefault(); if(secs[i+1]) secs[i+1].scrollIntoView({behavior:'smooth'}); } if(e.key==='ArrowUp'||e.key==='ArrowLeft'||e.key==='PageUp'){ e.preventDefault(); if(secs[i-1]) secs[i-1].scrollIntoView({behavior:'smooth'}); } });
  // reveal (a deep link or a print shows everything at once)
  if(location.hash||matchMedia('print').matches){ document.querySelectorAll('.reveal').forEach(function(el){ el.classList.add('in'); }); }
  try{ var io=new IntersectionObserver(function(es){ es.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target);} }); },{rootMargin:'0px 0px -10% 0px'}); document.querySelectorAll('.reveal').forEach(function(el){ io.observe(el); }); }catch(err){ document.querySelectorAll('.reveal').forEach(function(el){ el.classList.add('in'); }); }
  // numbers count up when they arrive
  try{ var cio=new IntersectionObserver(function(es){ es.forEach(function(e){ if(!e.isIntersecting) return; cio.unobserve(e.target); var el=e.target, to=+el.dataset.count, t0=performance.now(); (function tick(now){ var p=Math.min(1,(now-t0)/1400), v=Math.round(to*(1-Math.pow(1-p,3))); el.textContent=v.toLocaleString(); if(p<1) requestAnimationFrame(tick); })(t0); }); },{threshold:.4}); document.querySelectorAll('[data-count]').forEach(function(el){ cio.observe(el); }); }catch(err){ document.querySelectorAll('[data-count]').forEach(function(el){ el.textContent=(+el.dataset.count).toLocaleString(); }); }
  // full-bleed bands drift as you pass them
  var bands=[].slice.call(document.querySelectorAll('.bandimg .pimg'));
  function par(){ var vh=window.innerHeight; bands.forEach(function(p){ var r=p.parentElement.getBoundingClientRect(); if(r.bottom<0||r.top>vh) return; var k=(r.top+r.height/2-vh/2)/vh; p.style.transform='translateY('+(k*-60)+'px)'; }); }
  window.addEventListener('scroll',par,{passive:true}); par();
  // the gallery turns its own pages while it is on screen
  (function(){ var g=document.getElementById('gallery'); if(!g) return; var vis=false, hold=0; try{ new IntersectionObserver(function(es){ vis=es[0].isIntersecting; },{threshold:.5}).observe(g); }catch(e){}
    g.addEventListener('pointerdown',function(){ hold=Date.now()+15000; }); g.addEventListener('wheel',function(){ hold=Date.now()+15000; },{passive:true});
    setInterval(function(){ if(!vis||Date.now()<hold||document.hidden) return; var w=g.firstElementChild.getBoundingClientRect().width+18; var next=g.scrollLeft+w; if(next>g.scrollWidth-g.clientWidth-10) next=0; g.scrollTo({left:next,behavior:'smooth'}); },5000); })();
  // drag to scroll the galleries
  ['gallery','evs'].forEach(function(id){ var el=document.getElementById(id); if(!el) return; var down=false,sx=0,sl=0; el.addEventListener('mousedown',function(e){ down=true; sx=e.pageX; sl=el.scrollLeft; el.style.scrollSnapType='none'; }); window.addEventListener('mouseup',function(){ if(down){ down=false; el.style.scrollSnapType=''; } }); el.addEventListener('mousemove',function(e){ if(!down) return; el.scrollLeft=sl-(e.pageX-sx); }); });
  // neighbours: the working, on tap
  document.querySelectorAll('tr.nb').forEach(function(tr){
    var psf=+tr.dataset.psf, top=+tr.dataset.top, yrs=2031-top, b1=psf+yrs*50, b2=b1*1.06;
    var w=document.createElement('tr'); w.className='work'; w.innerHTML='<td colspan="4">Sells for $'+psf.toLocaleString()+' psf today. By 2031 it is '+yrs+' years older than Thomson Reserve, and '+yrs+' × $50 = $'+(yrs*50).toLocaleString()+' psf comes back. $'+Math.round(b1).toLocaleString()+', plus 6% for harmonised floor area, is $'+Math.round(b2).toLocaleString()+' psf brand new. Thomson Reserve asks $2,800.</td>';
    tr.parentNode.insertBefore(w, tr.nextSibling);
    tr.addEventListener('click',function(){ tr.classList.toggle('open'); });
  });
  // convergence band
  (function(){ var box=document.getElementById('band'); var cs=getComputedStyle(document.documentElement), C={}; ['g1','g2','g3','g5','card','ink','e4'].forEach(function(k){ C[k]=cs.getPropertyValue('--'+k).trim(); }); var rows=[].slice.call(document.querySelectorAll('tr.nb')).map(function(tr){ return {name:tr.querySelector('b').textContent, a:+tr.dataset.psf, b:+tr.dataset.asnew}; });
    var lo=1800, hi=3600, W=1100, L=170, X=function(v){ return L+(v-lo)/(hi-lo)*(W-L-40); };
    var s='<svg viewBox="0 0 '+W+' '+(90+rows.length*44)+'">';
    [2000,2200,2400,2600,2800,3000,3200,3400].forEach(function(v){ s+='<line x1="'+X(v)+'" y1="34" x2="'+X(v)+'" y2="'+(60+rows.length*44)+'" stroke="'+C.g1+'"/><text x="'+X(v)+'" y="'+(78+rows.length*44)+'" font-size="11" fill="'+C.g3+'" text-anchor="middle">$'+v.toLocaleString()+'</text>'; });
    rows.forEach(function(r,i){ var y=64+i*44; s+='<text x="'+(L-16)+'" y="'+(y+4)+'" font-size="12.5" fill="'+C.g5+'" text-anchor="end">'+r.name+'</text><line x1="'+X(r.a)+'" y1="'+y+'" x2="'+X(r.b)+'" y2="'+y+'" stroke="'+C.g2+'" stroke-width="2"/><circle cx="'+X(r.a)+'" cy="'+y+'" r="5" fill="'+C.card+'" stroke="'+C.ink+'" stroke-width="1.5"/><circle cx="'+X(r.b)+'" cy="'+y+'" r="6" fill="'+C.ink+'"/><text x="'+(X(r.b)+12)+'" y="'+(y+4)+'" font-size="11.5" fill="'+C.ink+'">$'+r.b.toLocaleString()+' brand new</text><text x="'+(X(r.a)-10)+'" y="'+(y+4)+'" font-size="11" fill="'+C.g3+'" text-anchor="end">$'+r.a.toLocaleString()+' today</text>'; });
    var t0=X(2800), yb=50+rows.length*44; s+='<line x1="'+t0+'" y1="34" x2="'+t0+'" y2="'+(yb-10)+'" stroke="'+C.e4+'" stroke-width="2"/><text x="'+t0+'" y="22" font-size="11.5" fill="'+C.e4+'" text-anchor="middle" font-weight="500">Thomson Reserve, $2,800 brand new</text></svg>';
    box.innerHTML='<div class="eyebrow" style="margin-bottom:10px">Each neighbour: what it sells for today, and its brand-new price by the age gap method, against Thomson Reserve at $2,800</div>'+s; })();
  // firepower
  var prices=PRICES;
  function fp(){ var sale=+document.getElementById('i-sale').value, loan=+document.getElementById('i-loan').value; var net=sale-loan-sale*0.02-3000; var max=net>0?net/0.29:0;
    document.getElementById('v-sale').textContent='$'+sale.toLocaleString(); document.getElementById('v-loan').textContent='$'+loan.toLocaleString(); document.getElementById('v-max').textContent='$'+(max/1e6).toFixed(2)+'M';
    var fits=prices.filter(function(p){ return p[2]<=max; }); var best=fits.length?fits[fits.length-1]:null;
    document.getElementById('v-fits').innerHTML= best ? 'Reaches a <b>'+best[0]+'</b>, '+best[1].toLocaleString()+' sqft, $'+(best[2]/1e6).toFixed(2)+'M at $2,800 psf'+(fits.length>1?', and everything below it.':'.') : 'Below the 2-bedroom entry at this loan. Try a smaller loan.'; }
  ['i-sale','i-loan'].forEach(function(id){ document.getElementById(id).addEventListener('input',fp); }); fp();
  // progress bar + brand wash drift + hero pointer light
  (function(){ var prog=document.getElementById('prog'), ws=[].slice.call(document.querySelectorAll('.wash i')), hero=document.getElementById('hero'), bg=hero.querySelector('.bg'), hl=hero.querySelector('.hl');
    function onScroll(){ var h=document.documentElement, p=h.scrollTop/(h.scrollHeight-h.clientHeight||1); prog.style.width=(p*100)+'%'; ws.forEach(function(w,i){ w.style.transform='translateY('+(-h.scrollTop*(i?0.06:0.1))+'px)'; }); }
    window.addEventListener('scroll',onScroll,{passive:true}); onScroll();
    if(matchMedia('(pointer:fine)').matches && !matchMedia('(prefers-reduced-motion:reduce)').matches){
      hero.addEventListener('mousemove',function(e){ var r=hero.getBoundingClientRect(), x=(e.clientX-r.left)/r.width, y=(e.clientY-r.top)/r.height; hl.style.setProperty('--mx',(x*100)+'%'); hl.style.setProperty('--my',(y*100)+'%'); bg.style.transform='scale(1.08) translate('+((x-.5)*-16)+'px,'+((y-.5)*-10)+'px)'; });
      hero.addEventListener('mouseleave',function(){ bg.style.transform=''; });
      // cards tilt toward the pointer
      [].slice.call(document.querySelectorAll('.stat,.from,.pair,.bcard,.gcard,.pplan,.plan,.calc')).forEach(function(c){ c.classList.add('tilt');
        c.addEventListener('mousemove',function(e){ var r=c.getBoundingClientRect(), x=(e.clientX-r.left)/r.width-.5, y=(e.clientY-r.top)/r.height-.5; c.style.transform='perspective(900px) rotateX('+(-y*4)+'deg) rotateY('+(x*5)+'deg) translateY(-2px)'; });
        c.addEventListener('mouseleave',function(){ c.style.transform=''; }); });
    }
    // the band chart draws itself in when it arrives
    var band=document.getElementById('band'); if(band){ try{ new IntersectionObserver(function(es){ if(!es[0].isIntersecting) return; var els=band.querySelectorAll('svg line,svg circle,svg text'); [].forEach.call(els,function(el,i){ el.style.animationDelay=(Math.min(i,60)*22)+'ms'; }); band.classList.add('in'); },{threshold:.3}).observe(band); }catch(e){ band.classList.add('in'); } }
    // price matrix: hover lights the whole psf column
    var mx=document.querySelector('.matrix'); if(mx){ mx.addEventListener('mouseover',function(e){ var td=e.target.closest('td,th'); if(!td||td.cellIndex<2) return; var i=td.cellIndex; mx.querySelectorAll('.hl').forEach(function(x){ x.classList.remove('hl'); }); mx.querySelectorAll('tr').forEach(function(tr){ var c=tr.children[i]; if(c) c.classList.add('hl'); }); }); mx.addEventListener('mouseleave',function(){ mx.querySelectorAll('.hl').forEach(function(x){ x.classList.remove('hl'); }); }); }
  })();
  // presenter: from the link (?agent=Name&tel=+65...) or saved on this device via "Present as me"
  (function(){
    var $=function(id){ return document.getElementById(id); };
    var q=new URLSearchParams(location.search), saved=null;
    try{ saved=JSON.parse(localStorage.getItem('jnd_agent')||'null'); }catch(e){}
    var me=q.get('agent')?{name:q.get('agent'),tel:q.get('tel')||''}:saved;
    function link(a){ return location.origin+location.pathname+'?agent='+encodeURIComponent(a.name)+(a.tel?'&tel='+encodeURIComponent(a.tel):''); }
    function apply(a){ if(!a||!a.name) return; $('agent-name').textContent=a.name; $('agent-tel').textContent=(a.tel||'')+(a.tel?' · ':'')+'ERA Realty Network'; }
    function showLink(a){ $('me-url').value=link(a); $('me-link').hidden=false; $('me-open').hidden=true; $('me-form').hidden=true; }
    apply(me); if(saved&&saved.name) showLink(saved);
    $('me-open').addEventListener('click',function(){ $('me-form').hidden=false; $('me-open').hidden=true; if(me){ $('me-name').value=me.name||''; $('me-tel').value=me.tel||''; } $('me-name').focus(); });
    $('me-cancel').addEventListener('click',function(){ $('me-form').hidden=true; if(saved&&saved.name) $('me-link').hidden=false; else $('me-open').hidden=false; });
    $('me-edit').addEventListener('click',function(e){ e.preventDefault(); $('me-link').hidden=true; $('me-form').hidden=false; $('me-name').value=saved.name; $('me-tel').value=saved.tel||''; });
    $('me-form').addEventListener('submit',function(e){ e.preventDefault(); var a={name:$('me-name').value.trim(),tel:$('me-tel').value.trim()}; if(!a.name) return; try{ localStorage.setItem('jnd_agent',JSON.stringify(a)); }catch(err){} saved=a; me=a; apply(a); showLink(a); });
    $('me-copy').addEventListener('click',function(){ var u=$('me-url'); u.select(); u.setSelectionRange(0,999); var done=function(){ $('me-copy').textContent='Copied'; setTimeout(function(){ $('me-copy').textContent='Copy'; },1800); }; if(navigator.clipboard){ navigator.clipboard.writeText(u.value).then(done,function(){ document.execCommand('copy'); done(); }); } else { document.execCommand('copy'); done(); } });
  })();
})();
</script>
</body>
</html>'''
out = HTML
for k, v in {"{{DISTRICT}}": esc(D["district"]), "{{PREVIEW}}": esc(D["preview"]), "{{TAGLINE}}": esc(D["tagline"]), "{{THESIS}}": esc(D["thesis"]), "{{FACTS}}": facts_html,
             "{{MIX}}": mix_html, "{{BRIEF}}": brief_html, "{{GALLERY}}": gallery_html, "{{PRICE_BASIS}}": esc(D["price_basis"]), "{{PRICES}}": price_rows, "{{PRICE_HEAD}}": price_head, "{{NEIGH}}": neigh_rows,
             "{{SINMING}}": sinming_rows, "{{EVIDENCE}}": evidence_html, "{{TIMELINE}}": timeline_html, "{{FALSIFY}}": falsify_html, "{{SOURCES}}": esc(D["sources"]), "{{UPSIDE}}": upside_html, "{{JTX}}": jtx_rows}.items():
    out = out.replace(k, v)
T = D["theme"]; _rgb = lambda h: ",".join(str(int(h.lstrip("#")[i:i+2], 16)) for i in (0, 2, 4))
out = out.replace("{{THEMEVARS}}", "{" + "".join("--%s:%s;" % (k, v) for k, v in T.items() if k not in ("display", "h1", "fonts", "concept")) + "--dark2rgb:%s;--font-display:'%s','Avenir Next','Helvetica Neue',Arial,sans-serif;--font-h1:'%s','Avenir Next','Helvetica Neue',Arial,sans-serif;--font-body:'Outfit','Avenir Next','Helvetica Neue',Arial,sans-serif;--ok:#3E7C59;" % (_rgb(T["dark2"]), T["display"], T["h1"]) + "}").replace("{{FONTS}}", T["fonts"])
out = out.replace("var prices=PRICES;", "var prices=" + json.dumps([[p[0], p[1], p[2]] for p in D["prices"]]) + ";")
open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(out)
print("built", len(out), "bytes")
