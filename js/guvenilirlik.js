/* id: guvenilirlik-v138 */ try {
// =====================================================================
// OXXai v138 · GÜVENİLİRLİK RAPORU (YH-13; ölçüm YH-09: scripts/guvenilirlik.py)
// Tahmin karnesinde katlanır panel: "%X dediğimiz tahminler gerçekte %Y tuttu" — futbol maç öncesi, canlı, basket, at ayrı.
// Rakamlar yalnız karne dosyalarından (daily.json → guvenilirlik ve canli.guvenilirlik, pazar_karne.json → canli.guvenilirlik,
// basket.json → live.guvenilirlik, at/karne.json → guvenilirlik); dosyada yoksa "veri yok". n < 50 kovalar "veri az".
// Panel açılmadan ek dosya indirilmez (açılış süresi etkilenmez).
// =====================================================================
(function(){ "use strict";
  const AZ=50, ST={tab:"fb", open:false, pk:null, at:null, yuk:false};
  const E=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const yz=v=>v==null||!isFinite(v)?"–":"%"+Math.round(v*100);
  const yz1=v=>v==null||!isFinite(v)?"–":"%"+(Math.round(v*1000)/10).toLocaleString("tr-TR");
  const d4=v=>v==null||!isFinite(v)?"–":(Math.round(v*1e4)/1e4).toLocaleString("tr-TR",{minimumFractionDigits:4,maximumFractionDigits:4});
  const n0=v=>v==null?"–":Number(v).toLocaleString("tr-TR");
  const j=u=>fetch(u,{cache:"no-cache"}).then(r=>r.ok?r.json():null).catch(()=>null);
  function kaynak(){ const D=(typeof DAILY!=="undefined"&&DAILY)||null, B=(typeof BK!=="undefined"&&BK.data)||null;
    return { fb:D&&D.guvenilirlik||null, fb1:ST.pk&&ST.pk.canli&&ST.pk.canli.guvenilirlik||null,
             cn:D&&D.canli&&D.canli.guvenilirlik||null, bk:B&&B.live&&B.live.guvenilirlik||null, at:ST.at&&ST.at.guvenilirlik||null }; }
  function ozet(g){ return `<div class="gv-m"><div><b>${yz1(g.ece)}</b><small>ortalama sapma (ECE)</small></div><div><b>${d4(g.guvenilirlik)}</b><small>kalibrasyon hatası<br>(küçük iyi)</small></div><div><b>${d4(g.cozunurluk)}</b><small>ayırt etme gücü<br>(büyük iyi)</small></div></div>`; }
  function kovalar(g,birim){ if(!g||!g.n) return `<div class="gv-yok">veri yok</div>`;
    const K=(g.kovalar||[]).filter(b=>b.n>0);
    let h=`<div class="gv-lg"><span><i style="background:var(--c-green)"></i>gerçekte tutan</span><span><i style="background:var(--c-gold)"></i>söylediğimiz ortalama</span><span><i style="background:var(--ink);opacity:.3"></i>%95 aralık</span></div><div>`;
    for(const b of K){ const az=b.n<AZ, a=b.aralik.split("-").map(Number), w=b.wilson95||[];
      const lo=w[0]!=null?w[0]:b.gercek, hi=w[1]!=null?w[1]:b.gercek;
      h+=`<div class="gv-r${az?" az":""}"><div class="gv-l">%${Math.round(a[0]*100)}–${Math.round(a[1]*100)}<small>dediğimiz</small></div>
        <div class="gv-tr" role="img" aria-label="Söylenen ${yz(b.tahmin)}, gerçekleşen ${yz(b.gercek)}"><span class="gv-ci" style="left:${(lo*100).toFixed(1)}%;width:${Math.max(.5,(hi-lo)*100).toFixed(1)}%"></span><span class="gv-f" style="width:${(b.gercek*100).toFixed(1)}%"></span><span class="gv-tk" style="left:${(b.tahmin*100).toFixed(1)}%"></span></div>
        <div class="gv-t" data-gv-k="${E(b.aralik)}">${yz(b.tahmin)} dediğimiz <b>${n0(b.n)}</b> ${birim} gerçekte <b>${yz(b.gercek)}</b> tuttu · %95: ${yz(lo)}–${yz(hi)}${az?`<span class="gv-az">veri az</span>`:""}</div></div>`; }
    return h+`</div>`; }
  function blok(baslik,g,birim,ek){ if(!g||!g.n) return `<h3 class="gv-h">${baslik}</h3><div class="gv-yok">veri yok</div>`;
    return `<h3 class="gv-h">${baslik}</h3><p class="gv-p">${n0(g.n)} ${birim}${ek?` · ${ek}`:""} · genel: söylediğimiz ortalama <b>${yz1(g.ort_tahmin)}</b>, gerçekleşen <b>${yz1(g.gercek_oran)}</b>.</p>${ozet(g)}${kovalar(g,birim)}`; }
  function kars(P,ad){ if(!P||!P.n) return `<div class="gv-cmp"><b>${ad}</b>: veri yok.</div>`;
    const ga=P.fark_ga95||[], az=P.n<AZ;
    const yorum=az?"veri az; yorum için erken":(ga[1]!=null&&ga[1]<0)?"model piyasadan anlamlı biçimde iyi":(ga[0]!=null&&ga[0]>0)?"piyasa modelden anlamlı biçimde iyi":"aradaki fark anlamlı değil";
    return `<div class="gv-cmp" data-gv-p="${E(ad)}"><b>${ad}</b> (${n0(P.n)} maç): log-kayıp OXXai <b>${d4(P.ll_model)}</b> · piyasa <b>${d4(P.ll_piyasa)}</b> (küçük iyi). Fark ${d4(P.fark)}${ga[0]!=null?`, %95: ${d4(ga[0])} … ${d4(ga[1])}`:""} → ${yorum}.</div>`; }
  function icerik(){ const S=kaynak(); let h="";
    if(ST.tab==="fb"){ const F=S.fb, M=S.fb1;
      h+=blok("Maç öncesi öneriler",F&&F.tum,"öneri","maç başlamadan kilitlenmiş");
      h+=`<h3 class="gv-h">Piyasa ile karşılaştırma</h3>`+kars(F&&F.piyasa,"Gösterilen öneri ve piyasa")+kars(M&&M.piyasa,"1X2 olasılıkları ve piyasa");
      h+=blok("1X2 olasılıkları (her sonuç ayrı)",M&&M.model,"olasılık",M&&M.model&&M.model.n_mac?`${n0(M.model.n_mac)} maç`:""); }
    else if(ST.tab==="cn"){ h+=(typeof window.aiKarne==="function"?window.aiKarne():""); h+=blok("Canlı seçimler",S.cn,"seçim","seçim anındaki olasılık · 75. dakika sonrası hariç"); }
    else if(ST.tab==="bk") h+=blok("Basket: favorinin kazanması",S.bk,"maç","maç başlamadan kilitlenmiş");
    else h+=blok("At yarışı: atların kazanma olasılığı",S.at,"at",S.at&&S.at.n_kosu?`${n0(S.at.n_kosu)} koşu · koşudan önce kilitlenmiş`:"");
    if(ST.yuk&&!ST.bitti&&ST.tab!=="cn") h+=`<p class="gv-p">Yükleniyor…</p>`;
    return h; }
  function ciz(){ const el=document.getElementById("gvIc"); if(!el) return; el.innerHTML=icerik();
    document.querySelectorAll("#gvSeg button").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.t===ST.tab))); }
  async function yukle(){ if(ST.yuk) return; ST.yuk=true; ciz();
    const ps=[j("data/pazar_karne.json").then(d=>{ ST.pk=d; }), j("data/at/karne.json").then(d=>{ ST.at=d; })];
    try{ if(typeof bkLoad==="function"&&!(BK&&BK.data)) ps.push(bkLoad()); }catch(e){}
    await Promise.all(ps); ST.bitti=true; ciz(); }
  function kur(){ const box=document.getElementById("karne"); if(!box) return;
    let d=document.getElementById("gvPanel");
    if(!d){ d=document.createElement("details"); d.id="gvPanel"; d.className="kz-tech gv";
      d.innerHTML=`<summary>📐 Güvenilirlik raporu: "%X dediğimiz" gerçekte ne kadar tuttu?</summary><div class="panel gv-in">
        <p class="gv-p">Yalnız sonuçlanmış ve önceden kilitlenmiş tahminler. Her satırda söylediğimiz olasılık (sarı çizgi) ile gerçekleşen oran (yeşil) yan yana; çizgi yeşilin ucundaysa söylediğimiz tutuyor.</p>
        <div class="gv-seg" id="gvSeg" role="group" aria-label="Güvenilirlik bölümü"><button type="button" data-t="fb">Futbol</button><button type="button" data-t="cn">Canlı</button><button type="button" data-t="bk">Basket</button><button type="button" data-t="at">At</button></div>
        <div id="gvIc"></div>
        <p class="gv-p" style="font-size:var(--t-c1)">ECE: söylenen ile gerçekleşen arasındaki ağırlıklı ortalama fark. Kalibrasyon hatası ve ayırt etme gücü Brier skorunun Murphy ayrışımından gelir. ${AZ}'den az tahmini olan satırlar "veri az" diye işaretlenir.</p></div>`;
      d.addEventListener("toggle",()=>{ ST.open=d.open; if(d.open){ ciz(); yukle(); } });
      d.querySelector("#gvSeg").addEventListener("click",e=>{ const b=e.target.closest("button[data-t]"); if(!b) return; ST.tab=b.dataset.t; ciz(); }); }
    const tech=document.getElementById("kzTech");
    if(tech&&tech.parentNode===box){ if(d.nextSibling!==tech) box.insertBefore(d,tech); } else if(d.parentNode!==box) box.appendChild(d);
    d.open=ST.open; if(ST.open) ciz(); }
  if(typeof renderKarne==="function"){ const _rk=renderKarne; renderKarne=function(){ const r=_rk.apply(this,arguments); try{ kur(); }catch(e){} return r; }; }
  try{ const v=document.getElementById("v-karne"); if(v&&!v.hidden) kur(); }catch(e){}
  window.oxxGuv={ac:t=>{ if(t) ST.tab=t; kur(); const d=document.getElementById("gvPanel"); if(d){ d.open=true; ST.open=true; ciz(); return yukle(); } }, durum:ST};
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: guvenilirlik-v138 */
