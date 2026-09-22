/* Render public source metadata as text, never as source-supplied HTML. */
(async()=>{
 const checked=document.getElementById('checked'),container=document.getElementById('projects');
 const node=(tag,text,parent)=>{const e=document.createElement(tag);e.textContent=text;if(parent)parent.append(e);return e;};
 const link=(text,url,parent)=>{const a=node('a',text,parent);if(url.startsWith('https://jndtoolkit.com/launch/'))a.href=url;return a;};
 const labels={'current':'Model matches published sources','review-required':'Model review needed','awaiting-model':'Site plan released · Model pending','awaiting-site-plan':'Awaiting site plan','source-unavailable':'Source needs attention'};
 try{
  const response=await fetch('data/launch-updates.json',{cache:'no-cache'});if(!response.ok)throw Error('Unavailable');const data=await response.json();
  checked.textContent='Last checked: '+new Date(data.checkedAt).toLocaleString('en-SG',{timeZone:'Asia/Singapore',dateStyle:'medium',timeStyle:'short'})+' SGT · '+data.projects.length+' published launches connected.';
  for(const p of data.projects){
   const card=node('article','',container);card.className='panel update-card';const badge=node('span',labels[p.status]||'Review pending',card);badge.className='badge';
   node('h2',p.name,card);node('p',p.message,card);
   if(!p.located)node('p','Location verification pending. No map marker has been placed.',card);
   const facts=node('p',[p.buildingFacts.address,p.buildingFacts.towers].filter(Boolean).join(' · '),card);facts.className='facts';
   link('Open latest launch slides ↗',p.url,card);
   node('small','Published source: '+(p.sourceUpdatedAt?.slice(0,10)||'date unavailable')+' · Model: '+(p.modelAsOf||'not yet checked'),card);
   const details=node('details','',card);node('summary','Plans and source version',details);const list=node('ul','',details);
   for(const source of p.geometrySources){const li=node('li','',list);link(source.file+' ↗',source.url,li);node('small','SHA-256',li);node('code',source.sha256,li);}
   if(!p.geometrySources.length)node('li','No published geometry asset found yet.',list);
   for(const missing of p.missingAssets)node('li','Missing source: '+missing,list);
   node('small','Geometry source version',details);node('code',p.sourceFingerprint,details);
  }
 }catch{checked.textContent='Launch update status is unavailable. Reload this page to retry.';}
})();
