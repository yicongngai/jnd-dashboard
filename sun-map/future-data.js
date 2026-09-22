/* Completed-development scenario. Never derive a tower from a project marker alone. */
(function(root){
 const G=typeof module==='object'?require('./solar.js'):root.SolarGeometry;
 function inside(point,ring){let yes=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){const a=ring[i],b=ring[j];if(((a[1]>point[1])!==(b[1]>point[1]))&&(point[0]<(b[0]-a[0])*(point[1]-a[1])/(b[1]-a[1])+a[0]))yes=!yes;}return yes;}
 function apply(existing,catalog,study,bounds,enabled){
  // Some base-source parts already describe unbuilt developments. Exclude only
  // individually reviewed source IDs, even when the future scenario is off.
  const planned=new Set(catalog.projects.flatMap(p=>p.excludeExistingOsmIds||[]));
  existing=existing.filter(f=>!planned.has(f.properties.osmId));
  if(!enabled)return existing;
  const projects=catalog.projects.filter(p=>p.towers?.length&&p.site&&G.intersects(G.bbox({coordinates:[p.site]}),bounds));
  // Replace only snapshot footprints whose centre is inside the curated development site.
  // Roads, adjacent estates, and marker-only projects do not remove any source geometry.
  const retained=existing.filter(f=>{const b=G.bbox(f.geometry),point=[(b[0]+b[2])/2,(b[1]+b[3])/2];return !projects.some(p=>inside(point,p.site));});
  for(const p of projects)for(const t of p.towers){const height=t.floors*3,source=`Future ${p.name}, ${t.name}: ${t.floors} storeys × 3 m = ${height} m estimated roof height. Approximate site-plan massing and placement; not surveyed. ${p.modelNote} ${p.launchSync?.message||''}${t.heightNote?' '+t.heightNote:''}`;
   retained.push({type:'Feature',geometry:t.geometry,properties:{key:'future:'+p.id+':'+t.name,name:p.name+' · '+t.name,future:true,project:p.id,floors:t.floors,height,baseHeight:0,quality:'derived',source,floorSource:p.planUrl,geometrySource:t.geometrySource,originalHeight:height,originalQuality:'derived',originalSource:source,sources:[{dataset:p.planDataset||'Vault site plan / elevation chart',updated:p.asOf},{dataset:p.geometryDataset||'OneMap project location',updated:p.geometryDate||p.coordinateDate}]}});
  }
  return retained.map((f,id)=>({...f,id}));
 }
 const api={apply,inside};if(typeof module==='object')module.exports=api;else root.FutureData=api;
})(typeof window==='object'?window:globalThis);
