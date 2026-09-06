#!/usr/bin/env python3
"""Apply the OS look to index-live-auto.html in place. Idempotent: run it after any regeneration
that rebuilds the file from an older template. Presentation only; no data, no logic."""
import re, sys
P = "index-live-auto.html"
s = open(P, encoding="utf-8").read()
if "theme-os-toolkit.css" in s and 'id="os-headline"' in s:
    print("already applied"); sys.exit(0)
if "theme-os-toolkit.css" not in s:
    s = s.replace("</head>", '<link rel="stylesheet" href="theme-os-toolkit.css">\n</head>', 1)
s = s.replace("<h1>JND <span>Tools</span> Dashboard</h1>", "<h1>JND <span>Toolkit</span></h1>", 1)
a = '''  <div class="sec">📍 Recent Transactions — near a location</div>
  <div class="card" style="padding:14px 16px">'''
b = '''  <div class="os-hero">
    <div class="os-eyebrow" id="os-eyebrow">From the papers</div>
    <h1 class="os-line" id="os-headline" title="Open the article">Singapore property, in the news today.</h1>
    <div class="os-hmeta" id="os-hmeta"></div>
    <p class="os-sub">See what has sold around you. Private caveats from URA, three years. HDB resales, twelve months. Ranked by distance from where you stand. Your location stays on this device.</p>
  <div class="card os-nm" style="padding:14px 16px">'''
assert a in s, "near-me block not found"
s = s.replace(a, b, 1)
a = '''  </div>
  <div class="kpis">'''
assert a in s
s = s.replace(a, '''  </div>
  </div>
  <div class="kpis">''', 1)
s = s.replace('📍 Use my current location', 'Use my location', 1)
s = s.replace('placeholder="block · road · project"', 'placeholder="or a block, road or project"', 1)
s = s.replace("project\\u2019s nearest block", "project’s nearest block")
js = '''<div class="sky"><i class="a"></i><i class="b"></i><i class="c"></i><div class="grain"></div></div>
<script>
(function(){ // the hero headline: the day's property news, one at a time, a new one every three hours
  var el=document.getElementById('os-headline'), meta=document.getElementById('os-hmeta'), eye=document.getElementById('os-eyebrow'); if(!el) return;
  var items=[], cur=-1, manual=0;
  var paper={ST:'The Straits Times',BT:'The Business Times',ZB:'Lianhe Zaobao',EdgeProp:'EdgeProp'};
  function pick(){ return items.length ? (Math.floor(Date.now()/(3*3600*1000)) + manual) % items.length : -1; }
  function show(i, instant){ if(i<0||i===cur) return; cur=i; var it=items[i];
    var go=function(){ el.textContent=it.h; el.style.cursor=it.link?'pointer':'default';
      meta.innerHTML=[paper[it.src]||it.src, it.date, it.topic].filter(Boolean).join(' · ')+(it.link?' · <a class="os-read" href="'+it.link+'" target="_blank" rel="noopener">Read the article ↗</a>':'')+' · <a class="os-next" onclick="return osNextHeadline()">Next story ›</a>'; };
    if(instant){ go(); return; }
    el.classList.add('fade'); meta.classList.add('fade'); setTimeout(function(){ go(); el.classList.remove('fade'); meta.classList.remove('fade'); }, 420); }
  el.addEventListener('click', function(){ var it=items[cur]; if(it&&it.link) window.open(it.link,'_blank','noopener'); });
  window.osNextHeadline=function(){ if(!items.length) return false; manual++; show(pick()); return false; };
  fetch('headlines.json',{cache:'no-store'}).then(function(r){return r.json();}).then(function(j){
    items=(j.items||[]).filter(function(x){return x.h;}); if(!items.length) return;
    eye.textContent='From the papers, '+(items.length)+' stories this week'; show(pick(), true);
    setInterval(function(){ show(pick()); }, 60000);
  }).catch(function(){});
})();
(function(){ // JND Toolkit, the OS look: lights answer the scroll, sections ease in, no motion on its own
  var L=[document.querySelector('.sky .a'),document.querySelector('.sky .b'),document.querySelector('.sky .c')]; var cur=0,target=0,raf=null;
  function frame(){ cur+=(target-cur)*.08; var y=cur;
    L[0].style.transform='translate('+(y*.10)+'px,'+(-y*.16)+'px) scale('+(1+Math.min(.25,y/6000))+')';
    L[1].style.transform='translate('+(-y*.12)+'px,'+(-y*.05)+'px)';
    L[2].style.transform='translate('+(y*.04)+'px,'+(-y*.22)+'px)';
    if(Math.abs(target-cur)>.5) raf=requestAnimationFrame(frame); else raf=null; }
  window.addEventListener('scroll',function(){ target=window.scrollY||0; if(!raf) raf=requestAnimationFrame(frame); },{passive:true});
  try{ var io=new IntersectionObserver(function(es){ es.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target);} }); },{rootMargin:'0px 0px -8% 0px'});
    document.querySelectorAll('#tool-mp .kpis, #tool-mp .sec, #tool-mp .cards3 > .card').forEach(function(el){ if(el.getBoundingClientRect().top>window.innerHeight){ el.classList.add('reveal'); io.observe(el);} }); }catch(e){}
  document.querySelectorAll('#tool-mp .sec > h2, .app-tabs button').forEach(function(x){ var t=x.firstChild; while(t&&t.nodeType!==3) t=t.nextSibling; if(t) t.textContent=t.textContent.replace(/^[^A-Za-z0-9]+/,''); });
})();
</script>
</body>'''
assert s.count("</body>") == 1
s = s.replace("</body>", js, 1)
open(P, "w", encoding="utf-8").write(s)
print("applied")
