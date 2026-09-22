/* JND Toolkit — deterministic Singapore sun study. No inferred height for missing data. */
'use strict';
const $=id=>document.getElementById(id),home=[103.8320123,1.3039812],empty=()=>({type:'FeatureCollection',features:[]}),collection=features=>({type:'FeatureCollection',features});
let map,center=home.slice(),features=[],study=null,shadowStudy=null,selected=null,loadId=0,revision=0,sceneEpoch=0,workerScene=-1,inFlight=null,ready=false,loading=false,playing=false,showShadows=true,estimates=true,workerBusy=false,pending=null,completed=null,notice='',loadError='',release='',coverageCounts=null,maximumHeight=0,includeFuture=true,futureCatalog=[],loadedViewport=null,requestedViewport=null,overview=false,edgeClipped=false,panTimer=null;
let shadowCanvas=null,shadowContext=null,canvasBoundsKey='',groundShadowLayer=null;
const heightEdits=new Map(),buildingWorker=new Worker('building-worker.js?v=28'),shadowWorker=new Worker('shadow-worker.js?v=28');
fetch('data/future-projects.json?v=28',{cache:'no-cache'}).then(r=>r.json()).then(d=>{futureCatalog=d.projects;renderFutureProjects();searchControl.refresh();}).catch(()=>{$('future-status').textContent='Future-project catalogue unavailable.';});
let places=[];fetch('data/places.json?v=28').then(r=>r.json()).then(x=>{places=x;searchControl.refresh();}).catch(()=>{});
const today=()=>new Date(Date.now()+8*3600000).toISOString().slice(0,10);
$('date').value=today();$('date').min='2000-01-01';$('date').max='2100-12-31';
const moment=()=>SolarEngine.instant($('date').value,Number($('time').value));
const sun=(date=moment())=>SolarEngine.position(date,center[1],center[0]);
const clock=d=>d?d.toLocaleTimeString('en-SG',{timeZone:'Asia/Singapore',hour:'numeric',minute:'2-digit',hour12:true}).toUpperCase():'—';
function counts(){if(coverageCounts)return coverageCounts;const local=features.filter(f=>f.properties.quality!=='outline'&&study&&SolarGeometry.intersects(SolarGeometry.bbox(f.geometry),study));return coverageCounts={total:local.length,recorded:local.filter(f=>f.properties.quality==='tagged').length,estimated:local.filter(f=>f.properties.quality==='derived').length,landed:local.filter(f=>f.properties.landedFlat).length,missing:local.filter(f=>f.properties.quality==='unknown').length,future:local.filter(f=>f.properties.future).length,manual:local.filter(f=>f.properties.quality==='manual').length};}
function status(){const c=counts();$('status').textContent=loading?'Updating buildings for this view…':overview?'Pan across Singapore. Zoom in to see buildings and shadows.':loadError||`${c.total.toLocaleString()} footprints in view${c.future?' · '+c.future+' future building sections':''} · ${c.recorded} recorded heights · ${c.estimated} estimated${estimates?'':' (excluded)'}${c.landed?' · '+c.landed+' landed footprints (flat)':''}${c.manual?' · '+c.manual+' user-entered':''} · ${c.missing} missing.`;$('quality-note').textContent=notice||'Missing heights cast no shadow. Clear ground does not confirm sunlight.';document.body.dataset.loading=String(loading);}
function stop(){playing=false;clearTimeout(stop.timer);$('play').textContent='▶';$('play').setAttribute('aria-label','Play the day');}
function nextFrame(){if(!playing)return;stop.timer=setTimeout(()=>{if(!playing)return;const m=Number($('time').value)+10;if(m>1200){stop();return;}$('time').value=m;update();},120);}
function repaintShadowCanvas(){groundShadowLayer?.update();}
function clearShadows(){if(shadowContext){shadowContext.clearRect(0,0,2048,2048);repaintShadowCanvas();}++sceneEpoch;completed=null;pending=null;map?.getSource('shadow-data')?.setData(empty());}
function renderBuildings(){if(!ready)return;coverageCounts=null;maximumHeight=features.reduce((max,f)=>(estimates||f.properties.quality!=='derived')?Math.max(max,f.properties.height||0):max,0);clearShadows();const shown=features.map(f=>({...f,properties:{...f.properties,renderHeight:f.properties.height&&(estimates||f.properties.quality!=='derived')?f.properties.height:0}}));map.getSource('building-data').setData(collection(shown));}
function scheduleShadows(s){const id=++revision;pending=null;
 if(!ready||loading||!shadowStudy||loadError||overview){notice=overview?'Singapore overview · Zoom in for building shadows.':loadError?'Study unavailable. Retry loading this area.':edgeClipped&&!shadowStudy?'Shadows unavailable at this dataset boundary.':'Preparing building data…';status();return;}
 const minimum=Math.max(5,Math.atan(maximumHeight/2200)*180/Math.PI);
 if(!showShadows||s.altitude<minimum){clearShadows();renderReadout();notice=!showShadows?'Shadows switched off.':s.altitude<=0?'Sun below the horizon.':`Shadows hidden below ${minimum.toFixed(1)}° altitude to keep the study within its data buffer.`;status();nextFrame();return;}
 notice=completed?'Showing '+clock(SolarEngine.instant(completed.date,completed.minutes))+' shadows · Updating to '+clock(moment())+'…':'Calculating shadows for '+clock(moment())+'…';status();pending={id,epoch:sceneEpoch,date:$('date').value,minutes:Number($('time').value),features,altitude:s.altitude,bearing:s.bearing,bounds:shadowStudy,estimates,raster:Boolean(shadowContext)};dispatch();
}
function dispatch(){if(workerBusy||!pending)return;workerBusy=true;inFlight=pending;pending=null;const payload={...inFlight};if(workerScene===inFlight.epoch)delete payload.features;else workerScene=inFlight.epoch;shadowWorker.postMessage(payload);}
shadowWorker.onmessage=({data})=>{
 const frame=inFlight;
 if(!frame||data.id!==frame.id){data.bitmap?.close();return;}
 workerBusy=false;inFlight=null;
 // A newer slider position replaces the queued request, not a valid completed frame.
 // Only changes to geometry/date/visibility invalidate the in-flight scene.
 if(frame.epoch===sceneEpoch){
  if(data.error){console.error('Shadow calculation failed:',data.error);clearShadows();renderReadout();notice='Shadow calculation failed. Change time or reload the area.';stop();}
  else{
   if(data.bitmap){
    shadowContext.clearRect(0,0,2048,2048);shadowContext.drawImage(data.bitmap,0,0);data.bitmap.close();
    const b=frame.bounds,key=b.join(',');if(key!==canvasBoundsKey){canvasBoundsKey=key;groundShadowLayer.update(b);}
    repaintShadowCanvas();map.getSource('shadow-data').setData(empty());
   }else{if(shadowContext){shadowContext.clearRect(0,0,2048,2048);repaintShadowCanvas();}
    map.getSource('shadow-data').setData(collection(data.coordinates.length?[{type:'Feature',properties:{},geometry:{type:'MultiPolygon',coordinates:data.coordinates}}]:[]));}

   completed={date:frame.date,minutes:frame.minutes,elapsed:data.elapsed,polygons:data.polygons??data.coordinates.length};
   if(scrubPointer!==null)scrubStats.frames++;reportScrub();
   renderReadout(frame.date,frame.minutes);
   notice=pending?'Showing '+clock(SolarEngine.instant(frame.date,frame.minutes))+' shadows · Updating to '+clock(moment())+'…':'Ground-shadow estimate · '+clock(SolarEngine.instant(frame.date,frame.minutes))+' · Auto-updates as you pan. Missing heights cast no shadow.';
   if(edgeClipped)notice+=' Coverage ends at the dashed boundary.';
   if(!pending)nextFrame();
  }
  status();
 }else data.bitmap?.close();
 dispatch();
};
shadowWorker.onerror=()=>{workerBusy=false;inFlight=null;pending=null;clearShadows();notice='Shadow engine unavailable. Reload the page to retry.';stop();status();};
let chartKey='',pathKey='',pathStops=[],currentSunMarker=null,showSunPath=true;
function renderSunPath(){
 if(!ready)return;
 const visible=showSunPath&&!overview&&SolarEngine.validDate($('date').value),source=map.getSource('sun-path');
 if(!visible){source.setData(empty());for(const p of pathStops)p.marker.remove();pathStops=[];currentSunMarker?.remove();currentSunMarker=null;pathKey='';return;}
 const radius=Math.max(65,Math.min(340,260*2**(16.1-map.getZoom()))),day=$('date').value,key=day+':'+center.join(',')+':'+radius.toFixed(0);
 if(pathKey!==key){
  pathKey=key;const path=SunPath.day(day,center,radius);
  source.setData(collection(path.line.length?[{type:'Feature',properties:{},geometry:{type:'LineString',coordinates:path.line}}]:[]));
  for(const p of pathStops)p.marker.remove();
  pathStops=path.stops.map(p=>{const el=document.createElement('button');el.className='sun-path-stop';el.textContent=p.label;el.type='button';el.title=clock(SolarEngine.instant(day,p.minute))+' · Click to set study time';el.setAttribute('aria-label',p.label+', '+clock(SolarEngine.instant(day,p.minute))+', set study time');el.onclick=e=>{e.stopPropagation();stop();$('time').value=p.minute;update();};const marker=new maplibregl.Marker({element:el,anchor:'top',offset:[0,9]}).setLngLat(p.coordinate).addTo(map);return{...p,el,marker};});
 }
 const minute=Number($('time').value),s=sun();for(const p of pathStops)p.el.setAttribute('aria-pressed',p.minute===minute);
 if(s.altitude<=0&&(!pathStops.length||minute<pathStops[0].minute||minute>pathStops.at(-1).minute)){currentSunMarker?.remove();currentSunMarker=null;return;}
 if(!currentSunMarker){const el=document.createElement('div');el.className='sun-path-current';const icon=document.createElement('span');icon.className='sun-icon';icon.textContent='☀';const label=document.createElement('span');el.append(icon);el.append(label);currentSunMarker=new maplibregl.Marker({element:el,anchor:'bottom',offset:[0,-5]}).setLngLat(center).addTo(map);currentSunMarker.label=label;}
 currentSunMarker.label.textContent=clock(moment());currentSunMarker.setLngLat(SunPath.point(center,s.bearing,radius));
}
$('sun-path-toggle').onclick=()=>{showSunPath=!showSunPath;$('sun-path-toggle').textContent=showSunPath?'Sun path on':'Sun path off';$('sun-path-toggle').setAttribute('aria-pressed',showSunPath);renderSunPath();};
function update(){if(!SolarEngine.validDate($('date').value)){stop();$('date').setCustomValidity('Choose a real date from 2000 to 2100.');$('date').reportValidity();++revision;clearShadows();renderSunPath();notice='Choose a valid study date.';status();return;}$('date').setCustomValidity('');
 if((completed&&completed.date!==$('date').value)||(inFlight?.epoch===sceneEpoch&&inFlight.date!==$('date').value))clearShadows();if(!completed)renderReadout();renderSunPath();scheduleShadows(sun());
}
function renderReadout(day=$('date').value,minute=Number($('time').value)){
 const d=SolarEngine.instant(day,minute),s=sun(d),[time,ampm]=clock(d).split(' ');$('time-label').replaceChildren(document.createTextNode(time+' '));const small=document.createElement('small');small.textContent=ampm||'';$('time-label').append(small);$('time').setAttribute('aria-valuetext',clock(d)+' Singapore time');
 $('period').textContent=s.altitude<=0?'Sun below horizon':s.altitude<5?'Sun near horizon':minute<720?'Morning sun':minute<900?'Early afternoon':'Afternoon sun';
 const compass=['N','NE','E','SE','S','SW','W','NW'][Math.round(s.bearing/45)%8];$('direction').textContent=s.altitude>89?'Near zenith · bearing unstable':`${s.bearing.toFixed(1)}° ${compass} · true north reference`;$('altitude').textContent=s.altitude.toFixed(1)+'°';$('sun-symbol').textContent=s.altitude>0?'☀':'☾';$('coordinates').textContent=center[1].toFixed(5)+'° N · '+center[0].toFixed(5)+'° E';
 const key=day+center.join(',');if(chartKey!==key){chartKey=key;const times=SolarEngine.events(day,center[1],center[0]);$('sunrise').textContent=clock(times.sunrise);$('sunset').textContent=clock(times.sunset);const pts=[];for(let m=360;m<=1200;m+=20)pts.push([(m-360)/840*720,55-Math.max(0,sun(SolarEngine.instant(day,m)).altitude)/90*50]);const path=pts.map((p,i)=>(i?'L':'M')+p.join(',')).join(' ');$('sun-curve').setAttribute('d',path);$('sun-area').setAttribute('d',path+' L720,60 L0,60 Z');}
 $('sun-dot').setAttribute('cx',(minute-360)/840*720);$('sun-dot').setAttribute('cy',55-Math.max(0,s.altitude)/90*50);document.querySelectorAll('#months button').forEach((b,i)=>b.setAttribute('aria-pressed',i===Number(day.slice(5,7))-1));
 if(ready){map.setLight({anchor:'map',position:[1.5,s.bearing,Math.max(0,Math.min(90,90-s.altitude))],intensity:.22,color:'#ffffff'});renderSunPath();}
}
$('play').onclick=()=>{if(playing){stop();return;}if(loading||loadError)return;playing=true;if(Number($('time').value)>=1200)$('time').value=360;$('play').textContent='Ⅱ';$('play').setAttribute('aria-label','Pause the day');update();};
// Handle pointer scrubbing ourselves: a native WebKit range drag can defer worker/paint
// delivery until release. Keep the native range for keyboard and assistive technology.
const timeline=$('time');let scrubPointer=null;
const scrubStats={inputs:0,frames:0,lastFrames:0,lastInputs:0};
const diagnostics=new URLSearchParams(location.search||'').has('diagnostics');
if(diagnostics){const out=document.createElement('output');out.id='scrub-diagnostics';out.style.cssText='position:fixed;top:0;left:0;z-index:99;background:white;color:black;padding:6px;font:12px monospace';document.body.append(out);}
function reportScrub(){if(diagnostics)$('scrub-diagnostics').textContent=`Drag active: ${scrubPointer!==null}; inputs: ${scrubStats.inputs}; frames while held: ${scrubStats.frames}; last drag: ${scrubStats.lastInputs} inputs, ${scrubStats.lastFrames} frames; last calculation: ${completed?.elapsed??0} ms`;}

