/* id: ara-geri-v142 */ try {
// v142 · Arama kayması (sabit düzen, 16px giriş, klavyede alt menü gizli, arama sırasında yeniden çizim yok) + gezinme yığını ve geri düğmesi. Ayrıntı: data/gelisim.json
(function(){ "use strict";
const W=window, D=document, H=history;
const $$=id=>D.getElementById(id);
const E=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const vz=b=>{ try{ if(typeof buzz==="function") buzz(b||7); }catch(e){} };
const TXT=/^(search|text|email|tel|number|url|password)$/;
const isTxt=el=>!!(el&&((el.tagName==="INPUT"&&TXT.test(el.type||"text"))||el.tagName==="TEXTAREA"||el.isContentEditable));
const touch=()=>{ try{ return matchMedia("(pointer:coarse)").matches||navigator.maxTouchPoints>0; }catch(e){ return false; } };
const R=D.documentElement;
function kb(){ const on=touch()&&isTxt(D.activeElement)&&!D.activeElement.closest("#sheet,#msheet,#botSheet,.sheet");
R.classList.toggle("gx-kb",on); }
D.addEventListener("focusin",kb); D.addEventListener("focusout",()=>setTimeout(kb,60));
try{ if(W.visualViewport) W.visualViewport.addEventListener("resize",()=>{ const vv=W.visualViewport; if(vv.height>innerHeight*.9&&!isTxt(D.activeElement)) R.classList.remove("gx-kb"); }); }catch(e){}
const ARA=[["v-bulten","btQBox","btQ"],["v-basket","bkQBox","bkQ"],["v-sonuclar","rsQBox","rsQ"]];
function araSync(){ for(const [v,b] of ARA){ const s=$$(v), bx=$$(b); if(s) s.classList.toggle("gx-ara",!!(bx&&!bx.hidden)); }
const cv=$$("v-canli"), ci=$$("cvQi"); if(cv) cv.classList.toggle("gx-ara",!!(ci&&(ci.value.trim()||D.activeElement===ci))); }
function araWatch(){ for(const [,b] of ARA){ const bx=$$(b); if(bx&&!bx.__gx){ bx.__gx=1; new MutationObserver(araSync).observe(bx,{attributes:true,attributeFilter:["hidden"]}); } } araSync(); }
araWatch(); setTimeout(araWatch,1500); setTimeout(araWatch,4000);
D.addEventListener("focusin",e=>{ if(e.target&&e.target.id==="cvQi") araSync(); }); D.addEventListener("focusout",()=>setTimeout(araSync,80));
function hizala(listId,headSel){ const L=$$(listId), h=D.querySelector(headSel); if(!L||!h) return;
const hb=h.getBoundingClientRect().bottom, lt=L.getBoundingClientRect().top;
if(lt<hb-1){ const y=Math.max(0,Math.round(scrollY+lt-hb-4)); if(Math.abs(y-scrollY)>1) W.scrollTo(0,y); } }
const odak=id=>{ const i=$$(id); return !!(i&&D.activeElement===i); };
const sigB=()=>[BT.q,BT.f,BT.day,BT.lg].join("|");
let bLast="", bPend=false;
try{ const _rb=renderBulten; renderBulten=function(){
if(BT.q&&odak("btQ")&&sigB()===bLast&&$$("btList")&&$$("btList").children.length){ bPend=true; return; }
const ara=!!BT.q, yeni=ara&&sigB()!==bLast; const y=scrollY;
const r=_rb.apply(this,arguments); bLast=ara?sigB():""; bPend=false;
if(ara){ if(Math.abs(scrollY-y)>1) W.scrollTo(0,y); if(yeni) hizala("btList","#v-bulten .bt-head"); }
return r; }; }catch(e){}
D.addEventListener("focusout",e=>{ if(e.target&&e.target.id==="btQ"&&bPend) setTimeout(()=>{ if(bPend&&!odak("btQ")) try{ renderBulten(); }catch(_){} },120); });
try{ const _rk=renderBasket; renderBasket=function(){ const y=scrollY, ara=!!(BK&&BK.q); const r=_rk.apply(this,arguments); if(ara){ if(Math.abs(scrollY-y)>1) W.scrollTo(0,y); hizala("bkList","#v-basket .bt-head"); } return r; }; }catch(e){}
try{ const _rr=renderRes; renderRes=function(){ const y=scrollY, ara=!!(RS&&RS.q); const r=_rr.apply(this,arguments); if(ara){ if(Math.abs(scrollY-y)>1) W.scrollTo(0,y); hizala("rsList","#v-sonuclar .bt-head"); } return r; }; }catch(e){}
function cvIds(){ try{ const sp=IDLV.sp||1; return (IDL.live[sp]||[]).filter(m=>qMatch(IDLV.q,[m.h,m.a,m.comp])).map(m=>m.id).sort().join(","); }catch(e){ return null; } }
let cLast="";
try{ const _ira=idlRenderAll; idlRenderAll=function(){
const v=$$("v-canli"), box=$$("idlBox");
if(IDLV.q&&v&&!v.hidden&&box&&box.innerHTML){ const ids=cvIds(); const k=ids+"|"+IDLV.q+"|"+IDLV.sp+"|"+IDLV.sort;
if(ids!=null&&k===cLast){ try{ box.querySelectorAll(".lv-c[data-id]").forEach(r=>{ const c=r.querySelector(".lclk"), sp=c?+c.dataset.sp:(IDLV.sp||1), m=(IDL.byId[sp]||{})[+r.dataset.id]; if(!m) return;
const b=r.querySelector(".lv-sc b"), t=`${m.hs}-${m.as}`; if(b&&b.textContent!==t) b.textContent=t; });
const sub=$$("liveSub"); if(sub&&(IDL.ok[1]||IDL.ok[2])) sub.textContent=`${IDL.live[1].length} futbol · ${IDL.live[2].length} basketbol maçı oynanıyor`; }catch(e){}
return; }
const y=scrollY; const r=_ira.apply(this,arguments); cLast=k; if(Math.abs(scrollY-y)>1) W.scrollTo(0,y); return r; }
cLast=""; return _ira.apply(this,arguments); }; }catch(e){}
function geciktir(id){ const i=$$(id); if(!i||!i.oninput||i.oninput.__gx) return; const f=i.oninput; let t;
const g=function(e){ const self=this; clearTimeout(t); t=setTimeout(()=>{ try{ f.call(self,e); }catch(_){} },160); }; g.__gx=1; i.oninput=g; }
const AD={bulten:"Bülten",canli:"Canlı",kupon:"KUPO",at:"At",power:"POWER",sonuclar:"Sonuçlar",more:"Menü",basket:"Basket",
sonuc:"Kayıtlı",tahmin:"Tahmin",ligler:"Ligler",karne:"Karne",gelisim:"Gelişim",rehber:"Rehber",
"kupon/eski":"Eski KUPO","kupon/oyn":"Takip","kupon/snc":"Sonuçlar","at/program":"Program","at/turler":"Türler","at/sonuc":"Sonuç","at/kupon":"At KUPO"};
const KOK=new Set(["bulten","canli","kupon","at","power","sonuclar","more","basket"]);
const UST={sonuc:"more",tahmin:"more",ligler:"more",karne:"more",gelisim:"more",rehber:"more"};
const ust=k=>UST[k]||(k.indexOf("/")>0?k.split("/")[0]:"bulten");
const ad=k=>AD[k]||AD[ust(k)]||"Geri";
const ATTAB=["program","turler","sonuc","kupon"];
let CUR=null, BUSY=0, IGN=0, PEND=null;
function key(){ const s=[...D.querySelectorAll("main > section.view")].find(x=>!x.hidden); if(!s) return CUR?CUR.k:"bulten"; const v=s.id.slice(2);
if(v==="at"){ const m=/^#at(?:\/([^/]*))?/.exec(location.hash||""), r=m&&m[1]||"";
if(ATTAB.includes(r==="bahis"?"turler":r)) return "at/"+(r==="bahis"?"turler":r);
if(!r||r==="bugun") return "at";
return CUR&&/^at/.test(CUR.k)?CUR.k:"at"; }
if(v==="kupon"){ let t=""; try{ t=KP.tab||""; }catch(e){} return ["eski","oyn","snc"].includes(t)?"kupon/"+t:"kupon"; }
return v; }
const st=()=>{ const s=H.state; return s&&typeof s==="object"?s:{}; };
const dep=()=>+st().gg||0;
const oPush=H.pushState.bind(H), oRep=H.replaceState.bind(H);
const MER=["gx","gg","gp","gov"];
H.pushState=function(s,t,u){ let n=s; try{ const c=st(); if(c.gx!=null&&(n==null||typeof n==="object")){ n=Object.assign({},n||{}); for(const f of MER) if(!(f in n)&&c[f]!=null) n[f]=c[f]; } }catch(e){}
const r=oPush(n,t,u); plan(); return r; };
H.replaceState=function(s,t,u){ let n=s; try{ const c=st(); if((c.gx!=null||c.gguard)&&(n==null||typeof n==="object")){ n=Object.assign({},n||{}); for(const f of MER.concat("gguard")) if(!(f in n)&&c[f]!=null) n[f]=c[f]; } }catch(e){}
const r=oRep(n,t,u); plan(); return r; };
const yaz=(o,u)=>{ try{ oRep(Object.assign({},st(),o),"",u||location.href); }catch(e){} };
const navB=v=>D.querySelector(`nav.tabs button[data-v="${v}"]`);
function git(k){ BUSY++; try{
const [a,b]=k.split("/");
if(a==="at"){ const v=$$("v-at"); if(!v||v.hidden) showSport("at");
const h=location.hash||"", ok=b?h==="#at/"+b:(h==="#at"||h==="#at/bugun");
if(!ok){ try{ oRep(H.state,"","#at/"+(b||"bugun")); }catch(e){} try{ W.dispatchEvent(new HashChangeEvent("hashchange")); }catch(e){} } }
else if(a==="kupon"){ try{ KP.tab=b||"cp"; }catch(e){} const n=navB("kupon"); if(n) n.click(); try{ kuponTab(b||"cp"); }catch(e){} setTimeout(()=>{ try{ if((KP.tab||"cp")!==(b||"cp")) kuponTab(b||"cp"); }catch(e){} },40); }
else if(a==="basket") showSport("bk");
else if(a==="karne"||a==="rehber") goView(a,"more");
else if(a==="gelisim"){ const g=$$("moreGel"); if(g) g.click(); else goView("gelisim","more"); }
else { const n=navB(a); if(n) n.click(); else goView(a);
if(a==="bulten"){ const vb=$$("v-bulten"); if(vb&&vb.hidden) try{ showSport("fb"); }catch(e){} } }
}catch(e){ try{ console.warn("[geri]",e); }catch(_){} } finally{ setTimeout(()=>{ BUSY--; CUR={k:key(),u:location.href}; yaz({gx:CUR.k}); boya(); },90); } }
let pT=null; function plan(){ clearTimeout(pT); pT=setTimeout(isle,70); }
function isle(){ if(IGN>0||BUSY>0){ plan(); return; }
const k=key(), u=location.href;
if(!CUR){ CUR={k,u}; return; }
if(k===CUR.k){ CUR.u=u; if(st().gx!==k&&!st().gguard) yaz({gx:k}); boya(); return; }
const p=CUR; CUR={k,u};
if(KOK.has(k)){ const d=dep();
if(d>0){ PEND={k,u}; IGN++; try{ H.go(-d); }catch(e){ IGN--; PEND=null; yaz({gx:k,gg:0,gp:null}); } }
else yaz({gx:k,gg:0,gp:null},u);
boya(); return; }
const kard=p.k.indexOf("/")>0&&k.indexOf("/")>0&&p.k.split("/")[0]===k.split("/")[0];
if(kard){ yaz({gx:k},u); boya(); return; }
try{ oRep(Object.assign({},st(),{gx:p.k}),"",p.u); oPush({gx:k,gg:dep()+1,gp:p.k},"",u); }catch(e){}
boya(); }
let cikT=0, cikTm=null;
function bekci(){ if(CUR&&CUR.k!=="bulten"){ git("bulten"); setTimeout(()=>{ try{ oPush({gx:"bulten",gg:0,gp:null},"",location.href.split("#")[0]+"#bulten"); }catch(e){} },120); return; }
const now=Date.now(); cikT=now; try{ toast("Çıkmak için bir kez daha geri dokun"); }catch(e){} vz(10);
clearTimeout(cikTm); cikTm=setTimeout(()=>{ if(st().gguard) try{ oPush({gx:key(),gg:0,gp:null},"",location.href); }catch(e){} },2200); }
W.addEventListener("popstate",e=>{ const s=st();
if(IGN>0){ IGN--; if(PEND){ const P=PEND; PEND=null; yaz({gx:P.k,gg:0,gp:null},P.u); if(key()!==P.k) git(P.k); CUR={k:P.k,u:P.u}; boya(); } return; }
if(s.gguard){ bekci(); return; }
clearTimeout(cikTm);
const sh=$$("sheet"); if(sh&&!sh.hidden&&sh.__gx&&s.gov!=="sheet"){ sh.__gx=0; kapatSheet(sh); }
if(s.gx==null) return;
if(!CUR||s.gx!==CUR.k){ CUR={k:s.gx,u:location.href}; git(s.gx); }
else boya(); });
function kapatSheet(sh){ try{ const x=sh.querySelector("#setDone,#instClose,#shClose,#pkX,#lgX,[data-x],.sh-x,.x-close"); if(x){ x.click(); }
else if(typeof sh.onclick==="function") sh.onclick({target:sh,currentTarget:sh,preventDefault(){},stopPropagation(){}}); }catch(e){}
if(!sh.hidden&&typeof sh.onclick!=="function"){  } }
function sheetIzle(){ const sh=$$("sheet"); if(!sh||sh.__gxw) return; sh.__gxw=1; let acik=!sh.hidden;
new MutationObserver(()=>{ const a=!sh.hidden; geciktir("pkQ"); geciktir("lgQ"); if(a) pill(); if(a===acik) return; acik=a;
if(a){ if(typeof sh.onclick!=="function"&&!sh.querySelector("#setDone,#instClose,#shClose,#pkX,#lgX")) return;
sh.__gx=1; setTimeout(()=>{ if(sh.hidden||!sh.__gx) return; try{ oPush(Object.assign({},st(),{gov:"sheet"}),"",location.href); }catch(e){} pill(); },0); }
else if(sh.__gx){ sh.__gx=0; if(st().gov==="sheet"){ IGN++; try{ H.back(); }catch(e){ IGN--; } } }
}).observe(sh,{attributes:true,attributeFilter:["hidden"],childList:true}); }
const IC='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>';
function dugme(lbl,fn){ const b=D.createElement("button"); b.type="button"; b.className="gx-geri"; b.setAttribute("aria-label","Geri: "+lbl); b.innerHTML=IC+"<span>"+E(lbl)+"</span>"; b.dataset.gxl=lbl;
b.addEventListener("click",e=>{ e.preventDefault(); e.stopPropagation(); vz(7); fn(); }); return b; }
function geri(){ const s=st(), d=dep();
if(d>0&&s.gp){ try{ H.back(); }catch(e){ git(s.gp); } return; }
const k=CUR?CUR.k:key(), u=ust(k); git(u); setTimeout(()=>yaz({gx:u,gg:0,gp:null}),120); }
const onceki=()=>{ const s=st(), k=CUR?CUR.k:key(); return dep()>0&&s.gp?s.gp:ust(k); };
function koy(host,before,lbl,fn,cls){ if(!host) return; let b=host.querySelector(":scope > .gx-geri");
if(b&&b.dataset.gxl===lbl) return; if(b) b.remove(); b=dugme(lbl,fn); host.insertBefore(b,before||host.firstChild); if(cls) host.classList.add(cls); }
function sil(sel){ D.querySelectorAll(sel).forEach(b=>{ const h=b.parentElement; b.remove(); if(h) h.classList.remove("gx-has"); }); }
function pill(){ try{
const k=CUR?CUR.k:key(), alt=!KOK.has(k), lbl=ad(onceki());
D.querySelectorAll("main > section.view").forEach(s=>{ const v=s.id.slice(2), t=s.querySelector(".ltitle");
if(!t) return; const ok=!s.hidden&&alt&&k===v; if(ok) koy(t,null,lbl,geri,"gx-has"); else { const b=t.querySelector(":scope > .gx-geri"); if(b){ b.remove(); t.classList.remove("gx-has"); } } });
const hero=$$("kxHero"); if(hero){ if(/^kupon\//.test(k)) koy(hero,null,lbl,geri,"gx-has"); else { const b=hero.querySelector(":scope > .gx-geri"); if(b){ b.remove(); hero.classList.remove("gx-has"); } } }
const ah=D.querySelector("#at2Box .a2-hd"); if(ah){ if(/^at\//.test(k)&&D.querySelector("#at2Nav .a2-seg")) koy(ah,null,lbl,geri,"gx-has"); else { const b=ah.querySelector(":scope > .gx-geri"); if(b){ b.remove(); ah.classList.remove("gx-has"); } } }
const sh=$$("sheet"); if(sh&&!sh.hidden&&sh.__gx){ const bx=sh.querySelector(".box"); if(bx){ const h=bx.querySelector(":scope > h2, :scope > h3"); koy(bx,h||bx.querySelector(":scope > .grab + *")||bx.firstChild,ad(k),()=>{ if(st().gov==="sheet"){ try{ H.back(); }catch(e){} } else kapatSheet(sh); }); } }
const mx=D.querySelector("#msheet:not([hidden]) .ms-top .ms-x"); if(mx&&mx.dataset.gxl!==ad(k)){ mx.classList.add("gx-geri"); mx.dataset.gxl=ad(k); mx.setAttribute("aria-label","Geri: "+ad(k)); mx.innerHTML=IC+"<span>"+E(ad(k))+"</span>"; }
const bh=D.querySelector("#botSheet:not([hidden]) .bt-h"); if(bh) koy(bh,null,ad(k),()=>{ try{ botClose(); }catch(e){} });
}catch(e){} }
let bT=0; function boya(){ if(bT) return; bT=requestAnimationFrame(()=>{ bT=0; pill(); }); }
sil("#v-karne .backlink, #v-rehber .backlink");
function kur(){ const s=st();
CUR={k:key(),u:location.href};
if(s.gx!=null||s.ms||s.bt||s.at2){ yaz({gx:CUR.k,gg:+s.gg||0}); }
else if(!s.gguard){ try{ oRep(Object.assign({},s,{gguard:1}),"",location.href); oPush({gx:CUR.k,gg:0,gp:null},"",location.href); }catch(e){} }
sheetIzle();
const mo=new MutationObserver(ms=>{ let v=false; for(const m of ms){ if(m.type==="attributes"&&m.target.matches&&m.target.matches("section.view")) v=true; } if(v) plan(); boya(); });
const main=D.querySelector("main"); if(main) mo.observe(main,{attributes:true,attributeFilter:["hidden"],subtree:true,childList:true});
["msheet","botSheet"].forEach(id=>{ const el=$$(id); if(el&&!el.__gxw){ el.__gxw=1; new MutationObserver(boya).observe(el,{attributes:true,attributeFilter:["hidden"],childList:true}); } });
D.addEventListener("click",e=>{ if(e.target.closest&&e.target.closest("[onclick],button,a")) setTimeout(()=>{ ["msheet","botSheet"].forEach(id=>{ const el=$$(id); if(el&&!el.__gxw){ el.__gxw=1; new MutationObserver(boya).observe(el,{attributes:true,attributeFilter:["hidden"],childList:true}); } }); boya(); },60); },true);
W.addEventListener("hashchange",plan);
try{ const _kt=kuponTab; kuponTab=function(){ const r=_kt.apply(this,arguments); plan(); return r; }; }catch(e){}
boya(); }
setTimeout(kur,400);
W.oxxGeri={durum:()=>({cur:CUR&&CUR.k,state:H.state,ign:IGN,busy:BUSY}),geri,git};
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: ara-geri-v142 */
/* id: canli-piyasa-v144 */ try {
(function(){
  "use strict";
  // =====================================================================
  // v144 · YH-10 · CANLI PİYASA OLASILIĞI + CG HARMANI (futbol) — scripts/canli_guc.py piyasa() / harman() ile BİREBİR
  // • Canlı oranlardan (m.odds = idlOdds: MS, ana çizgi Alt/Üst, sıradaki gol) marjı ayrılmış piyasa olasılığı (power yöntemi).
  // • Harman: p_i ∝ exp(a·ln p_CG,i + b·ln p_piyasa,i); (a, b) pazar × dakika dilimi (0–30, 30–60, 60–75, 75+), lab/canli_piyasa_lab.py
  //   zaman sıralı kapısından gelir. Kapalı (askıdaki) pazarda ya da oran yokken CG aynen kalır.
  // • Bayrak: data/canli_piyasa.json → kullan=true ise açılır (gece yeniden sınanır; tutmazsa kendiliğinden kapanır). Kapalıyken etkisiz.
  // • Kanca: canli-gt-v107 core() dönüşünde (CG açıkken) CPH.apply → pencere, Seçenekler, canlı altın, işaret aynı sayıyı görür.
  // =====================================================================
  const DL=["0","30","60","75"], PZ=["ms","ou","ng"], H={on:false,W:null,src:"kapali"};
  function implied(o){ const q=o.map(x=>1/x); let lo=1,hi=3,k=1; for(let i=0;i<40;i++){ k=(lo+hi)/2; if(q.reduce((a,b)=>a+Math.pow(b,k),0)>1) lo=k; else hi=k; }
    const p=q.map(x=>Math.pow(x,k)), s=p.reduce((a,b)=>a+b,0); return p.map(x=>x/s); }
  const dilim=t=>t>=75?"75":t>=60?"60":t>=30?"30":"0";
  function hk(pc,pm,a,b){ const z=pc.map((x,i)=>a*Math.log(Math.max(x,1e-9))+b*Math.log(Math.max(pm[i],1e-9))), mx=Math.max(...z), e=z.map(v=>Math.exp(v-mx)), s=e.reduce((x,y)=>x+y,0); return e.map(v=>v/s); }
  function piyasa(od){ const o={}; if(!od) return o;
    if(od.ms&&!od.ms.lock&&od.ms.v&&od.ms.v.length===3) o.ms=implied(od.ms.v);
    if(od.ng&&!od.ng.lock&&od.ng.v&&od.ng.v.length===3) o.ng=implied(od.ng.v);
    if(od.ou&&!od.ou.lock&&od.ou.alt&&od.ou.ust) o.ou=[+od.ou.l,implied([od.ou.alt,od.ou.ust])[1]];
    return o; }
  function gecerli(W){ try{ const o={}; for(const m of PZ){ o[m]={}; for(const d of DL){ const v=W[m][d], a=+v[0], b=+v[1];
      if(!(isFinite(a)&&isFinite(b)&&a>=0&&a<=2&&b>=0&&b<=2)) return null; o[m][d]=[a,b]; } } return o; }catch(e){ return null; } }
  function apply(P,m){ if(!H.on||!H.W||!P) return P; const mk=piyasa(m&&m.odds), dl=dilim(P.t), W=H.W;
    if(mk.ms){ const r=hk([P.H,P.D,P.A],mk.ms,W.ms[dl][0],W.ms[dl][1]); P.H=r[0]; P.D=r[1]; P.A=r[2]; }
    if(mk.ng){ const r=hk([P.nextH,P.none,P.nextA],mk.ng,W.ng[dl][0],W.ng[dl][1]); P.nextH=r[0]; P.none=r[1]; P.nextA=r[2]; }
    if(mk.ou&&+P.line===mk.ou[0]&&P.pOver>0&&P.pOver<1) P.pOver=hk([P.pOver,1-P.pOver],[mk.ou[1],1-mk.ou[1]],W.ou[dl][0],W.ou[dl][1])[0];
    if(mk.ms||mk.ng||mk.ou){ P.pz=mk; P.harman=true; } return P; }
  window.CPH={H,piyasa,apply,hk,dilim,implied};
  try{ fetch("data/canli_piyasa.json",{cache:"no-cache"}).then(r=>r.ok?r.json():null).then(j=>{ if(!j||j.kullan!==true) return;
      const W=gecerli(j.W); if(!W) return; H.W=W; H.on=true; H.src="canli_piyasa"; }).catch(()=>{}); }catch(e){}
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: canli-piyasa-v144 */
/* id: neden-v145 */ try {
// v145 · YH-22 "Neden bu tahmin?" kısa açıklama kartı. Maç penceresindeki öneri kutusunda "ⓘ Neden bu tahmin?" düğmesi,
// bülten satırında / Canlı sekmesi satırında uzun basma (masaüstünde sağ tık), basket penceresi ve at koşu kartı / at profili.
// İçerik yalnız ekranda gösterilen olasılığı üreten GERÇEK girdilerden (aynı fonksiyonlar: fullPred/kpFix/recOf, idlPred/idlPick/liveCal,
// bkPredict, BX_AT.merged + sinyal) ve kilitli karne kovalarından (daily.json guvenilirlik, basket.json live.guvenilirlik, at/karne.json).
// Verisi olmayan madde gösterilmez. Kart yalnız açılınca hesaplanır (açılış süresi etkilenmez). Futbol ve at ayrı fonksiyonlar.
(function(){ "use strict";
const W=window, D=document;
const E=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fin=v=>v!=null&&isFinite(v);
const yz=p=>"%"+Math.min(99,Math.max(1,Math.round(p*100)));
const nf=(x,d)=>(+x).toLocaleString("tr-TR",{minimumFractionDigits:d,maximumFractionDigits:d});
const n1=x=>nf(x,1), n2=x=>nf(x,2), n0=x=>Math.round(+x).toLocaleString("tr-TR");
const kisa=n=>{ try{ return typeof shortTeam==="function"?shortTeam(n):n; }catch(e){ return n; } };
const YASAK=/bahis|ganyan|banko|bulut|kupon|tjk/i;
const vz=b=>{ try{ if(typeof buzz==="function") buzz(b||6); }catch(e){} };
// ---------- kart ----------
function kapat(){ const o=D.getElementById("ndSheet"); if(o){ o.remove(); D.removeEventListener("keydown",esc_,true); } }
function esc_(e){ if(e.key==="Escape"){ e.stopPropagation(); kapat(); } }
function kart(o){ kapat(); if(!o) return null;
  const L=(o.maddeler||[]).filter(x=>x&&!YASAK.test(String(x).replace(/<[^>]+>/g,""))).slice(0,6);
  const el=D.createElement("div"); el.id="ndSheet"; el.className="nd-ov";
  el.innerHTML=`<div class="nd-c" role="dialog" aria-modal="true" aria-labelledby="ndT"><button type="button" class="nd-x" aria-label="Kapat">✕</button>
    <h2 id="ndT">Neden bu tahmin?</h2>${o.ust?`<p class="nd-s">${o.ust}</p>`:""}
    <ul class="nd-l">${L.map(x=>`<li>${x}</li>`).join("")}</ul>
    <p class="nd-f">Tahmindir, garanti değildir.</p></div>`;
  el.addEventListener("click",e=>{ if(e.target===el||e.target.closest(".nd-x")){ e.preventDefault(); e.stopPropagation(); kapat(); } });
  D.body.appendChild(el); D.addEventListener("keydown",esc_,true);
  try{ el.querySelector(".nd-x").focus({preventScroll:true}); }catch(e){}
  return el; }
function ekle(el,html){ try{ if(!el||!el.isConnected||!html||YASAK.test(html.replace(/<[^>]+>/g,""))) return; const ul=el.querySelector(".nd-l"); if(!ul||ul.children.length>=6) return; ul.insertAdjacentHTML("beforeend",`<li>${html}</li>`); }catch(e){} }
W.addEventListener("popstate",kapat);
// kilitli karne kovası: "%X–Y dediğimiz n tahmin %Z tuttu" (n < 50 ise gösterilmez)
function kova(g,p,birim){ try{ const K=g&&g.kovalar; if(!K||!fin(p)) return null;
  for(const b of K){ const a=String(b.aralik||"").split("-").map(Number); if(a.length!==2||!(p>=a[0]&&(p<a[1]||(a[1]>=1&&p<=1)))) continue;
    if(!(b.n>=50)||!fin(b.gercek)) return null;
    return `Geçmiş isabet: <b>%${Math.round(a[0]*100)}–${Math.round(a[1]*100)}</b> dediğimiz ${n0(b.n)} ${birim} gerçekte <b>%${Math.round(b.gercek*100)}</b> tuttu (maçtan önce kilitlenmiş kayıtlar).`; }
  }catch(e){} return null; }
// ---------- FUTBOL · maç öncesi ----------
function fbOrt(m,f){
  const pm=m.sp?{lg:"i"+m.ci,h:m.h,a:m.a,dt:new Date(m.ts)}:m;
  const FP=fullPred(pm,f); if(!FP||!FP.r) return null;
  const r=kpFix(FP.r,f), R=recOf(r,f); if(!R) return null;
  const odds=!!(f&&f.odds&&f.odds.length===3), guc=!!(f&&f.kpy==="guc"&&f.kp), kons=!!(f&&f.kp&&f.kp.length===3&&f.kpy!=="guc");
  const I=[];   // [öncelik, html]
  // 1) yol
  if(kons) I.push([1,`Yol: <b>robot konseyi</b>. Geçmişte piyasayı geçen robotların ortak olasılığı kullanıldı.`]);
  else if(odds){ const w=MP("marketW",.6); I.push([1,w>=.99?`Yol: <b>piyasa kalibre</b>. Olasılık iddaa oranlarından (marjı ayrılmış) gelir, OXXai'nin geçmiş isabetine göre öğrenilmiş kalibrasyonla düzeltilir.`
    :`Yol: <b>piyasa kalibre</b>. iddaa oranlarından marjı ayrılmış olasılık, OXXai gol modeliyle birleştirildi (piyasa payı %${Math.round(w*100)}).`]); }
  else if(guc) I.push([1,`Yol: <b>güç modeli topluluğu</b>. Oran yok; Poisson, Elo ve pi-rating puanları birleştirildi (geçmiş maçlarda sınanıp devreye alındı).`]);
  else I.push([1,`Yol: <b>Poisson gol modeli</b>. Oran yok; ${r.source==="form"?"sezon verisi az, son maç formu ağırlıklı":r.source==="cup"?"farklı lig / kupa: lig güç katsayılarıyla ortak ölçek":"takımların sezon hücum / savunma gücü ve son formu"}.`]);
  // 2) piyasa ile karşılaştırma
  let q=null; try{
    if(odds&&"1X2".includes(R.k)&&R.k.length===1) q=implied(f.odds)["1X2".indexOf(R.k)];
    else if((R.k==="U"||R.k==="A")&&f&&f.ou&&f.ou[0]&&f.ou[1]) q=implied([f.ou[0],f.ou[1]])[R.k==="U"?0:1]; }catch(e){ q=null; }
  if(fin(q)){ const d=Math.round((R.cp-q)*100);
    I.push([2,`Piyasa ${E(R.n)} için <b>${yz(q)}</b> veriyor, OXXai <b>${yz(R.cp)}</b>${Math.abs(d)>=2?` (${Math.abs(d)} puan ${d>0?"yukarıda":"aşağıda"})`:" (aynı düzeyde)"}.`]); }
  else if(fin(r.H)) I.push([2,`OXXai olasılıkları: 1 <b>${yz(r.H)}</b> · X <b>${yz(r.D)}</b> · 2 <b>${yz(r.A)}</b>${fin(r.o25)?` · 2,5 Üst <b>${yz(r.o25)}</b>`:""}.`]);
  // 3) takım gücü (modelin kullandığı sezon hücum / savunma puanı; 1 = lig ortalaması)
  try{ const hT=findTeam(FP.inp.home), aT=findTeam(FP.inp.away);
    const fit=t=>{ if(!t) return null; if(r.source==="cup"){ const a=absRating(t); return a?{att:a.att,def:a.def}:null; } return FIT[t.lg]&&FIT[t.lg].t[t.name]||null; };
    const h=fit(hT), a=fit(aT);
    if(h&&a&&fin(h.att)&&fin(h.def)&&fin(a.att)&&fin(a.def)){ const gh=h.att/h.def, ga=a.att/a.def, g=gh>=ga?m.h:m.a, k=Math.max(gh,ga)/Math.min(gh,ga);
      I.push([5,`Takım gücü (hücum ÷ savunma, 1 = lig ortalaması): ${E(kisa(m.h))} <b>${n2(gh)}</b> · ${E(kisa(m.a))} <b>${n2(ga)}</b>${k>=1.1?` · ${E(kisa(g))} daha güçlü`:" · güçler yakın"}.`]); } }catch(e){}
  // 4) son form (modelde %30 ağırlıkla kullanılır; güç modeli yolunda 1X2'ye girmez)
  if(!guc){ const fm=F=>F&&F.list&&F.list.length?F.list.slice(-5).map(x=>{ const [a,b]=String(x.s).split("-").map(Number); return a>b?"G":a===b?"B":"M"; }).join(""):"";
    const a=fm(FP.F1), b=fm(FP.F2); if(a||b) I.push([7,`Son form (G galibiyet, B beraberlik, M mağlubiyet): ${E(kisa(m.h))} <b>${a||"–"}</b> · ${E(kisa(m.a))} <b>${b||"–"}</b>.`]); }
  // 5) beklenen gol
  if(fin(r.lh)&&fin(r.la)) I.push([4,`Beklenen gol: ${E(kisa(m.h))} <b>${n1(r.lh)}</b> – <b>${n1(r.la)}</b> ${E(kisa(m.a))} (toplam ${n1(r.lh+r.la)}).`]);
  // 6) taze veri (kadro / oran hareketi) yalnız kapıdan geçip uygulandıysa
  try{ const tz=(f&&Array.isArray(f.tz))?f.tz:[]; const s=[]; if(tz.some(x=>/^kadro_/.test(x))) s.push("son kadro bilgisi"); if(tz.some(x=>/^hareket_/.test(x))) s.push("oran hareketi");
    if(s.length) I.push([6,`Taze veri: ${s.join(" ve ")} olasılığı ayarladı.`]); }catch(e){}
  // 7) lig güveni (analist katsayısı, recOf ile aynı)
  try{ const comp=f&&(f.cn||f.ln), AF=(typeof ANALYST!=="undefined"&&ANALYST&&ANALYST.kabul&&comp)?(ANALYST.ligler||{})[comp]:null;
    if(AF&&fin(AF.k)&&Math.abs(AF.k-1)>=.005) I.push([8,`Lig güveni: bu ligde geçmiş öneriler ${AF.k<1?"söylenenden az":"söylenenden çok"} tuttu; yüzde ×${n2(AF.k)} ile düzeltildi.`]); }catch(e){}
  // 8) geçmiş isabet (kilitli kayıtların ilgili kovası; yoksa kalibrasyon tablosu)
  const kv=kova(typeof DAILY!=="undefined"&&DAILY&&DAILY.guvenilirlik&&DAILY.guvenilirlik.tum,R.cp,"tahmin");
  if(kv) I.push([3,kv]); else if(R.cn&&fin(R.ch)) I.push([3,`Geçmiş isabet: bu güvendeki ${n0(R.cn)} öneriden <b>%${Math.round(R.ch*100)}</b>'i tuttu.`]);
  const keep=I.slice().sort((x,y)=>x[0]-y[0]).slice(0,6);
  const ust=`${E(m.h)} – ${E(m.a)}<br>${R.tier==="w"?`<b>Pas</b> · net tahmin yok; en olası ${E(R.n)} <b>${yz(R.cp)}</b>`:`OXXai: <b>${E(R.n)}</b> <b>${yz(R.cp)}</b>`}`;
  return {ust, maddeler:I.filter(x=>keep.includes(x)).map(x=>x[1]), R}; }
// ---------- FUTBOL · canlı ----------
function fbCanli(lv){
  const P=idlPred(lv), K=P&&idlPick(lv,P); if(!K||!K.best) return null;
  const b=K.best, cp=Math.min(liveCal(b.p).p,.99), I=[];
  const t=fin(P.t)?Math.floor(P.t):null, rc=lv.rc||[0,0];
  I.push([1,`Durum: ${t!=null?`<b>${t}.</b> dakika · `:""}skor <b>${+lv.hs||0}-${+lv.as||0}</b>${(rc[0]||rc[1])?` · kırmızı kart ${E(kisa(lv.h))} ${rc[0]||0}, ${E(kisa(lv.a))} ${rc[1]||0}`:""}.`]);
  if(fin(P.LH)&&fin(P.LA)) I.push([2,`Kalan sürede beklenen gol: ${E(kisa(lv.h))} <b>${n1(P.LH)}</b> – <b>${n1(P.LA)}</b> ${E(kisa(lv.a))}${P.model==="cg"?" (canlı güç modeli: atılan gol takım gücünü günceller)":""}.`]);
  const SRC={iddaa:"iddaa bülteni",model:"OXXai modeli","canli-oran":"canlı orandan"};
  if(P.L&&fin(P.L[0])&&fin(P.L[1])&&SRC[P.src]) I.push([3,`Maç öncesi beklenti: <b>${n1(P.L[0])}</b> – <b>${n1(P.L[1])}</b> gol (${SRC[P.src]}).`]);
  if(P.adj&&fin(P.adj.mH)&&fin(P.adj.mA)&&(Math.abs(P.adj.mH-1)>=.01||Math.abs(P.adj.mA-1)>=.01)) I.push([5,`Maç istatistikleri (şut, topa sahip olma, korner) kalan gol beklentisini ${E(kisa(lv.h))} ×${n2(P.adj.mH)}, ${E(kisa(lv.a))} ×${n2(P.adj.mA)} değiştirdi.`]);
  let q=null; try{ const od=lv.odds||{};
    if("1X2".includes(b.k)&&b.k.length===1&&od.ms&&!od.ms.lock&&od.ms.v&&od.ms.v.every(x=>x>1)) q=implied(od.ms.v)["1X2".indexOf(b.k)];
    else if((b.k==="U"||b.k==="A")&&od.ou&&!od.ou.lock&&od.ou.alt>1&&od.ou.ust>1) q=implied([od.ou.ust,od.ou.alt])[b.k==="U"?0:1];
    else if(/^G[012]$/.test(b.k)&&od.ng&&!od.ng.lock&&od.ng.v&&od.ng.v.every(x=>x>1)) q=implied(od.ng.v)[{G1:0,G0:1,G2:2}[b.k]]; }catch(e){ q=null; }
  if(fin(q)) I.push([4,`Canlı oran ${b.o?`<b>${n2(b.o)}</b> `:""}→ piyasa <b>${yz(q)}</b> · OXXai <b>${yz(cp)}</b>${P.harman?"; canlı oranlar olasılığa sınanmış ağırlıkla katıldı":""}.`]);
  try{ const S=W.aiST&&W.aiST.get(String(lv.id)), Ii=typeof LGF!=="undefined"&&LGF.isaret;
    if(Ii&&S&&S.on) I.push([2,`Altın işaret: en güçlü canlı seçimin olasılığı %${Math.round(Ii.esik*100)} eşiğinin üstünde (oran en az 1,05, ${Ii.dkmax}. dakikadan önce).`]);
    else if(Ii&&t!=null&&t>=Ii.dkmax) I.push([6,`${Ii.dkmax}. dakikadan sonra altın işaret verilmez.`]); }catch(e){}
  const kv=kova(typeof DAILY!=="undefined"&&DAILY&&DAILY.canli&&DAILY.canli.guvenilirlik,cp,"canlı seçim"); if(kv) I.push([3,kv]);
  const keep=I.slice().sort((x,y)=>x[0]-y[0]).slice(0,6), tier=cp>=.70?"g":cp>=.58?"m":"w";
  const ust=`${E(lv.h)} – ${E(lv.a)} · CANLI<br>${tier==="w"?`<b>Pas</b> · en olası ${E(b.n)} <b>${yz(cp)}</b>`:`OXXai: <b>${E(b.n)}</b> <b>${yz(cp)}</b>`}`;
  return {ust, maddeler:I.filter(x=>keep.includes(x)).map(x=>x[1]), cp, b}; }
function fbAc(m,f){ let o=null; try{ const lv=m&&(m.sp===1?m:(m.iid||(f&&f.iid))?IDL.byId[1][m.iid||f.iid]:null); o=lv&&lv.sp===1&&(lv.min!=null||lv.hs!=null)?fbCanli(lv):fbOrt(m,f); }catch(e){ console.warn("neden-v145",e); }
  if(!o){ try{ toast("Bu maç için açıklama hesaplanamadı"); }catch(_){} return; } vz(6); kart(o); }
W.ndFb=fbOrt; W.ndCanli=fbCanli;
// maç penceresi: öneri kutusuna düğme
try{ const _mr=msRender; msRender=function(){ const r=_mr.apply(this,arguments); try{ const el=D.getElementById("msheet");
    if(el&&!el.hidden&&MS.m&&MS.tab==="tahmin"){ const rb=el.querySelector(".ms-body .recbig"); if(rb&&!rb.querySelector(".nd-b")) rb.insertAdjacentHTML("beforeend",`<button type="button" class="nd-b" data-nd="fb" aria-haspopup="dialog">ⓘ Neden bu tahmin?</button>`); } }catch(e){} return r; }; }catch(e){}
D.addEventListener("click",e=>{ const b=e.target.closest&&e.target.closest("#msheet .nd-b"); if(!b) return; e.preventDefault(); e.stopPropagation();
  try{ const lv=MS.live; if(lv&&lv.sp===1){ const o=fbCanli(lv); if(o){ vz(6); kart(o); return; } } }catch(_){}
  let o=null; try{ o=fbOrt(MS.m,MS.f); }catch(_){ o=null; } if(!o){ try{ toast("Bu maç için açıklama hesaplanamadı"); }catch(_){} return; } vz(6); kart(o); },true);
// ---------- uzun basma: bülten satırı, Canlı sekmesi satırı ----------
const LP={t:0,x:0,y:0,on:false,el:null};
const SATIR="#btList .ib-r[data-i],.lv-c[data-id]";
const HARIC="[data-mk],.kx-add,button,a,input,.star,.gold-seal";
function satirAc(row){ try{
  if(row.matches(".ib-r")){ const x=IB.rows[+row.dataset.i]; if(!x) return false; fbAc(x.m,x.f); return true; }
  const c=row.querySelector(".lclk"); if(c&&+c.dataset.sp!==1) return false; const m=IDL.byId[1][+row.dataset.id]; if(!m) return false;
  const o=fbCanli(m); if(!o) return false; vz(6); kart(o); return true; }catch(e){ console.warn("neden-v145",e); return false; } }
D.addEventListener("pointerdown",e=>{ if(e.button>0) return; const row=e.target.closest&&e.target.closest(SATIR); if(!row||e.target.closest(HARIC)) return;
  clearTimeout(LP.t); LP.on=false; LP.x=e.clientX; LP.y=e.clientY; LP.el=row;
  LP.t=setTimeout(()=>{ if(LP.el===row&&satirAc(row)) LP.on=true; },520); },true);
D.addEventListener("pointermove",e=>{ if(LP.el&&(Math.abs(e.clientX-LP.x)>10||Math.abs(e.clientY-LP.y)>10)){ clearTimeout(LP.t); LP.el=null; } },true);
["pointerup","pointercancel"].forEach(t=>D.addEventListener(t,()=>{ clearTimeout(LP.t); LP.el=null; },true));
D.addEventListener("scroll",()=>{ clearTimeout(LP.t); LP.el=null; },{passive:true,capture:true});
D.addEventListener("click",e=>{ if(!LP.on) return; LP.on=false; if(e.target.closest&&e.target.closest("#ndSheet")) return; e.preventDefault(); e.stopPropagation(); },true);
D.addEventListener("contextmenu",e=>{ const row=e.target.closest&&e.target.closest(SATIR); if(!row||e.target.closest(HARIC)) return; e.preventDefault(); clearTimeout(LP.t);
  if(LP.on) return; satirAc(row); },true);
// ---------- BASKET ----------
function bkNeden(f){ const p=bkPredict(f); if(!p||!p.L||!p.H||!p.A) return null;
  const L=p.L, H=p.H, A=p.A, k=L.kscale||1, I=[], fav=p.pH>=.5?f.h:f.a;
  const g=((H.off||0)+(A.def||0)-((A.off||0)+(H.def||0)))*k;
  if(fin(g)) I.push([1,`Takım gücü farkı (sezon hücum / savunma): ${Math.abs(g)<.5?"güçler yakın":`<b>${E(g>0?f.h:f.a)}</b> lehine <b>${n1(Math.abs(g))}</b> sayı`}.`]);
  if(f.neutral) I.push([2,`Tarafsız saha: ev avantajı hesaba katılmadı.`]); else if(fin(L.hca)) I.push([2,`Ev avantajı: ${E(kisa(f.h))} lehine <b>${n1(L.hca*k)}</b> sayı (bu ligin geçmiş maçlarından).`]);
  if(fin(f.yd)&&Math.abs(f.yd)>=.1) I.push([4,`Dinlenme / arka arkaya maç düzeltmesi: <b>${E(f.yd>0?f.h:f.a)}</b> lehine ${n1(Math.abs(f.yd))} sayı.`]);
  const od=f.odds, Dm=BK.data&&BK.data.market;
  if(f.cp&&f.cp.ph!=null) I.push([3,`Piyasa: oran çizgisi geçmiş maçlarda sınanıp tahmine çapa olarak eklendi${od&&od.spread!=null?` (handikap ${n1(od.spread)}${od.ou?`, toplam ${n1(od.ou)}`:""})`:""}.`]);
  else if(od&&od.spread!=null&&od.ou) I.push([3,`Piyasa çizgisi: handikap <b>${n1(od.spread)}</b>, toplam <b>${n1(od.ou)}</b>; tahmine %${Math.round(((L.syn&&Dm)?1:(Dm&&Dm.w!=null?Dm.w:.5))*100)} ağırlıkla katıldı.`]);
  else I.push([5,`Piyasa çizgisi yok; yalnız OXXai takım güçleri.`]);
  I.push([2,`Beklenen skor <b>${p.ms[0]}-${p.ms[1]}</b> · fark <b>${n1(Math.abs(p.mar))}</b> · toplam <b>${n1(p.tot)}</b> sayı.`]);
  const kv=kova(BK.data&&BK.data.live&&BK.data.live.guvenilirlik,Math.max(p.pH,p.pA),"maç"); if(kv) I.push([3,kv]);
  const keep=I.slice().sort((x,y)=>x[0]-y[0]).slice(0,6);
  return {ust:`${E(f.h)} – ${E(f.a)}<br>OXXai: <b>${E(fav)}</b> kazanır <b>${yz(Math.max(p.pH,p.pA))}</b>`, maddeler:I.filter(x=>keep.includes(x)).map(x=>x[1]), p}; }
W.ndBk=bkNeden;
try{ const _bo=bkOpen; bkOpen=function(f){ const r=_bo.apply(this,arguments); try{ const bx=D.getElementById("bkd"), bar=bx&&bx.querySelector(".bk-bar");
    if(bar&&!bx.querySelector(".nd-b")){ const nt=bar.nextElementSibling&&bar.nextElementSibling.matches("p.note")?bar.nextElementSibling:bar;
      nt.insertAdjacentHTML("afterend",`<button type="button" class="nd-b nd-bk" aria-haspopup="dialog">ⓘ Neden bu tahmin?</button>`);
      bx.querySelector(".nd-b").onclick=e=>{ e.preventDefault(); e.stopPropagation(); let o=null; try{ o=bkNeden(f); }catch(_){ o=null; } if(!o){ try{ toast("Bu maç için açıklama hesaplanamadı"); }catch(_){} return; } vz(6); kart(o); }; } }catch(e){} return r; }; }catch(e){}
// ---------- AT YARIŞI (ayrı) ----------
const AL={id:"İdman",hp:"Handikap puanı",st:"Start",hv:"Pist/hava",km:"Hız eğilimi",ms:"Mesafe",gl:"Gelişim",wfa:"Yaşa göre kilo"};
let AK=null, AKp=null;
function atKarne(){ if(AK) return Promise.resolve(AK); if(!AKp) AKp=fetch("data/at/karne.json",{cache:"no-cache"}).then(r=>r.ok?r.json():null).then(j=>{ AK=j; return j; }).catch(()=>null); return AKp; }
function atNeden(r,no){ const X=W.BX_AT; if(!X||!r) return null; const M=X.merged(r), A=M.A||[]; if(!A.length) return null;
  const by={}; for(const h of (M.c&&M.c.atlar)||[]) by[String(h.no)]=h;
  const x=no!=null?A.find(h=>String(h.no)===String(no)):A[0]; if(!x||!fin(x.p_goster)) return null;
  const rank=A.indexOf(x)+1, pq=(by[String(x.no)]||{}).p_piyasa, I=[];
  I.push(rank===1?`Sıra: koşudaki ${A.length} at arasında <b>en olası</b> at.`:`Sıra: koşudaki ${A.length} at arasında <b>${rank}.</b> sırada; en olası ${E(A[0].no)} ${E(A[0].ad)} ${yz(A[0].p_goster)}.`);
  let sg=[]; try{ const S=W.BX_AT_SIG&&W.BX_AT_SIG.sig(x)||{}; const ks=Object.keys(S).filter(k=>AL[k]); ks.sort((a,b)=>(S[a][1]==="g"?0:S[a][1]?2:1)-(S[b][1]==="g"?0:S[b][1]?2:1)); sg=ks.slice(0,3).map(k=>`${AL[k]}: <b>${E(S[k][0])}</b>`); }catch(e){}
  if(sg.length) I.push(`Modelin öne çıkan sinyalleri (koşudakilere göre): ${sg.join(" · ")}.`);
  else if(x.gerekce&&x.gerekce!=="belirgin artısı yok"&&!YASAK.test(x.gerekce)) I.push(`Modelin gerekçesi: ${E(String(x.gerekce).split(" · ").slice(0,2).join("; "))}.`);
  if(x.form) I.push(`Son koşu dereceleri: <b>${E(String(x.form).slice(-6).split("").join(" "))}</b> (sağdaki en yeni; 0 = ilk 9 dışı).`);
  if(fin(pq)&&fin(x.p_kazanma)){ const d=Math.round((x.p_kazanma-pq)*100); I.push(`Piyasa <b>${yz(pq)}</b> · sabah modeli <b>${yz(x.p_kazanma)}</b>${Math.abs(d)>=2?` (model ${Math.abs(d)} puan ${d>0?"daha iyimser":"daha temkinli"})`:" (aynı düzeyde)"}${x.p_oran!=null?"; gösterilen olasılık oranla güncellendi":""}.`); }
  else if(fin(x.p_kazanma)) I.push(`Piyasa verisi henüz yok; gösterilen olasılık sabah modeli (koşu sabahı kilitlendi).`);
  return {ust:`${E(r.hipodrom)} ${E(r.kosu)}. koşu · ${E(r.saat||"")}<br>OXXai: <b>${E(x.no)} ${E(x.ad)}</b> kazanır <b>${yz(x.p_goster)}</b>`, maddeler:I, x}; }
W.ndAt=atNeden;
function atAc(kid,no){ try{ const X=W.BX_AT, d=String(kid).split("/")[0], Dd=X&&X.AT&&X.AT.data&&X.AT.data[d], r=Dd&&(Dd.kosular||[]).find(z=>z.kosu_id===kid);
    const o=atNeden(r,no); if(!o){ toast("Bu koşu için açıklama hesaplanamadı"); return; } vz(6); const el=kart(o);
    atKarne().then(j=>{ const kv=kova(j&&j.guvenilirlik,o.x.p_goster,"at"); if(kv) ekle(el,kv); }); }catch(e){ console.warn("neden-v145",e); } }
D.addEventListener("click",e=>{ const b=e.target.closest&&e.target.closest("[data-nd-at]"); if(!b) return; e.preventDefault(); e.stopPropagation(); atAc(b.dataset.ndAt,b.dataset.ndNo||null); },true);
(function atKur(){ const box=D.getElementById("at2Box"), A2=W.BX_AT2; if(!box||!A2||!W.BX_AT) return;
  const dec=s=>{ try{ return decodeURIComponent(s); }catch(e){ return s; } }, unK=s=>String(s).split("~").map(dec).join("/");
  function run(){ try{ if(box.querySelector(".nd-at")) return; const rt=A2.route(); if(!rt||(rt.v!=="kosu"&&rt.v!=="at")) return;
      const kid=unK(rt.a[0]||""), d=kid.split("/")[0], Dd=W.BX_AT.AT.data&&W.BX_AT.AT.data[d], r=Dd&&(Dd.kosular||[]).find(z=>z.kosu_id===kid); if(!r) return;
      const rh=box.querySelector(".a2-rh"); if(!rh) return;
      const M=W.BX_AT.merged(r), x=rt.v==="at"?(M.A||[]).find(h=>String(h.no)===String(rt.a[1])):(M.A||[])[0]; if(!x) return;
      rh.insertAdjacentHTML("afterend",`<button type="button" class="nd-b nd-at" data-nd-at="${E(kid)}"${rt.v==="at"?` data-nd-no="${E(x.no)}"`:""} aria-haspopup="dialog">ⓘ Neden bu tahmin?${rt.v==="kosu"?` <small>${E(x.no)} ${E(x.ad)}</small>`:""}</button>`); }catch(e){} }
  new MutationObserver(run).observe(box,{childList:true}); run(); })();
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: neden-v145 */
