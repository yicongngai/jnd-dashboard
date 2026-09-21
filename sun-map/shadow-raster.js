/* Rasterise the same nonzero-winding union as PolygonEngine, without re-tiling
   a large GeoJSON after every time change. One opaque fill prevents dark overlaps. */
(function(root){
 function signedArea(r){let a=0;for(let i=1;i<r.length;i++)a+=r[i-1][0]*r[i][1]-r[i][0]*r[i-1][1];return a;}
 const mercator=lat=>Math.log(Math.tan(Math.PI/4+lat*Math.PI/360));
 function paint(ctx,polygons,bounds,size=2048){
  const [west,south,east,north]=bounds,yNorth=mercator(north),ySouth=mercator(south);
  ctx.clearRect(0,0,size,size);ctx.beginPath();
  for(const rings of polygons)for(let i=0;i<rings.length;i++){
   const original=rings[i],r=(signedArea(original)>0)===(i===0)?original:original.slice().reverse();
   for(let j=0;j<r.length;j++){const p=r[j],x=(p[0]-west)/(east-west)*size,y=(yNorth-mercator(p[1]))/(yNorth-ySouth)*size;if(j===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);}ctx.closePath();
  }
  ctx.fillStyle='#1B1D22';ctx.fill('nonzero');
 }
 const api={paint,signedArea};if(typeof module==='object')module.exports=api;else root.ShadowRaster=api;
})(typeof window==='object'?window:globalThis);
