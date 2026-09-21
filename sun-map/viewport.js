/* Shared viewport policy. Detailed shadows at street scale; pan anywhere in Singapore. */
(function(root){
 const G=typeof module==='object'?require('./solar.js'):root.SolarGeometry;
 // Navigation envelope includes offshore islands; not an administrative boundary.
 const coverage=[103.58,1.13,104.43,1.49],buffer=2250;
 function pad(b,m){return [...G.offset([b[0],b[1]],-m,-m),...G.offset([b[2],b[3]],m,m)];}
 function contains(outer,inner){return outer&&inner&&inner[0]>=outer[0]&&inner[1]>=outer[1]&&inner[2]<=outer[2]&&inner[3]<=outer[3];}
 function plan(bounds,zoom){
  if(!Array.isArray(bounds)||bounds.length!==4||!bounds.every(Number.isFinite)||bounds[0]>=bounds[2]||bounds[1]>=bounds[3])throw Error('Invalid map viewport.');
  const width=(bounds[2]-bounds[0])*111320,height=(bounds[3]-bounds[1])*110574;
  if(zoom<15||Math.max(width,height)>7000)return{overview:true};
  const wanted=pad(bounds,120),study=wanted.map((x,i)=>i<2?Math.max(x,coverage[i]):Math.min(x,coverage[i]));
  if(study[0]>=study[2]||study[1]>=study[3])return{overview:true};
  return{overview:false,study,bounds:pad(study,buffer),center:[(study[0]+study[2])/2,(study[1]+study[3])/2]};
 }
 const api={plan,pad,contains,coverage,buffer};if(typeof module==='object')module.exports=api;else root.ViewportPolicy=api;
})(typeof window==='object'?window:globalThis);
