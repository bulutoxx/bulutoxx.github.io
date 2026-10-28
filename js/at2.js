/* id: at2-v106 */ try {
// =====================================================================
// v106 · AT YARIŞI 2.0 — lab/at/TASARIM.md Aşama 1 (iskelet + sekmeler) ve Aşama 2 (koşu kartı, profiller, takip, istatistik)
// • at-v73 çekirdeği (BX_AT: AT, merged, cRace, load, render, goldOfDay, padok) SARILIR; veri ve OXXai cevapları aynen kalır.
// • Eski render() gizli #atBox'a yazmaya devam eder (atkupon-v98 deco'su ve geriye uyum için); her yeni veri çiziminde
//   bu ekran yeniden boyanır. Yeni ekranlar #at2Box'ta, sekmeler uygulamanın yapışkan .at-head kabında (#at2Nav).
// • Yollar: #at · #at/{bugun|program|turler|sonuc|kupon} (sekme: replaceState) · #at/kosu/<id> · #at/at/<id>/<no>
//   · #at/jokey/<ad> · #at/antrenor/<ad> · #at/takip · #at/istatistik (detay: pushState → tarayıcı geri tuşu çalışır).
// • Kupon: atkupon-v98'in kurucusu (data-atkr / data-atkh / data-atka → openB) ve KX deposu kullanılır; ayrı kupon yok.
// • Takip: "bx-at-fav" (at adları dizisi) aynen kalır; jokey ve antrenör "bx-at-takip" anahtarına eklenir.
// Veri yalnız depodaki türetilmiş dosyalardan; tjk.org'a istek yok, şans oyunu sitesine bağlantı yok, para tutarı yok · 18+.
// =====================================================================
(function(){
  const X=window.BX_AT; if(!X||!X.AT) return;
  const AT=X.AT, sec=$("v-at"); if(!sec) return;
  const head=sec.querySelector(".at-head"), wrap=sec.querySelector(".wrap"), old=$("atBox"); if(!head||!wrap||!old) return;
  // ---------- yardımcılar ----------
  const E=s=>s==null?"":esc(s);
  const enc=encodeURIComponent, dec=s=>{ try{ return decodeURIComponent(s); }catch(e){ return s; } };
  const K=kid=>String(kid).split("/").map(enc).join("~"), unK=s=>String(s).split("~").map(dec).join("/");
  const lsG=(k,d)=>{ try{ const v=localStorage.getItem(k); return v==null?d:v; }catch(e){ return d; } };
  const lsS=(k,v)=>{ try{ localStorage.setItem(k,v); }catch(e){} };
  const P=(x,d)=>x==null||!isFinite(x)?"–":"%"+(x*100).toLocaleString("tr-TR",{maximumFractionDigits:d==null?(x<.1&&x>0?1:0):d});
  const fx=(x,d=2)=>x==null||!isFinite(+x)?"–":(+x).toLocaleString("tr-TR",{minimumFractionDigits:d,maximumFractionDigits:d});
  const tsOf=(d,s)=>Date.parse(d+"T"+(s||"23:59")+":00+03:00");
  const NOW=()=>Date.now();
  const dayOf=kid=>String(kid||"").split("/")[0];
  const tap=()=>{ try{ buzz(6); }catch(e){} };
  const S={mode:lsG("bx-at2-mod","sade")==="merakli"?"merakli":"sade",sort:"p",bt:lsG("bx-at2-bt","altili")==="turler"?"turler":"altili",
    hip:"",hipU:false,pickTur:null,pdOpen:false,kk:null,last:"",sig:""};
  if(!AT.sev) AT.sev=lsG("bx-at2-sev","orta");
  // ---------- takip (geriye uyumlu) ----------
  const TK={at:[],jokey:[],antrenor:[]};
  function tkLoad(){ try{ const a=JSON.parse(localStorage.getItem("bx-at-fav")||"[]"); TK.at=Array.isArray(a)?a.filter(x=>typeof x==="string"):[]; }catch(e){ TK.at=[]; }
    try{ const o=JSON.parse(localStorage.getItem("bx-at-takip")||"{}")||{}; TK.jokey=Array.isArray(o.jokey)?o.jokey:[]; TK.antrenor=Array.isArray(o.antrenor)?o.antrenor:[]; }catch(e){ TK.jokey=[]; TK.antrenor=[]; } }
  function tkSave(){ lsS("bx-at-fav",JSON.stringify(TK.at.slice(-200))); lsS("bx-at-takip",JSON.stringify({v:1,jokey:TK.jokey.slice(-100),antrenor:TK.antrenor.slice(-100)})); }
  tkLoad();
  const isTk=(k,v)=>!!v&&TK[k].includes(v);
  function tkTog(k,v){ if(!v) return; const i=TK[k].indexOf(v); if(i>=0) TK[k].splice(i,1); else TK[k].push(v); tkSave(); try{ buzz(8); }catch(e){}
    toast(i>=0?"Takipten çıkarıldı":"⭐ "+v+" takip listende"); paint(); }
  const tkN=()=>TK.at.length+TK.jokey.length+TK.antrenor.length;
  // ---------- veri görünümleri ----------
  const D=()=>AT.d&&AT.data[AT.d]||null;
  const races=()=>((D()||{}).kosular||[]).slice().sort((a,b)=>(a.saat||"").localeCompare(b.saat||"")||a.hipodrom.localeCompare(b.hipodrom,"tr")||a.kosu-b.kosu);
  const hips=()=>[...new Set(races().map(r=>r.hipodrom))];
  function raceById(id){ const Dd=AT.data[dayOf(id)]; return Dd&&(Dd.kosular||[]).find(r=>r.kosu_id===id)||null; }
  function M(r){ const m=X.merged(r), by={}; for(const h of (m.c&&m.c.atlar)||[]) by[String(h.no)]=h;
    m.A.forEach(h=>{ const x=by[String(h.no)]||{}; h.no=String(h.no); h.pq=x.p_piyasa!=null?x.p_piyasa:null; h.p=h.p_goster; h.ps=h.p_kazanma; h.p3=h.p_ilk3_oran!=null?h.p_ilk3_oran:h.p_ilk3; });
    m.son=m.c&&m.c.sonuc||null; return m; }
  function st(r){ const c=X.cRace(r); if(c&&c.sonuc) return "bitti"; const t=tsOf(dayOf(r.kosu_id),r.saat);
    if(isFinite(t)&&NOW()>=t) return "kosuldu"; if(c&&(c.durum==="oran_var"||(c.atlar||[]).some(h=>h.p_oran!=null))) return "oran"; return "bekliyor"; }
  const open=r=>{ const s=st(r); return s==="bekliyor"||s==="oran"; };
  function stPill(r,m){ const s=st(r);
    if(s==="bitti"){ m=m||M(r); const ok=m.son.tuttu!=null?!!m.son.tuttu:(m.A[0]&&String(m.son.kazanan)===m.A[0].no); return `<span class="a2-pill ${ok?"ok":"no"}">${ok?"✓":"✗"} Bitti</span>`; }
    const dt=tsOf(dayOf(r.kosu_id),r.saat)-NOW();
    if(s==="kosuldu") return dt>-4*60e3?`<span class="a2-pill w">Koşuluyor</span>`:`<span class="a2-pill w">Sonuç bekleniyor</span>`;
    if(isFinite(dt)&&dt<=10*60e3) return `<span class="a2-pill or">Başlamak üzere</span>`;
    if(s==="oran") return `<span class="a2-pill or">Oranla güncel</span>`; return `<span class="a2-pill">Sabah tahmini</span>`; }
  const golds=()=>D()?X.goldOfDay(D()):[];
  const dLbl=d=>X.dLbl(d);
  const ALT=()=>AT.alt&&AT.alt[AT.d]||null;
  const FORM=f=>f?`<span class="a2-fm" role="img" aria-label="Son koşu dereceleri: ${E(String(f).slice(-6).split("").join(", "))}">${String(f).slice(-6).split("").map(c=>`<i class="${c==="1"?"f1":c==="2"||c==="3"?"f2":c==="0"?"f0":""}">${E(c)}</i>`).join("")}</span>`:`<span class="a2-mut" style="font-size:12.5px">form yok (ilk koşusu olabilir)</span>`;
  function whyOf(x,r){ const t=[]; if(x.form){ const f=String(x.form).slice(-3); if(/1/.test(f)) t.push("son koşularında birincilik var"); else if(/[23]/.test(f)) t.push("son koşularında tabela yaptı"); }
    const uy=(x.son3||[]).filter(k=>k.pist===r.pist).length; if(uy>=2) t.push(`${r.pist} pistte deneyimli`);
    if(x.pq!=null&&x.ps!=null&&x.pq-x.ps>.05) t.push("piyasa da güçlü görüyor");
    if(x.gerekce&&x.gerekce!=="belirgin artısı yok") t.unshift(x.gerekce);
    return t.length?t.slice(0,2).join(" · ").replace(/^./,c=>c.toLocaleUpperCase("tr")):"Belirgin bir artısı yok; olasılığı rakiplerin zayıflığından geliyor"; }
  const JOK=()=>AT.jok||null;
  const jokOf=ad=>((JOK()||{}).jokeyler||[]).find(z=>z.ad===ad)||null, antOf=ad=>((JOK()||{}).antrenorler||[]).find(z=>z.ad===ad)||null;
  // KUPO: aktif at kuponu (v98 ile aynı seçim: aktif kupon at ise o, yoksa son açılan at kuponu)
  function atCoupon(){ const KX=window.KX; if(!KX||!Array.isArray(KX.L)) return null; const L=KX.L.filter(c=>c&&c.spor==="at"&&c.durum==="acik"); if(!L.length) return null;
    const a=L.find(c=>c.id===KX.aktif); if(a) return a; const id=lsG("bx-kupon-at-son",""); return L.find(c=>c.id===id)||L.slice().sort((x,y)=>(y.upd||y.olusturma)-(x.upd||x.olusturma))[0]; }
  const inCp=kid=>{ const c=atCoupon(); return c&&(c.at||[]).find(x=>(x.kid||[]).includes(kid))||null; };
  const TURAD={ganyan:"Kazanan",plase:"Derece",ikili:"İkili",sirali_ikili:"Sıralı İkili",cifte:"Çifte",uclu:"Sıralı Üçlü",tabela:"Tabela",altili:"6'lı Tahmin"};
  // ---------- simgeler ----------
  const IC={star:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8L3.5 9.7l5.9-.9z"/></svg>`,
    starF:`<svg viewBox="0 0 24 24" fill="#E9C766" stroke="#E9C766" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8L3.5 9.7l5.9-.9z"/></svg>`,
    back:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>`,
    chev:`<svg class="a2-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg>`,
    stat:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M5 20V10M12 20V4M19 20v-7"/></svg>`,
    sync:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12a8 8 0 0 1 14-5.3L20 9M20 4v5h-5M20 12a8 8 0 0 1-14 5.3L4 15M4 20v-5h5"/></svg>`};
  // =====================================================================
  // Yönlendirme
  // =====================================================================
  const TABS=[["bugun","Bugün"],["program","Program"],["turler","Türler"],["sonuc","Sonuç"],["kupon","KUPO"]];
  const isTab=v=>TABS.some(t=>t[0]===v);
  function route(){ const m=/^#at(?:\/(.*))?$/.exec(location.hash||""); if(!m) return {v:"bugun",a:[]};
    const p=(m[1]||"").split("/").filter(Boolean); const v=(p[0]==="bahis"?"turler":p[0])||"bugun"; return {v,a:p.slice(1).map((s,i)=>(v==="kosu"||v==="at")&&i===0?s:dec(s))}; }
  function go(path,push){ const h="#at"+(path?"/"+path:""); if(location.hash===h){ paint(true); return; }
    try{ if(push) history.pushState({at2:(history.state&&history.state.at2||0)+1},"",h); else history.replaceState(history.state,"",h); }catch(e){}
    paint(true); }
  function goBack(fb){ if(history.state&&history.state.at2) history.back(); else go(fb,false); }
  function onPop(){ if(!/^#at(\/|$)/.test(location.hash||"")) return; const v=$("v-at"); if(v&&v.hidden){ try{ showSport("at"); }catch(e){} return; } paint(true); }
  window.addEventListener("popstate",onPop); window.addEventListener("hashchange",onPop);
  // =====================================================================
  // Üst gezinme (yapışkan) ve boyama
  // =====================================================================
  const nav=document.createElement("div"); nav.id="at2Nav"; head.appendChild(nav);
  const box=document.createElement("div"); box.id="at2Box"; box.tabIndex=-1; box.setAttribute("aria-live","polite"); wrap.insertBefore(box,old);
  sec.classList.add("at2");
  function navHtml(rt){ const c=atCoupon(), n=c?(c.at||[]).length:0;
    if(isTab(rt.v)) return `<nav class="a2-seg" aria-label="At yarışı bölümleri">${TABS.map(([k,l])=>`<a href="#at/${k}" data-tab="${k}"${rt.v===k?' aria-current="page"':""}>${l}${k==="kupon"&&n?`<span class="a2-n" aria-label="${n} satır">${n}</span>`:""}</a>`).join("")}</nav>`;
    const fb={kosu:"program",at:"program",jokey:"istatistik",antrenor:"istatistik",takip:"bugun",istatistik:"bugun"}[rt.v]||"bugun";
    const lbl=(history.state&&history.state.at2)?({kosu:"Program",at:"Koşu",jokey:"Geri",antrenor:"Geri",takip:"Geri",istatistik:"Geri"}[rt.v]||"Geri"):({kosu:"Program",at:"Program",jokey:"İstatistik",antrenor:"İstatistik"}[rt.v]||"At Yarışı");
    let t="", right="";
    if(rt.v==="kosu"){ const r=raceById(unK(rt.a[0]||"")); t=r?`${r.hipodrom} · ${r.kosu}. Koşu`:"Koşu"; right=`<a class="a2-ib" href="#at/takip" aria-label="Takip listem">${tkN()?IC.starF:IC.star}</a>`; }
    else if(rt.v==="at"){ const r=raceById(unK(rt.a[0]||"")); const h=r&&(r.atlar||[]).find(x=>String(x.no)===String(rt.a[1])); t=h?h.ad:"At"; const on=h&&isTk("at",h.ad);
      right=h?`<button class="a2-ib" type="button" data-tk="at|${E(h.ad)}" aria-pressed="${on}" aria-label="${on?"Takipten çıkar":"Takip et"}">${on?IC.starF:IC.star}</button>`:""; }
    else if(rt.v==="jokey"||rt.v==="antrenor"){ t=rt.a[0]||""; const on=isTk(rt.v,t); right=`<button class="a2-ib" type="button" data-tk="${rt.v}|${E(t)}" aria-pressed="${on}" aria-label="${on?"Takipten çıkar":"Takip et"}">${on?IC.starF:IC.star}</button>`; }
    else if(rt.v==="takip") t="Takip listem"; else if(rt.v==="istatistik") t="İstatistik";
    return `<div class="a2-bar"><button class="a2-back" type="button" data-back="${fb}" aria-label="Geri: ${E(lbl)}">${IC.back}<span>${E(lbl)}</span></button><span class="a2-bt" role="heading" aria-level="2">${E(t)}</span>${right||'<span style="width:44px;flex:none"></span>'}</div>`; }
  let cdT=null, io=null;
  function paint(nav0){ const v=$("v-at"); if(!v||v.hidden) return; const rt=route();
    // derin bağlantıda koşunun günü seçili gün değilse ona geç (merged/cRace seçili güne bakar)
    if((rt.v==="kosu"||rt.v==="at")&&rt.a[0]){ const d=dayOf(unK(rt.a[0])); if(d&&d!==AT.d&&AT.data[d]){ AT.d=d; try{ X.render(); }catch(e){} } }
    nav.innerHTML=navHtml(rt);
    let h=""; try{ h=body(rt); }catch(e){ console.error(e); h=`<div class="a2-card a2-empty"><div class="e" aria-hidden="true">⚠️</div><b>Bu ekran açılamadı</b><p>${E(e.message)}</p><a class="a2-btn q" href="#at/bugun" data-tab="bugun">Bugün'e dön</a></div>`; }
    const y=window.scrollY; box.innerHTML=h; S.sig=sig();
    if(nav0){ window.scrollTo(0,0); try{ box.focus({preventScroll:true}); }catch(e){} } else if(Math.abs(window.scrollY-y)>2) window.scrollTo(0,y);
    try{ if(io) io.disconnect(); const bt=nav.querySelector(".a2-bt"), big=box.querySelector("h1.a2-h2"); if(bt&&big&&"IntersectionObserver" in window){ bt.classList.add("hid"); io=new IntersectionObserver(es=>{ for(const x of es) bt.classList.toggle("hid",x.isIntersecting||x.boundingClientRect.top>0); },{rootMargin:"-"+Math.round(nav.getBoundingClientRect().bottom||0)+"px 0px 0px 0px"}); io.observe(big); } }catch(e){}
    try{ const cc=box.querySelector('.a2-chips .a2-chip[aria-current="true"]'); if(cc){ const sc=cc.parentElement; sc.scrollLeft=Math.max(0,cc.offsetLeft-sc.clientWidth/2+cc.offsetWidth/2); } }catch(e){}
    S.last=rt.v; clearInterval(cdT); const cd=$("at2cd"); if(cd) cdT=setInterval(tick,15000); }
  function tick(){ const cd=$("at2cd"); if(!cd){ clearInterval(cdT); return; } const mn=Math.round((+cd.dataset.t-NOW())/6e4); if(mn<=0){ paint(); return; } cd.innerHTML=cdHtml(mn); }
  const cdHtml=mn=>mn>=60?Math.floor(mn/60)+"<small>sa</small> "+(mn%60)+"<small>dk</small>":mn+"<small>dk</small>";
  const sig=()=>{ const C=AT.canli&&AT.canli[AT.d], A=ALT(), c=atCoupon(); return [AT.d,AT.days.join(","),AT.busy?1:0,C&&C.guncelleme_tsi,A&&A.guncelleme_tsi,!!AT.jok,!!AT.model,!!AT.karne,c&&c.id,c&&c.upd,c&&(c.at||[]).length,tkN()].join("|"); };
  let schT=null; function schedule(){ clearTimeout(schT); schT=setTimeout(()=>{ if(sig()!==S.sig) paint(); },60); }
  new MutationObserver(schedule).observe(old,{childList:true});
  try{ const _s=window.kxSave; if(typeof _s==="function") window.kxSave=function(){ const r=_s.apply(this,arguments); schedule(); return r; }; }catch(e){}
  window.addEventListener("storage",e=>{ if(!e.key||/^bx-(kuponlar|at-fav|at-takip)/.test(e.key)){ tkLoad(); paint(); } });
  // eski at penceresi (horseSheet) → At profili ekranı (uyum işlevi)
  X.horseSheet=(rid,no)=>{ try{ if($("v-at").hidden) showSport("at"); }catch(e){} go("at/"+K(rid)+"/"+enc(no),true); };
  // =====================================================================
  // Ekranlar
  // =====================================================================
  function body(rt){
    if(!AT.d){ if(AT.busy||!AT.model&&!AT.days.length&&!S.loadedOnce) return skel();
      if(AT.kyn&&AT.kyn.bugun===istDay(new Date())&&AT.kyn.durum!=="program_yok") return kynCard()+istHtml(true);
      return `<div class="a2-card a2-empty"><div class="e" aria-hidden="true">🗓️</div><b>Yakın günlerde koşu programı yok</b><p>Laboratuvar her sabah 05:23 ve öğlen 12:23'te yeni programı işler. Hipodromlar genelde pazartesi dinlenir.</p><button class="a2-btn q" type="button" data-re>Yeniden dene</button></div>${istHtml(true)}`; }
    const V={bugun:vBugun,program:vProgram,turler:vTurler,sonuc:vSonuc,kupon:vKupon,kosu:vKosu,at:vAt,jokey:a=>person("jokey",a[0]),antrenor:a=>person("antrenor",a[0]),takip:vTakip,istatistik:()=>istHtml(false)}[rt.v]||vBugun;
    return V(rt.a); }
  const skel=()=>`<div class="a2-sk" style="height:56px"></div><div class="a2-sk" style="height:150px"></div><div class="a2-sk" style="height:120px"></div><div class="a2-sk" style="height:64px"></div><p class="a2-sr">Yükleniyor</p>`;
  const notFound=t=>`<div class="a2-card a2-empty"><div class="e" aria-hidden="true">🔎</div><b>${E(t)}</b><p>Bu kayıt seçili günün verisinde yok (eski bir bağlantı olabilir).</p><a class="a2-btn q" href="#at/program" data-tab="program">Programa dön</a></div>`;
  const foot=()=>{ const Dd=D(); return `<p class="a2-foot">${Dd&&Dd.kilit_zamani_tsi?`Kilit: ${E(Dd.kilit_zamani_tsi)} · model ${E(Dd.model_surumu||"")}. `:""}Veri: herkese açık yarış sonuç arşivi (GitHub aynası); OXXai resmî yarış sitesine istek atmaz. Hobi amaçlı olasılıktır, garanti değildir. Para tutarı gösterilmez · 18+</p>`; };
  const dayChips=()=>AT.days.length>1?`<div class="a2-chips" role="group" aria-label="Gün seç">${AT.days.map(x=>`<button class="a2-chip" type="button" data-day="${x}" aria-pressed="${x===AT.d}">${E(dLbl(x))}</button>`).join("")}</div>`:"";
  function titleRow(){ const R=races(); return `<div class="a2-hd"><h1><img class="at-emb a2-emb" src="icons/oxxai-at.webp" alt="" aria-hidden="true" decoding="async" onerror="this.onerror=null;this.src='icons/oxxai-at.png'">At Yarışı<span class="a2-dn">DENEME</span><small>${E(dLbl(AT.d))} · ${hips().length} hipodrom · ${R.length} koşu</small></h1>
    <a class="a2-ib" href="#at/istatistik" aria-label="İstatistik: model karnesi ve jokey sıralaması">${IC.stat}</a><a class="a2-ib" href="#at/takip" aria-label="Takip listem${tkN()?" ("+tkN()+")":""}">${tkN()?IC.starF:IC.star}</a></div>`; }
  // ---------- kaynak durumu (data/at/kaynak_durum.json · lab/at/kaynak_durum.py): bugünün programı yoksa dürüstçe söyle ----------
  function kynCard(){ const t=istDay(new Date()); if(AT.days.includes(t)) return ""; const k=AT.kyn&&AT.kyn.bugun===t?AT.kyn:null;
    const son=k&&k.ayna_son_guncelleme?Date.parse(k.ayna_son_guncelleme):NaN, sa=isFinite(son)?Math.max(0,Math.round((NOW()-son)/36e5)):null;
    const ne=isFinite(son)?` Açık yarış arşivi en son <b>${E(new Date(son).toLocaleString("tr-TR",{timeZone:"Europe/Istanbul",day:"numeric",month:"long",hour:"2-digit",minute:"2-digit"}))}</b> güncellendi${sa>=1?` (${sa} saat önce)`:""}.`:"";
    const dn=k&&k.dun_kosu&&k.dun_sonuclu<k.dun_kosu?` Dünün ${k.dun_kosu} koşusundan ${k.dun_sonuclu} tanesinin sonucu arşive geldi; kalanlar gelince kendiliğinden eklenir.`:"";
    const alt=AT.d&&AT.d!==t?` Aşağıda <b>${E(dLbl(AT.d))}</b> günü gösteriliyor.`:"";
    if(k&&k.durum==="program_yok") return `<div class="a2-card a2-empty" role="status"><div class="e" aria-hidden="true">🗓️</div><b>Bugün yerli koşu programı yok</b><p>Açık yarış arşivi bugün güncellendi; bugün için yerli hipodrom koşusu görünmüyor.${dn}${alt}</p></div>`;
    if(k&&k.bugun_kosu>0) return `<div class="a2-card a2-empty" role="status"><div class="e" aria-hidden="true">⏳</div><b>Bugünün programı geldi, tahminler hazırlanıyor</b><p>Açık yarış arşivi bugünün ${k.bugun_kosu} koşusunu yayınladı; kilitli tahminler birkaç dakika içinde burada olur.${alt}</p></div>`;
    return `<div class="a2-card a2-empty" role="status"><div class="e" aria-hidden="true">📭</div><b>Bugünün programı henüz yayınlanmadı</b><p>OXXai bugünün koşularını açık yarış arşivi programı yayınlayınca hazırlar; tahmin uydurulmaz.${ne}${dn}${alt}</p><button class="a2-btn q" type="button" data-re>Yeniden dene</button></div>`; }
  // ---------- 1) BUGÜN ----------
  function vBugun(){ const d=AT.d, R=races(); let h=titleRow()+kynCard()+dayChips();
    const nx=R.find(open);
    if(nx){ const m=M(nx), t=tsOf(d,nx.saat), mn=Math.max(0,Math.round((t-NOW())/6e4)), far=mn>12*60;
      h+=`<a class="a2-card" href="#at/kosu/${K(nx.kosu_id)}" aria-label="Sıradaki koşu: ${E(nx.hipodrom)} ${nx.kosu}. koşu, saat ${E(nx.saat)}${far?"":", "+mn+" dakika sonra"}">
        <div class="a2-ch"><h2>Sıradaki koşu</h2>${stPill(nx,m)}</div>
        <div class="a2-nx-t">${far?`<div class="a2-nx-c" style="font-size:26px">${E(dLbl(d))}<small>${E(nx.saat)}</small></div>`:`<div class="a2-nx-c" id="at2cd" data-t="${t}" aria-hidden="true">${cdHtml(mn)}</div>`}
          <div class="a2-nx-m"><b>${E(nx.hipodrom)} · ${nx.kosu}. Koşu · ${E(nx.saat)}</b><span>${E(nx.mesafe)} m ${E(nx.pist)} · ${E(nx.sinif)} · ${m.A.length} at</span></div>${IC.chev}</div>
        <div class="a2-mini">${m.A.slice(0,3).map((x,i)=>`<div><span class="a2-no${i===0?" top":""}">${E(x.no)}</span><span class="a2-hn"><b>${isTk("at",x.ad)?'<span class="a2-star" aria-label="takipte">★</span> ':""}${E(x.ad)}</b></span><span class="a2-hp"><b style="font-size:15px">${P(x.p)}</b></span></div>`).join("")}</div></a>`; }
    else{ const eks=R.filter(r=>st(r)!=="bitti").length; h+=`<div class="a2-card a2-empty"><div class="e" aria-hidden="true">🏁</div><b>${E(dLbl(d))} ${eks?"koşular koşuldu":"koşular tamamlandı"}</b><p>${eks?`${eks} koşunun sonucu arşive henüz gelmedi; gelince kendiliğinden eklenir. `:""}Sonuçlar ve modelin karnesi "Sonuç" sekmesinde.</p><a class="a2-btn q" href="#at/sonuc" data-tab="sonuc">Sonuçlara git</a></div>`; }
    // takip ettiklerin koşuyor
    const FT=[], seen=new Set();
    for(const r of R){ const m=M(r); for(const x of m.A){ const why=isTk("at",x.ad)?"":isTk("jokey",x.jokey)?"jokey "+x.jokey:isTk("antrenor",x.antrenor)?"antrenör "+x.antrenor:null; if(why==null) continue;
      const k=r.kosu_id+"|"+x.no; if(seen.has(k)) continue; seen.add(k); FT.push({r,x,why,m}); } }
    if(FT.length) h+=`<div class="a2-card"><div class="a2-ch"><h2>⭐ Takip ettiklerin koşuyor</h2><a class="a2-more" href="#at/takip">Tümü</a></div>${FT.slice(0,5).map(o=>`<a class="a2-hrow" href="#at/at/${K(o.r.kosu_id)}/${enc(o.x.no)}"><span class="a2-no">${E(o.x.no)}</span><span class="a2-hn"><b>${E(o.x.ad)}</b><small>${E(o.r.hipodrom)} ${o.r.kosu}. koşu · ${E(o.r.saat)}${o.why?" · "+E(o.why):""} · ${P(o.x.p)}</small></span>${stPill(o.r,o.m)}</a>`).join("")}</div>`;
    // altın atlar
    const G=golds();
    h+=`<h2 class="a2-sec">🥇 Günün altın atları</h2>`;
    h+=G.length?`<div class="a2-gl" role="list">${G.map(g=>{ const s=st(g.r), m=s==="bitti"?M(g.r):null;
        const res=s==="bitti"?(String(m.son.kazanan)===String(g.h.no)?`<span class="a2-pill ok">✓ Kazandı</span>`:`<span class="a2-pill no">✗ Kazanamadı</span>`):s==="kosuldu"?`<span class="a2-pill w">Sonuç bekleniyor</span>`:`<span class="a2-pill">${E(g.r.saat)}</span>`;
        return `<a class="a2-gc${G.length===1?" one":""}" role="listitem" href="#at/at/${K(g.r.kosu_id)}/${enc(g.h.no)}"><div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><span class="p">${P(g.h.p_kazanma)}</span>${res}</div><b>${E(g.h.no)} · ${E(g.h.ad)}</b><small>${E(g.r.hipodrom)} ${g.r.kosu}. koşu · ${E(g.r.mesafe)} m ${E(g.r.pist)} · ilk 3: ${P(g.h.p_ilk3)}</small></a>`; }).join("")}</div>
        <p class="a2-note">Kural: koşusunun en olası atı, %35+ ve en yakın rakibine 12+ puan fark. Model emin değilse altın vermez.</p>`
      :`<div class="a2-card"><p class="a2-note" style="margin:0">${E(dLbl(d))} altın kuralına uyan at yok: model hiçbir koşuda yeterince emin değil.</p></div>`;
    // padok notu (kısaltılmış; altın satırı yukarıda kart olarak var)
    let pd=null; try{ pd=window.BX_padok&&window.BX_padok(); }catch(e){}
    if(pd&&pd.L&&pd.L.length){ const L=pd.L.filter(([i])=>i!=="🥇"), row=([i,t])=>`<p><i aria-hidden="true">${i}</i><span>${t}</span></p>`;
      h+=`<h2 class="a2-sec">📋 Padok Notu</h2><div class="a2-card a2-pd">${L.slice(0,3).map(row).join("")}
        ${L.length>3?`<details id="at2pd"${S.pdOpen?" open":""}><summary>${S.pdOpen?"Daha az göster":`Devamını oku (${L.length-3})`}</summary>${L.slice(3).map(row).join("")}</details>`:""}
        <p class="a2-up">${pd.up?"Güncellendi "+E(pd.up):"Sabah tahmini"} · oran, sonuç ve 6'lı ayakları geldikçe yeniden yazılır.</p></div>`; }
    // hipodromlar
    const A=ALT();
    h+=`<h2 class="a2-sec">Hipodromlar</h2><div class="a2-rl">${hips().map(x=>{ const RR=R.filter(r=>r.hipodrom===x).sort((a,b)=>a.kosu-b.kosu), b=RR.filter(r=>st(r)==="bitti").length, six=A&&(A.altililar||[]).some(a=>a.hipodrom===x);
        return `<a class="a2-rr" href="#at/program" data-tab="program" data-hip="${E(x)}"><span class="k"><b>${RR.length}</b><small>koşu</small></span><span class="m"><b>${E(x)}</b><small>${E(RR[0].saat)}–${E(RR[RR.length-1].saat)} · ${b?b+" bitti · ":""}${RR.length-b} kaldı${six?" · 6'lı var":""}</small></span>${IC.chev}</a>`; }).join("")}</div>`;
    return h+foot(); }
  // ---------- 2) PROGRAM ----------
  function vProgram(){ const H=hips(); if(!S.hipU||!H.includes(S.hip)){ const nx=races().find(open); S.hip=nx?nx.hipodrom:H.includes(S.hip)?S.hip:H[0]; } AT.hip=S.hip;
    const R=races().filter(r=>r.hipodrom===S.hip).sort((a,b)=>a.kosu-b.kosu), G=new Set(golds().map(g=>g.r.kosu_id)), A=ALT(), al=((A&&A.altililar)||[]).filter(a=>a.hipodrom===S.hip);
    let h=titleRow()+kynCard()+dayChips();
    if(S.pickTur) h+=`<div class="a2-pick" role="status"><span><b style="color:var(--a2-ink)">${E(TURAD[S.pickTur]||"")}</b> KUPO'su için başlamamış bir koşu seç.</span><button type="button" data-pickx>Vazgeç</button></div>`;
    h+=`<div class="a2-chips" role="group" aria-label="Hipodrom seç">${H.map(x=>`<button class="a2-chip" type="button" data-hp="${E(x)}" aria-pressed="${x===S.hip}">${E(x)} <small>${races().filter(r=>r.hipodrom===x).length}</small></button>`).join("")}</div>`;
    h+=`<div class="a2-rl">${R.map(r=>{ const m=M(r), f=m.A[0]||{}, s=st(r), a6=al.find(a=>(a.kosular||[]).includes(r.kosu)), ay=a6?a6.kosular.indexOf(r.kosu)+1:0, fv=m.A.some(x=>isTk("at",x.ad));
        const top=s==="bitti"?`🏁 ${E(m.son.kazanan)} ${E(m.son.kazanan_ad||"")}`:`${E(f.no)} ${E(f.ad)} ${P(f.p)}`;
        return `<a class="a2-rr${s==="bitti"?" done":""}" href="#at/kosu/${K(r.kosu_id)}" data-kid="${E(r.kosu_id)}" aria-label="${r.kosu}. koşu, saat ${E(r.saat)}"><span class="k"><b>${r.kosu}</b><small>${E(r.saat)}</small></span>
          <span class="m"><b>${G.has(r.kosu_id)?'<span class="a2-dot" role="img" aria-label="altın at"></span>':""}${fv?'<span class="a2-star" role="img" aria-label="takipteki at">★</span> ':""}${top}</b>
          <small>${E(r.mesafe)} m ${E(r.pist)} · ${m.A.length} at${ay?` · 6'lı ${ay}. ayak`:""} · ${E(r.sinif)}</small></span>${stPill(r,m)}</a>`; }).join("")}</div>`;
    h+=`<div class="a2-legend"><span><span class="a2-dot"></span>altın at</span><span><span class="a2-star">★</span> takipteki at</span><span>Bitmeyen koşuda ilk satır: en olası at</span></div>`;
    return h+foot(); }
  // ---------- 3) KOŞU KARTI ----------
  function vKosu(a){ const r=raceById(unK(a[0]||"")); if(!r) return notFound("Koşu bulunamadı");
    const m=M(r), s=st(r), sib=((AT.data[dayOf(r.kosu_id)]||{}).kosular||[]).filter(x=>x.hipodrom===r.hipodrom).sort((x,y)=>x.kosu-y.kosu);
    let h=`<div class="a2-chips" role="group" aria-label="${E(r.hipodrom)} koşuları">${sib.map(x=>`<a class="a2-chip sq${st(x)==="bitti"?" done":""}" href="#at/kosu/${K(x.kosu_id)}" data-sib="1"${x.kosu_id===r.kosu_id?' aria-current="true"':""} aria-label="${x.kosu}. koşu, saat ${E(x.saat)}${st(x)==="bitti"?", bitti":""}">${x.kosu}</a>`).join("")}</div>`;
    h+=`<h1 class="a2-h2">${E(r.hipodrom)} · ${r.kosu}. Koşu</h1>
      <div class="a2-rh"><span class="a2-pill">${E(dLbl(dayOf(r.kosu_id)))} ${E(r.saat)}</span><span class="a2-pill">${E(r.mesafe)} m</span><span class="a2-pill">${E(r.pist)}</span><span class="a2-pill">${E(r.sinif)}</span><span class="a2-pill">${m.A.length} at</span>${stPill(r,m)}</div>`;
    if(r.kosudan_once===false) h+=`<span class="a2-tag">Koşudan sonra kilitlendi · karneye sayılmaz</span>`;
    if(m.son){ const nm=no=>(m.A.find(y=>y.no===String(no))||{}).ad||"";
      h+=`<div class="a2-card gold"><div class="a2-ch"><h2>🏁 Sonuç</h2><small>piyasa oranı ${fx(m.son.ganyan)}</small></div><div class="a2-res">${(m.son.sira||[]).map((no,i)=>`<div><span class="pl">${i+1}.</span><span class="a2-no${i===0?" w":""}">${E(no)}</span><span class="a2-hn"><b>${E(nm(no))}</b></span><span class="a2-hp"><small>model ${P((m.A.find(y=>y.no===String(no))||{}).ps)}</small></span></div>`).join("")}</div>
        <p class="a2-note" style="margin-top:10px">Modelin ilk seçimi ${E(m.son.model_ilk)} ${E(nm(m.son.model_ilk))}: ${m.son.tuttu?'<b class="up">kazandı ✓</b>':'<b class="dn">kazanamadı ✗</b>'}${m.son.kosan?` · ${m.son.kosan} at koştu`:""}${m.son.esit?" · eşit derece var":""}.</p></div>`; }
    h+=`<div class="a2-seg" role="group" aria-label="Görünüm" style="margin:0 0 12px"><button type="button" data-mode="sade" aria-pressed="${S.mode==="sade"}">Sade</button><button type="button" data-mode="merakli" aria-pressed="${S.mode==="merakli"}">Meraklı</button></div>`;
    const win=m.son?String(m.son.kazanan):null, href=x=>`#at/at/${K(r.kosu_id)}/${enc(x.no)}`, star=x=>isTk("at",x.ad)?'<span class="a2-star" aria-label="takipte">★</span> ':"";
    if(S.mode==="sade"){
      h+=`<div class="a2-card a2-sade"><div class="a2-ch"><h2>Kim kazanır?</h2><small>${m.oranli?"oranla güncel":"sabah tahmini"}</small></div>
        ${m.A.slice(0,3).map((x,i)=>`<a class="hc${i===0?" first":""}${win===x.no?" a2-win":""}" href="${href(x)}"><span class="a2-no${win===x.no?" w":i===0?" top":""}">${E(x.no)}</span><span class="a2-hn"><b>${star(x)}${E(x.ad)}${win===x.no?" 🏁":""}</b><small>${E([x.jokey,x.kilo?fx(x.kilo,1)+" kg":null].filter(Boolean).join(" · "))}</small><div class="a2-why">${E(whyOf(x,r))}</div><div class="a2-barr"><i style="width:${Math.max(3,Math.round(x.p/(m.A[0].p||1)*100))}%"></i></div></span><span class="a2-hp"><b>${P(x.p)}</b><small>ilk 3: ${P(x.p3)}</small></span></a>`).join("")}
        ${m.A.slice(3).map(x=>`<a class="a2-hrow${win===x.no?" a2-win":""}" href="${href(x)}"><span class="a2-no${win===x.no?" w":""}">${E(x.no)}</span><span class="a2-hn"><b>${star(x)}${E(x.ad)}${win===x.no?" 🏁":""}</b><small>${E(x.jokey||"")}</small></span><span class="a2-hp"><b class="m">${P(x.p)}</b></span></a>`).join("")}
        ${r.ikili_onerisi&&r.ikili_onerisi.sira?`<p class="a2-note" style="margin-top:10px">Sabahın ikili önerisi: <b style="color:var(--a2-gi)">${r.ikili_onerisi.sira.map(E).join(" – ")}</b> · tam bu sırayla gelme olasılığı ${P(r.ikili_onerisi.p,1)}</p>`:""}</div>`;
    } else {
      const so={p:(a,b)=>b.p-a.p,no:(a,b)=>(+a.no)-(+b.no),oran:(a,b)=>(a.oran||999)-(b.oran||999),kilo:(a,b)=>(b.kilo||0)-(a.kilo||0)}[S.sort]||((a,b)=>b.p-a.p);
      const A=m.A.slice().sort(so);
      h+=`<div class="a2-card"><div class="a2-sortb" role="group" aria-label="Sırala"><span>Sırala:</span>${[["p","Olasılık"],["no","No"],["oran","Oran"],["kilo","Kilo"]].map(([k,l])=>`<button type="button" data-sort="${k}" aria-pressed="${S.sort===k}">${l}</button>`).join("")}</div>
        ${A.map(x=>{ const df=x.pq!=null&&x.ps!=null?x.pq-x.ps:null, s3=x.son3||[], uy=s3.filter(k=>k.pist===r.pist).length, um=s3.filter(k=>Math.abs((+k.mesafe||0)-(+r.mesafe||0))<=200).length;
          return `<div class="a2-mk"><a class="a2-mk-a" href="${href(x)}"><span class="a2-no${win===x.no?" w":x===m.A[0]?" top":""}">${E(x.no)}</span><span class="a2-hn"><b>${star(x)}${E(x.ad)}${win===x.no?" 🏁":""}</b><small>${E([x.yas?x.yas+" yaş":null,x.kilo?fx(x.kilo,1)+" kg":null,x.jokey].filter(Boolean).join(" · "))}</small></span><span class="a2-hp"><b>${P(x.p)}</b><small>${x.oran?"oran "+fx(x.oran):"oran yok"}</small></span></a>
            <div class="a2-mk-b">${FORM(x.form)}${x.antrenor?`<span>· ${E(x.antrenor)}</span>`:""}</div>
            <div class="a2-mk-c"><div><b>${P(x.ps)}</b><small>model sabah</small></div><div><b>${P(x.pq)}</b><small>piyasa</small></div><div><b class="${df==null?"":df>0.02?"up":df<-0.02?"dn":""}">${df==null?"–":(df>0.005?"▲ ":df<-0.005?"▼ ":"")+Math.abs(Math.round(df*100))}</b><small>piyasa farkı</small></div><div><b>${s3.length?uy+"/"+s3.length:"–"}</b><small>${E(r.pist)} uyumu</small></div></div></div>`; }).join("")}
        <div class="a2-legend"><span>Form: son 6 koşu derecesi (sağdaki en yeni; 0 = ilk 9 dışı)</span><span>Piyasa: piyasa oranından marjı ayrılmış olasılık (AGF değildir)</span><span>▲ piyasa modelden fazla inanıyor (puan)</span><span>Pist uyumu: son 3 koşudan kaçı aynı pistte (mesafe uyumu at profilinde)</span></div></div>
        <div class="a2-miss"><b>Henüz veri yok:</b> start/kulvar, handikap puanı, sahip, pedigri, idman/galop, AGF ve gün içi oran hareketi. Açık arşivde bulunmadıkları için uydurulmaz.</div>`;
    }
    const x0=inCp(r.kosu_id);
    h+=s==="bitti"||s==="kosuldu"?`<p class="a2-note" style="margin-top:12px">Koşu başladı; KUPO'ya eklenemez.</p><button class="a2-btn q" type="button" data-share="${E(r.kosu_id)}" style="margin-top:8px">📤 Paylaş</button>`
      :`<div class="a2-row2" style="margin-top:12px"><button class="a2-btn g${x0?" on":""}" type="button" data-atkr="${E(r.kosu_id)}" aria-label="Bu koşudan at KUPO'su kur">${x0?`✓ KUPO'da · ${E(TURAD[x0.tur]||"")}`:"＋ KUPO"}</button><button class="a2-btn q" type="button" data-share="${E(r.kosu_id)}">📤 Paylaş</button></div>`;
    return h+foot(); }
  // ---------- 4) AT PROFİLİ ----------
  function vAt(a){ const r=raceById(unK(a[0]||"")); if(!r) return notFound("At bulunamadı"); const m=M(r), x=m.A.find(y=>y.no===String(a[1])); if(!x) return notFound("At bulunamadı");
    const rank=m.A.indexOf(x)+1, fv=isTk("at",x.ad), jk=jokOf(x.jokey), an=antOf(x.antrenor), s=st(r), win=m.son&&String(m.son.kazanan)===x.no, der=m.son?(m.son.sira||[]).map(String).indexOf(x.no)+1:0;
    let h=`<div style="display:flex;align-items:center;gap:12px;margin:2px 0 6px"><span class="a2-no${win?" w":rank===1?" top":""}" style="width:48px;height:48px;font-size:20px;border-radius:14px">${E(x.no)}</span>
      <div style="flex:1;min-width:0"><h1 class="a2-h2" style="margin:0">${E(x.ad)}</h1><a class="a2-mut" style="font-size:13px;display:inline-flex;min-height:44px;align-items:center" href="#at/kosu/${K(r.kosu_id)}">${E(r.hipodrom)} ${r.kosu}. koşu · ${E(r.saat)} · ${E(r.mesafe)} m ${E(r.pist)} ›</a></div></div>
      <div class="a2-rh">${x.yas?`<span class="a2-pill">${E(x.yas)} yaş</span>`:""}${x.kilo?`<span class="a2-pill">${fx(x.kilo,1)} kg</span>`:""}<span class="a2-pill">${rank}. favori</span>${der?`<span class="a2-pill ${der===1?"ok":""}">${der}. geldi</span>`:""}${stPill(r,m)}</div>
      <div class="a2-card"><div class="a2-kpis"><div><b style="color:var(--a2-gi)">${P(x.p)}</b><small>kazanma<br>${m.oranli&&x.p_oran!=null?"oranla":"sabah"}</small></div><div><b>${P(x.p3)}</b><small>ilk 3'e<br>girme</small></div><div><b>${P(x.pq)}</b><small>piyasa<br>olasılığı</small></div><div><b>${x.oran?fx(x.oran):"–"}</b><small>piyasa<br>oranı</small></div></div>
        ${x.p_oran!=null?`<p class="a2-note" style="margin:8px 2px 0">Sabah tahmini ${P(x.ps)} · oranla güncel ${P(x.p_oran)}.</p>`:""}
        <p class="a2-why" style="margin:8px 2px 0">${E(whyOf(x,r))}.</p></div>
      <div class="a2-card"><div class="a2-ch"><h2>Form</h2><small>son 6 koşu</small></div>${FORM(x.form)}
        ${(x.son3||[]).length?`<div style="margin-top:10px">${x.son3.map(k=>`<div class="a2-hrow"><span class="a2-no${k.sira===1?" w":""}">${k.sira!=null?E(k.sira):"–"}</span><span class="a2-hn"><b>${E(k.hipodrom)} · ${E(k.mesafe)} m ${E(k.pist)}</b><small>${E(k.tarih?fD(k.tarih):"")}${k.pist===r.pist?" · aynı pist":""}${Math.abs((+k.mesafe||0)-(+r.mesafe||0))<=200?" · benzer mesafe":""}</small></span></div>`).join("")}</div>`:`<p class="a2-note">Son koşu ayrıntısı henüz veri yok (ilk koşusu olabilir ya da oran dosyası gelmedi).</p>`}</div>
      <div class="a2-card"><div class="a2-ch"><h2>Ekip</h2></div>
        ${x.jokey?`<a class="a2-hrow" href="#at/jokey/${enc(x.jokey)}"><span class="a2-no" aria-hidden="true">🏇</span><span class="a2-hn"><b>${isTk("jokey",x.jokey)?'<span class="a2-star">★</span> ':""}${E(x.jokey)}</b><small>Jokey${jk?` · 90 günde kazanma ${P(jk.kazanma_90g)} · katkı ${jk.katki>0?"+":""}${fx(jk.katki,1)}`:" · 90 günlük sıralamada yok"}</small></span>${IC.chev}</a>`:""}
        ${x.antrenor?`<a class="a2-hrow" href="#at/antrenor/${enc(x.antrenor)}"><span class="a2-no" aria-hidden="true">🧑‍🏫</span><span class="a2-hn"><b>${isTk("antrenor",x.antrenor)?'<span class="a2-star">★</span> ':""}${E(x.antrenor)}</b><small>Antrenör${an?` · 90 günde kazanma ${P(an.kazanma_90g)}`:" · 90 günlük sıralamada yok"}</small></span>${IC.chev}</a>`:""}
        ${!x.jokey&&!x.antrenor?`<p class="a2-note">Ekip bilgisi henüz gelmedi.</p>`:""}</div>
      <div class="a2-row2"><button class="a2-btn ${fv?"q":"g"}" type="button" data-tk="at|${E(x.ad)}" aria-pressed="${fv}">${fv?"★ Takipte":"☆ Takip et"}</button>${s==="bitti"||s==="kosuldu"?`<a class="a2-btn q" href="#at/kosu/${K(r.kosu_id)}">Koşu kartı</a>`:`<button class="a2-btn q" type="button" data-atkh="${E(r.kosu_id)}|${E(x.no)}">＋ Bu atla KUPO</button>`}</div>
      <div class="a2-miss"><b>Henüz veri yok:</b> kariyer tablosu (pist, mesafe, hipodrom, sınıf, jokeyle uyum) laboratuvarda üretilecek; pedigri, sahip ve idman verisi açık kaynakta yok.</div>`;
    return h+foot(); }
  // ---------- 5) JOKEY / ANTRENÖR ----------
  function person(kind,ad){ ad=ad||""; const L=(JOK()||{})[kind==="jokey"?"jokeyler":"antrenorler"]||[], z=L.find(q=>q.ad===ad), rk=z?L.indexOf(z)+1:null, fv=isTk(kind,ad);
    const today=[], seen=new Set(); for(const r of races()){ const m=M(r); for(const x of m.A) if(x[kind]===ad&&!seen.has(r.kosu_id+x.no)){ seen.add(r.kosu_id+x.no); today.push({r,x,m}); } }
    let h=`<h1 class="a2-h2">${E(ad)}</h1><div class="a2-rh"><span class="a2-pill">${kind==="jokey"?"Jokey":"Antrenör"}</span>${rk?`<span class="a2-pill g">${rk}. sırada</span>`:""}${z&&z.form_trend?`<span class="a2-pill">${z.form_trend==="yukseliyor"?"📈 formu yükseliyor":z.form_trend==="dusuyor"?"📉 formu düşüyor":"➖ formu sabit"}</span>`:""}</div>`;
    if(z) h+=`<div class="a2-card"><div class="a2-kpis"><div><b>${E(z.binis_90g||z.kosu_90g||"–")}</b><small>${kind==="jokey"?"biniş":"koşu"}<br>90 gün</small></div><div><b>${P(z.kazanma_90g)}</b><small>kazanma</small></div><div><b>${P(z.ilk3_90g)}</b><small>ilk 3</small></div><div><b class="${z.katki>0?"up":"dn"}">${z.katki>0?"+":""}${fx(z.katki,1)}</b><small>katkı<br>puanı</small></div></div>
      <p class="a2-note" style="margin-top:10px">Katkı, ${kind==="jokey"?"jokeyin":"antrenörün"} aynı atlarla beklenenden ne kadar iyi sonuç aldığını ölçer; atın gücünden arındırılmıştır.${z.uzmanlik?` Uzmanlık: <b style="color:var(--a2-ink2)">${E([z.uzmanlik.pist,z.uzmanlik.mesafe&&z.uzmanlik.mesafe+" mesafe",z.uzmanlik.hipodrom].filter(Boolean).join(", "))}</b>.`:""}</p></div>`;
    else h+=`<div class="a2-card"><p class="a2-note" style="margin:0">${JOK()?"Bu isim son 90 günün sıralamasında yok (az koşu); istatistik için henüz veri yok.":"Jokey istatistikleri yükleniyor."}</p></div>`;
    if(kind==="jokey"&&z&&(z.bugun_binis||[]).length&&!today.length) for(const b of z.bugun_binis){ const r=raceById(b.kosu_id); if(r){ const m=M(r), x=m.A.find(q=>q.ad===b.at); if(x) today.push({r,x,m}); } }
    h+=`<div class="a2-card"><div class="a2-ch"><h2>${E(dLbl(AT.d))} ${kind==="jokey"?"binişleri":"atları"}</h2><small>${today.length}</small></div>${today.length?today.map(o=>`<a class="a2-hrow" href="#at/at/${K(o.r.kosu_id)}/${enc(o.x.no)}"><span class="a2-no">${E(o.x.no)}</span><span class="a2-hn"><b>${E(o.x.ad)}</b><small>${E(o.r.hipodrom)} ${o.r.kosu}. koşu · ${E(o.r.saat)}</small></span><span class="a2-hp"><b style="font-size:15px">${P(o.x.p)}</b>${st(o.r)==="bitti"?`<small>${String(o.m.son.kazanan)===o.x.no?"✓ kazandı":"bitti"}</small>`:""}</span></a>`).join(""):`<p class="a2-note" style="margin:0">Bu gün programda kaydı yok.</p>`}</div>
      <button class="a2-btn ${fv?"q":"g"}" type="button" data-tk="${kind}|${E(ad)}" aria-pressed="${fv}">${fv?"★ Takipte":"☆ Takip et"}</button>`;
    return h+foot(); }
  // ---------- 6) SONUÇ ----------
  function vSonuc(){ const d=AT.d, R=races(), B=R.filter(r=>st(r)==="bitti"), ok=B.filter(r=>{ const m=M(r); return m.son.tuttu!=null?m.son.tuttu:(m.A[0]&&String(m.son.kazanan)===m.A[0].no); }).length;
    const kg=AT.karne&&AT.karne.gunler, kd=kg&&(Array.isArray(kg)?kg.find(x=>x.tarih===d):kg[d]), me=((AT.model||{}).degerlendirme||{}).metrik||{};
    let h=titleRow()+dayChips()+`<div class="a2-card"><div class="a2-kpis k3"><div><b>${B.length}/${R.length}</b><small>koşu bitti</small></div><div><b style="color:var(--a2-gi)">${ok}</b><small>ilk seçim<br>kazandı</small></div><div><b>${B.length?P(ok/B.length):"–"}</b><small>günlük<br>isabet</small></div></div>
      <p class="a2-note" style="margin-top:10px">${kd&&kd.kosu?`Kilitli karne: ${kd.kosu} koşu · ilk seçim ${P(kd.ilk_secim_isabet)}. `:""}Uzun dönem ilk seçim isabeti: sabah modeli ${P(me.model&&me.model.ilk_secim_isabet)}, oranla harman ${P(me.harman&&me.harman.ilk_secim_isabet)}, piyasa favorisi ${P(me.favori&&me.favori.ilk_secim_isabet)}.</p></div>`;
    // karnede olup canlı dosyada olmayan koşular (eski günler)
    const have=new Set(B.map(r=>r.kosu_id)), KO=((AT.karne&&AT.karne.kosular)||[]).filter(x=>String(x.kosu_id||"").split("/")[0]===d&&!have.has(x.kosu_id));
    if(!B.length&&!KO.length) h+=`<div class="a2-card a2-empty"><div class="e" aria-hidden="true">⏳</div><b>Henüz biten koşu yok</b><p>Sonuçlar açık arşive düştükçe yaklaşık 30 dakikada bir buraya gelir.</p></div>`;
    const lastT=x=>Math.max(...B.filter(r=>r.hipodrom===x).map(r=>tsOf(dayOf(r.kosu_id),r.saat)),0);
    for(const x of hips().slice().sort((a,b)=>lastT(b)-lastT(a))){ const BB=B.filter(r=>r.hipodrom===x).sort((a,b)=>b.kosu-a.kosu); if(!BB.length) continue;
      h+=`<h2 class="a2-sec">${E(x)}</h2>`+BB.map(r=>{ const m=M(r), nm=no=>(m.A.find(y=>y.no===String(no))||{}).ad||"", tt=m.son.tuttu!=null?m.son.tuttu:(m.A[0]&&String(m.son.kazanan)===m.A[0].no);
        return `<a class="a2-card" href="#at/kosu/${K(r.kosu_id)}"><div class="a2-ch"><h2>${r.kosu}. Koşu <span class="a2-mut" style="font-weight:500;font-size:13px">· ${E(r.saat)} · ${E(r.mesafe)} m ${E(r.pist)}</span></h2><span class="a2-pill ${tt?"ok":"no"}">${tt?"✓ model":"✗ model"}</span></div>
          <div class="a2-res">${(m.son.sira||[]).slice(0,3).map((no,i)=>`<div><span class="pl">${i+1}.</span><span class="a2-no${i===0?" w":""}">${E(no)}</span><span class="a2-hn"><b>${E(nm(no))}</b></span>${i===0?`<span class="a2-hp"><small>oran ${fx(m.son.ganyan)}</small></span>`:""}</div>`).join("")}</div>
          <p class="a2-note" style="margin-bottom:0">Model ilk seçimi: ${E(m.son.model_ilk)} ${E(nm(m.son.model_ilk))} · kazananın sabah olasılığı ${P((m.A.find(y=>y.no===String(m.son.kazanan))||{}).ps)}${r.kosudan_once===false?" · karneye sayılmaz":""}</p></a>`; }).join(""); }
    if(KO.length) h+=`<h2 class="a2-sec">Karne kayıtları</h2><div class="a2-card">${KO.map(x=>{ const k=String(x.kosu_id).split("/"); return `<div class="a2-hrow"><span class="a2-no">${E(k[2])}</span><span class="a2-hn"><b>${E(k[1])} ${E(k[2])}. koşu · kazanan: ${E(x.kazanan||"–")}</b><small>Modelin ilk seçimi: ${E(x.ilk_secim||"–")} · kazananın olasılığı ${P(x.p_kazanan)}</small></span><span class="a2-pill ${x.ilk_secim_tuttu?"ok":"no"}">${x.ilk_secim_tuttu?"✓":"✗"}</span></div>`; }).join("")}</div>`;
    const A=ALT(), sv=AT.sev||"orta";
    if(A&&(A.altililar||[]).length) h+=`<h2 class="a2-sec">6'lı tahmin durumu · ${E(SVN[sv])}</h2>`+A.altililar.map(Xa=>{ const s=Xa.sonuc, at=(s&&s.ayak_tuttu&&s.ayak_tuttu[sv])||[]; const n=at.filter(v=>v!=null).length, dus=at.some(v=>v===false);
      return `<a class="a2-card" href="#at/turler" data-tab="turler" data-bt="altili"><div class="a2-ch"><h2>${E(Xa.hipodrom)} ${Xa.no}. 6'lı</h2><span class="a2-pill ${s&&s.tamam?(s.tuttu&&s.tuttu[sv]?"ok":"no"):dus?"no":n?"or":""}">${s&&s.tamam?(s.tuttu&&s.tuttu[sv]?"✓ Tuttu":"✗ Tutmadı"):dus?"KUPO düştü":n?n+"/6 ayakta":"Başlamadı"}</span></div><p class="a2-note" style="margin:0">${E(SVN[sv])} KUPO · ${n}/6 ayak bitti · ${at.filter(Boolean).length} ayak tuttu</p></a>`; }).join("");
    return h+foot(); }
  // ---------- 7) BAHİS ----------
  const SVN={dar:"Dar",orta:"Orta",genis:"Geniş"};
  function karneK(){ if(S.kk) return S.kk; try{ const k=window.ATK_KARNE&&window.ATK_KARNE(); if(k) return S.kk=k; }catch(e){}
    if(!S.kkP) S.kkP=X.j("data/at/kupon_karne.json").then(k=>{ S.kk=k&&k.turler?k:null; if(S.kk&&$("v-at")&&!$("v-at").hidden) paint(); }).catch(()=>{});
    return null; }
  function vTurler(){ let h=titleRow()+`<div class="a2-seg" role="group" aria-label="Tahmin türü" style="margin:0 0 12px"><button type="button" data-bt="altili" aria-pressed="${S.bt==="altili"}">6'lı Tahmin</button><button type="button" data-bt="turler" aria-pressed="${S.bt==="turler"}">Tüm türler</button></div>`;
    if(S.bt==="altili"){ h+=dayChips(); const A=ALT(), sv=AT.sev||"orta", Kk=AT.altK;
      if(!A||!(A.altililar||[]).length) return h+`<div class="a2-card a2-empty"><div class="e" aria-hidden="true">🎯</div><b>Bu gün için 6'lı tahmini hazırlanıyor</b><p>Laboratuvar programdaki "oran başlangıcı" koşularından 6'lıları kurar ve her ayağın atlarını OXXai olasılıklarıyla seçer.</p></div>`+foot();
      h+=`<div class="a2-chips" role="group" aria-label="Kapsam">${["dar","orta","genis"].map(k=>`<button class="a2-chip" type="button" data-sev="${k}" aria-pressed="${sv===k}">${SVN[k]} <small>≤${E((A.butce||{})[k]||{dar:64,orta:192,genis:576}[k])}</small></button>`).join("")}</div>
        <p class="a2-note" style="margin:-4px 2px 12px">"6'yı birden tutma olasılığı" her ayağın seçilen atlarının toplam olasılığının çarpımıdır; KUPO ilk ayak başlayınca kilitlenir. 🥇 = tek at ayak.</p>`;
      for(const Xa of A.altililar){ const L=Xa.seviyeler&&Xa.seviyeler[sv]; if(!L) continue; const s=Xa.sonuc, at=(s&&s.ayak_tuttu&&s.ayak_tuttu[sv])||[];
        const first=raceById(`${AT.d}/${Xa.hipodrom}/${Xa.baslangic_kosu}`), started=first?!open(first):true, c=atCoupon(), has=c&&(c.at||[]).find(z=>z.tur==="altili"&&z.alt===Xa.id&&z.sev===sv);
        h+=`<div class="a2-card"><div class="a2-ch"><h2>${E(Xa.hipodrom)} ${Xa.no}. 6'lı</h2><small>${Xa.baslangic_kosu}.–${Xa.baslangic_kosu+5}. koşu · ${E(Xa.saat||"")}<br>${Xa.kaynak==="oran"?"oranla güncel":"sabah tahmini"}</small></div>
          <div class="a2-kpis k3" style="margin-bottom:6px"><div><b style="color:var(--a2-gi)">${P(L.p,1)}</b><small>6'yı birden<br>tutma</small></div><div><b>${E(L.kombinasyon)}</b><small>kombinasyon</small></div><div>${s&&s.tamam?`<b class="${s.tuttu&&s.tuttu[sv]?"up":"dn"}">${s.tuttu&&s.tuttu[sv]?"✓ Tuttu":"✗"}</b><small>${at.filter(Boolean).length}/6 ayak</small>`:`<b>${L.ayaklar.filter(x=>x.banko).length}</b><small>tek at ayak</small>`}</div></div>
          ${L.ayaklar.map((g,i)=>{ const w=s&&s.kazananlar?s.kazananlar[i]:null, ok=at[i], kid=`${AT.d}/${Xa.hipodrom}/${g.kosu}`;
            return `<div class="a2-al${ok===true?" ok":ok===false?" no":""}"><a class="i" href="#at/kosu/${K(kid)}" aria-label="${i+1}. ayak, ${g.kosu}. koşu">${i+1}. ayak<small>${g.kosu}. koşu ${E(g.saat||"")}</small></a><span class="s">${g.secim.map(no=>{ const hh=(g.atlar||[]).find(q=>String(q[0])===String(no)); return `<span class="${w!=null&&String(w)===String(no)?"w":""}">${E(no)}${hh?" "+E(String(hh[1]).slice(0,14)):""}</span>`; }).join("")}${g.banko?`<em>🥇 tek at</em>`:""}</span><span class="p">${P(g.p_ayak)}${w!=null?`<small>kazanan ${E(w)}</small>`:""}</span></div>`; }).join("")}
          ${Xa.kosudan_once===false?`<p class="a2-note">Koşular başladıktan sonra kuruldu; karneye sayılmaz.</p>`:""}
          <div class="a2-row2" style="margin-top:10px">${started?`<button class="a2-btn q" type="button" disabled>İlk ayak başladı</button>`:`<button class="a2-btn g${has?" on":""}" type="button" data-atka="${E(Xa.id)}">${has?`✓ KUPO'da · ${SVN[sv]}`:`＋ KUPO'ya ekle · ${SVN[sv]}`}</button>`}<button class="a2-btn q" type="button" data-als="${E(Xa.id)}">📤 Paylaş</button></div></div>`; }
      const g=Kk&&Kk.geriye_donuk, gs=g&&g.seviyeler&&g.seviyeler[sv];
      if(gs&&gs.n){ const si=g.sinama&&g.sinama.seviyeler&&g.sinama.seviyeler[sv], ca=Kk.canli&&Kk.canli.seviyeler&&Kk.canli.seviyeler[sv];
        h+=`<div class="a2-card"><div class="a2-ch"><h2>📊 6'lı karnesi · ${SVN[sv]}</h2></div><p class="a2-note" style="margin:0">Geriye dönük test (${E((g.donem||[]).join(" – "))}): ${gs.n} altılıdan tutan <b style="color:var(--a2-ink)">${gs.isabet}</b> · model beklentisi ${fx(gs.beklenen,1)} · 5 ayak tutan ${gs.bes_ayak||0} · ort. ${Math.round(gs.ort_kombinasyon||0)} kombinasyon · ayak isabeti ${P(gs.ayak_isabet)}${gs.altin_ayak&&gs.altin_ayak.n?` · tek at ayak isabeti ${P(gs.altin_ayak.isabet)} (${gs.altin_ayak.n} ayak)`:""}.${si&&si.n?`<br>Son 1/3 sınama dilimi: ${si.n} altılıdan tutan ${si.isabet} · beklenti ${fx(si.beklenen,1)}.`:""}${ca&&ca.n?`<br>Canlı (koşudan önce kilitli): ${ca.n} altılıdan tutan ${ca.isabet} · beklenti ${fx(ca.beklenen,1)}.`:""} 6'lı bir şans oyunudur.</p></div>`; }
    } else {
      const KK=karneK(), T=(KK&&KK.turler)||{};
      h+=`<p class="a2-note" style="margin:0 2px 10px">Her türün kuralı ve modelin geçmiş koşulardaki dürüst karnesi. Çubuk: gerçekleşen isabet; camgöbeği çizgi: modelin beklediği. KUPO kurmak için bir tür seç, sonra koşuyu seç.</p>`;
      if(!KK) h+=`<div class="a2-sk" style="height:120px"></div><div class="a2-sk" style="height:120px"></div>`;
      for(const k of ["ganyan","plase","ikili","sirali_ikili","cifte","uclu","tabela","altili"]){ const z=T[k]; if(!z) continue;
        const r=z.isabet_orani!=null?+z.isabet_orani:(z.n?z.isabet/z.n:null), e=z.beklenen_oran!=null?+z.beklenen_oran:(z.n?z.beklenen/z.n:null), sc=Math.max(r||0,e||0,.0001);
        h+=`<div class="a2-card"><div class="a2-ch"><h2>${E(z.ad||TURAD[k])}</h2><small>${E(z.kisa||"")}</small></div><p class="a2-note" style="margin:0 0 10px;color:var(--a2-ink2)">${E(String(z.kural||"").split(" Varsayım")[0])}</p>
          ${k==="altili"?`<p class="a2-note" style="margin:0">Geçmiş ${E(z.n)} altılıda en olası KUPO ${E(z.isabet)} kez tuttu (model beklentisi ${fx(z.beklenen,1)}).</p>`
            :`<div class="a2-kbr"><span class="t">En olası tek</span><span class="tr" role="img" aria-label="Gerçekleşen ${P(r,1)}, beklenen ${P(e,1)}"><i style="width:${Math.min(100,(r||0)/sc*90)}%"></i><u style="left:${Math.min(98,(e||0)/sc*90)}%"></u></span><span class="v">${P(r,1)}</span></div>
            ${(z.kutu||[]).slice(0,2).map(q=>{ const rr=+q.isabet_orani||0, ee=+q.beklenen_oran||0; return `<div class="a2-kbr" style="margin-top:6px"><span class="t">${E(q.at)} at kutu</span><span class="tr" role="img" aria-label="Gerçekleşen ${P(rr,0)}, beklenen ${P(ee,0)}"><i style="width:${Math.min(100,rr*100)}%"></i><u style="left:${Math.min(98,ee*100)}%"></u></span><span class="v">${P(rr,0)}</span></div>`; }).join("")}
            <p class="a2-note" style="margin:8px 0 0">${E(fx(z.n,0))} koşuda gerçekleşen ${P(r,1)} · model ${P(e,1)}</p>`}
          ${k!=="altili"?`<button class="a2-btn q" type="button" style="margin-top:12px" data-pick="${k}">Koşu seç → ${E(z.ad||TURAD[k])} kur</button>`:`<button class="a2-btn q" type="button" style="margin-top:12px" data-bt="altili">6'lı tahminlerine git</button>`}</div>`; }
      if(KK&&KK.uyari) h+=`<p class="a2-note">${E(KK.uyari)}</p>`;
    }
    return h+foot(); }
  // ---------- 8) KUPON (KUPO'daki At Kuponu; Aşama 3'te genişleyecek) ----------
  function vKupon(){ let h=titleRow()+`<div class="a2-syn">${IC.sync}<span>Bu liste KUPO'daki <b style="color:var(--a2-ink)">At KUPO'su</b> ile aynıdır: koşu kartında eklediğin satır KUPO'da, KUPO'da eklediğin burada görünür.</span></div>`;
    const c=atCoupon(), I=(c&&c.at)||[], others=window.KX?(window.KX.L||[]).filter(z=>z&&z.spor==="at"&&z.durum==="acik"&&z!==c).length:0;
    if(!I.length) return h+`<div class="a2-card a2-empty"><div class="e" aria-hidden="true">🎟️</div><b>At KUPO'su boş</b><p>Bir koşu kartında ya da 6'lı kartında “＋&nbsp;KUPO” düğmesine dokun.</p><a class="a2-btn p" href="#at/program" data-tab="program">Programa git</a></div>`+(others?`<p class="a2-note">${others} açık at KUPO'su daha var; KUPO'da görebilirsin.</p>`:"")+foot();
    const nm=(x,leg,no)=>x.ad&&(x.ad[(leg?(leg+1)+":":"")+no]||(x.tur!=="cifte"&&x.tur!=="altili"&&x.ad[no]))||"";
    const selTxt=x=>(x.sec||[]).map((col,i)=>{ const lb=x.tur==="cifte"?(i?`${x.kosu+1}. k.: `:`${x.kosu}. k.: `):x.tur==="altili"?`${i+1}. `:(x.sec.length>1?`${i+1}.: `:""); return lb+col.map(no=>x.tur==="altili"?no:`${no} ${nm(x,x.tur==="cifte"?i:0,no)}`.trim()).join(x.tur==="altili"?",":", "); }).join(x.tur==="altili"?" / ":" · ");
    const stx=x=>x.ok===true?'<b class="up">✓ tuttu</b>':x.ok===false?'<b class="dn">✗ tutmadı</b>':x.need?"sonuç eksik":"bekliyor";
    const kom=I.reduce((a,x)=>a+(+x.komb||0),0), all=I.reduce((a,x)=>a*(x.p||0),1);
    h+=`<div class="a2-card gold"><div class="a2-ch"><h2>${E(c.ad||"At KUPO'su")}</h2><small>${I.length} satır</small></div>
      ${I.map(x=>`<a class="a2-kr" href="#at/kosu/${K((x.kid||[])[0]||"")}"><span class="tt">${E(x.tur==="altili"?"6'lı":TURAD[x.tur]||x.tur)}</span><span class="tx"><b>${E(x.hip)} ${E(x.kosu)}. ${x.tur==="altili"?"6'lı":"koşu"} · ${E(x.saat||"")}${x.d&&x.d!==AT.d?` · ${E(dLbl(x.d))}`:""}</b><small>${E(selTxt(x))}</small><small>${E(x.komb)} kombinasyon · tutma olasılığı <b style="color:var(--a2-gi)">${P(x.p,1)}</b> · ${stx(x)}${x.res?` · sonuç ${E(x.res)}`:""}</small></span>${IC.chev}</a>`).join("")}
      ${I.length>1?`<p class="a2-note" style="margin:10px 0 0">Tüm satırların birlikte tutma olasılığı ${P(all,2)} · toplam ${kom.toLocaleString("tr-TR")} kombinasyon.</p>`:""}
      <button class="a2-btn p" type="button" data-kupo="${E(c.id)}" style="margin-top:12px">KUPO'da aç</button></div>
      ${others?`<p class="a2-note">${others} açık at KUPO'su daha var; KUPO'da görebilirsin.</p>`:""}
      <p class="a2-note">Satırı değiştirmek için koşu kartındaki “✓ KUPO'da” düğmesine dokun. Silme ve arşiv KUPO'da.</p>`;
    return h+foot(); }
  // ---------- 9) TAKİP ----------
  function vTakip(){ let h=`<h1 class="a2-h2" style="margin-bottom:12px">Takip listem</h1>`;
    const run=(k,ad)=>{ for(const r of races()){ const m=M(r); const x=m.A.find(y=>y[k==="at"?"ad":k]===ad); if(x) return {r,x,m}; } return null; };
    const secH=(k,l)=>{ const L=TK[k]; return `<div class="a2-card"><div class="a2-ch"><h2>${l}</h2><small>${L.length}</small></div>${L.length?L.map(ad=>{ const o=run(k,ad), href=k==="at"?(o?`#at/at/${K(o.r.kosu_id)}/${enc(o.x.no)}`:""):`#at/${k}/${enc(ad)}`;
        const inner=`<b>${E(ad)}</b><small>${o?`${E(dLbl(AT.d))} ${E(o.r.hipodrom)} ${o.r.kosu}. koşu · ${E(o.r.saat)}${k!=="at"?" · "+E(o.x.ad):""} · ${P(o.x.p)}`:`${E(dLbl(AT.d))} programda yok`}</small>`;
        return `<div class="a2-hrow">${href?`<a class="a2-hn" href="${href}" style="min-height:44px;display:flex;flex-direction:column;justify-content:center">${inner}</a>`:`<span class="a2-hn">${inner}</span>`}${o?stPill(o.r,o.m):""}<button class="a2-x" type="button" data-tk="${k}|${E(ad)}" aria-label="${E(ad)} takipten çıkar">✕</button></div>`; }).join(""):`<p class="a2-note" style="margin:0">Henüz yok. ${k==="at"?"At":k==="jokey"?"Jokey":"Antrenör"} profilindeki “☆ Takip et” ile ekle.</p>`}</div>`; };
    h+=secH("at","🐎 Atlar")+secH("jokey","🏇 Jokeyler")+secH("antrenor","🧑‍🏫 Antrenörler");
    h+=`<div class="a2-card"><div class="a2-ch"><h2>🔔 “Atım koşuyor” bildirimi</h2><span class="a2-pill">yakında</span></div><p class="a2-note" style="margin:0">Takip ettiğin at, jokey ya da antrenör programa girince Bugün ekranının üstünde “Takip ettiklerin koşuyor” kartında görünür. Telefona bildirim gönderimi ayrı bir aşamada, yalnız sen açarsan gelecek.</p></div>`;
    return h+foot(); }
  // ---------- 10) İSTATİSTİK (eski hero + "Model ne kadar başarılı?" + jokey sıralaması) ----------
  function istHtml(short){ const Mm=AT.model&&AT.model.degerlendirme, me=(Mm&&Mm.metrik)||{}, n=(Mm&&Mm.kosu_sayisi&&Mm.kosu_sayisi.sinama)||0;
    const Kk=((AT.karne&&AT.karne.kosular)||[]).filter(x=>x.kosudan_once!==false&&!x.mod_hatali), kn=Kk.length, kh=Kk.filter(x=>x.ilk_secim_tuttu).length;
    let h=short?"":`<h1 class="a2-h2" style="margin-bottom:12px">İstatistik<span class="a2-dn">DENEME</span></h1>`;
    h+=`<div class="a2-card"><div class="a2-ch"><h2>Model ne kadar başarılı?</h2><small>${n?n.toLocaleString("tr-TR")+" koşu":""}</small></div>
      <div class="a2-kpis"><div><b>${P(me.model&&me.model.ilk_secim_isabet)}</b><small>sabah tahmini<br>ilk seçim</small></div><div><b style="color:var(--a2-gi)">${P(me.harman&&me.harman.ilk_secim_isabet)}</b><small>oranla harman<br>ilk seçim</small></div><div><b>${P(me.favori&&me.favori.ilk_secim_isabet)}</b><small>piyasa favorisi<br>aynı koşular</small></div><div><b>${kn?P(kh/kn):"–"}</b><small>kilitli karne<br>${kn?kn+" koşu":"birikiyor"}</small></div></div>
      <p class="a2-note" style="margin-top:10px">🧪 Dürüst durum: <b style="color:var(--a2-ink2)">sabah tahmini</b> oran açılmadan yapılır ve piyasa favorisinin gerisindedir. Koşu öncesi oranla harmanlanınca olasılık hatasında piyasayı az farkla geçiyor, ilk seçim isabetinde ise henüz favori seviyesinde. OXXai at laboratuvarı her gece geçmiş koşulardan yeniden öğrenir, yalnız isabeti artıran ayarı kabul eder. Garanti değildir · 18+. Şans oyunu sitesine yönlendirme yoktur.</p></div>`;
    if(short) return h;
    const J=JOK(); if(!J||!(J.jokeyler||[]).length) return h+`<div class="a2-card"><p class="a2-note" style="margin:0">Jokey istatistikleri hazırlanıyor. Laboratuvar her gece geçmiş koşulardan jokeylerin atın gücünden arındırılmış katkısını hesaplar.</p></div>`+foot();
    const tr=t=>t==="yukseliyor"?" 📈":t==="dusuyor"?" 📉":"";
    const L=(arr,k,nn)=>{ const A=arr.slice(0,nn), mx=Math.max(...A.map(x=>Math.abs(+x.katki||0)),1e-9);
      return A.map((x,i)=>`<a class="a2-jr" href="#at/${k}/${enc(x.ad)}"><span class="rk">${i+1}</span><span class="a2-hn"><b>${isTk(k,x.ad)?'<span class="a2-star">★</span> ':""}${E(x.ad)}${tr(x.form_trend)}</b><small>${E(x.binis_90g||x.kosu_90g)} ${k==="jokey"?"biniş":"koşu"} · kazanma ${P(x.kazanma_90g)} · ilk 3 ${P(x.ilk3_90g)}${(x.bugun_binis||[]).length?` · bugün ${x.bugun_binis.length} biniş`:""}</small></span><span class="kk"><b class="${+x.katki>0?"up":"dn"}">${+x.katki>0?"+":""}${fx(x.katki,1)}</b><div class="a2-barr"><i style="width:${Math.max(4,Math.abs(+x.katki||0)/mx*100)}%;${+x.katki<0?"background:#FF8A80":""}"></i></div></span></a>`).join(""); };
    h+=`<h2 class="a2-sec">🏇 Jokeyler · son 90 gün</h2><div class="a2-card"><p class="a2-note" style="margin:0 0 6px">“Katkı”, jokeyin aynı atla beklenenden ne kadar iyi sonuç aldığını gösterir; yalnız kazanma sayısına bakmaz. 📈 formu yükselen, 📉 düşen.</p>${L(J.jokeyler,"jokey",25)}</div>`;
    if((J.antrenorler||[]).length) h+=`<h2 class="a2-sec">🧑‍🏫 Antrenörler</h2><div class="a2-card">${L(J.antrenorler,"antrenor",15)}</div>`;
    if((J.ikililer||[]).length) h+=`<h2 class="a2-sec">🤝 En uyumlu jokey–antrenör ikilileri</h2><div class="a2-card">${J.ikililer.slice(0,10).map((x,i)=>`<div class="a2-jr"><span class="rk">${i+1}</span><span class="a2-hn"><b>${E(x.jokey)} + ${E(x.antrenor)}</b><small>${E(x.binis)} birliktelik · kazanma ${P(x.kazanma)}</small></span><span class="kk"><b class="${+x.katki>0?"up":"dn"}">${+x.katki>0?"+":""}${fx(x.katki,1)}</b></span></div>`).join("")}</div>`;
    return h+`<p class="a2-note">Dönem: ${E((J.donem||[]).join(" – "))} · güncelleme ${E(J.guncelleme||"")}. Kaynak: açık yarış sonuç arşivi; yalnız türetilmiş istatistik.</p>`+foot(); }
  // =====================================================================
  // Paylaş (eski metinlerle aynı)
  // =====================================================================
  async function shareText(t,ok){ try{ if(navigator.share){ await navigator.share({text:t}); return; } }catch(e){ return; }
    try{ await navigator.clipboard.writeText(t); toast(ok); }catch(e){ location.href="https://wa.me/?text="+encodeURIComponent(t); } }
  function shareRace(rid){ const r=raceById(rid); if(!r) return; const m=M(r);
    shareText(`🐎 ${r.hipodrom} ${r.kosu}. koşu · ${r.saat||""} (${r.mesafe} m ${r.pist})\nOXXai tahmini${m.oranli?" (oranla güncel)":" (sabah)"}:\n`+m.A.slice(0,3).map((h,i)=>`${i+1}) ${h.no} ${h.ad} %${Math.round(h.p_goster*100)}`).join("\n")+`\nHobi amaçlı olasılıktır, garanti değildir · 18+\nbulutoxx.github.io/#at/kosu/${K(rid)}`,"📋 Koşu tahmini kopyalandı"); }
  function shareAlt(id){ const A=ALT(), Xa=A&&(A.altililar||[]).find(x=>x.id===id); if(!Xa) return; const sv=AT.sev||"orta", L=Xa.seviyeler[sv]; if(!L) return;
    shareText(`🎯 ${Xa.hipodrom} ${Xa.no}. 6'lı (${Xa.baslangic_kosu}.–${Xa.baslangic_kosu+5}. koşular) · OXXai ${SVN[sv]} tahmini\n`+L.ayaklar.map((g,i)=>`${i+1}. ayak: ${g.secim.join("-")}${g.banko?" (tek at)":""}`).join("\n")+`\n6'yı birden tutma olasılığı %${(L.p*100).toFixed(1).replace(".",",")} · ${L.kombinasyon} kombinasyon\nHobi amaçlı olasılıktır, garanti değildir · 18+`,"📋 6'lı tahmini kopyalandı"); }
  // =====================================================================
  // Etkileşim (tek dinleyici; kupon düğmeleri data-atkr/atkh/atka → atkupon-v98 yakalar)
  // =====================================================================
  function onClick(e){ const t=e.target;
    const a=t.closest("a[href^='#at']");
    if(a&&(nav.contains(a)||box.contains(a))){ e.preventDefault(); tap();
      if(a.dataset.hip){ S.hip=a.dataset.hip; S.hipU=true; }
      if(a.dataset.bt){ S.bt=a.dataset.bt; lsS("bx-at2-bt",S.bt); }
      const path=a.getAttribute("href").replace(/^#at\/?/,""), v=path.split("/")[0]||"bugun";
      // 6'lı/tür seçimi modunda programdan koşuya dokununca kurucu doğrudan açılır
      if(S.pickTur&&v==="kosu"&&a.dataset.kid){ const r=raceById(a.dataset.kid); if(r&&open(r)&&typeof window.atkOpen==="function"){ const tur=S.pickTur; S.pickTur=null; paint(); window.atkOpen(r.kosu_id,{tur}); return; } if(r&&!open(r)){ toast("Bu koşu başladı; başlamamış bir koşu seç"); return; } }
      if(isTab(v)){ if(v!=="program") S.pickTur=null; go(path,false); }
      else if(a.dataset.sib) go(path,false);   // koşu çipleri: aynı yığın seviyesinde geçiş (geri tuşu programa döner)
      else go(path,true);
      return; }
    const b=t.closest("button"); if(!b||!(nav.contains(b)||box.contains(b))) return;
    const d=b.dataset;
    if(d.back!=null){ tap(); goBack(d.back); return; }
    if(d.day){ tap(); AT.d=d.day; S.hipU=false; try{ X.render(); }catch(_){} paint(); return; }
    if(d.hp){ tap(); S.hip=d.hp; S.hipU=true; paint(); return; }
    if(d.mode){ tap(); S.mode=d.mode; lsS("bx-at2-mod",S.mode); paint(); return; }
    if(d.sort){ tap(); S.sort=d.sort; paint(); return; }
    if(d.bt){ tap(); S.bt=d.bt; lsS("bx-at2-bt",S.bt); if(route().v!=="turler") go("turler",false); else paint(); return; }
    if(d.sev){ tap(); AT.sev=d.sev; lsS("bx-at2-sev",d.sev); try{ X.render(); }catch(_){} paint(); return; }
    if(d.tk){ const i=d.tk.indexOf("|"); tkTog(d.tk.slice(0,i),d.tk.slice(i+1)); return; }
    if(d.share){ shareRace(d.share); return; }
    if(d.als){ shareAlt(d.als); return; }
    if(d.pick){ tap(); S.pickTur=d.pick; go("program",false); return; }
    if(d.pickx!=null){ S.pickTur=null; paint(); return; }
    if(d.kupo){ try{ const KX=window.KX, c=KX&&KX.L.find(z=>z.id===d.kupo); if(c){ KX.aktif=c.id; lsS("bx-kupon-at-son",c.id); window.kxSave&&window.kxSave(); } window.kxOpen("cp"); }catch(_){ toast("KUPO açılamadı"); } return; }
    if(d.re!=null){ X.load(); return; } }
  nav.addEventListener("click",onClick); box.addEventListener("click",onClick);
  // padok içindeki at adları (eski data-ah) → At profili
  box.addEventListener("click",e=>{ const s=e.target.closest("[data-ah]"); if(!s||!box.contains(s)) return; e.preventDefault(); const [rid,no]=s.dataset.ah.split("|"); tap(); go("at/"+K(rid)+"/"+enc(no),true); });
  box.addEventListener("keydown",e=>{ if((e.key==="Enter"||e.key===" ")&&e.target.matches&&e.target.matches(".pd-h[data-ah]")){ e.preventDefault(); e.target.click(); } });
  box.addEventListener("toggle",e=>{ if(e.target&&e.target.id==="at2pd"){ S.pdOpen=e.target.open; const s=e.target.querySelector("summary"); if(s) s.textContent=S.pdOpen?"Daha az göster":`Devamını oku (${e.target.querySelectorAll("p").length})`; } },true);
  // padok bağlantıları klavyeyle de açılsın
  new MutationObserver(()=>box.querySelectorAll(".pd-h[data-ah]:not([tabindex])").forEach(x=>x.tabIndex=0)).observe(box,{childList:true});
  // =====================================================================
  // showSport("at") sarmalayıcısı: eski AT.tab değerleri yeni sekmelere eşlenir, #at/... bağlantısı korunur
  // =====================================================================
  const MAP={altin:"bugun",sonuc:"sonuc",altili:"turler",jokey:"istatistik"};
  try{ const _ss=showSport; showSport=function(s){ if(s!=="at") return _ss.apply(this,arguments);
      const h0=location.hash, st0=history.state; const r=_ss.apply(this,arguments);
      let path=/^#at\//.test(h0)?h0:null; const lt=AT.tab; if(lt&&lt!=="tah"){ AT.tab="tah"; const v=MAP[lt]; if(v){ path="#at/"+v; if(v==="turler"){ S.bt="altili"; } } }
      if(path) try{ history.replaceState(/^#at\//.test(h0)?st0:null,"",path); }catch(e){}
      paint(true); return r; }; }catch(e){}
  // derin bağlantı: #at/... ile açılış
  if(/^#at\//.test(location.hash||"")) setTimeout(()=>{ try{ showSport("at"); }catch(e){} },450);
  const _ld=X.load; X.load=async function(){ const r=await _ld.apply(this,arguments); S.loadedOnce=true; schedule(); return r; };
  setInterval(()=>{ const v=$("v-at"); if(v&&!v.hidden&&!document.hidden&&route().v==="bugun") paint(); },60000);
  window.BX_AT2={paint,route,go,TK};
  paint();
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: at2-v106 */
/* id: at3-v109 */ try {
// =====================================================================
// v109 · AT YARIŞI 2.0 — lab/at/TASARIM.md Aşama 3 ve 4 (at2-v106'yı SARAR; at2 ve atkupon-v98 kodu değişmez)
// • Kupon sekmesi tam işlevli: at2 #at2Box'u her boyadığında (MutationObserver) Kupon ekranı bu blokla yeniden yazılır.
//   Veri TEK depo: KUPO'nun "bx-kuponlar" listesi (window.KX.L) içindeki spor:"at" kuponları — ayrı depo yok.
//   Satır sil · tür değiştir (atkupon-v98 kurucusu seçimler korunarak açılır: window.atkOpen) · düzenle · yeni at kuponu
//   aç/adlandır · kuponlar arası geçiş (KUPO'nun aktif kuponu da değişir) · Eski at kuponları · istatistik.
//   Futbol KUPO'ları burada hiç listelenmez; at satırları futbol "items" dizisine asla yazılmaz.
// • Yüzen "At kuponum" çubuğu (#at3Bar): Kupon sekmesi dışındaki at ekranlarında, kupon boş değilse; dokununca Kupon sekmesi.
// • Oran izi: data/at/oran_izi/<gün>.json (lab/at/canli.py her 30 dk; yalnız oran değişince nokta) → koşu kartında ve
//   at profilinde mini çizgi. Veri yoksa "henüz iz yok"; ara değer/uydurma yok.
// • Kariyer: data/at/kariyer.json (lab/at/kariyer.py; yalnız günün koşucuları, sonuç arşivinden türetilmiş) → At profili.
// Veri yalnız depodaki türetilmiş dosyalardan; tjk.org'a istek yok, oyun bağlantısı yok, para tutarı yok · 18+.
// =====================================================================
(function(){
  const X=window.BX_AT, A2=window.BX_AT2; if(!X||!X.AT||!A2||!window.KX) return;
  const AT=X.AT, sec=$("v-at"), box=$("at2Box"), nav=$("at2Nav"); if(!sec||!box||!nav) return;
  // ---------- yardımcılar ----------
  const E=s=>s==null?"":esc(s), enc=encodeURIComponent, dec=s=>{ try{ return decodeURIComponent(s); }catch(e){ return s; } };
  const K=kid=>String(kid).split("/").map(enc).join("~"), unK=s=>String(s).split("~").map(dec).join("/");
  const lsS=(k,v)=>{ try{ localStorage.setItem(k,v); }catch(e){} };
  const NOW=()=>Date.now(), uid=()=>Date.now().toString(36)+Math.random().toString(36).slice(2,6);
  const P=(x,d)=>x==null||!isFinite(x)?"–":(x>0&&x<.0001?"<%0,01":"%"+(x*100).toLocaleString("tr-TR",{maximumFractionDigits:d==null?(x<.01?2:x<.1?1:0):d}));
  const fN=n=>(+n||0).toLocaleString("tr-TR"), fx=(x,d=2)=>x==null||!isFinite(+x)?"–":(+x).toLocaleString("tr-TR",{minimumFractionDigits:d,maximumFractionDigits:d});
  const tsOf=(d,s)=>Date.parse(d+"T"+(s||"23:59")+":00+03:00"), dayOf=kid=>String(kid||"").split("/")[0];
  const tap=()=>{ try{ buzz(6); }catch(e){} };
  const KX=()=>window.KX;
  const TUR={ganyan:{ad:"Kazanan",kol:1,enaz:2},plase:{ad:"Derece",kol:1,enaz:7},ikili:{ad:"İkili",kol:1,enaz:7},sirali_ikili:{ad:"Sıralı İkili",kol:2,enaz:4},
    cifte:{ad:"Çifte",kol:2,enaz:2},uclu:{ad:"Sıralı Üçlü",kol:3,enaz:4},tabela:{ad:"Tabela",kol:4,enaz:5},altili:{ad:"6'lı Tahmin",kol:6,enaz:1}};
  const ORDER=["ganyan","plase","ikili","sirali_ikili","cifte","uclu","tabela","altili"];
  const KAR=()=>{ try{ const k=window.ATK_KARNE&&window.ATK_KARNE(); if(k&&k.turler) for(const t of ORDER){ const z=k.turler[t]; if(z&&TUR[t]){ if(z.ad) TUR[t].ad=z.ad; if(z.en_az_at) TUR[t].enaz=+z.en_az_at; } } return k||null; }catch(e){ return null; } };
  const SVN={dar:"Dar",orta:"Orta",genis:"Geniş"};
  const IC={pen:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/></svg>`,
    ok:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>`,
    sync:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12a8 8 0 0 1 14-5.3L20 9M20 4v5h-5M20 12a8 8 0 0 1-14 5.3L4 15M4 20v-5h5"/></svg>`,
    chev:`<svg class="a2-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg>`};
  // ---------- KUPO deposu (window.KX; v95/v98 ile aynı şema ve aynı aktif kupon kuralı) ----------
  const isAt=c=>!!c&&c.spor==="at";
  const opens=()=>KX().L.filter(c=>isAt(c)&&c.durum==="acik").sort((a,b)=>a.olusturma-b.olusturma);
  const pasts=()=>KX().L.filter(c=>isAt(c)&&c.durum!=="acik").sort((a,b)=>(b.bitti||b.arsivAt||b.olusturma)-(a.bitti||a.arsivAt||a.olusturma));
  function cur(){ const L=opens(); if(!L.length) return null; const a=L.find(c=>c.id===KX().aktif); if(a) return a;
    let id=""; try{ id=localStorage.getItem("bx-kupon-at-son")||""; }catch(e){} return L.find(c=>c.id===id)||L.slice().sort((x,y)=>(y.upd||y.olusturma)-(x.upd||x.olusturma))[0]; }
  function save(c){ if(c) c.upd=NOW(); try{ window.kxSave(); }catch(e){} }
  function setAct(c){ if(!c) return; KX().aktif=c.id; lsS("bx-kupon-at-son",c.id); save(); try{ paintCoupon(); }catch(e){} }
  function nextNo(){ let mx=0; for(const c of KX().L){ const m=/^At (?:Kuponu|KUPO'su) (\d+)$/.exec(c.ad||""); if(m) mx=Math.max(mx,+m[1]); } return mx+1; }
  function newAt(){ const c={id:uid(),ad:"At KUPO'su "+nextNo(),spor:"at",items:[],at:[],olusturma:NOW(),upd:NOW(),durum:"acik"}; KX().L.push(c); setAct(c); return c; }
  function delC(c){ try{ const k="bx-kuponlar-sil"; const L=JSON.parse(localStorage.getItem(k)||"[]"); if(!L.includes(c.id)) L.push(c.id); localStorage.setItem(k,JSON.stringify(L.slice(-500))); }catch(e){}
    KX().L=KX().L.filter(z=>z.id!==c.id); if(KX().aktif===c.id) KX().aktif=null; try{ window.kxAct(); }catch(e){} save(); }
  const doneR=x=>x.ok!=null||!!x.need||!!x.iade;
  function stAt(c){ const I=Array.isArray(c&&c.at)?c.at:[]; if(!I.length) return "e"; if(I.some(i=>i.ok===false)) return "x"; const L=I.filter(i=>!i.iade); if(!L.length) return "i";
    if(L.every(i=>i.ok===true)) return "g"; if(I.every(doneR)) return "q"; return "w"; }
  const STL={e:"Boş",w:"Bekliyor",g:"Tuttu",x:"Tutmadı",q:"Sonuç eksik",i:"İade"};
  const stPill=c=>{ const s=stAt(c); return `<span class="a2-pill ${s==="g"?"ok":s==="x"?"no":s==="q"?"w":""}">${s==="g"?"✓ ":s==="x"?"✗ ":s==="i"?"↺ ":""}${STL[s]}</span>`; };
  const pAll=I=>I.reduce((a,x)=>a*(+x.p||0),1), kAll=I=>I.reduce((a,x)=>a+(+x.komb||0),0);
  // ---------- koşu durumu ----------
  function raceById(id){ const D=AT.data[dayOf(id)]; return D&&(D.kosular||[]).find(r=>r.kosu_id===id)||null; }
  function cOf(kid){ const C=(AT.canli||{})[dayOf(kid)]; return C&&(C.kosular||[]).find(x=>x.kosu_id===kid)||null; }
  function startedK(kid,x){ const c=cOf(kid); if(c&&(c.sonuc||c.durum==="bitti")) return true; const r=raceById(kid); const t=r?tsOf(dayOf(kid),r.saat):(x&&x.t);
    return isFinite(t)&&t<=NOW(); }
  const rowOpen=x=>x.ok==null&&!x.iade&&!startedK(x.kid[0],x);
  // ---------- Kupon sekmesi ----------
  const U={edit:false,cf:null,tur:null,od:null,ocf:null};
  const nm=(x,leg,no)=>x.ad&&(x.ad[(leg?(leg+1)+":":"")+no]||(x.tur!=="cifte"&&x.tur!=="altili"&&x.ad[no]))||"";
  const selTxt=x=>(x.sec||[]).map((col,i)=>{ const lb=x.tur==="cifte"?(i?`${x.kosu+1}. k.: `:`${x.kosu}. k.: `):x.tur==="altili"?`${i+1}. `:((x.sec.length>1)?`${i+1}.: `:"");
    return lb+col.map(no=>x.tur==="altili"?no:`${no} ${nm(x,x.tur==="cifte"?i:0,no)}`.trim()).join(x.tur==="altili"?",":", "); }).join(x.tur==="altili"?" / ":" · ");
  const where=x=>x.tur==="altili"?`${x.hip} ${x.altNo||""}. 6'lı · ${x.kosu}.–${x.kosu+5}. koşular`:x.tur==="cifte"?`${x.hip} ${x.kosu}. + ${x.kosu+1}. koşu`:`${x.hip} ${x.kosu}. koşu`;
  function rowHtml(x,i,ro){ const T=TUR[x.tur]||{ad:x.tur}, op=!ro&&rowOpen(x), d=x.d&&x.d!==AT.d?` · ${X.dLbl(x.d)}`:"";
    const st=x.ok===true?'<b class="up">✓ tuttu</b>':x.ok===false?`<b class="dn">✗ tutmadı${x.srz?" (sırasız tuttu)":""}</b>`:x.iade?"↺ iade · koşul dışı":x.need?"sonuç eksik":startedK(x.kid[0],x)?"koşu başladı · sonuç bekleniyor":"bekliyor";
    const res=x.ok===true?`<span class="a3-res ok" role="img" aria-label="Tuttu">✓</span>`:x.ok===false?`<span class="a3-res no" role="img" aria-label="Tutmadı">✗</span>`:"";
    const href=x.tur==="altili"?"#at/turler":`#at/kosu/${K(x.kid[0])}`;
    let h=`<div class="a2-kr a3-r" data-rid="${E(x.id)}"><a class="a3-rl" href="${href}"${x.tur==="altili"?' data-bt="altili"':""}><span class="tt">${E(x.tur==="altili"?"6'lı":T.ad)}</span><span class="tx"><b>${E(where(x))}${x.saat?" · "+E(x.saat):""}${E(d)}</b><small>${E(selTxt(x))}${x.tur==="altili"&&x.sev?" · "+E(SVN[x.sev]||""):""}</small><small>${fN(x.komb)} kombinasyon · OXXai <b style="color:var(--a2-gi)">${P(x.p)}</b> · ${st}${x.res?` · sonuç ${E(x.res)}`:""}${(x.kx||[]).length?` · koşmayan at çıkarıldı (${E(x.kx.join(", "))})`:""}</small></span>${res}</a>`;
    if(op){ h+=`<div class="a3-ra">${x.tur!=="altili"?`<button type="button" data-k3="tur" data-i="${i}" aria-expanded="${U.tur===x.id}">Tür: ${E(T.ad)} ▾</button><button type="button" data-k3="ed" data-i="${i}">Düzenle</button>`:`<button type="button" data-k3="six" data-i="${i}">6'lıyı gör</button>`}<button type="button" class="a3-rm" data-k3="rm" data-i="${i}" aria-label="${E(where(x))} satırını KUPO'dan çıkar">✕</button></div>`;
      if(U.tur===x.id&&x.tur!=="altili") h+=turPick(x,i); }
    else if(!ro&&x.ok==null&&!x.iade) h+=`<div class="a3-ra"><button type="button" class="a3-rm" data-k3="rm" data-i="${i}" aria-label="${E(where(x))} satırını KUPO'dan çıkar">✕</button></div>`;
    return h+`</div>`; }
  function nOf(kid){ const r=raceById(kid); if(!r) return 0; const c=cOf(kid); if(c&&(c.atlar||[]).some(h=>h.p_oran!=null)) return c.atlar.filter(h=>h.p_oran!=null).length; return (r.atlar||[]).length; }
  function turPick(x,i){ const n=nOf(x.kid[0]), r=raceById(x.kid[0]), nx=r&&raceById(`${dayOf(r.kosu_id)}/${r.hipodrom}/${r.kosu+1}`);
    const L=ORDER.filter(t=>t!=="altili"&&t!==x.tur).map(t=>{ let er=""; if(n<TUR[t].enaz) er=`${n} atlı koşuda ${TUR[t].ad} yok`; else if(t==="cifte"&&(!nx||startedK(nx.kosu_id))) er="Sonraki koşu yok ya da başladı";
      return `<button type="button" data-k3="tset" data-i="${i}" data-t="${t}"${er?` aria-disabled="true" data-er="${E(er)}"`:""}>${E(TUR[t].ad)}</button>`; }).join("");
    return `<div class="a3-tp" role="group" aria-label="Yeni tahmin türü"><p>Tür seç: kurucu, seçtiğin atlar korunarak açılır; kombinasyon ve OXXai olasılığını görüp “Satırı güncelle” ile onaylarsın.</p><div>${L}</div></div>`; }
  // satırın atlarını yeni türe taşı (kurucu son sözü söyler; hiçbir şey kendiliğinden kaydedilmez)
  function conv(x,t){ const S=(x.tur==="cifte"?[x.sec[0]||[]]:x.sec||[]).map(c=>(c||[]).map(String)), H=[...new Set(S.flat())], k=TUR[t].kol;
    if(t==="ganyan"||t==="plase") return [H.slice(0,1)];
    if(t==="ikili") return [H];
    if(t==="cifte") return [S[0]&&S[0].length?S[0].slice():H.slice(0,1),[]];
    const ordered=S.length>1&&x.tur!=="cifte";
    return Array.from({length:k},(_,j)=>ordered?(S[j]?S[j].slice():[]):(x.tur==="ikili"?H.slice():(j===0?H.slice():[]))); }
  function statsHtml(){ const all=KX().L.filter(isAt), P0=pasts(), D=P0.filter(c=>{ const s=stAt(c); return s==="g"||s==="x"; }), W=D.filter(c=>stAt(c)==="g");
    const R=all.flatMap(c=>c.at||[]).filter(x=>x.ok!=null&&!x.iade), Kk=KAR();
    if(!R.length&&!D.length) return `<h2 class="a2-sec">📊 At KUPO'su istatistiğin</h2><div class="a2-card"><p class="a2-note" style="margin:0">Henüz sonuçlanan at satırın yok. Koşular bittikçe kazanma oranın, tür bazlı isabetin ve OXXai olasılığının ne kadar tuttuğu burada birikir (yalnız bu telefonda).</p></div>`;
    const by={}; for(const x of R){ const b=by[x.tur]||(by[x.tur]={n:0,h:0,e:0}); b.n++; if(x.ok) b.h++; b.e+=+x.p||0; }
    const hr=R.length?R.filter(x=>x.ok).length/R.length:null, pr=R.length?R.reduce((a,x)=>a+(+x.p||0),0)/R.length:null, pc=D.length?D.reduce((a,c)=>a+pAll(c.at||[]),0)/D.length:null;
    const rate=z=>!z||!z.n?null:(z.isabet_orani!=null?+z.isabet_orani:(+z.isabet||0)/z.n);
    const kt=ORDER.filter(t=>by[t]).map(t=>{ const b=by[t], z=Kk&&Kk.turler&&Kk.turler[t]; return `<div><span><b>${E(TUR[t].ad)}</b></span><span>${b.h}/${b.n}</span><span>${P(b.e/b.n)}</span><span>${z&&z.n&&t!=="altili"?P(rate(z)):"–"}</span></div>`; }).join("");
    return `<h2 class="a2-sec">📊 At KUPO'su istatistiğin</h2><div class="a2-card">
      <div class="a2-kpis k3"><div><b style="color:var(--a2-gi)">${D.length?P(W.length/D.length):"–"}</b><small>KUPO kazanma<br>${W.length}/${D.length}</small></div><div><b>${hr==null?"–":P(hr)}</b><small>satır isabeti<br>${R.filter(x=>x.ok).length}/${R.length}</small></div><div><b>${pr==null?"–":P(pr)}</b><small>OXXai ortalama<br>satır olasılığı</small></div></div>
      <p class="a2-note" style="margin-top:10px">OXXai olasılığı ne kadar tuttu: satırlarda ortalama <b style="color:var(--a2-ink2)">${pr==null?"–":P(pr)}</b> demişti, gerçekte <b style="color:var(--a2-ink2)">${hr==null?"–":P(hr)}</b> tuttu.${D.length?` KUPO'larda ortalama birlikte tutma olasılığı ${P(pc)}, gerçekleşen ${P(W.length/D.length)}.`:""}${R.length<20?" Örnek az; temkinli oku.":""}</p>
      ${kt?`<div class="a3-kt" role="table" aria-label="Tür bazlı isabet"><div role="row"><span>Tür</span><span>Tutan</span><span>OXXai bekl.</span><span>Geri test</span></div>${kt}</div><p class="a2-note" style="margin:6px 0 0">Geri test: o türde en olası tek kombinasyonun geçmiş koşulardaki isabeti${Kk&&Kk.donem?` (${E((Kk.donem||[]).join(" – "))})`:""}.</p>`:""}</div>`; }
  function oldHtml(){ const L=pasts(); if(!L.length) return "";
    return `<h2 class="a2-sec">🗂️ Eski at KUPO'ların <span class="a2-mut" style="text-transform:none;letter-spacing:0;font-weight:600">· ${L.length}</span></h2>`+L.slice(0,30).map(c=>{ const I=c.at||[], o=U.od===c.id, h=I.filter(x=>x.ok).length;
      return `<div class="a3-oc"><button type="button" class="a3-oh" data-k3="oo" data-c="${E(c.id)}" aria-expanded="${o}"><span class="tx"><b>${E(c.ad)}</b><small>${E(ist(new Date(c.bitti||c.arsivAt||c.olusturma),{day:"numeric",month:"short",year:"numeric"}))} · ${I.length} satır · ${h}/${I.length} tuttu · OXXai ${P(pAll(I))}${c.durum==="arsiv"?" · arşiv":""}</small></span>${stPill(c)}${IC.chev}</button>
        ${o?`<div class="a3-od">${I.length?I.map((x,i)=>rowHtml(x,i,true)).join(""):`<p class="a2-note">Boş KUPO.</p>`}
          ${U.ocf===c.id?`<div class="a3-cf" role="alertdialog" aria-label="KUPO'yu sil"><p><b>${E(c.ad)}</b> kalıcı olarak silinsin mi? KUPO'dan da silinir.</p><div class="a2-row2"><button class="a2-btn q" type="button" data-k3="ocfno">Vazgeç</button><button class="a2-btn q a3-btn-d" type="button" data-k3="ocfdel" data-c="${E(c.id)}">Sil</button></div></div>`
            :`<div class="a2-row2" style="margin-top:8px">${c.durum==="arsiv"?`<button class="a2-btn q" type="button" data-k3="oback" data-c="${E(c.id)}">↩ Açık KUPO'lara al</button>`:`<span></span>`}<button class="a2-btn q" type="button" data-k3="odel" data-c="${E(c.id)}">Sil</button></div>`}</div>`:""}</div>`; }).join("")
      +(L.length>30?`<p class="a2-note">En yeni 30 KUPO gösteriliyor; tümü KUPO › Eski KUPO'larım bölümünde.</p>`:""); }
  function vKupon(hd){ const L=opens(), c=cur(); try{ KAR(); }catch(e){}
    let h=hd+`<div class="a2-syn">${IC.sync}<span>Buradaki at KUPO'ları <b style="color:var(--a2-ink)">KUPO ekranındakilerle aynıdır</b>: bir yerde yaptığın değişiklik ötekinde de görünür. Futbol KUPO'ları burada listelenmez.</span></div>`;
    h+=`<div class="a2-chips a3-sw" role="group" aria-label="At KUPO'ların">${L.map(z=>`<button class="a2-chip" type="button" data-k3="sw" data-c="${E(z.id)}" aria-pressed="${!!c&&z.id===c.id}"><span>${E(z.ad)}</span> <small>${(z.at||[]).length}</small></button>`).join("")}<button class="a2-chip a3-new" type="button" data-k3="new">＋ Yeni at KUPO'su</button></div>`;
    if(!c){ h+=`<div class="a2-card a2-empty"><div class="e" aria-hidden="true">🎟️</div><b>Açık at KUPO'su yok</b><p>Yeni bir at KUPO'su aç ya da bir koşu kartında “＋&nbsp;KUPO” düğmesine dokun; at KUPO'su kendiliğinden açılır.</p><div class="a2-row2"><button class="a2-btn g" type="button" data-k3="new">＋ Yeni at KUPO'su</button><a class="a2-btn p" href="#at/program" data-tab="program">Programa git</a></div></div>`; }
    else { const I=c.at||[], ks=new Set(I.flatMap(x=>x.kid||[])).size, e=I.reduce((a,x)=>a+(+x.p||0),0), wi=I.length>1?I.reduce((b,x,i)=>(+x.p||0)<(+I[b].p||0)?i:b,0):-1, w=wi>=0?I[wi]:null;
      h+=`<div class="a2-card gold a3-cp" data-c="${E(c.id)}"><div class="a3-ch">${U.edit?`<input class="a3-in" id="a3In" maxlength="32" value="${E(c.ad)}" aria-label="KUPO adı" enterkeyhint="done" autocomplete="off"><button class="a2-ib" type="button" data-k3="rok" aria-label="Adı kaydet">${IC.ok}</button>`
          :`<h2>${E(c.ad)}</h2><button class="a2-ib" type="button" data-k3="ren" aria-label="KUPO adını değiştir">${IC.pen}</button>${stPill(c)}`}</div>
        <p class="a3-meta">At yarışı KUPO'su · ${I.length} satır · ${E(ist(new Date(c.olusturma),{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}))} açıldı</p>
        ${I.length?I.map((x,i)=>rowHtml(x,i,false)).join(""):`<p class="a2-note" style="margin:6px 2px 10px">Bu KUPO boş. Program'dan bir koşu seç ve “＋ KUPO'ya ekle”ye dokun; 6'lı için Türler sekmesi.</p>`}
        ${I.length?`<div class="a2-kpis k3" style="margin-top:10px"><div><b>${I.length}</b><small>satır<br>${ks} koşu</small></div><div><b>${fN(kAll(I))}</b><small>toplam<br>kombinasyon</small></div><div><b style="color:var(--a2-gi)">${P(pAll(I))}</b><small>OXXai birlikte<br>tutma</small></div></div>
          <p class="a2-note" style="margin:8px 2px 0">Beklenen tutan satır ${e.toLocaleString("tr-TR",{maximumFractionDigits:1})} / ${I.length}${w?` · en zayıf halka: ${E(w.hip)} ${w.kosu}. koşu (${E((TUR[w.tur]||{}).ad||"")}, ${P(w.p)})`:""}. Olasılık indirimli Harville yöntemiyle hesaplanır, koşu başlayana kadar oran geldikçe güncellenir. Para tutarı gösterilmez.</p>`:""}
        <div class="a3-acts"><a class="a2-btn g" href="#at/program" data-tab="program">＋ Koşu ekle</a><button class="a2-btn p" type="button" data-kupo="${E(c.id)}">KUPO'da aç</button></div>
        ${U.cf===c.id?`<div class="a3-cf" role="alertdialog" aria-label="KUPO'yu sil"><p><b>${E(c.ad)}</b> silinsin mi? İçindeki ${I.length} satır da silinir (KUPO'dan da); geri alınamaz.</p><div class="a2-row2"><button class="a2-btn q" type="button" data-k3="cfno">Vazgeç</button><button class="a2-btn q a3-btn-d" type="button" data-k3="cfdel">Sil</button></div></div>`
          :`<div class="a3-acts"><button class="a2-btn q" type="button" data-k3="arch"${I.length?"":" disabled"}>Eski KUPO'lara taşı</button><button class="a2-btn q" type="button" data-k3="del">KUPO'yu sil</button></div>`}</div>`;
      if(L.length>1) h+=`<p class="a2-note">${L.length} açık at KUPO'n var; yukarıdaki çiplerle geçiş yap. Seçtiğin KUPO, alt menüdeki KUPO ekranında da aktif olur.</p>`; }
    h+=statsHtml()+oldHtml();
    h+=`<p class="a2-foot">KUPO kayıtları yalnızca bu telefonda tutulur. OXXai oyun almaz, hiçbir siteye yönlendirmez ve para tutarı göstermez. Hobi amaçlı olasılıktır, garanti değildir · 18+</p>`;
    return h; }
  // ---------- boyama kancası: at2 #at2Box'u yazdıkça ----------
  let self=false;
  function route(){ try{ return A2.route(); }catch(e){ return {v:"bugun",a:[]}; } }
  function enhance(){ const rt=route(); try{
      if(rt.v==="kupon"){ if(box.querySelector(":scope > .a3-k")) return; const hd=(box.querySelector(":scope > .a2-hd")||{}).outerHTML||"";
        self=true; try{ window.atkGrade&&window.atkGrade(); }catch(e){}
        box.innerHTML=`<div class="a3-k" hidden></div>`+vKupon(hd); afterKupon(); }
      else if(rt.v==="kosu") deco("kosu",rt); else if(rt.v==="at") deco("at",rt);
    }catch(e){ console.error(e); } bar(); }
  new MutationObserver(()=>{ if(self){ self=false; return; } enhance(); }).observe(box,{childList:true});
  function repaintK(){ const y=window.scrollY; box.querySelector(":scope > .a3-k")&&box.querySelector(":scope > .a3-k").remove(); self=false; enhance(); if(Math.abs(window.scrollY-y)>2) window.scrollTo(0,y); }
  function afterKupon(){ const inp=$("a3In"); if(!inp) return; try{ inp.focus({preventScroll:true}); inp.select(); }catch(e){}
    inp.onkeydown=e=>{ if(e.key==="Enter"){ e.preventDefault(); rename(inp.value); } else if(e.key==="Escape"){ U.edit=false; repaintK(); } };
    inp.onblur=()=>setTimeout(()=>{ if(U.edit&&$("a3In")===inp) rename(inp.value); },150); }
  function rename(v){ const c=cur(); U.edit=false; v=String(v||"").replace(/\s+/g," ").trim().slice(0,32); if(c&&v&&v!==c.ad){ c.ad=v; save(c); toast("KUPO adı: "+v); } repaintK(); }
  // ---------- tıklamalar ----------
  box.addEventListener("click",e=>{ const b=e.target.closest("[data-k3]"); if(!b||!box.contains(b)) return; e.preventDefault(); e.stopPropagation(); tap();
    const a=b.dataset.k3, c=cur(), i=+b.dataset.i, x=c&&c.at?c.at[i]:null, oc=b.dataset.c?KX().L.find(z=>z.id===b.dataset.c):null;
    if(a==="sw"&&oc){ setAct(oc); U.edit=false; U.cf=null; U.tur=null; toast(`${oc.ad} aktif · KUPO'da da`); repaintK(); return; }
    if(a==="new"){ const n=newAt(); U.edit=true; U.cf=null; U.tur=null; toast(`${n.ad} açıldı · adını değiştirebilirsin`); repaintK(); return; }
    if(a==="ren"){ U.edit=true; repaintK(); return; }
    if(a==="rok"){ const inp=$("a3In"); rename(inp?inp.value:""); return; }
    if(a==="oo"){ U.od=U.od===b.dataset.c?null:b.dataset.c; U.ocf=null; repaintK(); return; }
    if(a==="odel"){ U.ocf=b.dataset.c; repaintK(); return; }
    if(a==="ocfno"){ U.ocf=null; repaintK(); return; }
    if(a==="ocfdel"&&oc){ const ad=oc.ad; U.ocf=null; U.od=null; delC(oc); toast(`${ad} silindi`); repaintK(); return; }
    if(a==="oback"&&oc){ oc.durum="acik"; delete oc.arsivAt; delete oc.bitti; setAct(oc); save(oc); U.od=null; toast(`${oc.ad} açık KUPO'lara alındı`); repaintK(); return; }
    if(!c) return;
    if(a==="rm"&&x){ c.at.splice(i,1); if(U.tur===x.id) U.tur=null; save(c); toast(`Satır çıkarıldı · ${c.at.length} satır kaldı`); try{ Sound.toggle(false); }catch(_){} repaintK(); return; }
    if(a==="tur"&&x){ U.tur=U.tur===x.id?null:x.id; repaintK(); return; }
    if(a==="tset"&&x){ if(b.dataset.er){ toast(b.dataset.er); return; } const t=b.dataset.t; if(typeof window.atkOpen!=="function"){ toast("Kurucu yüklenemedi"); return; }
      U.tur=null; setAct(c); window.atkOpen(x.kid[0],{row:Object.assign({},x,{tur:t,sec:conv(x,t)})}); return; }
    if(a==="ed"&&x){ if(typeof window.atkOpen==="function"){ setAct(c); window.atkOpen(x.kid[0],{row:x}); } return; }
    if(a==="six"&&x){ try{ AT.d=x.d; AT.sev=x.sev||AT.sev; X.render(); }catch(_){} A2.go("turler",false); return; }
    if(a==="arch"){ c.durum="arsiv"; c.arsivAt=NOW(); save(c); try{ window.kxAct(); }catch(_){} U.cf=null; toast(`${c.ad} Eski at KUPO'larına taşındı`); repaintK(); return; }
    if(a==="del"){ U.cf=c.id; repaintK(); return; }
    if(a==="cfno"){ U.cf=null; repaintK(); return; }
    if(a==="cfdel"){ const ad=c.ad; U.cf=null; delC(c); toast(`${ad} silindi`); repaintK(); return; }
  },true);
  // KUPO/kurucu değişikliği: at2 zaten imza (kupon id/upd/satır) değişince yeniden boyar; kupon dışı yollar (eski kupon) için de tazele
  let rT=null; const later=()=>{ clearTimeout(rT); rT=setTimeout(()=>{ if(!$("v-at").hidden&&route().v==="kupon"&&!U.edit) repaintK(); bar(); },80); };
  try{ const _s=window.kxSave; if(typeof _s==="function") window.kxSave=function(){ const r=_s.apply(this,arguments); later(); return r; }; }catch(e){}
  window.addEventListener("storage",e=>{ if(!e.key||/^bx-kuponlar/.test(e.key)) later(); });
  // =====================================================================
  // Yüzen "At kuponum" çubuğu
  // =====================================================================
  // body'ye eklenir: görünüm kabının dönüşümü (transform) position:fixed'i kaydırmasın; #v-at gizlenince çubuk da gizlenir
  const B=document.createElement("button"); B.id="at3Bar"; B.type="button"; B.hidden=true; document.body.appendChild(B);
  new MutationObserver(()=>bar()).observe(sec,{attributes:true,attributeFilter:["hidden"]});
  B.addEventListener("click",()=>{ tap(); A2.go("kupon",false); });
  function navH(){ const n=document.querySelector("nav.tabs"); if(!n) return 72; const r=n.getBoundingClientRect(); return r.height&&r.top<innerHeight?Math.max(0,innerHeight-r.top):0; }
  function bar(){ try{ const rt=route(), c=cur(), I=(c&&c.at)||[], show=!$("v-at").hidden&&rt.v!=="kupon"&&I.length>0;
      if(!show){ if(!B.hidden){ B.hidden=true; sec.classList.remove("a3-hasbar"); } return; }
      B.style.setProperty("--a3-nb",navH()+"px");
      const wt=I.filter(x=>x.ok==null&&!x.iade).length, html=`<span class="n" aria-hidden="true">${I.length}</span><span class="tx"><b>At KUPO'm · ${E(c.ad)}</b><small>${I.length} satır · ${fN(kAll(I))} komb. · OXXai <b>${P(pAll(I))}</b>${wt?` · ${wt} bekliyor`:""}</small></span><span class="go" aria-hidden="true">Aç ›</span>`;
      if(B.innerHTML!==html.replace(/&#39;/g,"'")) B.innerHTML=html; B.setAttribute("aria-label",`At KUPO'm ${c.ad}: ${I.length} satır, OXXai birlikte tutma olasılığı ${P(pAll(I))}. KUPO sekmesini aç`);
      if(B.hidden){ B.hidden=false; sec.classList.add("a3-hasbar"); } }catch(e){} }
  window.addEventListener("resize",bar); window.addEventListener("hashchange",()=>setTimeout(bar,30));
  setInterval(()=>{ if(!document.hidden) bar(); },20000);
  // =====================================================================
  // Aşama 4 · oran izi ve kariyer (yalnız depodaki türetilmiş dosyalar)
  // =====================================================================
  const OI={}, KR={v:undefined,t:0,p:null};
  function oiLoad(d){ const o=OI[d]; if(o&&(o.p||NOW()-o.t<5*60e3)) return; OI[d]={v:o?o.v:undefined,t:NOW(),p:X.j("data/at/oran_izi/"+d+".json").then(v=>{ OI[d]={v:v&&v.kosular?v:null,t:NOW(),p:null}; redeco(); })}; }
  function krLoad(){ if(KR.p||(KR.v!==undefined&&NOW()-KR.t<30*60e3)) return; KR.p=X.j("data/at/kariyer.json").then(v=>{ KR.v=v&&v.atlar?v:null; KR.t=NOW(); KR.p=null; redeco(); }); }
  function redeco(){ const v=route().v; if((v==="kosu"||v==="at")&&!$("v-at").hidden){ box.querySelectorAll("[data-a3d]").forEach(n=>n.remove()); enhance(); } }
  function izOf(r){ const d=dayOf(r.kosu_id), o=OI[d]; const z=o&&o.v&&o.v.kosular&&o.v.kosular[r.hipodrom+"/"+r.kosu]; return z&&Array.isArray(z.t)&&z.t.length?z:null; }
  const izLoaded=d=>!!OI[d]&&OI[d].v!==undefined;
  function series(z,no){ const v=(z.o||{})[String(no)]||[]; const pts=[]; z.t.forEach((t,i)=>{ const y=v[i]; if(y!=null&&isFinite(+y)) pts.push([t,+y]); }); return pts; }
  // mini çizgi: y ekseni ters (oran düştükçe çizgi yükselir = piyasa daha çok inanıyor); ölçek log
  function spark(pts,big){ const W=big?320:84, H=big?72:28, pad=big?6:3; if(pts.length<2) return "";
    const ys=pts.map(p=>Math.log(p[1])), lo=Math.min(...ys), hi=Math.max(...ys), span=hi-lo||1;
    const XY=pts.map((p,i)=>[pad+(W-2*pad)*i/(pts.length-1), pad+(H-2*pad)*((Math.log(p[1])-lo)/span)*(hi===lo?0:1)+(hi===lo?(H-2*pad)/2:0)]);
    const f=pts[0][1], l=pts[pts.length-1][1], col=l<f-.005?"#3BEA7E":l>f+.005?"#FF6B78":"#B6C0D3";
    const d=XY.map((q,i)=>(i?"L":"M")+q[0].toFixed(1)+" "+q[1].toFixed(1)).join(" ");
    return `<svg class="a3-sp${big?" big":""}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="Piyasa oranı ${pts.map(p=>p[0]+" "+fx(p[1])).join(", ")}"><path d="${d}" fill="none" stroke="${col}" stroke-width="${big?2.2:1.8}" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>${XY.map((q,i)=>i===XY.length-1||big?`<circle cx="${q[0].toFixed(1)}" cy="${q[1].toFixed(1)}" r="${big?(i===XY.length-1?3.2:2.2):2.4}" fill="${i===XY.length-1?col:"#8893AB"}"/>`:"").join("")}</svg>`; }
  function chg(pts){ if(!pts.length) return `<span class="a3-ov">–</span>`; const f=pts[0][1], l=pts[pts.length-1][1];
    if(pts.length<2) return `<span class="a3-ov"><b>${fx(l)}</b>tek ölçüm</span>`;
    const dn=l<f-.005, up=l>f+.005; return `<span class="a3-ov"><b class="${dn?"up":up?"dn":""}">${fx(l)} ${dn?"▼":up?"▲":"="}</b>ilk ${fx(f)}</span>`; }
  const noIz=(r,z)=>`<p class="a2-note" style="margin:0">${z&&z.t.length===1?`Henüz iz yok: bu koşu için tek ölçüm var (${E(z.t[0])}). Oran değiştikçe yeni nokta eklenir ve çizgi oluşur.`:`Henüz iz yok. Laboratuvar gün içinde yaklaşık 30 dakikada bir koşu öncesi piyasa oranlarını kaydeder; yalnız oran değişince nokta eklenir.`}</p>`;
  function cardOran(r){ const d=dayOf(r.kosu_id); if(!izLoaded(d)) return `<div class="a2-card" data-a3d><div class="a2-ch"><h2>📈 Gün içi piyasa oranı</h2></div><div class="a2-sk" style="height:56px;margin:0"></div></div>`;
    const z=izOf(r); let h=`<div class="a2-card" data-a3d="oran"><div class="a2-ch"><h2>📈 Gün içi piyasa oranı</h2><small>${z?`${z.t.length} ölçüm · ${E(z.t[0])}${z.t.length>1?"–"+E(z.t[z.t.length-1]):""}`:""}</small></div>`;
    if(!z||z.t.length<2) return h+noIz(r,z)+`</div>`;
    const A=(r.atlar||[]).map(a=>({no:String(a.no),ad:a.ad,pts:series(z,a.no)})).filter(a=>a.pts.length).sort((a,b)=>a.pts[a.pts.length-1][1]-b.pts[b.pts.length-1][1]);
    const row=a=>`<a class="a3-oir" href="#at/at/${K(r.kosu_id)}/${enc(a.no)}"><span class="a2-no">${E(a.no)}</span><span class="a2-hn"><b>${E(a.ad)}</b></span>${spark(a.pts)||'<span class="a3-sp"></span>'}${chg(a.pts)}</a>`;
    h+=`<div class="a3-oi">${A.slice(0,6).map(row).join("")}${A.length>6?`<details><summary>Diğer ${A.length-6} at</summary>${A.slice(6).map(row).join("")}</details>`:""}</div>
      <p class="a2-note" style="margin:8px 2px 0">Sıra: en son piyasa oranı (düşük = favori). Çizgi yukarı = oran düştü, piyasa daha çok inanıyor (▼ yeşil); aşağı = oran yükseldi (▲ kırmızı). Yalnız koşu öncesi ölçümler; ara değer üretilmez.</p></div>`;
    return h; }
  function cardOranAt(r,no){ const d=dayOf(r.kosu_id); if(!izLoaded(d)) return `<div class="a2-card" data-a3d><div class="a2-ch"><h2>📈 Piyasa oranı · gün içi</h2></div><div class="a2-sk" style="height:72px;margin:0"></div></div>`;
    const z=izOf(r), pts=z?series(z,no):[]; let h=`<div class="a2-card" data-a3d="oran"><div class="a2-ch"><h2>📈 Piyasa oranı · gün içi</h2><small>${pts.length?pts.length+" ölçüm":""}</small></div>`;
    if(pts.length<2) return h+(pts.length===1?`<p class="a2-note" style="margin:0">Henüz iz yok: tek ölçüm ${E(pts[0][0])} · oran ${fx(pts[0][1])}. Oran değiştikçe çizgi oluşur.</p>`:noIz(r,z))+`</div>`;
    const f=pts[0][1], l=pts[pts.length-1][1], dn=l<f-.005, up=l>f+.005;
    return h+`${spark(pts,true)}<div class="a3-pts">${pts.map(p=>`<span>${E(p[0])} <b>${fx(p[1])}</b></span>`).join("")}</div>
      <p class="a2-note" style="margin:8px 2px 0">${E(pts[0][0])}'den beri ${fx(f)} → <b class="${dn?"up":up?"dn":""}">${fx(l)} ${dn?"▼ oran düştü (piyasa güçleniyor)":up?"▲ oran yükseldi (piyasa soğuyor)":"değişmedi"}</b>. Koşu öncesi ölçümler; garanti değildir.</p></div>`; }
  function cardKariyer(r,h){ if(KR.v===undefined) return `<div class="a2-card" data-a3d><div class="a2-ch"><h2>🗂️ Kariyer</h2></div><div class="a2-sk" style="height:96px;margin:0"></div></div>`;
    const z=KR.v&&KR.v.atlar&&KR.v.atlar[h.ad]; let o=`<div class="a2-card" data-a3d="kariyer"><div class="a2-ch"><h2>🗂️ Kariyer</h2><small>${z&&z.n?`${E(String(z.ilk||"").slice(0,4))}–${E(String(z.sonT||"").slice(0,4))}`:""}</small></div>`;
    if(!z) return o+`<p class="a2-note" style="margin:0">Kariyer özeti henüz yok. Laboratuvar her gece yalnız o günün koşucuları için açık sonuç arşivinden kompakt bir özet üretir.</p></div>`;
    if(!z.n) return o+`<p class="a2-note" style="margin:0">Açık arşivde bu atın bu günden önce koşusu yok (ilk koşusu olabilir).</p></div>`;
    const d=z.d||[0,0,0], i3=d[0]+d[1]+d[2], pist=r.pist, mg=(()=>{ const m=+r.mesafe||0; return m<=1400?"1000–1400":m<=1700?"1500–1700":m<=2100?"1800–2100":"2200+"; })();
    const dist=(obj,cur,lbl)=>{ const E2=Object.entries(obj||{}).sort((a,b)=>b[1][0]-a[1][0]); if(!E2.length) return ""; const mx=Math.max(...E2.map(e=>e[1][0]),1);
      return `<div class="a3-sub">${lbl}</div><div class="a3-dist">${E2.map(([k,v])=>`<div class="a3-dr${k===cur?" on":""}"><span class="l">${E(k)}${k===cur?"<em>bugün</em>":""}</span><span class="tr" role="img" aria-label="${E(k)}: ${v[0]} koşu, ${v[1]} birincilik, ${v[2]!=null?v[2]+" kez ilk 3":""}"><i style="width:${v[0]/mx*100}%"></i><u style="width:${(v[2]!=null?v[2]:v[1])/mx*100}%"></u></span><span class="v">${v[0]} koşu${v[1]?` · ${v[1]} birinci`:""}</span></div>`).join("")}</div>`; };
    const son=(z.son||[]).map(s=>`<i class="${s===1?"f1":s===2||s===3?"f2":""}">${s?E(s):"–"}</i>`).join("");
    o+=`<div class="a2-kpis"><div><b>${fN(z.n)}</b><small>koşu</small></div><div><b style="color:var(--a2-gi)">${d[0]}</b><small>1.</small></div><div><b>${d[1]}</b><small>2.</small></div><div><b>${d[2]}</b><small>3.</small></div></div>
      <p class="a2-note" style="margin:8px 2px 0">Kazanma ${P(d[0]/z.n)} · ilk 3 ${P(i3/z.n)}${z.jk&&h.jokey?` · bugünkü jokeyi ${E(h.jokey)} ile ${z.jk[0]} koşu${z.jk[0]?`, ${z.jk[1]} birincilik`:""}`:""}.</p>
      ${son?`<div class="a3-sub">Son ${z.son.length} derece <span style="text-transform:none;letter-spacing:0;font-weight:500">(en yeni solda)</span></div><span class="a2-fm" role="img" aria-label="Son dereceler: ${E(z.son.join(", "))}">${son}</span>`:""}
      ${dist(z.pist,pist,"Pist")}${dist(z.mes,mg,"Mesafe")}${dist(Object.fromEntries(Object.entries(z.hip||{}).map(([k,v])=>[k,[v[0],v[1],null]])),r.hipodrom,"Hipodrom")}
      <p class="a2-note" style="margin:10px 2px 0">Gri çubuk koşu sayısı, altın çubuk ilk 3'e girdiği koşular (hipodromda birincilik). Yalnız bu günden önceki sonuçlar; kaynak açık yarış sonuç arşivi (türetilmiş özet).</p></div>`;
    return o; }
  function deco(kind,rt){ if(box.querySelector("[data-a3d]")) return; const r=raceById(unK(rt.a[0]||"")); if(!r) return; const d=dayOf(r.kosu_id); oiLoad(d);
    if(kind==="kosu"){ const main=box.querySelector(".a2-sade")||(box.querySelector(".a2-sortb")||{closest:()=>null}).closest(".a2-card"); if(!main) return;
      main.insertAdjacentHTML("afterend",cardOran(r));
      const z=izOf(r), miss=box.querySelector(".a2-miss"); if(miss&&z&&z.t.length>1) miss.innerHTML=miss.innerHTML.replace(" ve gün içi oran hareketi"," (gün içi oran hareketi yukarıda)"); return; }
    krLoad(); const h=(r.atlar||[]).find(y=>String(y.no)===String(rt.a[1])); if(!h) return;
    const cards=[...box.querySelectorAll(":scope > .a2-card")], kpi=cards.find(c=>c.querySelector(".a2-kpis")), form=cards.find(c=>/^Form/.test((c.querySelector("h2")||{}).textContent||""));
    if(kpi) kpi.insertAdjacentHTML("afterend",cardOranAt(r,h.no)); if(form) form.insertAdjacentHTML("afterend",cardKariyer(r,h));
    const miss=box.querySelector(":scope > .a2-miss"); if(miss&&KR.v&&KR.v.atlar&&KR.v.atlar[h.ad]) miss.innerHTML=`<b>Henüz veri yok:</b> pedigri, sahip ve idman/galop verisi açık kaynakta yok; uydurulmaz.`; }
  // ilk durum
  window.BX_AT3={enhance,bar,conv,cur,stats:statsHtml};
  enhance();
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: at3-v109 */
