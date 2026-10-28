/* id: kpaylas-v129 */ try {
// =====================================================================
// v129 · KUPO PAYLAŞ (futbol + basket) — KUPO ekranında her KUPO'nun altında "Paylaş", ayrıca "Seç" → Tümünü seç → seçilenleri tek metin olarak paylaş.
// • KUPO'lar ekranındayken açık KUPO'lar, Eski KUPO'larım'dayken biten/arşivlenen KUPO'lar listelenir. At KUPO'ları burada değil (kpaylas-at-v129).
// • Metin kuponum-v95'in kendi paylaş metni (window.kxShareText). navigator.share varsa o; yoksa panoya kopyalanır + bildirim.
// • Veri yalnız telefonda (localStorage "bx-kuponlar"); hiçbir sunucuya gönderilmez.
// =====================================================================
(function(){
  const $$=id=>document.getElementById(id);
  const SHI='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12M8 7l4-4 4 4"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg>';
  const CKI='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5 10 17 19 7"/></svg>';
  // ortak paylaşım (at bloğu da kullanır): önce telefonun paylaşım menüsü, yoksa panoya kopyala
  async function kpShare(title,text){ let url=""; try{ url=appLink(); }catch(e){}
    if(navigator.share){ try{ await navigator.share(url?{title,text,url}:{title,text}); return true; }catch(e){ if(e&&e.name==="AbortError") return false; } }
    const full=text+(url?"\n"+url:"");
    try{ await navigator.clipboard.writeText(full); toast("Kopyalandı · istediğin yere yapıştır"); return true; }catch(e){}
    try{ const ta=document.createElement("textarea"); ta.value=full; ta.setAttribute("readonly",""); ta.style.cssText="position:fixed;top:0;left:0;opacity:0"; document.body.appendChild(ta); ta.select(); const ok=document.execCommand("copy"); ta.remove(); if(ok){ toast("Kopyalandı · istediğin yere yapıştır"); return true; } }catch(e){}
    toast("Paylaşılamadı · KUPO'yu açıp tekrar dene"); return false; }
  window.kpShare=kpShare;
  window.kpJoin=function(T,legal){ const L=T.map(t=>String(t).replace(/\n[^\n]*$/,"")); return L.length===1?T[0]:`🏆 OXXai · ${L.length} KUPO\n\n`+L.join("\n\n")+`\n\n${legal}`; };
  const isAt=c=>!!c&&c.spor==="at";
  const tab=()=>{ try{ return KP.tab||"cp"; }catch(e){ return "cp"; } };
  const S={sel:false,pick:new Set()};
  function list(){ const K=(window.KX&&window.KX.L)||[], t=tab(), L=K.filter(c=>c&&!isAt(c)&&Array.isArray(c.items)&&c.items.length);
    if(t==="cp") return L.filter(c=>c.durum==="acik").sort((a,b)=>a.olusturma-b.olusturma);
    if(t==="eski") return L.filter(c=>c.durum!=="acik").sort((a,b)=>(b.bitti||b.arsivAt||b.olusturma)-(a.bitti||a.arsivAt||a.olusturma));
    return []; }
  function st(c){ const I=c.items; if(I.some(x=>x.ok===false)) return "Tutmadı"; if(I.every(x=>x.ok===true)) return "Tuttu"; return c.durum==="arsiv"?"Arşivde":"Bekliyor"; }
  function meta(c){ const bk=c.items.filter(x=>x.sp==="bk").length, fb=c.items.length-bk;
    return [fb?`⚽ ${fb} maç`:"",bk?`🏀 ${bk} maç`:"",st(c)].filter(Boolean).join(" · "); }
  const pv=c=>c.items.slice(0,2).map(x=>`${x.h} – ${x.a}`).join(", ")+(c.items.length>2?` +${c.items.length-2}`:"");
  function html(L){ const n=[...S.pick].filter(id=>L.some(c=>c.id===id)).length, all=L.length&&n===L.length, t=tab();
    return `<div class="kp-hd"><div><b>${t==="eski"?"Eski KUPO'larını paylaş":"KUPO'larını paylaş"}</b><small>${S.sel?`${n} / ${L.length} KUPO seçili`:"Her KUPO'yu tek tek paylaş ya da seçip birlikte gönder"}</small></div>
      ${L.length>1||S.sel?`<button type="button" class="kp-tg" data-kpf="sel" aria-pressed="${S.sel}">${S.sel?"Vazgeç":"Seç"}</button>`:""}</div>
      ${S.sel?`<div class="kp-bar"><button type="button" data-kpf="all">${all?"Seçimi kaldır":"Tümünü seç"}</button><button type="button" class="kp-go" data-kpf="go" ${n?"":"disabled"}>${SHI.replace('aria-hidden','style="width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;vertical-align:-3px;margin-right:4px" aria-hidden')}Seçilenleri paylaş (${n})</button></div>`:""}
      ${L.map(c=>{ const on=S.pick.has(c.id); return `<div class="kp-r${S.sel&&on?" on":""}" data-c="${esc(c.id)}"><div class="kp-rt">${S.sel?`<button type="button" class="kp-ck" role="checkbox" aria-checked="${on}" data-kpf="ck" data-c="${esc(c.id)}" aria-label="${esc(c.ad)} seç">${CKI}</button>`:""}
        <div class="kp-tx"><b>${esc(c.ad)}</b><small>${esc(meta(c))}</small><i>${esc(pv(c))}</i></div></div>
        <button type="button" class="kp-sh" data-kpf="one" data-c="${esc(c.id)}" aria-label="${esc(c.ad)} KUPO'sunu paylaş">${SHI}Paylaş</button></div>`; }).join("")}
      <p class="kp-nt">Paylaşılan metin yalnızca tahminleri içerir. KUPO'ların bu telefonda kalır; hiçbir yere yüklenmez.</p>`; }
  const sig=L=>tab()+"|"+S.sel+"|"+[...S.pick].join(",")+"|"+L.map(c=>c.id+":"+c.ad+":"+(c.upd||0)+":"+c.items.map(x=>x.ok==null?"-":x.ok?1:0).join("")).join(",");
  function place(p){ const t=tab(), cb=$$("cpBox"), od=$("kxOld");
    if(t==="cp"&&cb){ if(cb.nextElementSibling!==p) cb.after(p); } else if(t==="eski"&&od){ if(od.previousElementSibling!==p) od.before(p); } }
  function $(id){ return $$(id); }
  function paint(){ try{ const v=$$("v-kupon"); if(!v||!$$("cpBox")) return; let p=$$("kpF");
      if(!p){ p=document.createElement("section"); p.id="kpF"; p.className="kp-pan"; p.setAttribute("aria-label","KUPO paylaş"); }
      const L=list(); place(p); if(!p.isConnected) return;
      if(!L.length){ if(!p.hidden) p.hidden=true; p.dataset.s=""; return; }
      if(p.hidden) p.hidden=false; const s=sig(L); if(p.dataset.s===s) return; p.dataset.s=s; p.innerHTML=html(L);
    }catch(e){ console.error(e); } }
  let T=null; const later=()=>{ clearTimeout(T); T=setTimeout(paint,60); };
  window.kpPaintF=paint;
  document.addEventListener("click",e=>{ const b=e.target.closest("[data-kpf]"); if(!b||!b.closest("#kpF")) return; e.preventDefault(); e.stopPropagation(); try{ buzz(6); }catch(_){}
    const a=b.dataset.kpf, L=list(), K=(window.KX&&window.KX.L)||[];
    if(a==="sel"){ S.sel=!S.sel; S.pick.clear(); paint(); return; }
    if(a==="ck"){ const id=b.dataset.c; S.pick.has(id)?S.pick.delete(id):S.pick.add(id); paint(); return; }
    if(a==="all"){ const all=L.length&&L.every(c=>S.pick.has(c.id)); S.pick.clear(); if(!all) L.forEach(c=>S.pick.add(c.id)); paint(); return; }
    if(a==="one"){ const c=K.find(x=>x.id===b.dataset.c); if(!c||typeof window.kxShareText!=="function") return; kpShare(`${c.ad} · OXXai`,window.kxShareText(c)); return; }
    if(a==="go"){ const C=L.filter(c=>S.pick.has(c.id)); if(!C.length){ toast("Önce paylaşmak istediğin KUPO'ları seç"); return; } if(typeof window.kxShareText!=="function") return;
      kpShare(C.length===1?`${C[0].ad} · OXXai`:`${C.length} KUPO · OXXai`,window.kpJoin(C.map(c=>window.kxShareText(c)),LEGAL_SHARE)); return; }
  },true);
  // sekme değişince seçim sıfırlanır
  document.addEventListener("click",e=>{ if(e.target.closest("#kxSeg [data-kt]")){ S.sel=false; S.pick.clear(); } later(); },true);
  let mo=null; function hook(){ const v=$$("v-kupon"); if(!v||mo) return; mo=new MutationObserver(R=>{ if(R.every(r=>r.target.closest&&r.target.closest(".kp-pan"))) return; later(); }); mo.observe(v,{childList:true,subtree:true,attributes:true,attributeFilter:["hidden"]}); later(); }
  hook(); setTimeout(hook,1500);
  try{ const _s=window.kxSave; if(typeof _s==="function") window.kxSave=function(){ const r=_s.apply(this,arguments); later(); return r; }; }catch(e){}
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: kpaylas-v129 */
/* id: kpaylas-at-v129 */ try {
// =====================================================================
// v129 · AT KUPO PAYLAŞ — futbol paylaş listesinden ayrı. Her at KUPO'sunun altında "Paylaş" + çoklu seçim.
// • KUPO ekranı (#kpA: KUPO'larım = açık, Eski KUPO'larım = biten) ve At › KUPO sekmesi (#kpAt: açık + eski).
// • Metin atkupon-v98'in paylaş metni (window.atkShareText). Veri yalnız telefonda; sunucuya gönderilmez.
// =====================================================================
(function(){
  const $$=id=>document.getElementById(id);
  const SHI='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12M8 7l4-4 4 4"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg>';
  const CKI='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5 10 17 19 7"/></svg>';
  const LEGAL="Hobi amaçlı olasılık; garanti değildir · 18+";
  const isAt=c=>!!c&&c.spor==="at";
  const share=(t,x)=>window.kpShare?window.kpShare(t,x):(navigator.share?navigator.share({title:t,text:x}).catch(()=>{}):navigator.clipboard.writeText(x).then(()=>toast("Kopyalandı")).catch(()=>{}));
  const join=T=>window.kpJoin?window.kpJoin(T,LEGAL):T.join("\n\n");
  const ST={}; const S=k=>ST[k]||(ST[k]={sel:false,pick:new Set()});
  const all=()=>((window.KX&&window.KX.L)||[]).filter(c=>isAt(c)&&Array.isArray(c.at)&&c.at.length);
  const opens=()=>all().filter(c=>c.durum==="acik").sort((a,b)=>a.olusturma-b.olusturma);
  const pasts=()=>all().filter(c=>c.durum!=="acik").sort((a,b)=>(b.bitti||b.arsivAt||b.olusturma)-(a.bitti||a.arsivAt||a.olusturma));
  const ktab=()=>{ try{ return KP.tab||"cp"; }catch(e){ return "cp"; } };
  function list(k){ if(k==="kpAt") return opens().concat(pasts().slice(0,30)); const t=ktab(); return t==="cp"?opens():t==="eski"?pasts():[]; }
  function st(c){ const I=c.at; if(I.some(x=>x.ok===false)) return "Tutmadı"; const L=I.filter(x=>!x.iade); if(L.length&&L.every(x=>x.ok===true)) return "Tuttu"; return c.durum==="arsiv"?"Arşivde":c.durum!=="acik"?"Bitti":"Bekliyor"; }
  const ks=x=>x.tur==="altili"?`${x.kosu}.–${(+x.kosu||0)+5}. koşular`:x.tur==="cifte"?`${x.kosu}.+${(+x.kosu||0)+1}. koşu`:`${x.kosu}. koşu`;
  const pv=c=>c.at.slice(0,2).map(x=>`${x.hip||""} ${ks(x)}`.trim()).join(", ")+(c.at.length>2?` +${c.at.length-2}`:"");
  function html(k,L){ const s=S(k), n=[...s.pick].filter(id=>L.some(c=>c.id===id)).length, al=L.length&&n===L.length;
    return `<div class="kp-hd"><div><b>🐎 At KUPO'larını paylaş</b><small>${s.sel?`${n} / ${L.length} KUPO seçili`:"Her at KUPO'sunu tek tek paylaş ya da seçip birlikte gönder"}</small></div>
      ${L.length>1||s.sel?`<button type="button" class="kp-tg" data-kpa="sel" aria-pressed="${s.sel}">${s.sel?"Vazgeç":"Seç"}</button>`:""}</div>
      ${s.sel?`<div class="kp-bar"><button type="button" data-kpa="all">${al?"Seçimi kaldır":"Tümünü seç"}</button><button type="button" class="kp-go" data-kpa="go" ${n?"":"disabled"}>Seçilenleri paylaş (${n})</button></div>`:""}
      ${L.map(c=>{ const on=s.pick.has(c.id); return `<div class="kp-r${s.sel&&on?" on":""}" data-c="${esc(c.id)}"><div class="kp-rt">${s.sel?`<button type="button" class="kp-ck" role="checkbox" aria-checked="${on}" data-kpa="ck" data-c="${esc(c.id)}" aria-label="${esc(c.ad)} seç">${CKI}</button>`:""}
        <div class="kp-tx"><b>${esc(c.ad)}</b><small>🐎 ${c.at.length} satır · ${esc(st(c))}</small><i>${esc(pv(c))}</i></div></div>
        <button type="button" class="kp-sh" data-kpa="one" data-c="${esc(c.id)}" aria-label="${esc(c.ad)} KUPO'sunu paylaş">${SHI}Paylaş</button></div>`; }).join("")}
      <p class="kp-nt">Paylaşılan metin yalnızca tahminleri içerir. KUPO'ların bu telefonda kalır; hiçbir yere yüklenmez.</p>`; }
  const sig=(k,L)=>(k==="kpA"?ktab():"")+"|"+S(k).sel+"|"+[...S(k).pick].join(",")+"|"+L.map(c=>c.id+":"+c.ad+":"+c.durum+":"+(c.upd||0)+":"+c.at.map(x=>x.ok==null?"-":x.ok?1:0).join("")).join(",");
  function fill(p,k){ const L=list(k); if(!L.length){ if(!p.hidden) p.hidden=true; p.dataset.s=""; return; } if(p.hidden) p.hidden=false; const s=sig(k,L); if(p.dataset.s===s) return; p.dataset.s=s; p.innerHTML=html(k,L); }
  function mk(id){ let p=$$(id); if(!p){ p=document.createElement("section"); p.id=id; p.className="kp-pan"; p.setAttribute("aria-label","At KUPO paylaş"); } return p; }
  // KUPO ekranı: futbol panelinin hemen altı (yoksa cpBox / kxOld komşusu)
  function paintK(){ try{ const v=$$("v-kupon"), cb=$$("cpBox"); if(!v||!cb) return; const p=mk("kpA"), t=ktab(), f=$$("kpF"), od=$$("kxOld");
      const anc=f&&f.isConnected?f:t==="eski"?null:cb;
      if(anc){ if(anc.nextElementSibling!==p) anc.after(p); } else if(od){ if(od.previousElementSibling!==p) od.before(p); }
      if(p.isConnected) fill(p,"kpA"); }catch(e){ console.error(e); } }
  // At › KUPO sekmesi: KUPO kartının altı
  function paintAt(){ try{ const box=$$("at2Box"), v=$$("v-at"); if(!box) return; const on=/^#at\/kupon(\/|$)/.test(location.hash||"")&&v&&!v.hidden&&box.querySelector(":scope > .a3-k");
      let p=$$("kpAt"); if(!on){ if(p) p.remove(); return; } p=mk("kpAt");
      const anc=box.querySelector(":scope > .a3-cp")||box.querySelector(":scope > .a2-empty")||box.querySelector(":scope > .a3-sw");
      if(anc){ if(anc.nextElementSibling!==p) anc.after(p); } else if(p.parentNode!==box) box.appendChild(p);
      fill(p,"kpAt"); }catch(e){ console.error(e); } }
  let T=null; const later=()=>{ clearTimeout(T); T=setTimeout(()=>{ paintK(); paintAt(); },70); };
  document.addEventListener("click",e=>{ const b=e.target.closest("[data-kpa]"); const p=b&&b.closest("#kpA,#kpAt"); if(!p) return; e.preventDefault(); e.stopPropagation(); try{ buzz(6); }catch(_){}
    const k=p.id, s=S(k), a=b.dataset.kpa, L=list(k), redo=()=>{ p.dataset.s=""; fill(p,k); };
    if(a==="sel"){ s.sel=!s.sel; s.pick.clear(); redo(); return; }
    if(a==="ck"){ const id=b.dataset.c; s.pick.has(id)?s.pick.delete(id):s.pick.add(id); redo(); return; }
    if(a==="all"){ const al=L.length&&L.every(c=>s.pick.has(c.id)); s.pick.clear(); if(!al) L.forEach(c=>s.pick.add(c.id)); redo(); return; }
    if(typeof window.atkShareText!=="function"){ toast("At KUPO'su henüz yüklenmedi; birazdan tekrar dene"); return; }
    if(a==="one"){ const c=all().find(x=>x.id===b.dataset.c); if(c) share(`${c.ad} · OXXai`,window.atkShareText(c)); return; }
    if(a==="go"){ const C=L.filter(c=>s.pick.has(c.id)); if(!C.length){ toast("Önce paylaşmak istediğin KUPO'ları seç"); return; }
      share(C.length===1?`${C[0].ad} · OXXai`:`${C.length} at KUPO'su · OXXai`,join(C.map(c=>window.atkShareText(c)))); return; }
  },true);
  document.addEventListener("click",e=>{ if(e.target.closest("#kxSeg [data-kt]")){ const s=S("kpA"); s.sel=false; s.pick.clear(); } later(); },true);
  window.addEventListener("hashchange",later);
  const obs=(el,o)=>new MutationObserver(R=>{ if(R.every(r=>r.target.closest&&r.target.closest(".kp-pan"))&&R.every(r=>![...r.addedNodes].some(n=>n.classList&&n.classList.contains("kp-pan")))) return; later(); }).observe(el,o);
  let h1=0,h2=0; function hook(){ const v=$$("v-kupon"), b=$$("at2Box"); if(v&&!h1){ h1=1; obs(v,{childList:true,subtree:true,attributes:true,attributeFilter:["hidden"]}); } if(b&&!h2){ h2=1; obs(b,{childList:true}); } later(); }
  hook(); setTimeout(hook,1500); setTimeout(hook,4500);
  try{ const _s=window.kxSave; if(typeof _s==="function") window.kxSave=function(){ const r=_s.apply(this,arguments); later(); return r; }; }catch(e){}
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: kpaylas-at-v129 */
/* id: oransiz-kupa-v132 */ try {
// v132: Bültende MS oranı kapalı (dev favori kupa maçı) ve lig modeli olmayan maç: maç listede görünür, uydurma tahmin gösterilmez
(function(){ try{
  const bos=f=>!!(f&&f.src==="iddaa"&&String(f.lg||"").startsWith("i")&&!f.odds&&!f.io&&!(f.kp&&f.kp.length===3));
  if(typeof quickPred==="function"){ const _q=quickPred; quickPred=function(m,f){ if(bos(f)) return null; return _q.apply(this,arguments); }; }
  if(typeof fullPred==="function"){ const _f=fullPred; fullPred=function(m,f){ if(bos(f)) return null; return _f.apply(this,arguments); }; }
}catch(e){} })();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: oransiz-kupa-v132 */
/* id: canli-coklu-v133 */ try {
// v133 · Canlı maçta 2. (ve sonraki) tahmin + ilk yarı gol tahmini
// • Maç öncesi modeli ve maç öncesi oranı olmayan maç (ör. Azerbaycan Kupası, lig "i"+ci): canlı gol beklentisi artık
//   iddaa canlı oranlarından (MS 1/X/2, Alt/Üst; marj ayıklanır) geri çözülür; canlı oran da yoksa lig ortalaması (1,45 / 1,15).
//   Hesap dakika, skor ve kırmızı kartla canlı modelde (canli-gt-v107 core) yapılır.
// • Başlamış maç penceresi canlı eşini takım adından da bulur (fikstür kaydında iid yoksa "tahmin hesaplanamadı" kalmaz).
(function(){ "use strict";
  const C=new Map();
  function pois(l,K){ const o=[]; let p=Math.exp(-l); for(let k=0;k<=K;k++){ o.push(p); p*=l/(k+1); } return o; }
  // kalan sürede (rem payı) LH/LA ile 1/X/2 ve Üst olasılığı; skor durumu etkisi yok (geri çözüm için yeterli)
  function fwd(lh,la,hs,as,rem,line){ const PH=pois(lh*rem,8), PA=pois(la*rem,8); let H=0,D=0,A=0,O=0; const tot=hs+as;
    for(let i=0;i<=8;i++) for(let j=0;j<=8;j++){ const p=PH[i]*PA[j], a=hs+i, b=as+j; if(a>b)H+=p; else if(a===b)D+=p; else A+=p; if(line!=null&&tot+i+j>line) O+=p; }
    const z=H+D+A||1; return {H:H/z,D:D/z,A:A/z,O}; }
  window.lvOranL=function(m){ try{ if(!m||m.sp!==1) return null; const od=m.odds||{};
      const ms=od.ms&&!od.ms.lock&&od.ms.v&&od.ms.v.length===3&&od.ms.v.every(x=>x>1)?od.ms.v:null, ou=od.ou&&!od.ou.lock&&od.ou.alt>1&&od.ou.ust>1?od.ou:null;
      if(!ms&&!ou) return null;
      const s=idlSecs(m), t=s==null?30:Math.min(120,s/60), rem=fbRemShare(t,m); if(!(rem>.02)) return null;   // maç sonuna çok az kala oran bilgisi geri çözülmez
      const hs=+m.hs||0, as=+m.as||0, key=[m.id,Math.round(t),hs,as,ms&&ms.join(),ou&&[ou.l,ou.alt,ou.ust].join()].join("|");
      if(C.has(key)) return C.get(key);
      let q=null; if(ms){ const r=ms.map(x=>1/x), z=r[0]+r[1]+r[2]; q=r.map(x=>x/z); }
      let po=null; if(ou){ const a=1/ou.alt, b=1/ou.ust; po=b/(a+b); }
      let best=null;
      for(let T=1.2;T<=4.61;T+=.1) for(let sh=.2;sh<=.801;sh+=.025){ if(!ms&&Math.abs(sh-.56)>.013) continue;
        const F=fwd(T*sh,T*(1-sh),hs,as,rem,ou?ou.l:null); let e=0;
        if(q) e+=(F.H-q[0])**2+(F.D-q[1])**2+(F.A-q[2])**2; if(po!=null) e+=(F.O-po)**2;
        if(!best||e<best.e) best={e,L:[+(T*sh).toFixed(3),+(T*(1-sh)).toFixed(3)]}; }
      const L=best&&best.e<.05?best.L:null; if(C.size>400) C.clear(); C.set(key,L); return L; }catch(e){ return null; } };
  // başlamış maç penceresi: canlı eş iid ile bulunamadıysa takım adlarıyla
  try{ const _om=openMatch; openMatch=function(m,tab){ const r=_om.apply(this,arguments);
      try{ if(MS.m===m&&!MS.live&&m&&!m.sp){ const t=m.dt&&m.dt.getTime?m.dt.getTime():NaN;
          if(isFinite(t)&&t<Date.now()&&t>Date.now()-3*3600e3){ const find=()=>(IDL.live&&IDL.live[1]||[]).find(x=>tmEq(x.h,m.h)&&tmEq(x.a,m.a))||null;
            const go=()=>{ const lv=find(); if(lv&&MS.m===m&&!MS.live){ MS.live=lv; msRender(); } };
            if(find()) go(); else if(typeof IDL.load==="function"&&Date.now()-(IDL.at[1]||0)>15000) IDL.load(1).then(go).catch(()=>{}); } } }catch(e){}
      return r; }; }catch(e){}
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: canli-coklu-v133 */
/* id: canli-nabiz-v134 */ try {
// =====================================================================
// OXXai v134 · CANLI NABIZ: canlı skor ekranda anlık güncellenir
// Kök neden (şikâyet "canlı maç izlerken skor değişmiyor"): açık maç penceresi (openMatch → msRender) açılış anındaki
// IDL nesnesinin kopyasını (MS.live) çiziyordu; IDL.load her yenilemede yeni nesneler ürettiği için pencere yalnız
// "↻ Güncel tahmin"e basınca tazeleniyordu. Bülten (Takip/arama) ve KUPO canlı satırları da 60–120 sn'lik döngülere kalıyordu.
// Çözüm: sayfa görünürken 15 sn'de bir (yalnız canlı bir yüzey ekrandayken) iddaa canlı bülteni tazelenir ve
//  • açık maç penceresi yeni veriye bağlanır; skor/kart/devre değişince yeniden çizilir (kaydırma yeri korunur),
//  • Canlı sekmesi dışındaki canlı satırların (.lv-c) skor ve dakikası yerinde güncellenir, KUPO canlı satırları yeniden bezenir.
// Sayfa gizliyken çalışmaz (everyVisible); görünür olunca hemen bir tur atar. Canlı sekmesinin kendi 10 sn döngüsü değişmez.
// =====================================================================
(function(){ "use strict";
  const PER=15000;
  const sig=m=>m?[m.hs,m.as,(m.rc||[]).join(","),m.st].join("|"):"";
  const vis=id=>{ const v=document.getElementById(id); return !!(v&&!v.hidden); };
  const msOpen=()=>{ const el=document.getElementById("msheet"); return !!(el&&!el.hidden&&typeof MS!=="undefined"&&MS.m); };
  const tms=d=>{ try{ const t=d&&d.getTime?d.getTime():Date.parse(d); return isFinite(t)?t:NaN; }catch(e){ return NaN; } };
  function msStarted(){ const m=MS.m; if(!m) return false; if(m.sp||MS.live) return true; const t=tms(m.dt); return isFinite(t)&&t<Date.now()+60e3&&t>Date.now()-3*3600e3; }
  function msFind(){ const m=MS.m, by=(IDL.byId&&IDL.byId[1])||{};
    if(MS.live&&MS.live.sp===1) return by[MS.live.id]||null;
    if(m&&m.sp===1) return by[m.id]||null;
    if(m&&m.iid&&by[m.iid]) return by[m.iid];
    try{ return (IDL.live[1]||[]).find(x=>tmEq(x.h,m.h)&&tmEq(x.a,m.a))||null; }catch(e){ return null; } }
  function msUpdate(){ if(!msOpen()||!msStarted()) return;
    const nw=msFind(); if(!nw) return; const old=MS.live, ch=!old||sig(old)!==sig(nw);
    MS.live=nw; if(MS.m&&MS.m.sp===1) MS.m=nw;
    const el=document.getElementById("msheet");
    if(ch&&MS.tab!=="form"){ const sc=el.scrollTop; try{ msRender(); }catch(e){} el.scrollTop=sc; }
    else { const b=el.querySelector(".ms-sc.live b"); if(b) b.textContent=`${nw.hs}-${nw.as}`; } }
  // Canlı sekmesi dışındaki canlı satırlar (bülten takip/arama, güç sayfası vb.): skor ve dakika yerinde
  function rowsUpdate(){ const by=(IDL.byId&&IDL.byId[1])||{};
    document.querySelectorAll(".lv-c[data-id]").forEach(r=>{ if(r.closest("#idlBox")) return; const c=r.querySelector(".lclk"), sp=c?+c.dataset.sp:1; const m=(IDL.byId[sp]||by)[+r.dataset.id]; if(!m) return;
      const b=r.querySelector(".lv-sc b"), t=`${m.hs}-${m.as}`; if(b&&b.textContent!==t){ b.textContent=t; r.classList.remove("nb-gol"); void r.offsetWidth; r.classList.add("nb-gol"); } }); }
  function kupoLive(){ try{ const box=document.getElementById("cpBox"); if(!box||!box.offsetParent) return false; return (CP.items||[]).some(x=>x.ok==null&&(x.live||(tms(x.dt)<Date.now()&&tms(x.dt)>Date.now()-3*3600e3))); }catch(e){ return false; } }
  function need(){ if(document.hidden) return false;
    if(msOpen()&&msStarted()) return true;
    if(document.querySelector(".lv-c[data-id]")&&[...document.querySelectorAll(".lv-c[data-id]")].some(r=>!r.closest("#idlBox")&&r.offsetParent)) return true;
    return kupoLive(); }
  let busy=false;
  async function tick(force){ if(busy||!need()) return; busy=true;
    try{ if(typeof idlCanliVisible==="function"&&idlCanliVisible()&&!msOpen()) return;   // Canlı sekmesi kendi 10 sn döngüsüyle tazelenir
      if(force||Date.now()-(IDL.at[1]||0)>=PER-1500) await IDL.load(1,!!force);
      msUpdate(); rowsUpdate();
      try{ if(kupoLive()&&window.kxLiveDeco) window.kxLiveDeco(); }catch(e){}
    }catch(e){} finally{ busy=false; } }
  if(typeof everyVisible==="function") everyVisible(()=>tick(false),PER); else setInterval(()=>{ if(!document.hidden) tick(false); },PER);
  // arka plandan dönüş: hemen tazele (10 sn'den eskiyse); Canlı sekmesi de anında yeniden çizilir
  function back(){ if(document.hidden) return; setTimeout(()=>{ try{
      if(Date.now()-(IDL.at[1]||0)>10e3){
        if(typeof idlCanliVisible==="function"&&idlCanliVisible()) IDL.load(IDLV.sp,true).then(()=>{ idlRenderAll(); msUpdate(); });
        else tick(true); } }catch(e){} },150); }
  document.addEventListener("visibilitychange",back);
  window.addEventListener("pageshow",e=>{ if(e.persisted) back(); });
  window.addEventListener("online",back);
  // maç penceresi açılırken veri eskiyse hemen tazele
  try{ const _om=openMatch; openMatch=function(){ const r=_om.apply(this,arguments); try{ if(MS.m&&msStarted()&&Date.now()-(IDL.at[1]||0)>PER) tick(true); }catch(e){} return r; }; }catch(e){}
  window.oxxNabiz={tick,need};
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: canli-nabiz-v134 */
