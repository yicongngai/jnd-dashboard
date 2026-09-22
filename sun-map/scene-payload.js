/* Keep complete source records in the app; send only fields consumed by each engine. */
(function(root){
 function render(features,estimates){return features.map(f=>({type:'Feature',id:f.id,geometry:f.geometry,properties:{
  renderHeight:f.properties.height&&(estimates||f.properties.quality!=='derived')?f.properties.height:0,
  baseHeight:f.properties.baseHeight,quality:f.properties.quality,future:Boolean(f.properties.future)
 }}));}
 function shadows(features){return features.filter(f=>f.properties.height).map(f=>({type:'Feature',geometry:f.geometry,properties:{
  height:f.properties.height,minHeight:f.properties.minHeight,quality:f.properties.quality
 }}));}
 const api={render,shadows};if(typeof module==='object')module.exports=api;else root.ScenePayload=api;
})(typeof window==='object'?window:globalThis);