function scrubAt(e){const r=timeline.getBoundingClientRect(),min=Number(timeline.min),max=Number(timeline.max),step=Number(timeline.step)||1;
 const fraction=Math.max(0,Math.min(1,(e.clientX-r.left-9)/Math.max(1,r.width-18)));
 const minute=min+Math.round(fraction*(max-min)/step)*step;
 if(Number(timeline.value)!==minute){timeline.value=minute;scrubStats.inputs++;stop();update();reportScrub();}
}
timeline.onpointerdown=e=>{if(e.button!==0||e.isPrimary===false)return;e.preventDefault();scrubPointer=e.pointerId;scrubStats.inputs=0;scrubStats.frames=0;timeline.setAttribute('data-pointer-focus','true');timeline.focus({preventScroll:true});timeline.setPointerCapture(e.pointerId);scrubAt(e);};
timeline.onpointermove=e=>{if(e.pointerId===scrubPointer){e.preventDefault();scrubAt(e);}};
function finishScrub(e){if(e.pointerId!==scrubPointer)return;if(e.type==='pointerup')scrubAt(e);scrubStats.lastFrames=scrubStats.frames;scrubStats.lastInputs=scrubStats.inputs;scrubPointer=null;reportScrub();if(timeline.hasPointerCapture(e.pointerId))timeline.releasePointerCapture(e.pointerId);}
timeline.onpointerup=finishScrub;timeline.onpointercancel=finishScrub;timeline.onlostpointercapture=()=>{scrubPointer=null;};
timeline.onkeydown=timeline.onblur=()=>timeline.removeAttribute('data-pointer-focus');
timeline.oninput=timeline.onchange=()=>{stop();update();};$('date').onchange=()=>{stop();update();};$('now').onclick=()=>{stop();$('date').value=today();update();};
['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].forEach((name,i)=>{const b=document.createElement('button');b.textContent=name;b.setAttribute('aria-pressed','false');b.onclick=()=>{stop();const [y,,day]=($('date').value||today()).split('-').map(Number),last=new Date(Date.UTC(y,i+1,0)).getUTCDate();$('date').value=`${y}-${String(i+1).padStart(2,'0')}-${String(Math.min(day,last)).padStart(2,'0')}`;update();};$('months').append(b);});
$('view').onclick=()=>{const on=map.getPitch()<10;map.easeTo({pitch:on?45:0,duration:250});};
$('shadows').onclick=()=>{showShadows=!showShadows;$('shadows').textContent=showShadows?'Shadows on':'Shadows off';$('shadows').setAttribute('aria-pressed',showShadows);update();};
$('estimates').onchange=()=>{estimates=$('estimates').checked;renderBuildings();update();};
function viewport(){const b=map.getBounds();return[b.getWest(),b.getSouth(),b.getEast(),b.getNorth()];}
function requestView(force=false,name){
 if(!ready)return;clearTimeout(panTimer);panTimer=null;const visible=viewport(),plan=ViewportPolicy.plan(visible,map.getZoom());
 if(plan.overview){
  ++loadId;loading=false;overview=true;loadedViewport=null;requestedViewport=null;features=[];coverageCounts=null;study=null;shadowStudy=null;selected=null;$('building').hidden=true;stop();clearShadows();
  map.getSource('building-data').setData(empty());map.getSource('boundary-data').setData(empty());$('load-area').disabled=false;$('load-area').textContent='Zoom in for shadows';$('place').textContent='Singapore';center=map.getCenter().toArray();update();return;
 }
 if(!force&&((loading&&ViewportPolicy.contains(requestedViewport,visible))||(!loading&&!loadError&&ViewportPolicy.contains(loadedViewport,visible)))){renderSunPath();return;}
 overview=false;requestedViewport=plan.study;loading=true;loadError='';stop();$('load-area').disabled=true;$('load-area').textContent='Updates automatically';
 // Keep the last bounded study visible while the next neighbourhood loads.
 const id=++loadId;loadArea.next={id,center:map.getCenter().toArray(),name:name||(Math.abs(map.getCenter().toArray()[0]-center[0])+Math.abs(map.getCenter().toArray()[1]-center[1])<.0001?$('place').textContent:'Map neighbourhood')};
 notice='Updating this view · Previous study remains visible until ready.';status();buildingWorker.postMessage({id,center:loadArea.next.center,study:plan.study,bounds:plan.bounds,future:includeFuture});
}
function loadArea(location=map.getCenter().toArray(),name='Map neighbourhood'){requestView(true,name);}
function queueView(){clearTimeout(panTimer);panTimer=setTimeout(()=>requestView(),150);}
buildingWorker.onmessage=({data})=>{if(data.id!==loadId)return;loading=false;$('load-area').disabled=false;$('load-area').textContent='Refresh this view';
 if(data.error){loadError=data.error;clearShadows();selected=null;$('building').hidden=true;features=[];coverageCounts=null;map.getSource('building-data').setData(empty());map.getSource('boundary-data').setData(empty());notice='Study unavailable. Retry loading this area.';status();return;}
 center=loadArea.next.center;$('place').textContent=loadArea.next.name;selected=null;$('building').hidden=true;map.setFilter('selected-building',['==',['id'],-1]);
 features=data.features;study=data.study;shadowStudy=data.shadowStudy;edgeClipped=data.clipped;loadedViewport=study;requestedViewport=null;release=data.release;
 for(const f of features){const edit=heightEdits.get(f.properties.key);if(edit&&!f.properties.landedFlat)Object.assign(f.properties,edit);}
 renderBuildings();map.getSource('study-point').setData(collection([{type:'Feature',properties:{},geometry:{type:'Point',coordinates:center}}]));
 map.getSource('boundary-data').setData(collection(shadowStudy?[{type:'Feature',properties:{},geometry:{type:'Polygon',coordinates:SolarGeometry.rectangle(shadowStudy)}}]:[]));update();
};
buildingWorker.onerror=()=>{loading=false;loadError='Building dataset could not be read. Reload the page to retry.';$('load-area').disabled=false;clearShadows();status();};
$('load-area').onclick=()=>{if(overview)map.easeTo({zoom:16.1,duration:300});else requestView(true);};
$('home').onclick=()=>{map.jumpTo({center:home,zoom:16.1});loadArea(home,'ION Orchard');};
$('future').onchange=()=>{includeFuture=$('future').checked;renderFutureProjects();requestView(true,$('place').textContent);};
function renderFutureProjects(){
 const modeled=futureCatalog.filter(p=>p.towers?.length).length,review=futureCatalog.filter(p=>p.launchSync&&p.launchSync.status!=='current').length;
 $('future-status').textContent=`${modeled} projects with building models · ${futureCatalog.length-modeled} awaiting model alignment. Future heights and footprints are approximate.${review?' '+review+' launches awaiting plans or model review.':''}`;
 if(!ready)return;map.getSource('future-projects').setData(collection(includeFuture?futureCatalog.map((p,i)=>({p,i})).filter(({p})=>p.center).map(({p,i})=>({type:'Feature',id:i,geometry:{type:'Point',coordinates:p.center},properties:{name:p.name,modeled:Boolean(p.towers?.length)}})):[]));
}
function showProject(index){const p=futureCatalog[index];if(!p)return;selected=null;$('building').hidden=false;$('building-name').textContent=p.name;$('building-address').textContent=p.address||'Select an individual building for its block address.';$('address-source').hidden=true;$('address-retry').hidden=true;$('height-edit-note').hidden=true;
 $('height-source').textContent=p.towers?.length?`Completed-development scenario · ${p.towers.length} building sections. ${p.modelNote} ${p.launchSync?.message||''}`:'Future development · Tower placement is not yet aligned. No future shadows are calculated for this project.';if(!p.towers?.length&&p.launchSync)$('height-source').textContent=p.launchSync.message;
 $('height-form').hidden=true;$('reset-height').hidden=true;$('source-link').hidden=!(p.launchSync?.url||p.planUrl);$('source-link').href=p.launchSync?.url||p.planUrl||'#';$('source-link').textContent=p.launchSync?'View '+(p.launchSync.sourceLabel||'JND Launches')+' ↗':'View site-plan source ↗';
 $('source-detail').textContent=`Expected completion: ${p.top}. ${p.launchSync?(p.launchSync.sourceLabel||'JND Launches')+' source updated: '+(p.launchSync.sourceUpdatedAt?.slice(0,10)||'date unavailable')+' · Model checked: '+(p.asOf||'pending'):'Vault / ERA portal snapshot: '+p.asOf}. ${p.floorRange?'Listed residential floors: '+p.floorRange+'. ':''}Completion dates are source estimates.`;
}
function choose(p){map.jumpTo({center:[p.lon,p.lat],zoom:16.1});loadArea([p.lon,p.lat],p.name);}
const searchControl=LocationSearch.mount({document,input:$('query'),list:$('results'),status:$('search-status'),form:$('search'),container:$('location-search'),
 getPlaces(){const upcoming=futureCatalog.filter(p=>p.center).map(p=>({name:p.name,address:p.address,lon:p.center[0],lat:p.center[1]}));const names=new Set(upcoming.map(p=>p.name.toLowerCase()));return [...upcoming,...places.filter(p=>!names.has(p.name.toLowerCase())).map(p=>({...p,name:p.name.replace(/^street:/i,'')}))];},
 async lookup(q,signal){const response=await fetch('https://photon.komoot.io/api/?'+new URLSearchParams({q,lat:'1.35',lon:'103.82',bbox:ViewportPolicy.coverage.join(','),limit:'8'}),{signal});if(!response.ok)throw Error('Search unavailable');const data=await response.json();return LocationSearch.match(q,data.features.map(f=>({lon:f.geometry.coordinates[0],lat:f.geometry.coordinates[1],name:[f.properties.name,f.properties.housenumber,f.properties.street].filter(Boolean).join(' · ')})).filter(p=>p.name&&p.lon>ViewportPolicy.coverage[0]&&p.lon<ViewportPolicy.coverage[2]&&p.lat>ViewportPolicy.coverage[1]&&p.lat<ViewportPolicy.coverage[3]));},choose});
const lookupAddress=AddressLookup.client((...args)=>fetch(...args));let addressSequence=0;
function paintAddress(p){$('building-address').textContent=p.address||'Address not recorded in the building source.';$('address-source').hidden=!p.addressSource;$('address-source').href=p.addressSource||'#';$('address-source').textContent=p.addressInherited?'Address source · parent building ↗':'Address source ↗';$('address-retry').hidden=true;}
async function resolveAddress(f){const seq=++addressSequence;if(!AddressLookup.queries(f.properties).length)return;$('building-address').textContent='Looking up this block in OneMap…';$('address-retry').hidden=true;
 try{const found=await lookupAddress(f,features);if(seq!==addressSequence||selected?.properties.key!==f.properties.key)return;
  if(found){Object.assign(selected.properties,found);paintAddress(selected.properties);}else{$('building-address').textContent='OneMap has not confirmed a unique address for this footprint.';}
 }catch(e){if(seq===addressSequence&&selected?.properties.key===f.properties.key){$('building-address').textContent=e.message;$('address-retry').hidden=false;}}
}
$('address-retry').onclick=()=>{if(selected)resolveAddress(selected);};
function selectBuilding(f){selected=features.find(x=>x.id===f.id);if(!selected)return;$('building').hidden=false;const p=selected.properties;$('building-name').textContent=p.name||p.address||'Building';paintAddress(p);if(!p.address)resolveAddress(selected);$('height-source').textContent=p.source;$('height').value=p.height===null?'':p.height.toFixed(1);$('source-link').textContent='View building source ↗';$('source-link').hidden=!(p.floorSource||p.geometrySource);$('source-link').href=p.floorSource||p.geometrySource||'#';$('source-detail').textContent=(p.sources||[]).map(s=>s.dataset+(s.updated&&!s.updated.startsWith('2000-01-01')?' · source dated '+s.updated.slice(0,10):' · date unavailable')).filter((v,i,a)=>a.indexOf(v)===i).join('; ');$('height-form').hidden=p.quality==='outline'||p.landedFlat;$('reset-height').hidden=p.quality==='outline'||p.landedFlat;$('height-edit-note').hidden=p.quality==='outline'||p.landedFlat;map.setFilter('selected-building',['==',['id'],selected.id]);}
$('close-building').onclick=()=>{$('building').hidden=true;selected=null;map.setFilter('selected-building',['==',['id'],-1]);};
function editHeight(height){if(!selected)throw Error('Select a building first');if(selected.properties.landedFlat)throw Error('Landed homes stay as flat footprints.');if(!Number.isFinite(height)||height<1||height>400||height<=selected.properties.baseHeight)throw Error('Roof height must be 1–400 m and higher than the building base.');const p={height,quality:'manual',source:`User-entered roof height: ${height} m above ground. Not independently verified.`};Object.assign(selected.properties,p);heightEdits.set(selected.properties.key,p);renderBuildings();selectBuilding(selected);update();}
$('height-form').onsubmit=e=>{e.preventDefault();try{editHeight(Number($('height').value));$('height').setCustomValidity('');}catch(e){$('height').setCustomValidity(e.message);$('height').reportValidity();}};$('height').oninput=()=>$('height').setCustomValidity('');
$('reset-height').onclick=()=>{if(!selected)return;const p=selected.properties;Object.assign(p,{height:p.originalHeight,quality:p.originalQuality,source:p.originalSource});heightEdits.delete(p.key);renderBuildings();selectBuilding(selected);update();};
$('about').onclick=()=>$('info').showModal();$('close-info').onclick=()=>$('info').close();document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});window.addEventListener('message',e=>{if(e.source===parent&&e.origin===location.origin&&e.data?.type==='jnd-sun-visibility'&&!e.data.visible)stop();});
try{
 map=new maplibregl.Map({container:'map',center:home,zoom:16.1,pitch:45,maxZoom:19,minZoom:10,cooperativeGestures:true,maxBounds:[ViewportPolicy.coverage.slice(0,2),ViewportPolicy.coverage.slice(2)],style:{version:8,sources:{base:{type:'raster',tiles:['https://www.onemap.gov.sg/maps/tiles/Grey/{z}/{x}/{y}.png'],tileSize:256,maxzoom:18,attribution:'<img src="vendor/onemap-logo.png" alt="OneMap" style="height:14px;vertical-align:middle"> Map © <a href="https://www.onemap.gov.sg/">OneMap / SLA</a> · Buildings © <a href="https://docs.overturemaps.org/attribution/">Overture</a>, <a href="https://www.openstreetmap.org/copyright">OSM contributors</a>'}},layers:[{id:'ground',type:'background',paint:{'background-color':'#F7F7F8'}},{id:'base',type:'raster',source:'base',paint:{'raster-opacity':.24,'raster-saturation':-1}}]}});
 map.addControl(new maplibregl.NavigationControl(),'top-right');map.addControl(new maplibregl.ScaleControl({maxWidth:90}),'bottom-left');
 map.on('moveend',queueView);map.on('resize',queueView);
 map.on('move',()=>{if(!panTimer)panTimer=setTimeout(()=>{panTimer=null;requestView();},800);});
 map.on('pitchend',()=>{const on=map.getPitch()>10;$('view').textContent=on?'3D view':'2D view';$('view').setAttribute('aria-pressed',on);});
 map.on('load',()=>{for(const id of ['building-data','shadow-data','boundary-data','study-point','sun-path','future-projects'])map.addSource(id,{type:'geojson',data:empty()});
  shadowCanvas=document.createElement('canvas');shadowCanvas.width=shadowCanvas.height=2048;shadowContext=shadowCanvas.getContext?.('2d');

  if(shadowContext){groundShadowLayer=new GroundShadowLayer(shadowCanvas);map.addLayer(groundShadowLayer);}
  map.addLayer({id:'shadows',type:'fill',source:'shadow-data',paint:{'fill-color':'#1B1D22','fill-opacity':.62,'fill-antialias':false}});
  map.addLayer({id:'unknown-footprints',type:'fill',source:'building-data',paint:{'fill-color':'#C7C9CE','fill-opacity':.15}});
  map.addLayer({id:'footprint-lines',type:'line',source:'building-data',paint:{'line-color':'#9EA2AA','line-width':.6}});
  map.addLayer({id:'buildings',type:'fill-extrusion',source:'building-data',filter:['>',['get','renderHeight'],0],paint:{'fill-extrusion-color':['case',['==',['get','future'],true],'#A9BFC6',['match',['get','quality'],'derived','#E6E7E9','assumed','#D3C7B5','manual','#F2A63A','#C7C9CE']],'fill-extrusion-height':['get','renderHeight'],'fill-extrusion-base':['min',['get','baseHeight'],['get','renderHeight']],'fill-extrusion-opacity':1}});
  map.addLayer({id:'selected-building',type:'line',source:'building-data',filter:['==',['id'],-1],paint:{'line-color':'#8E2118','line-width':3}});
  map.addLayer({id:'loaded-boundary',type:'line',source:'boundary-data',paint:{'line-color':'#41454E','line-width':1.5,'line-dasharray':[4,4],'line-opacity':.8}});
  map.addLayer({id:'sun-path-line',type:'line',source:'sun-path',layout:{'line-cap':'round','line-join':'round'},paint:{'line-color':'#C99B35','line-width':2.5,'line-opacity':.8}});
  map.addLayer({id:'study-centre',type:'circle',source:'study-point',paint:{'circle-radius':5,'circle-color':'#CF3F22','circle-stroke-color':'white','circle-stroke-width':2}});
  map.addLayer({id:'future-markers',type:'circle',source:'future-projects',paint:{'circle-radius':['interpolate',['linear'],['zoom'],10,4,16,6],'circle-color':['case',['get','modeled'],'#3D6977','#ffffff'],'circle-stroke-width':2,'circle-stroke-color':'#3D6977','circle-opacity':.9}});
  map.on('click',e=>{const hits=map.queryRenderedFeatures(e.point,{layers:['buildings','unknown-footprints']});if(hits.length){selectBuilding(hits[0]);return;}const projects=map.queryRenderedFeatures(e.point,{layers:['future-markers']});if(projects.length)showProject(projects[0].id);});map.on('mouseenter','unknown-footprints',()=>map.getCanvas().style.cursor='pointer');map.on('mouseleave','unknown-footprints',()=>map.getCanvas().style.cursor='');ready=true;renderFutureProjects();loadArea(home,'ION Orchard');});
 map.on('error',e=>{if(e.sourceId==='base'){$('map-error').hidden=false;$('map-error').textContent='Basemap unavailable. Check your connection; building studies still require their own data.';}});
}catch(e){loadError='This browser could not start the 3D map. Use a current browser with WebGL enabled.';status();}
update();
function publicState(){return {place:$('place').textContent,center,date:$('date').value,minutes:Number($('time').value),displayedTime:$('time-label').textContent,sun:SolarEngine.validDate($('date').value)?sun():null,loading,loadError,counts:counts(),release,study,shadowStudy,overview,includeFuture,futureProjects:{catalog:futureCatalog.length,modeled:futureCatalog.filter(p=>p.towers?.length).length},completed,showShadows,estimates,notice,selected:selected?{id:selected.id,name:selected.properties.name,address:selected.properties.address||null,height:selected.properties.height,quality:selected.properties.quality}:null};}
if(document.modelContext?.registerTool){const lifecycle=new AbortController();window.addEventListener('pagehide',()=>lifecycle.abort());const register=tool=>{try{Promise.resolve(document.modelContext.registerTool(tool,{signal:lifecycle.signal})).catch(()=>{});}catch(e){}};
 register({name:'read_sun_study',description:'Read visible sun study state, loaded height coverage and completed shadow time.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true},execute:()=>publicState()});
 register({name:'set_sun_study_time',description:'Set a valid date and Singapore time for the current study. Shadows compute asynchronously; read_sun_study reports completion.',inputSchema:{type:'object',properties:{date:{type:'string'},minutes:{type:'integer',minimum:360,maximum:1200}},required:['date','minutes'],additionalProperties:false},execute:input=>{if(!SolarEngine.validDate(input.date)||!Number.isInteger(input.minutes)||input.minutes<360||input.minutes>1200)throw Error('Valid date (2000–2100) and minutes 360–1200 required');stop();$('date').value=input.date;$('time').value=input.minutes;update();return publicState();}});
}
