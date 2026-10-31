/* id: canli-gt-v107 */ try {
// =====================================================================
// v107 · CANLI GÜNCEL TAHMİN + İSTATİSTİK AYARI (tek doğruluk kaynağı: window.liveProbs)
// • Canlı maç penceresinde "↻ Güncel tahmin": iddaa canlı (skor, dakika, kart, oran) + ESPN maç istatistikleri
//   (isabetli şut, şut, topa sahip olma, korner) yeniden çekilir; MS 1/X/2, sıradaki gol, kalan sürede gol (0,5/1,5 Üst),
//   canlı Alt/Üst çizgisi ve KG için "önceki → şimdi" ve kısa gerekçe gösterilir.
// • İstatistik ayarı: kalan süre gol beklentileri (LH, LA) log-ölçekte sınırlı katsayıyla eğilir (her takımda en çok ±%25,
//   varsayılan κ=0,5 → tipik etki birkaç puan). Formül ve kaynaklar: scripts/canli_istat.py (sunucu aynı formülü kullanır,
//   ayarlı/ayarsız olasılığı data/archive/live_stats/ altına kaydeder; lab/canli_istat_lab.py kapıdan geçince κ'yı günceller).
// • Tek kaynak: idlPred artık liveProbs'tur → maç penceresi, Seçenekler, Power Now, KUPO "OXXai şimdi", OXXai sohbeti aynı sayıyı
//   görür. Gösterilen yüzde her yerde liveShown = liveCal(liveProbs) (KUPO/Power Now/öneri kartıyla aynı düzeltme).
//   Kırmızı kart artık MS ve sıradaki gole de uygulanır (önceden yalnız Alt/Üst'te; toplayıcı live_pred ile aynı hale geldi).
// • İstek birleştirme: ESPN özet isteği ui-v92 fetch birleştirmesinden geçer; ayrıca maç başına tek uçuş + 20 sn kilit;
//   iddaa yüklemesi 5 sn içinde yapılmışsa tekrar edilmez; ESPN skor tablosu yalnız eşleşme yoksa (90 sn'de bir) yenilenir.
// =====================================================================
(function(){
  "use strict";
  if(typeof idlPred!=="function"||typeof fbRemShare!=="function") return;
  const DEF={kappa:.5,b_sot:.6,b_sh:.3,b_pos:.1,b_tempo:.12,cap:Math.log(1.25),k_info:6,t_full:30,tempo_ref:.27,max_age:900e3};
  const C=Object.assign({src:"varsayılan"},DEF);
  try{ fetch("data/canli_istat.json",{cache:"no-cache"}).then(r=>r.ok?r.json():null).then(j=>{ if(!j||!j.kabul) return; const k=+j.kappa; if(isFinite(k)&&k>=0&&k<=1.5){ C.kappa=k; C.src="lab"; } }).catch(()=>{}); }catch(e){}
  const _base=idlPred;   // eski fonksiyon (karşılaştırma ve geri dönüş için saklanır)

  // ---------- canlı güç modeli (CG) · scripts/canli_guc.py ile BİREBİR; data/canli_guc.json → kullan=true ise açılır ----------
  // Kalan gol ~ Negatif Binom (Gamma-Poisson): maçta atılan gol takım gücünü Bayes yoluyla günceller; skor durumu, kırmızı kart,
  // uzatmalı kalan süre. Parametreler lab/canli_guc_lab.py'nin zaman sıralı kapısından gelir. Kapalıysa eski yol aynen çalışır.
  const GDEF={s:1,h1:.4437,xi:1,e1:3,e2:3,rmin:1,a:8,g_tr:.1,g_trl:0,g_ld:-.1,g_lv:-.1,rc_own:.72,rc_opp:1.25,nmax:10,g_l2:0,g_ldl:0};   // v136: g_l2/g_ldl geç dakika (nötr 0)
  const G={on:false,P:null,cal:null,src:"eski"};
  try{ fetch("data/canli_guc.json",{cache:"no-cache"}).then(r=>r.ok?r.json():null).then(j=>{ if(!j||j.kullan!==true||!j.params) return;
      const P=Object.assign({},GDEF); for(const k of Object.keys(GDEF)){ const v=+j.params[k]; if(j.params[k]!=null&&isFinite(v)) P[k]=v; }
      if(!(P.s>0&&P.a>0&&P.h1>.3&&P.h1<.6&&Math.abs(P.xi)<2&&P.nmax>=6&&P.nmax<=15)) return;
      const k=j.kal; G.cal=k&&isFinite(+k.a)&&isFinite(+k.b)?{a:+k.a,b:+k.b}:null; G.P=P; G.on=true; G.src="canli_guc"; SHOWN.clear(); }).catch(()=>{}); }catch(e){}
  const gF=(u,xi)=>u+xi*(u*u-u)/2;
  function cgRem(t,pd,P){ const h1=P.h1; if(pd===0) return 1-h1; if(pd==null) pd=t<45?1:2;
    if(pd===1){ const a=Math.max(0,t), r=t<45?(45-t)+P.e1:Math.max(P.e1-(t-45),P.rmin); return (1-gF(a/(a+r),P.xi))*h1+(1-h1); }
    const a=Math.max(0,t-45), r=t<90?(90-t)+P.e2:Math.max(P.e2-(t-90),P.rmin); return Math.max(.004,(1-gF(a/(a+r),P.xi))*(1-h1)); }
  function cgLams(lh,la,hs,as,t,rc,pd,P){ const rem=cgRem(t,pd,P), el=Math.max(0,1-rem), d=hs-as, late=Math.min(1,Math.max(0,(t-60)/30));
    const kL=Math.exp((P.g_l2||0)*Math.min(1,Math.max(0,(t-70)/15)));
    const st=dd=>t<15?1:dd<0?Math.exp(P.g_tr+P.g_trl*late):dd>0?Math.exp(P.g_ld+(P.g_ldl||0)*late):Math.exp(P.g_lv);
    const a=P.a, s=P.s, r0=(rc&&rc[0])||0, r1=(rc&&rc[1])||0;
    const kH=Math.pow(P.rc_own,r0)*Math.pow(P.rc_opp,r1), kA=Math.pow(P.rc_own,r1)*Math.pow(P.rc_opp,r0);
    const bH=(a+hs)/(a+s*lh*el), bA=(a+as)/(a+s*la*el);
    return [s*lh*rem*st(d)*kH*bH*kL, s*la*rem*st(-d)*kA*bA*kL, a+hs, a+as]; }
  function nbV(mu,r,K){ const q=r/(r+mu), u=mu/(r+mu), o=[Math.pow(q,r)]; for(let k=0;k<K;k++) o.push(o[k]*(k+r)/(k+1)*u); const z=o.reduce((s,x)=>s+x,0); return o.map(x=>x/z); }
  const pdM=m=>{ try{ return window.CDR&&CDR.pdOf?CDR.pdOf(m):null; }catch(e){ return null; } };

  // ---------- çekirdek: skor/zaman/kart modeli + isteğe bağlı istatistik çarpanı ----------
  function lamOf(m){ let L=IDL.lam[String(m.id)], src="iddaa";
    if(!L){ const f=(typeof FIXTURES!=="undefined"?FIXTURES:[]).find(x=>x.iid===m.id); if(f){ try{ const p=quickPred({lg:f.lg,h:f.h,a:f.a},f); if(p&&p.lh!=null) L=[p.lh,p.la]; src="model"; }catch(e){} } }
    if(!L){ try{ const q=typeof window.lvOranL==="function"?window.lvOranL(m):null; if(q){ L=q; src="canli-oran"; } }catch(e){} }   // v133
    if(!L){ L=[1.45,1.15]; src="ort"; } return {L,src}; }
  function tOf(m){ const s=idlSecs(m); return s==null?(m.h1!=null?46:30):Math.min(120,s/60); }
  function core(m,mH,mA){
    const {L,src}=lamOf(m); if(L[0]==null||L[1]==null) return null;
    const t=tOf(m), hs=+m.hs||0, as=+m.as||0, rc=m.rc||[0,0];
    const cg=G.on&&G.P?cgLams(L[0],L[1],hs,as,t,rc,pdM(m),G.P):null;
    let LH0,LA0;
    if(cg){ LH0=cg[0]; LA0=cg[1]; }
    else{ const rem=fbRemShare(t,m), d=hs-as, st=t>=15?1:0, up=Math.exp(.1), dn=Math.exp(-.1);   // v117: devre bilgisi (m.st) iletilir
      LH0=L[0]*rem*(st?(d<0?up:dn):1)*Math.pow(.72,rc[0]||0)*Math.pow(1.25,rc[1]||0);
      LA0=L[1]*rem*(st?(d>0?up:dn):1)*Math.pow(.72,rc[1]||0)*Math.pow(1.25,rc[0]||0); }
    const K=cg?G.P.nmax:8, LH=LH0*mH, LA=LA0*mA, PH=cg?nbV(LH,cg[2],K):poisV(LH,8), PA=cg?nbV(LA,cg[3],K):poisV(LA,8), TT=new Array(2*K+1).fill(0);
    let H=0,D=0,A=0,best={p:-1},more=0,kg=0;
    for(let i=0;i<=K;i++) for(let j=0;j<=K;j++){ const p=PH[i]*PA[j], fH=hs+i, fA=as+j; TT[i+j]+=p;
      if(fH>fA)H+=p; else if(fH===fA)D+=p; else A+=p; if(p>best.p) best={p,s:fH+"-"+fA}; if(fH+fA>2) more+=p; if(fH>0&&fA>0) kg+=p; }
    const z=H+D+A, p0=cg?PH[0]*PA[0]:Math.exp(-(LH+LA)), tot=hs+as, ou=m.odds&&m.odds.ou, line=ou?ou.l:tot+.5;
    const cgOver=need=>need<=0?1:Math.max(0,1-TT.slice(0,need).reduce((s,x)=>s+x,0));      // kalan gol ≥ need
    const out={H:H/z,D:D/z,A:A/z,ft:best.s,ftp:best.p/z,nextH:(1-p0)*LH/(LH+LA||1),nextA:(1-p0)*LA/(LH+LA||1),none:p0,o25:more/z,t,
      line,pOver:cg?cgOver(Math.floor(line)-tot+1):1-poisCdf(Math.floor(line)-tot,LH+LA),src,
      LH,LA,LH0,LA0,L,kg:kg/z,r05:1-p0,r15:cg?cgOver(2):1-poisCdf(1,LH+LA),model:cg?"cg":"eski"};
    if(cg&&window.CPH&&CPH.H.on){ try{ CPH.apply(out,m); }catch(e){} }    // v144 YH-10: canlı piyasa harmanı (bayrak kapalıyken etkisiz)
    return out; }

  // ---------- istatistik deposu (maç başına; oturum boyunca saklanır) ----------
  const SK="bx-cgt-v107", ST=new Map();
  try{ const o=JSON.parse(sessionStorage.getItem(SK)||"{}"); for(const [k,v] of Object.entries(o)) if(v&&v.at&&Date.now()-v.at<3*3600e3) ST.set(k,v); }catch(e){}
  function persist(){ try{ const o={}; for(const [k,v] of ST) if(v.at&&Date.now()-v.at<3*3600e3) o[k]={at:v.at,st:v.st,ev:v.ev,lg:v.lg,hist:(v.hist||[]).slice(-10)}; sessionStorage.setItem(SK,JSON.stringify(o)); }catch(e){} }
  function fresh(m){ const E=ST.get(String(m.id)); return E&&E.st&&Date.now()-E.at<=C.max_age?E:null; }
  function recentPrev(E,t){ let p=null; for(const h of (E.hist||[])){ const dt=t-h.t; if(dt>=8&&dt<=20&&(!p||h.t<p.t)) p=h; } return p; }
  const pay=(x,y)=>(x+1)/(x+y+2);
  // scripts/canli_istat.py → feats() ile birebir aynı
  function feats(st,prev,L,t){
    const e=L[0]/(L[0]+L[1]); let ds=null,dh=null,dp=null,info=0,rate=null;
    if(st.sot){ ds=pay(st.sot[0],st.sot[1])-e; info+=st.sot[0]+st.sot[1]; }
    if(prev&&st.sot&&prev.sot){ const a=st.sot[0]-prev.sot[0], b=st.sot[1]-prev.sot[1]; if(a>=0&&b>=0&&a+b>=2){ const dr=pay(a,b)-e; ds=ds==null?dr:.6*ds+.4*dr; } }
    if(st.sh){ dh=pay(st.sh[0],st.sh[1])-e; info+=.35*(st.sh[0]+st.sh[1]); if(t>=20) rate=(st.sh[0]+st.sh[1])/Math.max(t,1); }
    if(st.pos&&st.pos[0]+st.pos[1]>0) dp=st.pos[0]/(st.pos[0]+st.pos[1])-(.5+.5*(e-.5));
    const w=info/(info+C.k_info), wt=Math.min(1,t/C.t_full);
    const tl=rate!=null?Math.max(-.7,Math.min(.7,Math.log(Math.max(rate,1e-3)/C.tempo_ref))):0;
    return {ds,dh,dp,w,wt,tl}; }
  function multOf(F){ const s=C.kappa*F.w*F.wt*(C.b_sot*(F.ds||0)+C.b_sh*(F.dh||0)+C.b_pos*(F.dp||0)), g=C.kappa*F.wt*C.b_tempo*F.tl;
    const cl=x=>Math.max(-C.cap,Math.min(C.cap,x)); return {mH:Math.exp(cl(s+g)),mA:Math.exp(cl(-s+g)),s,g}; }

  // ---------- gösterilen yüzde: grup tutarlı canlı düzeltme ----------
  // liveCal (Platt / kova) en olası seçimlerin geçmiş isabetinden öğrenildi. Her seçeneğe ayrı ayrı uygulanınca 1/X/2 toplamı
  // %100'ü aşıyordu (ör. 0-0'da %42/%40/%36). Artık: grubun en olası seçeneği eskisi gibi liveCal ile düzeltilir, kalan olasılık
  // diğerlerine model oranında dağıtılır (1/X/2, sıradaki gol); iki yönlü pazarlarda (Alt/Üst, KG, başka gol) tümleyen alınır.
  // liveCal sarılır: aynı ham olasılık hangi ekrandan gelirse gelsin (pencere, Power Now, KUPO, sohbet) aynı yüzdeye döner.
  const _lc=liveCal, SHOWN=new Map();
  // CG açıkken kendi kalibrasyonu (kal yoksa olasılık olduğu gibi: CG zaman sıralı sınamada Platt'sız daha iyi çıktı); kapalıyken eski liveCal
  const cgCal=p=>{ if(!G.cal||!(p>0&&p<1)) return {p}; const x=Math.log(p/(1-p)); return {p:1/(1+Math.exp(-(G.cal.a+G.cal.b*x)))}; };
  const baseCal=p=>{ try{ return G.on?cgCal(p):(_lc(p)||{p}); }catch(e){ return {p}; } };
  function put(raw,o){ if(raw==null||!isFinite(raw)) return; SHOWN.delete(raw); SHOWN.set(raw,o); }
  function pair(a){ if(a==null||!isFinite(a)) return null; const b=1-a, hi=a>=b?a:b, lo=a>=b?b:a, o=baseCal(hi), v=Math.min(.99,o.p); put(hi,o); put(lo,{p:1-v}); return a>=b?v:1-v; }
  function tri(xs,fixed){ // fixed: [indeks, gösterilen değer] (sıradaki gol üçlüsünde "gol olmaz" ikiliden gelir)
    let bi, bv;
    if(fixed){ bi=fixed[0]; bv=fixed[1]; } else { bi=xs.indexOf(Math.max(...xs)); const o=baseCal(xs[bi]); bv=Math.min(.99,o.p); put(xs[bi],o); }
    const rest=xs.reduce((s,x,i)=>i===bi?s:s+x,0);
    xs.forEach((x,i)=>{ if(i!==bi) put(x,{p:rest>0?(1-bv)*x/rest:(1-bv)/(xs.length-1)}); }); }
  function reg(P){ try{ if(!P) return; tri([P.H,P.D,P.A]); const gn=pair(P.none); if(gn!=null) tri([P.nextH,P.none,P.nextA],[1,gn]);
      pair(P.pOver); pair(P.kg); pair(P.r15);
      if(SHOWN.size>20000){ let n=SHOWN.size-15000; for(const k of SHOWN.keys()){ SHOWN.delete(k); if(--n<=0) break; } } }catch(e){} }
  liveCal=function(p){ const v=SHOWN.get(p); return v?v:G.on?baseCal(p):_lc.apply(this,arguments); };
  // ---------- TEK DOĞRULUK KAYNAĞI ----------
  function liveProbs(m){
    if(!m||m.sp!==1) return null;
    let base=null; try{ base=core(m,1,1); }catch(e){ base=null; }
    if(!base){ try{ return _base(m); }catch(e){ return null; } }
    base.adj=null;
    const E=fresh(m); if(!E){ reg(base); return base; }
    const prev=recentPrev(E,base.t), F=feats(E.st,prev&&prev.st,base.L,base.t), M=multOf(F);
    const P=core(m,M.mH,M.mA); if(!P){ reg(base); return base; }
    P.adj={mH:M.mH,mA:M.mA,F,at:E.at,st:E.st,prev:prev?{t:prev.t,st:prev.st}:null,kappa:C.kappa}; P.raw=base; reg(P); return P; }
  function calP(p){ try{ return typeof liveCal==="function"?Math.min(.99,liveCal(p).p):p; }catch(e){ return p; } }
  function rawOf(P,k){ if(!P) return null; const L=String(P.line);
    const T={"1":P.H,"X":P.D,"2":P.A,G1:P.nextH,G2:P.nextA,G0:P.none,GG:1-P.none,R05:P.r05,R15:P.r15,KGV:P.kg,KGY:1-P.kg,U:P.pOver,A:1-P.pOver};
    if(k in T) return T[k]; if(k==="U"+L) return P.pOver; if(k==="A"+L) return 1-P.pOver; return null; }
  function liveShown(m,k){ const P=liveProbs(m); const r=rawOf(P,k); return r==null?null:calP(r); }
  idlPred=liveProbs;                       // tüm eski çağıranlar (pencere, Seçenekler, Power Now, KUPO, OXXai) aynı kaynağa bağlanır
  window.liveProbs=liveProbs; window.liveShown=liveShown; window.liveProbsBase=m=>{ try{ return core(m,1,1); }catch(e){ return null; } };
  window.CGT={C,ST,feats,multOf,core,G,cgLams,nbV,cgRem};

  // ---------- ESPN eşleşme + istatistik ----------
  let plAt=0;
  function espnFind(m){ const pool=[]; try{ pool.push(...Object.values(Live.events()||{})); }catch(e){} try{ pool.push(...Object.values(Pick.extra||{})); }catch(e){}
    const c=pool.filter(e=>e&&e.state!=="post"&&ESPN[e.lg]&&Math.abs(Date.parse(e.date)-m.ts)<6*3600e3&&tmEq(e.h,m.h)&&tmEq(e.a,m.a));
    return c.find(e=>e.state==="in")||c[0]||null; }
  const num=v=>{ const x=parseFloat(String(v==null?"":v).replace(",",".").replace("%","")); return isFinite(x)?x:null; };
  function statsOf(a){ const o={}; (a||[]).forEach(s=>{ if(s&&s.name) o[s.name]=num(s.displayValue!=null?s.displayValue:s.value); }); return o; }
  function parseStats(j){
    if(!j||typeof j!=="object") return null;
    const comp=j.header&&j.header.competitions&&j.header.competitions[0], cs=(comp&&comp.competitors)||[];
    const hc=cs.find(c=>c.homeAway==="home"), ac=cs.find(c=>c.homeAway==="away");
    const hid=hc&&hc.team&&String(hc.team.id), aid=ac&&ac.team&&String(ac.team.id);
    let H=null,A=null;
    for(const t of ((j.boxscore&&j.boxscore.teams)||[])){ const id=t.team&&String(t.team.id), side=t.homeAway||(id&&id===hid?"home":id&&id===aid?"away":null);
      if(side==="home") H=statsOf(t.statistics); else if(side==="away") A=statsOf(t.statistics); }
    if((!H||!A)&&hc&&ac&&hc.statistics&&ac.statistics){ H=statsOf(hc.statistics); A=statsOf(ac.statistics); }
    if(!H||!A) return null;
    const pr=(k,f)=>H[k]!=null&&A[k]!=null?[f(H[k]),f(A[k])]:null, I=x=>Math.max(0,Math.round(x)), R=x=>Math.round(x*10)/10;
    const st={sot:pr("shotsOnTarget",I),sh:pr("totalShots",I),pos:pr("possessionPct",R),co:pr("wonCorners",I)};
    Object.keys(st).forEach(k=>{ if(!st[k]) delete st[k]; });
    if(st.sot&&st.sh&&(st.sot[0]>st.sh[0]||st.sot[1]>st.sh[1])) delete st.sh;          // tutarsız veri: şut sayısını kullanma
    return st.sot||st.sh?st:null; }
  async function loadStats(m){
    const id=String(m.id), E=ST.get(id)||{hist:[]};
    let ev=espnFind(m);
    if(!ev&&Date.now()-plAt>90e3){ plAt=Date.now(); try{ await Pick.loadEspn(); }catch(e){} ev=espnFind(m); }
    if(!ev) return {ok:false,why:"maç ESPN akışında bulunamadı"};
    let j=null; try{ const r=await fetch(`https://site.api.espn.com/apis/site/v2/sports/soccer/${ESPN[ev.lg]}/summary?event=${encodeURIComponent(ev.id)}`,{cache:"no-store"}); j=r&&r.ok?await r.json():null; }catch(e){ j=null; }
    const st=parseStats(j);
    if(!st) return {ok:false,why:j?"ESPN bu maç için istatistik vermiyor":"ESPN'e şu an ulaşılamadı"};
    const t=tOf(m); E.at=Date.now(); E.st=st; E.ev=ev.id; E.lg=ev.lg; E.hist=(E.hist||[]).filter(h=>h.t<t-.5).concat([{at:E.at,t,st}]).slice(-10);
    ST.set(id,E); persist(); return {ok:true}; }

  // ---------- önceki → şimdi ----------
  const RES={}, BASE={}, BUSY={}, LOCK={};
  // ham model değerleri saklanır; gösterimde ikisi de aynı anki düzeltmeyle (liveCal) yüzdeye çevrilir
  function snap(m){ const P=liveProbs(m); if(!P) return null; const v=k=>rawOf(P,k);
    return {at:Date.now(),t:P.t,hs:m.hs,as:m.as,line:P.line,H:v("1"),D:v("X"),A:v("2"),nH:v("G1"),nA:v("G2"),r05:v("R05"),r15:v("R15"),ov:v("U"+P.line),kg:v("KGV"),
      LH:P.LH,LA:P.LA,adj:P.adj?{mH:P.adj.mH,mA:P.adj.mA}:null}; }
  const f1=x=>(Math.round(x*10)/10).toLocaleString("tr-TR",{minimumFractionDigits:1,maximumFractionDigits:1});
  const remMin=t=>Math.max(1,Math.round((t<=90?90:120)-t));
  function reasons(m,P,pv0){
    const H=shortTeam(m.h), A=shortTeam(m.a), o={ms:"",gol:"",ou:"",gen:[]};
    const a=P&&P.adj, rm=remMin(P.t);
    o.gen.push(`Skor ${m.hs}-${m.as}, kalan yaklaşık ${rm} dk`);
    if((m.rc||[])[0]||(m.rc||[])[1]) o.gen.push(`kırmızı kart ${m.rc[0]||0}-${m.rc[1]||0} hesaba katıldı`);
    if(a){ const st=a.st, pv=a.prev;
      if(pv&&pv.st&&pv.st.sot&&st.sot){ const x=st.sot[0]-pv.st.sot[0], y=st.sot[1]-pv.st.sot[1], dt=Math.round(P.t-pv.t);
        if(x>=0&&y>=0&&Math.max(x,y)>=2&&x!==y) o.gen.push(`${x>y?H:A} son ${dt} dk'da ${Math.max(x,y)} isabetli şut (rakip ${Math.min(x,y)}), baskı arttı`); }
      const parts=[]; if(st.sot) parts.push(`isabetli şut ${st.sot[0]}-${st.sot[1]}`); if(st.sh) parts.push(`şut ${st.sh[0]}-${st.sh[1]}`); if(st.pos) parts.push(`topa sahip olma %${Math.round(st.pos[0])}-%${Math.round(st.pos[1])}`); if(st.co) parts.push(`korner ${st.co[0]}-${st.co[1]}`);
      if(parts.length) o.gen.push("İstatistik: "+parts.join(", "));
      const dH=Math.round((a.mH-1)*100), dA=Math.round((a.mA-1)*100), sg=x=>(x>0?"+":x<0?"−":"±")+Math.abs(x);
      o.ms=Math.abs(dH-dA)>=2?`${dH>dA?H:A} istatistikte üstün; gol beklentisi ayarı ${H} ${sg(dH)}%, ${A} ${sg(dA)}%`:`İstatistik dengeli (ayar ${H} ${sg(dH)}%, ${A} ${sg(dA)}%); skor ve kalan süre belirleyici`; }
    else o.ms=`Skor ${m.hs}-${m.as} ve kalan ~${rm} dk belirleyici`;
    if(pv0&&pv0.t!=null){ const dt=Math.round(P.t-pv0.t), g=(m.hs+m.as)-((pv0.hs||0)+(pv0.as||0));
      if(g>0) o.ms+=` · son güncellemeden beri ${g} gol oldu`; else if(dt>=3) o.ms+=` · ${dt} dk geçti, gol yok: süre azaldıkça mevcut skorun olasılığı artar`; }
    o.gol=`Kalan sürede beklenen gol ${f1(P.LH+P.LA)} (${H} ${f1(P.LH)} · ${A} ${f1(P.LA)})`;
    const need=Math.floor(P.line)-(m.hs+m.as)+1;
    o.ou=`${lnF(P.line)} çizgisi için ${need} gol daha gerekli`+((m.hs>0&&m.as>0)?" · iki takım da gol attı, KG kesinleşti":m.hs>0?` · KG için ${A} gol bulmalı`:m.as>0?` · KG için ${H} gol bulmalı`:" · iki takım da henüz gol atmadı");
    return o; }

  async function refresh(){
    const lv0=MS.live; if(!lv0||lv0.sp!==1) return; const id=String(lv0.id);
    if(BUSY[id]) return BUSY[id];
    if(LOCK[id]&&Date.now()-LOCK[id]<20e3&&RES[id]){ toast("Az önce güncellendi · birkaç saniye sonra tekrar dene"); return; }
    const run=(async()=>{
      paintBusy(true);
      const prev=(RES[id]&&RES[id].now)||BASE[id]||snap(lv0);
      try{ if(Date.now()-(IDL.at[1]||0)>5000){ for(let i=0;i<20&&IDL.busy&&IDL.busy[1];i++) await new Promise(r=>setTimeout(r,150)); if(Date.now()-(IDL.at[1]||0)>5000) await IDL.load(1,true); } }catch(e){}
      const m=(IDL.byId[1]&&IDL.byId[1][lv0.id])||lv0;
      let S={ok:false,why:"istatistik yok"}; try{ S=await loadStats(m); }catch(e){}
      if(MS.live&&String(MS.live.id)===id){ MS.live=m; if(MS.m&&MS.m.sp) MS.m=m; }
      const P=liveProbs(m), now=snap(m);
      RES[id]={at:Date.now(),prev,now,why:P?reasons(m,P,prev):null,stats:S.ok,miss:S.ok?"":S.why,clock:(()=>{ try{ return idlClockTxt(m); }catch(e){ return ""; } })()};
      LOCK[id]=Date.now();
      try{ buzz(8); }catch(e){}
      if(MS.m&&MS.live&&String(MS.live.id)===id){ const el=$("msheet"), sc=el?el.scrollTop:0; msRender(); if(el) el.scrollTop=sc; }
      try{ if(window.kxLiveDeco) window.kxLiveDeco(); }catch(e){}
      try{ const v=$("v-power"); if(v&&!v.hidden&&typeof renderPower==="function") renderPower(); }catch(e){}
      try{ const bd=$("pwBadge"); if(bd&&typeof pwLiveCands==="function"){ const n=pwLiveCands().length; bd.hidden=!n; bd.textContent=n; } }catch(e){}
    })();
    BUSY[id]=run; try{ await run; } finally{ delete BUSY[id]; paintBusy(false); } }
  function paintBusy(on){ const b=document.querySelector("#msheet .cgt-btn"); if(b){ b.setAttribute("aria-busy",on?"true":"false"); b.disabled=!!on; const t=b.querySelector(".cgt-tx"); if(t) t.textContent=on?"Güncelleniyor…":"Güncel tahmin"; } }
  const hms=t=>{ try{ return ist(new Date(t),{hour:"2-digit",minute:"2-digit",second:"2-digit"}); }catch(e){ return ""; } };
  function cell(a,b,line0,line1){ a=a==null?null:calP(a); b=b==null?null:calP(b); const pc=x=>x==null?"–":"%"+pc9(x);
    if(a==null||(line0!=null&&line1!=null&&line0!==line1)) return `<span class="cgt-v">${a==null?"–":pc(a)} <i class="eq">→</i> <b>${pc(b)}</b></span>`;
    const d=Math.round(b*100)-Math.round(a*100), cls=d>0?"up":d<0?"dn":"eq", ar=d>0?"▲":d<0?"▼":"=";
    return `<span class="cgt-v">${pc(a)} <i class="${cls}" aria-hidden="true">${ar}</i> <b>${pc(b)}</b></span>`; }
  function cardHtml(lv){
    const id=String(lv.id), R=RES[id], H=shortTeam(lv.h), A=shortTeam(lv.a), E=fresh(lv);
    const at=R?`Son güncelleme <b>${esc(hms(R.at))}</b>${R.clock?` · ${esc(R.clock)}`:""}${R.stats?(E?" · istatistikli":" · istatistik 15 dk'dan eski"):""}`
      :`Canlı veri <b>${esc(hms(lv.got||IDL.at[1]||Date.now()))}</b> · skor, dakika ve kart; istatistik için dokun`;
    let h=`<section class="cgt" aria-label="Güncel canlı tahmin"><div class="cgt-top"><button type="button" class="cgt-btn" aria-busy="false"><span class="cgt-ic" aria-hidden="true">↻</span><span class="cgt-tx">Güncel tahmin</span></button><span class="cgt-at" aria-live="polite">${at}</span></div>`;
    if(R&&R.now&&MS.tab==="tahmin"){ const p=R.prev||{}, n=R.now, w=R.why||{gen:[]};
      const row=(lab,a,b,l0,l1)=>`<div class="cgt-r"><span>${esc(lab)}</span>${cell(a,b,l0,l1)}</div>`;
      h+=`<div class="cgt-res">
        <div class="cgt-g"><h5>Maç sonucu</h5>${row("MS 1 · "+H,p.H,n.H)}${row("MS X",p.D,n.D)}${row("MS 2 · "+A,p.A,n.A)}<p class="cgt-why">${esc(w.ms||"")}</p></div>
        <div class="cgt-g"><h5>Gol</h5>${row("Sıradaki gol · "+H,p.nH,n.nH)}${row("Sıradaki gol · "+A,p.nA,n.nA)}${row("Kalan sürede gol (0,5 Üst)",p.r05,n.r05)}${row("Kalan sürede 1,5 Üst",p.r15,n.r15)}<p class="cgt-why">${esc(w.gol||"")}</p></div>
        <div class="cgt-g"><h5>Alt / Üst · KG</h5>${row(`Canlı ${lnF(n.line)} Üst`+(p.line!=null&&p.line!==n.line?` (önce ${lnF(p.line)})`:""),p.ov,n.ov,p.line,n.line)}${row("KG Var",p.kg,n.kg)}<p class="cgt-why">${esc(w.ou||"")}</p></div>
        <p class="cgt-why">${esc(w.gen.join(" · "))}.</p>
        ${R.stats?`<p class="cgt-note">Kaynak: iddaa canlı bülteni (skor, dakika, kart, oran) + ESPN maç istatistikleri. İstatistik ayarı ölçülüdür (κ ${String(C.kappa).replace(".",",")}, takım başına en çok ±%25); ${G.on?"yüzdeler canlı güç modeliyle (geçmiş canlı maçlardan öğrenildi) hesaplanmıştır":"yüzdeler geçmiş canlı isabete göre düzeltilmiştir"}.</p>`
          :`<p class="cgt-note warn">İstatistik yok: ${esc(R.miss||"veri alınamadı")}. Tahmin skor, dakika ve kart modeliyle güncellendi.</p>`}
      </div>`; }
    return h+`</section>`; }
  function infoHtml(lv){ const P=liveProbs(lv); if(!P) return "";
    const r=(n,s,k)=>{ const v=calP(rawOf(P,k)); return `<div class="cgt-r"><span>${esc(n)}${s?`<small>${esc(s)}</small>`:""}</span><span class="cgt-v"><b>%${pc9(v)}</b></span></div>`; };
    return `<div class="mg cgt-info"><h4>Diğer canlı olasılıklar (bilgi)</h4>${r("KG Var","iki takım da gol atar","KGV")}${r("Kalan sürede gol (0,5 Üst)","maçta en az bir gol daha","R05")}${r("Kalan sürede 1,5 Üst","en az iki gol daha","R15")}${r("Sıradaki gol · "+shortTeam(lv.h),"","G1")}${r("Sıradaki gol · "+shortTeam(lv.a),"","G2")}</div>`; }
  // pencere kutularında gösterilen yüzde = liveShown (KUPO / Power Now / öneri kartıyla aynı)
  function calPatch(el){
    el.querySelectorAll(".ms-body .mo[data-p]:not([data-cal])").forEach(b=>{ const p=+b.dataset.p; if(!isFinite(p)) return; const cp=calP(p); b.dataset.cal="1"; if(Math.abs(cp-p)<1e-9) return;
      b.dataset.p=String(cp); const sm=b.querySelector("small"), fairB=b.hasAttribute("data-fair");
      if(sm) sm.textContent=`%${pc9(cp)}${fairB?" · adil":""}`;
      if(fairB){ const bb=b.querySelector("b"); if(bb&&cp>0.005){ bb.textContent=fO(1/cp); b.dataset.o=(1/cp).toFixed(2); } }
      b.classList.remove("t2","t3"); const t=ptier(cp); if(t) b.classList.add(t);
      const o=+b.dataset.o; b.classList.toggle("val",!fairB&&o>0&&cp*o>1.08);
      const n=b.querySelector(".mo-n"); if(n){ const tx=n.textContent.replace(/^🔥\s*/,""); n.textContent=(t==="t3"?"🔥 ":"")+tx; } });
    el.querySelectorAll(".ms-body .ms-big>div").forEach(d=>{ const s=(d.querySelector("small")||{}).textContent||"", b=d.querySelector("b"); if(!b||d.dataset.cal) return; const P=liveProbs(MS.live); if(!P) return;
      if(/Başka gol olur/.test(s)){ b.textContent="%"+pc9(calP(1-P.none)); d.dataset.cal=1; } else if(/Başka gol olmaz/.test(s)){ b.textContent="%"+pc9(calP(P.none)); d.dataset.cal=1; } }); }
  function startedNoLive(m){ if(!m||m.sp||MS.live) return false; if(m.live||m.started) return true; const t=m.dt&&m.dt.getTime?m.dt.getTime():NaN; return isFinite(t)&&t<Date.now()-60e3&&t>Date.now()-3*3600e3; }
  function paint(){
    const el=$("msheet"), m=MS.m; if(!el||!m||el.hidden) return;
    el.querySelectorAll(".cgt,.cgt-lv,.cgt-pre,.cgt-info").forEach(x=>x.remove());
    const lv=MS.live;
    if(lv&&lv.sp===1){
      calPatch(el);
      if(MS.tab!=="form"){ const hd=el.querySelector(".ms-hd"); if(hd) hd.insertAdjacentHTML("afterend",cardHtml(lv)); const b=el.querySelector(".cgt-btn"); if(b) b.onclick=e=>{ e.stopPropagation(); try{ Sound.tap(); }catch(_){} refresh(); }; }
      if(MS.tab==="oran"){ const body=el.querySelector(".ms-body"); const P=liveProbs(lv);
        if(body){ body.insertAdjacentHTML("afterbegin",`<p class="cgt-lv"><span class="cgt-lbl">CANLI</span>Olasılıklar şu anki skor, dakika ve kartlara göre${P&&P.adj?" + maç istatistikleri":""} hesaplandı. Maç öncesi pazarlar canlıda gösterilmez.</p>`);
          const pb=body.querySelector(".oyn-bar"); const ih=infoHtml(lv); if(ih){ const last=[...body.querySelectorAll(".mg,p.note")].pop(); if(last) last.insertAdjacentHTML("afterend",ih); else body.insertAdjacentHTML("beforeend",ih); } void pb; } }
      return; }
    if(startedNoLive(m)&&MS.tab!=="form"){ const body=el.querySelector(".ms-body");
      if(body) body.insertAdjacentHTML("afterbegin",`<div class="cgt-pre" role="note"><span class="cgt-lbl pre">MAÇ ÖNCESİ</span> Maç başladı; bu maç için canlı bülten verisi yok. Aşağıdaki olasılıklar <b>maç başlamadan önceki</b> hesaptır, skoru ve dakikayı içermez.</div>`);
      const hd=el.querySelector(".pz-hd small"); if(hd&&!/maç öncesi/.test(hd.textContent)) hd.textContent+=" · maç öncesi"; }
  }
  try{ const _mr=msRender; msRender=function(){ const r=_mr.apply(this,arguments); try{ paint(); }catch(e){ console.warn("canli-gt-v107",e); } return r; }; }catch(e){}
  try{ const _om=openMatch; openMatch=function(m,tab){ const r=_om.apply(this,arguments); try{ if(MS.live&&MS.live.sp===1){ const id=String(MS.live.id); if(!RES[id]) BASE[id]=snap(MS.live); } }catch(e){} return r; }; }catch(e){}
  window.cgtRefresh=refresh;
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: canli-gt-v107 */
/* id: canli-dr-v117 */ try {
// =====================================================================
// v117 · CANLI KALAN SÜRE MODELİ (uzatma dakikası + artan gol yoğunluğu) — sunucuyla tek kaynak
// • Formül scripts/canli_istat.py → rem_share() ile BİREBİR aynı; toplayıcı (collector.live_pred) da onu kullanır.
// • Parametreler tek kaynaktan: data/daily.json → canli.zaman. Toplayıcının zaman sıralı kapısı (maç-blok bootstrap %95 GA
//   sıfırı dışlamalı) kabul etmedikçe eski doğrusal model kullanılır; kabulde sunucu ve uygulama aynı anda geçer.
// • Her durumda geçerli düzeltmeler: 90+X dakikada formül artık uzatma devresine (120) düşmez; devre arası (iddaa s=49)
//   ikinci yarının tamamı kalmış sayılır; ilk yarı uzatması (s=2, 45+X) ikinci yarı sanılmaz (v117 modelinde).
// • v117 modeli: devre 45+e dk (e1, e2 beklenen uzatma; uzatma başladıysa kalan = max(e − geçen, rmin)); yarı içinde gol
//   yoğunluğu λ(u) ∝ 1 + ξ(u − ½) (Dixon & Robinson 1998). Kalan pay 1 − F(u), F(u) = u + ξ(u² − u)/2; yarı payları h1 / 1 − h1.
// =====================================================================
(function(){
  "use strict";
  if(typeof fbRemShare!=="function") return;
  const ZDEF={v:117,e1:3,e2:3,xi:1,rmin:1};          // canli_istat.ZDEF ile aynı
  function zaman(){ try{ const z=DAILY&&DAILY.canli&&DAILY.canli.zaman; if(!z||!z.kabul) return null; const Z=Object.assign({},ZDEF);
      for(const k of ["e1","e2","xi","rmin"]) if(typeof z[k]==="number"&&isFinite(z[k])) Z[k]=z[k]; return Z; }catch(e){ return null; } }
  // devre: 1 ilk yarı, 2 ikinci yarı, 0 devre arası, null bilinmiyor (iddaa s: 2 / 3 / 49)
  function pdOf(c){ if(c==null) return null; if(typeof c==="number") return c; if(typeof c!=="object") return null;
    if(c.pd!=null) return c.pd; if(c.sp!==1) return null; return c.st===2?1:c.st===3?2:c.st===49?0:null; }
  const F=(u,xi)=>u+xi*(u*u-u)/2;
  function remShare(t,ctx,Zo){
    const h1=(typeof MODEL!=="undefined"&&MODEL&&MODEL.params&&MODEL.params.h1)||.4428;
    let pd=pdOf(ctx); const Z=Zo===undefined?zaman():Zo;
    if(pd===0) return 1-h1;                                    // devre arası
    if(!Z){ if(t<45) return (45-t)/45*h1+(1-h1); return Math.max(.012,(90-t)/45*(1-h1)); }   // eski model (90+ hatası düzeltildi)
    if(pd==null) pd=t<45?1:2;
    const e1=Z.e1, e2=Z.e2, xi=Z.xi, rmin=Z.rmin;
    if(pd===1){ const a=Math.max(0,t), r=t<45?(45-t)+e1:Math.max(e1-(t-45),rmin); return (1-F(a/(a+r),xi))*h1+(1-h1); }
    const a=Math.max(0,t-45), r=t<90?(90-t)+e2:Math.max(e2-(t-90),rmin); return Math.max(.004,(1-F(a/(a+r),xi))*(1-h1)); }
  fbRemShare=remShare;                                         // eski fbLive / idlPred / canli-gt-v107 core aynı kaynağa bağlanır
  // ESPN saati: "90'+3'" → 93 (eskiden 90'da kalıyordu); "45'+2'" belirsiz (devre arası olabilir) → 45 kalır
  try{ const _fm=fbMinute; fbMinute=function(clock,detail){ const r=_fm.apply(this,arguments);
      if(r===90){ const m=String(clock||"").match(/^\s*90'?\s*\+\s*(\d+)/); if(m) return 90+Math.min(15,+m[1]); } return r; }; }catch(e){}
  window.CDR={ZDEF,zaman,pdOf,remShare};
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: canli-dr-v117 */
/* id: oxx-kupon-v110 */ try {
// =====================================================================
// v110 · OXXai'nin KUPO'ları (sözleşme: lab/OXX_KUPON.md). Arayüz yalnız OKUR; data/ dosyalarına yazmaz.
// • KUPO › Kuponlarım üstünde #oxkBox: gün seçici, kilitli futbol+basket kuponları (strateji adı, bacaklar, kilit, OXXai olasılığı,
//   toplam oran, canlı durum), "Kopyala → kuponuma" (KX deposuna yeni kupon + kxAdd; kullanıcı verisi yalnız localStorage).
//   Bacak sonucu dosyada varsa o; yoksa uygulamanın sonuç verisi (RS.load / BK canlı) + mkHit.
// • Karne: strateji başına CANLI ve GERİYE DÖNÜK ayrı satır (kupon, tutan, beklenen, bacak isabeti) + son öğrenme olayları.
// • At kuponları futbol listesine karışmaz: window.oxxAtKartHtml() bağımsız kart; At › Kupon sekmesi çizilince #at2Box sonuna
//   ince kanca (MutationObserver) ile eklenir; #at2Box yoksa sessizce atlanır.
// • OXXai sohbeti: "oxx kuponları", "bugün ne oynadın", "oxx karnesi" → kısa cevap + KUPO'ya yönlendirme.
// =====================================================================
(function(){
  const NOW=()=>Date.now(), $$=id=>document.getElementById(id);
  const E=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const today=()=>{ try{ return istDay(new Date()); }catch(e){ return new Date().toISOString().slice(0,10); } };
  const addD=(d,k)=>{ const t=new Date(Date.parse(d+"T12:00:00Z")+k*864e5); return t.toISOString().slice(0,10); };
  const pct=p=>p==null||isNaN(p)?"–":(p>0&&p<.1?(p*100).toLocaleString("tr-TR",{maximumFractionDigits:1}):String(Math.round(p*100)));
  const f2=x=>x==null||isNaN(x)?"–":(+x).toLocaleString("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2});
  const f1=x=>x==null||isNaN(x)?"–":(+x).toLocaleString("tr-TR",{maximumFractionDigits:1});
  const tU=s=>{ if(!s) return 0; const t=Date.parse(String(s).replace(/Z?$/,"Z").replace(/ZZ$/,"Z")); return isNaN(t)?0:t; };
  const hm=t=>{ try{ return ist(new Date(t),{hour:"2-digit",minute:"2-digit"}); }catch(e){ return ""; } };
  const dLbl=d=>{ const t=today(); if(d===t) return "Bugün"; if(d===addD(t,-1)) return "Dün"; if(d===addD(t,1)) return "Yarın";
    try{ return new Date(d+"T12:00:00Z").toLocaleDateString("tr-TR",{day:"numeric",month:"long",weekday:"short",timeZone:"UTC"}); }catch(e){ return d; } };
  const dKisa=d=>{ try{ return new Date(d+"T12:00:00Z").toLocaleDateString("tr-TR",{day:"numeric",month:"short",timeZone:"UTC"}); }catch(e){ return d; } };
  const AD={fb_altin:"Altın",fb_70:"%70+",fb_3lu:"En olası 3'lü",fb_deger:"Değer",fb_guvenli:"Güvenli",bk_en_olasi:"Basket en olası",
    at_altin:"Altın atlar",at_sirali_ikili:"Sıralı ikili",at_ikili:"İkili",at_cifte:"Çifte",at_altili_dar:"6'lı dar (64)",at_altili_orta:"6'lı orta (192)",at_altili_genis:"6'lı geniş (576)"};
  const ACK={fb_altin:"oxx'in en güvendiği, oranı makul maçlar",fb_70:"birlikte tutma olasılığı ≥ %70",fb_3lu:"günün en olası 3 seçimi",fb_deger:"olasılık × oran en yüksek",fb_guvenli:"yeni pazarlarda ≥ %80 seçimler",bk_en_olasi:"basketin en olası seçimleri"};
  const SIRA=["fb_altin","fb_70","fb_3lu","fb_deger","fb_guvenli","bk_en_olasi"], SIRA_AT=["at_altin","at_sirali_ikili","at_ikili","at_cifte","at_altili_dar","at_altili_orta","at_altili_genis"];
  const ad=s=>AD[s]||s;
  // ---------- veri (yalnız okuma; 5 dk bellek önbelleği) ----------
  const C=new Map();
  function j(url,ttl){ const c=C.get(url); if(c&&(c.p||NOW()-c.at<(ttl||300e3))) return c.p||Promise.resolve(c.v);
    const p=fetch(url,{cache:"no-cache"}).then(r=>r.ok?r.json():null).catch(()=>null).then(v=>{ C.set(url,{at:NOW(),v}); return v; }); C.set(url,{at:NOW(),p}); return p; }
  const peek=url=>{ const c=C.get(url); return c&&!c.p?c.v:undefined; };
  const U={gun:d=>`data/oxx_kupon/${d}.json`, at:d=>`data/oxx_kupon/at/${d}.json`, karne:"data/oxx_karne.json", gunluk:"data/ogrenme_gunlugu.json", ayar:"data/oxx_ayar.json", rb:"data/oxx_rollback.json"};
  const S={d:null, tab:"gun", acik:true, atAll:{}};
  try{ const v=localStorage.getItem("bx-oxk"); if(v){ const o=JSON.parse(v); if(o&&o.acik===false) S.acik=false; if(o&&o.tab==="karne") S.tab="karne"; } }catch(e){}
  const saveUI=()=>{ try{ localStorage.setItem("bx-oxk",JSON.stringify({acik:S.acik,tab:S.tab})); }catch(e){} };
  // ---------- bacak / kupon durumu ----------
  const RSV={};   // gün → RS.load sonucu (uygulamanın sonuç önbelleği)
  let gradeAt=0;
  function fbRes(l){ const d=(()=>{ try{ return istDay(new Date(tU(l.bas_utc))); }catch(e){ return null; } })(); const R=d&&RSV[d];
    if(!R||!R.list) return null; const m=(l.iid&&R.list.find(x=>x.id===l.iid))||R.list.find(x=>{ try{ return tmEq(x.h,l.h)&&tmEq(x.a,l.a); }catch(e){ return false; } });
    return m||null; }
  function fbLive(l){ try{ const L=typeof IDL!=="undefined"&&IDL.live&&IDL.live[1]||[]; return (l.iid&&L.find(x=>x.id===l.iid))||L.find(x=>tmEq(x.h,l.h)&&tmEq(x.a,l.a))||null; }catch(e){ return null; } }
  function bkF(l){ try{ return (BK.data&&BK.data.fixtures||[]).find(x=>x.h===l.h&&x.a===l.a)||null; }catch(e){ return null; } }
  // s: g tuttu · x tutmadı · l sürüyor · w bekliyor · q sonuç bekleniyor (maç bitti, sonuç yok) ; sc: skor metni
  function legSt(l,sp){ if(l.tuttu===true) return {s:"g",sc:l.sonuc||""}; if(l.tuttu===false) return {s:"x",sc:l.sonuc||""};
    const t0=tU(l.bas_utc), now=NOW(); if(!t0||t0>now) return {s:"w"};
    if(sp==="bk"){ const f=bkF(l); let lv=null; try{ lv=f&&bkLiveOf(f); }catch(e){}
      if(lv&&lv.state==="post"&&lv.hs!=null){ const ok=mkHit(l.kod,+lv.hs,+lv.as,null,null,null); return {s:ok===true?"g":ok===false?"x":"q",sc:`${lv.hs}-${lv.as}`}; }
      if(lv&&lv.state==="in") return {s:"l",sc:lv.hs!=null?`${lv.hs}-${lv.as}`:""};
      return {s:now-t0<3*3600e3?"l":"q"}; }
    const m=fbRes(l); if(m){ const ok=mkHit(l.kod,m.hs,m.as,m.h1,m.a1,null); return {s:ok===true?"g":ok===false?"x":"q",sc:`${m.hs}-${m.as}`}; }
    const lv=fbLive(l); if(lv) return {s:"l",sc:lv.hs!=null?`${lv.hs}-${lv.as}`:""};
    return {s:now-t0<130*60e3?"l":"q"}; }
  function kupSt(k,sp){ const L=(k.bacaklar||[]).map(l=>legSt(l,sp));
    if(k.durum==="gecersiz") return {s:"v",t:"Geçersiz",L};
    if(k.durum==="tuttu"||k.tuttu===true) return {s:"g",t:"Tuttu",L};
    if(k.durum==="tutmadi"||k.tuttu===false) return {s:"x",t:"Tutmadı",L};
    if(L.some(x=>x.s==="x")) return {s:"x",t:"Tutmadı",L};
    if(L.length&&L.every(x=>x.s==="g")) return {s:"g",t:"Tuttu",L};
    if(L.some(x=>x.s!=="w")) return {s:"l",t:"Sürüyor",L};
    return {s:"w",t:"Bekliyor",L}; }
  // Başlamış ve sonucu dosyada olmayan futbol bacakları için uygulamanın sonuç verisini (RS.load) bir kez yükle
  function needGrade(D){ if(!D||typeof RS==="undefined"||!RS.load) return; const days=new Set();
    for(const k of (D.futbol&&D.futbol.kuponlar)||[]) for(const l of k.bacaklar||[]) if(l.tuttu==null&&tU(l.bas_utc)&&NOW()-tU(l.bas_utc)>100*60e3){ try{ days.add(istDay(new Date(tU(l.bas_utc)))); }catch(e){} }
    const due=[...days].filter(d=>!RSV[d]||(d===today()&&NOW()-(RSV[d].at||0)>120e3)); if(!due.length||NOW()-gradeAt<30e3) return; gradeAt=NOW();
    Promise.all(due.slice(0,3).map(d=>RS.load(d).then(r=>{ if(r&&r.list) RSV[d]=r; }).catch(()=>{}))).then(()=>paint()); }
  // ---------- KUPO bölümü ----------
  const legHtml=(l,sp,st)=>{ const t0=tU(l.bas_utc);
    const ic=st.s==="g"?`<i class="g" role="img" aria-label="Tuttu">✓</i>`:st.s==="x"?`<i class="x" role="img" aria-label="Tutmadı">✗</i>`:st.s==="l"?`<i class="l" role="img" aria-label="Sürüyor">●</i>`:`<i role="img" aria-label="${st.s==="q"?"Sonuç bekleniyor":"Bekliyor"}">${st.s==="q"?"…":"⏳"}</i>`;
    return `<div class="oxk-l"><div class="t"><b>${sp==="bk"?"🏀 ":""}${E(l.h)} – ${E(l.a)}</b><small>${E(l.lig||"")}${t0?` · ${E(hm(t0))}`:""}</small>
      <small><em>${E(l.secim||l.kod)}</em> · OXXai %${pct(l.p)}${l.oran?` · oran ${f2(l.oran)}`:""}${l.tahmin?` · tahmin ${E(l.tahmin)}`:""}</small></div>
      <div class="r">${ic}${st.sc?`<span>${E(st.sc)}${l.iy?` <small style="color:var(--ink3)">(İY ${E(l.iy)})</small>`:""}</span>`:""}</div></div>`; };
  function kupHtml(k,sp,blk,D){ const st=kupSt(k,sp), L=k.bacaklar||[], lk=blk.kilit_tsi||D.kilit_tsi||"";
    const up=L.filter(l=>tU(l.bas_utc)>NOW()).length;
    return `<div class="oxk-c" data-oxid="${E(k.id)}"><div class="oxk-ch"><span class="oxk-nm">${E(ad(k.strateji))}</span><span class="oxk-sp">${sp==="bk"?"🏀 basket":"⚽ futbol"}</span><span class="oxk-st ${st.s}">${st.s==="g"?"✓ ":st.s==="x"?"✗ ":""}${E(st.t)}</span></div>
      <div class="oxk-mt"><span>${L.length} maç</span><span>Toplam oran <b>${k.oran?f2(k.oran):"–"}</b></span><span>OXXai <b>%${pct(k.p)}</b></span>${lk?`<span>🔒 ${E(D.geriye_donuk?"sonradan kuruldu":String(lk).slice(11,16))}</span>`:""}</div>
      ${L.map((l,i)=>legHtml(l,sp,st.L[i])).join("")}
      ${D.geriye_donuk?"":`<button type="button" class="oxk-cp" data-oxk="cp" data-id="${E(k.id)}" ${up?"":"disabled"} aria-label="${E(ad(k.strateji))} KUPO'sunu kendi KUPO'ma kopyala">${up?`⧉ KUPO'ma kopyala${up<L.length?` <small style="font-weight:500;color:var(--ink3)">(${up}/${L.length} maç)</small>`:""}`:"Maçlar başladı · kopyalanamaz"}</button>`}</div>`; }
  function gunHtml(D,d){ const t=today();
    const nav=`<div class="oxk-day"><button type="button" data-oxk="dp" aria-label="Önceki gün">‹</button><b>${E(dLbl(d))}${D&&D.geriye_donuk?`<span class="oxk-gd" title="Kilit sistemi bu gün çalışmıyordu; KUPO'lar sonradan, yalnız o günden önce bilinenle kuruldu">geriye dönük</span>`:""}<small>${E(dKisa(d))}</small></b><button type="button" data-oxk="dn" aria-label="Sonraki gün" ${d>=t?"disabled":""}>›</button></div>`;
    if(D===undefined) return nav+`<div class="oxk-emp">Yükleniyor…</div>`;
    if(!D) return nav+`<div class="oxk-emp"><b>Bu gün için OXXai KUPO'su yok</b>${d===t?"KUPO'lar gün içinde, yeterli aday maç hazır olunca kilitlenir.":"O gün kilit yapılmamış."}</div>`;
    const K=[]; for(const sp of ["futbol","basket"]){ const b=D[sp]; if(b&&Array.isArray(b.kuponlar)) for(const k of b.kuponlar) K.push([k,sp==="basket"?"bk":"fb",b]); }
    K.sort((a,b)=>SIRA.indexOf(a[0].strateji)-SIRA.indexOf(b[0].strateji));
    let h=nav;
    if(D.geriye_donuk) h+=`<p class="oxk-note"><b>Geriye dönük:</b> bu günün KUPO'ları sonradan, yalnız o günden önce bilinen bilgiyle kuruldu. Karnede canlı KUPO'lardan ayrı sayılır.</p>`;
    const fbL=D.futbol&&D.futbol.kilit_tsi;
    if(!K.length) return h+`<div class="oxk-emp"><b>Henüz kilitli KUPO yok</b>Futbol KUPO'ları günün en az 10 aday maçı hazır olunca kilitlenir; kilitten sonra değişmez.</div>`;
    h+=K.map(([k,sp,b])=>kupHtml(k,sp,b,D)).join("");
    if(!D.futbol&&d===t) h+=`<p class="oxk-note">Futbol KUPO'ları henüz kilitlenmedi.</p>`;
    if(!D.basket&&D.futbol) h+=`<p class="oxk-note">Bugün basket KUPO'su yok (en olası seçimler eşiği geçmedi ya da maç yok).</p>`;
    h+=`<p class="oxk-ft">${fbL&&!D.geriye_donuk?`Kilit ${E(String(fbL).slice(11,16))}: KUPO'lar kilitten sonra değişmez. `:""}Olasılık bacakların çarpımıdır (maçlar bağımsız sayılır). ${window.OXX_OZ&&!window.OXX_OZ.atAcik()?"":"At KUPO'ları At › KUPO sekmesinde. "}${E(D.uyari||"Hobi amaçlı · 18+")}</p>`;
    return h; }
  // karne satırı
  const ozet=(o,cls,lbl)=>{ o=o||{n:0}; const b=o.bacak||null;
    return `<span class="${cls||""}">${lbl}</span><span class="${cls||""}">${o.n||0}</span><span class="${cls||""}">${o.n?`${o.tutan}<small>%${pct(o.isabet)}</small>`:"–"}</span><span class="${cls||""}">${o.n?f1(o.beklenen):"–"}</span><span class="${cls||""}">${b&&b.n?`${b.tutan}/${b.n}<small>%${pct(b.isabet)}</small>`:"–"}</span>`; };
  function karneBlok(id,s){ return `<div class="oxk-k"><h3>${E(ad(id))}</h3><p>${E(s.ad||"")}${ACK[id]?` · ${E(ACK[id])}`:""}${s.bekleyen?` · ${s.bekleyen} KUPO sonuç bekliyor`:""}</p>
      <div class="oxk-kt" role="table" aria-label="${E(ad(id))} karnesi"><span class="h"></span><span class="h">KUPO</span><span class="h">Tutan</span><span class="h">Beklenen</span><span class="h">Bacak</span>
      ${ozet(s.canli,"","Canlı")}${ozet(s.geriye_donuk,"gdr","Geriye dönük")}</div></div>`; }
  const sayi=x=>String(x).replace(/(\d)\.(\d)/g,"$1,$2");
  function olayMetni(r){ let a=String(r.aciklama||r.anahtar||""); for(const [k,v] of Object.entries(AD)) a=a.split(k).join(v+" KUPO'su");
    a=a.replace(/\bp_min\b/g,"olasılık eşiği").replace(/\bomin\b/g,"en düşük oran").replace(/\bomax\b/g,"en yüksek oran").replace(/\bgunde\b/g,"günlük maç sayısı").replace(/^keşif:\s*/i,"Keşif denemesi: ");
    return sayi(a); }
  function olayKarar(r){ const k=String(r.karar||""), n=String(r.neden||"");
    if(/kabul/i.test(k)) return `<span class="ok">kabul edildi, uygulanıyor</span>`;
    if(/GER[İI] ALIND/i.test(k)) return `<span class="no">geri alındı</span> (kabulden sonra kötüleşti; 14 gün dondu)`;
    if(/kal[ıi]c[ıi]/i.test(k)) return `<span class="ok">kalıcı oldu</span> (14 gün sonra da iyi)`;
    if(/uzat/i.test(k)) return `yeniden sınama uzatıldı (veri az)`;
    if(/veri_yetersiz/.test(k)) return `veri yetersiz, denenemedi`;
    if(/dondur/.test(k)) return `dondurulmuş anahtar, denenmedi`;
    if(/ret/.test(k)){ const why=/Altın isabeti düştü/.test(n)?"Altın KUPO isabeti düşüyordu":/güçlü/.test(n)?"güçlü seçimlerin isabeti düşüyordu":/iyileşme yok|alt sınır/.test(n)?"sınamada anlamlı iyileşme yok":/kupon sayısı/.test(n)?"KUPO sayısı çok azalıyordu":"ölçüt geçilemedi";
      return `<span class="no">reddedildi</span>: ${why}`; }
    return E(k||"–"); }
  function olaylarHtml(G,A,R){ const ev=[];
    for(const r of (G&&G.kayitlar)||[]) ev.push({t:r.tarih||"",h:`<b>${E(olayMetni(r))}</b> → ${olayKarar(r)}`});
    for(const g of (A&&A.gecmis)||[]) if(g&&g.olay==="geri_alindi"&&!ev.some(x=>x.t===g.tarih&&/geri alındı/.test(x.h))) ev.push({t:g.tarih||"",h:`<b>${E(sayi(g.anahtar||""))}</b> → <span class="no">geri alındı</span>`});
    ev.sort((a,b)=>String(b.t).localeCompare(String(a.t)));
    let h=""; if(R&&R.aktif) h+=`<li><span class="gb">Geri alma etkin</span>${R.neden?`: ${E(R.neden)}`:""}${R.bitis?` <small>${E(R.bitis)} tarihine kadar yeni ayar kabul edilmez</small>`:""}</li>`;
    const izl=(A&&A.izlenen)||[]; if(izl.length) h+=`<li><span class="gb">İzlenen ayar</span>: ${izl.map(z=>E(sayi(`${z.anahtar||""}`))).join(", ")} <small>kabulden 14 gün sonra yeniden sınanır</small></li>`;
    h+=ev.slice(0,5).map(x=>`<li>${x.h}<small>${E(x.t?dKisa(String(x.t).slice(0,10)):"")}</small></li>`).join("");
    if(!h) h=`<li>Henüz öğrenme olayı yok.</li>`;
    const ay=A&&A.surum?`<p class="oxk-ft">Etkin ayar: <b style="color:var(--ink2)">${E(A.surum)}</b>. OXXai her gece en fazla 3 küçük ayar dener; yalnız ileriye dönük sınamada anlamlı iyileşme varsa kabul eder.</p>`:"";
    return `<div class="oxk-k"><h3>Son öğrenme olayları</h3><ul class="oxk-ev">${h}</ul>${ay}</div>`; }
  function karneHtml(K,G,A,R){ if(K===undefined) return `<div class="oxk-emp">Yükleniyor…</div>`;
    if(!K||!K.stratejiler) return `<div class="oxk-emp"><b>Karne henüz yok</b>İlk KUPO'lar sonuçlanınca burada görünür.</div>`;
    const dn=K.donem||{}, gd=dn.geriye_donuk||[], cn=dn.canli||[];
    let h=`<p class="oxk-note"><b>Canlı</b> = maçtan önce gerçekten kilitlenen KUPO'lar${cn.length?` (${E(dKisa(cn[0]))}'den beri)`:""}. <b style="color:#FFD89A">Geriye dönük</b> = kilit sistemi kurulmadan önceki günler için sonradan, yalnız o günden önce bilinenle kurulanlar${gd.length?` (${E(dKisa(gd[0]))} – ${E(dKisa(gd[1]))})`:""}. İkisi toplanmaz. <b>Beklenen</b> = OXXai olasılıklarının toplamı; iyi ayarlı robotta tutan ≈ beklenen.</p>`;
    for(const id of SIRA){ const s=K.stratejiler[id]; if(s) h+=karneBlok(id,s); }
    h+=G===undefined?`<div class="oxk-k"><h3>Son öğrenme olayları</h3><div class="oxk-emp">Yükleniyor…</div></div>`:olaylarHtml(G,A,R);
    h+=`<p class="oxk-ft">At KUPO'larının karnesi At › KUPO sekmesinde. ${E(K.uyari||"")}</p>`; return h; }
  function shell(){ const v=$$("v-kupon"); if(!v) return null; let b=$$("oxkBox");
    if(!b){ b=document.createElement("section"); b.id="oxkBox"; b.className="oxk"; b.setAttribute("aria-label","OXXai'nin KUPO'ları");
      const ch=$$("kxChips"), cb=$$("cpBox"), anc=ch||cb; if(anc) anc.before(b); else v.appendChild(b);
      b.addEventListener("click",onClick); }
    return b; }
  function paint(){ const b=shell(); if(!b) return; const tab=(typeof KP!=="undefined"&&KP.tab)||"cp"; b.hidden=tab!=="cp"; if(b.hidden) return;
    if(!S.d) S.d=today(); const d=S.d;
    const D=peek(U.gun(d)), K=peek(U.karne);
    let n=0, w=0; if(D) for(const sp of ["futbol","basket"]) for(const k of (D[sp]&&D[sp].kuponlar)||[]){ n++; const s=kupSt(k,sp==="basket"?"bk":"fb").s; if(s==="g") w++; }
    const sub=D===undefined?"yükleniyor":D?`${dLbl(d)} · ${n} KUPO${w?` · ${w} tuttu`:""}`:`${dLbl(d)} · KUPO yok`;
    let h=`<div class="oxk-hd"><span class="oxk-bdg" aria-hidden="true">OXXai</span><h2>OXXai'nin KUPO'ları<small>${E(sub)} · kendi oynadığı, kilitli</small></h2><button type="button" class="oxk-tg" data-oxk="tg" aria-expanded="${S.acik}" aria-controls="oxkBd">${S.acik?"Gizle":"Göster"}</button></div>`;
    h+=`<div class="oxk-bd" id="oxkBd"><div class="oxk-seg" role="group" aria-label="OXXai bölümü"><button type="button" data-oxk="t" data-t="gun" aria-pressed="${S.tab==="gun"}">KUPO'lar</button><button type="button" data-oxk="t" data-t="karne" aria-pressed="${S.tab==="karne"}">Karne</button></div>`;
    h+=S.tab==="karne"?karneHtml(K,peek(U.gunluk),peek(U.ayar),peek(U.rb)):gunHtml(D,d);
    h+=`</div>`;
    b.classList.toggle("min",!S.acik); b.innerHTML=h;
    // eksik veriyi getir
    const need=[]; if(D===undefined) need.push(j(U.gun(d))); if(S.tab==="karne"){ for(const u of [U.karne,U.gunluk,U.ayar,U.rb]) if(peek(u)===undefined) need.push(j(u)); } else if(K===undefined) need.push(j(U.karne));
    if(need.length) Promise.all(need).then(()=>{ if(S.d===d) paint(); });
    else if(S.acik&&S.tab==="gun") needGrade(D); }
  window.oxkPaint=paint;
  function onClick(e){ const t=e.target.closest("[data-oxk]"); if(!t) return; e.stopPropagation(); const a=t.dataset.oxk; try{ buzz(6); }catch(_){}
    if(a==="tg"){ S.acik=!S.acik; saveUI(); paint(); return; }
    if(a==="t"){ S.tab=t.dataset.t==="karne"?"karne":"gun"; S.acik=true; saveUI(); paint(); return; }
    if(a==="dp"||a==="dn"){ const nd=addD(S.d||today(),a==="dp"?-1:1); if(nd>today()) return; S.d=nd; paint(); return; }
    if(a==="cp"){ kopyala(t.dataset.id); return; } }
  // ---------- Kopyala → kuponuma: KX deposunda yeni kupon, bacaklar mevcut ekleme yolu (kxAdd) ile ----------
  function kupBul(id){ for(const [u,c] of C) if(c&&c.v&&/oxx_kupon\/\d/.test(u)) for(const sp of ["futbol","basket"]) for(const k of (c.v[sp]&&c.v[sp].kuponlar)||[]) if(k.id===id) return [k,sp==="basket"?"bk":"fb"]; return [null]; }
  function kopyala(id){ const [k,sp]=kupBul(id); if(!k) return; const KX=window.KX;
    if(!KX||!Array.isArray(KX.L)||typeof window.kxAdd!=="function"){ try{ toast("KUPO hazır değil, biraz sonra tekrar dene"); }catch(e){} return; }
    const L=(k.bacaklar||[]).filter(l=>tU(l.bas_utc)>NOW()); if(!L.length){ toast("Bu KUPO'nun maçları başladı; kopyalanamaz"); return; }
    const c={id:Date.now().toString(36)+Math.random().toString(36).slice(2,6),ad:`OXXai ${ad(k.strateji)} · ${dKisa(String(k.id).slice(0,10))}`.slice(0,32),items:[],olusturma:NOW(),durum:"acik",oxx:k.id};
    KX.L.push(c); KX.aktif=c.id; let n=0;
    for(const l of L){ try{ if(typeof MKT_N!=="undefined"&&l.kod&&!MKT_N[l.kod]&&l.secim) MKT_N[l.kod]=String(l.secim).replace(/ \((ev|dep\.?)\)$/,""); }catch(e){}
      const mm={lg:sp==="bk"?"bk-"+(l.lg||"bk"):(l.lg||"oxx"),h:l.h,a:l.a,dt:new Date(tU(l.bas_utc))};
      const ex=sp==="bk"?{sp:"bk"}:(l.iid?{iid:l.iid}:{});
      try{ if(window.kxAdd({mm,ex},{k:l.kod,n:l.secim,o:l.oran||null,p:l.p},true)) n++; }catch(e){} }
    if(!n){ const i=KX.L.indexOf(c); if(i>=0) KX.L.splice(i,1); try{ window.kxSave&&window.kxSave(); }catch(e){} toast("Kopyalanamadı"); return; }
    try{ window.kxSave&&window.kxSave(); localStorage.setItem("bx-coupon",JSON.stringify(c.items)); }catch(e){}
    toast(`${c.ad} açıldı · ${n} maç${n<(k.bacaklar||[]).length?` (${(k.bacaklar||[]).length-n} maç başladığı için eklenmedi)`:""}`);
    try{ renderKupon(); }catch(e){} try{ paintCoupon(); }catch(e){}
    setTimeout(()=>{ const cb=$$("kxChips")||$$("cpBox"); if(cb) cb.scrollIntoView({block:"start",behavior:"smooth"}); },60); }
  window.oxxKopyala=kopyala;
  // ---------- KUPO zincirleri ----------
  try{ const _rk=renderKupon; renderKupon=function(){ const r=_rk.apply(this,arguments); try{ paint(); }catch(e){ console.warn("oxx-kupon-v110",e); } return r; }; }catch(e){}
  try{ const _kt=kuponTab; kuponTab=function(){ const r=_kt.apply(this,arguments); try{ paint(); }catch(e){} return r; }; }catch(e){}
  try{ const b=document.querySelector('nav.tabs button[data-v="kupon"]'); if(b) b.addEventListener("click",()=>setTimeout(()=>{ try{ paint(); }catch(e){} },40)); }catch(e){}
  setInterval(()=>{ const v=$$("v-kupon"); if(v&&!v.hidden&&!document.hidden&&S.acik&&S.tab==="gun"&&S.d===today()){ C.delete(U.gun(S.d)); paint(); } },5*60e3);

  // =====================================================================
  // At › Kupon sekmesi: "OXXai'nin at KUPO'ları" (bağımsız kart + ince kanca)
  // =====================================================================
  const atSel=l=>{ const s=l.secim||[], a=l.adlar||[]; return s.map((no,i)=>`${no}${a[i]?" "+a[i]:""}`).join(l.tur==="sirali_ikili"?" → ":" + "); };
  function atLegSt(l){ return l.tuttu===true?"g":l.tuttu===false?"x":tU(l.bas_utc)&&tU(l.bas_utc)<NOW()?"l":"w"; }
  function atKupHtml(k){ const st=kupSt({durum:k.durum,tuttu:k.tuttu,bacaklar:[]},"at"); let s=st.s;
    const L=k.bacaklar||[];
    if(s==="w"){ if(L.some(l=>l.tuttu===false)) s="x"; else if(L.some(l=>l.tuttu!=null||atLegSt(l)==="l")) s="l"; }
    const tt={g:"✓ Tuttu",x:"✗ Tutmadı",l:"Sürüyor",w:"Bekliyor",v:"Geçersiz"}[s];
    if(/^at_altili/.test(k.strateji)){
      return `<div class="oxk-c"><div class="oxk-ch"><span class="oxk-nm">${E(k.hipodrom||"")} 6'lı</span><span class="oxk-sp">${E(ad(k.strateji))}</span><span class="oxk-st ${s}">${tt}</span></div>
        <div class="oxk-mt"><span>${E(k.kombinasyon||"–")} kombinasyon</span><span>OXXai <b>%${pct(k.p)}</b></span>${k.kilit_tsi?`<span>🔒 ${E(String(k.kilit_tsi).slice(11,16))}</span>`:""}</div>
        <div class="oxk-ay">${L.map(l=>`<span class="${l.tuttu===true?"g":l.tuttu===false?"x":""}">${E(l.kosu)}. k: ${E((l.secim||[]).join(","))}${l.tuttu===true?" ✓":l.tuttu===false?` ✗${l.kazanan?" ("+E(l.kazanan)+")":""}`:""}</span>`).join("")}</div></div>`; }
    return `<div class="oxk-c"><div class="oxk-ch"><span class="oxk-nm">${E(L[0]?`${L[0].hipodrom} ${L[0].kosu}. koşu`:"")}${k.tur==="cifte"&&L[1]?` + ${E(L[1].kosu)}.`:""}</span><span class="oxk-sp">${E(L[0]&&L[0].saat||"")}</span><span class="oxk-st ${s}">${tt}</span></div>
      ${L.map(l=>{ const ls=atLegSt(l); return `<div class="oxk-l"><div class="t"><b>${E(atSel(l))}</b><small>${k.tur==="cifte"?`${E(l.kosu)}. koşu · `:""}OXXai %${pct(l.p)}${l.sonuc&&l.sonuc.length?` · sonuç ${E(l.sonuc.slice(0,4).join("-"))}`:""}</small></div>
        <div class="r"><i class="${ls==="g"?"g":ls==="x"?"x":ls==="l"?"l":""}" role="img" aria-label="${ls==="g"?"Tuttu":ls==="x"?"Tutmadı":ls==="l"?"Koşuldu, sonuç bekleniyor":"Bekliyor"}">${ls==="g"?"✓":ls==="x"?"✗":ls==="l"?"…":"⏳"}</i></div></div>`; }).join("")}
      ${k.tur==="cifte"?`<div class="oxk-mt" style="margin-bottom:0"><span>İkisi birlikte OXXai <b>%${pct(k.p)}</b></span></div>`:""}</div>`; }
  function atKarneSatir(s){ const o=(x,l)=>x&&x.n?`${l}: ${x.n} KUPO · ${x.tutan} tuttu · beklenen ${f1(x.beklenen)}`:`${l}: henüz yok`;
    return `<small style="display:block;margin-top:1px">${E(o(s.canli,"Canlı"))}</small><small style="display:block;color:#FFD89A">${E(o(s.geriye_donuk,"Geriye dönük"))}</small>`; }
  window.oxxAtKartHtml=function(){ const d=today(), A=peek(U.at(d)), G=peek(U.gun(d)), K=peek(U.karne);
    let D=A; if(!D&&G&&G.at) D={kuponlar:G.at.kuponlar,kilit_tsi:G.at.kilit_tsi,geriye_donuk:G.geriye_donuk};
    let h=`<div class="oxk oxk-at" id="oxkAt" aria-label="OXXai'nin at KUPO'ları"><div class="oxk-hd"><span class="oxk-bdg" aria-hidden="true">OXXai</span><h2>OXXai'nin at KUPO'ları<small>${E(dLbl(d))}${D&&D.kilit_tsi?` · 🔒 ${E(String(D.kilit_tsi).slice(11,16))}`:""} · kendi oynadığı, kilitli</small></h2></div>`;
    if(A===undefined&&G===undefined) return h+`<div class="oxk-emp">Yükleniyor…</div></div>`;
    const Ks=(D&&D.kuponlar)||[];
    if(!Ks.length) h+=`<div class="oxk-emp"><b>Bugün OXXai at KUPO'su yok</b>KUPO'lar gece robotunun tahmini hazır olduktan sonra, henüz başlamamış koşular için kilitlenir.</div>`;
    else { const by={}; for(const k of Ks) (by[k.strateji]=by[k.strateji]||[]).push(k);
      for(const id of [...SIRA_AT,...Object.keys(by).filter(x=>!SIRA_AT.includes(x))]){ const L=by[id]; if(!L) continue; const w=L.filter(k=>k.tuttu===true||k.durum==="tuttu").length, all=S.atAll[id], sh=all?L:L.slice(0,3);
        const ks=K&&K.stratejiler&&K.stratejiler[id];
        h+=`<div class="oxk-gr"><div class="oxk-gh">${E(ad(id))}<small>${L.length} KUPO${w?` · ${w} tuttu`:""}</small></div>${ks?`<div class="oxk-note" style="margin:-2px 2px 8px">${atKarneSatir(ks)}</div>`:""}
          ${sh.map(atKupHtml).join("")}${L.length>3?`<button type="button" class="oxk-more" data-oxat="${E(id)}" aria-expanded="${!!all}">${all?"Daha az göster":`Tümünü göster (${L.length})`}</button>`:""}</div>`; } }
    h+=`<p class="oxk-ft">Olasılıklar OXXai at modelinin koşudan önce kilitlediği tahminden. Hobi amaçlı ölçümdür; tutar ve oyun bağlantısı yoktur · 18+</p></div>`;
    return h; };
  // ince kanca: #at2Box "kupon" sekmesini çizince sona ekle (yoksa sessizce atla)
  function atKanca(){ const box=$$("at2Box"); if(!box) return false; if(box.__oxk) return true; box.__oxk=1;
    const put=()=>{ if(!/^#at\/kupon(\/|$)/.test(location.hash||"")) return; const v=$$("v-at"); if(v&&v.hidden) return;
      const d=today(); if(peek(U.at(d))===undefined||peek(U.gun(d))===undefined||peek(U.karne)===undefined){ Promise.all([j(U.at(d)),j(U.gun(d)),j(U.karne)]).then(()=>{ const o=$$("oxkAt"); if(o) o.outerHTML=window.oxxAtKartHtml(); else put(); }); }
      if($$("oxkAt")) return; box.insertAdjacentHTML("beforeend",window.oxxAtKartHtml()); };
    new MutationObserver(()=>{ try{ if(!$$("oxkAt")) put(); }catch(e){} }).observe(box,{childList:true});
    box.addEventListener("click",e=>{ const b=e.target.closest("[data-oxat]"); if(!b) return; e.preventDefault(); e.stopPropagation(); const id=b.dataset.oxat; S.atAll[id]=!S.atAll[id]; const o=$$("oxkAt"); if(o) o.outerHTML=window.oxxAtKartHtml(); });
    put(); return true; }
  if(!atKanca()){ let n=0; const tm=setInterval(()=>{ if(atKanca()||++n>20) clearInterval(tm); },1500); window.addEventListener("hashchange",()=>{ try{ atKanca(); }catch(e){} }); }

  // =====================================================================
  // OXXai sohbeti: OXXai'nin KUPO'ları / bugün ne oynadın / OXXai karnesi
  // =====================================================================
  const NZ=t=>String(t||"").toLocaleLowerCase("tr").replace(/ç/g,"c").replace(/ğ/g,"g").replace(/ı/g,"i").replace(/ö/g,"o").replace(/ş/g,"s").replace(/ü/g,"u").replace(/[^a-z0-9 ]/g," ").replace(/\s+/g," ").trim();
  const RX_KAR=/\b(oxxai|oxx|bulutoxx)\w*( (in|un|nin|nun))? (kupon\w* )?(karne\w*|isabet\w*|performans\w*|basari\w*)\b|\b(senin|kendi) (kupon\w* )?karne(n|ni|si|sini)\b/;
  const RX_KUP=/\b(oxxai|oxx|bulutoxx)\w*( (in|un|nin|nun))? (gunluk |bugunku |kendi |kilitli )?kupon\w*|\b(bugun|dun|bu aksam)? ?ne oynadin\b|\bne oynuyorsun\b|\bhangi kupon\w* (oynadin|yaptin|kurdun)|\bsenin kupon(un|lar|larin|larini)\b|\bkendi kupon(un|lar|larin)\b|\boxx ne oynadi\b/;
  async function oxxBot(raw){ const s=NZ(raw); if(!s) return null; const kar=RX_KAR.test(s), kup=!kar&&RX_KUP.test(s); if(!kar&&!kup) return null;
    const ch=["KUPO'yu aç",kar?"OXXai KUPO'ları":"OXXai karnesi"]; S.tab=kar?"karne":"gun"; S.acik=true; S.d=today(); saveUI();
    if(kar){ const [K,G]=await Promise.all([j(U.karne),j(U.gunluk)]); if(!K||!K.stratejiler) return {html:"🤖 OXXai karnesi henüz hazır değil; ilk kilitli KUPO'lar sonuçlanınca KUPO'da görünecek.",chips:ch};
      const satir=id=>{ const z=K.stratejiler[id]; if(!z) return ""; const c=z.canli||{}, g=z.geriye_donuk||{};
        return `<li><b>${E(ad(id))}</b>: canlı ${c.n?`${c.tutan}/${c.n}`:"henüz yok"} · geriye dönük ${g.n?`${g.tutan}/${g.n} (beklenen ${f1(g.beklenen)})`:"–"}</li>`; };
      const son=((G&&G.kayitlar)||[]).slice(-1)[0];
      return {html:`🤖 <b>OXXai karnesi</b> (tutan/KUPO; canlı ve geriye dönük ayrı):<ul class="bt-ul">${SIRA.map(satir).join("")}</ul>${son?`Son öğrenme: ${E(olayMetni(son))} → ${olayKarar(son)}.<br>`:""}Ayrıntı ve bacak isabeti KUPO › OXXai'nin KUPO'ları › Karne'de.`,chips:ch}; }
    const d=today(), D=await j(U.gun(d));
    const K=[]; if(D) for(const sp of ["futbol","basket"]) for(const k of (D[sp]&&D[sp].kuponlar)||[]) K.push([k,sp==="basket"?"bk":"fb"]);
    if(!K.length) return {html:`🤖 Bugün henüz KUPO'mu kilitlemedim. Futbol KUPO'ları günün en az 10 aday maçı hazır olunca kilitlenir; kilitten sonra değişmez. Önceki günleri KUPO › OXXai'nin KUPO'larında görebilirsin.`,chips:ch};
    const li=K.map(([k,sp])=>{ const st=kupSt(k,sp); return `<li><b>${E(ad(k.strateji))}</b>: ${(k.bacaklar||[]).length} maç${k.oran?` · oran ${f2(k.oran)}`:""} · OXXai %${pct(k.p)} · ${E(st.t)}</li>`; }).join("");
    const lk=D.futbol&&D.futbol.kilit_tsi;
    return {html:`🤖 Bugün ${K.length} KUPO oynadım${lk?` (kilit ${E(String(lk).slice(11,16))})`:""}:<ul class="bt-ul">${li}</ul>Bacakları görmek ya da birini kendi KUPO'na kopyalamak için KUPO'ya bak.`,chips:ch}; }
  window.oxxBot=oxxBot;
  if(typeof botAnswer==="function"){ const _ba=botAnswer; botAnswer=async function(raw){ try{ const r=await oxxBot(raw); if(r) return r; }catch(e){} return _ba.apply(this,arguments); }; }
  document.addEventListener("click",e=>{ const b=e.target.closest("#botChips button[data-q]"); if(!b) return; const t=b.dataset.q;
    if(t==="OXXai KUPO'ları"||t==="OXXai karnesi"){ S.tab=t==="OXXai karnesi"?"karne":"gun"; S.acik=true; S.d=today(); saveUI(); } },true);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: oxx-kupon-v110 */
/* id: oxxai-v111 */ try {
// =====================================================================
// v111 · OXXai: tek seferlik "BULUTOXX artık OXXai" kartı, ana ekran simgesi yenileme yardımı (iOS kartı, Android notu),
// cihazlar arası/simge değişiminde veri taşıma (yedek kodu), WebP desteklemeyen tarayıcıda PNG yedeği.
// iOS: ana ekrana eklenen web uygulamasının verisi Safari'den AYRIDIR ve simge kaldırılınca silinir → kart önce yedek almayı söyler.
// Android: kurulu uygulama aynı kökeni/kapsamı (start_url/scope/id "./") paylaşır; simge ve ad manifestten kendiliğinden güncellenir.
// =====================================================================
(function(){
  // WebP açılamazsa aynı adlı PNG'ye geç
  addEventListener("error",e=>{ const t=e.target; if(t&&t.tagName==="IMG"&&/oxxai-[\w-]+\.webp(\?|$)/.test(t.src)&&!t.dataset.oxpng){ t.dataset.oxpng=1; t.src=t.src.replace(/\.webp(\?|$)/,(/oxxai-splash/.test(t.src)?".jpg":".png")+"$1"); } },true);
  const LS={get:k=>{ try{ return localStorage.getItem(k); }catch(e){ return null; } }, set:(k,v)=>{ try{ localStorage.setItem(k,v); }catch(e){} }};
  const UA=navigator.userAgent||"";
  const isIOS=/iPhone|iPad|iPod/.test(UA)||(/Macintosh/.test(UA)&&navigator.maxTouchPoints>1);
  const standalone=navigator.standalone===true||(window.matchMedia&&matchMedia("(display-mode: standalone)").matches);
  const isAndroid=/Android/.test(UA);
  const K_HELLO="bx-oxxai-hos", K_ICON="bx-oxxai-ikon";
  const existing=(()=>{ try{ return typeof termsAccepted==="function"&&termsAccepted(); }catch(e){ return false; } })();
  // yeni gelen kullanıcıya ad değişikliği/simge kartı gösterilmez (simgesi zaten yeni)
  if(!existing){ LS.set(K_HELLO,"1"); if(!(isIOS&&standalone)) LS.set(K_ICON,"1"); }

  // ---------- veri taşıma (yedek kodu) ----------
  const PFX=/^(bx-|bulutoxx-|buluto-)/;
  function backupCode(){ const o={}; for(let i=0;i<localStorage.length;i++){ const k=localStorage.key(i); if(PFX.test(k)&&!/^bx-oxxai-/.test(k)){ const v=localStorage.getItem(k); if(v!=null&&v.length<400000) o[k]=v; } }
    return "OXXAI-YEDEK:"+btoa(unescape(encodeURIComponent(JSON.stringify({v:1,t:Date.now(),d:o})))); }
  function parseCode(t){ const m=String(t||"").trim().match(/OXXAI-YEDEK:([A-Za-z0-9+/=]+)/); if(!m) return null; try{ const j=JSON.parse(decodeURIComponent(escape(atob(m[1])))); return j&&j.d&&typeof j.d==="object"?j:null; }catch(e){ return null; } }
  async function copyBackup(){ const c="OXXai: "+location.origin+location.pathname.replace(/index\.html$/,"")+"\n"+backupCode(); let ok=false; try{ await navigator.clipboard.writeText(c); ok=true; }catch(e){}
    if(ok){ toast("Yedek kodu kopyalandı ✓ Notlar'a yapıştırıp sakla"); return; }
    sheet(`<h2>Yedek kodun</h2><p>Kodu seçip kopyala, Notlar'a yapıştırıp sakla.</p><textarea readonly id="oxBkT">${c}</textarea><button class="oxw-go" type="button" data-x="1">Tamam</button>`); const ta=$("oxBkT"); if(ta){ ta.focus(); ta.select(); } }
  function restoreSheet(){
    sheet(`<h2>Yedeği geri yükle</h2><p>Eski simgede kopyaladığın <b>OXXAI-YEDEK:</b> kodunu aşağıya yapıştır.</p><textarea id="oxRsT" placeholder="OXXAI-YEDEK:..." autocomplete="off" autocapitalize="off" spellcheck="false"></textarea>
      <button class="oxw-go" type="button" id="oxRsGo">Geri yükle</button>`);
    const ta=$("oxRsT"); try{ navigator.clipboard.readText().then(t=>{ if(parseCode(t)&&ta&&!ta.value) ta.value=t.trim(); }).catch(()=>{}); }catch(e){}
    $("oxRsGo").onclick=()=>{ const j=parseCode(ta.value); if(!j){ toast("Kod tanınmadı. OXXAI-YEDEK: ile başlayan kodun tamamını yapıştır."); return; }
      let n=0; for(const [k,v] of Object.entries(j.d)){ if(PFX.test(k)&&typeof v==="string"){ LS.set(k,v); n++; } }
      LS.set(K_HELLO,"1"); LS.set(K_ICON,"1"); toast(`${n} kayıt geri yüklendi ✓`); setTimeout(()=>location.reload(),900); }; }
  window.oxxaiBackup={copy:copyBackup,restore:restoreSheet,code:backupCode};

  // ---------- kart iskeleti ----------
  function sheet(inner,onClose){ const old=$("oxw"); if(old) old.remove();
    const el=document.createElement("div"); el.className="oxw"; el.id="oxw";
    el.innerHTML=`<div class="oxw-c" role="dialog" aria-modal="true" aria-label="OXXai"><button class="oxw-x" type="button" data-x="1" aria-label="Kapat">✕</button>${inner}</div>`;
    const close=()=>{ el.classList.add("out"); setTimeout(()=>el.remove(),260); if(onClose) onClose(); };
    el.addEventListener("click",e=>{ if(e.target===el||e.target.closest("[data-x]")) close(); });
    document.body.appendChild(el); return el; }

  function welcome(){
    const hello=!LS.get(K_HELLO), icon=standalone&&!LS.get(K_ICON)&&(isIOS||isAndroid);
    if(!hello&&!icon) return;
    let h=`<img class="oxw-lg" src="icons/oxxai-logo.webp" alt="" width="118" height="118">`;
    h+= hello?`<h2><s>BULUTOXX</s> artık <em>OXX<i>ai</i></em></h2><p>Aynı uygulama, yeni kimlik. Tahminlerin, KUPO'ların ve ayarların yerinde duruyor.</p>`
             :`<h2>Yeni <em>OXX<i>ai</i></em> simgesi</h2>`;
    if(icon&&isIOS) h+=`<div class="oxw-box"><h3><img src="icons/oxxai2-apple-180.png" alt="">Yeni simgeyi ana ekranında gör</h3>
      <ol><li><b>Verilerimi kopyala</b>'ya dokun, Notlar'a yapıştır (bağlantı ve yedek kodu birlikte).</li><li>Ana ekranda simgeye basılı tut → <b>Uygulamayı Sil</b>.</li><li>Nottaki bağlantıya dokun, Safari'de <b>Paylaş → Ana Ekrana Ekle</b>.</li><li>Yeni simgeden aç: Menü › <b>Verilerimi taşı</b> › <b>Yedeği geri yükle</b>.</li></ol>
      <small>iPhone'da ana ekran uygulamasının verisi Safari'den ayrıdır; simgeyi silmek bu telefondaki KUPO'larını ve ayarlarını da siler. Önce yedek al. İstemezsen hiçbir şey yapma: eski simge de OXXai'yi açar.</small>
      <div class="oxw-bk"><button type="button" id="oxBkC">📋 Verilerimi kopyala</button><button type="button" id="oxBkR">↩︎ Yedeği geri yükle</button></div></div>`;
    else if(icon&&isAndroid) h+=`<div class="oxw-box"><h3><img src="icons/oxxai2-192.png" alt="">Ana ekran simgesi</h3><p style="margin:0;font-size:13.5px;color:var(--ink2)">Telefonun OXXai simgesini ve adını birkaç gün içinde kendiliğinden günceller. KUPO'ların ve ayarların silinmez; bir şey yapmana gerek yok.</p></div>`;
    h+=`<button class="oxw-go" type="button" data-x="1">Harika, devam et</button>`;
    sheet(h,()=>{ LS.set(K_HELLO,"1"); if(icon) LS.set(K_ICON,"1"); });
    const c=$("oxBkC"), r=$("oxBkR"); if(c) c.onclick=e=>{ e.stopPropagation(); copyBackup(); }; if(r) r.onclick=e=>{ e.stopPropagation(); restoreSheet(); };
  }
  let tries=0;
  function later(){ if(++tries>40) return; if(document.querySelector(".gate:not(.out),#splash,.bt-sheet:not([hidden])")) { setTimeout(later,1500); return; } welcome(); }
  setTimeout(later,1600);

  // ---------- Menü: Verilerimi taşı ----------
  function menu(){ const ml=document.querySelector("#v-more .mlist"); if(!ml||$("moreOxBk")) return;
    const c=document.createElement("button"); c.className="cell"; c.id="moreOxBk"; c.type="button";
    c.innerHTML=`<span class="ic oxbk"><svg viewBox="0 0 24 24"><path d="M4 8h13l-3-3M20 16H7l3 3"/></svg></span><span class="tx"><b>Verilerimi taşı</b><small>Yedek kodu: KUPO'ların ve ayarların başka simgeye veya telefona</small></span><span class="ar">›</span>`;
    c.onclick=()=>sheet(`<img class="oxw-lg" src="icons/oxxai-logo.webp" alt="" width="96" height="96" style="width:96px"><h2>Verilerimi taşı</h2><p>KUPO'ların, takip ettiklerin ve ayarların yalnız bu cihazda durur. Yedek kodunu kopyala; yeni simgede ya da başka telefonda geri yükle.</p>
      <div class="oxw-bk" style="margin:0 0 4px"><button type="button" id="oxBkC2">📋 Verilerimi kopyala</button><button type="button" id="oxBkR2">↩︎ Yedeği geri yükle</button></div>`);
    ml.appendChild(c);
    document.addEventListener("click",e=>{ if(e.target.closest("#oxBkC2")){ e.stopPropagation(); copyBackup(); } else if(e.target.closest("#oxBkR2")){ e.stopPropagation(); restoreSheet(); } },true); }
  menu(); setTimeout(menu,1200);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: oxxai-v111 */
/* id: canli-gece-v115 */ try {
// v115 · Gece yarısı ve "canlı maç yok" durumları:
// 1) Gün değişince (İstanbul saati) uygulama açık olsa da Bülten/Canlı yeni güne geçer, veri tazelenir.
// 2) Canlı altın KUPO yoksa (canlı maç yok / canlı bülten alınamadı) yerine sonraki 24 saatin altın kuponu gösterilir.
(function(){
  const TH=.75, SOLO=.85, MINP=.78; let open=false;
  const of2=o=>(+o).toLocaleString("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2});
  function cands(){ const now=Date.now(), out=[];
    for(const m of Pick.list()){ if(m.live||m.started||!m.dt) continue; const t=m.dt.getTime(); if(t<now+5*60e3||t>now+864e5) continue;
      const f=m.src==="fx"?FIXTURES.find(x=>x.lg===m.lg&&x.h===m.h&&x.a===m.a):fxOdds(m); if(!f||!f.odds) continue;
      let p=null; try{ p=quickPred(m,f); }catch(e){} if(!p||!p.pm) continue;
      let R=null; try{ R=recOf({H:p.pm[0],D:p.pm[1],A:p.pm[2],o25:p.o25m},f); }catch(e){}
      if(R&&R.o&&R.o>=1.05&&R.cp>=MINP) out.push({m,R,f}); }
    return out.sort((a,b)=>b.R.cp-a.R.cp).slice(0,12); }
  function build(){ const c=cands(); let best=null;
    (function rec(i,sel,p,o){ if(sel.length>=2&&p>=TH&&(!best||o>best.o+1e-9)) best={sel:sel.slice(),p,o};
      if(sel.length>=4) return; for(let j=i;j<c.length;j++){ const np=p*c[j].R.cp; if(np<TH) continue; sel.push(c[j]); rec(j+1,sel,np,o*c[j].R.o); sel.pop(); } })(0,[],1,1);
    if(!best){ const s=c.find(x=>x.R.cp>=SOLO); if(s) best={sel:[s],p:s.R.cp,o:s.R.o}; }
    return best; }
  function paint(){ const lg=$("lgBtn"); if(!lg) return;
    let b=$("lgPreBtn"), pan=$("lgPrePan");
    if(!b){ b=document.createElement("button"); b.type="button"; b.id="lgPreBtn"; b.className="lg-btn"; b.onclick=()=>{ open=!open; try{ buzz(8); Sound.tap(); }catch(e){} paint(); }; }
    if(!pan){ pan=document.createElement("div"); pan.id="lgPrePan"; pan.className="lg-pan"; pan.hidden=true; }
    const lp=$("lgPan")||lg; if(lp.nextElementSibling!==b) lp.after(b); if(b.nextElementSibling!==pan) b.after(pan);
    const liveOn=!lg.classList.contains("off");
    if(liveOn){ b.hidden=true; pan.hidden=true; return; }
    const ok=typeof IDL!=="undefined"&&IDL.ok&&IDL.ok[1], failed=typeof IDL!=="undefined"&&IDL.failed, nLive=((typeof IDL!=="undefined"&&IDL.live&&IDL.live[1])||[]).length;
    const why=failed&&!ok?"Canlı bülten şu an alınamıyor · birazdan yeniden denenecek":ok&&!nLive?"Şu an oynanan canlı maç yok":ok?"Taranıyor · şu an yeterince güvenli canlı seçim yok":"Canlı bülten bekleniyor";
    lg.querySelector(".lg-t small")&&(lg.querySelector(".lg-t small").textContent=why);
    const K=build(); b.hidden=false;
    if(!K){ b.classList.add("off"); pan.hidden=true; b.innerHTML=`<span class="lg-ic">🥇</span><span class="lg-t"><b>Sıradaki altın KUPO</b><small>Sonraki 24 saatte yeterince güvenli kombinasyon yok</small></span>`; return; }
    b.classList.remove("off"); b.setAttribute("aria-expanded",String(open));
    const t0=K.sel.map(x=>x.m.dt).sort((a,c)=>a-c)[0];
    b.innerHTML=`<span class="lg-ic">🥇</span><span class="lg-t"><b>Sıradaki altın KUPO · ${K.sel.length} maç</b><small>Sonraki 24 saat · ilk maç ${esc((istDay(t0)===istDay(new Date())?"bugün ":"yarın ")+ist(t0,{hour:"2-digit",minute:"2-digit"}))} · toplam oran ${of2(K.o)} · ${open?"kapat":"dokun, gör"}</small></span><span class="lg-p">%${pc9(K.p)}</span>`;
    pan.hidden=!open; if(!open) return;
    pan.innerHTML=K.sel.map(x=>{ const m=x.m; return `<div class="pw-r"${omA(m)}><div class="pw-m"><b>${esc(m.h)} - ${esc(m.a)}</b><small>${goldOf(m)?"🥇 ":""}${esc(istDay(m.dt)===istDay(new Date())?"Bugün":"Yarın")} ${esc(ist(m.dt,{hour:"2-digit",minute:"2-digit"}))} · ${esc((x.f&&(x.f.cn||x.f.ln))||m.lg||"")}</small></div><div class="pw-s"><span>${esc(x.R.n||x.R.label||"")}</span><b>%${pc9(x.R.cp)}</b><small>oran ${of2(x.R.o)}</small></div></div>`; }).join("")
      +`<button type="button" class="lg-add" id="lgPreAdd">+ Altın seçimleri KUPO'ya ekle</button><p class="lg-n">Canlı maç başlayınca üstte canlı altın KUPO yeniden taranır. Birlikte tutma olasılığı %${Math.round(TH*100)}+ olsa da kesinlik değildir · 18+</p>`;
    $("lgPreAdd").onclick=()=>{ try{ buzz([10,30,10]); }catch(e){} let n=0; for(const x of K.sel){ if(!CP.items.some(c=>c.k===cpKey(x.m)&&c.mk===x.R.k)){ cpToggle(x.m,x.R.k,+x.R.o,x.R.cp); n++; } } try{ paintCoupon(); }catch(e){} try{ toast(n?`🥇 ${n} seçim KUPO'ya eklendi`:"Bu seçimler zaten KUPO'nda"); }catch(e){} };
  }
  try{ const _lp=window.lgPaint; if(_lp){ window.lgPaint=function(){ const r=_lp.apply(this,arguments); try{ paint(); }catch(e){} return r; }; } }catch(e){}
  try{ const _ira=idlRenderAll; idlRenderAll=function(){ const r=_ira.apply(this,arguments); try{ paint(); }catch(e){} return r; }; }catch(e){}
  // gün değişimi
  let DAY=istDay(new Date());
  function rollover(){ const d=istDay(new Date()); if(d===DAY) return; const old=DAY; DAY=d;
    try{ if(BT.day===old) BT.day=d; }catch(e){}
    try{ if(typeof RS!=="undefined"&&RS.day===old) RS.day=d; }catch(e){}
    try{ renderBulten(); }catch(e){} try{ idlRenderAll(); }catch(e){} try{ paint(); }catch(e){}
    try{ loadData(true); }catch(e){} }
  setInterval(()=>{ try{ rollover(); }catch(e){} },30e3);
  document.addEventListener("visibilitychange",()=>{ if(!document.hidden) try{ rollover(); const v=$("v-canli"); if(v&&!v.hidden){ idlRenderAll(); } }catch(e){} });
  window.addEventListener("focus",()=>{ try{ rollover(); }catch(e){} });
  setInterval(()=>{ const v=$("v-canli"); if(v&&!v.hidden&&!document.hidden) try{ paint(); }catch(e){} },60e3);
  setTimeout(()=>{ try{ paint(); }catch(e){} },1500);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: canli-gece-v115 */
