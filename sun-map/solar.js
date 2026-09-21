/* WGS84 local-plane projections, ground-shadow geometry and explicit height provenance. */
(function(root){
 'use strict';const rad=Math.PI/180,a=6378137,e2=6.69437999014e-3;
 function metresPerDegree(lat){const s=Math.sin(lat*rad),d=Math.sqrt(1-e2*s*s);return {east:rad*a/d*Math.cos(lat*rad),north:rad*a*(1-e2)/(d*d*d)};}
 function offset(p,east,north){const m=metresPerDegree(p[1]);return[p[0]+east/m.east,p[1]+north/m.north];}
 function shadowVector(height,altitude,bearing){if(!Number.isFinite(height)||height<=0||!Number.isFinite(altitude)||altitude<=0||altitude>90||!Number.isFinite(bearing))return null;const length=height/Math.tan(altitude*rad);return {east:-Math.sin(bearing*rad)*length,north:-Math.cos(bearing*rad)*length,length};}
 function shadows(feature,altitude,bearing){const v=shadowVector(feature.properties.height,altitude,bearing);if(!v||altitude<5)return[];const base=feature.properties.minHeight||0,b=base>0?shadowVector(base,altitude,bearing):{east:0,north:0},polys=feature.geometry.type==='Polygon'?[feature.geometry.coordinates]:feature.geometry.coordinates,out=[];
  for(const rings of polys){out.push(rings.map(r=>r.map(p=>offset(p,v.east,v.north))));
   for(const ring of rings)for(let i=0;i<ring.length-1;i++){const p=ring[i],q=ring[i+1];out.push([[offset(p,b.east,b.north),offset(q,b.east,b.north),offset(q,v.east,v.north),offset(p,v.east,v.north),offset(p,b.east,b.north)]]);}}
  return out;
 }
 function parseHeight(value){if(typeof value==='number')return Number.isFinite(value)&&value>0&&value<=1000?value:null;if(typeof value!=='string')return null;const m=value.trim().match(/^(\d+(?:\.\d+)?)\s*(m|metres?|meters?|ft|feet|')?$/i);if(!m)return null;const n=Number(m[1])*(/^(ft|feet|')$/i.test(m[2]||'')?.3048:1);return n>0&&n<=1000?n:null;}
 function heightInfo(tags){const h=parseHeight(tags.height);if(h!==null)return{height:h,quality:'tagged',source:'Height recorded in source data; not independently surveyed'};const levels=Number(tags.floors??tags['building:levels']);if(Number.isFinite(levels)&&levels>0&&levels<=200)return{height:levels*3,quality:'derived',floors:levels,source:levels+' storeys × 3 m; estimated height'};return{height:null,quality:'unknown',source:'Height missing. This footprint casts no modelled shadow.'};}
 function bbox(geometry){let w=Infinity,s=Infinity,e=-Infinity,n=-Infinity;function walk(c){if(typeof c[0]==='number'){w=Math.min(w,c[0]);e=Math.max(e,c[0]);s=Math.min(s,c[1]);n=Math.max(n,c[1]);}else for(const v of c)walk(v);}walk(geometry.coordinates);return[w,s,e,n];}
 function intersects(a,b){return a[0]<=b[2]&&a[2]>=b[0]&&a[1]<=b[3]&&a[3]>=b[1];}
 function rectangle(b){return[[[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]],[b[0],b[1]]]];}
 const api={offset,shadowVector,shadows,heightInfo,parseHeight,bbox,intersects,rectangle,metresPerDegree};if(typeof module==='object')module.exports=api;else root.SolarGeometry=api;
})(typeof window==='object'?window:globalThis);
