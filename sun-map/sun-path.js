/* A schematic compass arc: distance is a display scale, bearing is astronomical. */
(function(root){
 const S=typeof module==='object'?require('./solar-engine.js'):root.SolarEngine;
 const G=typeof module==='object'?require('./solar.js'):root.SolarGeometry;
 function point(center,bearing,radius){return G.offset(center,Math.sin(bearing*Math.PI/180)*radius,Math.cos(bearing*Math.PI/180)*radius);}
 function day(day,center,radius=260){
  const events=S.events(day,center[1],center[0]),start=S.instant(day,0).getTime();
  const minute=d=>Math.round((d.getTime()-start)/60000);
  if(!events.sunrise||!events.sunset)return{line:[],stops:[]};
  const rise=minute(events.sunrise),set=minute(events.sunset),line=[];
  for(let m=rise;m<=set;m++){const s=S.position(S.instant(day,m),center[1],center[0]);line.push(point(center,s.bearing,radius));}
  const stops=[{minute:rise,label:'Sunrise'},...[540,720,900].filter(m=>m>rise&&m<set).map(m=>({minute:m,label:m===720?'Noon':m<720?m/60+' AM':m/60-12+' PM'})),{minute:set,label:'Sunset'}].map(p=>({...p,coordinate:point(center,S.position(S.instant(day,p.minute),center[1],center[0]).bearing,radius)}));
  return{line,stops};
 }
 const api={day,point};if(typeof module==='object')module.exports=api;else root.SunPath=api;
})(typeof window==='object'?window:globalThis);
