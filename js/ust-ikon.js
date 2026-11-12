/* id: ust-ikon-v101 */ try {
(function(){
  try{
    MODES.full.ic='<path class="f" d="M4 9.5h3.2L12 5.6v12.8l-4.8-3.9H4a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1z"/><path d="M15.6 9.2a4 4 0 0 1 0 5.6M18.4 6.6a7.6 7.6 0 0 1 0 10.8"/>';
    MODES.vib.ic='<rect x="8.2" y="3.6" width="7.6" height="16.8" rx="2.2"/><path d="M11 17.2h2M4.6 9v6M2.6 10.6v2.8M19.4 9v6M21.4 10.6v2.8"/>';
    MODES.mute.ic='<path class="f" d="M4 9.5h3.2L12 5.6v12.8l-4.8-3.9H4a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1z"/><path d="M16 9.6l4.8 4.8M20.8 9.6 16 14.4"/>';
    if(typeof paintMode==="function") paintMode();
  }catch(e){}
  const RF='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19.2 9.6A7.6 7.6 0 0 0 5.4 7.8M4.8 14.4a7.6 7.6 0 0 0 13.8 1.8"/><path d="M5 4.2v3.8h3.8M19 19.8V16h-3.8"/></svg>';
  function paint(){ const rf=document.getElementById("hdrRefresh"); if(!rf||rf.dataset.ic101) return; const sv=rf.querySelector("svg"); if(sv){ sv.outerHTML=RF; rf.dataset.ic101="1"; } }
  paint(); setTimeout(paint,800); setTimeout(paint,2500); setTimeout(paint,6000);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: ust-ikon-v101 */
