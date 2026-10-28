/* id: ui-v122-yardim */ try {
// v122 · Ortak biçim yardımcıları (saf fonksiyonlar; tüm katmanlardan önce yüklenir).
//  fO(1.357) → "1,36" (oran, Türkçe virgül) · fD("2026-10-17") → "17 Eki" · fDY(...) → "17 Eki 2026"
//  trEk(76) → "76'sı" · trYz(76) → "%76'sı" · trYz(40,"nde") → "%40'ında" (iyelik + bulunma)
(function(){
  const N2=new Intl.NumberFormat("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2});
  window.fO=function(x){ const n=+x; return isFinite(n)?N2.format(n):"–"; };
  const DF=new Intl.DateTimeFormat("tr-TR",{timeZone:"Europe/Istanbul",day:"numeric",month:"short"});
  const DFY=new Intl.DateTimeFormat("tr-TR",{timeZone:"Europe/Istanbul",day:"numeric",month:"short",year:"numeric"});
  function toDate(d){ if(d instanceof Date) return d; if(typeof d==="number") return new Date(d);
    const t=String(d||"").trim(); let m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(t); if(m) return new Date(t+"T12:00:00+03:00");
    m=/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/.exec(t); if(m) return new Date(`${m[3]}-${m[2].padStart(2,"0")}-${m[1].padStart(2,"0")}T12:00:00+03:00`);
    return new Date(t); }
  window.fD=function(d){ const x=toDate(d); return isNaN(x)?String(d||""):DF.format(x).replace(".",""); };
  window.fDY=function(d){ const x=toDate(d); return isNaN(x)?String(d||""):DFY.format(x).replace(".",""); };
  // sayının okunuşunun son hecesi: [ünlüyle bitiyor mu, son ünlü]
  const BIR={1:[0,"i"],2:[1,"i"],3:[0,"ü"],4:[0,"ü"],5:[0,"i"],6:[1,"ı"],7:[1,"i"],8:[0,"i"],9:[0,"u"]};
  const ON={1:[0,"u"],2:[1,"i"],3:[0,"u"],4:[0,"ı"],5:[1,"i"],6:[0,"ı"],7:[0,"i"],8:[0,"i"],9:[0,"ı"]};
  function ses(x){ let t=String(x==null?"":x).replace(/[%\s]/g,""); const v=t.split(/[.,]/);
    if(v.length>1&&/[1-9]/.test(v[1])) t=v[1].replace(/0+$/,""); else t=v[0];
    let n=Math.abs(parseInt(t,10)); if(!isFinite(n)) return [0,"i"]; if(n===0) return [0,"ı"];
    if(n%10) return BIR[n%10]; if(n%100) return ON[(n%100)/10]; if(n%1000) return [0,"ü"]; if(n%1e6) return [0,"i"]; return [0,"u"]; }
  window.trSfx=function(x,k){ const [s,v]=ses(x); let e=(s?"s":"")+v; if(k==="nde") e+="n"+(/[ıu]/.test(v)?"da":"de"); return e; };
  window.trEk=function(x,k){ return x+"'"+trSfx(x,k); };
  window.trYz=function(x,k){ return "%"+trEk(x,k); };
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: ui-v122-yardim */
/* id: perf-v118 */ try {
// =====================================================================
// OXXai v118 · Performans (P0)
// 1) Tek zamanlayıcı: tüm setInterval'lar ortak bir planlayıcıya bağlanır. Sayfa gizliyken durur; görünür olunca vadesi gelenler bir kez çalışır.
//    İstisna (arka planda sürer): 5 dk ve üstü seyrek işler (ör. sonuç bildirimi), fn.oxxBg=true olanlar ve koşulu "document.hidden||…" diye
//    kendisi yazanlar (ör. at hatırlatma bildirimi). Yeni kod için: everyVisible(fn, ms).
// 2) Açılış: lig güçleri robotun data/ratings.json dosyasından gelir (telefonda yeniden eğitim yok);
//    data/season.json (3,8 MB) yalnız puan durumu, aralarındaki maçlar, maç tahmini ve Motor sayfasında, gerekince arka planda yüklenir.
// 3) Sürüm kontrolü: 1,25 MB index.html yerine data/version.json ({"v":"<APP_V>"}).
// =====================================================================
(function(){
  "use strict";
  const W=window, nSI=W.setInterval, nCI=W.clearInterval, nST=W.setTimeout, nCT=W.clearTimeout;
  // ---------- 1) Planlayıcı ----------
  const T=new Map(); let seq=5e8, tmr=0, at=Infinity;
  const BG=5*60e3, hid=()=>document.hidden===true;
  function nextOf(t,now){ return t.al ? (Math.floor(now/t.al)+1)*t.al+40 : now+t.ms; }
  function arm(){
    let nx=Infinity; const h=hid();
    for(const t of T.values()) if(!h||t.bg) if(t.next<nx) nx=t.next;
    if(tmr&&nx===at) return;
    if(tmr){ nCT.call(W,tmr); tmr=0; } at=nx;
    if(nx<Infinity) tmr=nST.call(W,run,Math.max(0,nx-Date.now()));
  }
  function run(){
    tmr=0; at=Infinity; const t0=Date.now(), h=hid();
    const due=[...T.values()].filter(t=>(!h||t.bg)&&t.next<=t0+5).sort((a,b)=>a.next-b.next);
    for(const t of due){
      if(Date.now()-t0>12) break;   // tek uzun görev olmasın: kalanlar bir sonraki turda
      if(!T.has(t.id)) continue;
      t.next=nextOf(t,Date.now());
      try{ t.fn.apply(W,t.args); }catch(e){ nST.call(W,()=>{ throw e; },0); }
    }
    arm();
  }
  function add(fn,ms,o){ o=o||{}; ms=Math.max(10,+ms||0); const id=++seq, now=Date.now();
    const t={id,fn,ms,args:o.args||[],bg:!!o.bg,al:o.align?Math.max(1000,+o.align):0}; t.next=nextOf(t,now); T.set(id,t); arm(); return id; }
  W.everyVisible=function(fn,ms,o){ return add(fn,ms,Object.assign({},o,{bg:false})); };
  // Arka planda da çalışacaklar: 5 dk ve üstü, fn.oxxBg=true ya da gizliyken çalışma koşulunu kendisi yazan (ör. "!document.hidden||PR().sys" → at hatırlatma bildirimi)
  const bgOf=(fn,ms)=>{ if((+ms||0)>=BG||fn.oxxBg===true) return true; try{ return /document\.hidden\s*\|\|/.test(Function.prototype.toString.call(fn)); }catch(e){ return false; } };
  W.setInterval=function(fn,ms,...a){ if(typeof fn!=="function") return nSI.call(W,fn,ms,...a); return add(fn,ms,{args:a,bg:bgOf(fn,ms)}); };
  W.clearInterval=function(id){ if(T.has(id)){ T.delete(id); arm(); return; } return nCI.call(W,id); };
  W.clearTimeout=function(id){ if(T.has(id)){ T.delete(id); arm(); return; } return nCT.call(W,id); };
  document.addEventListener("visibilitychange",arm);
  W.OXX_T={ list:()=>[...T.values()].map(t=>({ms:t.ms,bg:t.bg,al:t.al})) };

  // ---------- 2) Sezon: küçük özet + tembel tam veri ----------
  const PK=["decay","prior","mkt","h1"];
  W.oxxRatingsSeason=function(r,m){ try{
    if(!r||r.v!==1||!r.leagues) return null;
    const P=(m&&m.params)||{}, R=r.params||{};
    for(const k of PK) if((P[k]==null?null:P[k])!==(R[k]==null?null:R[k])) return null;   // ayarlar uyuşmazsa eski yol
    const S={};
    for(const [lg,L] of Object.entries(r.leagues)){
      const tm=L.tm||[];
      const d={name:L.name, asOf:L.asOf, season:L.season, _lite:true, _n:L.n,
        matches:(L.m||[]).map(x=>({d:x[0],h:tm[x[1]],a:tm[x[2]],ft:[x[3],x[4]],season:x[5]}))};
      if(L.cup) d.cup=true; if(L.espn) d.espn=L.espn; if(L.src) d.src=L.src;
      d._o=L.o?L.o.map(i=>tm[i]):(L.cup?tm:undefined);   // takım sırası tam veriyle aynı kalsın
      if(L.fit){ const F=L.fit, t={}; tm.forEach((n,i)=>{ if(F.a[i]!=null) t[n]={att:F.a[i],def:F.d[i],n:F.c[i]}; });
        d._fit={t,mu:F.mu,gamma:F.gamma,h1:F.h1,n:F.n,avg:F.avg}; }
      S[lg]=d; }
    return S; }catch(e){ return null; } };
  let full=null, fullP=null, wanted=false;
  const lite=()=>{ try{ return Object.values(SEASON).some(d=>d&&d._lite); }catch(e){ return false; } };
  function merge(s){
    let n=0;
    for(const [lg,d] of Object.entries(SEASON)){ const f=s&&s[lg]; if(!d||!d._lite||!f) continue;
      const ms=(f.matches||[]).filter(m=>m&&m.ft&&m.ft.length===2);
      if(d._n!=null&&ms.length!==d._n) continue;   // farklı sürüm: bu lig özetle kalır
      d.matches=ms.sort((a,b)=>a.d<b.d?-1:1);
      for(const k of Object.keys(f)) if(k!=="matches"&&!(k in d)) d[k]=f[k];
      delete d._lite; n++; }
    return n;
  }
  function refresh(){
    const vis=id=>{ const v=document.getElementById(id); return v&&!v.hidden; };
    try{ if(vis("v-ligler")&&typeof renderLigler==="function") renderLigler(); }catch(e){}
    try{ if(vis("v-karne")&&typeof renderKarne==="function") renderKarne(); }catch(e){}
    try{ if(typeof autoGrade==="function"&&typeof S!=="undefined"&&Object.values(S.matches||{}).some(m=>!m.result)) autoGrade(); }catch(e){}
    try{ document.dispatchEvent(new CustomEvent("oxx:season")); }catch(e){}
  }
  function ensure(){
    if(typeof SEASON==="undefined"||!Object.keys(SEASON).length) return Promise.resolve(false);
    wanted=true;
    if(!lite()) return Promise.resolve(true);
    if(fullP) return fullP;
    fullP=fetch("data/season.json",{cache:"no-cache"}).then(r=>r.ok?r.json():null).then(s=>{ fullP=null; if(!s) return false; full=s; if(merge(s)) refresh(); return !lite(); })
      .catch(()=>{ fullP=null; return false; });
    return fullP;
  }
  W.oxxSeason={ ensure, isLite:lite,
    after(){ if(full&&lite()) merge(full); if(wanted&&lite()) ensure(); } };   // yenilemeden sonra: değişmeyen ligler bellekten, gerekiyorsa arka planda tazele
  // Maç tahmini: tam veri (aralarındaki maçlar, puan durumu, trend) hazır olmadan sonuç çizilmesin
  let gate=false;
  document.addEventListener("submit",e=>{ const f=e.target; if(!f||f.id!=="f"||gate||!lite()) return;
    e.preventDefault(); e.stopImmediatePropagation();
    const b=f.querySelector("button[type=submit]"); if(b) b.disabled=true;
    const go=()=>{ if(b) b.disabled=false; gate=true; try{ f.requestSubmit(); }finally{ gate=false; } };
    Promise.race([ensure(),new Promise(r=>nST.call(W,r,10000))]).then(go,go);
  },true);
  // Önden yükle: tahmin formuna dokunulunca
  document.addEventListener("focusin",e=>{ if(e.target&&e.target.closest&&e.target.closest("#f")&&lite()) ensure(); },true);
  // Puan durumu / Motor sayfası açılınca tam veri gerekir (sekme dinleyicileri eski işlev referansını tuttuğu için tıklamadan sonra da bakılır)
  const need=()=>{ if(!lite()) return; for(const id of ["v-ligler","v-karne"]){ const v=document.getElementById(id); if(v&&!v.hidden){ ensure(); return; } } };
  document.addEventListener("click",()=>nST.call(W,need,0),true);
  W.addEventListener("hashchange",()=>nST.call(W,need,0));
  document.addEventListener("DOMContentLoaded",()=>{
    for(const [fn,vid] of [["renderLigler","v-ligler"],["renderKarne","v-karne"]]){ try{ const o=W[fn]; if(typeof o!=="function") continue;
      W[fn]=function(){ const v=document.getElementById(vid); if(v&&!v.hidden&&lite()) ensure(); return o.apply(this,arguments); }; }catch(e){} }
    try{ const o=W.autoGrade; if(typeof o==="function") W.autoGrade=function(){ if(lite()&&typeof S!=="undefined"&&Object.values(S.matches||{}).some(m=>!m.result)) ensure(); return o.apply(this,arguments); }; }catch(e){}
  });

  // ---------- 3) Sürüm ----------
  let vc={t:0,v:null}, fb=false;
  W.oxxLatestV=async function(force){
    if(!force&&Date.now()-vc.t<20e3) return vc.v;
    try{ const r=await fetch("data/version.json?t="+Date.now(),{cache:"no-store"});
      if(r.ok){ const j=await r.json(); const v=j&&typeof j.v==="string"?j.v:null; vc={t:Date.now(),v}; return v; }
      if(r.status===404&&!fb){ fb=true;   // eski yayın (version.json yok): bir kez eski yöntem
        const q=await fetch("index.html?vchk="+Date.now(),{cache:"no-store"}); if(!q.ok) return null; const m=(await q.text()).match(/const APP_V="([^"]+)"/); const v=m?m[1]:null; vc={t:Date.now(),v}; return v; }
    }catch(e){}
    return null;
  };
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: perf-v118 */
/* id: istek-v124 */ try {
// =====================================================================
// OXXai v124 · Dış istekleri azalt (denetim P1 #10: açılışta ESPN'e 62–124 istek)
// ESPN (site.api.espn.com) istekleri tek kapıdan geçer; çağıran kod değişmez, yanıt biçimi aynıdır:
//  1) Aynı adres = tek istek: aynı anda gelenler birleşir, sonuç paylaşılır (Canlı + Sıradaki maçlar + Bülten aynı ligin
//     scoreboard'unu bir kez çeker).
//  2) Önbellek: ligde canlı maç ya da 15 dk içinde başlayacak maç varsa 20 sn (gizliyken 60 sn); yoksa (boş gün, bitmiş ya da ileri tarihli maçlar)
//     10 dk. Maç özeti (summary) zaten yalnız açık maçta "Güncel tahmin"e basınca istenir; 20 sn (mevcut "az önce güncellendi" kilidi).
//  3) Sayfa gizliyken ağa çıkılmaz: önbellekte varsa (eski de olsa) o döner, yoksa istek hata verir (çağıranlar hatayı zaten tolere eder).
//     Böylece arka planda kalan sekme ESPN'i yoklamaz (perf-v118 planlayıcısıyla aynı kural).
//  4) Aynı anda en çok 4 ESPN isteği (açılışta ani yük yok).
//  5) 10 dk'lık sonuçlar Cache Storage'da ("oxx-istek-v124") tutulur: uygulama kısa süre içinde yeniden açılınca yeniden indirilmez.
// iddaa canlı çağrıları DEĞİŞMEZ (Canlı sekmesi açıkken gerekli; perf-v118 planlayıcısı gizliyken zaten durduruyor).
// Ölçüm: window.istekV124.say → {ag, onbellek, birlesik, gizli, hata}
// =====================================================================
(function(){
  "use strict";
  const W=window; if(!W.fetch||W.istekV124) return;
  const nf=W.fetch.bind(W), nST=W.setTimeout;
  const RX=/^https:\/\/site\.api\.espn\.com\//;
  const KISA=20e3, GZ=60e3, UZUN=10*60e3, OZET=20e3, ESKI=24*3600e3, PAR=4, CN="oxx-istek-v124";
  const M=new Map(), IN=new Map(), Q=[]; let akt=0;
  const say={ag:0,onbellek:0,birlesik:0,gizli:0,hata:0};
  const ozetMi=u=>/\/summary\?/.test(u);
  const gizli=()=>document.hidden===true;
  // önbellek süresi: sonuç yakında değişebilir mi?
  function ttlOf(u,txt){
    if(ozetMi(u)) return OZET;
    try{
      const j=JSON.parse(txt), now=Date.now();
      for(const e of ((j&&j.events)||[])){
        const st=(e&&e.status&&e.status.type&&e.status.type.state)||"pre", t=Date.parse(e&&e.date);
        if(st==="in") return KISA;
        if(st==="pre"&&(!isFinite(t)||t<now+15*60e3)) return KISA;   // başlamak üzere ya da gecikmiş
      }
      return UZUN;
    }catch(e){ return KISA; }
  }
  const yanit=e=>new Response(e.s===204||e.s===304?null:e.b,{status:e.s,statusText:e.st||"",headers:{"content-type":e.ct||"application/json"}});
  // ---- kalıcı önbellek (Cache Storage; yoksa yalnız bellek) ----
  let CP=null;
  function kasa(){ if(CP) return CP; try{ CP=Promise.resolve(W.caches&&W.isSecureContext?W.caches.open(CN):null).catch(()=>null); }catch(e){ CP=Promise.resolve(null); } return CP; }
  async function diskOku(u){
    try{ const c=await kasa(); if(!c) return null; const r=await c.match(u); if(!r) return null;
      const t=+r.headers.get("x-oxx-t")||0, ttl=+r.headers.get("x-oxx-ttl")||0; if(!t||Date.now()-t>ESKI) return null;
      return {t,ttl,s:r.status,st:r.statusText,ct:r.headers.get("content-type"),b:await r.text()}; }catch(e){ return null; }
  }
  function diskYaz(u,e){
    kasa().then(c=>{ if(!c) return; return c.put(u,new Response(e.b,{status:e.s,headers:{"content-type":e.ct||"application/json","x-oxx-t":String(e.t),"x-oxx-ttl":String(e.ttl)}})); }).catch(()=>{});
  }
  nST.call(W,()=>{ kasa().then(async c=>{ if(!c) return; for(const k of await c.keys()){ const r=await c.match(k); const t=r&&+r.headers.get("x-oxx-t"); if(!t||Date.now()-t>ESKI) await c.delete(k); } }).catch(()=>{}); },45e3);
  // ---- sıra (en çok PAR eşzamanlı) ----
  function sira(fn){ return new Promise((ok,no)=>{ Q.push([fn,ok,no]); pompa(); }); }
  function pompa(){ while(akt<PAR&&Q.length){ const [fn,ok,no]=Q.shift(); akt++; Promise.resolve().then(fn).then(ok,no).finally(()=>{ akt--; pompa(); }); } }
  async function getir(u){
    let e=M.get(u);
    if(!e&&!ozetMi(u)){ e=await diskOku(u); if(e&&!M.has(u)) M.set(u,e); e=M.get(u)||e; }
    if(e&&Date.now()-e.t<e.ttl){ say.onbellek++; return e; }
    if(gizli()){ const canli=e&&e.ttl===KISA&&Date.now()-e.t>GZ; if(e&&!canli){ say.onbellek++; return e; } if(!e){ say.gizli++; throw new TypeError("istek-v124: sayfa gizli, ağ isteği yapılmadı"); } }   // canlı ligler gizliyken de dakikada bir (gol bildirimi)
    if(IN.has(u)){ say.birlesik++; return IN.get(u); }
    const p=sira(async()=>{
      if(gizli()){ const x=M.get(u); if(x&&!(x.ttl===KISA&&Date.now()-x.t>GZ)) return x; if(!x){ say.gizli++; throw new TypeError("istek-v124: sayfa gizli, ağ isteği yapılmadı"); } }
      say.ag++;
      const r=await nf(u,{cache:"no-store"}); const b=await r.text();
      const x={t:Date.now(),s:r.status,st:r.statusText,ct:r.headers.get("content-type")||"application/json",b,ttl:r.ok?ttlOf(u,b):KISA};
      M.set(u,x); if(r.ok&&!ozetMi(u)) diskYaz(u,x);
      return x;
    });
    IN.set(u,p); p.catch(()=>{}).finally(()=>{ if(IN.get(u)===p) IN.delete(u); });
    try{ return await p; }catch(err){ say.hata++; const x=M.get(u)||e; if(x) return x; throw err; }
  }
  W.fetch=function(input,init){
    try{
      const url=typeof input==="string"?input:(input&&input.url)||"";
      const get=!init||((!init.method||String(init.method).toUpperCase()==="GET")&&!init.signal&&!init.body);
      if(get&&typeof input==="string"&&RX.test(url)) return getir(url).then(yanit);
    }catch(e){}
    return nf(input,init);
  };
  W.istekV124={say, liste:()=>[...M.entries()].map(([u,e])=>({u,yas_sn:Math.round((Date.now()-e.t)/1000),ttl_sn:e.ttl/1000,s:e.s})),
    temizle(){ M.clear(); try{ kasa().then(c=>c&&W.caches.delete(CN)); }catch(e){} CP=null; }};
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: istek-v124 */
/* id: ui-v92 */ try {
// v92: (1) aynı ESPN adresine aynı anda gelen istekleri tek ağ isteğinde birleştir (açılışta her lig 3 kez çekiliyordu)
//      (2) erişilebilirlik: ekran okuyucu etiketleri, role=button öğelerine klavye erişimi, Esc ile sohbeti kapatma
(function(){
  try{
    const _f=window.fetch.bind(window), IN=new Map(), TTL=3000;
    window.fetch=function(input,init){
      try{
        const url=typeof input==="string"?input:(input&&input.url)||"";
        const get=!init||((!init.method||String(init.method).toUpperCase()==="GET")&&!init.signal&&!init.body);
        if(get&&typeof input==="string"&&/^https:\/\/site\.api\.espn\.com\//.test(url)){
          const now=Date.now(), e=IN.get(url);
          if(e&&now-e.t<TTL) return e.p.then(r=>r.clone());
          const p=_f(input,init); IN.set(url,{t:now,p});
          p.catch(()=>{}).finally(()=>setTimeout(()=>{ const x=IN.get(url); if(x&&x.p===p) IN.delete(url); },TTL));
          return p.then(r=>r.clone());
        }
      }catch(e){}
      return _f(input,init);
    };
  }catch(e){}
  function a11y(){
    try{
      document.querySelectorAll(".pw-pre:not([aria-label])").forEach(b=>b.setAttribute("aria-label","KUPO'ya ekle"));
      document.querySelectorAll('[role="button"]:not([tabindex]):not(button):not(a)').forEach(b=>b.tabIndex=0);
      const t=document.getElementById("toast"); if(t&&!t.hasAttribute("role")){ t.setAttribute("role","status"); t.setAttribute("aria-live","polite"); }
      const g=document.getElementById("goal"); if(g&&!g.hasAttribute("role")){ g.setAttribute("role","status"); g.setAttribute("aria-live","polite"); }
      const s=document.getElementById("sheet"); if(s&&!s.hasAttribute("role")){ s.setAttribute("role","dialog"); s.setAttribute("aria-modal","true"); }
      const bs=document.getElementById("botSheet"); if(bs&&!bs.hasAttribute("role")){ bs.setAttribute("role","dialog"); bs.setAttribute("aria-modal","true"); bs.setAttribute("aria-label","OXXai sohbet asistanı"); }
    }catch(e){}
  }
  let q=0; const sched=()=>{ if(q) return; q=1; requestAnimationFrame(()=>{ q=0; a11y(); }); };
  try{ new MutationObserver(sched).observe(document.documentElement,{childList:true,subtree:true}); }catch(e){}
  sched();
  // Enter / Boşluk: role=button öğelerini (div/span) düğme gibi çalıştır; Esc: açık sohbeti kapat
  document.addEventListener("keydown",e=>{
    try{
      const el=e.target;
      if((e.key==="Enter"||e.key===" ")&&el&&el.getAttribute&&el.getAttribute("role")==="button"&&!/^(BUTTON|A|INPUT|TEXTAREA|SELECT)$/.test(el.tagName)&&!el.isContentEditable){ e.preventDefault(); el.click(); return; }
      if(e.key==="Escape"){ const bs=document.getElementById("botSheet"); if(bs&&!bs.hidden&&typeof botClose==="function"){ e.preventDefault(); botClose(); } }
    }catch(x){}
  });
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: ui-v92 */
