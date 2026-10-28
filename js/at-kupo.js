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
/* id: atkupon-v98 */ try {
// =====================================================================
// v98 · AT KUPONU — KUPO'da tek sporlu at yarışı kuponları
// • Veri: "bx-kuponlar" içindeki kupon {id,ad,spor:"at",items:[],at:[satır],olusturma,durum,upd}. spor alanı olmayan kupon futboldur
//   (eski kuponlar hiç değişmez). At satırları items'a değil "at" dizisine yazılır → futbol puanlama/süzme/istatistik onlara dokunmaz.
//   Satır: {id,tur,d,kid:[koşu id],hip,kosu,saat,t,sec:[[at no]…],ad:{no:ad},komb,p,pk:"oran"|"sabah",gd:[γ,δ],sev?,alt?,ok?,need?,man?,res?}
// • Tek spor kuralı: futbol eklemesi aktif kupon at kuponuyken son açık futbol kuponuna (yoksa yeni "Kupon N") yönlenir; at satırı da
//   son at kuponuna (yoksa yeni "At Kuponu N"). Aynı koşu bir kuponda tek satırda bulunur (yeni satır eskisinin yerini alır).
// • Olasılık: indirimli Harville P(i,j,k,l)=p_i·p_j^γ/Σp^γ·p_k^δ/Σp^δ·p_l^δ/Σp^δ; γ,δ data/at/kupon_karne.json'dan (yoksa 1).
//   p: oran açıldıysa canlı p_oran (γ_oran,δ_oran), yoksa sabah p_kazanma. Ekürili atlar Ganyan/Plase/Çifte'de tek birim.
// • Sonuç: AT.load'un çektiği data/at/canli/<gün>.json (sonuc.sira); yüklenmemiş günler için gün başına tek j() çağrısı.
// =====================================================================
(function(){
  if(!window.KX||!window.BX_AT) return;
  const KX=window.KX, A=()=>window.BX_AT, NOW=()=>Date.now();
  const uid=()=>Date.now().toString(36)+Math.random().toString(36).slice(2,6);
  const LSAT="bx-kupon-at-son", LSTUR="bx-atk-tur";
  const lsG=(k,d)=>{ try{ const v=localStorage.getItem(k); return v==null?d:v; }catch(e){ return d; } };
  const lsS=(k,v)=>{ try{ localStorage.setItem(k,v); }catch(e){} };
  const lion=c=>{ try{ return window.kxLion(c); }catch(e){ return ""; } };
  const sfx=(s,abl)=>{ try{ return window.kxSfx(s,abl); }catch(e){ return s; } };
  const fP=p=>{ if(p==null||!isFinite(p)) return "–"; const x=p*100; if(x>0&&x<.01) return "<%0,01"; const d=x>=10?0:x>=1?1:2; return "%"+x.toLocaleString("tr-TR",{maximumFractionDigits:d}); };
  const fN=n=>(+n||0).toLocaleString("tr-TR");
  const f1=x=>(+x||0).toLocaleString("tr-TR",{maximumFractionDigits:1});
  const HORSE=`<span class="atk-ic" aria-hidden="true"><svg viewBox="0 0 64 64"><path d="M41 52 C43.5 45 45 38 43.5 31 C42 24 37.5 18.5 32 16.5 L30.5 10.5 L27.6 16 C22.8 17.2 18.6 21 16 26.5 L12.2 33.4 C11.2 35.6 12.4 38.2 14.8 38.2 L19.6 37 C22.2 38.6 23.8 41.5 23.8 45.2 L23.4 52 Z" fill="#E9C766"/><circle cx="25.6" cy="24.6" r="2" fill="#0B1222"/></svg></span>`;
  // ---------- tahmin türleri (kurallar kupon_karne.json'dan güncellenir) ----------
  const TUR={
    ganyan:{ad:"Kazanan",kisa:"koşunun birincisi",kol:1,tek:1,ek:1,enaz:2,lbl:["Seç"],ip:"Kazanacak atı seç"},
    plase:{ad:"Derece",kisa:"at ilk 2'ye girer",kol:1,tek:1,ek:1,enaz:7,lbl:["Seç"],ip:"İlk ikiye girecek atı seç"},
    ikili:{ad:"İkili",kisa:"ilk iki, sırasız",kol:1,min:2,enaz:7,lbl:["Seç"],ip:"İlk ikiye girecek atları seç (en az 2); her ikili ayrı kombinasyon"},
    sirali_ikili:{ad:"Sıralı İkili",kisa:"ilk iki, sıralı",kol:2,enaz:4,lbl:["1.","2."],ip:"Her sıra için at seç; birden çok at seçersen kombinasyon çoğalır"},
    cifte:{ad:"Çifte",kisa:"bu koşu + sonraki koşu birincileri",kol:2,ek:1,iki:1,enaz:2,lbl:["Seç","Seç"],ip:"İki koşunun da kazananını seç"},
    uclu:{ad:"Sıralı Üçlü",kisa:"ilk üç, sıralı",kol:3,enaz:4,lbl:["1.","2.","3."],ip:"Birinci, ikinci ve üçüncüyü sırasıyla seç"},
    tabela:{ad:"Tabela",kisa:"ilk dört, sıralı",kol:4,enaz:5,lbl:["1.","2.","3.","4."],ip:"İlk dört dereceyi sırasıyla seç"},
    altili:{ad:"6'lı Tahmin",kisa:"art arda 6 koşunun birincileri",kol:6}};
  const ORDER=["ganyan","plase","ikili","sirali_ikili","cifte","uclu","tabela","altili"];
  // ---------- geri test karnesi (paralel laboratuvar dosyası; yoksa zarifçe gizlenir) ----------
  let KAR, karP=null;
  function karne(){ if(KAR!==undefined) return Promise.resolve(KAR);
    if(!karP) karP=A().j("data/at/kupon_karne.json").then(k=>{ KAR=k&&k.turler?k:null;
      if(KAR) for(const t of ORDER){ const z=KAR.turler[t]; if(z&&TUR[t]){ if(z.ad) TUR[t].ad=z.ad; if(z.kisa) TUR[t].kisa=z.kisa; if(z.en_az_at) TUR[t].enaz=+z.en_az_at; } }
      return KAR; }).catch(()=>{ KAR=null; return null; });
    return karP; }
  window.ATK_KARNE=()=>KAR;
  function gd(oranli){ const H=KAR&&KAR.harville||{}; const g=oranli?(H.gamma_oran??H.gamma):H.gamma, d=oranli?(H.delta_oran??H.delta):H.delta;
    return [isFinite(+g)&&+g>0?+g:1, isFinite(+d)&&+d>0?+d:1]; }
  const rate=o=>!o||!o.n?null:(o.isabet_orani!=null?+o.isabet_orani:(+o.isabet||0)/o.n);
  const erate=o=>!o||!o.n?null:(o.beklenen_oran!=null?+o.beklenen_oran:(+o.beklenen||0)/o.n);
  function karLine(tur,komb){ const z=KAR&&KAR.turler&&KAR.turler[tur]; if(!z||!z.n) return "";
    const S=(z.seviyeler||[]).filter(s=>s.n); let s=S.filter(x=>+x.kombinasyon<=komb).sort((a,b)=>b.kombinasyon-a.kombinasyon)[0]||S[0]||z;
    const K=+s.kombinasyon||1, ad=TUR[tur].ad;
    const what=tur==="altili"?`${s.seviye?({dar:"Dar",orta:"Orta",genis:"Geniş"}[s.seviye]||s.seviye)+" ":""}6'lı (${fN(K)} kombinasyon)`:K===1?`en olası tek ${ad.toLocaleLowerCase("tr")} kombinasyonu`:`en olası ${fN(K)} ${ad.toLocaleLowerCase("tr")} kombinasyonu`;
    const r=rate(s), e=erate(s), si=s.sinama&&s.sinama.n?s.sinama:null;
    let t=tur==="altili"?`Geçmiş ${fN(s.n)} altılıda ${what} <b>${fN(s.isabet)}</b> kez tuttu; model ${f1(s.beklenen)} bekliyordu`
      :`Geçmiş ${fN(s.n)} koşuda ${what} <b>${fP(r)}</b> tuttu; model ${fP(e)} bekliyordu`;
    if(si) t+=tur==="altili"?` · son 1/3 sınama: ${fN(si.n)} altılıda ${fN(si.isabet)}`:` · son 1/3 sınama diliminde ${fP(rate(si))} (model ${fP(erate(si))})`;
    return t+"."; }
  // ---------- veri erişimi ----------
  const dayOf=kid=>String(kid||"").split("/")[0];
  const CAN={};   // kuponda olup AT'nin yüklemediği günler: {gün:{v,t}}
  function canliDay(d){ const C=((A().AT.canli)||{})[d], M=CAN[d]&&CAN[d].v; if(C&&M) return String(C.guncelleme_tsi||"")>=String(M.guncelleme_tsi||"")?C:M; return C||M||null; }
  function raceOf(kid){ const D=A().AT.data[dayOf(kid)]; return D&&(D.kosular||[]).find(r=>r.kosu_id===kid)||null; }
  function cOf(kid){ const C=canliDay(dayOf(kid)); if(!C) return null; const k=String(kid).split("/"); return (C.kosular||[]).find(x=>x.kosu_id===kid||(x.hipodrom===k[1]&&String(x.kosu)===k[2]))||null; }
  function nextRace(r){ const D=A().AT.data[dayOf(r.kosu_id)]; return D&&(D.kosular||[]).find(x=>x.hipodrom===r.hipodrom&&x.kosu===r.kosu+1)||null; }
  const tsOf=(d,saat)=>Date.parse(d+"T"+(saat||"23:59")+":00+03:00");
  const startTs=r=>tsOf(dayOf(r.kosu_id),r.saat);
  function started(r){ const c=cOf(r.kosu_id); if(c&&(c.sonuc||c.durum==="bitti")) return true; const t=startTs(r); return isFinite(t)&&t<=NOW(); }
  function altOf(r){ const Al=(A().AT.alt||{})[dayOf(r.kosu_id)]; return ((Al&&Al.altililar)||[]).filter(X=>X.hipodrom===r.hipodrom&&(X.kosular||[]).includes(r.kosu)); }
  function altById(d,id){ const Al=(A().AT.alt||{})[d]; return ((Al&&Al.altililar)||[]).find(X=>X.id===id)||null; }
  // ekürili gruplar: canlı dosyada koşu düzeyi "ekuri" (koşu öncesi, programdan) + sonuc.ekuri + 6'lı ayakları
  function ekK(kid){ const G=[], seen=new Set(), c=cOf(kid), r=raceOf(kid);
    const put=g=>{ if(!Array.isArray(g)) return; const m=g.map(String).sort(); const k=m.join(","); if(m.length>1&&!seen.has(k)){ seen.add(k); G.push(m); } };
    for(const g of (c&&Array.isArray(c.ekuri)?c.ekuri:[])) put(g);
    for(const g of (c&&c.sonuc&&Array.isArray(c.sonuc.ekuri)?c.sonuc.ekuri:[])) put(g);
    if(r) for(const X of altOf(r)) for(const L of Object.values(X.seviyeler||{})) for(const a of L.ayaklar||[]) if(a.kosu===r.kosu) for(const g of a.ekuri||[]) put(g);
    return G; }
  const ekuriOf=r=>ekK(r.kosu_id);
  function field(r){ const c=cOf(r.kosu_id), by={}; if(c) for(const h of c.atlar||[]) by[String(h.no)]=h;
    const oranli=!!(c&&(c.atlar||[]).some(h=>h.p_oran!=null));
    const H=(r.atlar||[]).map(h=>{ const x=by[String(h.no)]||{}; const p=oranli?(x.p_oran!=null?+x.p_oran:0):(+h.p_kazanma||0);
      return {no:String(h.no),ad:h.ad,jokey:x.jokey||h.jokey||"",p,ps:+h.p_kazanma||0,oran:x.oran||null,off:oranli&&x.p_oran==null}; });
    const s=H.reduce((a,h)=>a+h.p,0)||1; H.forEach(h=>h.p/=s); H.sort((a,b)=>b.p-a.p||(+a.no- +b.no));
    const C=canliDay(dayOf(r.kosu_id));
    return {r,c,H,oranli,ek:ekuriOf(r),up:oranli&&C&&C.guncelleme_tsi?String(C.guncelleme_tsi).slice(11,16):""}; }
  function unitsOf(F){ const used=new Set(), U=[]; for(const g of F.ek||[]){ const m=g.filter(no=>F.H.some(h=>h.no===no)); if(m.length>1){ U.push(m); m.forEach(x=>used.add(x)); } }
    for(const h of F.H) if(!used.has(h.no)) U.push([h.no]); return U; }
  const unitOf=(F,no)=>unitsOf(F).find(u=>u.includes(no))||[no];
  const nUnits=(F,S)=>unitsOf(F).filter(u=>u.some(no=>S.includes(no))).length;
  // ---------- indirimli Harville ----------
  function HV(ps,g,d){ const n=ps.length, p=ps.map(x=>Math.max(1e-9,+x||0)), sp=p.reduce((a,b)=>a+b,0); for(let i=0;i<n;i++) p[i]/=sp;
    const pg=p.map(x=>Math.pow(x,g)), pd=p.map(x=>Math.pow(x,d)), Sg=pg.reduce((a,b)=>a+b,0), Sd=pd.reduce((a,b)=>a+b,0);
    const P12=(i,j)=>i===j?0:p[i]*pg[j]/(Sg-pg[i]);
    const P123=(i,j,k)=>(k===i||k===j||i===j)?0:P12(i,j)*pd[k]/(Sd-pd[i]-pd[j]);
    const P1234=(i,j,k,l)=>(l===i||l===j||l===k)?0:P123(i,j,k)*pd[l]/(Sd-pd[i]-pd[j]-pd[k]);
    return {n,p,P12,P123,P1234}; }
  // tek koşuluk türler: sec = [[no…]…] → {komb,p}
  function calcF(tur,sec,F,F2){ const [g,d]=gd(F.oranli), V=HV(F.H.map(h=>h.p),g,d), ix=no=>F.H.findIndex(h=>h.no===String(no));
    const S=(sec||[]).map(c=>[...new Set((c||[]).map(ix).filter(i=>i>=0))]); const s0=S[0]||[];
    let p=0,k=0;
    if(tur==="ganyan"){ for(const i of s0) p+=V.p[i]; k=nUnits(F,(sec[0]||[]).map(String)); }
    else if(tur==="plase"){ const set=new Set(s0); for(const i of set) p+=V.p[i]; for(let i=0;i<V.n;i++) if(!set.has(i)) for(const j of set) p+=V.P12(i,j); k=nUnits(F,(sec[0]||[]).map(String)); }
    else if(tur==="ikili"){ for(let a=0;a<s0.length;a++) for(let b=a+1;b<s0.length;b++){ p+=V.P12(s0[a],s0[b])+V.P12(s0[b],s0[a]); k++; } }
    else if(tur==="sirali_ikili"){ for(const i of s0) for(const j of S[1]||[]) if(i!==j){ p+=V.P12(i,j); k++; } }
    else if(tur==="uclu"){ for(const i of s0) for(const j of S[1]||[]) if(j!==i) for(const l of S[2]||[]) if(l!==i&&l!==j){ p+=V.P123(i,j,l); k++; } }
    else if(tur==="tabela"){ for(const i of s0) for(const j of S[1]||[]) if(j!==i) for(const l of S[2]||[]) if(l!==i&&l!==j) for(const m of S[3]||[]) if(m!==i&&m!==j&&m!==l){ p+=V.P1234(i,j,l,m); k++; } }
    else if(tur==="cifte"&&F2){ const ix2=no=>F2.H.findIndex(h=>h.no===String(no)); let a=0,b=0; for(const i of s0) a+=V.p[i];
      for(const i of new Set((sec[1]||[]).map(ix2).filter(i=>i>=0))) b+=F2.H[i].p; p=a*b; k=nUnits(F,(sec[0]||[]).map(String))*nUnits(F2,(sec[1]||[]).map(String)); }
    return {komb:k,p:Math.min(1,p),gd:[g,d]}; }
  // OXXai önerisi: o koşu için en olası tek kombinasyon
  function suggest(tur,F,F2){ const [g,d]=gd(F.oranli), V=HV(F.H.map(h=>h.p),g,d), ok=F.H.map((h,i)=>h.off?-1:i).filter(i=>i>=0), no=i=>F.H[i].no, top=ok.slice(0,8);
    let best=null; const take=(p,sec)=>{ if(!best||p>best.p) best={p,sec}; };
    if(tur==="ganyan"||tur==="plase"||tur==="cifte"){ const bu=(G,isP)=>{ let b=null; for(const u of unitsOf(G)){ if(u.every(x=>(G.H.find(h=>h.no===x)||{}).off)) continue; const c=calcF(isP?"plase":"ganyan",[u],G); if(!b||c.p>b.p) b={p:c.p,u}; } return b; };
      const a=bu(F,tur==="plase"); if(!a) return null; if(tur!=="cifte") return {p:a.p,sec:[a.u]};
      if(!F2) return null; const b=bu(F2,false); if(!b) return null; return {p:a.p*b.p,sec:[a.u,b.u]}; }
    if(tur==="ikili"){ for(const i of ok) for(const j of ok) if(i<j) take(V.P12(i,j)+V.P12(j,i),[[no(i),no(j)]]); }
    if(tur==="sirali_ikili"){ for(const i of ok) for(const j of ok) if(i!==j) take(V.P12(i,j),[[no(i)],[no(j)]]); }
    if(tur==="uclu"){ for(const i of top) for(const j of top) for(const l of top) take(V.P123(i,j,l),[[no(i)],[no(j)],[no(l)]]); }
    if(tur==="tabela"){ for(const i of top) for(const j of top) for(const l of top) for(const m of top) take(V.P1234(i,j,l,m),[[no(i)],[no(j)],[no(l)],[no(m)]]); }
    return best; }
  window.ATK_TEST={HV,calcF,suggest,unitsOf,gd,setKarne:k=>{ KAR=k; }};
  function elig(tur,r,F){ if(!r) return "Koşu bulunamadı"; if(started(r)) return "Koşu başladı";
    const n=F.H.filter(h=>!h.off).length, T=TUR[tur];
    if(tur==="altili"){ const L=altOf(r).filter(X=>X.kosular[0]===r.kosu||X.kosular.includes(r.kosu)); if(!L.length) return "Bu koşu bir 6'lının ayağı değil"; return ""; }
    if(tur==="cifte"){ const r2=nextRace(r); if(!r2) return "Sonraki koşu yok"; if(started(r2)) return "Sonraki koşu başladı"; }
    if(n<T.enaz) return `${n} atlı koşuda ${T.ad} yok (en az ${T.enaz} at)`;
    return ""; }
  // ---------- kupon deposu ----------
  const isAt=c=>!!c&&c.spor==="at";
  const openAts=()=>KX.L.filter(c=>isAt(c)&&c.durum==="acik").sort((a,b)=>a.olusturma-b.olusturma);
  function nextAtNo(){ let mx=0; for(const c of KX.L){ const m=/^At (?:Kuponu|KUPO'su) (\d+)$/.exec(c.ad||""); if(m) mx=Math.max(mx,+m[1]); } return mx+1; }
  function newAt(){ const c={id:uid(),ad:"At KUPO'su "+nextAtNo(),spor:"at",items:[],at:[],olusturma:NOW(),upd:NOW(),durum:"acik"}; KX.L.push(c); return c; }
  function save(c){ if(c) c.upd=NOW(); try{ window.kxSave(); }catch(e){} }
  function act(){ try{ return window.kxAct(); }catch(e){ return null; } }
  function atAct(create){ const c=act(); if(isAt(c)) return c; const id=lsG(LSAT,"");
    let a=KX.L.find(x=>x.id===id&&isAt(x)&&x.durum==="acik")||openAts().sort((x,y)=>(y.upd||y.olusturma)-(x.upd||x.olusturma))[0]||null;
    if(!a&&create){ a=newAt(); save(a); } return a; }
  function setActive(c){ if(!c) return; KX.aktif=c.id; if(isAt(c)) lsS(LSAT,c.id); save(); try{ paintCoupon(); }catch(e){} hdrFix(); }
  function futAct(){ const c=act(); if(!isAt(c)) return c;
    let f=KX.L.filter(x=>x.durum==="acik"&&!isAt(x)).sort((a,b)=>(b.upd||b.olusturma)-(a.upd||a.olusturma))[0];
    if(!f){ let mx=0; for(const x of KX.L){ const m=/^(?:Kupon(?:um)?|KUPO) (\d+)$/.exec(x.ad||""); if(m) mx=Math.max(mx,+m[1]); } f={id:uid(),ad:"KUPO "+(mx+1),items:[],olusturma:NOW(),upd:NOW(),durum:"acik"}; KX.L.push(f); }
    KX.aktif=f.id; save(); return f; }
  // futbol ekleme yolları aktif at kuponuna yazmasın (tek spor): önce futbol kuponuna geç
  const FUT_SEL='[data-kxr] .kx-add,.ib-od span[data-mk],#msheet .mo,#msheet .rb-add,[data-ba="add"],[data-ba="all"],[data-ba="ladd"],.pw-add,.ob[data-mk]';
  ["pointerdown","click"].forEach(t=>window.addEventListener(t,e=>{ try{ if(e.target.closest&&e.target.closest(FUT_SEL)&&isAt(act())){ const f=futAct(); if(t==="click") toast(`${f.ad} aktif · at KUPO'ları futbolla karışmaz`); } }catch(_){} },true));
  // v122: futbolun cpToggle'ı artık sarmalanmıyor; futbol tarafı her eklemeden önce "oxx:cp-oncesi" olayı yayar (ui-v122)
  document.addEventListener("oxx:cp-oncesi",()=>{ try{ if(isAt(act())) futAct(); }catch(e){} });
  function delCoupon(c){ try{ const k="bx-kuponlar-sil"; const L=JSON.parse(localStorage.getItem(k)||"[]"); if(!L.includes(c.id)) L.push(c.id); localStorage.setItem(k,JSON.stringify(L.slice(-500))); }catch(e){}
    KX.L=KX.L.filter(z=>z.id!==c.id); if(KX.aktif===c.id) KX.aktif=null; act(); save(); }
  // ---------- satır ----------
  function rowRaces(x){ return x.kid.map(raceOf); }
  function addRow(row,c){ c=c||atAct(true); const R0=raceOf(row.kid[0]); if(R0&&started(R0)){ toast("Bu koşu başladı; KUPO'ya eklenemez"); return false; }
    const ov=c.at.filter(x=>x.id!==row.id&&x.kid.some(k=>row.kid.includes(k)));
    const wasEdit=c.at.some(x=>x.id===row.id);
    c.at=c.at.filter(x=>x.id!==row.id&&!ov.includes(x)); c.at.push(row); c.at.sort((a,b)=>(a.t||0)-(b.t||0)||String(a.hip||"").localeCompare(String(b.hip||""),"tr")||(a.kosu||0)-(b.kosu||0));
    setActive(c); save(c); try{ Sound.olay?Sound.olay("kupoEkle"):Sound.toggle(true); buzz(10); }catch(e){}
    toast(wasEdit?`Satır güncellendi · ${TUR[row.tur].ad}`:ov.length?`Aynı koşudan tek satır: ${TUR[row.tur].ad} olarak güncellendi · ${c.at.length} satır`:`${sfx(c.ad)} eklendi · ${TUR[row.tur].ad} · ${c.at.length} satır`);
    refresh(); return true; }
  function mkRow(tur,r,sec,F,F2,extra){ const ad={}; for(const h of F.H) ad[h.no]=h.ad; if(F2) for(const h of F2.H) ad["2:"+h.no]=h.ad;
    const R=calcF(tur,sec,F,F2), kid=tur==="cifte"?[r.kosu_id,F2.r.kosu_id]:[r.kosu_id];
    return Object.assign({id:uid(),tur,d:dayOf(r.kosu_id),kid,hip:r.hipodrom,kosu:r.kosu,saat:r.saat||"",t:startTs(r),sec:sec.map(c=>c.map(String)),ad,komb:R.komb,p:R.p,pk:F.oranli?"oran":"sabah",gd:R.gd,at0:NOW()},extra||{}); }
  function altRow(d,X,sv){ const L=X.seviyeler&&X.seviyeler[sv]; if(!L) return null; const ad={};
    L.ayaklar.forEach((g,i)=>(g.atlar||[]).forEach(h=>{ ad[(i?(i+1)+":":"")+h[0]]=h[1]; }));
    return {id:uid(),tur:"altili",d,kid:L.ayaklar.map(g=>`${d}/${X.hipodrom}/${g.kosu}`),hip:X.hipodrom,kosu:X.baslangic_kosu,saat:X.saat||"",t:tsOf(d,X.saat),
      sec:L.ayaklar.map(g=>g.secim.map(String)),ad,komb:L.kombinasyon,p:L.p,pk:X.kaynak==="oran"?"oran":"sabah",sev:sv,alt:X.id,altNo:X.no,at0:NOW()}; }
  const nmOf=(x,leg,no)=>x.ad&&(x.ad[(leg?(leg+1)+":":"")+no]||(x.tur!=="cifte"&&x.tur!=="altili"&&x.ad[no]))||"";
  function legLbl(x,i){ if(x.tur==="cifte") return i?`${x.kosu+1}. k.`:`${x.kosu}. k.`; if(x.tur==="altili") return `${i+1}.`; if(TUR[x.tur].kol===1) return ""; return `${i+1}.`; }
  // canlı yeniden hesap (koşu başlamadıysa güncel oranla)
  function recalc(x){ try{ if(x.ok!=null) return false; const r=raceOf(x.kid[0]); if(!r||started(r)) return false;
      if(x.tur==="altili"){ const X=altById(x.d,x.alt), L=X&&X.seviyeler&&X.seviyeler[x.sev]; if(L&&Math.abs(L.p-x.p)>1e-6){ x.p=L.p; x.pk=X.kaynak==="oran"?"oran":"sabah"; return true; } return false; }
      const F=field(r), F2=x.tur==="cifte"?(()=>{ const r2=raceOf(x.kid[1]); return r2?field(r2):null; })():null; if(x.tur==="cifte"&&!F2) return false;
      // koşmayacak at (oran açıldı, bu atın oranı yok): seçimden düşülür, kombinasyon ve olasılık yeniden hesaplanır (seçim silinmez; oran gelirse geri sayılır)
      const off=(G,no)=>{ const h=G&&G.H.find(z=>z.no===String(no)); return !!(h&&h.off); }, G_=i=>x.tur==="cifte"&&i===1?F2:F;
      const es=x.sec.map((c,i)=>c.filter(no=>!off(G_(i),no))), kx=[...new Set(x.sec.flatMap((c,i)=>c.filter(no=>off(G_(i),no)).map(no=>(x.tur==="cifte"&&i?"2:":"")+no)))];
      const R=calcF(x.tur,es,F,F2), pk=F.oranli?"oran":"sabah", kxs=kx.join(",");
      if(Math.abs(R.p-x.p)>1e-6||pk!==x.pk||R.komb!==x.komb||kxs!==(x.kx||[]).join(",")){ x.p=R.p; x.pk=pk; x.gd=R.gd; x.komb=R.komb; if(kx.length) x.kx=kx; else delete x.kx; return true; } }catch(e){} return false; }
  // ---------- sonuç ----------
  // her derece (1..k) için geçerli atlar: eşit dereceli (dead heat) atların hepsi kapladıkları her sıra için geçerli sayılır.
  // O[p]: o sıra açık (sonuç eksik ya da listenin sonundaki eşitlik bloğu listelenmeyen bir atla uzayabilir) → yalnız o zaman belirsiz.
  function slots(s,k){ const q=(Array.isArray(s.sira)&&s.sira.length?s.sira:(s.kazanan!=null?[s.kazanan]:[])).map(String).filter(Boolean);
    let dr=Array.isArray(s.derece)&&s.derece.length===q.length?s.derece.map(Number):null;
    if(dr&&dr.some((d,i)=>!(d>=1)||(i&&d<dr[i-1]))) dr=null;
    if(!dr){ if(s.esit) return {q,bad:1}; dr=q.map((_,i)=>i+1); }
    const trunc=q.length>=4&&!(+s.kosan>0&&+s.kosan<=q.length), V=[], O=[];
    for(let p=1;p<=k;p++){ const v=[]; for(let j=0;j<q.length;j++){ const d=dr[j], t=dr.filter(z=>z===d).length; if(d<=p&&p<=d+t-1) v.push(q[j]); }
      let open=!v.length; if(!open&&trunc){ const d=dr[q.indexOf(v[v.length-1])]; if(dr[dr.length-1]===d&&dr.filter(z=>z===d).length>1) open=true; }
      V.push(v); O.push(open); }
    return {q,V,O}; }
  // sıra başına aday kümelerinden farklı atlarla geçerli bir dizilim var mı: 1 kesin, .5 belirsiz (açık sırada listelenmeyen at), 0 yok
  function fit(cols,V,O,L){ let uns=false;
    const rec=(p,used,w)=>{ if(p===cols.length){ if(w){ uns=true; return false; } return true; }
      for(const h of cols[p]){ if(used.has(h)) continue; const inV=V[p].includes(h), wi=!inV&&O[p]&&!L.has(h); if(!inV&&!wi) continue;
        used.add(h); const r=rec(p+1,used,w||wi); used.delete(h); if(r) return true; }
      return false; };
    return rec(0,new Set(),false)?1:uns?.5:0; }
  const ekx=(S,G)=>{ const o=new Set(S.map(String)); for(const g of G||[]) if(g.some(n=>o.has(n))) g.forEach(n=>o.add(n)); return [...o]; };
  const NEED_N={ganyan:1,plase:2,ikili:2,sirali_ikili:2,uclu:3,tabela:4};
  function gradeRow(x){ if(x.man) return false; if(x.gv===2&&!x.need&&(x.ok!=null||x.iade)) return false;
    const T=TUR[x.tur]; if(!T) return false;
    const sig=()=>JSON.stringify([x.ok,!!x.need,x.res||"",x.iade||"",!!x.srz,x.kx||[],x.komb,x.gv||0]), b0=sig();
    const S=x.kid.map(k=>{ const c=cOf(k); return c&&c.sonuc?c.sonuc:null; });
    const multi=x.tur==="cifte"||x.tur==="altili", legOf=i=>multi?i:0;
    // koşmayan atlar (sonuc.kosmayan) seçimden düşülür
    const kmy=S.map(s=>s&&Array.isArray(s.kosmayan)?s.kosmayan.map(String):null);
    const eff=x.sec.map((c,i)=>{ const K=kmy[legOf(i)]; c=(c||[]).map(String); return K?c.filter(n=>!K.includes(n)):c; });
    let ok=null, need=false, res="", iade="", srz=false;
    if(kmy.some(Boolean)){ const kx=[...new Set(x.sec.flatMap((c,i)=>(c||[]).map(String).filter(n=>!eff[i].includes(n)).map(n=>(x.tur==="cifte"&&i?"2:":"")+(x.tur==="altili"&&i?(i+1)+":":"")+n)))];
      if(kx.length){ x.kx=kx; try{ if(x.tur==="altili") x.komb=eff.reduce((a,c)=>a*c.length,1); else { const r=raceOf(x.kid[0]); if(r){ const F=field(r), r2=x.tur==="cifte"?raceOf(x.kid[1]):null; if(x.tur!=="cifte"||r2) x.komb=calcF(x.tur,eff,F,r2?field(r2):null).komb; } } }catch(e){} } }
    if(multi){ const W=[];
      const R=S.map((s,i)=>{ if(!s) return null; const sl=slots(s,1); W[i]=sl.bad?sl.q[0]||"?":sl.V[0].join("="); if(sl.bad||!eff[i].length) return .5;
        return fit([ekx(eff[i],ekK(x.kid[i]))],sl.V,sl.O,new Set(sl.q)); });
      if(R.some(r=>r!=null)) res=R.map((r,i)=>r==null?"…":W[i]).join(x.tur==="cifte"?" / ":"-");
      if(R.some(r=>r===0)) ok=false; else if(R.every(r=>r===1)) ok=true; else if(R.every(r=>r!=null)) need=true; }
    else { const s=S[0]; if(s){ const k=NEED_N[x.tur], sl=slots(s,k), kos=+s.kosan||0, L=new Set(sl.q); res=sl.q.join("-");
        if(kos&&T.enaz&&kos<T.enaz) iade=`${kos} at koştu; ${T.ad} en az ${T.enaz} atla geçerli`;
        else if(eff.some(c=>!c.length)||(x.tur==="ikili"&&eff[0].length<2)) iade="seçilen at koşmadı";
        else if(sl.bad) need=true;
        else { let r;
          if(x.tur==="ganyan") r=fit([ekx(eff[0],ekK(x.kid[0]))],sl.V,sl.O,L);
          else if(x.tur==="plase"){ const ex=ekx(eff[0],ekK(x.kid[0])), U=new Set([...sl.V[0],...sl.V[1]]); r=ex.some(h=>U.has(h))?1:(sl.O[0]||sl.O[1])&&ex.some(h=>!L.has(h))?.5:0; }
          else if(x.tur==="ikili") r=fit([eff[0],eff[0]],sl.V,sl.O,L);
          else r=fit(eff.slice(0,k),sl.V,sl.O,L);
          if(r===1) ok=true; else if(r===0) ok=false; else need=true;
          // tabela: sıralı tutmadı ama seçilen dört at ilk dörde girdi → "sırasız" bilgisi (satır ✗ kalır)
          if(x.tur==="tabela"&&r===0&&!sl.O.some(Boolean)){ const F4=[...new Set(sl.V.flat())]; if(fit(eff.slice(0,4),[F4,F4,F4,F4],[0,0,0,0],L)===1) srz=true; } } } }
    // sonuç hiç gelmediyse: son koşunun saatinden 36 saat sonra "sonuç eksik"
    if(ok==null&&!need&&!iade&&x.ok==null){ const last=x.kid[x.kid.length-1].split("/"); const t=tsOf(last[0],multi?null:x.saat); if(isFinite(t)&&NOW()-t>36*3600e3) need=true; }
    if(iade){ x.iade=iade; delete x.ok; delete x.need; delete x.srz; x.gv=2; }
    else if(ok!=null){ x.ok=ok; delete x.need; delete x.iade; if(srz) x.srz=1; else delete x.srz; x.gv=2; }
    else if(need&&x.ok==null) x.need=1;   // eski kesin sonucu belirsizlikle ezme
    if(res) x.res=res;
    return sig()!==b0; }
  const doneR=x=>x.ok!=null||!!x.need||!!x.iade;
  function stAt(c){ try{ const I=Array.isArray(c&&c.at)?c.at:[]; if(!I.length) return "e"; if(I.some(i=>i.ok===false)) return "x"; const L=I.filter(i=>!i.iade); if(!L.length) return "i";
      if(L.every(i=>i.ok===true)) return "g"; if(I.every(doneR)) return "q"; return "w"; }catch(e){ return "w"; } }
  const ST={e:"Boş",w:"Bekliyor",g:"Tuttu",x:"Tutmadı",q:"Sonuç eksik",i:"İade"};
  const stPill=c=>{ const s=stAt(c); return `<span class="kx-st ${s==="i"?"e":s}">${s==="g"?"✓ ":s==="x"?"✗ ":s==="i"?"↺ ":""}${ST[s]}</span>`; };
  // bozuk/eksik at satırları (elle düzenlenmiş ya da yarım yazılmış kayıt) sessizce ayıklanır; spor:"at" olup at dizisi yoksa [] sayılır
  const atOk=x=>!!x&&!!TUR[x.tur]&&Array.isArray(x.kid)&&x.kid.length>0&&x.kid.every(k=>typeof k==="string")&&Array.isArray(x.sec)&&x.sec.every(Array.isArray);
  function fixAll(){ try{ for(const c of KX.L) if(isAt(c)&&(!Array.isArray(c.at)||c.at.some(x=>!atOk(x)))) c.at=(Array.isArray(c.at)?c.at:[]).filter(atOk); }catch(e){} }
  fixAll();
  const kStarted=(x,k)=>{ const r=raceOf(k); return r?started(r):(x.t||0)<=NOW(); };
  const ageOf=C=>{ const t=Date.parse(String(C&&C.guncelleme_tsi||"").replace(" ","T")+":00+03:00"); return isFinite(t)?NOW()-t:Infinity; };
  let fetching=false;
  // sonuç tazeleme: başlamış ve sonucu gelmemiş satır varsa (KUPO görünürken) canlı dosya 10 dakikada bir yeniden çekilir — AT.load'un
  // yüklediği gün (C) dolu olsa da; C taze ise (güncelleme < 10 dk) beklenir. Eski hatalı puanlanmış satırlar için gün bir kez çekilir.
  async function fetchDays(){ if(fetching) return; try{ fixAll(); const need=new Set(), now=NOW(), vis=$("v-kupon")&&!$("v-kupon").hidden;
      for(const c of KX.L) if(isAt(c)) for(const x of c.at||[]){ if(x.man) continue; const open=!(x.ok!=null&&!x.need)&&!x.iade, regr=x.gv!==2&&x.ok!=null; if(!open&&!regr) continue;
        for(const k of x.kid){ const d=dayOf(k); if(now<tsOf(d,"00:00")) continue; const C=((A().AT.canli)||{})[d];
          if(!C&&!CAN[d]) need.add(d);
          else if(open&&vis&&!(cOf(k)||{}).sonuc&&kStarted(x,k)&&(CAN[d]?now-CAN[d].t>10*60e3:ageOf(C)>10*60e3)) need.add(d); } }
      if(!need.size) return; fetching=true;
      try{ await Promise.all([...need].slice(0,4).map(d=>A().j("data/at/canli/"+d+".json").then(v=>{ CAN[d]={v:v&&v.kosular?v:null,t:NOW()}; }))); }finally{ fetching=false; }
      gradeAll(); }catch(e){ fetching=false; console.error(e); } }
  // KUPO görünürken 5 dakikada bir: yalnız başlamış/sonuçsuz satır varsa istek atar (fetchDays kendisi süzer)
  setInterval(()=>{ try{ if(document.hidden) return; const v=$("v-kupon"); if(!v||v.hidden) return; fetchDays(); }catch(e){} },5*60e3);
  function gradeAll(){ try{ fixAll(); let ch=false;
    for(const c of KX.L){ if(!isAt(c)) continue; let cc=false; for(const x of c.at||[]){ if(gradeRow(x)) cc=true; if(c.durum==="acik"&&recalc(x)) cc=true; } if(cc){ c.upd=NOW(); ch=true; } }
    const fin=[]; for(const c of KX.L){ if(!isAt(c)||c.durum!=="acik"||!(c.at||[]).length||!c.at.every(doneR)) continue; c.durum="bitti"; c.bitti=NOW(); c.upd=NOW(); fin.push(c); ch=true; }
    if(ch){ save(); if(fin.length){ act(); const c=fin[0], s=stAt(c); try{ toast(fin.length>1?`🏆 ${fin.length} at KUPO'n sonuçlandı · Eski KUPO'larım`:`🏆 ${c.ad} sonuçlandı: ${ST[s]} (${c.at.filter(i=>i.ok).length}/${c.at.length}) · Eski KUPO'larım`);
      if(Sound.olay){ const w=fin.some(x=>stAt(x)==="g"); if(w||s==="x") Sound.olay(w?"atKupoTuttu":"tutmadi"); } else Sound.toggle(s==="g"); }catch(e){} } refresh(); }
    return ch; }catch(e){ console.error(e); return false; } }
  window.atkGrade=gradeAll;
  // ---------- KUPO ekranında at kuponu ----------
  const UI={edit:false,cf:null,od:null,ocf:null};
  function selHtml(x){ const W=x.res?x.res.split(/\s*[\/-]\s*/):[];
    return `<div class="atk-sel">${x.sec.map((c,i)=>{ const lb=legLbl(x,i), win=x.tur==="cifte"||x.tur==="altili"?W[i]:(x.tur==="ikili"?null:W[i]);
      return `<div class="atk-sl">${lb?`<i>${esc(lb)}</i>`:""}<span>${c.map(no=>{ const nm=nmOf(x,x.tur==="cifte"||x.tur==="altili"?i:0,no); const w=(win!=null&&String(win)===no)||(x.tur==="ikili"&&W.slice(0,2).includes(no))||(x.tur==="plase"&&W.slice(0,2).includes(no));
        const w2=w||(win!=null&&String(win).split("=").includes(no)), kx=(x.kx||[]).includes((x.tur==="cifte"&&i?"2:":x.tur==="altili"&&i?(i+1)+":":"")+no);
        return `<span class="atk-h${w2?" w":""}${kx?" k":""}"${kx?` title="koşmadı"`:""}><u>${esc(no)}</u>${nm&&c.length<=4&&x.tur!=="altili"?esc(String(nm).slice(0,18)):""}</span>`; }).join("")}</span></div>`; }).join("")}</div>`; }
  function rowAt(x,i,weak,old,cid){ const T=TUR[x.tur], lbl=A().dLbl(x.d), r=raceOf(x.kid[0]), st=r?started(r):x.t<=NOW();
    const where=x.tur==="altili"?`${esc(x.hip)} ${x.altNo||""}. 6'lı · ${x.kosu}.–${x.kosu+5}. koşular`:x.tur==="cifte"?`${esc(x.hip)} ${x.kosu}. + ${x.kosu+1}. koşu`:`${esc(x.hip)} ${x.kosu}. koşu`;
    const res=x.ok===true?`<span class="kx-res g" role="img" aria-label="Tuttu"><i>✓</i></span>`:x.ok===false?`<span class="kx-res x" role="img" aria-label="${x.srz?"Sıralı tutmadı, sırasız tuttu":"Tutmadı"}"><i>✗</i></span>`
      :x.iade?`<span class="kx-res w" role="img" aria-label="İade, koşul dışı"><i>↺</i></span>`:old?`<span class="kx-res w" role="img" aria-label="Bekliyor"><i>⏳</i></span>`:`<button class="rm" type="button" data-atk="rm" data-i="${i}" aria-label="${esc(where)} satırını KUPO'dan çıkar">✕</button>`;
    const bd=(x.srz?`<span class="atk-bd srz">sırasız</span><span class="atk-bdn">4 at ilk dörtte, sıra tutmadı</span>`:"")+(x.iade?`<span class="atk-bd iade">iade · koşul dışı</span><span class="atk-bdn">${esc(x.iade)}</span>`:"")
      +((x.kx||[]).length?`<span class="atk-bd kx">koşmayan at çıkarıldı</span><span class="atk-bdn">${esc(x.kx.join(", "))} · kombinasyon ve olasılık yeniden hesaplandı</span>`:"");
    const man=x.need&&x.ok==null&&!x.iade?`<div class="kx-hint">Sonuç eksik:<span class="kx-man"><button type="button" data-atk="man" data-c="${cid}" data-i="${i}" data-v="1" aria-label="Tuttu olarak işaretle">✓</button><button type="button" data-atk="man" data-c="${cid}" data-i="${i}" data-v="0" aria-label="Tutmadı olarak işaretle">✗</button></span></div>`:"";
    return `<div class="cprow kx-r atk-r${weak?" weak":""}"><div class="l"><small>${HORSE}${esc(lbl)} · ${where}${x.saat?" · "+esc(x.saat):""}${x.tur==="altili"?" · "+({dar:"Dar",orta:"Orta",genis:"Geniş"}[x.sev]||""):""}</small>
      <b>${esc(T.ad)} <small>${esc(T.kisa)}</small></b>${selHtml(x)}
      <span class="kx-line"><span>${fN(x.komb)} kombinasyon</span><span>OXXai <span class="kx-pp">${fP(x.p)}</span></span>${weak&&x.ok==null?`<span class="kx-weak">En zayıf halka</span>`:""}${x.res?`<span class="kx-sc">Sonuç ${esc(x.res)}</span>`:st&&x.ok==null&&!x.need?`<span class="kx-sc">koşu başladı · sonuç bekleniyor</span>`:""}${bd}${!old&&!st&&x.ok==null?`<button type="button" class="kx-lnk" data-atk="ed" data-i="${i}">Düzenle</button>`:""}</span>${man}</div>${res}</div>`; }
  function sumAt(c){ const I=c.at, n=I.length, K=I.reduce((a,x)=>a+(+x.komb||0),0), p=I.reduce((a,x)=>a*(x.p||0),1), e=I.reduce((a,x)=>a+(x.p||0),0);
    const wi=I.reduce((b,x,i)=>(x.p||0)<(I[b].p||0)?i:b,0), w=I[wi], g=I.filter(x=>x.ok===true).length, xx=I.filter(x=>x.ok===false).length, iq=I.filter(x=>x.iade).length, sz=I.filter(x=>x.ok===false&&x.srz).length, wt=n-g-xx-iq;
    const no=I.filter(x=>x.pk==="oran").length, ks=new Set(I.flatMap(x=>x.kid)).size;
    return `<div class="panel cpsum kx-sum"><div class="list">
      <div><span>Satır</span><span>${n} satır<span class="kx-sub">${ks} koşu</span></span></div>
      <div><span>Toplam kombinasyon</span><span><b>${fN(K)}</b></span></div>
      <div><span>OXXai birlikte tutma olasılığı<span class="kx-sub">tüm satırlar birden</span></span><span><b>${fP(p)}</b></span></div>
      <div><span>Beklenen tutan satır<span class="kx-sub">olasılıklar toplamı</span></span><span>${f1(e)} / ${n}</span></div>
      ${n>1?`<div><span>En zayıf halka</span><span>${esc(w.hip)} ${w.kosu}. koşu<span class="kx-sub">${esc(TUR[w.tur].ad)} · ${fP(w.p)}</span></span></div>`:""}
      ${g||xx||iq?`<div><span>Sonuç</span><span>${g} tuttu · ${xx} tutmadı${sz?` (${sz} sırasız)`:""}${iq?` · ${iq} iade`:""}${wt?` · ${wt} bekliyor`:""}</span></div>`:""}
      <div><span>Olasılık kaynağı</span><span>${no===n?"oranla güncel":no?`${no} satır oranla, ${n-no} sabah`:"sabah tahmini"}</span></div></div>
      <p class="note">Her satırın olasılığı indirimli Harville yöntemiyle koşu olasılıklarından hesaplanır; birlikte tutma olasılığı satırların çarpımıdır (koşular bağımsız sayılır, aynı koşu tek satırda). Koşu başlayana kadar oran geldikçe güncellenir. Para tutarı ve kazanç gösterilmez.</p></div>`; }
  function karPanel(c){ if(!KAR) return ""; const T=[...new Set(c.at.map(x=>x.tur))]; const L=T.map(t=>{ const x=c.at.find(z=>z.tur===t); const s=karLine(t,x.komb); return s?`<p class="atk-kar"><b>${esc(TUR[t].ad)}</b> · ${s}</p>`:""; }).filter(Boolean);
    return L.length?`<div class="panel"><div class="kx-kh"><b style="font-size:17px">📊 Geri test karnesi</b><small>${esc((KAR.donem||[]).join(" – "))}</small></div>${L.join("")}</div>`:""; }
  function renderCp(box,c){ const I=c.at||[];
    const head=`<div class="kx-ch"><div class="kx-nm">${UI.edit?`<input class="kx-in" id="atkIn" maxlength="32" value="${esc(c.ad)}" aria-label="KUPO adı" enterkeyhint="done"><button type="button" class="kx-ic" data-atk="rok" aria-label="Adı kaydet">✓</button>`
        :`<h2>${esc(c.ad)}</h2><button type="button" class="kx-ic" data-atk="ren" aria-label="KUPO adını değiştir"><svg viewBox="0 0 24 24"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/></svg></button>`}</div>${UI.edit?"":stPill(c)}</div>
      <div class="kx-meta">${HORSE}At yarışı KUPO'su · ${I.length} satır · ${esc(ist(new Date(c.olusturma),{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}))} açıldı</div>`;
    const acts=UI.cf==="del"?`<div class="kx-cf" role="alertdialog" aria-label="KUPO'yu sil"><p><b>${esc(c.ad)}</b> silinsin mi? İçindeki ${I.length} satır da silinir; bu geri alınamaz.</p><div><button type="button" class="btn ghost" data-atk="cfno">Vazgeç</button><button type="button" class="btn dng" data-atk="cfdel">Sil</button></div></div>`
      :`<div class="kx-acts" style="grid-template-columns:repeat(3,minmax(0,1fr))"><button type="button" data-atk="share" ${I.length?"":"disabled"}><svg viewBox="0 0 24 24"><path d="M12 3v12M8 7l4-4 4 4"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg>Paylaş</button><button type="button" data-atk="arch" ${I.length?"":"disabled"}><svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="5" rx="1.5"/><path d="M5 9v9a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9M10 13h4"/></svg>Arşive kaldır</button><button type="button" class="dng" data-atk="del"><svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg>Sil</button></div>`;
    let h;
    if(!I.length) h=`<div class="atk-root"><div class="panel kx-card">${head}<div class="kx-empty atk-empty" style="padding:8px 0">${lion()}<b>${esc(c.ad)} boş</b><p>At Yarışı'nda koşu kartındaki <b>＋ KUPO</b>'ya dokun; Kazanan, Derece, İkili, Sıralı İkili, Çifte, Sıralı Üçlü, Tabela ya da 6'lı kur. OXXai her satırın tutma olasılığını canlı hesaplar.</p></div>
        <button class="btn" type="button" data-atk="gold">Altın atlarla kazanan listesi kur</button><button class="btn ghost" type="button" data-atk="goat">At Yarışı'na git</button></div>${acts}</div>`;
    else { const wi=I.length>1?I.reduce((b,x,i)=>(x.p||0)<(I[b].p||0)?i:b,0):-1;
      h=`<div class="atk-root"><div class="panel kx-card">${head}${I.map((x,i)=>rowAt(x,i,wi===i,false,c.id)).join("")}<button class="btn ghost" type="button" data-atk="goat" style="margin-top:6px">＋ Koşu ekle</button></div>${sumAt(c)}${karPanel(c)}${acts}
        <p class="kx-tip">Koşu bitince her satırda ✓/✗ görünür; tüm satırlar bitince KUPO sonucuyla <b>Eski KUPO'larım</b> bölümüne geçer. Kayıtlar yalnızca bu telefonda tutulur.</p>
        <p class="disc">OXXai yalnızca hobi amaçlı tahmin ve takip aracıdır; oyun almaz, para tutarı göstermez ve hiçbir siteye yönlendirmez · 18+</p></div>`; }
    box.innerHTML=h;
    const inp=$("atkIn"); if(inp){ inp.focus(); inp.select(); inp.onkeydown=e=>{ if(e.key==="Enter"){ e.preventDefault(); rename(c,inp.value); } else if(e.key==="Escape"){ UI.edit=false; refresh(); } }; inp.onblur=()=>setTimeout(()=>{ if(UI.edit) rename(c,inp.value); },120); } }
  function rename(c,v){ v=String(v||"").replace(/\s+/g," ").trim().slice(0,32); UI.edit=false; if(v&&v!==c.ad){ c.ad=v; save(c); toast("KUPO adı: "+v); } refresh(); }
  function shareText(c){ const s=stAt(c);
    return `🏆 OXXai · ${c.ad}${s==="g"||s==="x"?" · "+ST[s]:""}\n`+c.at.map((x,i)=>`${i+1}) 🐎 ${x.hip} ${x.tur==="altili"?x.kosu+".–"+(x.kosu+5)+". koşular":x.tur==="cifte"?x.kosu+".+"+(x.kosu+1)+". koşu":x.kosu+". koşu"} ${x.saat} · ${TUR[x.tur].ad}: ${x.sec.map(c=>c.join(",")).join(" / ")} · ${fN(x.komb)} komb. · OXXai ${fP(x.p)}${x.ok===true?" ✓":x.ok===false?(x.srz?" ✗ (sırasız)":" ✗"):x.iade?" ↺ iade":""}${x.res?" (sonuç "+x.res+")":""}`).join("\n")
      +`\nToplam ${fN(c.at.reduce((a,x)=>a+(+x.komb||0),0))} kombinasyon · birlikte tutma olasılığı ${fP(c.at.reduce((a,x)=>a*(x.p||0),1))}\nHobi amaçlı olasılık; garanti değildir · 18+`; }
  window.atkShareText=c=>shareText(c);   // v129: at KUPO paylaş listesi
  // Eski KUPO'larım: at kuponları ayrı bölüm + istatistik
  function statsAt(P){ const D=P.filter(c=>{ const s=stAt(c); return s==="g"||s==="x"; }), W=D.filter(c=>stAt(c)==="g"), R=P.flatMap(c=>c.at).filter(x=>x.ok!=null);
    const by={}; for(const x of R){ const b=by[x.tur]||(by[x.tur]={n:0,h:0,e:0}); b.n++; if(x.ok) b.h++; b.e+=x.p||0; }
    const pc=D.length?D.reduce((a,c)=>a+c.at.reduce((m,x)=>m*(x.p||0),1),0)/D.length:0, pr=R.length?R.reduce((a,x)=>a+(x.p||0),0)/R.length:0, hr=R.length?R.filter(x=>x.ok).length/R.length:0;
    const kt=ORDER.filter(t=>by[t]).map(t=>{ const b=by[t], z=KAR&&KAR.turler&&KAR.turler[t]; return `<div><span><b>${esc(TUR[t].ad)}</b></span><span>${b.h}/${b.n}</span><span>${fP(b.e/b.n)}</span><span>${z&&z.n?fP(rate(z)):"–"}</span></div>`; }).join("");
    return `<div class="panel"><div class="kx-kh"><b>${D.length} at KUPO'sundan ${W.length} tuttu</b><small>${P.length>D.length?`${P.length-D.length} KUPO'nun sonucu eksik`:"yalnızca bu telefonda"}</small></div>
      <div class="kx-tiles"><div class="kx-tile gd"><small>KUPO kazanma oranı</small><b>${D.length?fP(W.length/D.length):"–"}</b><div class="kx-bar"><i style="width:${D.length?Math.round(W.length/D.length*100):0}%"></i></div></div>
        <div class="kx-tile"><small>Satır isabeti</small><b>${R.length?fP(hr):"–"}</b><i>${R.filter(x=>x.ok).length} / ${R.length} satır tuttu${(()=>{ const z=R.filter(x=>x.ok===false&&x.srz).length; return z?` · ${z} sırasız`:""; })()}</i></div>
        ${D.length?`<div class="kx-tile w2"><small>OXXai kalibrasyonu · KUPO</small><i>OXXai bu KUPO'lara ortalama <b>${fP(pc)}</b> birlikte tutma olasılığı vermişti; gerçekte <b>${fP(W.length/D.length)}</b> tuttu.${D.length<10?" Örnek az, temkinli oku.":""}</i></div>`:""}
        ${R.length?`<div class="kx-tile w2"><small>OXXai kalibrasyonu · satır</small><i>Satırlarda OXXai ortalama <b>${fP(pr)}</b> demişti; gerçekte <b>${fP(hr)}</b> tuttu.</i></div>`:""}</div>
      ${kt?`<div class="atk-kt" style="margin-top:10px"><div><span>Tür</span><span>Tutan</span><span>OXXai bekl.</span><span>Geri test</span></div>${kt}</div><p class="note" style="margin:6px 0 0">Geri test: en olası tek kombinasyonun geçmiş koşulardaki isabeti${KAR?` (${esc((KAR.donem||[]).join(" – "))})`:""}.</p>`:""}</div>`; }
  function oldCard(c){ const I=c.at, s=stAt(c), h=I.filter(i=>i.ok).length, sz=I.filter(i=>i.ok===false&&i.srz).length, iq=I.filter(i=>i.iade).length, opn=UI.od===c.id;
    return `<div class="kx-oc"><button type="button" class="kx-oh" data-atk="oo" data-c="${c.id}" aria-expanded="${opn}"><b>${HORSE}${esc(c.ad)}</b>${stPill(c)}<small>${esc(ist(new Date(c.bitti||c.arsivAt||c.olusturma),{day:"numeric",month:"short",year:"numeric"}))} · ${I.length} satır · ${h}/${I.length} tuttu${sz?` · ${sz} sırasız`:""}${iq?` · ${iq} iade`:""} · OXXai ${fP(I.reduce((a,x)=>a*(x.p||0),1))}${c.durum==="arsiv"&&s==="w"?" · arşivde, sonuç bekliyor":""}</small></button>
      ${opn?`<div class="kx-od">${I.map((x,i)=>rowAt(x,i,false,true,c.id)).join("")}
        ${UI.ocf===c.id?`<div class="kx-cf"><p><b>${esc(c.ad)}</b> kalıcı olarak silinsin mi?</p><div><button type="button" class="btn ghost" data-atk="ocfno">Vazgeç</button><button type="button" class="btn dng" data-atk="ocfdel" data-c="${c.id}">Sil</button></div></div>`
          :`<div class="kx-acts"><button type="button" data-atk="osh" data-c="${c.id}"><svg viewBox="0 0 24 24"><path d="M12 3v12M8 7l4-4 4 4"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg>Paylaş</button>${c.durum==="arsiv"?`<button type="button" data-atk="oback" data-c="${c.id}"><svg viewBox="0 0 24 24"><path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/></svg>Geri al</button>`:`<span></span>`}<button type="button" class="dng" data-atk="odel" data-c="${c.id}"><svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg>Sil</button></div>`}</div>`:""}</div>`; }
  function decorateOld(box){ const P=KX.L.filter(c=>isAt(c)&&c.durum!=="acik").sort((a,b)=>(b.bitti||b.arsivAt||b.olusturma)-(a.bitti||a.arsivAt||a.olusturma));
    const ids=new Set(P.map(c=>c.id)); box.querySelectorAll('.kx-oc').forEach(el=>{ const b=el.querySelector('[data-kx="oo"][data-c]'); if(b&&ids.has(b.dataset.c)) el.remove(); });
    const old=box.querySelector(".atk-old"); if(old) old.remove(); if(!P.length) return;
    const fut=KX.L.some(c=>!isAt(c)&&c.durum!=="acik"&&c.items.length);
    if(!fut){ const em=box.querySelector(":scope > .kx-empty"); if(em) em.remove(); }
    const sec=document.createElement("div"); sec.className="atk-old"; sec.innerHTML=`<div class="atk-sec">${HORSE}At KUPO'ları</div>${statsAt(P)}<div class="kx-old">${P.map(oldCard).join("")}</div>`;
    box.appendChild(sec); }
  // ---------- KUPO kabuğuna bağlanma (futbol kodu değişmeden) ----------
  function decorate(){ try{ const v=$("v-kupon"); if(!v) return; fixAll(); const c=act();
      const cb=$("cpBox"); if(cb&&isAt(c)&&!(KP.tab==="eski"||KP.tab==="oyn")){ const root=cb.querySelector(":scope > .atk-root"); if(!root||root.dataset.c!==c.id||root.dataset.v!==String(c.upd||0)+(UI.edit?"e":"")+(UI.cf||"")){ renderCp(cb,c); const r=cb.querySelector(":scope > .atk-root"); if(r){ r.dataset.c=c.id; r.dataset.v=String(c.upd||0)+(UI.edit?"e":"")+(UI.cf||""); } } }
      const sub=$("kxSub"); if(sub&&isAt(c)&&KP.tab==="cp"){ const want=`Aktif KUPO: <b>${esc(c.ad)}</b> · 🐎 ${c.at.length} satır · ${KX.L.filter(x=>x.durum==="acik").length} açık KUPO`; if(sub.innerHTML!==want.replace(/&#39;/g,"'")) sub.innerHTML=want; }
      const ch=$("kxChips"); if(ch){ ch.querySelectorAll("button[data-kc]").forEach(b=>{ const k=KX.L.find(x=>x.id===b.dataset.kc); if(!isAt(k)||b.querySelector(".atk-ic")) return;
          const s=stAt(k); b.insertAdjacentHTML("afterbegin",(s!=="e"?`<i class="kx-dot ${s==="q"?"w":s}"></i>`:"")+HORSE); const sm=b.querySelector("small"); if(sm) sm.textContent=k.at.length||""; });
        /* v122: "＋ Yeni at KUPO'su" çipi futbol KUPO ekranından kaldırıldı; at KUPO'su At › KUPO'da açılır */ }
      const od=$("kxOld"); if(od&&!od.hidden){ const needs=KX.L.some(c=>isAt(c)&&c.durum!=="acik"); const mk=od.querySelector(".atk-old"); const stale=[...od.querySelectorAll('.kx-oc [data-kx="oo"][data-c]')].some(b=>isAt(KX.L.find(x=>x.id===b.dataset.c)));
        if(needs&&(!mk||stale||mk.dataset.v!==oldSig())){ decorateOld(od); const m=od.querySelector(".atk-old"); if(m) m.dataset.v=oldSig(); } }
    }catch(e){ console.error(e); } }
  const oldSig=()=>KX.L.filter(c=>isAt(c)&&c.durum!=="acik").map(c=>c.id+":"+(c.upd||0)).join(",")+"|"+UI.od+"|"+UI.ocf;
  let mo=null; function hook(){ const v=$("v-kupon"); if(!v||mo) return; mo=new MutationObserver(()=>{ decorate(); }); mo.observe(v,{childList:true,subtree:true}); decorate(); }
  hook(); setTimeout(hook,1500);
  function hdrFix(){ try{ const b=$("hdrKup"); if(!b) return; const c=act(); if(!isAt(c)) return; fixAll(); const bd=b.querySelector(".kx-bd"), n=c.at.length;
    if(bd&&(bd.hidden!==!n||bd.textContent!==String(n))){ bd.hidden=!n; bd.textContent=n; } const al=`KUPO: ${c.ad}, ${n} at satırı`; if(b.getAttribute("aria-label")!==al) b.setAttribute("aria-label",al); }catch(e){} }
  let hmo=null; function hdrHook(){ const b=$("hdrKup"); if(!b||hmo) return; hmo=new MutationObserver(hdrFix); hmo.observe(b,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:["hidden","aria-label"]}); hdrFix(); }
  hdrHook(); setTimeout(hdrHook,1500); setTimeout(hdrHook,4500);
  // v122: Power Now çizildikten sonra futbol tarafı "oxx:power-cizildi" olayı yayar (renderPower sarmalanmıyor)
  document.addEventListener("oxx:power-cizildi",()=>{ try{ const b=$("pwCp"), c=act(); if(b&&isAt(c)) b.innerHTML=`${lion()}${esc(c.ad)} · <b>${c.at.length} at satırı</b><span>Aç ›</span>`; }catch(e){} });
  // futbol "Hangi KUPO'ya?" listesinde at kuponları görünmez (tek spor)
  new MutationObserver(()=>{ const s=$("kxSheet"); if(!s||s.dataset.atk) return; s.dataset.atk=1; s.querySelectorAll("[data-pk]").forEach(b=>{ if(isAt(KX.L.find(x=>x.id===b.dataset.pk))) b.remove(); }); }).observe(document.body,{childList:true});
  function refresh(){ try{ hdrFix(); const v=$("v-kupon"); if(v&&!v.hidden){ window.kxRefresh(); decorate(); } deco(); }catch(e){} }
  // KUPO ekranı tıklamaları (futbolun data-kx'ine dokunmaz)
  document.addEventListener("click",e=>{ const b=e.target.closest("[data-atk]"); if(!b||!b.closest("#v-kupon")) return; e.stopPropagation(); const a=b.dataset.atk, c=act(), i=+b.dataset.i; try{ buzz(6); }catch(_){}
    if(a==="newat"){ const n=newAt(); setActive(n); toast(`${n.ad} açıldı · At Yarışı'ndan koşu ekle`); UI.edit=false; window.kxRefresh(); return; }
    if(a==="goat"){ try{ A().openAt(); }catch(_){} return; }
    if(a==="gold"){ goldCoupon(); return; }
    const oc=KX.L.find(x=>x.id===b.dataset.c);
    if(a==="man"&&oc){ const x=oc.at[i]; if(!x) return; x.ok=b.dataset.v==="1"; x.man=1; delete x.need; oc.upd=NOW(); gradeAll(); save(oc); refresh(); return; }
    if(a==="oo"){ UI.od=UI.od===b.dataset.c?null:b.dataset.c; UI.ocf=null; decorate(); return; }
    if(a==="osh"&&oc){ openShare({title:"KUPO'yu paylaş",text:shareText(oc),url:appLink()}); return; }
    if(a==="oback"&&oc){ oc.durum="acik"; delete oc.arsivAt; setActive(oc); save(oc); toast(`${oc.ad} KUPO'larıma geri alındı`); KP.tab="cp"; renderKupon(); return; }
    if(a==="odel"&&oc){ UI.ocf=oc.id; decorate(); return; }
    if(a==="ocfno"){ UI.ocf=null; decorate(); return; }
    if(a==="ocfdel"&&oc){ UI.ocf=null; UI.od=null; const ad=oc.ad; delCoupon(oc); toast(`${ad} silindi`); window.kxRefresh(); decorate(); return; }
    if(!isAt(c)) return;
    if(a==="rm"){ const x=c.at[i]; if(!x) return; c.at.splice(i,1); save(c); toast(`${sfx(c.ad,1)} çıkarıldı · ${c.at.length} satır`); try{ Sound.olay?Sound.olay("kupoCikar"):Sound.toggle(false); }catch(_){} refresh(); return; }
    if(a==="ed"){ const x=c.at[i]; if(!x) return; if(x.tur==="altili"){ AT_open6(x); return; } openB(x.kid[0],{row:x}); return; }
    if(a==="ren"){ UI.edit=true; decorate(); return; }
    if(a==="rok"){ const inp=$("atkIn"); rename(c,inp?inp.value:c.ad); return; }
    if(a==="share"){ openShare({title:"KUPO'yu paylaş",text:shareText(c),url:appLink()}); return; }
    if(a==="arch"){ c.durum="arsiv"; c.arsivAt=NOW(); save(c); act(); toast(`${c.ad} Eski KUPO'larıma taşındı`); try{ paintCoupon(); }catch(_){} renderKupon(); return; }
    if(a==="del"){ UI.cf="del"; decorate(); return; }
    if(a==="cfno"){ UI.cf=null; decorate(); return; }
    if(a==="cfdel"){ UI.cf=null; const ad=c.ad; delCoupon(c); try{ paintCoupon(); }catch(_){} toast(`${ad} silindi`); renderKupon(); return; }
  },true);
  function AT_open6(x){ try{ A().AT.d=x.d; A().AT.tab="altili"; A().AT.sev=x.sev; A().openAt(); }catch(e){} }
  function goldCoupon(){ const D=A().AT.d&&A().AT.data[A().AT.d]; if(!D){ toast("At yarışı verisi yükleniyor; birazdan tekrar dene"); try{ A().load(); }catch(e){} return; }
    const G=A().goldOfDay(D).filter(x=>!started(x.r)); if(!G.length){ toast("Şu an başlamamış koşuda altın at yok"); return; }
    const c=atAct(true); let n=0; for(const g of G){ const F=field(g.r); const row=mkRow("ganyan",g.r,[unitOf(F,String(g.h.no))],F); if(addRow(row,c)) n++; }
    if(n) toast(`${n} altın at ganyan satırı olarak ${sfx(c.ad)} eklendi`); }
  // ---------- At Yarışı bölümü: ＋ Kupon girişleri ----------
  function inCoupon(kid){ const c=atAct(false); return c?c.at.find(x=>x.kid.includes(kid)):null; }
  function deco(){ try{ const box=$("atBox"); if(!box) return;
      box.querySelectorAll(".at-race[data-rid]").forEach(el=>{ const kid=el.dataset.rid, r=raceOf(kid); let w=el.querySelector(".atk-acts"); const sh=el.querySelector(".at-share");
        const x=inCoupon(kid), st=r?started(r):true, want=st?"":(x?`<b>✓</b><span>KUPO'da · ${esc(TUR[x.tur].ad)}</span>`:`<b>＋</b><span>KUPO</span>`);
        if(st){ if(w){ const s2=w.querySelector(".at-share"); if(s2) w.after(s2); w.remove(); } return; }
        if(!w&&sh){ w=document.createElement("div"); w.className="atk-acts"; sh.before(w); w.innerHTML=`<button type="button" class="atk-add" data-atkr="${esc(kid)}" aria-label="Bu koşudan at KUPO'su kur"></button>`; w.appendChild(sh); sh.innerHTML="📤 Paylaş"; sh.setAttribute("aria-label","Bu koşunun tahminini paylaş"); }
        const b=w&&w.querySelector(".atk-add"); if(b&&b.innerHTML!==want.replace(/&#39;/g,"'")){ b.innerHTML=want; b.classList.toggle("on",!!x); } });
      box.querySelectorAll(".al-c").forEach(el=>{ const s=el.querySelector("[data-als]"); if(!s) return; const id=s.dataset.als, X=altById(A().AT.d,id); if(!X) return; const sv=A().AT.sev||"orta";
        const first=raceOf(`${A().AT.d}/${X.hipodrom}/${X.baslangic_kosu}`), st=first?started(first):true, c=atAct(false), has=c&&c.at.find(z=>z.tur==="altili"&&z.alt===id&&z.sev===sv);
        let b=el.querySelector(".atk-add"); const want=st?`<span>İlk ayak başladı · KUPO'ya eklenemez</span>`:has?`<b>✓</b><span>KUPO'da · ${({dar:"Dar",orta:"Orta",genis:"Geniş"})[sv]}</span>`:`<b>＋</b><span>KUPO'ya ekle · ${({dar:"Dar",orta:"Orta",genis:"Geniş"})[sv]}</span>`;
        if(!b){ s.insertAdjacentHTML("beforebegin",`<button type="button" class="atk-add" data-atka="${esc(id)}"></button>`); b=el.querySelector(".atk-add"); }
        if(b.innerHTML!==want.replace(/&#39;/g,"'")){ b.innerHTML=want; b.disabled=st; b.classList.toggle("on",!!has); } });
      gradeAll(); }catch(e){ console.error(e); } }
  let amo=null; function atHook(){ const b=$("atBox"); if(!b||amo) return; amo=new MutationObserver(deco); amo.observe(b,{childList:true}); deco(); }
  atHook(); setTimeout(atHook,1200); setTimeout(atHook,5000);
  let lastAh=null; document.addEventListener("click",e=>{ const t=e.target.closest("[data-ah]"); if(t) lastAh=t.dataset.ah; },true);
  new MutationObserver(()=>{ const s=$("atSheet"); if(!s||s.dataset.atk||!lastAh) return; s.dataset.atk=1; const [rid,no]=lastAh.split("|"), r=raceOf(rid); if(!r||started(r)) return;
    const fav=s.querySelector("#atFav"); if(fav) fav.insertAdjacentHTML("beforebegin",`<button type="button" class="atk-add atk-hs" data-atkh="${esc(rid)}|${esc(no)}"><b>＋</b><span>Bu atla KUPO kur</span></button>`); }).observe(document.body,{childList:true});
  document.addEventListener("click",e=>{ const b=e.target.closest("[data-atkr],[data-atka],[data-atkh]"); if(!b) return; e.preventDefault(); e.stopPropagation(); try{ buzz(8); }catch(_){}
    if(b.dataset.atkr){ const x=inCoupon(b.dataset.atkr); openB(b.dataset.atkr,x&&x.tur!=="altili"&&x.kid[0]===b.dataset.atkr?{row:x}:{}); return; }
    if(b.dataset.atkh){ const [rid,no]=b.dataset.atkh.split("|"); const s=$("atSheet"); if(s) s.remove(); openB(rid,{no}); return; }
    if(b.dataset.atka){ const d=A().AT.d, X=altById(d,b.dataset.atka), sv=A().AT.sev||"orta"; const row=X&&altRow(d,X,sv); if(!row) return; karne().then(()=>{ addRow(row); deco(); }); } },true);
  // ---------- kurucu (alt sayfa) ----------
  let B=null;
  function closeB(){ const s=$("atkSheet"); if(s) s.remove(); B=null; }
  function openB(kid,o){ o=o||{}; const r=raceOf(kid); if(!r){ toast("Bu koşunun verisi bulunamadı"); return; } if(started(r)){ toast("Bu koşu başladı; KUPO'ya eklenemez"); return; }
    const F=field(r); let tur=o.row?o.row.tur:(o.tur||lsG(LSTUR,"ganyan")); if(!TUR[tur]||elig(tur,r,F)) tur="ganyan";
    B={kid,tur,sec:[],edit:o.row?o.row.id:null,tgt:null,pick:false,sev:A().AT.sev||"orta",alt:null};
    resetSec(o.row?o.row.sec:null,o.no); if(o.row){ const c=atAct(false); if(c) B.tgt=c.id; }
    closeB0(); const s=document.createElement("div"); s.id="atkSheet"; s.className="kx-sh atk-sh"; s.setAttribute("role","dialog"); s.setAttribute("aria-modal","true"); s.setAttribute("aria-label","At KUPO'su kur");
    s.innerHTML=`<div></div>`; document.body.appendChild(s);
    s.addEventListener("click",onB); B.el=s; paintB(true);
    karne().then(()=>{ if(B&&B.el===s) paintB(false); });
    try{ s.querySelector(".atk-tur [aria-pressed=true]").focus({preventScroll:true}); }catch(e){} }
  function closeB0(){ const s=$("atkSheet"); if(s) s.remove(); }
  function resetSec(sec,no){ const T=TUR[B.tur]; B.sec=sec?sec.map(c=>c.slice()):Array.from({length:T.kol||1},()=>[]);
    if(no){ const r=raceOf(B.kid), F=field(r); B.sec[0]=T.ek?unitOf(F,String(no)):[String(no)]; } }
  const bRaces=()=>{ const r=raceOf(B.kid), F=field(r), r2=B.tur==="cifte"?nextRace(r):null, F2=r2?field(r2):null; return {r,F,r2,F2}; };
  function bCalc(){ const {r,F,r2,F2}=bRaces(), T=TUR[B.tur];
    if(B.tur==="altili"){ const L=altOf(r); const X=L.find(z=>z.id===B.alt)||L[0]; if(!X) return {err:"6'lı bulunamadı"}; B.alt=X.id; const S=X.seviyeler[B.sev]; return {X,S,komb:S?S.kombinasyon:0,p:S?S.p:0,err:S?"":"Kapsam yok"}; }
    const R=calcF(B.tur,B.sec,F,F2); let err="";
    if(T.tek&&!B.sec[0].length) err="Bir at seç";
    else if(B.tur==="ikili"&&B.sec[0].length<2) err="En az 2 at seç";
    else if(B.tur==="cifte"){ if(!B.sec[0].length) err=`${r.kosu}. koşu için at seç`; else if(!B.sec[1].length) err=`${r.kosu+1}. koşu için at seç`; }
    else if(T.kol>1){ const i=B.sec.findIndex(c=>!c.length); if(i>=0) err=`${i+1}. sıra için at seç`; else if(!R.komb) err="Geçerli kombinasyon yok: aynı at iki sırada"; }
    if(!err&&R.komb>5000) err=`${fN(R.komb)} kombinasyon çok fazla; en çok 5.000`;
    return Object.assign(R,{err,F,F2,r,r2}); }
  function gridHtml(F,cols,title,sub){ const T=TUR[B.tur], k=cols.length, U=unitsOf(F), ekOf=no=>{ const u=U.find(x=>x.includes(no)&&x.length>1); return u?U.filter(x=>x.length>1).indexOf(u)+1:0; };
    const dense=k>=3||(B.tur!=="cifte"&&TUR[B.tur].kol>=3);
    return `<div class="atk-g${dense?" dense":""}" style="--atk-cols:repeat(${k},38px)">${title?`<div class="atk-gt">${title}${sub?`<small>${sub}</small>`:""}</div>`:""}
      <div class="atk-hr hd"><span>No</span><span>At</span><span>%</span>${cols.map(ci=>`<span>${esc(T.lbl[ci]||"Seç")}</span>`).join("")}</div>
      ${F.H.map(h=>{ const e=ekOf(h.no); return `<div class="atk-hr${h.off?" off":""}"><span class="at-no">${esc(h.no)}</span><span class="atk-hn"><b>${esc(h.ad)}${e?`<i class="atk-ek" title="Eküri">E${U.filter(x=>x.length>1).length>1?e:""}</i>`:""}</b><small>${h.off?"oranı yok · koşmayabilir":esc([h.jokey,h.oran?"oran "+(+h.oran).toFixed(2).replace(".",","):null].filter(Boolean).join(" · "))}</small></span><span class="atk-hp">${h.off?"–":fP(h.p).replace("%","")}</span>
        ${cols.map(ci=>`<button type="button" class="atk-c" data-b="c" data-ci="${ci}" data-no="${esc(h.no)}" aria-pressed="${(B.sec[ci]||[]).includes(h.no)}" ${h.off?"disabled":""} aria-label="${esc(h.no)} ${esc(h.ad)} · ${esc(T.lbl[ci]==="Seç"?"seç":T.lbl[ci]+" sıra")}">${(B.sec[ci]||[]).includes(h.no)?"✓":esc(T.lbl[ci]==="Seç"?"":T.lbl[ci].replace(".",""))}</button>`).join("")}</div>`; }).join("")}</div>`; }
  function liveHtml(){ const R=bCalc(), T=TUR[B.tur];
    if(B.tur==="altili"){ const X=R.X, S=R.S; if(!X) return `<p class="atk-kar">${esc(R.err)}</p>`;
      return `<div class="atk-kpi"><div><small>Kombinasyon</small><b>${fN(R.komb)}</b></div><div class="gd"><small>6'yı birden tutma</small><b>${fP(R.p)}</b></div></div>
        <p class="atk-src">${X.kaynak==="oran"?"💹 Oranla güncel":"Sabah tahmini"} · ayaklar bağımsız sayılır, ayak olasılıkları çarpılır.</p>${KAR?`<p class="atk-kar">📊 ${karLine("altili",R.komb)}</p>`:""}`; }
    const {F}=R, sg=suggest(B.tur,F,R.F2), same=sg&&JSON.stringify(sg.sec.map(c=>c.slice().sort()))===JSON.stringify(B.sec.map(c=>c.slice().sort()));
    const sgT=sg?sg.sec.map((c,i)=>c.join(B.tur==="ikili"?" – ":", ")).join(B.tur==="cifte"?" / ":" → "):"";
    const one=T.tek&&B.sec[0].length?F.H.find(h=>h.no===B.sec[0][0]):null;
    return `<div class="atk-kpi"><div><small>Kombinasyon</small><b>${fN(R.komb)}</b></div><div class="gd"><small>Tutma olasılığı</small><b>${R.komb?fP(R.p):"–"}</b></div></div>
      <p class="atk-src">${F.oranli?`💹 Oranla güncel olasılık (p_oran${F.up?", "+esc(F.up):""})`:"Sabah tahmini olasılığı (p_kazanma; oran henüz yok)"}${T.kol>1||B.tur==="plase"||B.tur==="ikili"?` · indirimli Harville γ ${R.gd[0].toLocaleString("tr-TR")}, δ ${R.gd[1].toLocaleString("tr-TR")}`:""}${one&&one.oran&&B.tur==="ganyan"?` · piyasa oranı ${(+one.oran).toFixed(2).replace(".",",")} (bilgi)`:""}</p>
      ${sg?`<div class="atk-rec${same?" same":""}"><span>${same?"✓ Seçimin OXXai önerisiyle aynı":"OXXai önerisi"}: <b>${esc(sgT)}</b> · ${fP(sg.p)}</span>${same?"":`<button type="button" data-b="rec">Önerileni uygula</button>`}</div>`:""}
      ${KAR?(()=>{ const s=karLine(B.tur,R.komb||1); return s?`<p class="atk-kar">📊 ${s}</p>`:""; })():""}`; }
  function footHtml(){ const R=bCalc(), c=B.tgt?KX.L.find(x=>x.id===B.tgt):atAct(false);
    const lbl=R.err?esc(R.err):`${B.edit?"Satırı güncelle":"KUPO'ya ekle"} · ${fN(R.komb)} komb. · ${fP(R.p)}`;
    return `<button type="button" class="btn" data-b="go" ${R.err?"disabled":""}>${lbl}</button>
      <button type="button" class="atk-tg" data-b="tg">${lion()}<span>${c?`Aktif KUPO: <b>${esc(c.ad)}</b> · değiştir`:`Yeni KUPO açılır: <b>At KUPO'su ${nextAtNo()}</b>`}</span></button>`; }
  function paintB(full){ if(!B||!B.el) return; const box=B.el.firstElementChild, {r,F}=bRaces(), T=TUR[B.tur];
    if(B.pick){ const L=openAts(), c0=B.tgt||(atAct(false)||{}).id;
      box.innerHTML=`<div class="gr"></div><div class="atk-hd"><div><h3>Hangi at KUPO'suna?</h3><p>At KUPO'ları futbol KUPO'larından ayrıdır.</p></div><button type="button" class="atk-x" data-b="pickx" aria-label="Geri">‹</button></div>
        <div class="atk-pick" style="margin-top:10px"><div class="ls">${L.map(c=>`<button type="button" data-b="pk" data-id="${c.id}"><span>${esc(c.ad)}<small>${c.at.length} satır${c.at.length?` · OXXai ${fP(c.at.reduce((a,x)=>a*(x.p||0),1))}`:""}${c.id===c0?" · seçili":""}</small></span>${c.id===c0?"<i>●</i>":""}</button>`).join("")}
        <button type="button" data-b="pk" data-id="new"><span>＋ Yeni at KUPO'su<small>At KUPO'su ${nextAtNo()} olarak açılır</small></span></button></div></div>
        <button type="button" class="btn ghost" data-b="pickx" style="width:100%;margin:6px 0 16px">Vazgeç</button>`; return; }
    if(full||!box.querySelector(".atk-live")){
      const tabs=ORDER.map(t=>{ const er=elig(t,r,F); return `<button type="button" data-b="t" data-t="${t}" aria-pressed="${t===B.tur}" ${er?`aria-disabled="true" data-er="${esc(er)}"`:""}>${esc(TUR[t].ad)}</button>`; }).join("");
      let body="";
      if(B.tur==="altili"){ const L=altOf(r), R=bCalc(), X=R.X, S=R.S;
        body=`${L.length>1?`<div class="atk-sev">${L.map(z=>`<button type="button" data-b="alt" data-id="${esc(z.id)}" aria-pressed="${z.id===B.alt}">${z.no}. 6'lı</button>`).join("")}</div>`:""}
          <div class="atk-sev" role="group" aria-label="Kapsam">${[["dar","Dar"],["orta","Orta"],["genis","Geniş"]].map(([k,l])=>`<button type="button" data-b="sev" data-sev="${k}" aria-pressed="${k===B.sev}">${l}</button>`).join("")}</div>
          ${S?`<div class="atk-al">${S.ayaklar.map((g,i)=>`<div class="al-a"><span class="al-i">${i+1}.<small>${esc(g.saat||"")}</small></span><span class="al-s">${g.secim.map(no=>{ const hh=(g.atlar||[]).find(x=>String(x[0])===String(no)); return `<span class="al-h">${esc(no)}${hh?` ${esc(String(hh[1]).slice(0,12))}`:""}</span>`; }).join("")}${g.banko?`<em class="al-b">🥇 tek at</em>`:""}</span><span class="al-p">%${Math.round(g.p_ayak*100)}</span></div>`).join("")}</div>`:""}`; }
      else if(B.tur==="cifte"){ const R=bCalc(); body=gridHtml(F,[0],`${r.kosu}. koşu`,esc(r.saat||""))+(R.F2?gridHtml(R.F2,[1],`${R.r2.kosu}. koşu · sonraki`,esc(R.r2.saat||"")+(R.F2.oranli?" · 💹 oranla":"")):""); }
      else body=gridHtml(F,[...Array(T.kol).keys()]);
      box.innerHTML=`<div class="gr"></div><div class="atk-hd"><div><h3>${HORSE}${esc(r.hipodrom)} · ${r.kosu}. koşu</h3><p>${esc(A().dLbl(dayOf(r.kosu_id)))} ${esc(r.saat||"")} · ${esc([r.mesafe?r.mesafe+" m":"",r.pist].filter(Boolean).join(" "))}${F.oranli?` · <b>oranla güncel</b>`:" · sabah tahmini"}</p></div><button type="button" class="atk-x" data-b="x" aria-label="Kapat">✕</button></div>
        <div class="atk-tur" role="group" aria-label="Tahmin türü">${tabs}</div>
        <p class="atk-kural"><b>${esc(TUR[B.tur].kisa.charAt(0).toLocaleUpperCase("tr")+TUR[B.tur].kisa.slice(1))}.</b> ${esc(TUR[B.tur].ip||"Kapsamı seç; 6'lı tek dokunuşla KUPO'ya eklenir")}${TUR[B.tur].ek&&F.ek.length?" · Ekürili atlar (E) tek seçim sayılır.":""}</p>
        ${body}<div class="atk-live" aria-live="polite">${liveHtml()}</div><div class="atk-ft">${footHtml()}</div>`;
      const pr=box.querySelector(".atk-tur [aria-pressed=true]"); if(pr) try{ pr.scrollIntoView({inline:"nearest",block:"nearest"}); }catch(e){}
      return; }
    box.querySelectorAll(".atk-c").forEach(b=>{ const on=(B.sec[+b.dataset.ci]||[]).includes(b.dataset.no), lb=TUR[B.tur].lbl[+b.dataset.ci]; if(b.getAttribute("aria-pressed")!==String(on)){ b.setAttribute("aria-pressed",on); b.textContent=on?"✓":(lb==="Seç"?"":lb.replace(".","")); } });
    box.querySelector(".atk-live").innerHTML=liveHtml(); box.querySelector(".atk-ft").innerHTML=footHtml(); }
  function onB(e){ if(e.target===B.el){ closeB(); return; } const b=e.target.closest("[data-b]"); if(!b) return; e.stopPropagation(); const a=b.dataset.b; try{ buzz(6); }catch(_){}
    const {r,F}=bRaces(), T=TUR[B.tur];
    if(a==="x"){ closeB(); return; }
    if(a==="t"){ if(b.dataset.er){ toast(b.dataset.er); return; } if(B.tur===b.dataset.t) return; B.tur=b.dataset.t; lsS(LSTUR,B.tur); const keep=(B.sec[0]||[]).slice(0,1); resetSec(null); if(keep.length&&B.tur!=="altili") B.sec[0]=TUR[B.tur].ek?unitOf(F,keep[0]):keep; try{ Sound.tap(); }catch(_){} paintB(true); return; }
    if(a==="c"){ const ci=+b.dataset.ci, no=b.dataset.no, G=B.tur==="cifte"&&ci===1?bRaces().F2:F, unit=T.ek?unitOf(G,no):[no], cur=B.sec[ci]||(B.sec[ci]=[]), on=cur.includes(no);
      if(T.tek) B.sec[ci]=on?[]:unit.slice(); else B.sec[ci]=on?cur.filter(x=>!unit.includes(x)):[...new Set(cur.concat(unit))];
      paintB(false); return; }
    if(a==="rec"){ const sg=suggest(B.tur,F,bRaces().F2); if(sg){ B.sec=sg.sec.map(c=>c.slice()); while(B.sec.length<(T.kol||1)) B.sec.push([]); paintB(false); toast("OXXai önerisi uygulandı"); } return; }
    if(a==="sev"){ B.sev=b.dataset.sev; paintB(true); return; }
    if(a==="alt"){ B.alt=b.dataset.id; paintB(true); return; }
    if(a==="tg"){ B.pick=true; paintB(true); return; }
    if(a==="pickx"){ B.pick=false; paintB(true); return; }
    if(a==="pk"){ let c; if(b.dataset.id==="new"){ c=newAt(); save(c); } else c=KX.L.find(x=>x.id===b.dataset.id); if(c) B.tgt=c.id; B.pick=false; paintB(true); return; }
    if(a==="go"){ const R=bCalc(); if(R.err){ toast(R.err); return; } const c=(B.tgt&&KX.L.find(x=>x.id===B.tgt&&x.durum==="acik"))||atAct(true);
      let row; if(B.tur==="altili") row=altRow(dayOf(r.kosu_id),R.X,B.sev); else row=mkRow(B.tur,r,B.sec,F,R.F2);
      if(B.edit) row.id=B.edit; if(addRow(row,c)) closeB(); return; } }
  document.addEventListener("keydown",e=>{ if(e.key==="Escape"&&$("atkSheet")) closeB(); });
  window.atkOpen=openB;
  // ---------- OXXai: "at kuponu", "ikili öner", "üçlü öner", "bugün çifte" ----------
  const NZ=t=>A().NZ(t);
  const RX_ATK=/\bat kupon\w*/, FUT=/\b(kupon\w*|liste\w*|mac\w*|futbol|basket\w*|iddaa|lig\w*|sans\w*|skor\w*)\b/;
  const RX_TUR=[["sirali_ikili",/\bsirali ikili\b/],["tabela",/\btabela\b/],["uclu",/\b(sirali )?uclu( ganyan)?\b/],["ikili",/\bikili\b/],["cifte",/\bcifte\b/],["plase",/\b(plase|derece)\b/],["ganyan",/\b(ganyan|kazanan)\b/]];
  const RX_ON=/\b(oner\w*|tahmin\w*|kur\w*|yap\w*|ver\w*|getir\w*|hangi\w*|bugun\w*|yarin\w*|en iyi|en olasi|ne oynay\w*|ne yapay\w*|kombinasyon\w*)\b/;
  let PEND=[];
  async function ensureAt(){ for(let i=0;i<40&&A().AT.busy;i++) await new Promise(r=>setTimeout(r,150)); if(!A().AT.days.length) await A().load(); await karne(); return A().AT.d?A().AT.data[A().AT.d]:null; }
  function pickRaces(D,n){ let R=(D.kosular||[]).filter(r=>!started(r)); const v=A().VEN.find(x=>n.includes(x)); if(v) R=R.filter(r=>NZ(r.hipodrom).includes(v));
    const km=n.match(/\b(\d{1,2})\s*\.?\s*(?:kosu|ayak)/); if(km) R=R.filter(r=>r.kosu===+km[1]); return {R,v,km}; }
  function rowTxt(x){ return x.sec.map((c,i)=>c.map(no=>`${no} ${nmOf(x,x.tur==="cifte"?i:0,no)}`.trim()).join(x.tur==="ikili"?" – ":", ")).join(x.tur==="cifte"?" / ":" → "); }
  async function atBot(raw){ const n=NZ(raw); if(!n) return null;
    const hit=RX_TUR.find(([,rx])=>rx.test(n)); const isAtK=RX_ATK.test(n);
    if(!isAtK&&!hit) return null;
    if(!isAtK){ if(hit[0]==="ganyan"&&/\b(6 ?li|altili)\b/.test(n)) return null; if(FUT.test(n)) return null; if(!RX_ON.test(n)&&!/\b(at|kosu\w*|hipodrom)\b/.test(n)&&!A().VEN.some(v=>n.includes(v))) return null; }
    const D=await ensureAt(); if(!D) return {html:"🐎 Bugün için kilitli at yarışı tahmini henüz yok. Laboratuvar her sabah 05:23 ve öğlen 12:23'te yeni programı işler.",chips:["At bölümünü aç"]};
    const day=A().dLbl(A().AT.d);
    if(isAtK&&!hit){ const c=atAct(false);
      if(/\byeni\b/.test(n)){ const nc=newAt(); setActive(nc); PEND=[]; return {html:`🏆 Yeni at KUPO'su açtım: <b>${esc(nc.ad)}</b>. At Yarışı'nda koşu kartındaki ＋ KUPO ile satır ekleyebilir ya da "ikili öner" diyebilirsin.`,chips:["İkili öner","Bugün çifte","At bölümünü aç"]}; }
      if(c&&c.at.length&&!/\b(oner\w*|kur\w*|yap\w*|hazirla\w*)\b/.test(n)){ const p=c.at.reduce((a,x)=>a*(x.p||0),1);
        return {html:`🏆 <b>${esc(c.ad)}</b> · ${c.at.length} satır · ${fN(c.at.reduce((a,x)=>a+(+x.komb||0),0))} kombinasyon · birlikte tutma olasılığı <b>${fP(p)}</b> · ${ST[stAt(c)]}<ul class="bt-ul">${c.at.map(x=>`<li>${esc(x.hip)} ${x.kosu}. koşu · ${esc(TUR[x.tur].ad)}: ${esc(rowTxt(x))} · OXXai ${fP(x.p)}${x.ok===true?" ✓":x.ok===false?" ✗":""}</li>`).join("")}</ul><small>Hobi amaçlı olasılıktır · 18+</small>`,chips:["At KUPO'mu aç","İkili öner","Bugün çifte"]}; }
      // öneri: başlamamış koşulardan modelin en emin olduğu 3 ganyan
      const C=(D.kosular||[]).filter(r=>!started(r)).map(r=>{ const F=field(r), sg=suggest("ganyan",F); return sg?{r,F,sg}:null; }).filter(Boolean).sort((a,b)=>b.sg.p-a.sg.p).slice(0,3);
      if(!C.length) return {html:`🐎 ${esc(day)} başlamamış koşu kalmadı; at KUPO'su için yarının programını bekleyelim.`,chips:["At bölümünü aç"]};
      PEND=C.map(x=>mkRow("ganyan",x.r,x.sg.sec,x.F)); const p=PEND.reduce((a,x)=>a*x.p,1);
      return {html:`🐎 <b>At KUPO'su önerisi</b> · ${esc(day)}, modelin en emin olduğu ${PEND.length} koşu (Kazanan):<ul class="bt-ul">${PEND.map(x=>`<li>${esc(x.hip)} ${x.kosu}. koşu ${esc(x.saat)} · <b>${esc(rowTxt(x))}</b> · ${fP(x.p)}</li>`).join("")}</ul>Üçü birden tutma olasılığı <b>${fP(p)}</b>.${KAR?`<br><small>📊 ${karLine("ganyan",1)}</small>`:""}<br><small>Hobi amaçlı olasılıktır, garanti değildir · 18+</small>`,chips:["🐎 KUPO'ya ekle","İkili öner","Bugün çifte"]}; }
    const t=hit[0], T=TUR[t]; const {R}=pickRaces(D,n);
    const C=R.map(r=>{ const F=field(r); if(elig(t,r,F)) return null; const r2=t==="cifte"?nextRace(r):null, F2=r2?field(r2):null; const sg=suggest(t,F,F2); return sg?{r,F,F2,sg}:null; }).filter(Boolean).sort((a,b)=>b.sg.p-a.sg.p);
    if(!C.length) return {html:`🐎 ${esc(day)} ${esc(T.ad)} için uygun, başlamamış koşu bulamadım${T.enaz>2?` (${T.ad} en az ${T.enaz} atlı koşuda açılır)`:""}.`,chips:["At bölümünü aç","At kazanan öner"]};
    const x=C[0], row=mkRow(t,x.r,x.sg.sec,x.F,x.F2); PEND=[row];
    const alt=C.slice(1,3).map(y=>{ const z=mkRow(t,y.r,y.sg.sec,y.F,y.F2); return `${esc(z.hip)} ${z.kosu}. koşu: ${esc(z.sec.map(c=>c.join(t==="ikili"?"–":",")).join(t==="cifte"?" / ":"→"))} ${fP(z.p)}`; });
    const nxt={ganyan:"At derece öner",plase:"At ikili öner",ikili:"At sıralı ikili öner",sirali_ikili:"At üçlü öner",uclu:"At tabela öner",tabela:"Bugün çifte",cifte:"İkili öner"}[t];
    return {html:`🐎 <b>${esc(T.ad)} önerisi</b> · ${esc(day)} ${esc(row.hip)} ${t==="cifte"?`${row.kosu}. + ${row.kosu+1}. koşu`:`${row.kosu}. koşu`} (${esc(row.saat)})<br><b>${esc(rowTxt(row))}</b> · ${esc(T.kisa)} · tutma olasılığı <b>${fP(row.p)}</b>${alt.length?`<br><small>Diğer adaylar: ${alt.join(" · ")}</small>`:""}${KAR?`<br><small>📊 ${karLine(t,1)}</small>`:""}<br><small>${row.pk==="oran"?"Oranla güncel olasılık":"Sabah tahmini (oran henüz yok)"}; garanti değildir · 18+</small>`,chips:["🐎 KUPO'ya ekle",nxt,"At KUPO'mu aç"]}; }
  if(typeof botAnswer==="function"){ const _ba=botAnswer; botAnswer=async function(raw){ try{ const r=await atBot(raw); if(r) return r; }catch(e){ console.error(e); }
      const R=await _ba.apply(this,arguments);
      try{ if(R&&typeof R==="object"&&typeof R.html==="string"){
          // 6'lı cevabı: tek dokunuşla KUPO'ya ekle
          if(/^🎯 /.test(R.html)&&/6'lı (ganyan|tahmin)/.test(R.html)){ const d=A().AT.d, Al=(A().AT.alt||{})[d], sv=A().AT.sev||"orta", v=A().VEN.find(x=>NZ(raw).includes(x));
            const X=((Al&&Al.altililar)||[]).filter(X=>!v||NZ(X.hipodrom).includes(v)).find(X=>{ const r=raceOf(`${d}/${X.hipodrom}/${X.baslangic_kosu}`); return r&&!started(r); });
            if(X){ PEND=[altRow(d,X,sv)]; R.chips=["🐎 6'lıyı KUPO'ya ekle",...(R.chips||[])]; } }
          // "kuponlarım": at kuponlarını doğru say
          for(const c of KX.L.filter(isAt)){ const rx=new RegExp(`(<b>${esc(c.ad).replace(/[.*+?^${}()|[\]\\]/g,"\\$&")}</b>(?: \\(aktif\\))?) · 0 maç`); R.html=R.html.replace(rx,`$1 · 🐎 ${c.at.length} at satırı${c.at.length?` · OXXai ${fP(c.at.reduce((a,x)=>a*(x.p||0),1))} · ${ST[stAt(c)]}`:""}`); } } }catch(e){}
      return R; }; }
  document.addEventListener("click",e=>{ const b=e.target.closest("#botChips button[data-q]"); if(!b) return; const t=b.dataset.q;
    if(t==="🐎 KUPO'ya ekle"||t==="🐎 6'lıyı KUPO'ya ekle"){ e.preventDefault(); e.stopPropagation(); try{ buzz(8); }catch(_){}
      const L=PEND.filter(Boolean); if(!L.length){ toast("Eklenecek öneri kalmadı; yeniden sor"); return; } const c=atAct(true); let k=0; for(const x of L){ x.id=uid(); if(addRow(Object.assign({},x),c)) k++; } PEND=[];
      try{ botPush("bot",k?`✓ ${k} satır eklendi: <b>${esc(c.ad)}</b> · ${c.at.length} satır · birlikte tutma olasılığı <b>${fP(c.at.reduce((a,x)=>a*(x.p||0),1))}</b>`:"Koşu başladığı için eklenemedi."); botChips(["At KUPO'mu aç","İkili öner","Bugün çifte"]); }catch(_){} return; }
    if(t==="At KUPO'mu aç"){ e.preventDefault(); e.stopPropagation(); const c=atAct(true); setActive(c); try{ botThen(()=>window.kxOpen("cp")); }catch(_){ window.kxOpen("cp"); } } },true);
  // ilk boyama + tek seferlik sonuç kontrolü (yüklenmemiş günler)
  karne(); setTimeout(()=>{ gradeAll(); fetchDays(); },6000);
  document.querySelector('nav.tabs button[data-v="kupon"]')&&document.querySelector('nav.tabs button[data-v="kupon"]').addEventListener("click",()=>setTimeout(()=>{ karne().then(decorate); fetchDays(); gradeAll(); },60));
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: atkupon-v98 */
