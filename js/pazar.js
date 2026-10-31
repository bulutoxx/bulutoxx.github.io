/* id: canli-sirada-v103 */ try {
// v103 · Canlı sekmesinde "Sıradaki maçlar": canlı listenin altında başlamamış tüm maçlar (saat aralığı, lig seçimi, aynı arama kutusu)
(function(){
  const NX={win:"bug", lg:"", lim:300};
  const WIN=[["bug","Bugün (24:00'e kadar)",0],["1s","1 saat",3600e3],["3s","3 saat",3*3600e3],["yar","Yarın",0],["7g","7 gün",7*864e5]];
  const fold=x=>String(x||"").toLocaleLowerCase("tr").normalize("NFD").replace(/[̀-ͯ]/g,"").replace(/ı/g,"i");
  // v150: maç → fikstür eşlemesi her satırda FIXTURES.find yerine dizin üzerinden (aynı ilk eşleşme)
  let FXI=null, FXA=null, FXN=-1;
  const fxOf=m=>{ if(FXA!==FIXTURES||FXN!==FIXTURES.length){ FXA=FIXTURES; FXN=FIXTURES.length; FXI=new Map(); for(const x of FIXTURES){ const k=x.lg+"\u0001"+x.h+"\u0001"+x.a; if(!FXI.has(k)) FXI.set(k,x); } }
    return FXI.get(m.lg+"\u0001"+m.h+"\u0001"+m.a); };
  function lgN(m){ try{ const f=fxOf(m); return (f&&(f.cn||f.ln))||botLgName(m.lg); }catch(e){ return m.lg||""; } }
  function range(){ const now=Date.now(), d0=Date.parse(istDay(new Date())+"T00:00:00+03:00");
    if(NX.win==="bug") return [now,d0+864e5]; if(NX.win==="yar") return [d0+864e5,d0+2*864e5];
    const w=WIN.find(x=>x[0]===NX.win); return [now,now+(w?w[2]:3*3600e3)]; }
  function list(){ const q=fold(IDLV&&IDLV.q||""), now=Date.now(); let [a,b]=range(); if(q){ a=now; b=now+7*864e5; }
    let L=[]; try{ L=Pick.list().filter(m=>!m.live&&!m.started&&m.dt&&m.dt.getTime()>=a&&m.dt.getTime()<b); }catch(e){}
    NX.auto=false;
    if(!q&&NX.win==="bug"&&!L.some(m=>!m.live&&!m.started)){ try{ L=Pick.list().filter(m=>!m.live&&!m.started&&m.dt&&m.dt.getTime()>=now&&m.dt.getTime()<now+864e5); NX.auto=L.length>0; }catch(e){} }
    const lv=(typeof IDL!=="undefined"&&IDL.live&&IDL.live[1])||[]; L=L.filter(m=>!lv.some(x=>tmEq(x.h,m.h)&&tmEq(x.a,m.a)));
    L=L.map(m=>({m,lg:lgN(m)}));
    if(NX.lg) L=L.filter(x=>x.lg===NX.lg);
    if(q) L=L.filter(x=>fold(x.m.h+" "+x.m.a+" "+x.lg).includes(q));
    return L.sort((x,y)=>x.m.dt-y.m.dt); }
  function pick(m){ try{ const f=fxOf(m); const p=quickPred(m,f); if(!p||!p.pm) return null;
      const R=recOf({H:p.pm[0],D:p.pm[1],A:p.pm[2],o25:p.o25m},f); return R?{n:R.n,p:R.cp,o:R.o,t:R.tier,l:R.label}:null; }catch(e){ return null; } }
  function html(){ const L=list(), q=IDLV&&IDLV.q;
        const all=(()=>{ const s=NX.lg; NX.lg=""; const r=[...new Set(list().map(x=>x.lg))]; NX.lg=s; return r; })();
    const cnt={}; (()=>{ const s=NX.lg; NX.lg=""; list().forEach(x=>cnt[x.lg]=(cnt[x.lg]||0)+1); NX.lg=s; })();
    const topL=all.sort((x,y)=>(cnt[y]||0)-(cnt[x]||0)).slice(0,14);
    let h=`<div class="nx-h"><b>Sıradaki maçlar</b><small>${q?`"${esc(q)}" için 7 gün`:`${L.length} maç`}</small></div>`+(NX.auto&&!q?`<p class="nx-auto">Bugün başlamamış maç kalmadı · sonraki 24 saatin maçları gösteriliyor</p>`:"");
    try{ const D=lastFull(); if(D){ const g=D.guclu&&D.guclu.n?D.guclu:null, y=D.d===istDay(new Date(Date.now()-864e5));
        h+=`<button type="button" class="dayban nx-ban" data-nxr="${esc(D.d)}"><span>${y?"Dün":esc(ist(new Date(D.d+"T12:00:00+03:00"),{day:"numeric",month:"long"}))}</span><b>${g?`güçlü önerilerin ${trYz(Math.round(g.hit*100))} tuttu`:`önerilerin ${trYz(Math.round(D.hit*100))} tuttu`}</b><small>${g?`${Math.round(g.hit*g.n)}/${g.n}`:""} ›</small></button>`; } }catch(e){}
    try{ const G=L.filter(x=>goldOf(x.m)); if(G.length&&!q) h+=`<div class="nx-gold"><span class="gold-seal"><img src="icons/oxxai-mark.webp" alt="">ALTIN</span><span><b>${G.length} altın tahmin</b> ${esc(NX.win==="yar"?"yarın":NX.auto?"sonraki 24 saatte":"bu aralıkta")} · ${G.map(x=>esc(x.m.h)).slice(0,3).join(", ")}${G.length>3?"…":""}</span></div>`; }catch(e){}
    if(!q) h+=`<div class="nx-ch" role="group" aria-label="Zaman">${WIN.map(([k,l])=>`<button type="button" data-nxw="${k}" aria-pressed="${NX.win===k}">${l}</button>`).join("")}</div>`;
    if(topL.length>1) h+=`<div class="nx-ch" role="group" aria-label="Lig"><button type="button" data-nxl="" aria-pressed="${!NX.lg}">Tüm ligler</button>${(NX.lg&&!topL.includes(NX.lg)?[NX.lg].concat(topL):topL).map(l=>`<button type="button" data-nxl="${esc(l)}" aria-pressed="${NX.lg===l}">${esc(l)} <small>${cnt[l]||0}</small></button>`).join("")}</div>`;
    if(!L.length) return h+`<p class="nx-e">${q?"Aramana uyan başlamamış maç yok.":"Bu aralıkta başlamamış maç yok. Daha geniş bir zaman seç."}</p>`;
    let last="";
    for(const x of L.slice(0,NX.lim)){ const m=x.m, t=ist(m.dt,{hour:"2-digit",minute:"2-digit"}), dy=istDay(m.dt), lab=dy===istDay(new Date())?"Bugün":ist(m.dt,{weekday:"long",day:"numeric",month:"long"});
      if(lab!==last){ h+=`<div class="nx-t">${esc(lab)}</div>`; last=lab; }
      const P=pick(m);
      const gd=(()=>{ try{ return !!goldOf(m); }catch(e){ return false; } })(), tl=P?(P.t==="w"?"Pas":P.t==="g"?"Güçlü":"Tahmin"):"";
      h+=`<div class="kx-fxw${gd?" nx-g":""}" data-kxr="fx"><div class="fxrow"${omA(m)} role="button" tabindex="0"><span class="nx-tm">${esc(t)}</span><span class="nx-m"><span class="tm"><b>${esc(m.h)}</b> – <b>${esc(m.a)}</b></span><small>${gd?`<span class="gold-seal"><img src="icons/oxxai-mark.webp" alt="">ALTIN</span> `:""}${esc(x.lg)}</small></span>${P?`<span class="nx-p t-${P.t}"><em>${tl}</em>${P.t==="w"?"":esc(P.n)+" "}%${Math.round(P.p*100)}<i>${P.o?"oran "+fO(P.o):"OXXai"}</i></span>`:""}</div><button type="button" class="kx-add" data-kxa="1" aria-pressed="false" aria-label="Aktif KUPO'ya ekle (basılı tut: hangi KUPO'ya)"><b>＋</b> KUPO</button></div>`; }
    if(L.length>NX.lim) h+=`<button type="button" class="nx-more" data-nxm="1">${L.length-NX.lim} maç daha göster</button>`;
    return h; }
  function paint(){ try{ const cw=document.querySelector("#v-canli .wrap"); if(!cw) return; const v=$("v-canli"); if(!v||v.hidden) return;
      let box=$("nxBox"); const idl=$("idlBox");
      if(!box){ box=document.createElement("div"); box.id="nxBox"; }
      if(idl&&box.previousElementSibling!==idl) idl.after(box); else if(!idl&&!box.parentNode) cw.appendChild(box);
      box.innerHTML=html(); try{ kxPaint(); }catch(e){} }catch(e){} }
  document.addEventListener("click",e=>{ const r=e.target.closest("#nxBox [data-nxr]"); if(r){ try{ RS.day=r.dataset.nxr; $("navRes").click(); }catch(_){} return; } },true);
  document.addEventListener("click",e=>{ const b=e.target.closest("#nxBox [data-nxw],#nxBox [data-nxl],#nxBox [data-nxm]"); if(!b) return;
    if(b.dataset.nxw!=null){ NX.win=b.dataset.nxw; NX.lim=300; } else if(b.dataset.nxl!=null){ NX.lg=b.dataset.nxl; NX.lim=300; } else NX.lim+=300;
    try{ buzz(6); }catch(_){} paint(); });
  try{ const _r=idlRenderAll; idlRenderAll=function(){ const r=_r.apply(this,arguments); paint(); return r; }; }catch(e){}
  document.addEventListener("click",e=>{ if(e.target.closest('nav.tabs button[data-v="canli"]')) setTimeout(paint,60); },true);
  try{ const i=document.getElementById("cvQi"); if(i){ i.addEventListener("input",()=>setTimeout(paint,220)); } }catch(e){}
  setTimeout(()=>{ try{ const i=document.getElementById("cvQi"); if(i&&!i.dataset.nx){ i.dataset.nx=1; i.addEventListener("input",()=>setTimeout(paint,220)); } }catch(e){} },2500);
  setInterval(()=>{ const v=$("v-canli"); if(v&&!v.hidden&&!document.hidden) paint(); },60000);
  try{ const i=$("cvQi"); if(i) i.placeholder="Maç ara: takım veya lig (canlı ve sıradaki)"; }catch(e){}
  setTimeout(()=>{ try{ const i=$("cvQi"); if(i) i.placeholder="Maç ara: takım veya lig (canlı ve sıradaki)"; }catch(e){} },2600);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: canli-sirada-v103 */
/* id: pazar-v104 */ try {
// =====================================================================
// v104 · TÜM TAHMİNLER — motorun yeni pazarları (data/fixtures.json → pz / po; data/pazar_karne.json)
// • Maç sayfası "Seçenekler" sekmesi: gruplu, katlanabilir panel (MS · Çifte şans · Alt/Üst · KG · İlk yarı · İkinci yarı · İY/MS ·
//   MS + Alt/Üst · MS + KG · Daha gollü yarı). Her seçenek: OXXai olasılığı, oran (yoksa adil oran 1/p), geçmiş kalibrasyon notu, ＋ Kupon.
//   Tahmini skorla uyumlu birleşik seçenek vurgulanır ("2-1 ⇒ MS 1 & 2,5 Üst"). Tahmin sekmesinde kısa "skorla uyumlu" kartı.
// • Kod eşlemesi: uygulamada eskiden U15 = "1,5 Alt", U35 = "3,5 Alt", O15/O35 = Üst, IO05/IU05… = İY Üst/Alt idi (eski kuponlar
//   bozulmasın diye korunur). Motor kodları kupona eşdeğer uygulama koduyla yazılır: U15→O15, A15→U15, U35→O35, A35→U35,
//   U25→U, A25→A, IYU05→IO05, IYA05→IU05, IYU15→IO15, IYA15→IU15; diğer yeni kodlar (2Y…, IYMS_…, 1&U25…, DGY…) aynen.
// • mkHit genişletildi (İY skoru h1/a1; 2Y = MS − İY; İY skoru yoksa null → KUPO "sonuç eksik" + elle işaretleme).
// • Öneri / Altın mantığına dokunulmaz: yalnız gösterim ve kupon.
// =====================================================================
(function(){
  const CAT=[
    ["MS","Maç sonucu",["1","X","2"]],
    ["ÇŞ","Çifte şans",["1X","12","X2"]],
    ["AÜ","Alt / Üst",["U15","A15","U25","A25","U35","A35"]],
    ["KG","Karşılıklı gol",["KGV","KGY"]],
    ["İY","İlk yarı",["IY1","IYX","IY2","IYU05","IYA05","IYU15","IYA15"]],
    ["2Y","İkinci yarı",["2Y1","2YX","2Y2","2YU05","2YA05","2YU15","2YA15"]],
    ["İYMS","İY / MS",["IYMS_1_1","IYMS_1_X","IYMS_1_2","IYMS_X_1","IYMS_X_X","IYMS_X_2","IYMS_2_1","IYMS_2_X","IYMS_2_2"]],
    ["MSAÜ","MS + Alt/Üst",["1&U25","1&A25","X&U25","X&A25","2&U25","2&A25"]],
    ["MSKG","MS + KG",["1&KGV","1&KGY","X&KGV","X&KGY","2&KGV","2&KGY"]],
    ["YARI","Daha gollü yarı",["DGY1","DGYE","DGY2"]]];
  const AD={"1":"MS 1","X":"MS X","2":"MS 2","1X":"Çifte şans 1X","12":"Çifte şans 12","X2":"Çifte şans X2",
    U15:"1,5 Üst",A15:"1,5 Alt",U25:"2,5 Üst",A25:"2,5 Alt",U35:"3,5 Üst",A35:"3,5 Alt",KGV:"KG Var",KGY:"KG Yok",
    IY1:"İY 1",IYX:"İY X",IY2:"İY 2",IYU05:"İY 0,5 Üst",IYA05:"İY 0,5 Alt",IYU15:"İY 1,5 Üst",IYA15:"İY 1,5 Alt",
    "2Y1":"2Y 1","2YX":"2Y X","2Y2":"2Y 2","2YU05":"2Y 0,5 Üst","2YA05":"2Y 0,5 Alt","2YU15":"2Y 1,5 Üst","2YA15":"2Y 1,5 Alt",
    DGY1:"Daha gollü yarı: 1. yarı",DGYE:"Daha gollü yarı: eşit",DGY2:"Daha gollü yarı: 2. yarı"};
  for(const a of ["1","X","2"]) for(const b of ["1","X","2"]) AD[`IYMS_${a}_${b}`]=`İY/MS ${a}/${b}`;
  for(const a of ["1","X","2"]){ AD[a+"&U25"]=`MS ${a} & 2,5 Üst`; AD[a+"&A25"]=`MS ${a} & 2,5 Alt`; AD[a+"&KGV"]=`MS ${a} & KG Var`; AD[a+"&KGY"]=`MS ${a} & KG Yok`; }
  const GRP={}; CAT.forEach(([g,,L])=>L.forEach(k=>{ GRP[k]=g; }));
  const IYG=new Set(["İY","2Y","İYMS","YARI"]);
  const TUM={A15:"U15",A25:"U25",A35:"U35",KGY:"KGV",IYA05:"IYU05",IYA15:"IYU15","2YA05":"2YU05","2YA15":"2YU15"};
  // motor kodu → uygulama (kupon) kodu; çakışan eski kodlar korunur
  const E2A={U15:"O15",A15:"U15",U35:"O35",A35:"U35",U25:"U",A25:"A",IYU05:"IO05",IYA05:"IU05",IYU15:"IO15",IYA15:"IU15"};
  const A2E={}; for(const [e,a] of Object.entries(E2A)) A2E[a]=e;
  const toApp=e=>E2A[e]||e, toEng=a=>A2E[a]||(a==="U"?"U25":a==="A"?"A25":a);
  window.pzToApp=toApp; window.pzToEng=toEng; window.PZ_CAT=CAT; window.PZ_AD=AD;
  // ---------- adlar (mkName) ----------
  try{ Object.assign(MKT_N,{U:"2,5 Üst",A:"2,5 Alt",U25:"2,5 Üst",A25:"2,5 Alt",A15:"1,5 Alt",A35:"3,5 Alt",IYU05:"İY 0,5 Üst",IYA05:"İY 0,5 Alt",IYU15:"İY 1,5 Üst",IYA15:"İY 1,5 Alt"});
    for(const [k,v] of Object.entries(AD)) if(!(k in E2A)&&k!=="U15"&&k!=="U35") MKT_N[k]=v; }catch(e){}
  // ---------- mkHit: yeni kodlar ----------
  const fin=x=>x!=null&&x!==""&&isFinite(+x)&&+x>=0;
  function res3(h,a){ return h>a?"1":h<a?"2":"X"; }
  function pzHit(k,hs,as,h1,a1){
    if(!fin(hs)||!fin(as)) return null; hs=+hs; as=+as; const t=hs+as;
    const iy=fin(h1)&&fin(a1)&&+h1<=hs&&+a1<=as; const H1=iy?+h1:null, A1=iy?+a1:null;
    const H2=iy?hs-H1:null, A2=iy?as-A1:null, t1=iy?H1+A1:null, t2=iy?H2+A2:null, ms=res3(hs,as);
    let m;
    if((m=/^([UA])(15|25|35)$/.exec(k))){ const l=+m[2]/10; return m[1]==="U"?t>l:t<l; }
    if((m=/^(IY|2Y)([UA])(05|15)$/.exec(k))){ if(!iy) return null; const g=m[1]==="IY"?t1:t2, l=+m[3]/10; return m[2]==="U"?g>l:g<l; }
    if((m=/^(IY|2Y)([1X2])$/.exec(k))){ if(!iy) return null; return (m[1]==="IY"?res3(H1,A1):res3(H2,A2))===m[2]; }
    if((m=/^IYMS_([1X2])_([1X2])$/.exec(k))){ if(!iy) return null; return res3(H1,A1)===m[1]&&ms===m[2]; }
    if((m=/^([1X2])&(U25|A25|KGV|KGY)$/.exec(k))){ const sec=m[2]==="U25"?t>2.5:m[2]==="A25"?t<2.5:m[2]==="KGV"?(hs>0&&as>0):!(hs>0&&as>0); return ms===m[1]&&sec; }
    if((m=/^DGY([12E])$/.exec(k))){ if(!iy) return null; return m[1]==="1"?t1>t2:m[1]==="2"?t2>t1:t1===t2; }
    return undefined; }
  window.pzHit=pzHit;
  const NEWK=/^(U25|A25|A15|A35|(IY|2Y)[UA](05|15)|2Y[1X2]|IYMS_[1X2]_[1X2]|[1X2]&(U25|A25|KGV|KGY)|DGY[12E])$/;
  try{ const _mh=mkHit; mkHit=function(mk,hs,as,h1,a1,s0){ const k=String(mk||"");
      if(NEWK.test(k)){ const r=pzHit(k,hs,as,h1,a1); return r===undefined?null:r; }
      // eski İY kodları: İY skoru tutarsızsa (İY > MS) kontrol edilemez
      if(/^(IY[1X2]|I[OU](05|15))$/.test(k)&&fin(h1)&&fin(a1)&&(+h1>+hs||+a1>+as)) return null;
      return _mh.apply(this,arguments); }; }catch(e){}
  const needIY=a=>IYG.has(GRP[toEng(a)])||/^(IY[1X2]|I[OU](05|15))$/.test(a);
  window.pzNeedIY=needIY;
  // ---------- veri ----------
  let KAR=null;
  fetch("data/pazar_karne.json",{cache:"no-cache"}).then(r=>r.ok?r.json():null).then(d=>{ KAR=d; try{ if(MS.m&&MS.tab==="oran") msRender(); }catch(e){} }).catch(()=>{});
  function pzFull(f){ if(!f||!f.pz||typeof f.pz!=="object") return null; const P={};
    for(const [k,v] of Object.entries(f.pz)) if(v!=null&&isFinite(+v)) P[k]=+v;
    if(P.U25==null&&P.U!=null) P.U25=P.U; if(P.A25==null&&P.A!=null) P.A25=P.A;
    for(const [a,b] of Object.entries(TUM)) if(P[a]==null&&P[b]!=null) P[a]=Math.round((1-P[b])*1000)/1000;
    return Object.keys(P).length?P:null; }
  function oddOf(f,e){ const po=f&&f.po||{}; let o=po[e]; if(o==null&&e==="U25") o=po.U; if(o==null&&e==="A25") o=po.A;
    if(o==null&&f){ const L={"1":f.odds&&f.odds[0],"X":f.odds&&f.odds[1],"2":f.odds&&f.odds[2],U25:f.ou&&f.ou[0],A25:f.ou&&f.ou[1],KGV:f.ikg&&f.ikg[0],KGY:f.ikg&&f.ikg[1]}; o=L[e]; }
    o=+o; return o>1.001&&isFinite(o)?o:null; }
  window.pzFull=pzFull; window.pzOdd=oddOf;
  const f2=x=>(+x).toLocaleString("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2});
  const fair=p=>p>0.005?1/p:null;
  const pp=p=>p==null?"–":p<.01?"<1":String(Math.round(p*100));
  function calNote(e,p){ const K=KAR&&KAR.pazarlar&&KAR.pazarlar[e]; if(!K||!Array.isArray(K.kalibrasyon)) return "";
    const B=K.kalibrasyon.find(b=>{ const [lo,hi]=String(b.aralik||"").split("-").map(Number); return p>=lo&&(p<hi||(hi>=1&&p<=1)); });
    if(!B||!(B.n>=50)) return "Geçmişte bu olasılıkta yeterli örnek yok";
    return `Geçmişte bu olasılıkta %${Math.round(B.gercek*100)} tuttu · ${B.n.toLocaleString("tr-TR")} maç${K.oneriye_uygun===false?" · sınırlı ölçüm":""}`; }
  window.pzCal=calNote;
  // takım adlarıyla kısa açıklama
  function desc(e,m){ const H=shortTeam(m.h), A=shortTeam(m.a), R={"1":`${H} kazanır`,"X":"Beraberlik","2":`${A} kazanır`};
    const G={U15:"en az 2 gol",A15:"en fazla 1 gol",U25:"en az 3 gol",A25:"en fazla 2 gol",U35:"en az 4 gol",A35:"en fazla 3 gol",KGV:"iki takım da gol atar",KGY:"en az bir takım gol atmaz"};
    let x;
    if(R[e]) return R[e];
    if(e==="1X") return `${H} kaybetmez`; if(e==="X2") return `${A} kaybetmez`; if(e==="12") return "Beraberlik olmaz";
    if(G[e]) return G[e].charAt(0).toLocaleUpperCase("tr")+G[e].slice(1);
    if((x=/^(IY|2Y)([1X2])$/.exec(e))){ const y=x[1]==="IY"?"İlk yarı":"İkinci yarı"; return x[2]==="X"?`${y} berabere (eşit gol)`:`${y}nı ${x[2]==="1"?H:A} önde kapatır`.replace("İlk yarını","İlk yarıyı").replace("İkinci yarını","İkinci yarıyı"); }
    if((x=/^(IY|2Y)([UA])(05|15)$/.exec(e))){ const y=x[1]==="IY"?"İlk yarıda":"İkinci yarıda"; return x[3]==="05"?`${y} gol ${x[2]==="U"?"olur":"olmaz"}`:`${y} ${x[2]==="U"?"en az 2":"en fazla 1"} gol`; }
    if((x=/^IYMS_([1X2])_([1X2])$/.exec(e))){ const a={"1":`${H} önde`,"X":"berabere","2":`${A} önde`}[x[1]], b={"1":H,"X":"berabere","2":A}[x[2]]; return `İY ${a} · MS ${b}`; }
    if((x=/^([1X2])&(U25|A25|KGV|KGY)$/.exec(e))){ if(e==="X&KGY") return "0-0 biter"; return `${R[x[1]]} + ${G[x[2]]}`; }
    if(e==="DGY1") return "İlk yarıda daha çok gol"; if(e==="DGY2") return "İkinci yarıda daha çok gol"; if(e==="DGYE") return "İki yarıda eşit gol";
    return ""; }
  window.pzDesc=desc;
  // tahmini skorla uyumlu kodlar
  function fitCodes(ft,ht){ const out=new Set(); const s=/^(\d+)-(\d+)$/.exec(ft||""); if(!s) return out; const h=+s[1], a=+s[2];
    const all=[].concat(...CAT.map(c=>c[2])); const q=/^(\d+)-(\d+)$/.exec(ht||""); const h1=q?+q[1]:null, a1=q?+q[2]:null;
    for(const e of all){ if(IYG.has(GRP[e])&&!(q&&h1<=h&&a1<=a)) continue; const r=pzHit(e,h,a,h1,a1); if(r===true) out.add(e); }
    return out; }
  window.pzFit=fitCodes;
  // ---------- maç bağlamı ----------
  function ctxOf(m,f){ if(!m) return null; const dt=m.sp?new Date(m.ts):m.dt; const mm=m.sp?{lg:"i"+m.ci,h:m.h,a:m.a,dt}:m;
    const P=pzFull(f); if(!P) return null; try{ uyum(P,m,f); }catch(e){} return {m,f,mm,P,ex:{iid:(f&&f.iid)||m.iid||(m.sp?m.id:null)||null}}; }
  // Tutarlılık: MS 1/X/2 ve 2,5 A/Ü uygulamanın gösterdiği (harmanlı) olasılıktan; birleşikler bu toplamlara IPF ile uydurulur
  function uyum(P,m,f){ if(m.sp) return; const q=quickPred(m,f); if(!q||!q.pm) return; const H=q.pm[0],D=q.pm[1],A=q.pm[2],O=q.o25m!=null?q.o25m:q.o25; if(!(H>0&&O>0)) return;
    const R={"1":H,"X":D,"2":A}; P["1"]=H; P.X=D; P["2"]=A; P.U25=O; P.A25=1-O; P["1X"]=H+D; P["12"]=H+A; P.X2=D+A;
    const ipf=(cols,cm)=>{ const T={}; let ok=true; for(const r of ["1","X","2"]) for(const c of cols){ const v=P[r+"&"+c]; if(v==null){ ok=false; } T[r+"&"+c]=Math.max(1e-6,v||0); } if(!ok) return;
      for(let it=0;it<60;it++){ for(const r of ["1","X","2"]){ const s=cols.reduce((a,c)=>a+T[r+"&"+c],0); cols.forEach(c=>T[r+"&"+c]*=R[r]/s); }
        cols.forEach((c,i)=>{ const s=["1","X","2"].reduce((a,r)=>a+T[r+"&"+c],0); ["1","X","2"].forEach(r=>T[r+"&"+c]*=cm[i]/s); }); }
      for(const k in T) P[k]=Math.round(T[k]*1000)/1000; };
    ipf(["U25","A25"],[O,1-O]);
    if(P.KGV!=null) ipf(["KGV","KGY"],[P.KGV,1-P.KGV]);
    for(const r of ["1","X","2"]){ const ks=["1","X","2"].map(x=>"IYMS_"+x+"_"+r).filter(k=>P[k]!=null); const s=ks.reduce((a,k)=>a+P[k],0); if(s>0) ks.forEach(k=>P[k]=Math.round(P[k]*R[r]/s*1000)/1000); }
    if(P.U15!=null&&P.U15<O) P.U15=O; if(P.U35!=null&&P.U35>O) P.U35=O;
    for(const [x,y] of Object.entries(TUM)) if(P[y]!=null) P[x]=Math.round((1-P[y])*1000)/1000; }
  window.pzCtx=ctxOf;
  const optOf=(C,e)=>{ const p=C.P[e]; if(p==null) return null; const o=oddOf(C.f,e); return {k:toApp(e),e,n:AD[e]||e,p,o}; };
  const inCp=(C,a)=>{ try{ const k=cpKey(C.mm); return CP.items.some(c=>c.k===k&&c.mk===a); }catch(e){ return false; } };
  function toggle(C,e){ const o=optOf(C,e); if(!o) return; const O={mm:C.mm,ex:C.ex,opts:[o],rec:null};
    try{ buzz(8); }catch(_){}
    if(typeof kxAdd==="function") kxAdd(O,{k:o.k,n:o.n,o:o.o,p:o.p});
    else { cpToggle(C.mm,o.k,o.o||+(1/Math.max(.02,o.p)).toFixed(2),o.p); }
    const el=$("msheet");
    if(el&&!el.hidden&&MS.m){ const st=el.scrollTop; try{ msRender(); }catch(_){} el.scrollTop=st;
      try{ const nb=el.querySelector(`[data-pzk="${CSS.escape(e)}"]`); if(nb) nb.focus({preventScroll:true}); }catch(_){} }
    paintBtns(); try{ kxPaint(); }catch(_){} }
  window.pzToggle=toggle;
  // ---------- panel ----------
  const LSO="bx-pz-acik";
  const DEF_OPEN=["MS","AÜ","KG","MSAÜ"];
  let OPEN=null; function openSet(){ if(OPEN) return OPEN; let v=null; try{ v=JSON.parse(localStorage.getItem(LSO)||"null"); }catch(e){} OPEN=new Set(Array.isArray(v)?v:DEF_OPEN); return OPEN; }
  function saveOpen(){ try{ localStorage.setItem(LSO,JSON.stringify([...openSet()])); }catch(e){} }
  function btnHtml(C,e,label){ const a=toApp(e), on=inCp(C,a), n=AD[e]||e;
    return `<button type="button" class="pz-add" data-pzk="${esc(e)}" aria-pressed="${on}" aria-label="${esc(n)} ${on?"KUPO'da, çıkarmak için dokun":"aktif KUPO'ya ekle"}">${on?"✓ KUPO'da":label||"<b>＋</b> KUPO"}</button>`; }
  function rowHtml(C,e,fit){ const o=optOf(C,e); if(!o) return "";
    const ds=desc(e,C.m), cn=calNote(e,o.p), fo=fair(o.p);
    return `<div class="pz-r${fit?" fit":""}" data-pzr="${esc(e)}"><div class="pz-n"><b>${esc(o.n)}${fit?`<span class="pz-tag">${esc(fit)} ile uyumlu</span>`:""}</b>${ds?`<small>${esc(ds)}</small>`:""}</div>
      <div class="pz-p"><b>%${pp(o.p)}</b>${o.o?`<small>oran ${f2(o.o)}</small>`:fo?`<small class="fair">adil ${f2(fo)}</small>`:""}</div>
      ${btnHtml(C,e)}${cn?`<div class="pz-c">${esc(cn)}</div>`:""}</div>`; }
  function panelHtml(C,r){ const ft=r&&r.topFT&&r.topFT[0]&&r.topFT[0].s, ht=r&&r.topH1&&r.topH1[0]&&r.topH1[0].s; const FIT=fitCodes(ft,ht), O=openSet();
    const fitTop=["1&U25","1&A25","X&U25","X&A25","2&U25","2&A25","1&KGV","1&KGY","X&KGV","X&KGY","2&KGV","2&KGY","IYMS_1_1","IYMS_X_1","IYMS_X_X","IYMS_1_X","IYMS_2_2","IYMS_X_2"].filter(e=>FIT.has(e)&&C.P[e]!=null).slice(0,3);
    const fitBox=ft&&fitTop.length?`<div class="pz-fit" role="group" aria-label="Tahmini skorla uyumlu seçenekler"><p>Tahmini skor <b>${esc(ft)}</b>${ht?` (İY ${esc(ht)})`:""} ⇒ <b>${esc(AD[fitTop[0]])}</b></p>
      ${fitTop.map(e=>{ const o=optOf(C,e); return `<div class="pz-oc"><span>${esc(o.n)} · %${pp(o.p)}<small>${esc(desc(e,C.m))} · ${o.o?`oran ${f2(o.o)}`:`adil oran ${f2(fair(o.p))}`}</small></span>${btnHtml(C,e)}</div>`; }).join("")}</div>`:"";
    const groups=CAT.map(([g,t,L])=>{ const ks=L.filter(e=>C.P[e]!=null); if(!ks.length) return "";
      const best=ks.slice().sort((a,b)=>C.P[b]-C.P[a])[0], op=O.has(g), id="pzg-"+g.replace(/[^A-Za-z0-9]/g,"x");
      const kn=KAR&&KAR.gruplar&&KAR.gruplar[g==="MSAÜ"?"MS&AÜ":g==="MSKG"?"MS&KG":g==="AÜ"?"AÜ25":g];
      return `<div class="pz-g" data-pzg="${esc(g)}"><button type="button" class="pz-gh" aria-expanded="${op}" aria-controls="${id}"><span><b>${esc(t)}</b><small>En olası: ${esc(AD[best])} %${pp(C.P[best])}${kn&&kn.isabet!=null?` · geçmiş isabet %${Math.round(kn.isabet*100)}`:""}</small></span><i aria-hidden="true">›</i></button>
        <div class="pz-gb" id="${id}"${op?"":" hidden"}>${ks.map(e=>rowHtml(C,e,FIT.has(e)&&["MSAÜ","MSKG","İYMS"].includes(g)?ft:"")).join("")}</div></div>`; }).join("");
    const src=C.f&&C.f.pzy==="m"?"model yolu":"piyasa yolu";
    return `<section class="pz" aria-label="Tüm tahminler"><div class="pz-hd"><h3>Tüm tahminler</h3><small>OXXai pazar motoru · ${src}</small></div>
      <p class="pz-leg">1 = <b>${esc(C.m.h)}</b> · 2 = <b>${esc(C.m.a)}</b>. Yüzde: OXXai olasılığı. Oran yoksa <b>adil oran</b> (1 ÷ olasılık) gösterilir; gerçek oran değildir.</p>
      ${fitBox}${groups}
      <p class="pz-note">Kalibrasyon notu, geçmiş ${KAR&&KAR.n_mac?KAR.n_mac.toLocaleString("tr-TR")+" maçta":"maçlarda"} aynı olasılık aralığındaki tahminlerin gerçekte ne sıklıkla tuttuğunu gösterir. İlk/ikinci yarı seçenekleri ilk yarı skoruyla puanlanır. Garanti değildir.</p></section>`; }
  function paintBtns(){ try{ const C=curCtx(); if(!C) return; document.querySelectorAll("#msheet [data-pzk]").forEach(b=>{ const on=inCp(C,toApp(b.dataset.pzk)); if(b.getAttribute("aria-pressed")!==String(on)){ b.setAttribute("aria-pressed",on); b.innerHTML=on?"✓ KUPO'da":"<b>＋</b> KUPO"; const n=AD[b.dataset.pzk]||b.dataset.pzk; b.setAttribute("aria-label",`${n} ${on?"KUPO'da, çıkarmak için dokun":"aktif KUPO'ya ekle"}`); } }); }catch(e){} }
  window.pzPaint=paintBtns;
  function curCtx(){ try{ if(!MS.m||MS.live) return null; return ctxOf(MS.m,MS.f); }catch(e){ return null; } }
  // Seçenekler sekmesi: pz varsa eski kutular yerine gruplu panel (canlı maçta eski canlı pazarlar aynen)
  let LASTR=null;
  try{ const _mo=msOran; msOran=function(m,f,r,lv){ if(lv||!f||!f.pz) return _mo.apply(this,arguments); const C=ctxOf(m,f); if(!C) return _mo.apply(this,arguments);
      const mm=C.mm; let pb=""; try{ pb=playBar(mm); }catch(e){}
      const sc=(r&&r.topFT||[]).slice(0,9).map(x=>`<span class="msc"><b>${esc(x.s)}</b><small>%${(x.p*100).toFixed(1)}</small></span>`).join("");
      return pb+panelHtml(C,r)+(sc?`<div class="mg"><h4>En olası skorlar</h4><div class="msc-w">${sc}</div></div>`:""); }; }catch(e){}
  try{ const _mt=msTahmin; msTahmin=function(m,f,r,lv){ LASTR={m,r}; return _mt.apply(this,arguments); }; }catch(e){}
  function tahCard(C,r){ const ft=r&&r.topFT&&r.topFT[0]&&r.topFT[0].s, ht=r&&r.topH1&&r.topH1[0]&&r.topH1[0].s; const FIT=fitCodes(ft,ht);
    const e=["1&U25","1&A25","2&U25","2&A25","X&U25","X&A25"].find(k=>FIT.has(k)&&C.P[k]!=null); if(!e) return "";
    const o=optOf(C,e);
    return `<div class="pz-fit pz-tah" role="group" aria-label="Tahmini skorla uyumlu seçenek"><p>Tahmini skor <b>${esc(ft)}</b> ⇒ <b>${esc(o.n)}</b></p>
      <div class="pz-oc"><span>%${pp(o.p)} · ${o.o?`oran ${f2(o.o)}`:`adil oran ${f2(fair(o.p))}`}<small>${esc(desc(e,C.m))}</small></span>${btnHtml(C,e)}</div>
      <button type="button" class="pz-more" data-pzall="1">Tüm tahminler: İY, 2Y, İY/MS, MS + KG ›</button></div>`; }
  try{ const _mr=msRender; msRender=function(){ const r=_mr.apply(this,arguments); try{ const el=$("msheet"), m=MS.m; if(!el||!m) return r;
      const C=curCtx(); const tb=el.querySelector('.ms-tabs button[data-t="oran"]'); if(tb&&tb.textContent!=="Seçenekler") tb.textContent="Seçenekler";
      if(!C) return r;
      const al=el.querySelector("[data-allm]"); if(al) al.textContent="Tüm tahminler (İY, 2Y, İY/MS, MS + Alt/Üst…)";
      if(MS.tab==="tahmin"&&LASTR&&LASTR.m===m&&!el.querySelector(".pz-tah")){ const h=tahCard(C,LASTR.r); if(h){ const rb=el.querySelector(".ms-body .recbig"); if(rb) rb.insertAdjacentHTML("afterend",h); else { const b=el.querySelector(".ms-body"); if(b) b.insertAdjacentHTML("afterbegin",h); } } }
    }catch(e){ console.warn("pazar-v104",e); } return r; }; }catch(e){}
  document.addEventListener("click",e=>{ const el=e.target.closest&&e.target.closest("#msheet [data-pzk],#msheet .pz-gh,#msheet [data-pzall]"); if(!el) return;
    e.preventDefault(); e.stopPropagation();
    if(el.dataset.pzall){ try{ msGo("oran"); }catch(_){} return; }
    if(el.classList.contains("pz-gh")){ const g=el.closest("[data-pzg]").dataset.pzg, S=openSet(), op=el.getAttribute("aria-expanded")!=="true";
      el.setAttribute("aria-expanded",op); const gb=el.nextElementSibling; if(gb) gb.hidden=!op; if(op) S.add(g); else S.delete(g); saveOpen(); try{ buzz(5); Sound.tap(); }catch(_){} return; }
    const C=curCtx(); if(!C){ toast("Bu maç için pazar olasılığı yok"); return; } toggle(C,el.dataset.pzk); },true);
  // ---------- KUPO: seçim değiştir listesine yeni pazarlar (gruplu) + adil oran notu + "sonuç eksik" ----------
  function augO(O){ if(!O||O._pz||!O.mm||O.ex&&(O.ex.live||O.ex.sp)) return O; O._pz=1;
    let f=null; try{ const m=O.mm; f=m.src==="fx"?FIXTURES.find(x=>x.lg===m.lg&&x.h===m.h&&x.a===m.a):(FIXTURES.find(x=>x.lg===m.lg&&x.h===m.h&&x.a===m.a)||(O.ex&&O.ex.iid?FIXTURES.find(x=>x.iid===O.ex.iid):null)||fxOdds(m)); }catch(e){}
    const P=pzFull(f); if(!P) return O; O._P=P; O._f=f;
    const have=new Set((O.opts||[]).map(o=>o.k));
    for(const [,,L] of CAT) for(const e of L){ if(P[e]==null) continue; const a=toApp(e); if(have.has(a)) continue; O.opts.push({k:a,n:AD[e],o:oddOf(f,e),p:P[e],_e:e}); have.add(a); }
    return O; }
  const ORD={}; CAT.forEach(([,,L])=>L.forEach((k,i)=>{ ORD[k]=i; }));
  function koHtml(O,i,cur){ const by={}; for(const o of O.opts){ const g=GRP[toEng(o.k)]||(/^[UA]$/.test(o.k)?"AÜ":"MS"); (by[g]=by[g]||[]).push(o); }
    for(const g in by) by[g].sort((a,b)=>(ORD[toEng(a.k)]??99)-(ORD[toEng(b.k)]??99));
    const curG=GRP[toEng(cur)]||"MS";
    return CAT.filter(([g])=>by[g]&&by[g].length).map(([g,t])=>{ const sn=k=>String(mkName(k)).replace(/^Çifte şans /,"").replace(/^Daha gollü yarı: /,"").replace(/^(\d)\. yarı$/,"$1. yarı");
    const bt=by[g].map(o=>`<button type="button" data-kx="sw" data-i="${i}" data-k="${esc(o.k)}" aria-pressed="${o.k===cur}" aria-label="${esc(mkName(o.k))}" class="${O.rec&&O.rec.k===o.k?"rec":""}">${esc(sn(o.k))}<small>${o.o?f2(o.o):"adil "+f2(1/Math.max(.02,o.p||.5))} · %${pp(o.p)}</small></button>`).join("");
      const open=["MS","ÇŞ","AÜ","KG"].includes(g)||g===curG;
      return `<div class="pz-kg">${open?`<small>${esc(t)}</small><div class="pz-kw">${bt}</div>`:`<details><summary>${esc(t)}</summary><div class="pz-kw">${bt}</div></details>`}</div>`; }).join(""); }
  function kupoDeco(){ const box=$("cpBox"); if(!box) return; const OO=box._O;
    if(Array.isArray(OO)) OO.forEach(augO);
    box.querySelectorAll(".kx-opts:not(.pz-ko)").forEach(k=>{ const row=k.closest("[data-cpi]"); if(!row) return; const i=+row.dataset.cpi, O=OO&&OO[i], x=CP.items[i]; if(!O||!x||!O._P) return;
      k.classList.add("pz-ko"); k.innerHTML=koHtml(O,i,x.mk); });
    // adil oran notu (toplam oran)
    const I=CP.items||[], nf=I.filter(x=>x.fair).length, ko=box.querySelector(".kx-sum .kp-odd>span:first-child");
    if(ko&&!ko.querySelector(".pz-fair")&&nf) ko.insertAdjacentHTML("beforeend",`<span class="pz-fair">${nf===I.length?"Tüm seçimlerde":nf+" seçimde"} gerçek oran yok: adil oran (1 ÷ OXXai olasılığı) ile hesaplandı</span>`);
    // İY gerektiren seçimde ilk yarı skoru gelmediyse
    box.querySelectorAll(".cprow[data-cpi] .kx-hint").forEach(h=>{ const x=I[+h.closest("[data-cpi]").dataset.cpi]; if(!x||!x.need||x.ok!=null||h.dataset.pz) return;
      const tn=[...h.childNodes].find(n=>n.nodeType===3&&/Sonuç otomatik bulunamadı/.test(n.textContent)); if(!tn) return; h.dataset.pz="1";
      tn.textContent=x.s&&!x.s1&&needIY(x.mk)?`Sonuç eksik: ilk yarı skoru gelmedi (MS ${x.s}). Elle işaretle:`:"Sonuç eksik. Elle işaretle:"; }); }
  window.pzKupoDeco=kupoDeco;
  let kq=0; const ksched=()=>{ if(kq) return; kq=1; requestAnimationFrame(()=>{ kq=0; try{ kupoDeco(); }catch(e){} }); };
  function obsCp(){ const b=$("cpBox"); if(!b||b.dataset.pzo) return; b.dataset.pzo="1"; try{ new MutationObserver(ksched).observe(b,{childList:true,subtree:true}); }catch(e){} ksched(); }
  obsCp(); setTimeout(obsCp,1500);
  try{ const _rk=renderKupon; renderKupon=function(){ const r=_rk.apply(this,arguments); obsCp(); ksched(); return r; }; }catch(e){}
  // eski kuponlarım: İY gerektiren seçimde sonuç eksikse açıklama
  // ---------- OXXai sohbet: pazar soruları ----------
  const NZ=t=>String(t||"").toLocaleLowerCase("tr").replace(/ç/g,"c").replace(/ğ/g,"g").replace(/ı/g,"i").replace(/ö/g,"o").replace(/ş/g,"s").replace(/ü/g,"u").replace(/â/g,"a")
    .replace(/(\d)\s*[.,]\s*(\d)/g,"$1$2").replace(/[^a-z0-9&]+/g," ").replace(/\s+/g," ").trim();
  window.pzNZ=NZ;
  function teamPos(s,name){ let best=-1; const keys=new Set([NZ(name)]);
    try{ const T=TEAMS.find(t=>t.name===name||tmEq(t.name,name)); if(T) T.keys.forEach(k=>keys.add(NZ(k))); }catch(e){}
    NZ(name).split(" ").filter(w=>w.length>=4&&!/^(fc|sk|spor|club|city|united|real|athletic|deportivo|sporting)$/.test(w)).forEach(w=>keys.add(w));
    for(const k of keys){ if(!k||k.length<2) continue; const re=new RegExp("(^| )"+k.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+"\\w*","g"); let x; while((x=re.exec(s))) best=Math.max(best,x.index); }
    return best; }
  function lastPos(s,re){ let p=-1, x; const g=new RegExp(re.source,"g"); while((x=g.exec(s))) p=x.index; return p; }
  // metinden istenen pazar kodlarını çıkarır (motor kodları). Boş dizi → pazar sorusu değil.
  function detect(raw,m){ const s=NZ(raw); if(!s) return [];
    if(/\b(ne demek\w*|nedir|ne anlama|anlami\w*|manasi|nasil hesap\w*|aciklar misin)\b/.test(s)) return [];
    const out=[];
    const DG=/\b(daha gollu|gollu yari|en gollu|hangi yari\w*)\b/.test(s);
    const IYMS=/\b(iy ?ms|iyms|ilk yari ?(ve )?mac sonu\w*|ilk yari ?\/? ?ms)\b/.test(s);
    const Y2=/\b(ikinci yari\w*|2 yari\w*|2y|ikinci devre\w*|2 devre\w*|ikinci 45)\b/.test(s);
    const Y1=!Y2&&/\b(ilk yari\w*|ilkyari\w*|iy|1 yari\w*|ilk devre\w*|devre\w*|ilk 45)\b/.test(s);
    const KG=/\b(kg|kgv|kgy|karsilikli gol\w*|iki takim da gol\w*|iki takimda gol\w*)\b/.test(s), KGN=/\b(kg yok|kgy|karsilikli gol yok\w*|kg olmaz)\b/.test(s);
    const UST=/\b(ust\w*|over)\b/.test(s), ALT=/\b(alt|alti|altinda|under)\b/.test(s), LN=(/\b(05|15|25|35)\b/.exec(s)||[])[1]||null;
    const GOL=/\bgol\w*\b/.test(s), GOLN=/\b(gol (olmaz|yok|cikmaz|atilmaz|gelmez)|golsuz)\b/.test(s);
    const WIN=/\b(kazan\w*|galip\w*|yener|yenecek|alir|alacak|onde\w*|ustun)\b/.test(s), DRAW=/\b(berabere\w*|beraberlik)\b/.test(s), KIM=/\bkim\b/.test(s);
    const CS=/\b(cifte sans\w*|cs)\b/.test(s)||/\bkaybetmez\b/.test(s);
    // hangi takım?
    let side=null; const ex=/\bms ?([12x])\b/.exec(s)||/(^| )([12x]) ?(ve|&|\+) ?(2 ?5 |25 )?(ust|alt|kg)/.exec(s);
    if(ex) side=(ex[1]&&/^[12x]$/.test(ex[1])?ex[1]:ex[2]).toUpperCase();
    if(!side&&m&&(WIN||/\bkaybetmez\b/.test(s))&&!KIM){ const wp=lastPos(s,/\b(kazan\w*|galip\w*|yener|yenecek|alir|alacak|onde\w*|ustun|kaybetmez)\b/); const ph=teamPos(s.slice(0,wp+1),m.h), pa=teamPos(s.slice(0,wp+1),m.a);
      if(ph>=0||pa>=0) side=ph>pa?"1":"2"; else { const qh=teamPos(s,m.h), qa=teamPos(s,m.a); if(qh>=0&&qa<0) side="1"; else if(qa>=0&&qh<0) side="2"; } }
    if(!side&&DRAW) side="X";
    if(DG){ out.push("DGY1","DGYE","DGY2"); return out; }
    if(IYMS){ const q=/\b(?:iy ?ms|iyms)\s*([12x])\s*([12x])\b/.exec(s)||/\b([12x]) ?\/? ?([12x])\b/.exec(s.replace(/\biy ?ms\b/,""));
      if(q&&/iy ?ms|iyms/.test(s)) out.push(`IYMS_${q[1].toUpperCase()}_${q[2].toUpperCase()}`); else out.push("*IYMS"); return out; }
    if(Y1||Y2){ const H=Y1?"IY":"2Y";
      if(UST||ALT){ const l=LN==="15"?"15":"05"; out.push(H+(ALT&&!UST?"A":"U")+l); }
      else if(GOL&&!KG) out.push(H+(GOLN?"A05":"U05"));
      if(side) out.push(H+side); else if(KIM&&WIN) out.push(H+"1",H+"X",H+"2");
      return out; }
    if(CS&&!out.length){ const t=/\b(1x|x2|12)\b/.exec(s); if(t) out.push(t[1].toUpperCase()); else if(side==="1") out.push("1X"); else if(side==="2") out.push("X2"); else out.push("1X","12","X2"); return out; }
    const line=LN==="15"||LN==="35"||LN==="25"?LN:"25";
    if(side&&(UST||ALT)&&line==="25") out.push(`${side}&${ALT&&!UST?"A25":"U25"}`);
    else if(side&&KG) out.push(`${side}&${KGN?"KGY":"KGV"}`);
    else if(UST||ALT){ if(LN||side) out.push((ALT&&!UST?"A":"U")+line); }
    else if(KG) out.push(KGN?"KGY":"KGV");
    return out; }
  window.pzDetect=detect;
  const CHIP="＋ KUPO'ya ekle: ";
  const BQ=new Map();
  function fxFor(m){ try{ if(m.sp) return FIXTURES.find(x=>x.iid===m.id)||null; return (m.src==="fx"?FIXTURES.find(x=>x.lg===m.lg&&x.h===m.h&&x.a===m.a):FIXTURES.find(x=>x.lg===m.lg&&x.h===m.h&&x.a===m.a)||fxOdds(m))||null; }catch(e){ return null; } }
  function botBlock(m,codes){ const f=fxFor(m), C=ctxOf(m,f); if(!C) return null;
    let L=codes.slice(); if(L[0]==="*IYMS") L=CAT.find(c=>c[0]==="İYMS")[2].filter(e=>C.P[e]!=null).sort((a,b)=>C.P[b]-C.P[a]).slice(0,3);
    L=L.filter(e=>C.P[e]!=null).slice(0,4); if(!L.length) return null;
    const lines=L.map(e=>{ const o=optOf(C,e), cn=calNote(e,o.p); return `<span class="pz-bl">🧮 <b>${esc(o.n)}</b> · ${esc(desc(e,m))}: <b>%${pp(o.p)}</b>${o.o?` (oran ${f2(o.o)})`:` (adil oran ${f2(fair(o.p))})`}${cn?`<small>${esc(cn)}</small>`:""}</span>`; });
    const prim=L.length>1&&codes[0]!=="*IYMS"&&!/^DGY/.test(L[0])&&!/^(IY|2Y)[1X2]$/.test(L[0])&&!["1X","12","X2"].includes(L[0])?L[0]:L.slice().sort((a,b)=>C.P[b]-C.P[a])[0];
    const chips=[prim].concat(L.filter(e=>e!==prim).slice(0,1)).map(e=>{ const t=CHIP+AD[e]; BQ.set(t,{m,e}); return t; });
    return {C,L,html:lines.join(""),chips}; }
  const LEG={KGV:"KG Var",KGY:"KG Yok",U25:"2,5 Üst",A25:"2,5 Alt",U15:"1,5 Üst","1":"MS 1","X":"MS X","2":"MS 2",IYU05:"İY 0,5 Üst"};
  function mergeInto(R,B){ let h=String(R.html||"");
    for(const e of B.L){ const n=LEG[e]; if(!n) continue;
      const rx=new RegExp(`(?:✅|⚠️) <b>${n.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")}</b>: <b>%\\d+</b>(?: \\(oran [\\d.,]+\\))?\\. [^<]*(?:<br>)?`); h=h.replace(rx,"");
      if(e==="IYU05") h=h.replace(/ · İY'de gol \(İY 0,5 Üst\) %\d+/,""); }
    const at=[h.indexOf('<div class="bt-card'),h.indexOf('<small class="v69-g"'),h.indexOf('<small class="v70-g"')].filter(i=>i>=0).sort((a,b)=>a-b)[0];
    h=at!=null?h.slice(0,at).replace(/(<br>)+$/,"")+B.html+h.slice(at):h.replace(/(<br>)+$/,"")+B.html;
    return Object.assign({},R,{html:h,chips:[...new Set([...B.chips,"Tüm tahminleri aç",...(R.chips||[]).filter(c=>!/^＋ KUPO'ya ekle/.test(c))])].slice(0,6)}); }
  if(typeof botAnswer==="function"){ const _ba=botAnswer; botAnswer=async function(raw){ const c0=typeof BOT!=="undefined"?BOT.ctx:null;
      const R=await _ba.apply(this,arguments);
      try{ const c1=typeof BOT!=="undefined"?BOT.ctx:null;
        let m=null; if(c1&&c1!==c0&&c1.kind==="analiz"&&c1.match&&!c1.match.live) m=c1.match;
        if(!m){ // bağlam: önceki maç sorulmuşken yalnız pazar sorusu ("ikinci yarı gol") ve önceki katmanlar anlamadıysa
          const cm=c0&&c0.match; if(!cm||cm.live) return R; const h0=String(R&&R.html||"");
          if(!/tam anlayamadım|kafası biraz karıştı|anlayamadım/.test(h0)) return R;
          const codes=detect(raw,cm); if(!codes.length) return R; const B=botBlock(cm,codes); if(!B) return R;
          try{ BOT.ctx=c0; }catch(e){}
          return {html:`<b>${esc(cm.h)} - ${esc(cm.a)}</b>${B.html}`,chips:[...B.chips,"Tüm tahminleri aç","İlk yarı ne olur"]}; }
        const codes=detect(raw,m); if(!codes.length) return R;
        const B=botBlock(m,codes); if(!B) return R;
        return mergeInto(R&&typeof R==="object"?R:{html:String(R||"")},B); }catch(e){ console.warn("pazar-v104 bot",e); }
      return R; }; }
  document.addEventListener("click",e=>{ const b=e.target.closest&&e.target.closest("#botChips button[data-q]"); if(!b) return; const t=b.dataset.q;
    if(t==="Tüm tahminleri aç"){ const cm=typeof BOT!=="undefined"&&BOT.ctx&&BOT.ctx.match; if(!cm) return; e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
      const go=()=>{ openMatch(cm); setTimeout(()=>{ try{ msGo("oran"); }catch(_){} },60); }; try{ botThen(go); }catch(_){ go(); } return; }
    if(!t||t.indexOf(CHIP)!==0) return;
    e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
    const q=BQ.get(t); if(!q){ toast("Bu seçim artık geçerli değil; maçı yeniden sor"); return; }
    const C=ctxOf(q.m,fxFor(q.m)); if(!C){ toast("Bu maç için pazar olasılığı yok"); return; }
    toggle(C,q.e); const on=inCp(C,toApp(q.e)); b.textContent=on?`✓ KUPO'da: ${AD[q.e]}`:t; b.setAttribute("aria-pressed",on); },true);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: pazar-v104 */
/* id: sonuc-oxx-v104 */ try {
// =====================================================================
// v104 · SONUÇLAR: her biten maçta
//  • "OXXai" rozeti: OXXai'nin maç öncesi KİLİTLİ önerisi. Kaynak: data/archive/GÜN.json (maç başlayınca kilitlenen kayıt: sk/sp →
//    uygulamanın gösterdiği öneri, yoksa rk/rp); arşivde yoksa data/predlog.json (motorun kilitli günlüğü; yalnız ts ≤ başlama saati,
//    öneri kilitli olasılıklardan en olası seçenek). Kilitli kayıt yoksa rozet GÖSTERİLMEZ (sonradan hesaplanan tahmin gösterilmez).
//  • "Sen" rozeti: maç KUPO'daki bir kuponundaysa (açık + eski) seçimin ve sonucu; dokun → KUPO'da o kupon.
//  • Üstte günlük özet şeridi (OXXai x/y · Sen x/y), dokun → pazar bazında karşılaştırma. Kullanıcı verisi yalnız bu telefonda okunur.
// =====================================================================
(function(){
  const ARC=new Map(), ABUSY={}; let PLOG=null, PBUSY=null;
  function arcLoad(d){ if(ARC.has(d)) return Promise.resolve(ARC.get(d)); if(ABUSY[d]) return ABUSY[d];
    return ABUSY[d]=fetch(`data/archive/${d}.json`,{cache:"no-cache"}).then(r=>r.ok?r.json():null).catch(()=>null).then(A=>{ ARC.set(d,A&&typeof A==="object"?A:null); delete ABUSY[d]; return ARC.get(d); }); }
  function plogLoad(){ if(PLOG) return Promise.resolve(PLOG); if(PBUSY) return PBUSY;
    return PBUSY=fetch("data/predlog.json",{cache:"no-cache"}).then(r=>r.ok?r.json():null).catch(()=>null).then(L=>{ PLOG=Array.isArray(L)?L:[]; PBUSY=null; return PLOG; }); }
  window.rsOxxReset=()=>{ ARC.clear(); PLOG=null; };
  const NM=k=>{ try{ return mkName(k); }catch(e){ return k; } };
  const pcs=p=>Math.round((+p||0)*100);
  // OXXai'nin kilitli önerisi (yoksa null)
  function oxxOf(m,day){ const A=ARC.get(day), r=A&&A[String(m.id)];
    if(r&&(r.sk||r.rk)){ const k=r.sk||r.rk, p=r.sk?r.sp:r.rp; if(p!=null&&isFinite(+p)) return {k:String(k),p:+p,src:"arşiv"}; }
    if(PLOG&&m.ts){ const e=PLOG.find(x=>x&&x.d===day&&Array.isArray(x.p)&&x.p.length===3&&x.ts&&tmEq(x.h,m.h)&&tmEq(x.a,m.a));
      const lt=e?Date.parse(String(e.ts)):NaN;
      if(e&&isFinite(lt)&&lt<=m.ts){ const c=[["1",e.p[0]],["X",e.p[1]],["2",e.p[2]]]; if(e.o!=null&&isFinite(+e.o)) c.push(["U",+e.o],["A",1-e.o]);
        const b=c.sort((x,y)=>y[1]-x[1])[0]; return {k:b[0],p:+b[1],src:"günlük",ft:e.ft||null}; } }
    return null; }
  window.rsOxxOf=oxxOf;
  const hit=(k,m,s0)=>{ try{ const r=mkHit(k,m.hs,m.as,m.h1,m.a1,s0); return r==null?null:!!r; }catch(e){ return null; } };
  // kullanıcının kuponlarındaki seçimler (açık + eski), yalnız bu telefondan
  function mineOf(m,day){ const out=[]; try{ const L=(window.KX&&KX.L)||[];
      for(const c of L) for(const it of (c.items||[])){ if(!it||it.sp==="bk") continue;
        const same=(it.iid&&String(it.iid)===String(m.id))||(tmEq(it.h,m.h)&&tmEq(it.a,m.a)&&istDay(new Date(Date.parse(it.dt)))===day);
        if(!same) continue; const ok=it.ok!=null?!!it.ok:hit(it.mk,m,it.s0); out.push({c,it,ok}); } }catch(e){} return out; }
  window.rsMineOf=mineOf;
  const V=ok=>ok===true?`<i class="rs-v y" aria-hidden="true">✓</i>`:ok===false?`<i class="rs-v n" aria-hidden="true">✗</i>`:`<i class="rs-v q" aria-hidden="true">?</i>`;
  const VT=ok=>ok===true?"tuttu":ok===false?"tutmadı":"sonuç eksik";
  function badges(m,day){ const o=oxxOf(m,day), me=mineOf(m,day); let h="";
    if(o){ const ok=hit(o.k,m); o.ok=ok;
      h+=`<span class="rs-ox" role="img" aria-label="OXXai maç öncesi kilitli tahmini: ${esc(NM(o.k))}, yüzde ${pcs(o.p)}, ${VT(ok)}" title="Maç başlamadan kilitlenen OXXai önerisi (${o.src})"><img src="icons/oxxai-mark-crown-s.webp" alt=""><span class="tg">OXXai</span><span class="k">${esc(NM(o.k))} %${pcs(o.p)}</span>${V(ok)}</span>`; }
    const seen=new Set();
    for(const x of me.slice(0,3)){ const key=x.c.id+"|"+x.it.mk; if(seen.has(key)) continue; seen.add(key);
      h+=`<button type="button" class="rs-me" data-rsc="${esc(x.c.id)}" aria-label="Senin seçimin: ${esc(NM(x.it.mk))}, ${VT(x.ok)}, ${esc(x.c.ad)} içinde. KUPO'da aç"><span class="tg">Sen</span><span class="k">${esc(NM(x.it.mk))}</span>${V(x.ok)}<small>${esc(x.c.ad)}</small></button>`; }
    return {html:h?`<div class="rs-bx">${h}</div>`:"",o,me}; }
  // pazar grubu (karşılaştırma tablosu)
  function grp(k){ k=String(k); if(/^G[012G]$/.test(k)) return "Canlı"; if(/^[1X2]$/.test(k)) return "MS"; if(/^(1X|12|X2)$/.test(k)) return "Çifte şans";
    if(/^[UAO]\d|^[UA]$|^[UA][\d.]+$/.test(k)) return "Alt/Üst"; if(/^KG/.test(k)) return "KG"; if(/^(IY[1X2]|I[OU]\d\d|IY[UA]\d\d)$/.test(k)) return "İlk yarı";
    if(/^2Y/.test(k)) return "İkinci yarı"; if(/^IYMS/.test(k)) return "İY/MS"; if(/&(U25|A25)$/.test(k)) return "MS + Alt/Üst"; if(/&KG/.test(k)) return "MS + KG"; if(/^DGY/.test(k)) return "Daha gollü yarı"; return "Diğer"; }
  let OPEN=false;
  function dayLbl(d){ const t=istDay(new Date()), y=istDay(new Date(Date.now()-864e5)); return d===t?"bugün":d===y?"dün":ist(new Date(d+"T12:00:00+03:00"),{day:"numeric",month:"long"}); }
  function strip(list,day){ const O={n:0,h:0}, M={n:0,h:0}, G={}, both={o:0,m:0,n:0};
    for(const m of list){ const o=oxxOf(m,day), ok=o?hit(o.k,m):null, me=mineOf(m,day);
      if(o&&ok!=null){ O.n++; if(ok) O.h++; const g=grp(o.k); (G[g]=G[g]||{o:[0,0],m:[0,0]}).o[0]+=ok?1:0; G[g].o[1]++; }
      const u=new Map(); for(const x of me) if(x.ok!=null) u.set(x.c.id+"|"+x.it.mk,x);
      for(const x of u.values()){ M.n++; if(x.ok) M.h++; const g=grp(x.it.mk); (G[g]=G[g]||{o:[0,0],m:[0,0]}).m[0]+=x.ok?1:0; G[g].m[1]++; }
      if(o&&ok!=null&&u.size){ both.n++; if(ok) both.o++; const x=[...u.values()][0]; if(x.ok) both.m++; } }
    if(!O.n&&!M.n) return "";
    const D=dayLbl(day), r=(a,b)=>b?`${a}/${b}<small>%${Math.round(a/b*100)}</small>`:"–";
    const rows=Object.entries(G).sort((a,b)=>(b[1].o[1]+b[1].m[1])-(a[1].o[1]+a[1].m[1])).map(([g,v])=>`<tr><td>${esc(g)}</td><td>${v.o[1]?`${v.o[0]}/${v.o[1]}<small>%${Math.round(v.o[0]/v.o[1]*100)}</small>`:"–"}</td><td>${v.m[1]?`${v.m[0]}/${v.m[1]}<small>%${Math.round(v.m[0]/v.m[1]*100)}</small>`:"–"}</td></tr>`).join("");
    return `<div class="rs-vsw"><button type="button" class="rs-vs" id="rsVs" aria-expanded="${OPEN}" aria-controls="rsCmp" aria-label="OXXai ${D} ${O.h}/${O.n}${M.n?`, sen ${M.h}/${M.n}`:""}. Karşılaştırmayı ${OPEN?"gizle":"göster"}">
        <span><span class="d">${esc(D.charAt(0).toUpperCase()+D.slice(1))} · biten maçlarda isabet</span><span class="o"><i>OXXai</i><b>${O.h}/${O.n}</b>${O.n?`<small>%${Math.round(O.h/O.n*100)}</small>`:""}</span><span class="m"><i>SEN</i><b>${M.n?`${M.h}/${M.n}`:"–"}</b>${M.n?`<small>%${Math.round(M.h/M.n*100)}</small>`:`<small>KUPO'nda maç yok</small>`}</span></span><em aria-hidden="true">›</em></button>
      <div class="rs-cmp" id="rsCmp"${OPEN?"":" hidden"}><table><thead><tr><th>Pazar</th><th class="o">OXXai</th><th class="m">Sen</th></tr></thead><tbody>${rows}
        <tr><td><b>Toplam</b></td><td><b>${r(O.h,O.n)}</b></td><td><b>${r(M.h,M.n)}</b></td></tr></tbody></table>
        ${both.n?`<p>Aynı <b>${both.n}</b> maçta: OXXai <b>${both.o}</b>, sen <b>${both.m}</b> tutturdun.</p>`:""}
        <p>OXXai: maç başlamadan kilitlenen öneri (kilitli kaydı olmayan maç sayılmaz). Sen: KUPO'ların; bu bilgiler yalnız bu telefonda tutulur, hiçbir yere gönderilmez.</p></div></div>`; }
  function deco(){ try{ const list=$("rsList"), sum=$("rsSum"); if(!list||!sum) return; const c=RS.cache.get(RS.day); const L=c&&c.list; const day=RS.day;
      let w=$("rsVsBox"); if(!w){ w=document.createElement("div"); w.id="rsVsBox"; sum.before(w); }
      if(!L){ w.innerHTML=""; return; }
      w.innerHTML=strip(L,day);
      list.querySelectorAll(".rs-r").forEach(r=>{ const old=r.querySelector(".rs-bx"); if(old) old.remove();
        const tn=(r.querySelector(".ib-tm")||{}).textContent||""; const m=L.find(x=>`${x.h} - ${x.a}`===tn)||L.find(x=>{ const [h,a]=tn.split(" - "); return tmEq(x.h,h)&&tmEq(x.a,a); });
        if(!m) return; r.dataset.rsid=m.id; const B=badges(m,day); if(B.html){ const p=r.querySelector(".rs-p"); (p||r.lastElementChild).insertAdjacentHTML(p?"beforebegin":"afterend",B.html); }
        if(B.o){ const np=r.querySelector(".rs-np"); if(np) np.hidden=true;
          const p=r.querySelector(".rs-p:not(.rs-np)"); if(p&&!p.querySelector(".rs-ml")){ const t=p.firstChild; if(t&&t.nodeType===3&&/🔮/.test(t.textContent)){ t.textContent=t.textContent.replace("🔮",""); p.insertAdjacentHTML("afterbegin",`<span class="rs-ml" title="Güncel model hesabı; kilitli öneri değildir">Model</span>`); } } } }); }catch(e){ console.warn("sonuc-oxx-v104",e); } }
  window.rsOxxDeco=deco;
  let gen=0;
  try{ const _rr=renderRes; renderRes=function(){ const r=_rr.apply(this,arguments); const g=++gen, d=RS.day; deco();
      if(!ARC.has(d)||!PLOG) Promise.all([arcLoad(d),plogLoad()]).then(()=>{ if(g===gen&&RS.day===d) deco(); }); return r; }; }catch(e){}
  document.addEventListener("click",e=>{ const v=e.target.closest&&e.target.closest("#rsVs"); if(v){ OPEN=!OPEN; v.setAttribute("aria-expanded",OPEN); const c=$("rsCmp"); if(c) c.hidden=!OPEN; try{ buzz(5); Sound.tap(); }catch(_){} return; }
    const b=e.target.closest&&e.target.closest(".rs-me[data-rsc]"); if(!b) return; e.preventDefault(); e.stopPropagation();
    const id=b.dataset.rsc, c=(KX.L||[]).find(x=>x.id===id); if(!c){ toast("Bu KUPO artık yok"); return; } try{ buzz(8); }catch(_){}
    if(c.durum==="acik"){ KX.aktif=id; try{ kxSave(); localStorage.setItem("bx-coupon",JSON.stringify(c.items)); paintCoupon(); }catch(_){} kxOpen("cp"); toast(`KUPO · ${c.ad}`); }
    else { kxOpen("eski"); setTimeout(()=>{ const h=document.querySelector(`#kxOld .kx-oh[data-c="${CSS.escape(id)}"]`); if(h){ if(h.getAttribute("aria-expanded")!=="true") h.click();
        setTimeout(()=>{ const h2=document.querySelector(`#kxOld .kx-oh[data-c="${CSS.escape(id)}"]`); if(h2) h2.scrollIntoView({block:"center",behavior:"smooth"}); },80); } },160); } },true);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: sonuc-oxx-v104 */
