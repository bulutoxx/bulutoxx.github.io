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
const ara=!!BT.q, yeni=ara&&sigB()!==bLast; const y=ara?scrollY:0;   // v150: aramada değilse scrollY okunmaz (zorunlu yerleşim yok)
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
/* id: aralik-v146 */ try {
(function(){
// YH-26: basket %80 aralık (uyumlu / conformal). Yalnız lab/aralik_lab.py sınamasında kapsaması kanıtlanan lig × hedef için
// (data/bk_aralik.json). Aralıklar OXXai takım-gücü tahmini üzerinde sınandığından, piyasa çizgisiyle birleştirilen maçta gösterilmez.
const D=document; let AR=null;
fetch("data/bk_aralik.json",{cache:"no-cache"}).then(r=>r.ok?r.json():null).then(j=>{ AR=j; }).catch(()=>{});
const n0=x=>String(Math.round(x)), sg=x=>(x>0?"+":x<0?"−":"")+Math.abs(Math.round(x));
function satir(f,p){ if(!AR||!AR.aktif||!p||p.mkt) return ""; const c=AR.ligler&&AR.ligler[f.lg]; if(!c) return "";
  const L=p.L||{}, out=[];
  if(c.toplam&&isFinite(p.tot)) out.push(`toplam <b>${n0(p.tot+c.toplam.alt)}–${n0(p.tot+c.toplam.ust)}</b> sayı`);
  if(c.fark&&isFinite(p.mar)&&(L.kscale||1)===1&&!f.yd) out.push(`fark (ev − dep.) <b>${sg(p.mar+c.fark.alt)} … ${sg(p.mar+c.fark.ust)}</b>`);
  if(!out.length) return "";
  return `<p class="note ar-80" title="Geçmiş maçlarda bu aralık sonuçların yaklaşık %80'ini kapsadı (zaman sıralı sınama)">%80 aralık: ${out.join(" · ")}</p>`; }
try{ const _bo=bkOpen; bkOpen=function(f){ const r=_bo.apply(this,arguments); try{ const bx=D.getElementById("bkd"), bar=bx&&bx.querySelector(".bk-bar");
    if(bar&&!bx.querySelector(".ar-80")){ const h=satir(f,bkPredict(f)); if(h){ const nt=bar.nextElementSibling&&bar.nextElementSibling.matches("p.note")?bar.nextElementSibling:bar; nt.insertAdjacentHTML("afterend",h); } } }catch(e){} return r; }; }catch(e){}
window.BX_ARALIK={satir, get veri(){ return AR; }};
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: aralik-v146 */
/* id: masaustu-v150 */ try {
// =====================================================================
// OXXai v150 · MASAÜSTÜ: akıcı gezinme, gol uyarısı / ses / sistem bildirimi
// Kök nedenler (şikâyet: "desktopta menü çok ağır ilerliyor", "gol uyarısı ve sesler gelmiyor"):
//  1) goldOf() her satırda goldCalc() → imza için Pick.list() (1300+ maç) çağırıyordu: Canlı/Bülten çiziminde satır × maç
//     (≈2500 × 1357) döngü → sekme geçişinde 0,5–2 sn uzun görev, bülten kaydırırken yeni parça yüklenince takılma.
//     Çözüm: aynı eşzamanlı çizim içinde goldCalc() sonucu bir kez hesaplanır (mikro görev sonunda sıfırlanır; sonuç birebir aynı).
//  2) Masaüstünde sayfa çoğu zaman arka planda / başka pencerenin altında (document.hidden) kalıyor: zamanlayıcılar duruyor,
//     ses ve uyarılar "gizli" diye atlanıyor, gol kartı 7 sn sonra kimse görmeden kapanıyordu.
//     Çözüm (yalnız fare + hover cihazlarda; telefonda hiçbir şey değişmez): takip edilen canlı maç varken arka planda 30 sn'de
//     bir canlı skor tazelenir; gol kartı kullanıcı dönene kadar açık kalır; sekme başlığında "⚽ GOL!" ve simgede rozet;
//     dönünce kaçırılan olayların kısa özeti; Ayarlar › Sesler › "Masaüstü bildirimleri" açıksa (izin yalnız dokununca istenir)
//     pencere arkadayken sistem bildirimi.
// =====================================================================
(function(){ "use strict";
  const W=window, D=document;
  // ---------- 1) Altın hesabı: çizim başına bir kez ----------
  try{ if(typeof goldCalc==="function"){ const _gc=goldCalc; let memo=null, plan=false;
      goldCalc=function(){ if(memo) return memo; const r=_gc.apply(this,arguments); memo=r;
        if(!plan){ plan=true; Promise.resolve().then(()=>{ memo=null; plan=false; }); } return r; }; } }catch(e){}

  // ---------- alt boşluk: içerik alt menü + POWER NOW + yüzen çubukların arkasında kalmasın (her genişlikte; CSS en az 120 px tutar) ----------
  function altOlc(){ try{ const H=W.innerHeight; let top=H;
      D.querySelectorAll("nav.tabs, nav.tabs .pw-logo, #at3Bar").forEach(el=>{ if(!el.offsetParent&&getComputedStyle(el).position!=="fixed") return; const r=el.getBoundingClientRect(); if(r.width>0&&r.height>0&&r.bottom>H*.6&&r.top<top) top=r.top; });
      const v=Math.max(0,Math.round(H-top)); if(v!==altOlc.v){ altOlc.v=v; D.documentElement.style.setProperty("--oxx-alt",v+"px"); } }catch(e){} }
  altOlc(); W.addEventListener("resize",altOlc,{passive:true}); D.addEventListener("click",()=>setTimeout(altOlc,350),{capture:true,passive:true}); setTimeout(altOlc,1500);
  // ---------- 2) Masaüstü uyarıları ----------
  const DT=(()=>{ try{ return matchMedia("(hover:hover) and (pointer:fine)").matches; }catch(e){ return false; } })();
  W.OXX_DT={ dt:DT };
  if(!DT) return;
  const away=()=>D.hidden===true||(typeof D.hasFocus==="function"&&!D.hasFocus());
  const hasN=()=>"Notification" in W;
  const pr=()=>{ try{ return PREFS; }catch(e){ return {}; } };
  W.oxxDtBildir=function(){ return pr().dtBildirim!==false&&away(); };
  const KAC=[]; let bekle=false, baslik0=null, ikon0=null;
  // sekme başlığı + simge rozeti
  function isaret(txt){ try{ if(baslik0==null) baslik0=D.title; D.title="⚽ GOL! "+txt; }catch(e){}
    try{ const L=[...D.querySelectorAll('link[rel="icon"]')]; if(!L.length) return; if(!ikon0) ikon0=L.map(l=>l.getAttribute("href"));
      const img=new Image(); img.onload=()=>{ try{ const c=D.createElement("canvas"); c.width=c.height=64; const x=c.getContext("2d"); x.drawImage(img,0,0,64,64);
        x.beginPath(); x.arc(46,18,16,0,Math.PI*2); x.fillStyle="#FF3B30"; x.fill(); x.lineWidth=4; x.strokeStyle="#03060D"; x.stroke();
        x.fillStyle="#fff"; x.font="bold 22px system-ui,sans-serif"; x.textAlign="center"; x.textBaseline="middle"; x.fillText(String(Math.min(9,KAC.length||1)),46,19);
        const u=c.toDataURL("image/png"); L.forEach(l=>l.setAttribute("href",u)); }catch(e){} }; img.src=ikon0[0]; }catch(e){} }
  function temizle(){ try{ if(baslik0!=null){ D.title=baslik0; baslik0=null; } }catch(e){}
    try{ if(ikon0){ const L=[...D.querySelectorAll('link[rel="icon"]')]; L.forEach((l,i)=>l.setAttribute("href",ikon0[i]||ikon0[0])); ikon0=null; } }catch(e){} }
  W.oxxDtKacan=function(name,msg){ if(!away()) return; KAC.push(String(msg||"")); };
  // gol kartı: kullanıcı yokken kapanmasın
  try{ const _nx=Goal.next; Goal.next=function(){ const it=this.queue[0]; const r=_nx.apply(this,arguments);
      try{ if(it&&this.open&&away()){ clearTimeout(this.t); this.t=0; bekle=true; const e=it.e, t=`${e.h} ${e.hs}-${e.as} ${e.a}`; KAC.push("⚽ "+t); isaret(t); } }catch(e){}
      return r; }; }catch(e){}
  function don(){ if(away()) return; temizle();
    if(KAC.length){ const n=KAC.filter(x=>/^⚽/.test(x)).length, L=KAC.splice(0);
      try{ toast((n?`Sen yokken ${n} gol oldu · `:"Sen yokken · ")+L.slice(-3).map(x=>x.replace(/^⚽\s*/,"")).join(" · ")); }catch(e){} }
    if(bekle){ bekle=false; try{ if(Goal.open){ clearTimeout(Goal.t); Goal.t=setTimeout(()=>{ const b=D.getElementById("goalClose"); if(b) b.click(); },7000); } }catch(e){} } }
  D.addEventListener("visibilitychange",don); W.addEventListener("focus",don);
  // arka planda takip edilen canlı maçlar: 30 sn'de bir canlı skor (yerel setTimeout; ortak planlayıcı gizliyken durur)
  function izlenen(){ try{ return (IDL.live[1]||[]).some(m=>FOLLOW.has("i"+m.id)&&m.st!==3); }catch(e){ return false; } }
  let son=0;
  (function dongu(){ setTimeout(()=>{ try{ if(D.hidden&&izlenen()&&Date.now()-son>=28e3&&Date.now()-((IDL.at&&IDL.at[1])||0)>=25e3){ son=Date.now(); IDL.load(1,true).catch(()=>{}); } }catch(e){} dongu(); },30e3); })();
  // ---------- Ayarlar › Sesler › Masaüstü bildirimleri ----------
  const E=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const acik=()=>hasN()&&Notification.permission==="granted"&&pr().dtBildirim!==false;
  const altTx=()=>!hasN()?"Bu tarayıcı sistem bildirimi desteklemiyor":Notification.permission==="denied"?"Tarayıcı izni kapalı · adres çubuğundaki site ayarlarından açabilirsin":acik()?"Pencere arkadayken gol olunca sistem bildirimi":"Açınca tarayıcı bir kez izin ister";
  function hucre(set){ if(!set||set.querySelector("#dtBil")) return;
    set.insertAdjacentHTML("beforeend",`<div class="cell dt-bil"><span class="ic gold" aria-hidden="true">🔔</span><span class="tx"><b>Masaüstü bildirimleri</b><small id="dtBilTx">${E(altTx())}</small></span><label class="sw"><input type="checkbox" id="dtBil" ${acik()?"checked":""} ${hasN()?"":"disabled"} aria-label="Masaüstü bildirimleri"><i></i></label></div>`);
    const inp=set.querySelector("#dtBil"), tx=set.querySelector("#dtBilTx");
    inp.addEventListener("change",async()=>{ const P=pr();
      if(inp.checked){ let p=Notification.permission; if(p==="default"){ try{ p=await Notification.requestPermission(); }catch(e){} }
        if(p==="granted"){ P.dtBildirim=true; try{ toast("Masaüstü bildirimleri açık · pencere arkadayken gol olunca haber veririm"); }catch(e){} }
        else { inp.checked=false; P.dtBildirim=false; try{ toast("Tarayıcı izin vermedi · adres çubuğundaki site ayarlarından açabilirsin"); }catch(e){} } }
      else P.dtBildirim=false;
      try{ savePrefs(); }catch(e){} if(tx) tx.textContent=altTx(); }); }
  const sh=D.getElementById("sheet");
  if(sh) new MutationObserver(()=>{ const s=sh.querySelector("#sesSet"); if(s) hucre(s); }).observe(sh,{childList:true});
  W.OXX_DT.durum=()=>({kacan:KAC.slice(),bekle,baslik:D.title,izlenen:izlenen()});
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: masaustu-v150 */
/* id: at-kapali-v152 */ try {
// =====================================================================
// v152 · At yarışı bölümü kapalıyken uygulama davranışı (bayrak: data/ozellik.json, kapı: baslangic.js "ozellik-v152").
//  • showSport("at") / goView("at") → Bülten'e yönlenir; #at… adresi temizlenir (derin bağlantı, geri tuşu, kayıtlı spor seçimi).
//  • OXXai at sorularına kısa "bölüm kapalı" cevabı verir (at katmanının cevabından önce).
//  • Bayrak at:true gelirse hiçbir şey yapmaz (eski davranış birebir); bayrak bilinmezken at isteği bayrağı bekler.
// =====================================================================
(function(){
  const W=window, OZ=W.OXX_OZ; if(!OZ) return;
  const kapali=()=>OZ.at!==true;
  const atHash=()=>/^#at(\/|$)/.test(location.hash||"");
  let _ss=null;
  function yonlen(){ try{ if(atHash()) history.replaceState(history.state,"",location.pathname+location.search); }catch(e){}
    try{ if(_ss) _ss.call(W,"fb"); }catch(e){} }
  if(typeof showSport==="function"){ _ss=showSport;
    showSport=function(s){ if(s!=="at"||!kapali()) return _ss.apply(this,arguments);
      if(OZ.at===null){ const t=this, a=arguments; OZ.hazir.then(on=>{ if(on) _ss.apply(t,a); else yonlen(); }); return; }
      return yonlen(); }; }
  if(typeof goView==="function"){ const _gv=goView;
    goView=function(v){ if(v==="at"&&OZ.at===false) return _gv.call(this,"bulten","bulten"); return _gv.apply(this,arguments); }; }
  OZ.hazir.then(on=>{ if(on) return; if(atHash()) yonlen();
    try{ const v=document.getElementById("v-at"); if(v&&!v.hidden) yonlen(); }catch(e){} });
  // YH-65: at paketleri yüklenmediyse (bölüm kapalı) at katmanının yaptığı iki görünür işi burada yap:
  // #at… adresine sonradan geçiş (hashchange) Bülten'e döner; spor seçicide "🏀 Basket" kısa adı (at açıkken olduğu gibi).
  if(!OZ.atPaket){
    W.addEventListener("hashchange",()=>{ if(kapali()&&atHash()) yonlen(); });
    try{ document.querySelectorAll(".sport-sw button[data-s=\"bk\"]").forEach(b=>{ if(!b.dataset.sh){ b.dataset.sh=1; b.innerHTML="🏀 Basket"; } }); }catch(e){}
  }
  // ---------- OXXai ----------
  const NZ=t=>String(t||"").toLocaleLowerCase("tr").replace(/ç/g,"c").replace(/ğ/g,"g").replace(/ı/g,"i").replace(/ö/g,"o").replace(/ş/g,"s").replace(/ü/g,"u").replace(/[^a-z0-9 .]/g," ").replace(/\s+/g," ").trim();
  const AKEY=/\b(at yarisi|at yarislari|atyarisi|kosu|kosular|kosusu|ganyan|hipodrom|jokey|plase|veliefendi|atlar|padok|altin atlar)\b|\bat (bolum|yaris|kupo)\w*/;
  const ALTK=/\b(6 ?li|altili)\b/, FUTK=/\b(kupon|kuponu|mac|maci|maclar|futbol|basket|iddaa|lig)\b/;
  const CEVAP={html:"🐎 At yarışı bölümü şu an kapalı (veri kaynağı güncellenmiyor). Kaynak yeniden güncellenince bölüm geri açılacak. Futbol ve basket tahminleri aynen çalışıyor.",chips:["Bugün hangi maçlar var","En güvenli maçlar"]};
  OZ.atSorusu=raw=>{ const n=NZ(raw); return AKEY.test(n)||(ALTK.test(n)&&!FUTK.test(n)); };
  if(typeof botAnswer==="function"){ const _ba=botAnswer;
    botAnswer=async function(raw){ try{ if(kapali()&&OZ.atSorusu(raw)) return Object.assign({},CEVAP); }catch(e){} return _ba.apply(this,arguments); }; }
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: at-kapali-v152 */
/* id: cek-yenile-v153 */
try {
/* v153: Aşağı çekerek yenile (iPhone/Android). Sayfa en üstteyken parmakla aşağı çekilince
   mevcut "Güncelle" akışı (doRefresh) çalışır. Açık pencere/kaydırılmış iç alan/yatay kaydırmada devre dışı. */
(function(){
  if(!("ontouchstart" in window)) return;
  const ESIK=72, TAVAN=110;
  const ind=document.createElement("div"); ind.id="cekYen"; ind.setAttribute("aria-hidden","true");
  ind.innerHTML='<svg viewBox="0 0 24 24"><path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/></svg>';
  document.body.appendChild(ind);
  let y0=0,x0=0,dy=0,aktif=false,karar=0,mesgul=false;
  const engel=t=>{ for(let el=t; el&&el!==document.body&&el.nodeType===1; el=el.parentElement){
      if(el.matches&&el.matches("input,textarea,select,[contenteditable],.topbar")) return el.matches(".topbar")?false:true;
      const cs=getComputedStyle(el);
      if(cs.position==="fixed") return true;                                   // açık pencere / alt sayfa / alt menü
      if(el.scrollTop>0 && /(auto|scroll)/.test(cs.overflowY)) return true;      // iç kaydırma alanı yukarıda değil
    } return false; };
  const ciz=d=>{ const p=Math.min(1,d/ESIK); ind.style.transform=`translate(-50%,${Math.min(d,TAVAN)-48}px) rotate(${p*270}deg)`;
    ind.style.opacity=String(Math.min(1,p*1.3)); ind.classList.toggle("hazir",d>=ESIK); };
  const sifirla=()=>{ ind.classList.add("don"); ind.style.transform="translate(-50%,-48px)"; ind.style.opacity="0"; ind.classList.remove("hazir","doner");
    setTimeout(()=>ind.classList.remove("don"),260); };
  document.addEventListener("touchstart",e=>{
    aktif=false; karar=0; dy=0;
    if(mesgul||e.touches.length!==1||(window.scrollY||document.documentElement.scrollTop)>0) return;
    if(engel(e.target)) return;
    y0=e.touches[0].clientY; x0=e.touches[0].clientX; aktif=true;
  },{passive:true});
  document.addEventListener("touchmove",e=>{
    if(!aktif) return;
    const t=e.touches[0], ddy=t.clientY-y0, ddx=t.clientX-x0;
    if(!karar){ if(Math.abs(ddy)<8&&Math.abs(ddx)<8) return;
      karar=(ddy>0&&Math.abs(ddy)>Math.abs(ddx)*1.3)?1:-1; if(karar<0){ aktif=false; return; } }
    if((window.scrollY||0)>0){ aktif=false; sifirla(); return; }
    dy=Math.max(0,ddy)*0.55;                                                   // direnç
    if(e.cancelable) e.preventDefault();
    ciz(dy);
  },{passive:false});
  const birak=async()=>{
    if(!aktif) return; aktif=false;
    if(dy<ESIK){ sifirla(); return; }
    mesgul=true; ind.classList.add("doner"); ind.style.transform="translate(-50%,24px)"; ind.style.opacity="1";
    try{ if(navigator.vibrate) navigator.vibrate(10); }catch(e){}
    const t0=Date.now();
    try{ if(typeof doRefresh==="function") await doRefresh(); else { const b=document.getElementById("refreshBtn"); if(b) b.click(); } }catch(e){}
    const kalan=700-(Date.now()-t0); if(kalan>0) await new Promise(r=>setTimeout(r,kalan));
    mesgul=false; sifirla();
  };
  document.addEventListener("touchend",birak,{passive:true});
  document.addEventListener("touchcancel",()=>{ if(aktif){ aktif=false; sifirla(); } },{passive:true});
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: cek-yenile-v153 */

/* id: kg-piyasa-v165 */ try {
(function(){
  // YH-55 (2026-11-08): KG Var olasılığına iddaa KG oranı katılır. Kanıt: lab/kg_piyasa_lab.py → data/kg_piyasa_lab.json
  // (kilitli bülten, 3.295 sınama maçı: log-kayıp 0,6957 → 0,6871). Ayar motordan gelir (model.json params.kg_piyasa = {w});
  // alan yoksa (bayrak kapalı / geri alındı) hiçbir şey değişmez. Yalnız oranlı ve KG oranı (f.ikg) olan fikstür tahmininde.
  if(typeof predict!=="function") return;
  let KG=null;
  const ayar=()=>{ const P=(typeof MODEL!=="undefined"&&MODEL&&MODEL.params)||null, a=P&&P.kg_piyasa; return a&&a.w>0&&a.w<=1?a:null; };
  const lg=x=>{ x=Math.min(Math.max(x,1e-6),1-1e-6); return Math.log(x/(1-x)); };
  const _p=predict;
  predict=function(inp){
    const r=_p.apply(this,arguments);
    try{
      const a=ayar(), k=KG;
      if(a&&k&&r&&typeof r.btts==="number"&&!r.kgPiy&&inp&&inp.odds&&inp.odds.o1&&inp.odds.ox&&inp.odds.o2){
        const q=(1/k[0])/((1/k[0])+(1/k[1])), z=a.w*lg(q)+(1-a.w)*lg(r.btts);
        r.kgDist=r.btts; r.btts=1/(1+Math.exp(-z)); r.kgPiy=1;
      }
    }catch(e){}
    return r;
  };
  const sar=ad=>{ const f=window[ad]; if(typeof f!=="function") return;
    window[ad]=function(m,fx){ const o=KG, g=fx&&fx.ikg; KG=(Array.isArray(g)&&g.length===2&&g[0]>1&&g[1]>1)?g:null;
      try{ return f.apply(this,arguments); } finally{ KG=o; } }; };
  sar("quickPred"); sar("fullPred");
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: kg-piyasa-v165 */

/* id: ekran-acik-v179 */
try {
/* v179: OXXai açıkken ekran kararmasın (Ayarlar › "Ekran açık kalsın", varsayılan açık).
   Screen Wake Lock API; desteklemeyen/reddeden cihazlarda sessiz, görünmez küçük video döngüsü (ilk dokunuşta başlar).
   Uygulamadan çıkınca / arka plana alınınca kilit kendiliğinden bırakılır, geri dönünce yeniden alınır. */
(function(){
  const acik=()=>{ try{ return typeof PREFS==="undefined"||PREFS.awake!==false; }catch(e){ return true; } };
  let kilit=null, vid=null;
  async function al(){
    if(!acik()||document.hidden) return;
    if("wakeLock" in navigator){
      if(kilit&&!kilit.released) return;
      try{ kilit=await navigator.wakeLock.request("screen"); kilit.addEventListener("release",()=>{ kilit=null; }); return; }catch(e){ /* bazı ana ekran uygulamalarında reddedilir → video yöntemi */ }
    }
    try{ if(!vid){ vid=document.createElement("video"); vid.setAttribute("playsinline",""); vid.setAttribute("muted",""); vid.muted=true; vid.loop=true;
        vid.setAttribute("aria-hidden","true"); vid.style.cssText="position:fixed;width:1px;height:1px;opacity:0;pointer-events:none;left:-10px;top:-10px";
        vid.src="data:video/mp4;base64,AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAMpbW9vdgAAAGxtdmhkAAAAAAAAAAAAAAAAAAAD6AAAB9AAAQAAAQAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAlN0cmFrAAAAXHRraGQAAAADAAAAAAAAAAAAAAABAAAAAAAAB9AAAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAABAAAAAABAAAAAQAAAAAAAkZWR0cwAAABxlbHN0AAAAAAAAAAEAAAfQAAAAAAABAAAAAAHLbWRpYQAAACBtZGhkAAAAAAAAAAAAAAAAAABAAAAAgABVxAAAAAAALWhkbHIAAAAAAAAAAHZpZGUAAAAAAAAAAAAAAABWaWRlb0hhbmRsZXIAAAABdm1pbmYAAAAUdm1oZAAAAAEAAAAAAAAAAAAAACRkaW5mAAAAHGRyZWYAAAAAAAAAAQAAAAx1cmwgAAAAAQAAATZzdGJsAAAAtnN0c2QAAAAAAAAAAQAAAKZhdmMxAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAABAAEABIAAAASAAAAAAAAAABFUxhdmM2MC4zMS4xMDIgbGlieDI2NAAAAAAAAAAAAAAAGP//AAAALGF2Y0MBQsAK/+EAFWdCwAraewEQAAADABAAAAMAIPEiagEABGjOD8gAAAAQcGFzcAAAAAEAAAABAAAAFGJ0cnQAAAAAAAAKMAAACjAAAAAYc3R0cwAAAAAAAAABAAAAAgAAQAAAAAAUc3RzcwAAAAAAAAABAAAAAQAAABxzdHNjAAAAAAAAAAEAAAABAAAAAgAAAAEAAAAcc3RzegAAAAAAAAAAAAAAAgAAAoMAAAAJAAAAFHN0Y28AAAAAAAAAAQAAA1kAAABidWR0YQAAAFptZXRhAAAAAAAAACFoZGxyAAAAAAAAAABtZGlyYXBwbAAAAAAAAAAAAAAAAC1pbHN0AAAAJal0b28AAAAdZGF0YQAAAAEAAAAATGF2ZjYwLjE2LjEwMAAAAAhmcmVlAAAClG1kYXQAAAJtBgX//2ncRem95tlIt5Ys2CDZI+7veDI2NCAtIGNvcmUgMTY0IHIzMTA4IDMxZTE5ZjkgLSBILjI2NC9NUEVHLTQgQVZDIGNvZGVjIC0gQ29weWxlZnQgMjAwMy0yMDIzIC0gaHR0cDovL3d3dy52aWRlb2xhbi5vcmcveDI2NC5odG1sIC0gb3B0aW9uczogY2FiYWM9MCByZWY9MSBkZWJsb2NrPTE6MDowIGFuYWx5c2U9MHgxOjB4MSBtZT1oZXggc3VibWU9MiBwc3k9MSBwc3lfcmQ9MS4wMDowLjAwIG1peGVkX3JlZj0wIG1lX3JhbmdlPTE2IGNocm9tYV9tZT0xIHRyZWxsaXM9MCA4eDhkY3Q9MCBjcW09MCBkZWFkem9uZT0yMSwxMSBmYXN0X3Bza2lwPTEgY2hyb21hX3FwX29mZnNldD0wIHRocmVhZHM9MSBsb29rYWhlYWRfdGhyZWFkcz0xIHNsaWNlZF90aHJlYWRzPTAgbnI9MCBkZWNpbWF0ZT0xIGludGVybGFjZWQ9MCBibHVyYXlfY29tcGF0PTAgY29uc3RyYWluZWRfaW50cmE9MCBiZnJhbWVzPTAgd2VpZ2h0cD0wIGtleWludD0yNTAga2V5aW50X21pbj0xIHNjZW5lY3V0PTQwIGludHJhX3JlZnJlc2g9MCByY19sb29rYWhlYWQ9MTAgcmM9Y3JmIG1idHJlZT0xIGNyZj0yMy4wIHFjb21wPTAuNjAgcXBtaW49MCBxcG1heD02OSBxcHN0ZXA9NCBpcF9yYXRpbz0xLjQwIGFxPTE6MS4wMACAAAAADmWIhAW///8PRQABT3+AAAAABUGaIBX1"; document.body.appendChild(vid); }
      if(vid.paused) await vid.play(); }catch(e){}
  }
  function birak(){ try{ if(kilit){ kilit.release(); kilit=null; } }catch(e){} try{ if(vid&&!vid.paused) vid.pause(); }catch(e){} }
  document.addEventListener("visibilitychange",()=>{ if(document.hidden) birak(); else al(); });
  ["pointerdown","touchend","click"].forEach(ev=>document.addEventListener(ev,()=>{ if(acik()) al(); },{passive:true,capture:true}));
  document.addEventListener("change",e=>{ const t=e.target; if(t&&t.id==="p-awake"){ if(t.checked){ al(); try{ toast("Ekran açık kalacak"); }catch(x){} } else birak(); } },true);
  window.oxxEkran={al,birak,durum:()=>({api:"wakeLock" in navigator,kilit:!!(kilit&&!kilit.released),video:!!(vid&&!vid.paused),acik:acik()})};
  al();
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: ekran-acik-v179 */
/* id: saha-v180 */ try {
// =====================================================================
// v180 · CANLI MAÇ SAHA GRAFİĞİ (maç penceresi › "Saha" sekmesi; canlı ve biten futbol maçları)
// • Kaynak: ESPN maç özeti (summary) → commentary[].play içinden YALNIZ olay türü, dakika, takım ve saha konumu
//   (fieldPositionX/Y, şutlarda hedef fieldPosition2X/Y). Yorum metni (text) hiçbir yerde okunmaz, gösterilmez, saklanmaz;
//   olay adları kendi Türkçe etiketlerimizdir. Ham yanıt bellekte bile tutulmaz (yalnız ayrıştırılmış küçük olay listesi).
// • Konumlar olayı yapan takımın hücum yönüne göredir (X=100 rakip kale). Çizimde ev sahibi sağa hücum eder:
//   deplasman konumları x'=100−x, y'=100−y ile çevrilir. Tek SVG, en çok 60 işaret; en yeni olay nabız animasyonlu.
// • Baskı grafiği: dakika başına tehlike puanı (gol 5, isabetli şut 3, direk 3, engellenen/isabetsiz şut 2, korner 1,5,
//   rakip yarı sahada faul kazanımı 0,5; X>66 bölgede ×1,3) ve 5 dk kayan ortalama; ev üstte, deplasman altta.
//   Konum/olay vermeyen liglerde (ör. Süper Lig) istatistik geçmişinden (şut, isabetli şut, korner farkları; canli-gt
//   deposu + bu katmanın kendi ölçümleri) dakika aralıklarına dağıtılmış kaba baskı — "İstatistikten tahmini" etiketiyle.
// • Yenileme: sekme açıkken canlı maçta 30 sn'de bir; sayfa gizliyken istek yok (istek-v124 önbelleği zaten 20 sn).
//   "Güncel tahmin" akışı değişmez (canli-gt kartı bu sekmede de üstte kalır).
// • Bayrak: data/ozellik.json → "saha": true. Değilse (false / dosya yok) sekme hiç çizilmez.
// =====================================================================
(function(){
  "use strict";
  if(typeof msRender!=="function"||typeof MS==="undefined"||typeof ESPN==="undefined") return;
  const W=window, FL={on:false,bilinen:false};
  const E_=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const kisa=n=>{ try{ return shortTeam(n); }catch(e){ return String(n||""); } };
  const esit=(x,y)=>{ try{ return tmEq(x,y); }catch(e){ return String(x||"").toLowerCase()===String(y||"").toLowerCase(); } };
  const sayi=v=>{ const x=typeof v==="number"?v:parseFloat(v); return isFinite(x)?x:null; };
  try{ fetch("data/ozellik.json?t="+Date.now(),{cache:"no-store"}).then(r=>r&&r.ok?r.json():null)
    .then(j=>{ FL.bilinen=true; FL.on=!!(j&&j.saha===true); if(FL.on&&MS.m){ try{ msRender(); }catch(e){} } }).catch(()=>{ FL.bilinen=true; }); }catch(e){}

  // ---------- olay türleri (kendi etiketlerimiz) ----------
  // k: iç anahtar · w: tehlike puanı · s: şut mu (hedef çizgisi)
  function tur(t){ const s=String(t||"").toLowerCase().replace(/\s+/g,"-");
    if(!s) return null;
    if(/own-goal/.test(s)) return {k:"og",l:"Kendi kalesine gol",w:0};
    if(/penalty.*(scored|goal)/.test(s)) return {k:"goal",l:"Penaltı golü",w:5,s:1};
    if(/penalty.*(missed|saved)/.test(s)) return {k:"pmiss",l:"Kaçan penaltı",w:3,s:1};
    if(/penalty.*(awarded|won|conceded)/.test(s)) return {k:"pen",l:"Penaltı kararı",w:2};
    if(/^goal/.test(s)) return {k:"goal",l:"Gol",w:5,s:1};
    if(/woodwork|hit-(the-)?(post|bar)/.test(s)) return {k:"wood",l:"Direkten döndü",w:3,s:1};
    if(/blocked/.test(s)) return {k:"blk",l:"Engellenen şut",w:2,s:1};
    if(/on-target|saved/.test(s)) return {k:"sot",l:"İsabetli şut",w:3,s:1};
    if(/off-target|missed|wide/.test(s)) return {k:"off",l:"İsabetsiz şut",w:2,s:1};
    if(/^shot|attempt/.test(s)) return {k:"off",l:"Şut",w:2,s:1};
    if(/corner/.test(s)) return {k:"cor",l:"Korner",w:1.5};
    if(/yellow-red|second-yellow/.test(s)) return {k:"rc",l:"İkinci sarıdan kırmızı",w:0};
    if(/red-card/.test(s)) return {k:"rc",l:"Kırmızı kart",w:0};
    if(/yellow/.test(s)) return {k:"yc",l:"Sarı kart",w:0};
    if(/hand-?ball/.test(s)) return {k:"hand",l:"Elle oynama",w:0};
    if(/^foul/.test(s)) return {k:"foul",l:"Faul",w:0};
    if(/offside/.test(s)) return {k:"ofs",l:"Ofsayt",w:0};
    if(/substitution/.test(s)) return {k:"sub",l:"Oyuncu değişikliği",w:0};
    if(/free-kick/.test(s)) return {k:"fk",l:"Serbest vuruş",w:0};
    return null; }
  // ESPN saati "74'" · "45'+2'" · "90'+4'" → {d: gösterim, am: eksen dakikası}
  function saat(c,pd){ const dv=String((c&&c.displayValue)||""), m=dv.match(/(\d+)\s*'?\s*(?:\+\s*(\d+))?/);
    let b=m?+m[1]:null, a=m&&m[2]?+m[2]:0;
    if(b==null){ const v=sayi(c&&c.value); if(v==null) return null; b=Math.floor(v/60)+1; a=0; }
    const am=(pd===1||(b===45&&a>0&&pd!==2))?Math.min(45,b+a):b+a;
    return {d:a?`${b}+${a}'`:`${b}'`,am:Math.max(0,am)}; }
  // ---------- özet ayrıştırma (yalnız tür / dakika / takım / konum; text alanına DOKUNULMAZ) ----------
  function ayir(j){
    if(!j||typeof j!=="object") return null;
    const comp=j.header&&j.header.competitions&&j.header.competitions[0], cs=(comp&&comp.competitors)||[];
    const hc=cs.find(c=>c&&c.homeAway==="home"), ac=cs.find(c=>c&&c.homeAway==="away");
    if(!hc||!ac||!hc.team||!ac.team) return null;
    const T={h:{id:String(hc.team.id||""),n:hc.team.displayName||hc.team.name||""},a:{id:String(ac.team.id||""),n:ac.team.displayName||ac.team.name||""}};
    const taraf=t=>{ if(!t) return null; const id=t.id!=null?String(t.id):""; if(id&&id===T.h.id) return "h"; if(id&&id===T.a.id) return "a";
      const n=t.displayName||t.name||""; if(!n) return null; if(esit(n,T.h.n)) return "h"; if(esit(n,T.a.n)) return "a"; return null; };
    const sts=(comp.status&&comp.status.type)||{}, durum=sts.state||"pre";
    const ev=[], gor=new Set();
    const ekle=(p,kay)=>{ if(!p||typeof p!=="object") return; const ty=tur(p.type&&p.type.type); if(!ty) return;
      const sd=taraf(p.team); if(!sd) return; const pd=sayi(p.period&&p.period.number)||null, sa=saat(p.clock,pd); if(!sa) return;
      const id=p.id!=null?String(p.id):[ty.k,sd,sa.d,p.fieldPositionX,p.fieldPositionY].join("|"); if(gor.has(id)) return; gor.add(id);
      const x=sayi(p.fieldPositionX), y=sayi(p.fieldPositionY), x2=sayi(p.fieldPosition2X), y2=sayi(p.fieldPosition2Y);
      const ok=v=>v!=null&&v>=0&&v<=100;
      const kon=ok(x)&&ok(y)&&!(x===0&&y===0);
      const sn=sayi(p.clock&&p.clock.value);
      ev.push({k:ty.k,l:ty.l,w:ty.w,s:!!ty.s,sd,d:sa.d,am:sa.am,pd:pd||(sa.am>45?2:1),o:(pd||1)*1e5+(sn!=null?sn:sa.am*60),
        x:kon?x:null,y:kon?y:null,x2:kon&&ok(x2)&&ok(y2)&&!(x2===0&&y2===0)?x2:null,y2:kon&&ok(x2)&&ok(y2)&&!(x2===0&&y2===0)?y2:null,kay}); };
    for(const c of (Array.isArray(j.commentary)?j.commentary:[])) ekle(c&&c.play,"c");
    if(!ev.some(e=>e.kay==="c")) for(const k of (Array.isArray(j.keyEvents)?j.keyEvents:[])) ekle(k,"k");
    ev.sort((a,b)=>a.o-b.o);
    // istatistik (yedek baskı için)
    let st=null; try{ const H={},A={}; for(const t of ((j.boxscore&&j.boxscore.teams)||[])){ const sd=t.homeAway||taraf(t.team); const o=sd==="home"||sd==="h"?H:sd==="away"||sd==="a"?A:null; if(!o) continue;
        for(const s of (t.statistics||[])) if(s&&s.name) o[s.name]=sayi(s.displayValue!=null?String(s.displayValue).replace("%",""):s.value); }
      const pr=k=>H[k]!=null&&A[k]!=null?[Math.max(0,Math.round(H[k])),Math.max(0,Math.round(A[k]))]:null;
      const o={sh:pr("totalShots"),sot:pr("shotsOnTarget"),co:pr("wonCorners")}; if(o.sh||o.sot||o.co) st=o; }catch(e){ st=null; }
    let simdi=null; const sc=saat({displayValue:comp.status&&comp.status.displayClock},sayi(comp.status&&comp.status.period));
    if(durum==="in"&&sc) simdi=sc.am; if(simdi==null&&ev.length) simdi=ev[ev.length-1].am; if(durum==="post") simdi=Math.max(90,simdi||0);
    return {T,durum,simdi,ev,st,kon:ev.filter(e=>e.x!=null).length}; }

  // ---------- veri deposu (maç başına, oturum belleği) ----------
  const D=new Map(); let plAt=0;
  const RK={pre:0,in:1,post:2};
  function havuz(){ const o={}; try{ Object.assign(o,(typeof Pick!=="undefined"&&Pick.extra)||{}); }catch(e){} try{ const L=Live.events()||{}; for(const k in L){ const x=o[k]; if(!x||(RK[L[k].state]||0)>=(RK[x.state]||0)) o[k]=L[k]; } }catch(e){} return o; }
  function tsOf(m){ if(!m) return NaN; if(m.sp) return +m.ts; const d=m.dt; return d&&d.getTime?d.getTime():Date.parse(d); }
  function bul(m){ const P=havuz(); if(m.src==="espn"&&P[m.id]&&ESPN[P[m.id].lg]) return P[m.id];
    const ts=tsOf(m); if(!isFinite(ts)) return null;
    const c=Object.values(P).filter(e=>e&&ESPN[e.lg]&&Math.abs(Date.parse(e.date)-ts)<6*3600e3&&esit(e.h,m.h)&&esit(e.a,m.a));
    return c.find(e=>e.state==="in")||c.find(e=>e.state==="post")||c[0]||null; }
  const anahtar=m=>m?(m.sp?"i"+m.id:(m.src==="espn"?"e"+m.id:[m.lg,m.h,m.a].join("|"))):"";
  function kayit(k){ let S=D.get(k); if(!S){ S={at:0,P:null,err:"",ev:null,hist:[],busy:null,secim:"son",sel:null}; D.set(k,S); } return S; }
  function canliMi(m){ return !!((MS.live&&MS.live.sp===1)||(m&&m.live)); }
  function uygun(m){ if(!FL.on||!m||m.sp===2) return false; if(canliMi(m)) return true;
    const e=bul(m); if(e&&(e.state==="in"||e.state==="post")) return true;
    const t=tsOf(m); return isFinite(t)&&t<Date.now()-60e3&&t>Date.now()-4*3600e3; }
  async function yukle(zorla){
    const m=MS.m; if(!m) return; const k=anahtar(m), S=kayit(k);
    if(S.busy) return S.busy;
    const taze=S.P&&S.P.durum==="post"?600e3:25e3;
    if(!zorla&&S.at&&Date.now()-S.at<taze) return;
    S.busy=(async()=>{
      let ev=bul(m);
      if(!ev&&Date.now()-plAt>90e3&&typeof Pick!=="undefined"&&typeof Pick.loadEspn==="function"){ plAt=Date.now(); try{ await Pick.loadEspn(); }catch(e){} ev=bul(m); }
      S.at=Date.now();
      if(!ev){ S.err="yok"; return; }
      S.ev={id:ev.id,lg:ev.lg};
      let P=null, j=null;
      try{ const r=await fetch(`https://site.api.espn.com/apis/site/v2/sports/soccer/${ESPN[ev.lg]}/summary?event=${encodeURIComponent(ev.id)}`,{cache:"no-store"}); j=r&&r.ok?await r.json():null; }catch(e){ j=null; }
      try{ P=ayir(j); }catch(e){ P=null; } j=null;                    // ham yanıt (yorum metni dahil) burada bırakılır
      S.at=Date.now();
      if(!P){ S.err=document.hidden?"gizli":"ag"; return; }
      S.err=""; S.P=P;
      if(P.st&&P.simdi!=null){ S.hist=S.hist.filter(h=>h.t<P.simdi-.5).concat([{t:P.simdi,sh:P.st.sh,sot:P.st.sot,co:P.st.co}]).slice(-40); }
    })();
    try{ await S.busy; } finally{ S.busy=null; } }

  // ---------- baskı ----------
  const dakSon=P=>Math.max(90,Math.ceil(Math.max(P&&P.simdi||0,...((P&&P.ev)||[]).map(e=>e.am)))+0);
  function baskiOlay(P,N){ const h=new Array(N+1).fill(0), a=new Array(N+1).fill(0); let n=0;
    for(const e of P.ev){ const i=Math.max(0,Math.min(N,Math.round(e.am)));
      if(e.k==="foul"){ if(e.x==null||e.x>=50) continue; const w=.5*((100-e.x)>66?1.3:1); (e.sd==="h"?a:h)[i]+=w; continue; }
      if(!e.w) continue; const w=e.w*(e.x!=null&&e.x>66?1.3:1); (e.sd==="h"?h:a)[i]+=w; if(e.w>=1.5) n++; }
    return {h,a,n}; }
  function baskiIstat(S,N){ const h=new Array(N+1).fill(0), a=new Array(N+1).fill(0);
    const H=[]; try{ const lv=MS.live, C=W.CGT&&W.CGT.ST&&lv?CGT.ST.get(String(lv.id)):null; for(const x of ((C&&C.hist)||[])) if(x&&x.st) H.push({t:+x.t,sh:x.st.sh,sot:x.st.sot,co:x.st.co}); }catch(e){}
    for(const x of S.hist) H.push(x);
    const L=H.filter(x=>isFinite(x.t)&&(x.sh||x.sot||x.co)).sort((p,q)=>p.t-q.t);
    if(!L.length) return null;
    const pt=(x,i)=>{ const sot=x.sot?x.sot[i]:0, sh=x.sh?Math.max(x.sh[i],sot):sot, co=x.co?x.co[i]:0; return {sot,sh,co}; };
    let prev={t:0,v:[{sot:0,sh:0,co:0},{sot:0,sh:0,co:0}]};
    for(const x of L){ const v=[pt(x,0),pt(x,1)], t0=Math.max(0,Math.floor(prev.t)), t1=Math.max(t0+1,Math.min(N,Math.round(x.t)));
      if(x.t<=prev.t) continue;
      [0,1].forEach(i=>{ const d=v[i], p=prev.v[i]; const ds=Math.max(0,d.sot-p.sot), dsh=Math.max(0,(d.sh-d.sot)-(p.sh-p.sot)), dc=Math.max(0,d.co-p.co);
        const tot=3*ds+2*dsh+1.5*dc, per=tot/(t1-t0); for(let m=t0+1;m<=t1;m++) (i?a:h)[m]+=per; });
      prev={t:x.t,v}; }
    return {h,a,son:Math.round(prev.t)}; }
  const kayan=(v,k)=>v.map((_,i)=>{ let s=0,c=0; for(let j=Math.max(0,i-k+1);j<=i;j++){ s+=v[j]; c++; } return c?s/c:0; });
  function baskiSvg(B,N,simdi,P,kaynak){
    const h=kayan(B.h,5), a=kayan(B.a,5), son=Math.min(N,simdi==null?N:Math.round(simdi));
    let mx=0; for(let i=0;i<=son;i++) mx=Math.max(mx,h[i],a[i]); if(!(mx>0)) return "";
    const Wd=300, Hh=112, mid=56, amp=42, bw=Wd/(N+1), X=m=>m*bw;
    let bars="";
    for(let i=0;i<=son;i++){ const vh=h[i]/mx*amp, va=a[i]/mx*amp;
      if(vh>.4) bars+=`<rect x="${X(i).toFixed(2)}" y="${(mid-vh).toFixed(2)}" width="${Math.max(.6,bw-.35).toFixed(2)}" height="${vh.toFixed(2)}" class="bh"/>`;
      if(va>.4) bars+=`<rect x="${X(i).toFixed(2)}" y="${mid}" width="${Math.max(.6,bw-.35).toFixed(2)}" height="${va.toFixed(2)}" class="ba"/>`; }
    let ek="";
    for(const m of [15,30,45,60,75,90]) if(m<=N) ek+=`<line x1="${X(m)}" y1="10" x2="${X(m)}" y2="${Hh-10}" class="${m===45?"g45":"g"}"/><text x="${X(m)}" y="${Hh-1}" class="tx" text-anchor="${X(m)>Wd-8?"end":"middle"}">${m}'</text>`;
    if(P) for(const e of P.ev) if(e.k==="goal"){ ek+=`<circle cx="${(X(e.am)+bw/2).toFixed(2)}" cy="${e.sd==="h"?mid-amp-4:mid+amp+4}" r="2.6" class="${e.sd==="h"?"gh":"ga"}"><title>${E_(e.d)} Gol</title></circle>`; }
    if(simdi!=null&&simdi<N) ek+=`<line x1="${X(son)+bw}" y1="8" x2="${X(son)+bw}" y2="${Hh-12}" class="now"/>`;
    let s10="";{ let x=0,y=0; for(let i=Math.max(0,son-9);i<=son;i++){ x+=B.h[i]; y+=B.a[i]; } if(x+y>0){ const p=Math.round(x/(x+y)*100); s10=`<p class="sh-s10"><span class="sw h"></span>${E_(kisa(P?P.T.h.n:MS.m.h))} %${p} <span class="sep">·</span> <span class="sw a"></span>${E_(kisa(P?P.T.a.n:MS.m.a))} %${100-p}<small>son 10 dk baskı payı</small></p>`; } }
    return `<svg class="sh-bsvg" viewBox="0 0 ${Wd} ${Hh}" role="img" aria-label="Baskı grafiği: ev sahibi üstte, deplasman altta">
      <line x1="0" y1="${mid}" x2="${Wd}" y2="${mid}" class="ax"/>${ek}${bars}
      <text x="2" y="9" class="tl h">${E_(kisa(P?P.T.h.n:MS.m.h))}</text><text x="2" y="${Hh-13}" class="tl a">${E_(kisa(P?P.T.a.n:MS.m.a))}</text></svg>${s10}
      <small class="sh-src">${kaynak}</small>`; }

  // ---------- saha SVG ----------
  const PX=x=>(x/100*105), PY=y=>(y/100*68);
  function konum(e){ const f=e.sd==="a"; const t=v=>f?100-v:v; return {x:PX(t(e.x)),y:PY(t(e.y)),x2:e.x2!=null?PX(t(e.x2)):null,y2:e.y2!=null?PY(t(e.y2)):null}; }
  const yildiz=(cx,cy,r)=>{ let p=""; for(let i=0;i<10;i++){ const R=i%2?r*.45:r, a=-Math.PI/2+i*Math.PI/5; p+=(cx+R*Math.cos(a)).toFixed(2)+","+(cy+R*Math.sin(a)).toFixed(2)+" "; } return p.trim(); };
  function isaret(e,i,yeni){ const c=konum(e), cl=e.sd==="h"?"h":"a", x=c.x.toFixed(2), y=c.y.toFixed(2);
    let g="";
    if(e.s&&c.x2!=null) g+=`<line x1="${x}" y1="${y}" x2="${c.x2.toFixed(2)}" y2="${c.y2.toFixed(2)}" class="tr ${cl}"/>`;
    if(yeni) g+=`<circle cx="${x}" cy="${y}" r="2.2" class="pl ${cl}"/>`;
    switch(e.k){
      case "goal": g+=`<polygon points="${yildiz(c.x,c.y,2.7)}" class="st ${cl}"/>`; break;
      case "sot": case "pmiss": g+=`<circle cx="${x}" cy="${y}" r="1.45" class="f ${cl}"/>`; break;
      case "wood": g+=`<circle cx="${x}" cy="${y}" r="1.5" class="f ${cl}"/><circle cx="${x}" cy="${y}" r="2.3" class="rg"/>`; break;
      case "blk": g+=`<circle cx="${x}" cy="${y}" r="1.2" class="f ${cl} dim"/>`; break;
      case "off": g+=`<circle cx="${x}" cy="${y}" r="1.35" class="o ${cl}"/>`; break;
      case "cor": g+=`<polygon points="${(c.x-1.5).toFixed(2)},${(c.y+1.2).toFixed(2)} ${(c.x+1.5).toFixed(2)},${(c.y+1.2).toFixed(2)} ${x},${(c.y-1.4).toFixed(2)}" class="f ${cl}"/>`; break;
      case "foul": case "hand": g+=`<path d="M${(c.x-1.1).toFixed(2)} ${(c.y-1.1).toFixed(2)}l2.2 2.2M${(c.x+1.1).toFixed(2)} ${(c.y-1.1).toFixed(2)}l-2.2 2.2" class="x ${cl}"/>`; break;
      case "ofs": g+=`<rect x="${(c.x-1).toFixed(2)}" y="${(c.y-1).toFixed(2)}" width="2" height="2" transform="rotate(45 ${x} ${y})" class="o ${cl}"/>`; break;
      case "yc": case "rc": g+=`<rect x="${(c.x-.8).toFixed(2)}" y="${(c.y-1.15).toFixed(2)}" width="1.6" height="2.3" rx=".3" class="${e.k} ${cl}"/>`; break;
      default: g+=`<circle cx="${x}" cy="${y}" r="1" class="f ${cl} dim"/>`; }
    return `<g class="sh-m${yeni?" yeni":""}" data-i="${i}" data-sd="${e.sd}" data-k="${e.k}" tabindex="0" role="button" aria-label="${E_(e.d+" "+e.l)}"><circle cx="${x}" cy="${y}" r="3.6" class="hit"/>${g}</g>`; }
  function sahaSvg(P,L){
    const pa=16.5, pw=40.3*100/68, ga=5.5, gw=18.32*100/68, gl=7.32*100/68;
    const yy=v=>PY(50-v/2).toFixed(2), hh=v=>PY(v).toFixed(2);
    let s="";
    for(let i=0;i<10;i++) s+=`<rect x="${(i*10.5).toFixed(2)}" y="0" width="10.5" height="68" class="${i%2?"s2":"s1"}"/>`;
    const ln=`<g class="ln"><rect x="0" y="0" width="105" height="68"/><line x1="52.5" y1="0" x2="52.5" y2="68"/><circle cx="52.5" cy="34" r="9.15"/><circle cx="52.5" cy="34" r=".5" class="dot"/>
      <rect x="0" y="${yy(pw)}" width="${pa}" height="${hh(pw)}"/><rect x="${105-pa}" y="${yy(pw)}" width="${pa}" height="${hh(pw)}"/>
      <rect x="0" y="${yy(gw)}" width="${ga}" height="${hh(gw)}"/><rect x="${105-ga}" y="${yy(gw)}" width="${ga}" height="${hh(gw)}"/>
      <circle cx="11" cy="34" r=".5" class="dot"/><circle cx="94" cy="34" r=".5" class="dot"/>
      <path d="M16.5 26.7A9.15 9.15 0 0 1 16.5 41.3M88.5 26.7A9.15 9.15 0 0 0 88.5 41.3"/>
      <rect x="-1.6" y="${yy(gl)}" width="1.6" height="${hh(gl)}" class="gk"/><rect x="105" y="${yy(gl)}" width="1.6" height="${hh(gl)}" class="gk"/></g>`;
    const yon=`<text x="3" y="4.6" class="yn a">◀ ${E_(kisa(P.T.a.n))}</text><text x="102" y="4.6" class="yn h" text-anchor="end">${E_(kisa(P.T.h.n))} ▶</text>`;
    const son=L.length-1;
    const ms=L.map((e,i)=>isaret(e,i,i===son)).join("");
    return `<svg class="sh-svg" viewBox="-3 -2 111 72" role="img" aria-label="Saha: ev sahibi sağa hücum ediyor; son olayların konumları">${s}${ln}${yon}<g class="ms">${ms}</g></svg>`; }

  // ---------- çizim ----------
  const SAAT=t=>{ try{ return ist(new Date(t),{hour:"2-digit",minute:"2-digit",second:"2-digit"}); }catch(e){ return ""; } };
  function secilen(P,S){ const pos=P.ev.filter(e=>e.x!=null);
    let L=S.secim==="tum"?pos:pos.filter(e=>e.am>=(P.simdi!=null?P.simdi:dakSon(P))-15);
    if(L.length>60) L=L.slice(-60); return L; }
  function govde(m){
    const k=anahtar(m), S=kayit(k), P=S.P;
    const hN=P?P.T.h.n:m.h, aN=P?P.T.a.n:m.a;
    let h=`<div class="sh-wrap" data-k="${E_(k)}">`;
    const dur=P?(P.durum==="in"?`<span class="sh-cn">CANLI${P.simdi!=null?" "+Math.round(P.simdi)+"'":""}</span>`:P.durum==="post"?`<span class="sh-ms">MAÇ SONU</span>`:""):"";
    h+=`<div class="sh-hd"><h4>Saha</h4>${dur}<span class="sh-at">${S.at&&P?"Güncelleme "+E_(SAAT(S.at)):""}</span></div>`;
    if(!P){ if(S.busy||!S.at) return h+`<div class="sh-bos"><span class="sh-sp" aria-hidden="true"></span>Saha verisi yükleniyor…</div></div>`;
      const why=S.err==="yok"?"Bu maç ESPN maç akışında bulunamadı; saha ve baskı grafiği çizilemiyor."
        :S.err==="gizli"?"Uygulama arka plandayken veri alınmıyor."
        :"Saha verisine şu an ulaşılamıyor."+(canliMi(m)?" 30 sn sonra yeniden denenecek.":"");
      const N=90, B=baskiIstat(S,N);
      return h+`<p class="sh-bos warn" role="note">${E_(why)}</p>${B?`<div class="sh-bas"><div class="sh-bt"><h4>Baskı</h4><span class="sh-tag est">İstatistikten tahmini</span></div>${baskiSvg(B,N,B.son,null,"Şut, isabetli şut ve korner farklarının dakikalara dağıtılmış kaba tahmini.")}</div>`:""}</div>`; }
    const N=dakSon(P), L=secilen(P,S), konVar=P.kon>=5;
    if(konVar){
      h+=`<div class="sh-sec" role="group" aria-label="Zaman aralığı"><button type="button" data-s="son" aria-pressed="${S.secim!=="tum"}">Son 15 dk</button><button type="button" data-s="tum" aria-pressed="${S.secim==="tum"}">Tüm maç</button></div>`;
      h+=`<figure class="sh-pitch">${sahaSvg(P,L)}${L.length?"":`<figcaption class="sh-yok">Bu aralıkta konumlu olay yok</figcaption>`}</figure>`;
      h+=`<p class="sh-tip" aria-live="polite">Bir işarete dokun: dakika, olay ve takım</p>`;
      h+=`<div class="sh-lej"><span><i class="lj f h"></i>${E_(kisa(hN))}</span><span><i class="lj f a"></i>${E_(kisa(aN))}</span><span><i class="lj st"></i>Gol</span><span><i class="lj f n"></i>İsabetli</span><span><i class="lj o n"></i>İsabetsiz</span><span><i class="lj c n"></i>Korner</span></div>`;
    } else h+=`<p class="sh-bos" role="note">Bu lig için saha konum verisi yayınlanmıyor; aşağıdaki baskı grafiği ${P.ev.length>=5?"maç olaylarından":"maç istatistiklerinden"} hesaplandı.</p>`;
    const son5=P.ev.slice(-5).reverse();
    if(son5.length) h+=`<div class="sh-son"><h5>Son olaylar</h5><ol>${son5.map(e=>`<li><b>${E_(e.d)}</b><i class="sw ${e.sd}"></i><span>${E_(e.l)}</span><small>${E_(kisa(e.sd==="h"?hN:aN))}</small></li>`).join("")}</ol></div>`;
    // baskı
    const BO=baskiOlay(P,N); let bas="";
    if(BO.n>=3) bas=`<div class="sh-bt"><h4>Baskı</h4><span class="sh-tag">Olaylardan · 5 dk ortalama</span></div>`+baskiSvg(BO,N,P.simdi,P,"Gol 5, isabetli şut ve direk 3, diğer şut 2, korner 1,5, rakip yarı sahada kazanılan faul 0,5 puan; rakip kaleye yakın bölgede ×1,3.");
    else { const BI=baskiIstat(S,N); if(BI) bas=`<div class="sh-bt"><h4>Baskı</h4><span class="sh-tag est">İstatistikten tahmini</span></div>`+baskiSvg(BI,N,Math.min(P.simdi!=null?P.simdi:N,BI.son),P,"Şut, isabetli şut ve korner farklarının dakikalara dağıtılmış kaba tahmini; olay verisi gelmeyen liglerde kullanılır."); }
    h+=bas?`<div class="sh-bas">${bas}</div>`:`<p class="sh-bos">Baskı grafiği için henüz yeterli veri yok.</p>`;
    h+=`<p class="sh-not">Kaynak: ESPN maç akışı (yalnız olay türü, dakika ve saha konumu). Konumlar yaklaşıktır; olay adları OXXai'nindir.</p></div>`;
    return h; }
  function bagla(root,m){
    const S=kayit(anahtar(m)), P=S.P;
    root.querySelectorAll(".sh-sec button").forEach(b=>b.onclick=e=>{ e.stopPropagation(); S.secim=b.dataset.s; S.sel=null; try{ Sound.tap(); }catch(_){} ciz(); });
    const tip=root.querySelector(".sh-tip"); if(!tip||!P) return;
    const L=secilen(P,S);
    const goster=g=>{ const e=L[+g.dataset.i]; if(!e) return; S.sel=e.o+"|"+e.sd; root.querySelectorAll(".sh-m.sec").forEach(x=>x.classList.remove("sec")); g.classList.add("sec");
      const tk=kisa(e.sd==="h"?P.T.h.n:P.T.a.n);
      const bolge=e.x>=83&&e.y>=20&&e.y<=80?"ceza sahası içi":e.x>=66?"rakip yarı, kaleye yakın":e.x>=50?"rakip yarı saha":"kendi yarı sahası";
      tip.innerHTML=`<b>${E_(e.d)}</b> · ${E_(e.l)} · <span class="sw-t ${e.sd}">${E_(tk)}</span> <small>(${bolge})</small>`; };
    root.querySelectorAll(".sh-m").forEach(g=>{ g.addEventListener("click",ev=>{ ev.stopPropagation(); goster(g); });
      g.addEventListener("keydown",ev=>{ if(ev.key==="Enter"||ev.key===" "){ ev.preventDefault(); goster(g); } }); });
    if(S.sel){ const i=L.findIndex(e=>e.o+"|"+e.sd===S.sel), g=i>=0?root.querySelector(`.sh-m[data-i="${i}"]`):null; if(g) goster(g); else S.sel=null; } }   // yeniden çizimde seçim korunur
  function ciz(){ const el=$("msheet"); if(!el||el.hidden||!MS.m||MS.tab!=="saha") return; const body=el.querySelector(".ms-body"); if(!body) return;
    let w=body.querySelector(".sh-wrap"); const html=govde(MS.m);
    if(!w){ body.innerHTML=html; } else { const t=document.createElement("div"); t.innerHTML=html; w.replaceWith(t.firstElementChild); }
    w=body.querySelector(".sh-wrap"); if(w) bagla(w,MS.m); }

  // ---------- sekme ----------
  let zam=null;
  function zamanla(){ if(zam) return; zam=setInterval(()=>{
      if(!MS.m||MS.tab!=="saha"||$("msheet").hidden){ clearInterval(zam); zam=null; return; }
      if(document.hidden) return;
      const S=kayit(anahtar(MS.m)); if(S.P&&S.P.durum==="post") return;
      if(!canliMi(MS.m)&&!(S.P&&S.P.durum==="in")&&S.P) return;
      yukle(true).then(ciz,ciz); },30e3); }
  document.addEventListener("visibilitychange",()=>{ try{ if(!document.hidden&&MS.m&&MS.tab==="saha"){ const S=kayit(anahtar(MS.m)); if(Date.now()-S.at>30e3&&!(S.P&&S.P.durum==="post")) yukle(true).then(ciz,ciz); } }catch(e){} });
  function sus(){ const el=$("msheet"), m=MS.m; if(!el||el.hidden||!m) return;
    if(!uygun(m)){ if(MS.tab==="saha"){ MS.tab="tahmin"; setTimeout(()=>{ try{ msRender(); }catch(e){} },0); } return; }
    const tb=el.querySelector(".ms-tabs"); if(!tb) return;
    if(!tb.querySelector('[data-t="saha"]')){ tb.insertAdjacentHTML("beforeend",`<button type="button" role="tab" data-t="saha" aria-selected="${MS.tab==="saha"}">Saha</button>`); tb.classList.add("sh-4");
      const b=tb.querySelector('[data-t="saha"]'); b.onclick=()=>{ MS.tab="saha"; try{ Sound.tap(); }catch(e){} msRender(); }; }
    if(MS.tab!=="saha") return;
    tb.querySelectorAll("button").forEach(b=>b.setAttribute("aria-selected",String(b.dataset.t==="saha")));
    const body=el.querySelector(".ms-body"); if(body) body.innerHTML=govde(m);
    const w=body&&body.querySelector(".sh-wrap"); if(w) bagla(w,m);
    const S=kayit(anahtar(m)); if(!S.busy&&(!S.at||Date.now()-S.at>25e3)) yukle(false).then(ciz,ciz);
    if(canliMi(m)||!(S.P&&S.P.durum==="post")) zamanla(); }
  const _mr=msRender;
  msRender=function(){ const r=_mr.apply(this,arguments); try{ sus(); }catch(e){ console.warn("saha-v180",e); } return r; };
  W.sahaV180={ayir,tur,yukle,D,FL,durum:()=>{ const S=MS.m?D.get(anahtar(MS.m)):null; return S?{at:S.at,err:S.err,olay:S.P?S.P.ev.length:0,kon:S.P?S.P.kon:0,durum:S.P&&S.P.durum,simdi:S.P&&S.P.simdi,hist:S.hist.length}:null; }};
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: saha-v180 */
