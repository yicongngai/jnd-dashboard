/* Source-reviewed OSM outline corrections over the reproducible Overture tiles. */
(function(root){
 const G=typeof module==='object'?require('./solar.js'):root.SolarGeometry;
 function apply(tiles,bounds,data={updates:[]}){
  const updates=data.updates||[],replaced=new Set(updates.filter(u=>u.replaces).map(u=>u.replaces));
  const features=[];
  // Suppress every clipped fragment of a replaced ID. Add its whole current
  // outline once, including when it moved into this view from another tile.
  for(const tile of tiles)for(const f of tile.features)if(!replaced.has(f.properties.id))features.push(f);
  for(const u of updates)if(G.intersects(G.bbox(u.feature.geometry),bounds))features.push(u.feature);
  return [{features}];
 }
 const api={apply};if(typeof module==='object')module.exports=api;else root.OutlineUpdates=api;
})(typeof window==='object'?window:globalThis);
