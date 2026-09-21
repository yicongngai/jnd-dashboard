/* Fit the embedded study without nested scrolling; standalone layout is unchanged. */
(() => {
  if (!document.documentElement.classList.contains('embedded') || parent === window) return;
  let previous = 0, pending = false;
  function report() {
    pending = false;
    const height = Math.ceil(document.body.getBoundingClientRect().height);
    if (height > 0 && height !== previous) {
      previous = height;
      parent.postMessage({type: 'jnd-sun-height', height}, location.origin);
    }
  }
  function schedule() {
    if (!pending) { pending = true; requestAnimationFrame(report); }
  }
  new ResizeObserver(schedule).observe(document.body);
  window.addEventListener('load', schedule);
  window.addEventListener('message', event => {
    if (event.origin === location.origin && event.source === parent && event.data?.type === 'jnd-sun-visibility' && event.data.visible) schedule();
  });
  schedule();
})();
