/* Local suggestions are immediate; remote address lookups are debounced and cancellable. */
(function(root){
 const normal=s=>String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
 function match(query,places){
  const q=normal(query),words=q.split(' '),seen=new Set();
  return places.filter(p=>{
   const name=normal(p.name),key=name+'|'+p.lon+'|'+p.lat;
   if(seen.has(key)||!Number.isFinite(p.lon)||!Number.isFinite(p.lat))return false;
   seen.add(key);const tokens=normal(p.name+' '+(p.address||'')).split(' ');return words.every(w=>tokens.some(t=>/^\d+$/.test(w)?t===w:t.startsWith(w)));
  }).sort((a,b)=>{
   const score=p=>normal(p.name)===q?0:normal(p.name).startsWith(q)?1:2;
   return score(a)-score(b)||a.name.length-b.name.length||a.name.localeCompare(b.name);
  }).slice(0,8);
 }
 function mount({input,list,status,form,container,getPlaces,lookup,choose,document:doc=root.document}){
  let timer,controller,version=0,items=[],active=-1,lastRemote=0,composing=false;
  const cache=new Map();
  function cancel(){clearTimeout(timer);controller?.abort();version++;}
  function close(){cancel();list.replaceChildren();list.hidden=true;items=[];active=-1;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');status.textContent='';}
  function select(p){close();input.value=p.name;choose(p);}
  function highlight(index){
   active=index;
   Array.from(list.children).forEach((el,i)=>el.setAttribute('aria-selected',i===active?'true':'false'));
   if(active>=0){input.setAttribute('aria-activedescendant','location-option-'+active);list.children[active]?.scrollIntoView?.({block:'nearest'});}
   else input.removeAttribute('aria-activedescendant');
  }
  function render(found,message){
   items=found;active=-1;list.replaceChildren();input.removeAttribute('aria-activedescendant');
   for(const [i,p] of items.entries()){
    const option=doc.createElement('button');option.type='button';option.id='location-option-'+i;option.tabIndex=-1;
    option.setAttribute('role','option');option.setAttribute('aria-selected','false');
    const name=doc.createElement('span');name.textContent=p.name;option.append(name);
    if(p.address&&normal(p.address)!==normal(p.name)){const address=doc.createElement('small');address.textContent=p.address;option.append(address);}
    option.onmousedown=e=>e.preventDefault();option.onclick=()=>select(p);list.append(option);
   }
   list.hidden=!items.length;input.setAttribute('aria-expanded',String(Boolean(items.length)));
   status.className=items.length?'sr-only':'search-hint';
   status.textContent=message||(items.length?items.length+' suggestions. Use arrow keys to choose.':'No matching locations. Try a longer address.');
  }
  function search(submit=false){
   cancel();const seq=version,q=input.value.trim();
   if(q.length<2){close();return;}
   const local=match(q,getPlaces());
   if(submit&&local.length){select(local[0]);return;}
   render(local,local.length?'':'Searching addresses…');
   if(local.length)return;
   if(cache.has(normal(q))){const found=cache.get(normal(q));if(submit&&found.length)select(found[0]);else render(found);return;}
   timer=setTimeout(async()=>{
    if(seq!==version)return;
    controller=new AbortController();const abort=controller;const timeout=setTimeout(()=>abort.abort(),10000);lastRemote=Date.now();
    try{
     const found=await lookup(q,abort.signal);
     if(seq!==version)return;
     cache.set(normal(q),found);if(cache.size>100)cache.delete(cache.keys().next().value);
     if(submit&&found.length)select(found[0]);else render(found);
    }catch(error){if(seq===version)render([],'Address search unavailable. Try a condo name or another address.');}
    finally{clearTimeout(timeout);}
   },Math.max(submit?0:350,1100-(Date.now()-lastRemote)));
  }
  input.oninput=e=>{if(!composing&&!e?.isComposing)search();};
  input.oncompositionstart=()=>{composing=true;close();};input.oncompositionend=()=>{composing=false;search();};
  input.onfocus=()=>{if(input.value.trim().length>=2)search();};
  input.onkeydown=e=>{
   if(composing||e.isComposing)return;
   if(e.key==='Escape'){e.preventDefault();close();}
   if(e.key==='ArrowDown'||e.key==='ArrowUp'){
    e.preventDefault();if(!items.length)search();
    if(items.length)highlight(active<0?(e.key==='ArrowDown'?0:items.length-1):(active+(e.key==='ArrowDown'?1:-1)+items.length)%items.length);
   }
   if(e.key==='Enter'&&items.length){e.preventDefault();select(items[active<0?0:active]);}
  };
  input.onblur=e=>{if(!container.contains(e.relatedTarget))close();};
  doc.addEventListener('pointerdown',e=>{if(!container.contains(e.target))close();});
  form.onsubmit=e=>{e.preventDefault();if(items.length)select(items[active<0?0:active]);else search(true);};
  return {refresh(){if(doc.activeElement===input)search();},close};
 }
 const api={match,mount};if(typeof module==='object')module.exports=api;else root.LocationSearch=api;
})(typeof window==='object'?window:globalThis);
