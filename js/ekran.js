/* id: core-v69 */ try {
/* v69: canlı Platt kalibrasyonu (toplayıcı zaman sıralı sınamada kabul ettiyse) + karne gün sayısı dürüst */
(function(){
  const _lc=liveCal;
  liveCal=function(pp){ try{ const P=DAILY&&DAILY.canli&&DAILY.canli.platt;
      if(P&&P.kabul&&isFinite(P.a)&&isFinite(P.b)&&pp>0&&pp<1){ const x=Math.log(pp/(1-pp)); const q=1/(1+Math.exp(-(P.a+P.b*x))); let bn=null,bh=null; try{ const B=DAILY.canli.bins||[]; const k=B.find(x=>q>=x[0]&&q<x[1]&&x[2]&&x[3]!=null); if(k){ bn=k[2]; bh=k[3]; } }catch(_){} return {p:q, n:bn, h:bh, platt:true}; } }catch(e){}
    return _lc(pp); };
  tpKarne=async function(){ try{ const days=(DAILY&&DAILY.gunler||[]).filter(g=>g.n>0).map(g=>g.d).slice(-30); let n=0,h=0,g=0;
    for(const d of days){ let A=null; try{ const r=await fetch(`data/archive/${d}.json`,{cache:"no-cache"}); if(r.ok) A=await r.json(); }catch(e){} if(!A) continue; let had=0;
      for(const v of Object.values(A)){ if(v.ok==null||v.rp==null||!v.ro) continue; if(v.rp>=.70&&v.ro>=GOLD.omin&&v.ro<=GOLD.omax){ n++; had=1; if(v.ok) h++; } } g+=had; }
    TP.karne={n,h,g}; }catch(e){} };
  (function kw(i){ if(DAILY&&DAILY.gunler){ if(!TP.karne||!TP.karne.n) tpKarne().then(()=>{ try{ const v=$("v-tahmin"); if(v&&!v.hidden) renderTP(); }catch(e){} }); return; } if(i<40) setTimeout(()=>kw(i+1),1500); })(0);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: core-v69 */
/* id: ui-v70 */ try {
// =====================================================================
// OXXai v70: Üst çubuk ergonomisi + tek Yenile kapısı + tekrar eden menülerin birleşmesi
// • OXXai · Ses · Yenile: daha aşağıda, 52 px yüksek, altında adıyla; Yenile veriyi ve uygulama sürümünü birlikte tazeler
// • Sayfa içi tekrar eden "Güncelle" düğmeleri kalktı (Tahmin, Bülten ⋯, Sonuçlar) — hepsi üstteki Yenile'de
// • Kayıtlı tahminler, Tahmin listem'in üçüncü sekmesi oldu (Listem · Sonuç takibim · Kayıtlı)
// • Karne: aynı başlıklı günlük satırlar tekilleşti; "Canlı karne" adı iki farklı ölçümde kullanılmıyor
// =====================================================================
(function(){
  const lbl=(b,t)=>{ if(!b) return; let s=b.querySelector(".tbl"); if(!s){ s=document.createElement("span"); s.className="tbl"; b.appendChild(s); } s.textContent=t; };
  function hdr(){
    const tin=document.querySelector(".topbar .in"); if(!tin) return;
    const bot=$("hdrBot"), mode=$("modeBtn"); let rf=$("hdrRefresh");
    if(!rf){ rf=document.createElement("button"); rf.className="iconbtn"; rf.id="hdrRefresh"; rf.type="button"; rf.innerHTML='<svg viewBox="0 0 24 24"><path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/></svg>'; tin.appendChild(rf); }
    // sıra: OXXai · Ses · Yenile (en sağda)
    if(mode&&rf.previousElementSibling!==mode) mode.after(rf);
    if(bot&&mode&&bot.nextElementSibling!==mode) mode.before(bot);
    rf.setAttribute("aria-label","Yenile: verileri ve uygulamayı güncelle"); rf.title="Yenile";
    lbl(bot,"OXXai"); lbl(mode,"Ses"); lbl(rf,"Yenile");
    rf.onclick=v70Refresh;
  }
  async function verCheck(){ try{ const v=await oxxLatestV(true); return v&&v!==APP_V?v:null; }catch(e){ return null; } }   // v118: data/version.json
  let busy=false;
  async function v70Refresh(){
    if(busy) return; busy=true; const rf=$("hdrRefresh"); if(rf){ rf.classList.remove("ok"); rf.classList.add("spin"); }
    try{ buzz(10); }catch(e){}
    try{
      const nv=await verCheck();
      if(nv){ toast("✨ Yeni sürüm bulundu, uygulama yenileniyor…");
        try{ if(window.caches){ const ks=await caches.keys(); await Promise.all(ks.map(k=>caches.delete(k))); } }catch(e){}
        try{ const reg=navigator.serviceWorker&&await navigator.serviceWorker.getRegistration(); if(reg) await reg.update(); }catch(e){}
        setTimeout(()=>{ if(window.bxRepair) window.bxRepair(nv); else location.reload(); },500); return; }
      const jobs=[];
      try{ jobs.push(Promise.resolve(doRefresh())); }catch(e){}
      try{ if(typeof IDL!=="undefined"&&IDL.load) jobs.push(IDL.load(IDLV.sp,true).then(()=>{ try{ idlRenderAll(); idlBadge(); }catch(e){} }).catch(()=>{})); }catch(e){}
      try{ const v=$("v-sonuclar"); if(v&&!v.hidden&&typeof RS!=="undefined"){ RS.cache.delete(RS.day); jobs.push(RS.load(RS.day,true).then(()=>renderRes()).catch(()=>{})); } }catch(e){}
      await Promise.race([Promise.all(jobs),new Promise(r=>setTimeout(r,9000))]);
      try{ const v=$("v-karne"); if(v&&!v.hidden) renderKarne(); }catch(e){}
      try{ const v=$("v-power"); if(v&&!v.hidden&&typeof renderPower==="function") renderPower(); }catch(e){}
      if(rf){ rf.classList.add("ok"); setTimeout(()=>rf.classList.remove("ok"),1800); }
      toast("✅ Güncellendi · "+ist(new Date(),{hour:"2-digit",minute:"2-digit"})+" · uygulama güncel");
    }finally{ if(rf) rf.classList.remove("spin"); busy=false; }
  }
  window.v70Refresh=v70Refresh;
  hdr(); setTimeout(hdr,1200); setTimeout(hdr,4000);

  // ---- Menü: Kayıtlı tahminler → Listelerim; Analiz yalnız analiz araçları ----
  try{
    const an=MENU_PLAN.find(g=>g[0]==="Analiz"), ls=MENU_PLAN.find(g=>g[0]==="Listelerim");
    if(an&&ls){ const i=an[1].findIndex(x=>x[0]==='[data-go="sonuc"]'); if(i>=0){ const it=an[1].splice(i,1)[0]; it[2]="Kaydettiğin maç analizleri ve sonuçları"; ls[1].splice(1,0,it); } }
    if(ls){ const c=ls[1].find(x=>x[0]==="#moreCp"); if(c) c[2]="Seçtiğin tahminler, birlikte tutma olasılığı ve sonuçları"; }
    menuOrganize();
    if(IS_STANDALONE()){ const ins=document.querySelector('#v-more [data-act="install"]'); if(ins) ins.hidden=true; }
  }catch(e){}

  // ---- Tahmin listem: Listem · Sonuç takibim · Kayıtlı (tek kapı, üç sekme) ----
  function goKupon(t){ KP.tab=t; const b=document.querySelector('nav.tabs button[data-v="kupon"]'); if(b) b.click(); setTimeout(()=>{ try{ kuponTab(t); }catch(e){} },30); }
  function goSonuc(){ const b=document.querySelector('nav.tabs button[data-v="sonuc"]'); if(b) b.click(); }
  function addThird(){ const sg=$("kpSeg"); if(!sg||sg.querySelector('[data-kt="snc"]')) return;
    sg.insertAdjacentHTML("beforeend",`<button type="button" data-kt="snc" aria-pressed="false">Kayıtlı</button>`);
    sg.querySelector('[data-kt="snc"]').addEventListener("click",e=>{ e.stopPropagation(); buzz(6); goSonuc(); },true); }
  const _kt=kuponTab; kuponTab=function(t){ if(t==="snc"){ goSonuc(); return; } const r=_kt.apply(this,arguments); addThird(); return r; };
  function sncSeg(){ const v=$("v-sonuc"); if(!v||$("sncSeg")) return; const lt=v.querySelector(".ltitle");
    const html=`<div class="seg kp-seg" id="sncSeg" role="group" aria-label="Tahmin listem"><button type="button" data-k="cp">Listem</button><button type="button" data-k="oyn">Sonuç takibim</button><button type="button" data-k="snc" aria-pressed="true">Kayıtlı</button></div>`;
    lt?lt.insertAdjacentHTML("afterend",html):v.insertAdjacentHTML("afterbegin",html);
    $("sncSeg").onclick=e=>{ const b=e.target.closest("[data-k]"); if(!b||b.dataset.k==="snc") return; buzz(6); goKupon(b.dataset.k); window.scrollTo({top:0}); };
    const p=v.querySelector(".ltitle p"); if(p) p.textContent="Maç tahmini ekranında kaydettiğin analizler ve sonuçları"; }
  sncSeg(); addThird();

  // ---- Karne: aynı başlıklı günlük satırlar tekil, iki farklı "Canlı karne" adı ayrışır ----
  const _rk70=renderKarne;
  renderKarne=function(){ const r=_rk70.apply(this,arguments);
    try{ const seen=new Set(); document.querySelectorAll("#kzBox .kz-g").forEach(p=>{ const k=((p.querySelector("b")||{}).textContent||"").trim(); if(seen.has(k)) p.classList.add("dup"); else seen.add(k); });
      document.querySelectorAll("#karne .panel > h2").forEach(h=>{ if(h.textContent.trim()==="Canlı karne"&&!h.closest("#kzBox")){ h.textContent="Maç öncesi kilitli tahminler";
        const p=h.parentElement; p.querySelectorAll(".stat .k").forEach(k=>{ if(/Bahis şirketleri|Piyasa oranları/.test(k.textContent)) k.textContent="Oran favorisi doğru"; }); } });
    }catch(e){}
    return r; };

  // ---- Canlı: resmi bülten alınamazsa iki ayrı liste değil, tek yedek liste görünür ----
  try{ const _ira=idlRenderAll; idlRenderAll=function(){ const r=_ira.apply(this,arguments);
      try{ const box=$("idlBox"); if(box){ const ok=IDL.ok[1]||IDL.ok[2]; box.style.display=(!ok&&IDL.failed)?"none":""; } }catch(e){} return r; };
    idlRenderAll(); }catch(e){}
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: ui-v70 */
/* id: pw-v70 */ try {
// =====================================================================
// OXXai v70: Power Now — en üstte "Şu anın tek maçı" ve %70+ KUPO önerisi
// • Tek maç: önce şu an oynanan maçlardaki en olası canlı seçim (%80+, oran ≥1,15); yoksa yakında (3 saat içinde) başlayacak
//   maçların en güçlü maç öncesi tahmini (%70+); o da yoksa günün kalanındaki en güçlü tahmin. Power Now her 15 sn'de
//   yenilendiğinde maç durumuna göre (başladı, bitti, oran kapandı) kendiliğinden sıradakine geçer.
// • %70+ kupon: canlı ve 24 saat içindeki maç öncesi adaylardan, birlikte tutma olasılığı %70 ve üstünde kalan,
//   toplam oranı en yüksek 2–4 maçlık kombinasyon (farklı maçlardan). Altın kuralına dokunmaz.
// =====================================================================
(function(){
  const P70=.70, SOON=3*3600e3, DAY=24*3600e3;
  function pre70(){ const now=Date.now(), out=[];
    for(const m of Pick.list()){ if(m.live||m.started) continue; const t=m.dt.getTime(); if(t<now||t>now+DAY) continue;
      const f=m.src==="fx"?FIXTURES.find(x=>x.lg===m.lg&&x.h===m.h&&x.a===m.a):(typeof fxOdds==="function"?fxOdds(m):null); if(!f||!f.odds) continue;
      let p=null; try{ p=quickPred(m,f); }catch(e){} if(!p||!p.pm) continue;
      let R=null; try{ R=recOf({H:p.pm[0],D:p.pm[1],A:p.pm[2],o25:p.o25m},f); }catch(e){}
      if(R&&R.o&&R.o>=1.05&&R.cp>=P70) out.push({m,R,t}); }
    return out; }
  const keyOf=x=>{ try{ return x.m.sp?"L"+x.m.id:fkey(x.m); }catch(e){ return x.m.h+"|"+x.m.a; } };
  function pickOne(L,P){ const now=Date.now();
    const lv=L.filter(x=>x.o>=1.15).sort((a,b)=>b.p-a.p||b.o-a.o); if(lv.length) return {x:lv[0],kind:"live",alt:lv.slice(1,3).concat(P.slice(0,2)).slice(0,2)};
    const srt=(a,b)=>b.R.cp-a.R.cp, gd=x=>x.R.o>=1.15;
    const soon=P.filter(x=>x.t-now<=SOON).sort(srt), sG=soon.filter(gd); if(sG.length) return {x:sG[0],kind:"soon",alt:sG.slice(1,3)};
    const day=P.slice().sort(srt), dG=day.filter(gd); if(dG.length) return {x:dG[0],kind:"day",alt:dG.slice(1,3)};
    if(soon.length) return {x:soon[0],kind:"soon",alt:soon.slice(1,3)}; if(day.length) return {x:day[0],kind:"day",alt:day.slice(1,3)};
    const lv2=L.slice().sort((a,b)=>b.p-a.p); if(lv2.length) return {x:lv2[0],kind:"live",alt:lv2.slice(1,3)};
    return null; }
  function k70(L,P){ const pool=[], seen=new Set();
    for(const x of L){ if(!(x.o>=1.05)) continue; const k=keyOf(x); if(seen.has(k)) continue; seen.add(k); pool.push({x,p:x.p,o:x.o,live:1}); }
    for(const x of P){ const k=keyOf(x); if(seen.has(k)) continue; seen.add(k); pool.push({x,p:x.R.cp,o:x.R.o,live:0}); }
    const c=pool.sort((a,b)=>b.p-a.p).slice(0,14); let best=null;
    (function rec(i,sel,p,o){ if(sel.length>=2&&p>=P70&&(!best||o>best.o+1e-9||(Math.abs(o-best.o)<1e-9&&p>best.p))) best={sel:sel.slice(),p,o};
      if(sel.length>=4) return; for(let j=i;j<c.length;j++){ const np=p*c[j].p; if(np<P70) continue; sel.push(c[j]); rec(j+1,sel,np,o*c[j].o); sel.pop(); } })(0,[],1,1);
    return best; }
  const of2=o=>(+o).toLocaleString("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2});
  const lgN=m=>{ try{ return m.comp||(LEAGUES[m.lg]||{n:""}).n||""; }catch(e){ return ""; } };
  function stHtml(sel){ const x=sel.x, m=x.m;
    if(sel.kind==="live") return `<span class="o1-st live"><i></i>${esc(x.clock||"Canlı")} · ${m.hs}-${m.as}</span>`;
    const mn=Math.round((x.t-Date.now())/60e3);
    return mn<=180?`<span class="o1-st soon">⏱ ${mn<60?mn+" dk":Math.floor(mn/60)+" sa "+(mn%60)+" dk"} sonra · ${esc(ist(m.dt,{hour:"2-digit",minute:"2-digit"}))}</span>`
      :`<span class="o1-st">🗓️ ${istDay(m.dt)===istDay(new Date())?"Bugün":"Yarın"} ${esc(ist(m.dt,{hour:"2-digit",minute:"2-digit"}))}</span>`; }
  let lastKey=null;
  const _rp70=renderPower;
  renderPower=function(){ const r=_rp70.apply(this,arguments);
    try{ const v=$("v-power"), body=v&&v.querySelector(".pw-body"); if(!body) return r;
      let L=[]; try{ L=pwLiveCands(); }catch(e){} const P=pre70();
      const S=pickOne(L,P), K=k70(L,P);
      // ---- Tek maç kartı (en üstte) ----
      let c1=$("pwOne"); if(!c1){ c1=document.createElement("div"); c1.id="pwOne"; c1.className="pw-card pw-one1"; }
      if(body.firstElementChild!==c1) body.prepend(c1);
      if(!S){ c1.innerHTML=`<div class="pw-h"><span>Şu anın tek maçı</span></div><p class="o1-why">${IDL.ok[1]?"Şu an %80 üzeri canlı seçim ya da önümüzdeki 24 saatte %70 üzeri maç öncesi tahmin yok. Durum değiştikçe burası kendiliğinden dolar.":"Canlı ve günün maçları yükleniyor…"}</p>`; lastKey=null; }
      else{ const x=S.x, m=x.m, live=S.kind==="live", p=live?x.p:x.R.cp, o=live?x.o:x.R.o, n=live?x.n:x.R.n, k=keyOf(x)+"|"+(live?x.k:x.R.k);
        const why=live?"Şu an oynanan maçlar arasında tutma olasılığı en yüksek canlı seçim. Maç durumu değişirse sıradakine geçer."
          :S.kind==="soon"?"Yakında başlayacak maçlar arasında OXXai'nin en güçlü maç öncesi tahmini. Maç başlayınca canlı duruma göre yenilenir."
          :"Günün kalan maçları arasında OXXai'nin en güçlü tahmini.";
        c1.innerHTML=`<div class="pw-h"><span>Şu anın tek maçı</span><small>maç durumuna göre yenilenir</small></div>
          ${stHtml(S)}
          <div class="o1-m"${omA(m)}><b>${esc(m.h)} - ${esc(m.a)}</b><small>${esc(lgN(m))}${!live&&goldOf(m)?" · aynı zamanda günün 🥇 Altın tahmini":""}</small></div>
          <div class="o1-pick"><span class="k">${esc(n)}</span><span class="o">${of2(o)}</span><span class="p">%${pc9(p)}</span></div>
          <p class="o1-why">${why}</p>
          <button type="button" class="pw-add" id="pwOneAdd">+ KUPO</button>
          ${S.alt&&S.alt.length?`<div class="o1-next"><small style="color:var(--ink3);font-size:11.5px;align-self:center">Sıradakiler:</small>${S.alt.map(a=>`<button type="button"${omA(a.m)}>${esc(a.m.h)} · ${esc(a.R?a.R.n:a.n)} %${pc9(a.R?a.R.cp:a.p)}</button>`).join("")}</div>`:""}`;
        if(lastKey&&lastKey!==k){ c1.classList.remove("chg"); void c1.offsetWidth; c1.classList.add("chg"); }
        lastKey=k;
        $("pwOneAdd").onclick=()=>{ buzz([10,30,10]); pwAdd([x]); }; }
      // ---- %70+ kupon (tek maçın hemen altında) ----
      let c2=$("pwK70"); if(!c2){ c2=document.createElement("div"); c2.id="pwK70"; c2.className="pw-card pw-k70"; }
      if(c1.nextElementSibling!==c2) c1.after(c2);
      if(!K){ c2.innerHTML=`<div class="pw-h"><span>%70+ KUPO önerisi</span></div><p class="o1-why">Şu an birlikte tutma olasılığı %70'in üstünde kalan en az 2 maçlık bir kombinasyon yok. Adaylar canlı maçlar ve 24 saat içindeki maçlardan her 15 saniyede yeniden taranır.</p>`; }
      else{ c2.innerHTML=`<div class="pw-h"><span>%70+ KUPO önerisi</span><small>${K.sel.length} maç · en yüksek getirili</small></div>
          ${K.sel.map(s=>{ const x=s.x, m=x.m; return `<div class="pw-r"${omA(m)}><div class="pw-m"><b>${esc(m.h)} - ${esc(m.a)}</b><small>${!s.live&&goldOf(m)?"🥇 ":""}<i class="k70-tag ${s.live?"l":"p"}" style="margin:0 6px 0 0">${s.live?"CANLI "+esc(x.clock||"")+" · "+m.hs+"-"+m.as:esc((istDay(m.dt)===istDay(new Date())?"":"Yarın ")+ist(m.dt,{hour:"2-digit",minute:"2-digit"}))}</i>${esc(lgN(m))}</small></div><div class="pw-s"><span>${esc(s.live?x.n:x.R.n)}</span><b>%${pc9(s.p)}</b><i>${of2(s.o)}</i></div></div>`; }).join("")}
          <div class="k70-sum"><span>Birlikte tutma <b>%${pc9(K.p)}</b></span><span>Toplam oran <b>${of2(K.o)}</b></span></div>
          <button type="button" class="pw-add" id="pwK70Add">+ Bu maçları KUPO'ya ekle</button>
          <p class="o1-why" style="font-size:11.5px">%70 birlikte tutma, model tahminidir: benzer 10 KUPO'dan yaklaşık 3'ü tutmaz. Canlı oranlar hızla değişir.</p>`;
        $("pwK70Add").onclick=()=>{ buzz([10,30,10]); pwAdd(K.sel.map(s=>s.x)); }; }
    }catch(e){}
    return r; };
  try{ if(!$("v-power").hidden) renderPower(); }catch(e){}
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: pw-v70 */
/* id: canli-v70 */ try {
// =====================================================================
// OXXai v70: Canlı sekmesinde gerçek altın renkli "Canlı altın KUPO" — canlı maçlar 10 sn'de bir taranır.
// Adaylar: Power Now'un kalibre canlı seçimleri (%80+, açık oranlı). Kupon: farklı maçlardan 2–4 seçim,
// birlikte tutma olasılığı %75+ kalan en yüksek oranlı kombinasyon; yoksa tek başına %85+ en güçlü canlı seçim.
// Kupondaki maçlar canlı listede altın çerçeveyle işaretlenir. Tahmindir, garanti değildir.
// =====================================================================
(function(){
  // v135: son dakika seçimleri altına girmez (75. dk ve sonrası: model orada aşırı güvenliydi, %97,9 dediği %81,6 tuttu).
  // v136: eşikler data/canli_altin.json'dan (LGF; veriye dayalı seçim + 48 saatlik canlı kapı). Python eşi: scripts/canli_altin.py sec().
  const PMIN=0; let TH=LGF.kombine, open=false, lastSig="";
  function build(){ TH=LGF.kombine; const SOLO=LGF.tekli, DKMAX=LGF.dkmax; let L=[]; try{ L=pwLiveCands(); }catch(e){} const seen=new Set(), c=[];
    for(const x of L){ if(!(x.o>=1.05)) continue; if(!(x.p>=PMIN)) continue; if(x.m&&x.m.min!=null&&+x.m.min>=DKMAX) continue; if(seen.has(x.m.id)) continue; seen.add(x.m.id); c.push(x); if(c.length>=12) break; }
    let best=null;
    (function rec(i,sel,p,o){ if(sel.length>=2&&p>=TH&&(!best||o>best.o+1e-9)) best={sel:sel.slice(),p,o};
      if(sel.length>=4) return; for(let j=i;j<c.length;j++){ const np=p*c[j].p; if(np<TH) continue; sel.push(c[j]); rec(j+1,sel,np,o*c[j].o); sel.pop(); } })(0,[],1,1);
    if(!best){ const s=c.filter(x=>x.p>=SOLO).sort((a,b)=>b.p-a.p)[0]; if(s) best={sel:[s],p:s.p,o:s.o}; }
    return best; }
  const of2=o=>(+o).toLocaleString("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2});
  function paint(){ const cw=document.querySelector("#v-canli .wrap"); if(!cw) return;
    let b=$("lgBtn"); if(!b){ b=document.createElement("button"); b.type="button"; b.id="lgBtn"; b.className="lg-btn";
      b.onclick=()=>{ open=!open; buzz(8); try{ Sound.tap(); }catch(e){} paint(); }; }
    let pan=$("lgPan"); if(!pan){ pan=document.createElement("div"); pan.id="lgPan"; pan.className="lg-pan"; pan.hidden=true; }
    if(cw.firstElementChild!==b) cw.prepend(b); if(b.nextElementSibling!==pan) b.after(pan);
    const K=build(), ok=typeof IDL!=="undefined"&&(IDL.ok[1]);
    document.querySelectorAll(".lv-c.lg-on").forEach(e=>e.classList.remove("lg-on"));
    if(!K){ b.classList.add("off"); b.setAttribute("aria-expanded","false"); pan.hidden=true;
      b.innerHTML=`<span class="lg-ic">🥇</span><span class="lg-t"><b>Canlı altın KUPO</b><small>${ok?"Taranıyor · şu an yeterince güvenli canlı seçim yok":"Canlı maçlar yükleniyor…"}</small></span>`; lastSig=""; return; }
    const sig=K.sel.map(x=>x.m.id+x.k).join("|"); if(sig!==lastSig){ b.classList.remove("new"); void b.offsetWidth; if(lastSig) b.classList.add("new"); lastSig=sig; }
    b.classList.remove("off"); b.setAttribute("aria-expanded",String(open));
    b.innerHTML=`<span class="lg-ic">🥇</span><span class="lg-t"><b>Canlı altın KUPO · ${K.sel.length} maç</b><small>Birlikte tutma olasılığı · toplam oran ${of2(K.o)} · ${open?"kapat":"dokun, gör"}</small></span><span class="lg-p">%${pc9(K.p)}</span>`;
    K.sel.forEach(x=>{ const r=document.querySelector(`#v-canli .lv-c[data-id="${x.m.id}"]`); if(r) r.classList.add("lg-on"); });
    pan.hidden=!open; if(!open) return;
    pan.innerHTML=K.sel.map(x=>{ const m=x.m; return `<div class="pw-r"${omA(m)}><div class="pw-m"><b>${esc(m.h)} - ${esc(m.a)}</b><small>🔴 ${esc(x.clock||"")} · ${m.hs}-${m.as} · ${esc(m.comp||"")}</small></div><div class="pw-s"><span>${esc(x.n)}</span><b>%${pc9(x.p)}</b><i>${of2(x.o)}</i></div></div>`; }).join("")
      +`<button type="button" class="lg-add" id="lgAdd">+ Altın seçimleri KUPO'ya ekle</button><p class="lg-n">Canlı maçlar 10 saniyede bir yeniden taranır; maç durumu değişince KUPO da değişir. %${Math.round(TH*100)}+ birlikte tutma bile kesinlik değildir · 18+</p>`;
    $("lgAdd").onclick=()=>{ buzz([10,30,10]); try{ pwAdd(K.sel); }catch(e){} }; }
  window.lgPaint=paint; window.lgBuild=build;   // v136: lab/canli_altin_test.cjs (Python eşi scripts/canli_altin.py ile birebir sınama)
  try{ const _ira=idlRenderAll; idlRenderAll=function(){ const r=_ira.apply(this,arguments); try{ paint(); }catch(e){} return r; }; }catch(e){}
  try{ paint(); }catch(e){}
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: canli-v70 */
