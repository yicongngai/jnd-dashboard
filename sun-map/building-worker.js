importScripts('vendor/clipper.js?v=23','solar.js?v=23','polygon-engine.js?v=23','building-data.js?v=23','viewport.js?v=23','future-data.js?v=23','outline-updates.js?v=23');
const cache=new Map();let metadata=null,latest=0;
async function json(url){const r=await fetch(url,{signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error('Building data unavailable. Retry this area.');return r.json();}
async function tile(key){
 if(cache.has(key)){const hit=cache.get(key);cache.delete(key);cache.set(key,hit);return hit;}
 const promise=(async()=>{const r=await fetch('data/'+key+'.json.gz',{signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error('A required building tile is unavailable. Retry loading this area.');return new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).json();})();
 cache.set(key,promise);try{return await promise;}catch(e){cache.delete(key);throw e;}
}
onmessage=async({data})=>{latest=data.id;try{
 if(!metadata)metadata=Promise.all([json('data/manifest.json?v=23'),json('data/verified-floors.json?v=23'),json('data/future-projects.json?v=23'),json('data/house-types.json'),json('data/hdb-floors.json?v=23'),json('data/osm-refresh.json?v=23'),json('data/outline-updates.json?v=23'),json('data/original-details.json?v=23')]).catch(e=>{metadata=null;throw e;});
 const [manifest,verified,future,houses,hdb,refresh,outlines,originals]=await metadata;if(data.id!==latest)return;
 const study=data.study||BuildingData.extent(data.center,650),wanted=data.bounds||ViewportPolicy.pad(study,ViewportPolicy.buffer);
 const keys=BuildingData.tileKeys(wanted).filter(k=>k in manifest.tiles);
 if(!keys.length)throw Error('Choose a location within the supported Singapore dataset.');
 const tiles=[];let cursor=0;await Promise.all(Array.from({length:Math.min(4,keys.length)},async()=>{while(cursor<keys.length){if(data.id!==latest)return;tiles.push(await tile(keys[cursor++]));}}));
 if(data.id!==latest)return;
 const detailedTiles=OutlineUpdates.apply(tiles,wanted,originals);
 let features=BuildingData.merge(OutlineUpdates.apply(detailedTiles,wanted,outlines),wanted,verified.records,houses.records,data.landedHeight??6,hdb.records,refresh.records);
 features=FutureData.apply(features,future,study,wanted,data.future!==false);
 // Missing outer tiles are allowed only with a reduced, explicitly bounded shadow area.
 const corners=Object.keys(manifest.tiles).map(k=>k.split('-').map(Number)),xs=corners.map(c=>c[0]),ys=corners.map(c=>c[1]);
 const nw=BuildingData.tileCorner(Math.min(...xs),Math.min(...ys)),se=BuildingData.tileCorner(Math.max(...xs)+1,Math.max(...ys)+1);
 const safe=ViewportPolicy.pad([nw[0],se[1],se[0],nw[1]],-ViewportPolicy.buffer);
 const shadowStudy=study.map((x,i)=>i<2?Math.max(x,safe[i]):Math.min(x,safe[i]));
 const clipped=!ViewportPolicy.contains(safe,study);
 while(cache.size>32)cache.delete(cache.keys().next().value);
 postMessage({id:data.id,features,bounds:wanted,study,shadowStudy:shadowStudy[0]<shadowStudy[2]&&shadowStudy[1]<shadowStudy[3]?shadowStudy:null,clipped,release:manifest.release,tiles:keys.length});
}catch(e){if(data.id===latest)postMessage({id:data.id,error:e.message});}};
