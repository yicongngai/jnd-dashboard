/* Prepare the existing iframe near the Property map; keep its full scene for tab switches. */
(() => {
 const panel=document.getElementById('gm-view-sun'),frame=document.getElementById('gm-sun-frame'),card=document.getElementById('property-map'),button=document.querySelector('#gm-mode [data-mode="sun"]');
 if(!panel||!frame||!card||!button)return;
 let near=false,idle=null,started=false;
 const style=document.createElement('style');
 style.textContent='#gm-view-sun[data-preparing]{display:block!important;position:fixed;left:0;top:0;width:var(--sun-warm-width);opacity:0;pointer-events:none;z-index:-1}';
 document.head.append(style);
 function reveal(){panel.removeAttribute('data-preparing');panel.inert=false;panel.removeAttribute('aria-hidden');panel.style.removeProperty('--sun-warm-width');}
 function start(intent=false){
  if(started||document.hidden||(!intent&&!near))return;
  if(frame.getAttribute('src')){started=true;return;}
  const host=panel.parentElement,css=getComputedStyle(host),width=host.clientWidth-parseFloat(css.paddingLeft||0)-parseFloat(css.paddingRight||0);
  if(width<250)return; // The Market Pulse card has not been laid out yet.
  started=true;
  if(button.getAttribute('aria-pressed')!=='true'){
   panel.style.setProperty('--sun-warm-width',width+'px');panel.setAttribute('data-preparing','');panel.inert=true;panel.setAttribute('aria-hidden','true');
  }
  frame.loading='eager';frame.src=frame.dataset.src;
  frame.dataset.prepared='true';
 }
 function schedule(){
  if(started||idle!==null||!near||document.hidden||navigator.connection?.saveData)return;
  const run=()=>{idle=null;start();};
  idle=window.requestIdleCallback?requestIdleCallback(run,{timeout:1500}):setTimeout(run,250);
 }
 button.addEventListener('pointerenter',()=>start(true));button.addEventListener('focus',()=>start(true));
 button.addEventListener('click',()=>{reveal();frame.loading='eager';},true);
 new MutationObserver(()=>{if(button.getAttribute('aria-pressed')==='true')reveal();}).observe(button,{attributes:true,attributeFilter:['aria-pressed']});
 if('IntersectionObserver' in window){new IntersectionObserver(entries=>{near=entries.some(e=>e.isIntersecting);schedule();},{rootMargin:'600px'}).observe(card);}
 document.addEventListener('visibilitychange',schedule);
})();
