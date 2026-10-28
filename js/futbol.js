/* id: rec-v77 */ try {
// =====================================================================
// OXXai v77: Futbol önerilerinde tek doğruluk kaynağı
// Denetim bulgusu: Altın listesi 60 sn önbellekte kalıyordu; veri/kalibrasyon yüklenince Bülten/Power'daki Altın ile
// "Hazır tahminler"deki Altın farklı çıkabiliyordu (ör. yarın: 1 maç ↔ 3 maç). Ayrıca maç başlamadan 30 dk önce Altın
// mührü Bülten'den düşüyor ama Hazır tahminlerde kalıyordu.
// Çözüm: (1) her veri yüklemesinde sürüm (RECV) artar, tüm önbellekler geçersizleşir; (2) Altın kilitlenir: bir maç
// günün Altın'ı olduysa o gün boyunca (başlasa da) Altın kalır, günde en fazla 3 kuralı korunur; (3) her bölüm
// Altın kararını tek yerden (goldOf) okur.
// =====================================================================
(function(){
  window.RECV=window.RECV||0;
  function bump(){ window.RECV++; try{ GOLD.at=0; }catch(e){} GL.cache=null; }
  window.recBump=bump;
  const wrapA=(o,k)=>{ try{ const f=o[k]; if(typeof f!=="function") return; o[k]=function(){ const r=f.apply(this,arguments); if(r&&typeof r.then==="function") return r.then(v=>{ bump(); return v; },e=>{ bump(); throw e; }); bump(); return r; }; }catch(e){} };
  try{ const f=loadData; loadData=function(){ const r=f.apply(this,arguments); return Promise.resolve(r).finally(bump); }; }catch(e){}
  try{ const f=loadFixtures; loadFixtures=function(){ const r=f.apply(this,arguments); return Promise.resolve(r).finally(bump); }; }catch(e){}
  try{ const f=applyFixtureOdds; applyFixtureOdds=function(){ const r=f.apply(this,arguments); bump(); return r; }; }catch(e){}
  try{ if(typeof dailyLoad==="function"){ const f=dailyLoad; dailyLoad=function(){ const r=f.apply(this,arguments); return Promise.resolve(r).finally(bump); }; } }catch(e){}
  wrapA(Pick,"loadEspn");
  // ---- Altın kilidi ----
  const GL={cache:null, src:null, key:"bx-gold-lock2"};   // 2: Altın oran alt sınırı 1,15 ile kilitler sıfırlandı
  function rd(){ try{ return JSON.parse(localStorage.getItem(GL.key)||"{}"); }catch(e){ return {}; } }
  function wr(o){ try{ const keep={}, t0=istDay(new Date(Date.now()-2*864e5)); for(const d in o) if(d>=t0) keep[d]=o[d]; localStorage.setItem(GL.key,JSON.stringify(keep)); }catch(e){} }
  const _gc=goldCalc;
  goldCalc=function(){ const S=_gc(); if(GL.cache&&GL.src===S) return GL.cache;
    const lock=rd(), byDay={}, out=new Map(), list=Pick.list();
    for(const [k,x] of S){ (byDay[istDay(x.m.dt)]=byDay[istDay(x.m.dt)]||[]).push([k,x]); }
    const days=new Set([...Object.keys(byDay),...Object.keys(lock)]);
    for(const d of days){ const L=lock[d]||[], fresh=byDay[d]||[], items=[];
      for(const k of L){ const f=fresh.find(e=>e[0]===k); if(f){ items.push(f); continue; }
        const m=list.find(mm=>{ try{ return fkey(mm)===k; }catch(e){ return false; } }); if(!m) continue;
        try{ const fx=m.src==="fx"?FIXTURES.find(x=>x.lg===m.lg&&x.h===m.h&&x.a===m.a):fxOdds(m); if(!fx||!fx.odds) continue; const p=quickPred(m,fx); const R=recOf({H:p.pm[0],D:p.pm[1],A:p.pm[2],o25:p.o25m},fx); if(R) items.push([k,{m,f:fx,R,p,locked:true}]); }catch(e){} }
      for(const e of fresh){ if(items.length>=GOLD.perDay) break; if(!items.some(i=>i[0]===e[0])) items.push(e); }
      items.slice(0,GOLD.perDay).forEach(([k,x])=>out.set(k,x));
      const ks=items.slice(0,GOLD.perDay).map(i=>i[0]); if(ks.length&&d>=istDay(new Date())) lock[d]=ks; }
    wr(lock); GL.cache=out; GL.src=S; return out; };
  // Hazır tahminler Altın kararını tek yerden okur
  try{ const _tc=tpCands; tpCands=function(){ const L=_tc.apply(this,arguments); for(const x of L) x.gold=!!goldOf(x.m); return L; }; }catch(e){}
  bump();
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: rec-v77 */
/* id: gate-v78 */ try {
// =====================================================================
// OXXai v78: Sade onay — giriş ve "ana ekrana ekle" tek dokunuşla.
// Tam Kullanım Koşulları ve KVKK metni bir dokunuşla açılır; düğmenin hemen altında "devam ederek kabul edersin" yazar.
// Kayıt aynı: bx-terms {v, at, kvkk:true, yas18:true}. Ayarlar'daki "Kullanım koşulları" ekranı (tam metin) aynen kalır.
// =====================================================================
(function(){
  const _st=showTerms;
  function doc(title,html){ const old=$("g2doc"); if(old) old.remove(); const d=document.createElement("div"); d.className="gate g2"; d.id="g2doc"; d.style.zIndex=97;
    d.innerHTML=`<div class="gbox" role="dialog" aria-modal="true"><h2>${title}</h2><div class="g2-doc terms">${html}</div><button class="g2-go" type="button" id="g2docX">Tamam</button></div>`;
    document.body.appendChild(d); $("g2docX").onclick=()=>{ d.classList.add("out"); setTimeout(()=>d.remove(),250); }; }
  showTerms=function(gate){ if(!gate) return _st.apply(this,arguments);
    const old=$("gate"); if(old) old.remove();
    const el=document.createElement("div"); el.className="gate g2"; el.id="gate";
    el.innerHTML=`<div class="gbox" role="dialog" aria-modal="true" aria-labelledby="gT">
      <img class="glogo" src="icons/oxxai-logo.webp" alt="OXXai">
      <h2 id="gT">OXXai'ye hoş geldin 👋</h2>
      <ul class="g2-l">
        <li><span>⚽</span><div>Hobi amaçlı maç tahmini ve takip aracı. <b>Şans oyunu değildir</b>, para almaz.</div></li>
        <li><span>📊</span><div>Tahminler olasılıktır, <b>garanti değildir</b>.</div></li>
        <li><span>🔒</span><div>Hesap yok; listelerin yalnız bu telefonda kalır.</div></li>
      </ul>
      <label class="g2-chk"><input type="checkbox" id="gAll"><span><b>18 yaşını doldurdum.</b> OXXai'nin şans oyunu olmadığını ve tahminlerin garanti olmadığını anladım. <button type="button" id="gT1">Kullanım Koşulları</button>'nı ve <button type="button" id="gT2">KVKK Aydınlatma Metni</button>'ni okudum, kabul ediyorum.</span></label>
      <button class="g2-go" id="gGo" type="button" disabled>Onaylıyorum, devam et</button>
      <p class="g2-s">Yasa dışı şans oyunları suçtur · Destek: 115 (YEDAM)</p>
    </div>`;
    document.body.appendChild(el);
    $("gT1").onclick=e=>{ e.preventDefault(); e.stopPropagation(); doc("Kullanım Koşulları",TERMS_HTML); }; $("gT2").onclick=e=>{ e.preventDefault(); e.stopPropagation(); doc("KVKK Aydınlatma Metni",KVKK_HTML); };
    $("gAll").onchange=()=>{ $("gGo").disabled=!$("gAll").checked; try{ buzz(6); }catch(e){} };
    $("gGo").onclick=()=>{ if(!$("gAll").checked) return; try{ localStorage.setItem("bx-terms",JSON.stringify({v:TERMS_VER, at:Date.now(), kvkk:true, yas18:true, bahisDegil:true, kosullar:true, onay:"tek kutu"})); }catch(e){}
      try{ Count.call("hit","accept"); }catch(e){} try{ buzz(10); Sound.ready(); }catch(e){} el.classList.add("out"); setTimeout(()=>el.remove(),350);
      if(window._pendInst){ window._pendInst=false; setTimeout(()=>doInstall(),380); } };
    };
  // ana ekrana ekle: tek dokunuş
  doInstall=function(){ if(!termsAccepted()){ window._pendInst=true; showTerms(true); return; }
    const old=$("instGate"); if(old) old.remove();
    const el=document.createElement("div"); el.className="gate g2"; el.id="instGate";
    el.innerHTML=`<div class="gbox" role="dialog" aria-modal="true" aria-labelledby="iT"><img class="glogo" src="icons/oxxai-logo.webp" alt="OXXai">
      <h2 id="iT">Ana ekrana ekle</h2>
      <ul class="g2-l"><li><span>📲</span><div>OXXai telefonunda uygulama gibi açılır.</div></li><li><span>🔒</span><div>Listelerin yalnız bu cihazda kalır; simgeyi silersen listeler de silinebilir.</div></li></ul>
      <button class="g2-go" id="iGo" type="button">Ana ekrana ekle</button><button class="g2-no" id="iNo" type="button">Şimdi değil</button></div>`;
    document.body.appendChild(el);
    $("iNo").onclick=()=>{ el.classList.add("out"); setTimeout(()=>el.remove(),300); };
    $("iGo").onclick=()=>{ try{ const t=JSON.parse(localStorage.getItem("bx-terms")||"{}"); t.inst=Date.now(); localStorage.setItem("bx-terms",JSON.stringify(t)); }catch(e){}
      el.classList.add("out"); setTimeout(()=>el.remove(),300); try{ buzz(10); }catch(e){} return _doInstallL(); }; };
  // açılışta eski (uzun) onay ekranı açıksa sade olanla değiştir
  const g=$("gate"); if(g&&!termsAccepted()&&!g.classList.contains("g2")) showTerms(true);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: gate-v78 */
/* id: bulten-v80 */ try {
// =====================================================================
// OXXai v80: Bülten'de de gerçek altın renkli "Altın kupon" — Canlı'daki mantığın maç öncesi hâli.
// Seçili bülten gününün başlamamış maçlarından (en az 5 dk sonra başlayan) %78+ olasılıklı, açık oranlı seçimler;
// farklı maçlardan 2–4 seçim, birlikte tutma olasılığı %75+ kalan en yüksek oranlı kombinasyon; yoksa %85+ tek seçim.
// Olasılıklar Bülten'deki ile aynıdır (aynı model, aynı kalibrasyon). Kupondaki maçlar listede altın çerçeveyle işaretlenir.
// =====================================================================
(function(){
  const TH=.75, SOLO=.85, MINP=.78; let open=false, lastSig="";
  function cands(){ const day=BT.day||istDay(new Date()), now=Date.now(), out=[];
    for(const m of Pick.list()){ if(m.live||m.started) continue; const t=m.dt.getTime(); if(t<now+5*60e3||istDay(m.dt)!==day) continue;
      const f=m.src==="fx"?FIXTURES.find(x=>x.lg===m.lg&&x.h===m.h&&x.a===m.a):fxOdds(m); if(!f||!f.odds) continue;
      let p=null; try{ p=quickPred(m,f); }catch(e){} if(!p||!p.pm) continue;
      let R=null; try{ R=recOf({H:p.pm[0],D:p.pm[1],A:p.pm[2],o25:p.o25m},f); }catch(e){}
      if(R&&R.o&&R.o>=1.05&&R.cp>=MINP) out.push({m,R,f,p}); }
    return out.sort((a,b)=>b.R.cp-a.R.cp).slice(0,12); }
  function build(){ const c=cands(); let best=null;
    (function rec(i,sel,p,o){ if(sel.length>=2&&p>=TH&&(!best||o>best.o+1e-9)) best={sel:sel.slice(),p,o};
      if(sel.length>=4) return; for(let j=i;j<c.length;j++){ const np=p*c[j].R.cp; if(np<TH) continue; sel.push(c[j]); rec(j+1,sel,np,o*c[j].R.o); sel.pop(); } })(0,[],1,1);
    if(!best){ const s=c.find(x=>x.R.cp>=SOLO); if(s) best={sel:[s],p:s.R.cp,o:s.R.o}; }
    return best; }
  const of2=o=>(+o).toLocaleString("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2});
  function dayLbl(){ const d=BT.day||istDay(new Date()); return d===istDay(new Date())?"Bugün":d===istDay(new Date(Date.now()+864e5))?"Yarın":ist(new Date(d+"T12:00:00+03:00"),{weekday:"long"}); }
  function paint(){ const v=$("v-bulten"), list=$("btList"); if(!v||!list) return;
    let b=$("bgBtn"); if(!b){ b=document.createElement("button"); b.type="button"; b.id="bgBtn"; b.className="lg-btn"; b.style.marginTop="10px";
      b.onclick=()=>{ open=!open; try{ buzz(8); Sound.tap(); }catch(e){} paint(); }; }
    let pan=$("bgPan"); if(!pan){ pan=document.createElement("div"); pan.id="bgPan"; pan.className="lg-pan"; pan.hidden=true; }
    if(list.previousElementSibling!==pan){ list.before(b); b.after(pan); }
    const hide=BT.f==="live"||!!BT.q; b.hidden=hide; if(hide){ pan.hidden=true; return; }
    const K=build(); document.querySelectorAll("#btList .lg-on").forEach(e=>e.classList.remove("lg-on"));
    if(!K){ b.classList.add("off"); pan.hidden=true; b.setAttribute("aria-expanded","false");
      b.innerHTML=`<span class="lg-ic">🥇</span><span class="lg-t"><b>${esc(dayLbl())} altın KUPO</b><small>Taranıyor · bu gün için yeterince güvenli kombinasyon yok</small></span>`; lastSig=""; return; }
    const sig=K.sel.map(x=>fkey(x.m)+x.R.k).join("|"); if(sig!==lastSig){ b.classList.remove("new"); void b.offsetWidth; if(lastSig) b.classList.add("new"); lastSig=sig; }
    b.classList.remove("off"); b.setAttribute("aria-expanded",String(open));
    b.innerHTML=`<span class="lg-ic">🥇</span><span class="lg-t"><b>${esc(dayLbl())} altın KUPO · ${K.sel.length} maç</b><small>Birlikte tutma olasılığı · toplam oran ${of2(K.o)} · ${open?"kapat":"dokun, gör"}</small></span><span class="lg-p">%${pc9(K.p)}</span>`;
    const ks=new Set(K.sel.map(x=>fkey(x.m)));
    document.querySelectorAll("#btList .ib-r[data-i]").forEach(r=>{ try{ const x=IB.rows[+r.dataset.i]; if(x&&x.m&&ks.has(fkey(x.m))) r.classList.add("lg-on"); }catch(e){} });
    pan.hidden=!open; if(!open) return;
    pan.innerHTML=K.sel.map(x=>{ const m=x.m; return `<div class="pw-r"${omA(m)}><div class="pw-m"><b>${esc(m.h)} - ${esc(m.a)}</b><small>${goldOf(m)?"🥇 ":""}${esc(ist(m.dt,{hour:"2-digit",minute:"2-digit"}))} · ${esc((x.f&&(x.f.cn||x.f.ln))||(LEAGUES[m.lg]||{n:""}).n)}</small></div><div class="pw-s"><span>${esc(x.R.n)}</span><b>%${pc9(x.R.cp)}</b><i>${of2(x.R.o)}</i></div></div>`; }).join("")
      +`<button type="button" class="lg-add" id="bgAdd">+ Altın seçimleri KUPO'ya ekle</button><p class="lg-n">Seçili günün başlamamış maçları her veri yenilemesinde yeniden taranır; maç başlayınca KUPO'dan çıkar. %${Math.round(TH*100)}+ birlikte tutma bile kesinlik değildir · 18+</p>`;
    $("bgAdd").onclick=()=>{ buzz([10,30,10]); let n=0; for(const x of K.sel){ if(!CP.items.some(c=>c.k===cpKey(x.m)&&c.mk===x.R.k)){ cpToggle(x.m,x.R.k,+x.R.o,x.R.cp); n++; } } try{ paintCoupon(); }catch(e){} toast(n?`🥇 ${n} seçim KUPO'ya eklendi`:"Bu seçimler zaten KUPO'nda"); }; }
  window.bgPaint=paint;
  const _rb=renderBulten; renderBulten=function(){ const r=_rb.apply(this,arguments); try{ paint(); }catch(e){} return r; };
  setInterval(()=>{ const v=$("v-bulten"); if(v&&!v.hidden&&!document.hidden) try{ paint(); }catch(e){} },60e3);
  try{ paint(); }catch(e){}
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: bulten-v80 */
/* id: sade-v81 */ try {
// =====================================================================
// OXXai v81: Sade ekranlar (UX denetimi önerileri). Teknik/uzun/tekrarlı bloklar kapanır kutuya alınır; açık/kapalı
// tercihi hatırlanır. Ekranlar yeniden çizildikçe (MutationObserver) kurallar kendiliğinden yeniden uygulanır.
// =====================================================================
(function(){
  let OPEN=new Set(); try{ OPEN=new Set(JSON.parse(localStorage.getItem("bx-sx")||"[]")); }catch(e){}
  const saveO=()=>{ try{ localStorage.setItem("bx-sx",JSON.stringify([...OPEN].slice(-60))); }catch(e){} };
  function wrap(el,key,title,sub){ if(!el||!el.parentNode) return null; const p=el.parentNode;
    if(p.classList&&p.classList.contains("sx-in")) return p.parentNode;
    const d=document.createElement("details"); d.className="sx"; d.dataset.k=key; if(OPEN.has(key)) d.open=true;
    d.innerHTML=`<summary>${title}${sub?` <small>${sub}</small>`:""}</summary><div class="sx-in"></div>`;
    p.insertBefore(d,el); d.querySelector(".sx-in").appendChild(el);
    d.addEventListener("toggle",()=>{ d.open?OPEN.add(key):OPEN.delete(key); saveO(); }); return d; }
  const txt=e=>((e&&e.textContent)||"").trim();
  function apply(){
    try{ wrap($("legal"),"legal","Kullanım koşulları ve KVKK (tam metin)"); }catch(e){}
    try{ document.querySelectorAll("#v-rehber .wrap > .panel, #v-rehber > .panel").forEach(p=>{ const h=txt(p.querySelector("h2")); if(/nasıl çalış/i.test(h)) wrap(p,"reh-nasil","Nasıl çalışır?"); else if(/veri/i.test(h)&&!/telefon/i.test(h)) wrap(p,"reh-veri","Veri kaynakları"); }); }catch(e){}
    try{ const T=$("kzTech"); if(T) T.querySelectorAll(":scope > .panel").forEach((p,i)=>{ const h=txt(p.querySelector("h2"))||("Bölüm "+(i+1)); wrap(p,"kz-"+h.slice(0,24),esc(h)); }); }catch(e){}
    try{ document.querySelectorAll("#karne > .panel").forEach(p=>{ if(/Maç öncesi kilitli/.test(txt(p.querySelector("h2")))) wrap(p,"kz-mo","Maç öncesi ayrıntılar"); }); }catch(e){}
    try{ const tp=$("tpBox"); if(tp&&tp.innerHTML){ const n=tp.querySelectorAll(".tp-r").length; const d=wrap(tp,"tp","🥇 Hazır tahminler",n?n+" tahmin":""); if(d){ const s=d.querySelector("summary small"); if(s) s.textContent=n?n+" tahmin":""; } } }catch(e){}
    try{ document.querySelectorAll("#v-power .pw-body > .pw-card").forEach(c=>{ const h=txt(c.querySelector(".pw-h span"));
      if(/Canlı tekli yıldız/.test(h)&&!c.querySelector(".pw-line")) c.style.display="none";
      else if(/en güçlü öneriler/.test(h)) wrap(c,"pw-guclu","Bugünün en güçlü önerileri",c.querySelectorAll(".pw-line").length+" maç"); }); }catch(e){}
    try{ const n=document.querySelector("#v-canli .wrap > p.note"); if(n) wrap(n,"canli-not","Gol uyarısı nasıl çalışır?"); }catch(e){}
    try{ const p=document.querySelector("#v-sonuc .wrap > .panel"); if(p&&/sonuçlarını gir/i.test(txt(p.querySelector("h2")))) wrap(p,"snc-not","Sonuçlar nasıl işlenir?"); }catch(e){}
    try{ document.querySelectorAll(".lgchips").forEach((c,i)=>{ const n=c.querySelectorAll('button[aria-pressed="true"]').length; const d=wrap(c,"lg-"+i,"Ligleri göster / düzenle",n+" seçili"); if(d){ const s=d.querySelector("summary small"); if(s) s.textContent=n+" seçili"; } }); }catch(e){}
    try{ const g=$("gelList"); if(g&&!g.querySelector(":scope > details.sx")){ const hs=[...g.querySelectorAll(":scope > h3.gel-d")]; if(hs.length>1){ const d=document.createElement("details"); d.className="sx"; d.dataset.k="gel-eski"; if(OPEN.has("gel-eski")) d.open=true;
        d.innerHTML=`<summary>Önceki güncellemeler <small>${hs.length-1} gün</small></summary><div class="sx-in"></div>`; const inn=d.querySelector(".sx-in"); let n=hs[1]; g.insertBefore(d,n); while(d.nextSibling) inn.appendChild(d.nextSibling);
        d.addEventListener("toggle",()=>{ d.open?OPEN.add("gel-eski"):OPEN.delete("gel-eski"); saveO(); }); } } }catch(e){}
  }
  let raf=0; const mo=new MutationObserver(()=>{ if(raf) return; raf=requestAnimationFrame(()=>{ raf=0; mo.disconnect(); try{ apply(); }finally{ mo.observe(document.body,{childList:true,subtree:true}); } }); });
  apply(); mo.observe(document.body,{childList:true,subtree:true});
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: sade-v81 */
/* id: canli-ara-v84 */ try {
// v84: Canlı sekmesinde maç arama — takım veya lig adıyla canlı listeyi süzer (futbol ve basketbol)
(function(){
  IDLV.q="";
  const _l=idlListHtml; idlListHtml=function(sp,q){ if(q===undefined){ const v=$("v-canli"); if(v&&!v.hidden&&IDLV.q) q=IDLV.q; } return _l.call(this,sp,q); };
  function mount(){ const cw=document.querySelector("#v-canli .wrap"); if(!cw||$("cvQ")) return;
    const el=document.createElement("div"); el.className="cv-q"; el.id="cvQ"; el.onclick=e=>{ if(e.target===el) $("cvQi").focus(); };
    el.innerHTML=`<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg><input id="cvQi" type="search" placeholder="Canlı maç ara: takım veya lig" autocomplete="off" enterkeyhint="search" aria-label="Canlı maç ara"><button type="button" id="cvQx" aria-label="Aramayı temizle" hidden>✕</button>`;
    const idl=$("idlBox"); idl?idl.before(el):cw.prepend(el);
    let t; $("cvQi").oninput=e=>{ clearTimeout(t); t=setTimeout(()=>{ IDLV.q=e.target.value.trim(); $("cvQx").hidden=!IDLV.q; try{ idlRenderAll(); }catch(_){} try{ cvLegacy(); }catch(_){} },180); };
    $("cvQx").onclick=()=>{ $("cvQi").value=""; IDLV.q=""; $("cvQx").hidden=true; try{ idlRenderAll(); }catch(_){} try{ cvLegacy(); }catch(_){} $("cvQi").focus(); }; }
  // yedek liste (resmi bülten alınamazsa görünen ESPN listesi) için basit süzme
  function cvLegacy(){ const L=$("liveList"); if(!L) return; const q=(IDLV.q||"").toLocaleLowerCase("tr");
    L.querySelectorAll(":scope > *").forEach(x=>{ x.style.display=!q||x.textContent.toLocaleLowerCase("tr").includes(q)?"":"none"; }); }
  window.cvLegacy=cvLegacy;
  // arama kutusu her zaman altın kupon ile liste arasında kalsın
  const _ira=idlRenderAll; idlRenderAll=function(){ const r=_ira.apply(this,arguments); try{ mount(); const el=$("cvQ"), idl=$("idlBox"); if(el&&idl&&el.nextElementSibling!==idl) idl.before(el); if(IDLV.q) cvLegacy(); }catch(e){} return r; };
  mount();
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: canli-ara-v84 */
/* id: tahmin-canli-v85 */ try {
// =====================================================================
// OXXai v85: "Maç tahmini yap" ekranında oynanan/bitmiş maç koruması.
// Hata: Gimnastic 4-1 öndeyken (devre arası) form, maç öncesi modelle "MS 2 · 1-2" veriyordu; takımlar lig listesinde
// olmadığı için varsayılan lig (Süper Lig) ve sıfır form ile hesaplıyordu.
// Çözüm: Tahmin et'e basıldığında iki takım bültende/canlıda aranır.
//  • Maç oynanıyorsa: maç öncesi tahmin GÖSTERİLMEZ; skor + dakika ve canlı model tahmini (skoru hesaba katan) gösterilir.
//  • Maç bitmişse: sonuç gösterilir, tahmin yapılmaz.
//  • Maç bültendeyse (başlamamış): oranlı bülten tahmini önerilir; takımlar modelin liginde değilse uyarı gösterilir.
// =====================================================================
(function(){
  const of2=o=>(+o).toFixed(2).replace(".",",");
  function find(h,a){ try{ const L=omPool(); return L.find(m=>tmEq(m.h,h)&&tmEq(m.a,a))||L.find(m=>tmEq(m.h,a)&&tmEq(m.a,h))||null; }catch(e){ return null; } }
  function liveInfo(m){ if(m.sp!==1) return null; try{ const P=idlPred(m), K=idlPick(m,P); if(!P||!K) return null; const C=liveCal(K.best.p); return {P,K,cp:Math.min(C.p,.99)}; }catch(e){ return null; } }
  function isLive(m){ return !!(m.sp||m.live||m.started); }
  function isDone(m){ return !!(m.done||m.finished||/bitti|ms$|ft/i.test(String(m.status||m.st||""))); }
  let force=false;
  document.addEventListener("submit",e=>{ if(e.target.id!=="f"||force) return;
    const h=($("hn").value||"").trim(), a=($("an").value||"").trim(); if(!h||!a) return;
    const m=find(h,a); if(!m) return;
    const out=$("out"); if(!out) return;
    if(isLive(m)||isDone(m)){
      e.preventDefault(); e.stopImmediatePropagation();
      const L=liveInfo(m), sc=(m.hs!=null?m.hs:"?")+"-"+(m.as!=null?m.as:"?"), clk=(()=>{ try{ return idlClockTxt(m); }catch(_){ return m.clock||"oynanıyor"; } })();
      out.innerHTML=`<div class="panel tc-live"><div class="tc-h">${m.sp||m.live?"🔴 Bu maç şu an oynanıyor":"⏱ Bu maç başladı ya da bitti"}</div>
        <div class="tc-s"><b>${esc(m.h)}</b><span>${esc(sc)}</span><b>${esc(m.a)}</b></div><div class="tc-c">${esc(clk)}${m.comp?" · "+esc(m.comp):""}</div>
        ${L?`<div class="recbig rec-${L.cp>=.7?"g":L.cp>=.58?"m":"w"}" style="margin:10px 0"><small>OXXai CANLI TAHMİNİ · skor ve dakika hesaba katıldı</small><b>${esc(L.K.best.n)}</b><div class="rb-p">Olasılık <em>%${pc9(L.cp)}</em>${L.K.best.o?` · oran <em>${of2(L.K.best.o)}</em>`:""}</div><p>Tahmini son skor: <b>${esc(L.P.ft)}</b> · 1 %${pc9(L.P.H)} · X %${pc9(L.P.D)} · 2 %${pc9(L.P.A)}</p></div>`
          :`<p class="note">Canlı tahmin için resmi bülten verisi bekleniyor.</p>`}
        <p class="note" style="margin:6px 0 10px">Maç başladığı için <b>maç öncesi tahmin geçerli değil</b>; oyundaki skor ve kalan süre sonucu belirler.</p>
        <button type="button" class="btn" id="tcOpen">Canlı maç ekranını aç</button>
        <button type="button" class="btn ghost" id="tcPre" style="margin-top:8px">Yine de maç öncesi hesabı göster (yalnız bilgi)</button></div>`;
      $("tcOpen").onclick=()=>{ try{ buzz(8); openAny(m); }catch(_){} };
      $("tcPre").onclick=()=>{ force=true; try{ $("f").requestSubmit(); }finally{ setTimeout(()=>{ force=false; const o=$("out"); if(o) o.insertAdjacentHTML("afterbegin",`<div class="panel tc-warn">⚠️ Aşağıdaki hesap maç başlamadan önceki duruma göredir; maç şu an ${esc(sc)} sürüyor.</div>`); },1400); } };
      out.scrollIntoView({behavior:"smooth",block:"start"}); return; }
    // başlamamış ve bültende var: oranlı bülten tahminini öner (form, lig listesinde olmayan takımlar için zayıf kalır)
    setTimeout(()=>{ const o=$("out"); if(!o||o.querySelector(".tc-tip")) return; let R=null; try{ const f=m.src==="fx"?FIXTURES.find(x=>x.lg===m.lg&&x.h===m.h&&x.a===m.a):fxOdds(m); const p=quickPred(m,f); R=recOf({H:p.pm[0],D:p.pm[1],A:p.pm[2],o25:p.o25m},f); }catch(_){}
      const unk=!(LEAGUES[$("lig").value]&&(m.lg===$("lig").value));
      if(R) o.insertAdjacentHTML("afterbegin",`<div class="panel tc-tip">📋 Bu maç bültende var. Bültendeki oranlı tahmin: <b>${esc(R.n)} %${pc9(R.cp)}</b>${R.o?" · oran "+of2(R.o):""}.${unk?" <b>Not:</b> takımlar seçili ligde değil; aşağıdaki form hesabı yaklaşıktır, bülten tahmini daha güvenilirdir.":""} <button type="button" class="linkbtn" id="tcOpen2">Maç ekranını aç ›</button></div>`);
      const b=$("tcOpen2"); if(b) b.onclick=()=>openAny(m); },2200);
  },true);
  // OXXai: canlı maç sorusunda maç öncesi değil canlı tahmin
  const NZ=t=>String(t||"").toLocaleLowerCase("tr").replace(/ç/g,"c").replace(/ğ/g,"g").replace(/ı/g,"i").replace(/ö/g,"o").replace(/ş/g,"s").replace(/ü/g,"u").replace(/[^a-z0-9 ]/g," ").replace(/\s+/g," ").trim();
  const key=n=>NZ(n).split(" ").filter(w=>w.length>=4&&!/^(club|futbol|sport|united|city|real|deportivo|atletico|sporting)$/.test(w));
  if(typeof botAnswer==="function"){ const _ba=botAnswer; botAnswer=async function(raw){ try{ const n=" "+NZ(raw)+" ";
      const L=(IDL.live[1]||[]).concat(IDL.live[2]||[]); let hit=null;
      for(const m of L){ const kh=key(m.h), ka=key(m.a); const h=kh.some(w=>n.includes(" "+w+" ")), a=ka.some(w=>n.includes(" "+w+" ")); if(h&&a){ hit=m; break; } if(!hit&&(h||a)&&(kh.concat(ka)).some(w=>w.length>=6&&n.includes(" "+w+" "))) hit=m; }
      if(hit){ const Li=liveInfo(hit), clk=(()=>{ try{ return idlClockTxt(hit); }catch(_){ return "oynanıyor"; } })();
        return {html:`🔴 <b>${esc(hit.h)} ${hit.hs}-${hit.as} ${esc(hit.a)}</b> · ${esc(clk)}${hit.comp?" · "+esc(hit.comp):""}<br>`+(Li?`Canlı tahmin (skor ve dakika hesaba katıldı): <b>${esc(Li.K.best.n)} %${pc9(Li.cp)}</b>${Li.K.best.o?" · oran "+of2(Li.K.best.o):""} · tahmini son skor <b>${esc(Li.P.ft)}</b>.`:"Canlı tahmin için bülten verisi bekleniyor.")+`<br><small>Maç başladığı için maç öncesi tahmin geçerli değil. Garanti değildir.</small>`,chips:["Canlı maçlar","Canlı altın KUPO"]}; }
    }catch(e){} return _ba.apply(this,arguments); }; }
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: tahmin-canli-v85 */
/* id: oxxai-bot-v88 */ try {
// v88→v111: OXXai sohbet asistanı kimliği (üst çubuk düğmesi işareti + sohbet açılış afişi: taçlı tam logo + "OXXai")
(function(){
  function hdr(){ const b=$("hdrBot"); if(b&&!b.querySelector(".bb-img")){ const i=document.createElement("span"); i.className="bb-img"; i.setAttribute("aria-hidden","true"); b.prepend(i); } }
  function hero(){ const L=$("botLog"); if(L&&!$("bbHero")){ const d=document.createElement("div"); d.id="bbHero"; d.className="oxban"; d.setAttribute("role","img"); d.setAttribute("aria-label","OXXai sohbet asistanı");
    d.innerHTML=`<img src="icons/oxxai-logo.webp" alt="" width="200" height="200" loading="lazy" decoding="async"><b>OXX<i>ai</i><span> · sohbet asistanı</span></b>`; L.prepend(d); } }
  const _o=botOpen; botOpen=function(){ const r=_o.apply(this,arguments); try{ hero(); }catch(e){} return r; };
  hdr(); setTimeout(hdr,1500); setTimeout(hdr,4500);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: oxxai-bot-v88 */
