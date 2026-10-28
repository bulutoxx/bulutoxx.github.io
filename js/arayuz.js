/* id: perf-v118-nabiz */ try {
// v118: Canlı sekmesindeki yeşil noktanın dalgası (yukarıdaki stil). Düğme yeniden çizilirse dalga geri eklenir.
(function(){ const b=document.querySelector('nav.tabs button[data-v="canli"]'); if(!b) return;
  const put=()=>{ if(!b.querySelector(":scope > .pf-rip")){ const r=document.createElement("span"); r.className="pf-rip"; r.setAttribute("aria-hidden","true"); b.prepend(r); } };
  put(); try{ new MutationObserver(put).observe(b,{childList:true}); }catch(e){} })();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: perf-v118-nabiz */
/* id: ui-v122 */ try {
// v122 · Tasarım denetimi ilk 10 iş. Futbol tarafında olay yayınları, dayanıklı Gelişim günlüğü, yükleme iskeleti,
// At bağlamında alt çubuk, açık sayfada alt çubuk. Yardımcılar (fO, fD, trYz...) ui-v122-yardim bloğunda.
(function(){
  const $$=id=>document.getElementById(id), T0=Date.now();
  const SK=(n,t)=>`<div class="v122-sk" role="status" aria-live="polite">${"<i></i>".repeat(n||3)}<p>${t||"Yükleniyor…"}</p></div>`;

  // ---------- 1) Gelişim günlüğü: bozuk/farklı şemalı kayıt listeyi asla boşaltmaz ----------
  const gun=v=>{ if(v==null||v==="") return null; if(typeof v==="number"){ if(!(v>1e9)) return null; const d=new Date(v<1e12?v*1000:v); return isNaN(d)?null:istDay(d); }
    const t=String(v).trim(); let m=/^(\d{4}-\d{2}-\d{2})/.exec(t); if(m) return m[1];
    m=/^(\d{1,2})\.(\d{1,2})\.(\d{4})/.exec(t); if(m) return `${m[3]}-${m[2].padStart(2,"0")}-${m[1].padStart(2,"0")}`;
    const d=new Date(t); return isNaN(d)?null:istDay(d); };
  const normE=(e,tarihsiz)=>{ if(!e||typeof e!=="object") return null;
    const tarih=gun(e.tarih)||gun(e.t)||gun(e.date)||gun(e.zaman); if(!tarih&&!tarihsiz) return null;
    const baslik=String(e.baslik||e.b||e.title||(e.v?"Sürüm "+e.v:"")||"Yenilik");
    return Object.assign({},e,{tarih,tur:e.tur||"gelisme",baslik,detay:e.detay!=null?String(e.detay):String(e.m||e.msg||"")}); };
  function gelYedek(box,E){ box.innerHTML=E.slice().reverse().map(e=>`<div class="gel-e gel-${esc(e.tur)}"><span>•</span><div><b>${esc(e.baslik)}</b><p>${e.tarih?esc(fD(e.tarih)):""}${e.tarih&&e.detay?" · ":""}${esc(e.detay||"")}</p></div></div>`).join("")
    ||`<div class="panel empty"><b>Henüz kayıt yok</b></div>`; }
  if(typeof renderGel==="function"){ const _rg=renderGel;
    renderGel=function(){ const box=$$("gelList"); const G=(typeof GELISIM!=="undefined")?GELISIM:null;
      if(!G||!Array.isArray(G.olaylar)){ try{ return _rg.apply(this,arguments); }catch(e){ if(box) box.innerHTML=`<div class="panel empty"><b>Günlük yükleniyor…</b></div>`; return; } }
      const raw=G.olaylar, E=raw.map(x=>normE(x)).filter(Boolean);
      G.olaylar=E; let ok=true;
      try{ _rg.apply(this,arguments); }catch(e){ ok=false; } finally{ G.olaylar=raw; }
      try{ if(box&&!E.length&&raw.length) gelYedek(box,raw.map(x=>normE(x,true)).filter(Boolean)); else if(box&&(!ok||(E.length&&!box.querySelector(".gel-e")))) gelYedek(box,E.filter(e=>e.tur!=="karne").length?E.filter(e=>e.tur!=="karne"):E); }catch(e){} };
    if(typeof gelBadge==="function"){ const _gb=gelBadge; gelBadge=function(){ const G=(typeof GELISIM!=="undefined")?GELISIM:null; if(!G||!Array.isArray(G.olaylar)) return _gb();
      const raw=G.olaylar; G.olaylar=raw.map(x=>normE(x)).filter(Boolean); try{ return _gb(); }catch(e){} finally{ G.olaylar=raw; } }; }
  }

  // ---------- 5) Yükleme: "0 maç / maç yok" yalnız veri geldikten sonra ----------
  // Gerçek neden: Pick.list() 1,5 sn'lik önbelleği veri gelmeden (FIXTURES boşken) dolarsa, fikstür geldikten hemen sonraki
  // çizim de boş listeyi görüyordu (PL_RESET yalnız robotlarda çağrılıyordu); saat donuksa boş liste kalıcı oluyordu.
  // Çözüm: veri imzası (fikstür, ESPN, sezon) değişince önbellek ve tahmin önbelleği sıfırlanır; veri gelene kadar iskelet.
  const sig=()=>{ try{ return [FIXTURES.length,FIXTURES[0]&&FIXTURES[0].h,Object.keys(Pick.extra||{}).length,Object.keys(SEASON||{}).length].join("|"); }catch(e){ return ""; } };
  let SIG="";   // ilk çağrıda önbellek mutlaka sıfırlanır (blok yüklenmeden önce boş listeyle dolmuş olabilir)
  const tazele=()=>{ const s=sig(); if(s===SIG) return false; SIG=s; try{ if(window.PL_RESET) PL_RESET(); }catch(e){} try{ BT.cache.clear(); }catch(e){} return true; };
  const hazir=()=>{ try{ return (FIXTURES.length>0&&Object.keys(SEASON||{}).length>0)||Date.now()-T0>25000; }catch(e){ return true; } };
  window.v122Hazir=hazir;
  if(typeof Pick!=="undefined"&&Pick.list){ const _pl=Pick.list; Pick.list=function(){ tazele(); return _pl.apply(this,arguments); }; }
  if(typeof renderBulten==="function"){ const _rb=renderBulten;
    let tekrar=false;
    renderBulten=function(){ tazele(); let r=_rb.apply(this,arguments);
      // veri hazırken liste boş göründüyse eski (boş) önbellekten olabilir: bir kez sıfırlayıp yeniden çiz
      try{ const L=$$("btList"); if(!tekrar&&L&&hazir()&&!L.querySelector(".ib-r,.br,.idl")&&FIXTURES.length){ tekrar=true; try{ if(window.PL_RESET) PL_RESET(); BT.cache.clear(); r=_rb.apply(this,arguments); } finally{ tekrar=false; } } }catch(e){}
      try{ const L=$$("btList"); if(L&&!hazir()&&!L.querySelector(".ib-r,.br,.idl")){ L.innerHTML=SK(4,"Bülten yükleniyor…"); const s=$$("btSub"); if(s) s.textContent="Maçlar yükleniyor…"; } }catch(e){}
      return r; }; }
  // ---------- 6) Futbol → At ayrımı: renderPower ve cpToggle'ı At modülü sarmalamaz, olay dinler ----------
  if(typeof renderPower==="function"){ const _rp=renderPower;
    renderPower=function(){ tazele(); const r=_rp.apply(this,arguments);
      try{ const v=$$("v-power"), b=v&&v.querySelector(".pw-body"); if(b&&!hazir()) b.innerHTML=SK(3,"Power Now yükleniyor…"); }catch(e){}
      try{ document.dispatchEvent(new CustomEvent("oxx:power-cizildi")); }catch(e){}
      return r; }; }
  if(typeof cpToggle==="function"){ const _ct=cpToggle;
    cpToggle=function(){ try{ document.dispatchEvent(new CustomEvent("oxx:cp-oncesi",{detail:{args:[...arguments]}})); }catch(e){} return _ct.apply(this,arguments); }; }
  if(typeof renderRes==="function"){ const _rr=renderRes;
    renderRes=function(){ const r=_rr.apply(this,arguments);
      try{ const L=$$("rsList"), p=L&&L.querySelector(":scope > .panel.empty b"); if(p&&/yükleniyor/i.test(p.textContent)) L.innerHTML=SK(3,"Sonuçlar yükleniyor…"); }catch(e){}
      return r; }; }
  // veri gelince açık ekranı bir kez yeniden çiz (bekleme süresi dolana kadar)
  let son="";
  const izle=setInterval(()=>{ try{ const s=sig(), h=hazir(); const k=s+"|"+h; if(k!==son){ son=k; tazele(); try{ if(window.PL_RESET) PL_RESET(); BT.cache.clear(); }catch(e){}
        const vis=id=>{ const v=$$(id); return v&&!v.hidden; };
        if(vis("v-bulten")) renderBulten(); if(vis("v-power")) renderPower(); }
      if(h&&FIXTURES.length&&Date.now()-T0>90000) clearInterval(izle); }catch(e){} },400);

  // ---------- 6) At bağlamında alt çubukta seçili sekme yok ----------
  const atAcik=()=>{ const v=$$("v-at"); return !!(v&&!v.hidden); };
  const navTemizle=()=>{ const at=atAcik(); if(at) document.documentElement.setAttribute("data-v122-ctx","at"); else document.documentElement.removeAttribute("data-v122-ctx");
    if(at) document.querySelectorAll("nav.tabs button[aria-current]").forEach(b=>b.removeAttribute("aria-current")); };
  if(typeof goView==="function"){ const _gv=goView; goView=function(){ const r=_gv.apply(this,arguments); try{ navTemizle(); }catch(e){} return r; }; }
  try{ const nav=document.querySelector("nav.tabs"); if(nav) new MutationObserver(()=>{ if(atAcik()&&nav.querySelector("button[aria-current]")) navTemizle(); }).observe(nav,{subtree:true,attributes:true,attributeFilter:["aria-current"]});
    const va=$$("v-at"); if(va) new MutationObserver(navTemizle).observe(va,{attributes:true,attributeFilter:["hidden"]}); }catch(e){}
  navTemizle();

  // ---------- 9) Maç detayı: sekmeler yapışınca opak şerit (yalnız yapışıkken; üstteki renkli alanla çakışmaz) ----------
  const yapis=()=>{ try{ const t=document.querySelector("#msheet .ms-tabs"); if(!t) return; const top=parseFloat(getComputedStyle(t).top)||0;
      t.classList.toggle("v122-stuck",t.getBoundingClientRect().top<=top+1&&$$("msheet").scrollTop>0); }catch(e){} };
  document.addEventListener("scroll",e=>{ if(e.target&&e.target.id==="msheet") yapis(); },{capture:true,passive:true});
  // ---------- 9) Açık alt sayfa varken alt çubuk gizli ----------
  const MODAL='#sheet:not([hidden]),[aria-modal="true"],#msheet,#botSheet,#kxSheet,#atSheet,.sheet:not([hidden])';
  const gorunur=e=>{ if(!e||e.hidden) return false; const cs=getComputedStyle(e); if(cs.display==="none"||cs.visibility==="hidden"||+cs.opacity===0) return false; const r=e.getBoundingClientRect(); return r.width>0&&r.height>0; };
  let mq=0; const modalBak=()=>{ mq=0; let on=false; try{ for(const e of document.querySelectorAll(MODAL)){ if(e.closest("nav.tabs")) continue; if(gorunur(e)){ on=true; break; } } }catch(e){}
    document.documentElement.classList.toggle("v122-modal",on); };
  try{ new MutationObserver(()=>{ if(!mq) mq=requestAnimationFrame(modalBak); }).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:["hidden","class","open","aria-modal","style"]}); }catch(e){}
  modalBak();
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: ui-v122 */
/* id: bot-v123 */ try {
// =====================================================================
// OXXai v123 · Sohbet: takım ve gün sorularında sağlamlık
// 1) Takım adı: bültende (fikstür, 8 gün) Türkçe harf / ek / yazım toleransıyla aranır. Eski eşleştirici tek kelimenin puanına baktığı için
//    "psg" (paris saint germain) sorusu "Saint Louis"e gidiyor, rakibi U21 olan "Tallinna Kal" ya da yalnız gençler maçı olan "Levante"
//    hiç bulunamıyordu. Artık sorudaki kelimelerin kaçını karşıladığına bakılır; aynı kulübün iki yazımı ("Flamengo" / "Flamengo RJ")
//    varsa en yakın maç gelir.
// 2) Gün adı: "pazartesi maçları" bugün pazartesiyse ve bugünün kalan maçı yoksa gelecek pazartesi gösterilir.
// 3) Takımın 8 gün içinde maçı yoksa genel liste yerine bunu açıkça söyler (sonraki maç tarihi biliniyorsa onu da).
// 4) Veri hazır değilse (açılışın ilk saniyeleri) cevap vermeden önce bülten beklenir: "Bir saniye…". Puan durumu / form / aralarındaki
//    maçlar sorulursa tembel yüklenen tam sezon verisi (season.json) de tetiklenip beklenir.
// =====================================================================
(function(){
  "use strict";
  const V=window.BOT69, X=window.BOT70; if(!V||typeof V.teams!=="function") return;
  const D=864e5, N=s=>String(s||"").toLocaleLowerCase("tr").replace(/ç/g,"c").replace(/ğ/g,"g").replace(/ı/g,"i").replace(/ö/g,"o").replace(/ş/g,"s").replace(/ü/g,"u")
    .normalize("NFD").replace(/[̀-ͯ]/g,"").replace(/[^a-z0-9]+/g," ").trim();
  const GX=/\(k\)|\(frw\)|\bwomen\b|\bkadin\b|\bu ?1\d\b|\bu ?2\d\b|\bii\b|\breserves?\b| b$/;
  const TOP=new Set(["tr1","tr2","en","es","it","de","fr","pt","nl","ucl","uel","uecl","be"]);
  const tok=n=>{ try{ return tmTok(n); }catch(e){ return N(n).split(" ").filter(w=>w.length>=3); } };
  const lev=(a,b)=>{ try{ return qLev(a,b); }catch(e){ return 9; } };
  const SUF=["nin","nun","in","un","ndan","nden","dan","den","tan","ten","nda","nde","da","de","ta","te","yla","yle","la","le","yi","yu","ya","ye","na","ne","ni","nu","i","u","a","e"];
  // Türkçe ek atılmış kök yalnız tam ada, adın başına ya da (uzun kökte) tek harf yazım farkıyla eşleşir: "flamengonun" → flamengo
  function ws(w,t){ let b=ws1(w,t); if(b<3) for(const x of SUF){ if(w.length-x.length<4||!w.endsWith(x)) continue; const st=w.slice(0,-x.length);
      if(st===t) return 3; if(t.startsWith(st)&&st.length/t.length>=.55) b=Math.max(b,2); else if(st.length>=7&&lev(st,t.slice(0,st.length+1))<=1) b=Math.max(b,1); }
    return b; }
  function ws1(w,t){ if(w===t) return 3;
    if(w.length>=4&&t.startsWith(w)&&w.length/t.length>=.55) return 2;           // "lyon" → "lyonnes", "tallin" → "tallinna"
    if(t.length>=4&&w.startsWith(t)&&t.length/w.length>=.6) return 2;            // Türkçe ek: "tallinnanin", "flamengonun"
    if(w.length>=5&&t.length>=5&&lev(w,t.slice(0,w.length+1))<=(w.length>=8?2:1)) return 1;   // yazım hatası
    return 0; }
  // soru kelimeleri (takım adı adayları): bot sözlüğündeki dolgu kelimeleri ve "maçlara", "tahminlerine" gibi ekli halleri dışarıda
  const FILL=/^(mac|tahmin|bugun|yarin|aksam|oyna|takim|lig|gol|skor|sonuc|analiz|kupo|liste|oran|yuzde|hafta|bak|goster|soyle|nasil|neler|hangi|kazan|yener|bulten|program|fikstur|karsilas|altin|banko|guven|sagla|kesin|hazir|surpriz|canli|oner|risk|sistem|garanti|ilk|ikinci|devre|kombin)/;
  const words=s=>{ const S=V._stop||new Set(); return String(s||"").split(" ").filter(w=>w.length>=3&&!S.has(w)&&!/^\d+$/.test(w)&&!FILL.test(w)); };
  const youthQ=s=>/\bkadin|\(k\)|women|\bu ?\d\d\b|genc/.test(s);
  // bir maçın soru kelimelerini karşılama puanı
  function cover(W,m){ const H=tok(m.h), A=tok(m.a); let sum=0, full=true, hs=0, as=0, hw=new Set(), aw=new Set();
    for(const w of W){ let bh=0, ba=0; for(const t of H) bh=Math.max(bh,ws(w,t)); for(const t of A) ba=Math.max(ba,ws(w,t));
      const b=Math.max(bh,ba); sum+=b; if(b<2&&!(b===1&&w.length>=6)) full=false;
      if(bh) { hs=Math.max(hs,bh); hw.add(w); } if(ba){ as=Math.max(as,ba); aw.add(w); } }
    const both=hs>0&&as>0&&[...hw].some(w=>!aw.has(w))&&[...aw].some(w=>!hw.has(w));
    return {sum,full,hs,as,both}; }
  function pool(){ const now=Date.now(); try{ return Pick.list().filter(m=>{ const t=m.dt.getTime(); return t<=now+8*D&&!(m.started&&!m.live)&&(t>=now-3*3600e3); }); }catch(e){ return []; } }
  const gt=(x,y)=>{ for(let i=0;i<x.length;i++) if(x[i]!==y[i]) return x[i]>y[i]; return false; };
  function best(s,needFull){ const W=words(s); if(!W.length) return null; const yq=youthQ(s); let b=null;
    for(const m of pool()){ const c=cover(W,m); if((c.sum<2&&!(c.full&&c.sum>=1&&W.every(w=>w.length>=6)))||(needFull&&!c.full)) continue;
      const g=!yq&&(isGX(m.h)||isGX(m.a))?1:0;
      const k=[c.sum,-g,TOP.has(m.lg)?1:0,-m.dt.getTime()];
      if(!b||gt(k,b.k)) b={m,k,c}; }
    return b; }
  const res=(b)=>({m:b.m,v:b.c.sum+(b.c.both?1:0),both:b.c.both,hs:b.c.hs,as:b.c.as,t:b.m.dt.getTime()});
  // aynı kulübün yazım çeşitleri: "Flamengo" / "Flamengo RJ" (kısa ek), ikisi de büyükler takımı
  const variant=(x,y)=>{ const a=N(x), b=N(y); if(a===b) return true; const [s,l]=a.length<b.length?[a,b]:[b,a]; return l.startsWith(s+" ")&&l.slice(s.length+1).length<=3&&!isGX(x)&&!isGX(y); };
  const T3X=new Set(["fc","afc","cf","sc","ac","club","the","esw","frw"]);
  const t3=x=>N(x).split(" ").filter(w=>w.length>=3&&!T3X.has(w));
  // a: aranan takım (kanonik ad), b: bültendeki ad. a'nın kelimeleri b'de olmalı ("Flamengo" ⊂ "Flamengo RJ"); tersi yalnız b en az 2 kelimeyse
  const same=(a,b)=>{ const A=t3(a), B=t3(b); if(!A.length||!B.length) return false; return A.every(w=>B.includes(w))||(B.length>=2&&B.every(w=>A.includes(w))); };
  const isGX=n=>GX.test(N(n)+" ")||/\((k|w|[a-z]{2}w|wsl)\)/i.test(String(n||""));
  let gxNote=null;   // son cevapta büyükler maçı olmadığı için kadın / genç takımı maçı seçildiyse
  const _teams=V.teams;
  V.teams=function(s){ const old=_teams.apply(this,arguments);
    try{
      if(!old){ const b=best(s,true); if(b&&!youthQ(s)&&(isGX(b.m.h)||isGX(b.m.a))){ const W=words(s), sd=W.every(w=>tok(b.m.h).some(t=>ws(w,t)>=2))?b.m.h:b.m.a; if(isGX(sd)) gxNote={name:sd.replace(/\s*\([^)]*\)\s*$/,"").replace(/\s+(u ?\d\d|ii|b|reserves?|youth)$/i,""),m:b.m}; } return b?res(b):null; }
      const W=words(s); if(!W.length) return old;
      // soru bilinen bir takımın tam adıysa ("real madrid") ama bulunan maçta o takım yoksa ("Atlético Madrid") yanlış eşleşmedir
      let ft=null; try{ ft=W.length>=2?findTeam(W.join(" ")):null; }catch(e){}
      if(ft&&ft.name&&!same(ft.name,old.m.h)&&!same(ft.name,old.m.a)){
        // önce büyükler maçı; yoksa (yalnız kadın / genç takımı oynuyorsa) o maç
        const yq=youthQ(s); let hit=null, hitG=null;
        for(const m of pool()) if(same(ft.name,m.h)||same(ft.name,m.a)){ if(yq||!(isGX(m.h)||isGX(m.a))){ if(!hit||m.dt<hit.dt) hit=m; } else if(!hitG||m.dt<hitG.dt) hitG=m; }
        if(!hit&&hitG) gxNote={name:ft.name,m:hitG};
        hit=hit||hitG;
        return hit?{m:hit,v:4,both:false,hs:same(ft.name,hit.h)?3:0,as:same(ft.name,hit.a)?3:0,t:hit.dt.getTime()}:null; }
      const b=best(s,false); if(!b||b.m===old.m) return old;
      const oc=cover(W,old.m);
      if(b.c.full&&b.c.sum>=oc.sum+2) return res(b);                       // sorudaki kelimelerin çoğunu karşılayan maç (psg → Paris Saint-Germain)
      // aynı takımın daha yakın maçı (farklı kaynaktan farklı yazım)
      const side=o=>o.hs>=o.as?"h":"a", on=old.m[side(oc)];
      if(b.c.sum>=oc.sum&&b.m.dt<old.m.dt&&(variant(on,b.m.h)||variant(on,b.m.a))) return res(b);
    }catch(e){}
    return old; };
  // ---------- gün adı: bugünün kalan maçı yoksa gelecek hafta ----------
  const WDRE=/\b(pazartesi|sali|carsamba|persembe|cumartesi|cuma|pazar)\b/;
  const _day=V.day;
  V.day=function(s,raw){ const r=_day.apply(this,arguments);
    try{ if(r&&r.key==="d"&&WDRE.test(s)&&r.d===istDay(new Date())){
        const now=Date.now(), left=Pick.list().some(m=>{ const t=m.dt.getTime(); return !m.started&&t>=now&&t<r.to; });
        if(!left){ const d=istDay(new Date(Date.parse(r.d+"T12:00:00+03:00")+7*D)), f=Date.parse(d+"T00:00:00+03:00");
          if(Pick.list().some(m=>{ const t=m.dt.getTime(); return t>=f&&t<f+D; })) return {key:"d",d,from:f,to:f+D,label:ist(new Date(f+12*3600e3),{day:"numeric",month:"long",weekday:"long"})}; } } }catch(e){}
    return r; };
  // ---------- veri hazır mı? ----------
  const ready=()=>{ try{ return FIXTURES.length>0&&Pick.list().length>0; }catch(e){ return false; } };
  const SEAS=/\b(puan durumu|puan tablosu|siralama\w*|kacinci|form\w*|son maclar\w*|son \d+ mac|aralarinda\w*|h2h|gecmis maclar\w*)\b/;
  function wait(msg){ try{ const d=[...document.querySelectorAll("#botLog .bt-msg.bot")].pop(); if(d&&d.querySelector(".bt-dots")&&!d.querySelector(".v123-w")) d.insertAdjacentHTML("beforeend",`<small class="v123-w"> ${msg}</small>`); }catch(e){} }
  // sayaçla (saat dondurulmuş olsa bile en çok ms/200 tur)
  async function until(fn,ms){ for(let i=0;i<ms/200&&!fn();i++) await new Promise(r=>setTimeout(r,200)); return fn(); }
  // ---------- takımın yakında maçı yok ----------
  const GEN=/^(Önümüzdeki saatlerde|Önümüzdeki günlerde)/;
  function noMatch(raw,R){ try{
      const txt=String(R&&R.html||"").replace(/<[^>]+>/g,""); if(!GEN.test(txt)) return null;
      const s=V.rewrite(X&&X.rewrite?X.rewrite(raw):raw).s; if(!s) return null;
      if(_teams(s)||V.teams(s)) return null;
      const W=words(s); if(!W.length||W.length>3) return null;
      const name=V.isTeamWord(s); if(!name) return null;
      const T=tok(name).concat(t3(name)); if(!W.every(w=>T.some(t=>ws(w,t)>=2))) return null;          // sorunun tüm kelimeleri o takımın adı
      let nx=null; try{ const now=Date.now(); for(const m of Pick.list()){ const t=m.dt.getTime(); if(t<now) continue; if(same(m.h,name)||same(m.a,name)) if(!nx||t<nx.dt.getTime()) nx=m; } }catch(e){}
      const when=nx?` Bir sonraki maçı: <b>${esc(nx.h)} - ${esc(nx.a)}</b>, ${esc(ist(nx.dt,{day:"numeric",month:"long",weekday:"long"}))}.`:" Maç bültene eklenince sorarsan hemen analiz ederim.";
      return {html:`<b>${esc(name)}</b> için önümüzdeki 8 günde bültende maç bulamadım 🤷${when}`,chips:["Bugün hangi maçlar var","Yarın","En güvenli maçlar"]};
    }catch(e){ return null; } }
  if(typeof botAnswer==="function"){ const _ba=botAnswer;
    botAnswer=async function(raw){
      try{ if(!ready()){ wait("Bir saniye, bülteni açıyorum…"); await until(ready,8000); }
        const n=N(raw); if(SEAS.test(n)&&window.oxxSeason&&oxxSeason.isLite()){ wait("Bir saniye, sezon verisine bakıyorum…"); await Promise.race([oxxSeason.ensure(),new Promise(r=>setTimeout(r,6000))]); } }catch(e){}
      gxNote=null;
      const R=await _ba.apply(this,arguments);
      const Y=noMatch(raw,R); if(Y) return Y;
      // gün söylenmemişse ("maç programı") ve bugünün başlamamış maçı kalmadıysa (gece geç saat) yarının programı
      try{ const txt=String(R&&R.html||"").replace(/<[^>]+>/g,""), s=V.rewrite(X&&X.rewrite?X.rewrite(raw):raw).s||"";
        if(/^Bugün için .*bulamadım/.test(txt)&&!/\b(bugun\w*|bu gun|aksam\w*|gece\w*)\b/.test(s)&&!/(saglam|guvenli|banko|kesin|emin)/.test(s)){
          const R2=await _ba.call(this,"yarın "+raw); const t2=String(R2&&R2.html||"");
          if(/class="bt-card/.test(t2)) return Object.assign({},R2,{html:`<small class="v123-n">🌙 Bugün için önerebileceğim maç kalmadı; yarının programına baktım:</small><br>${t2}`}); } }catch(e){}
      try{ const g=gxNote; gxNote=null;
        if(g&&R&&typeof R.html==="string"&&R.html.includes(esc(g.m.h))&&R.html.includes(esc(g.m.a)))
          return Object.assign({},R,{html:`<small class="v123-n">ℹ️ <b>${esc(g.name)}</b> büyükler takımının önümüzdeki 8 günde bültende maçı yok; bulduğum en yakın maç:</small><br>${R.html}`}); }catch(e){}
      return R; };
  }
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: bot-v123 */
/* id: bot-v127 */ try {
// =====================================================================
// OXXai v127 · Sohbet: lig / kupa adları veriden öğrenilir
// Kök neden: lig eşleştirici (BOT_LG) sabit bir sözlük + gece koçunun bankasıydı. Bültene yeni giren yarışmalar ("Çekya Kupası",
// "Polonya Kupası", "Avusturya Kupası", "Rusya Kupası"…) sözlükte olmadığından "çekya kupası maçları" sorusunda yalnız ülke ("cekya")
// tanınıyor, cevap o ülkenin bütün liglerinden karışık geliyordu.
// Çözüm: bültendeki gerçek yarışma adlarından (fikstürdeki cn / ln ve LEAGUES adı) otomatik bir eş anlamlı sözlüğü kurulur:
//  · tam ad ("cekya 2 lig", "almanya 2 bundesliga"), virgülden sonraki tur / grup eki atılmış taban ad ("rusya kupasi"),
//  · ulusal kupa kalıbı: "<ülke> kupası" ve İngilizce / yerel karşılıkları ("czech cup", "puchar polski", "ofb cup", "mol cup"),
//  · ülke adının İngilizce karşılığıyla lig adları ("czech 2 lig"); Türkçe harf toleransı normalize ile ("cekya" = "Çekya").
// Aynı yarışmanın grupları ("Romanya Kupası, 1. Grup" … "4. Grup") tek aile sayılır: aile adı sorulunca hepsinden seçilir.
// Bir ifade birden çok yarışmaya gidiyorsa eklenmez. Sabit sözlükteki büyük ligler (ör. "türkiye süper lig" → Süper Lig) korunur.
// Sözlük veri değiştikçe kendiliğinden yenilenir; bundan sonra bültene giren her yarışma ek iş gerekmeden tanınır.
// =====================================================================
(function(){
  "use strict";
  if(typeof botAnswer!=="function"||typeof BOT_LG!=="object"||typeof nluPhrase!=="function") return;
  const N=s=>String(s||"").toLocaleLowerCase("tr").replace(/ç/g,"c").replace(/ğ/g,"g").replace(/ı/g,"i").replace(/ö/g,"o").replace(/ş/g,"s").replace(/ü/g,"u")
    .normalize("NFD").replace(/[̀-ͯ]/g,"").replace(/[^a-z0-9]+/g," ").trim();
  // ülke adları: Türkçe (normalize) → İngilizce / yerel karşılıklar (yarışma listesi değil; yalnız ülke adı çevirisi)
  const CC={cekya:"czech czechia cesko cek",polonya:"poland polish polska",avusturya:"austria austrian osterreich",rusya:"russia russian",almanya:"germany german deutschland",
    ingiltere:"england english",ispanya:"spain spanish",italya:"italy italian",fransa:"france french",hollanda:"netherlands holland dutch",portekiz:"portugal portuguese",
    yunanistan:"greece greek",danimarka:"denmark danish",norvec:"norway norwegian",isvec:"sweden swedish",romanya:"romania romanian",sirbistan:"serbia serbian",
    hirvatistan:"croatia croatian",gurcistan:"georgia georgian",turkiye:"turkey turkish",arjantin:"argentina",ekvador:"ecuador",paraguay:"",uruguay:"",macaristan:"hungary hungarian",
    belcika:"belgium belgian",isvicre:"switzerland swiss",iskocya:"scotland scottish",slovakya:"slovakia slovak",slovenya:"slovenia",bulgaristan:"bulgaria",ukrayna:"ukraine",
    brezilya:"brazil",meksika:"mexico",japonya:"japan",kolombiya:"colombia",sili:"chile",finlandiya:"finland",irlanda:"ireland",galler:"wales",kibris:"cyprus",israil:"israel",
    misir:"egypt",fas:"morocco",litvanya:"lithuania",letonya:"latvia",estonya:"estonia",karadag:"montenegro",arnavutluk:"albania",kazakistan:"kazakhstan",azerbaycan:"azerbaijan",
    ermenistan:"armenia",izlanda:"iceland",avustralya:"australia",cin:"china",tayland:"thailand",endonezya:"indonesia",venezuela:"",peru:"",bolivya:"bolivia",sirbistan_:"",
    "suudi arabistan":"saudi arabia saudi","guney afrika":"south africa","kuzey irlanda":"northern ireland","guney kore":"south korea korea","kuzey makedonya":"north macedonia macedonia",
    "bosna hersek":"bosnia","faroe adalari":"faroe","orta amerika":"central america",abd:"usa"};
  // yerel / İngilizce kupa adları → "<ülke> kupasi" (yalnız veride o kupa varsa etkili olur)
  const CUPN={"mol cup":"cekya","puchar polski":"polonya","ofb cup":"avusturya","ofb pokal":"avusturya","uniqa cup":"avusturya","dfb pokal":"almanya","coppa italia":"italya",
    "coupe de france":"fransa","knvb beker":"hollanda","taca de portugal":"portekiz","fa cup":"ingiltere","scottish cup":"iskocya","ziraat turkiye kupasi":"turkiye","ziraat kupasi":"turkiye",
    "svenska cupen":"isvec","dbu pokalen":"danimarka","magyar kupa":"macaristan","cupa romaniei":"romanya","kypello elladas":"yunanistan","hrvatski kup":"hirvatistan",
    "copa argentina":"arjantin","copa paraguay":"paraguay","copa ecuador":"ekvador","beker van belgie":"belcika","schweizer cup":"isvicre","russian cup":"rusya"};
  const CUPW=/\b(kupasi|kupa|cup|pokal|puchar|copa|coppa|coupe|taca|beker|kup)\b/;
  const SUFX=/\s+(\d+\s*)?(grup|grub|group|eleme|siralama|ana tur|final turu|turu|ilk etap|ikinci etap|playoff|play off)(\s+\w+)?$/;
  const CTRY=Object.keys(CC).filter(k=>!k.endsWith("_")).sort((a,b)=>b.split(" ").length-a.split(" ").length);
  const GEN=new Set("lig ligi league liga premier super pro primera division ligue serie profesyonel futbol ulusal national kupa kupasi cup a b c 1 2 3 i ii amator".split(" "));
  const BIG=new Set(["tr1","tr2","en","es","it","de","fr","nl","pt","be","ucl","uel","uecl"]);
  const lgFix=s=>s.replace(/\bligi\b/g,"lig").replace(/\bliga\b/g,"lig").replace(/\bleague\b/g,"lig").replace(/\bsuperliga(en)?\b/g,"super lig");
  const ctryOf=n=>{ for(const c of CTRY) if(n===c||n.startsWith(c+" ")) return c; return null; };
  let KEY="", AUTO=[], FAM=Object.create(null), FIRST=null; const AUTO_SET=new Set();
  function labelsOf(){ const by=Object.create(null);
    for(const f of (typeof FIXTURES!=="undefined"&&FIXTURES)||[]){ if(!f||!f.lg) continue; const s=by[f.lg]||(by[f.lg]={n:0,lab:new Set()}); s.n++;
      if(f.cn) s.lab.add(f.cn); if(f.ln) s.lab.add(f.ln); }
    for(const [lg,s] of Object.entries(by)){ const L=LEAGUES[lg]; if(L&&L.n) s.lab.add(L.n); }
    return by; }
  function build(){ const by=labelsOf(); const ph=Object.create(null), base=Object.create(null), fam=Object.create(null);
    const put=(p,lg,exact)=>{ p=N(p).replace(/\s+/g," ").trim(); if(!p||p.split(" ").length<2) return; const o=ph[p]||(ph[p]={lgs:new Set(),ex:new Set()}); o.lgs.add(lg); if(exact) o.ex.add(lg); };
    for(const [lg,s] of Object.entries(by)){ if(!LEAGUES[lg]) continue;
      for(const lab of s.lab){ const raw=String(lab); if(/women|kadin|\(k\)|\bu ?\d\d\b|juvenil|youth/i.test(N(raw))) continue;
        const full=N(raw), b0=N(raw.split(/,| - /)[0]).replace(SUFX,"").trim(), b=b0||full;
        (fam[b]=fam[b]||new Map()).set(lg,s.n); if(full===b) base[b]=lg;
        for(const v of new Set([full,b,lgFix(full),lgFix(b)])) put(v,lg,v===b||v===lgFix(b));
        const c=ctryOf(b), rest=c?b.slice(c.length).trim():"";
        if(c&&rest){ const al=(CC[c]||"").split(" ").filter(Boolean);
          for(const a of al) for(const r of new Set([rest,lgFix(rest)])) put(a+" "+r,lg,true);
          if(rest==="kupasi"){ put(c+" kupasi",lg,true); put(c+" cup",lg,true); for(const a of al){ put(a+" cup",lg,true); put(a+" kupasi",lg,true); } }
          // özel adlı kupa: "kral kupasi", "efl kupasi" — ülke olmadan da (ayırt edici kelime varsa)
          const rw=rest.split(" "); if(CUPW.test(rest)&&rw.length>=2&&rw.some(w=>w.length>=3&&!GEN.has(w))) put(rest,lg,false); } } }
    for(const [nm,c] of Object.entries(CUPN)){ const t=ph[c+" kupasi"]; if(t) for(const lg of t.lgs) put(nm,lg,true); }
    // aile: aynı taban adın grupları; temsilci = taban adı birebir taşıyan lig, yoksa en çok maçı olan
    const F2=Object.create(null), repOf=Object.create(null);
    for(const [b,m] of Object.entries(fam)){ const lgs=[...m.keys()]; const rep=base[b]||lgs.sort((x,y)=>m.get(y)-m.get(x))[0]; for(const lg of lgs) repOf[b+"|"+lg]=rep; if(lgs.length>1) F2[rep]=new Set(lgs); }
    const out=[];
    for(const [p,o] of Object.entries(ph)){ let lgs=[...o.lgs];
      // aynı ailenin üyeleri tek yarışma sayılır
      const reps=new Set(lgs.map(lg=>{ for(const [r,S] of Object.entries(F2)) if(S.has(lg)) return r; return lg; }));
      let lg=null; if(reps.size===1) lg=[...reps][0]; else if(o.ex.size===1) lg=[...o.ex][0];
      if(lg&&LEAGUES[lg]) out.push([p,lg]); }
    out.sort((a,b)=>b[0].split(" ").length-a[0].split(" ").length||b[0].length-a[0].length);
    // sabit sözlükteki büyük lig ile bültendeki aynı yarışma ("Süper Lig" ↔ "Türkiye Süper Lig"): ülke kelimesi o lige gidiyorsa tek aile
    for(const [ck,E] of Object.entries(BOT_LG)){ const c=N(ck); if(!BIG.has(E)||c.includes(" ")||!CC.hasOwnProperty(c)||!LEAGUES[E]) continue;
      const want=lgFix(c+" "+N(botLgName(E)));
      for(const [b,m] of Object.entries(fam)) if(lgFix(b)===want) for(const lg of m.keys()) if(lg!==E){ (F2[E]=F2[E]||new Set([E])).add(lg); }
    }
    FAM=F2; return out; }
  function existing(p,cur){ const toks=p.split(" "); for(const [k,v] of cur){ if(!LEAGUES[v]) continue; try{ if(nluPhrase(toks,N(k))) return [N(k),v]; }catch(e){} } return null; }
  function hasUp(lg){ try{ const now=Date.now(); return Pick.list().some(m=>m.lg===lg&&!m.started&&m.dt.getTime()>now&&m.dt.getTime()<now+8*864e5); }catch(e){ return false; } }
  function ensure(){ try{
      const k=((typeof FIXTURES!=="undefined"&&FIXTURES.length)||0)+"|"+Object.keys(LEAGUES).length;
      if(k!==KEY){ KEY=k; AUTO=build(); FIRST=null; }
      if(!AUTO.length) return;
      if(FIRST){ const ks=Object.keys(BOT_LG); if(ks.length===FIRST[2]&&ks[0]===FIRST[0]&&BOT_LG[FIRST[0]]===FIRST[1]) return; }   // kurulu (koç bankası yüklenince BOT_LG yeniden yazılır)
      const cur=Object.entries(BOT_LG).filter(([kk])=>!AUTO_SET.has(kk)), have=new Set(cur.map(([kk])=>N(kk)));
      const add=[];
      for(const [p,lg] of AUTO){ if(have.has(p)) continue;
        if(!CUPW.test(p)){ const e=existing(p,cur);   // büyük lig zaten doğru eşleşiyorsa (ör. "türkiye süper lig" → Süper Lig) dokunma
          if(e&&e[1]!==lg&&BIG.has(e[1])&&(hasUp(e[1])||(FAM[e[1]]&&FAM[e[1]].has(lg)))){ const c=ctryOf(p); if(!c||BOT_LG[c]===e[1]||N(botLgName(e[1]))===p.slice(c.length).trim()) continue; } }
        add.push([p,lg]); }
      for(const kk of Object.keys(BOT_LG)) delete BOT_LG[kk];
      AUTO_SET.clear(); for(const [p,lg] of add){ BOT_LG[p]=lg; AUTO_SET.add(p); }
      for(const [kk,v] of cur) if(!(kk in BOT_LG)) BOT_LG[kk]=v;
      const k0=Object.keys(BOT_LG); FIRST=k0.length?[k0[0],BOT_LG[k0[0]],k0.length]:null;
    }catch(e){} }
  // aile: temsilci lig sorulunca grupların hepsinden seç
  // "<ülke> ligi" (kupa sözü yok): ülke süzgecinde kupa yarışmaları karışmasın
  let LASTQ="";
  const isCupLg=lg=>CUPW.test(N(botLgName(lg)));
  if(typeof botPre==="function"){ const _bp=botPre;
    botPre=function(o){ const S=o&&o.lg&&FAM[o.lg];
      if(!S){ const L=_bp.apply(this,arguments);
        if(o&&o.cn&&!o.lg&&/\blig/.test(LASTQ)&&!CUPW.test(LASTQ)){ const L2=L.filter(x=>!(x&&x.m&&isCupLg(x.m.lg))); if(L2.length) return L2; }
        return L; }
      const o2=Object.assign({},o); delete o2.lg; return _bp.call(this,o2).filter(x=>x&&x.m&&S.has(x.m.lg)); }; }
  window.BOT127={ensure,phrases:()=>{ ensure(); return AUTO.slice(); },fam:()=>FAM};
  const _ba=botAnswer;
  botAnswer=async function(raw){ ensure(); LASTQ=N(raw); return _ba.apply(this,arguments); };
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: bot-v127 */
/* id: ui-v125 */ try {
// =====================================================================
// v125 · (1) At koşu kartı Meraklı görünümü ve at profili: yeni model sinyalleri küçük rozetlerle.
//   Kaynak: kilitli tahmin dosyasındaki "sinyal" alanı (lab/at/sinyal.py — yalnız koşu içi göreli ifade: sıra, iç/dış, var/yok)
//   ve yoksa gerekçe metni. Ham derece / ham puan gösterilmez. Verisi olmayan öğe görünmez.
// (2) Futbol Altın karnesi: sabit ya da geri test kaynaklı iddia yerine kilitli tahminlerin gerçek isabeti + örnek sayısı +
//   %95 güven aralığı (data/model.json → backtest.kalibrasyon.kilitli.mevcut_tum_arsiv.altin). goldKarne artık uygulamanın
//   GÖSTERDİĞİ öneriyle (sk/sp/sok) sayar; ham rp kullanılmaz.
// =====================================================================
(function(){
  const esc2=s=>s==null?"":(typeof esc==="function"?esc(s):String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])));
  // ---------------- (1) AT SİNYALLERİ ----------------
  try{ (function(){
    const X=window.BX_AT, A2=window.BX_AT2, box=document.getElementById("at2Box"); if(!X||!X.AT||!A2||!box) return;
    const dec=s=>{ try{ return decodeURIComponent(s); }catch(e){ return s; } };
    const unK=s=>String(s).split("~").map(dec).join("/"), dayOf=kid=>String(kid||"").split("/")[0];
    function raceById(id){ const D=X.AT.data&&X.AT.data[dayOf(id)]; return D&&(D.kosular||[]).find(r=>r.kosu_id===id)||null; }
    // Türkçe sıra eki (birincisi, üçüncüsü, altıncısı, dokuzuncusu, onuncusu): 1.'si, 3.'sü, 6.'sı, 9.'su, 10.'su
    const SUF={1:"si",2:"si",3:"sü",4:"sü",5:"si",6:"sı",7:"si",8:"si",9:"su"}, SUF0={1:"su",2:"si",3:"su",4:"sı",5:"si",6:"sı",7:"si",8:"si",9:"su"};
    const sira=n=>`${n}.'${n%10?SUF[n%10]:(SUF0[Math.floor(n/10)%10]||"si")}`;
    const ok=s=>Array.isArray(s)&&s.length===2&&s[0]>=1&&s[1]>=3&&s[0]<=s[1];
    const yuzde=(s,lbl)=>{ const q=s[0]/s[1]; if(s[0]===1) return [`${lbl}en iyisi`,"g"]; if(q<=.2) return ["koşudakilerin en iyi %20'si","g"]; if(q<=.4) return ["koşudakilerin en iyi %40'ı","g"]; if(q>.8) return ["alanın gerisinde","b"]; return ["alanın ortasında",""]; };
    const rankT=s=>{ const q=s[0]/s[1]; return [`alanın ${sira(s[0])}`, q<=1/3?"g":q>2/3?"b":""]; };
    // gerekçe metni → (anahtar, değer, ton); yalnız v6 sinyalleri ve yaşa göre kilo
    const GR=[["id",/son idmanda alanın en hızlılarından/,"alanın en hızlılarından","g"],["id",/son idman derecesi alanın gerisinde/,"alanın gerisinde","b"],
      ["hp",/handikap puanı alanın üstünde/,"alanın üstünde","g"],["hp",/handikap puanı alanın altında/,"alanın altında","b"],
      ["st",/dış kulvardan çıkıyor/,"dış kulvar",""],["st",/iç kulvardan çıkıyor/,"iç kulvar",""],
      ["hv",/(ıslak pistte|ağır\/ıslak pist beklentisinde) formu iyi/,"ıslak pistte formu iyi","g"],["hv",/(ıslak pistte|ağır\/ıslak pist beklentisinde) formu zayıf/,"ıslak pistte formu zayıf","b"],
      ["km",/hız figürü eğilimi \(Kalman\) alanın üstünde/,"alanın üstünde","g"],["km",/hız figürü eğilimi \(Kalman\) alanın altında/,"alanın altında","b"],
      ["ms",/bu mesafede en iyi derecelerini yapıyor/,"en iyi dereceleri bu mesafede","g"],["ms",/en iyi dereceleri başka mesafede/,"en iyi dereceleri başka mesafede","b"],
      ["wfa",/yaşına göre kilo avantajı olmalı/,"avantajlı","g"],["wfa",/yaşına göre etkin kilosu hafif/,"etkin kilosu hafif","g"],["wfa",/yaşına göre etkin kilosu ağır/,"etkin kilosu ağır","b"],
      ["wfa",/uzun mesafede yaş avantajı/,"uzun mesafede avantajlı","g"],["wfa",/uzun mesafede yaş dezavantajı/,"uzun mesafede dezavantajlı","b"]];
    const LBL={id:"İdman",hp:"Handikap puanı",st:"Start",hv:"Pist/hava",km:"Hız eğilimi",ms:"Mesafe",gl:"Gelişim",wfa:"Yaşa göre kilo"};
    const ORDER=["id","hp","st","km","ms","gl","wfa","hv"];
    function sig(h){ const S=(h&&h.sinyal&&typeof h.sinyal==="object")?h.sinyal:{}, G=String(h&&h.gerekce||""), o={};
      if(ok(S.id)) o.id=yuzde(S.id,"alanın ");
      if(ok(S.hp)) o.hp=rankT(S.hp);
      if(S.st==="ic"||S.st==="orta"||S.st==="dis") o.st=[{ic:"iç kulvar",orta:"orta kulvar",dis:"dış kulvar"}[S.st],""];
      if(ok(S.km)) o.km=rankT(S.km);
      if(S.ms==="uygun") o.ms=["en iyi dereceleri bu mesafeye yakın","g"]; else if(S.ms==="uzak") o.ms=["alışık olmadığı mesafe","b"];
      if(S.gl==="ust") o.gl=["beklenti alanın üstünde","g"]; else if(S.gl==="alt") o.gl=["beklenti alanın altında","b"];
      if(S.wfa==="avantaj") o.wfa=["avantajlı","g"];
      if(S.hv==="iyi") o.hv=["ıslak pistte formu iyi","g"]; else if(S.hv==="zayif") o.hv=["ıslak pistte formu zayıf","b"];
      for(const [k,re,t,c] of GR) if(!o[k]&&re.test(G)) o[k]=[t,c];
      return o; }
    const hava=r=>{ const s=r&&r.sinyal&&r.sinyal.hava; return s==="yagisli"?["yağışlı tahmin","b"]:s==="kuru"?["kuru tahmin",""]:null; };
    const chip=(k,v)=>`<span class="u125-r${v[1]?" "+v[1]:""}"><i>${esc2(LBL[k])}:</i>${esc2(v[0])}</span>`;
    const chips=o=>ORDER.filter(k=>o[k]).map(k=>chip(k,o[k])).join("");
    function rowNo(mk){ const a=mk.querySelector("a.a2-mk-a"), m=a&&/#at\/at\/[^/]+\/([^/?#]+)/.exec(a.getAttribute("href")||""); return m?dec(m[1]):null; }
    function decoKosu(r){ const miss=box.querySelector(":scope > .a2-miss"); if(!miss||miss.dataset.u125) return;
      const by={}; for(const h of r.atlar||[]) by[String(h.no)]=h;
      const var_=new Set(); let n=0;
      box.querySelectorAll(".a2-mk").forEach(mk=>{ if(mk.querySelector(".u125-sg")) return; const no=rowNo(mk), h=no!=null&&by[no]; if(!h) return;
        const o=sig(h); Object.keys(o).forEach(k=>var_.add(k)); const c=chips(o); if(!c) return; n++;
        const ref=mk.querySelector(".a2-mk-b")||mk.querySelector("a.a2-mk-a"); ref.insertAdjacentHTML("afterend",`<div class="u125-sg" aria-label="Sinyaller">${c}</div>`); });
      const hv=hava(r); miss.dataset.u125="1";
      if(!n&&!hv) return;
      let t=miss.innerHTML;
      if(var_.has("st")) t=t.replace("start/kulvar, ","");
      if(var_.has("hp")) t=t.replace("handikap puanı, ","");
      if(var_.has("id")) t=t.replace("idman/galop, ","");
      const ozet=ORDER.filter(k=>var_.has(k)&&k!=="hv").map(k=>LBL[k].toLocaleLowerCase("tr")).join(", ");
      miss.innerHTML=`<span class="u125-h">Bu koşuda yeni sinyaller</span>${hv?`<div class="u125-sg">${chip("hv",hv)}</div>`:""}${ozet?`<span class="u125-n">${esc2(ozet.charAt(0).toLocaleUpperCase("tr")+ozet.slice(1))}: verisi olan atlarda satırın altında, koşudakilere göre.</span>`:""}<span class="u125-m">${t}</span>`; }
    function decoAt(r,no){ const miss=box.querySelector(":scope > .a2-miss"); if(!miss||miss.dataset.u125) return;
      const h=(r.atlar||[]).find(y=>String(y.no)===String(no)); if(!h) return; miss.dataset.u125="1";
      const o=sig(h), hv=hava(r); if(hv&&!o.hv) o.hv=hv; const c=chips(o); if(!c) return;
      let t=miss.innerHTML; if(o.id) t=t.replace(/pedigri, sahip ve idman(\/galop)? verisi/,"pedigri ve sahip verisi");
      miss.innerHTML=`<span class="u125-h">Bu at için sinyaller</span><div class="u125-sg">${c}</div><span class="u125-n">Koşudakilere göre; tahmin anında bilinen bilgiden.</span><span class="u125-m">${t}</span>`; }
    function run(){ try{ const rt=A2.route(); if(!rt||(rt.v!=="kosu"&&rt.v!=="at")) return; const r=raceById(unK(rt.a[0]||"")); if(!r) return;
        if(rt.v==="kosu"){ if(box.querySelector(".a2-sortb")) decoKosu(r); } else decoAt(r,rt.a[1]); }catch(e){ console.error(e); } }
    new MutationObserver(run).observe(box,{childList:true});
    // at3 deco'su .a2-miss'i yerinde yeniden yazabilir (kariyer gelince): metin değişirse yeniden işle
    new MutationObserver(ms=>{ for(const m of ms){ const el=m.target.nodeType===1?m.target:m.target.parentElement, mi=el&&el.closest&&el.closest(".a2-miss");
        if(mi&&mi.dataset.u125&&!mi.querySelector(".u125-h")){ delete mi.dataset.u125; run(); return; } } }).observe(box,{subtree:true,childList:true,characterData:true});
    run();
    window.BX_AT_SIG={sig,sira};
  })(); }catch(e){ console.error(e); }

  // ---------------- (2) FUTBOL ALTIN KARNESİ ----------------
  try{ (function(){
    if(typeof GOLD==="undefined") return;
    const wilson=(h,n)=>{ if(!n) return null; const z=1.96, p=h/n, d=1+z*z/n, c=(p+z*z/(2*n))/d, w=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return [Math.max(0,c-w),Math.min(1,c+w)]; };
    const pc=x=>Math.round(x*100);
    // kilitli gerçek isabet: önce laboratuvarın kilitli arşiv ölçümü (uygulamanın sunduğu öneri yolu, Altın kuralı), yoksa uygulamanın sayımı
    function gk(){ let A=null; try{ A=MODEL&&MODEL.backtest&&MODEL.backtest.kalibrasyon&&MODEL.backtest.kalibrasyon.kilitli&&MODEL.backtest.kalibrasyon.kilitli.mevcut_tum_arsiv&&MODEL.backtest.kalibrasyon.kilitli.mevcut_tum_arsiv.altin; }catch(e){}
      if(A&&A.n>0&&A.tutan!=null){ const ci=Array.isArray(A.ci95)&&A.ci95[0]!=null?A.ci95:wilson(A.tutan,A.n); return {n:A.n,h:A.tutan,ci}; }
      const K=GOLD.karne; if(K&&K.n>0) return {n:K.n,h:K.h,ci:wilson(K.h,K.n)}; return null; }
    function txt(){ const g=gk(); if(!g) return null;
      return `Kilitli tahminlerde ${g.h}/${g.n} (%${pc(g.h/g.n)})${g.ci?` · aralık %${pc(g.ci[0])}–${pc(g.ci[1])}`:""}${g.n<30?" · örnek az, kesin değil":""}`; }
    window.oxxAltinKarneTxt=txt;
    const BOS="Kilitli tahminlerde henüz yeterli sonuçlanmış örnek yok; maçlar bittikçe burada görünür.";
    function fix(s){ if(typeof s!=="string"||!/geçmiş tahminler|%82|yeterli puanlanmış örneği/.test(s)) return s; const t=txt();
      return s.replace(/Kurala uyan geçmiş tahminler: <b>\d+\/\d+<\/b> \(%\d+\)\./g,(t||BOS).replace(/\.$/,"")+".")
        .replace(/Kilitli arşivde henüz yeterli örnek yok; geçmiş sınamada bu güvendeki öneriler %82 tuttu\./g,t?t+".":BOS)
        .replace(/Altın kuralına uyan geçmiş tahminler: <b>\d+\/\d+<\/b> tuttu \(%\d+\)( — örnek az, temkinli oku)?/g,`Altın: ${t||BOS.replace(/\.$/,"")}`)
        .replace(/ Kurala uyan geçmiş tahminler: \d+\/\d+ tuttu\./g,t?` ${t}.`:"")
        .replace(/Altın tahminlerin kilitli arşivde henüz yeterli puanlanmış örneği yok\./g,t?`Altın: ${t}.`:"Altın tahminlerin kilitli arşivde henüz yeterli puanlanmış örneği yok."); }
    // goldKarne: uygulamanın gösterdiği öneri (sk → sp olasılık, sok sonuç; oran sk'nin oranı) ile say
    if(typeof goldKarne==="function"){
      const odd=(v,k)=>{ if(k==="1"||k==="X"||k==="2"){ const i="1X2".indexOf(k); return Array.isArray(v.ms)?+v.ms[i]:null; } if(k==="U"||k==="A") return Array.isArray(v.ou)?+v.ou[k==="U"?0:1]:null; return null; };
      goldKarne=async function(){ try{ const days=(DAILY&&DAILY.gunler||[]).filter(g=>g.n>0).map(g=>g.d).slice(-30); let n=0,h=0;
          for(const d of days){ let A=null; try{ const r=await fetch(`data/archive/${d}.json`,{cache:"no-cache"}); if(r.ok) A=await r.json(); }catch(e){} if(!A) continue;
            for(const v of Object.values(A)){ if(!v||!v.sk||v.sp==null||v.sok==null) continue; const o=odd(v,String(v.sk));
              if(+v.sp>=.78&&o&&o>=GOLD.omin&&o<=GOLD.omax){ n++; if(v.sok) h++; } } }
          GOLD.karne={n,h,src:"sunulan"}; const thr=n>=20&&h/n<.72?.82:.78; if(thr!==GOLD.thr){ GOLD.thr=thr; GOLD.set=null; }
        }catch(e){} };
    }
    if(typeof karneOzetHtml==="function"){ const _k=karneOzetHtml; karneOzetHtml=function(){ return fix(_k.apply(this,arguments)); }; }
    if(typeof botAnswer==="function"){ const _b=botAnswer; botAnswer=async function(){ const R=await _b.apply(this,arguments); try{ if(R&&typeof R.html==="string"){ const h=fix(R.html); if(h!==R.html) return Object.assign({},R,{html:h}); } }catch(e){} return R; }; }
    if(typeof renderPower==="function"){ const _p=renderPower; renderPower=function(){ const r=_p.apply(this,arguments);
        try{ const v=document.getElementById("v-power"); if(v) v.querySelectorAll("p.note").forEach(p=>{ if(/Altın kuralına uyan geçmiş tahminler/.test(p.textContent)){ const t=txt(); p.textContent=t?`📒 Altın · ${t}.`:`📒 ${BOS}`; } }); }catch(e){} return r; }; }
    // OXXai KUPO karnesi: Altın bloğuna tek tek seçimlerin kilitli isabeti
    function oxk(){ try{ const b=document.getElementById("oxkBox"); if(!b) return; const t=txt(); if(!t) return;
        b.querySelectorAll(".oxk-k").forEach(k=>{ const h3=k.querySelector("h3"); if(!h3||h3.textContent.trim()!=="Altın"||k.querySelector(".u125-ak")) return;
          k.insertAdjacentHTML("beforeend",`<p class="u125-ak">🥇 Tek tek Altın seçimler · <b>${esc2(t)}</b>. Tahmindir, garanti değildir.</p>`); }); }catch(e){} }
    let oT=null; const kv=document.getElementById("v-kupon");
    if(kv) new MutationObserver(()=>{ clearTimeout(oT); oT=setTimeout(oxk,80); }).observe(kv,{childList:true,subtree:true});
  })(); }catch(e){ console.error(e); }
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: ui-v125 */
