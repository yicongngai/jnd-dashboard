/* Boolean operations in a local integer millimetre grid avoid unstable coincident longitude edges. */
(function(root){
 const C=typeof module==='object'?require('./vendor/clipper.js'):root.ClipperLib,G=typeof module==='object'?require('./solar.js'):root.SolarGeometry;
 function combine(polygons,origin,bounds){if(!polygons.length)return[];const metres=G.metresPerDegree(origin[1]),scale=1000;
  const encode=ring=>ring.slice(0,-1).map(p=>({X:Math.round((p[0]-origin[0])*metres.east*scale),Y:Math.round((p[1]-origin[1])*metres.north*scale)}));
  const paths=[];for(const rings of polygons)for(let i=0;i<rings.length;i++){const path=encode(rings[i]);if(path.length<3)continue;if(C.Clipper.Orientation(path)!==(i===0))path.reverse();paths.push(path);}
  const clipper=new C.Clipper(),tree=new C.PolyTree();if(!clipper.AddPaths(paths,C.PolyType.ptSubject,true))return[];if(bounds)clipper.AddPaths([encode(G.rectangle(bounds)[0])],C.PolyType.ptClip,true);
  if(!clipper.Execute(bounds?C.ClipType.ctIntersection:C.ClipType.ctUnion,tree,C.PolyFillType.pftNonZero,C.PolyFillType.pftNonZero))throw Error('Polygon clipping could not complete');
  const decode=ring=>{const out=ring.map(p=>[origin[0]+p.X/(metres.east*scale),origin[1]+p.Y/(metres.north*scale)]);out.push(out[0].slice());return out;};
  return C.JS.PolyTreeToExPolygons(tree).map(p=>[decode(p.outer),...p.holes.map(decode)]);
 }
 const api={combine};if(typeof module==='object')module.exports=api;else root.PolygonEngine=api;
})(typeof window==='object'?window:globalThis);
