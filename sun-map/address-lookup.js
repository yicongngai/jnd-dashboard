/* Public OneMap lookups: an address must belong to the clicked footprint. */
(function(root){
 const bounds=new WeakMap();
 function ring(point,ring){let inside=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){
  const a=ring[j],b=ring[i],cross=(point[0]-a[0])*(b[1]-a[1])-(point[1]-a[1])*(b[0]-a[0]);
  if(Math.abs(cross)<1e-14&&point[0]>=Math.min(a[0],b[0])&&point[0]<=Math.max(a[0],b[0])&&point[1]>=Math.min(a[1],b[1])&&point[1]<=Math.max(a[1],b[1]))return true;
  if((a[1]>point[1])!==(b[1]>point[1])&&point[0]<(b[0]-a[0])*(point[1]-a[1])/(b[1]-a[1])+a[0])inside=!inside;
 }return inside;}
 function contains(geometry,point){
  const polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates;
  let box=bounds.get(geometry);if(!box){const pts=polygons.flat(2);box=[Infinity,Infinity,-Infinity,-Infinity];for(const p of pts){box[0]=Math.min(box[0],p[0]);box[1]=Math.min(box[1],p[1]);box[2]=Math.max(box[2],p[0]);box[3]=Math.max(box[3],p[1]);}bounds.set(geometry,box);}
  if(point[0]<box[0]||point[0]>box[2]||point[1]<box[1]||point[1]>box[3])return false;
  return polygons.some(poly=>ring(point,poly[0])&&!poly.slice(1).some(hole=>ring(point,hole)));
 }
 const key=f=>f.properties.key||f.properties.id;
 const family=f=>f.properties.parent||key(f);
 function match(selected,rows,features){
  const found=new Map(),block=selected.properties.future?selected.properties.name?.match(/\bBlock\s+(\d+[A-Z]?)(?:\b|\s)/i)?.[1].toUpperCase():null;
  for(const r of rows){const number=String(r.BLK_NO||'').trim(),street=String(r.ROAD_NAME||'').trim(),postal=String(r.POSTAL||'').trim(),point=[Number(r.LONGITUDE),Number(r.LATITUDE)];
   if(!number||number==='NIL'||number==='0'||!street||street==='NIL'||!point.every(Number.isFinite)||(block&&number.toUpperCase()!==block)||!contains(selected.geometry,point))continue;
   const families=new Set(features.filter(f=>contains(f.geometry,point)).map(family));if(families.size!==1||!families.has(family(selected)))continue;
   const address=number+' '+street+(/^\d{6}$/.test(postal)?' · Singapore '+postal:'');
   found.set(address,{address,addressSource:'https://www.onemap.gov.sg/?'+new URLSearchParams({lat:point[1],lng:point[0]}),addressInherited:false});
  }
  return found.size===1?[...found.values()][0]:null;
 }
 function queries(p){const q=p.lookupQueries?.length?p.lookupQueries:[(p.name||'').split(' · ')[0]];return [...new Set(q)].filter(x=>x&&/[a-z]{3}/i.test(x)&&!/^(?:Building|Landed home|House|HDB|Residential|Residential building|Condominium)$|^Block\s+[\dA-Z]+$/i.test(x));}
 function client(fetcher){const cache=new Map();let queue=Promise.resolve();
  function request(url){const result=queue.then(async()=>{const r=await fetcher(url,{signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error(r.status===429?'OneMap is busy. Please try again shortly.':'OneMap lookup is unavailable. Please try again.');const d=await r.json();if(!Array.isArray(d.results))throw Error('OneMap lookup is unavailable. Please try again.');return d;});queue=result.catch(()=>{}).then(()=>new Promise(resolve=>setTimeout(resolve,650)));return result;}
  function search(q){if(cache.has(q))return cache.get(q);const job=(async()=>{const rows=[];for(let page=1;page<=30;page++){const d=await request('https://www.onemap.gov.sg/api/common/elastic/search?'+new URLSearchParams({searchVal:q,returnGeom:'Y',getAddrDetails:'Y',pageNum:page}));rows.push(...d.results);if(page>=Number(d.totalNumPages||1))return rows;}throw Error('OneMap returned too many locations to confirm this block.');})();cache.set(q,job);job.catch(()=>cache.delete(q));return job;}
  return async(selected,features)=>{const q=queries(selected.properties);if(q.length>5)return null;const rows=(await Promise.all(q.map(search))).flat();return match(selected,rows,features);};
 }
 const api={contains,match,queries,client};if(typeof module==='object')module.exports=api;else root.AddressLookup=api;
})(typeof window==='object'?window:globalThis);
