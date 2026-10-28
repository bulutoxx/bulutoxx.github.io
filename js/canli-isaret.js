/* id: canli-isaret-v140 */ try {
// =====================================================================
// OXXai v140 · CANLI ALTIN İŞARET: maç başladıktan (0') 75. dakikaya kadar her canlı futbol maçında en güçlü canlı seçim
// (Power Now / pwLiveCands adayı: en olası seçenek, oran ≥ 1,03; işaret için oran ≥ 1,05) için GÖSTERİLEN (kalibre; CG açıkken
// onun) olasılık ≥ eşik (varsayılan %80) ise maç altın rozetle işaretlenir: Canlı sekmesi satırı, bülten/takip canlı satırları,
// canlı maç penceresi. Histerezis: %80'de açılır, %77'nin altına inince kalkar (yanıp sönme yok). 75. dk ve sonrası işaret yok
// (v135 kararı: model orada aşırı güvenliydi). Gol / kırmızı kart / dakika değişince her canlı yenilemede (10–15 sn) yeniden hesap.
// Eşikler data/canli_altin.json → isaret (LGF.isaret); 48 saatlik canlı kapı lab/canli_altin_lab.py. Python eşi: scripts/canli_altin.py
// isaret() — lab/canli_altin_test.cjs 300 rastgele durumla birebir sınar. Canlı altın KUPO (canli-v70) değişmez. Tahmindir.
// =====================================================================
(function(){ "use strict";
  const F=()=>LGF.isaret;
  // saf kural (scripts/canli_altin.py → isaret ile BİREBİR). all: [{k,n,p(ham),o}], dk: m.min, was: önceki turda işaretli mi, cal: ham → gösterilen
  function aiRule(all,dk,I,was,cal){
    if(I.durum==="durduruldu") return null;
    if(dk!=null&&+dk>=I.dkmax) return null;
    const ok=(all||[]).filter(c=>c.o&&c.o>=1.03&&c.p!=null&&isFinite(c.p)&&c.p>=.6); if(!ok.length) return null;
    let b=ok[0]; for(const c of ok) if(c.p>b.p) b=c;
    if(!(b.o>=1.05)) return null;
    const p=Math.min(cal?cal(b.p):b.p,.99);
    return (p>=I.esik||(was&&p>=I.kapanis))?{k:b.k,n:b.n,p,ham:b.p,o:b.o}:null; }
  const ST=new Map();   // maç → {on, ever}
  const calF=p=>{ try{ return typeof liveCal==="function"?liveCal(p).p:p; }catch(e){ return p; } };
  function aiOf(m){ if(!m||m.sp!==1) return null; const id=String(m.id), S=ST.get(id)||{on:false,ever:false};
    let K=null; try{ K=idlPick(m,idlPred(m)); }catch(e){ K=null; }
    const r=K?aiRule(K.all,m.min,F(),S.on,calF):null;
    S.on=!!r; if(r) S.ever=true; ST.set(id,S);
    if(r) return r;
    return (S.ever&&m.min!=null&&+m.min>=F().dkmax)?{late:true}:null; }
  const pct=p=>Math.min(99,Math.max(1,Math.round(p*100)));
  function sealHtml(r){ return `<button type="button" class="gold-seal ai-seal" data-ai="1" title="Canlı altın işaret · tahmindir, garanti değildir" aria-label="Canlı altın işaret: ${esc(r.n)} yüzde ${pct(r.p)}. Açıklama için dokun"><img src="icons/oxxai-mark.webp" alt="">ALTIN · ${esc(r.n)} %${pct(r.p)}</button>`; }
  function lineHtml(r,cls){ if(!r) return ""; const s=r.late?"late":r.k+"|"+pct(r.p);
    return `<div class="${cls}" data-s="${esc(s)}">${r.late?`<span class="ai-x">🥇 Son dakikalarda (${F().dkmax}. dk sonrası) altın işaret yok</span>`:sealHtml(r)}</div>`; }
  function paintRow(row,r){ const old=row.querySelector(":scope > .ai-l"), s=r?(r.late?"late":r.k+"|"+pct(r.p)):"";
    if(!(old&&old.dataset.s===s)){ if(old) old.remove(); if(r){ const top=row.querySelector(":scope > .lv-top"); if(top) top.insertAdjacentHTML("afterend",lineHtml(r,"ai-l")); } }
    row.classList.toggle("ai-on",!!(r&&!r.late)); }
  function paintMs(){ const el=$("msheet"); if(!el) return; const old=el.querySelector(".ai-ms");
    const lv0=typeof MS!=="undefined"&&MS.live; if(el.hidden||!lv0||lv0.sp!==1){ if(old) old.remove(); return; }
    const m=(IDL.byId&&IDL.byId[1]&&IDL.byId[1][lv0.id])||lv0, r=aiOf(m), s=r?(r.late?"late":r.k+"|"+pct(r.p)):"";
    if(old&&old.dataset.s===s) return; if(old) old.remove(); if(!r) return;
    const t=el.querySelector(".ms-hd .ms-teams"); if(t) t.insertAdjacentHTML("afterend",lineHtml(r,"ai-ms")); }
  function aiDeco(){ try{ const by=(IDL.byId&&IDL.byId[1])||{};
      document.querySelectorAll(".lv-c[data-id]").forEach(row=>{ const c=row.querySelector(".lclk"); if(c&&+c.dataset.sp!==1) return; const m=by[+row.dataset.id]; if(m) paintRow(row,aiOf(m)); });
      paintMs(); }catch(e){} }
  // 1) satır şablonu: ilk çizimde rozet hazır gelir (Canlı sekmesi, bülten / takip canlı satırları)
  try{ const _r=idlRow; idlRow=function(m){ let h=_r.apply(this,arguments); try{ if(m&&m.sp===1){ const r=aiOf(m); if(r){
        if(!r.late) h=h.replace('<div class="lv-c"','<div class="lv-c ai-on"');
        const i=h.indexOf('</i></span></div>'); if(i>0) h=h.slice(0,i+17)+lineHtml(r,"ai-l")+h.slice(i+17); } } }catch(e){} return h; }; }catch(e){}
  // 2) Canlı sekmesi altında kısa açıklama
  function noteHtml(){ const I=F(); if(I.durum==="durduruldu") return `<p class="ai-note">🥇 Canlı altın işaret şu an kapalı (canlı denemede yeterince tutmadı).</p>`;
    return `<p class="ai-note">🥇 <b>Canlı altın işaret</b>: maçın en güçlü canlı seçiminin olasılığı %${Math.round(I.esik*100)} ve üzeriyse; %${Math.round(I.kapanis*100)}'in altına inince kalkar. Son dakikalarda (${I.dkmax}. dk sonrası) işaret yok.${I.durum==="kalici"?"":" Deneme sürüyor."} Tahmindir, garanti değildir.</p>`; }
  try{ const _b=idlBoxHtml; idlBoxHtml=function(){ const h=_b.apply(this,arguments); return IDLV.sp===1&&(IDL.live[1]||[]).length?h+noteHtml():h; }; }catch(e){}
  // 3) her canlı yenilemede (Canlı sekmesi 10 sn, canlı nabız 15 sn, pencere) yerinde güncelle
  try{ const _ld=IDL.load.bind(IDL); IDL.load=async function(sp){ const r=await _ld.apply(null,arguments); if(sp===1) aiDeco(); return r; }; }catch(e){}
  try{ const _mr=msRender; msRender=function(){ const r=_mr.apply(this,arguments); try{ paintMs(); }catch(e){} return r; }; }catch(e){}
  // 4) rozete dokununca / uzun basınca kısa açıklama
  function info(e){ const b=e.target.closest&&e.target.closest(".ai-seal"); if(!b) return; e.preventDefault(); e.stopPropagation(); const I=F();
    try{ buzz(6); }catch(_){}
    toast(`🥇 Canlı altın işaret: OXXai'nin bu maçtaki en güçlü canlı seçiminin olasılığı %${Math.round(I.esik*100)} ve üzerinde (skor, dakika ve kartlara göre sürekli yeniden hesaplanır). %${Math.round(I.kapanis*100)}'in altına inince kalkar; ${I.dkmax}. dakikadan sonra verilmez. Tahmindir, garanti değildir. 18+`); }
  document.addEventListener("click",info,true); document.addEventListener("contextmenu",info,true);
  // 5) karne satırı (Tahmin karnesi › Güvenilirlik raporu › Canlı)
  window.aiKarne=function(){ const I=F(), O=I.olcum, tag=I.durum==="kalici"?"kalıcı":I.durum==="durduruldu"?"durduruldu":"deneme", R=x=>Math.round(x*100);
    if(!O||!O.n) return `<h3 class="gv-h">🥇 Canlı altın işaret</h3><p class="gv-p" data-ai-karne="0">Veri birikiyor · eşik %${R(I.esik)} (${tag}). Maç başına ilk işaret anı bir kez sayılır; ${I.dkmax}. dakika sonrası işaret yok.</p>`;
    return `<h3 class="gv-h">🥇 Canlı altın işaret</h3><p class="gv-p" data-ai-karne="1">${O.n} işaretli maç · <b>${O.tuttu}</b> tuttu · <b>%${R(O.gercek)}</b>${O.ort_p!=null?` (söylediğimiz ortalama %${R(O.ort_p)}${O.wilson_alt!=null?`; %95 alt sınır %${R(O.wilson_alt)}`:""})`:""} · eşik %${R(I.esik)} (${tag})${O.n<15?" · veri az":""}. Maç başına ilk işaret anı sayılır.</p>`; };
  window.aiDeco=aiDeco; window.aiRule=aiRule; window.aiOf=aiOf; window.aiST=ST;
  try{ aiDeco(); }catch(e){}
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: canli-isaret-v140 */
