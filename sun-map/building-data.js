/* Versioned Overture tiles. IDs are stable strings: numeric MVT IDs exceed JS precision. */
(function(root){
 const G=typeof module==='object'?require('./solar.js'):root.SolarGeometry;
 const P=typeof module==='object'?require('./polygon-engine.js'):root.PolygonEngine;
 function tileAt(lon,lat,z=14){return[Math.floor((lon+180)/360*2**z),Math.floor((1-Math.asinh(Math.tan(lat*Math.PI/180))/Math.PI)/2*2**z)];}
 function tileCorner(x,y,z=14){return[x/2**z*360-180,Math.atan(Math.sinh(Math.PI*(1-2*y/2**z)))*180/Math.PI];}
 function extent(center,metres){const sw=G.offset(center,-metres,-metres),ne=G.offset(center,metres,metres);return[...sw,...ne];}
 function tileKeys(bounds){const [x0,y1]=tileAt(bounds[0],bounds[1]),[x1,y0]=tileAt(bounds[2],bounds[3]),keys=[];for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++)keys.push(x+'-'+y);return keys;}
 function merge(tiles,bounds,verified={},houses={},landedHeight=0,hdb={},refresh={},addresses={}){
  const groups=new Map();for(const tile of tiles)for(const f of tile.features){if(!G.intersects(G.bbox(f.geometry),bounds))continue;const id=f.properties.id;if(!id)continue;let group=groups.get(id);if(!group){group={...f,properties:{...f.properties},pieces:[]};groups.set(id,group);}group.pieces.push(...(f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates));}
  const features=[];for(const [key,g] of groups){let geometry=g.geometry;if(g.pieces.length>1){const merged=P.combine(g.pieces,[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2]);geometry={type:'MultiPolygon',coordinates:merged};}const candidate=verified[g.properties.osmId],v=candidate&&(!candidate.matchId||candidate.matchId===key)?candidate:null,p={...g.properties};if(v){p.floors=v.floors;p.name=v.name;p.floorSource=v.source;}
   const recent=refresh[key];
   if(recent&&recent.height&&!p.height&&!p.floors&&!p.hasParts&&!p.parent&&!p.minHeight){p.height=recent.height;p.floorSource=recent.source;p.osmRefresh=true;if(!p.name)p.name=recent.name;}
   const official=hdb[key];
   if(official&&!p.height&&!p.floors&&!p.hasParts&&!p.parent&&!p.minHeight){p.floors=official.floors;p.name=official.name;p.floorSource=official.source;p.hdbEstimate=true;}
   if(recent&&recent.floors&&!p.height&&!p.floors&&!p.hasParts&&!p.parent&&!p.minHeight){p.floors=recent.floors;p.floorSource=recent.source;p.osmRefresh=true;if(!p.name)p.name=recent.name;}
   const own=addresses[key]||{},parentAddress=p.parent?addresses[p.parent]:null;
   const a=own.address?own:parentAddress?.address?parentAddress:own;
   p.lookupQueries=own.lookupQueries||parentAddress?.lookupQueries||[];
   if(a.address){p.address=a.address;p.addressSource=a.source;p.addressInherited=a!==own;}
   if(own.name&&!v)p.name=own.name;
   if(!p.name&&a.name)p.name=a.name;
   if(!p.name&&own.block)p.name='Block '+own.block;
   if(!p.address&&official?.address){p.address=official.address.replace('|',' ');p.addressSource=official.source;}
   const h=G.heightInfo(p);let base=Number(p.minHeight)||0;
   const houseType=houses[key]||own.houseType||(p.parent&&(houses[p.parent]||addresses[p.parent]?.houseType||(['house','detached','semidetached_house','terrace','bungalow'].includes(groups.get(p.parent)?.properties.class)?groups.get(p.parent).properties.class:null)))||(['house','detached','semidetached_house','terrace','bungalow'].includes(p.class)?p.class:null);if(houseType){p.houseType=houseType;if(!p.name)p.name='Landed home';}
   // Overture defines height as bottom-to-top distance, min_height as ground-to-bottom.
   // Ambiguous elevated source parts are excluded until a user supplies roof height above ground.
   if(base>0){h.height=null;h.quality='unknown';h.source='Elevated part: roof elevation requires verification. No modelled shadow.';}
   if(p.hasParts){h.height=null;h.quality='outline';h.source='Overall outline. Individual building parts are modelled separately.';}
   if(v&&h.quality==='derived')h.source=v.sourceDescription||v.floors+' storeys verified by CDL; × 3 m is an estimate, not measured height.';
   if(p.hdbEstimate&&h.quality==='derived')h.source=`HDB maximum floor level ${p.floors} × 3 m; estimated height, not a measured roof. HDB data through December 2025. Exact address and matched footprint; lower wings and roof structures are not resolved.`;
   if(p.osmRefresh){const checked=recent?.checked||'2026-09-16';h.source=h.quality==='tagged'?`Height recorded in OpenStreetMap, checked ${checked}. Not independently surveyed.`:`${p.floors} storeys recorded in OpenStreetMap, checked ${checked}; × 3 m is an estimated height. Roof profiles and ground levels are not measured.`;}
   if(p.currentOutline)h.source+=' Outline updated from OpenStreetMap (15 September 2026); source mapping is not a survey.';
   else if(p.originalOutline)h.source+=' Outline restored from original Overture 2026-08-19.0 data; not independently surveyed.';
   if(houseType){h.height=null;h.quality='landed';h.source='Landed home shown as a flat footprint. 3D height and shadows are excluded.';p.landedFlat=true;base=0;}
   Object.assign(p,h,{key,baseHeight:base,originalHeight:h.height,originalQuality:h.quality,originalSource:h.source});
   features.push({type:'Feature',id:features.length,geometry,properties:p});
  }return features;
 }
 const api={tileAt,tileCorner,extent,tileKeys,merge};if(typeof module==='object')module.exports=api;else root.BuildingData=api;
})(typeof window==='object'?window:globalThis);
