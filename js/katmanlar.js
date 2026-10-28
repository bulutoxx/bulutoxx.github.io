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
