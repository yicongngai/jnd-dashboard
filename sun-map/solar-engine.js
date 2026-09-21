(function(root){
 'use strict';
 const A=typeof module==='object'?require('./vendor/astronomy.js'):root.Astronomy;
 function position(date,lat,lon){
  if(!(date instanceof Date)||!Number.isFinite(date.getTime())||!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)throw new Error('Invalid solar inputs');
  const observer=new A.Observer(lat,lon,0),eq=A.Equator('Sun',date,observer,true,true),h=A.Horizon(date,observer,eq.ra,eq.dec);
  return {altitude:h.altitude,bearing:h.azimuth};
 }
 function validDate(value){if(!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;const d=new Date(value+'T12:00:00Z');return Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===value&&Number(value.slice(0,4))>=2000&&Number(value.slice(0,4))<=2100;}
 function instant(day,minutes){if(!validDate(day)||!Number.isInteger(minutes)||minutes<0||minutes>1439)throw new Error('Choose a date from 2000–2100 and a valid Singapore time.');return new Date(new Date(day+'T00:00:00+08:00').getTime()+minutes*60000);}
 function events(day,lat,lon){const start=instant(day,0),observer=new A.Observer(lat,lon,0);return {sunrise:A.SearchRiseSet('Sun',observer,1,start,1)?.date??null,sunset:A.SearchRiseSet('Sun',observer,-1,start,1)?.date??null};}
 const api={position,instant,events,validDate};if(typeof module==='object')module.exports=api;else root.SolarEngine=api;
})(typeof window==='object'?window:globalThis);
