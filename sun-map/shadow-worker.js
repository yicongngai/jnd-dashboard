importScripts('vendor/clipper.js?v=6','solar.js?v=6','polygon-engine.js?v=25','shadow-raster.js?v=25');
let cachedFeatures=[],rasterCanvas=null,rasterContext=null;
onmessage=({data})=>{const started=performance.now();try{
 if(Array.isArray(data.features))cachedFeatures=data.features;
 const polygons=[];
 for(const f of cachedFeatures){if(!f.properties.height||(!data.estimates&&f.properties.quality==='derived'))continue;
  const parts=SolarGeometry.shadows(f,data.altitude,data.bearing);
  for(const p of parts)if(SolarGeometry.intersects(SolarGeometry.bbox({coordinates:p}),data.bounds))polygons.push(p);
 }
 if(data.raster&&typeof OffscreenCanvas!=='undefined'){
  if(!rasterCanvas){rasterCanvas=new OffscreenCanvas(2048,2048);rasterContext=rasterCanvas.getContext('2d');}
  if(rasterContext){ShadowRaster.paint(rasterContext,polygons,data.bounds);const bitmap=rasterCanvas.transferToImageBitmap();postMessage({id:data.id,bitmap,polygons:polygons.length,elapsed:Math.round(performance.now()-started)},[bitmap]);return;}
 }
 const origin=[(data.bounds[0]+data.bounds[2])/2,(data.bounds[1]+data.bounds[3])/2];
 const coordinates=PolygonEngine.combine(polygons,origin,data.bounds);
 postMessage({id:data.id,coordinates,elapsed:Math.round(performance.now()-started)});
}catch(e){postMessage({id:data.id,error:String(e)});}};
