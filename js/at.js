/* id: at-v73 */ try {
// =====================================================================
// OXXai v73: 🐎 At Yarışı (DENEME) — her gece kendini eğiten laboratuvarın (lab/at) olasılıkları.
// Veri: data/at/tahmin/<gün>.json (kilitli, yalnız türetilmiş olasılıklar), data/at/model.json (sınama ölçümleri),
// data/at/karne.json (kilitli tahminlerin sonuçları). Kaynak: açık yarış sonuç arşivi; resmî siteye istek yok. Hobi amaçlı, 18+.
// =====================================================================
(function(){
  const LOGO=(k)=>`<img class="at-emb" src="icons/oxxai-at.webp" alt="" aria-hidden="true" decoding="async" onerror="this.onerror=null;this.src='icons/oxxai-at.png'">`;
  const AT={days:[], d:null, data:{}, model:null, karne:null, hip:null, open:new Set(), busy:false, tab:"tah"};
  const pct=x=>x==null?"–":"%"+Math.round(x*100);
  const dISO=o=>istDay(new Date(Date.now()+o*864e5));
  const j=u=>fetch(u+"?t="+Date.now(),{cache:"no-store"}).then(r=>r.ok?r.json():null).catch(()=>null);
  async function load(){ if(AT.busy) return; AT.busy=true;
    try{ let offs=[0,1], got=await Promise.all(offs.map(o=>j("data/at/tahmin/"+dISO(o)+".json"))); if(!got.some(Boolean)){ offs=[-1,-2]; got=await Promise.all(offs.map(o=>j("data/at/tahmin/"+dISO(o)+".json"))); }
      AT.days=[]; offs.forEach((o,i)=>{ const d=got[i]; if(d&&d.kosular&&d.kosular.length){ AT.data[d.tarih]=d; AT.days.push(d.tarih); } });
      AT.days.sort(); if(!AT.d||!AT.data[AT.d]) AT.d=AT.days.includes(dISO(0))?dISO(0):AT.days[AT.days.length-1]||null;
      const [m,k]=await Promise.all([j("data/at/model.json"),j("data/at/karne.json")]); AT.model=m; AT.karne=k;
      AT.jok=await j("data/at/jokeyler.json"); AT.altK=await j("data/at/altili_karne.json"); AT.kyn=await j("data/at/kaynak_durum.json"); AT.sec=await j("data/at/secici.json");
      AT.alt=AT.alt||{}; const als=await Promise.all(AT.days.map(d=>j("data/at/altili/"+d+".json"))); AT.days.forEach((d,i)=>{ if(als[i]&&als[i].altililar) AT.alt[d]=als[i]; });
      AT.canli=AT.canli||{}; const cs=await Promise.all(AT.days.map(d=>j("data/at/canli/"+d+".json"))); AT.days.forEach((d,i)=>{ if(cs[i]&&cs[i].kosular) AT.canli[d]=cs[i]; });
    }finally{ AT.busy=false; } render(); }
  const SEV=[["dar","Dar"],["orta","Orta"],["genis","Geniş"]];
  function altiliHtml(){ const A=AT.alt&&AT.alt[AT.d], K=AT.altK;
    const kar=(sv)=>{ const g=K&&K.geriye_donuk&&K.geriye_donuk.seviyeler&&K.geriye_donuk.seviyeler[sv]; return g&&g.n?`Geriye dönük test (${esc((K.geriye_donuk.donem||[]).join(" – "))}): ${g.n} altılıdan tutan <b>${g.isabet}</b> · model beklentisi ${(+g.beklenen).toFixed(1).replace(".",",")} · 5 ayak tutan ${g.bes_ayak||0} · ort. ${Math.round(g.ort_kombinasyon||0)} kombinasyon · ayak isabeti %${Math.round((g.ayak_isabet||0)*100)}${g.altin_ayak&&g.altin_ayak.n?` · altın ayak (tek at) isabeti %${Math.round((g.altin_ayak.isabet||0)*100)} (${g.altin_ayak.n} ayak)`:""}${(()=>{ const t=K.geriye_donuk.sinama&&K.geriye_donuk.sinama.seviyeler&&K.geriye_donuk.sinama.seviyeler[sv]; return t&&t.n?`<br>Son 1/3 sınama dilimi: ${t.n} altılıdan tutan <b>${t.isabet}</b> · beklenti ${(+t.beklenen).toFixed(1).replace(".",",")}`:""; })()}${(()=>{ const c=K.canli&&K.canli.seviyeler&&K.canli.seviyeler[sv]; return c&&c.n?`<br>Canlı (koşudan önce kilitli): ${c.n} altılıdan tutan <b>${c.isabet}</b> · beklenti ${(+c.beklenen).toFixed(1).replace(".",",")}`:""; })()}`:""; };
    if(!A||!(A.altililar||[]).length) return `<div class="panel"><p class="note" style="margin:0">Bu gün için 6'lı tahmin tahmini hazırlanıyor. Laboratuvar programdaki "oran başlangıcı" koşularından 6'lıları kurar ve her ayak için atları OXXai olasılıklarıyla seçer.</p></div>`;
    const sv=AT.sev||"orta";
    let h=`<div class="at-tabs al-sev" role="group" aria-label="Kapsam">${SEV.map(([k,l])=>`<button type="button" data-sev="${k}" aria-pressed="${sv===k}">${l}</button>`).join("")}</div>
      <p class="note" style="margin:0 0 10px">Dar ≤${(A.butce||{}).dar||64}, Orta ≤${(A.butce||{}).orta||192}, Geniş ≤${(A.butce||{}).genis||576} kombinasyonla seçim yapar. "6'yı birden tutma olasılığı" her ayağın seçilen atlarının toplam olasılığının çarpımıdır; KUPO ilk ayak başlayınca kilitlenir. 🥇 = altın ayak (tek at). Para tutarı gösterilmez · 18+</p>`;
    for(const X of A.altililar){ const L=X.seviyeler&&X.seviyeler[sv]; if(!L) continue; const S=X.sonuc, at=S&&S.ayak_tuttu&&S.ayak_tuttu[sv];
      h+=`<div class="at-race al-c"><div class="at-rh"><b>${esc(X.hipodrom)} ${X.no}. 6'lı</b><span>${X.baslangic_kosu}.–${X.baslangic_kosu+5}. koşular · ${X.kaynak==="oran"?"💹 oranla güncel":"sabah tahmini"}</span><span class="t">${esc(X.saat||"")}</span></div>
        <div class="al-top"><div><b>%${(L.p*100).toFixed(L.p<.1?1:0).replace(".",",")}</b><small>6'yı birden tutma olasılığı</small></div><div><b>${L.kombinasyon}</b><small>kombinasyon</small></div>${S&&S.tamam?`<div class="${S.tuttu&&S.tuttu[sv]?"al-ok":"al-no"}"><b>${S.tuttu&&S.tuttu[sv]?"✓ TUTTU":"✗"}</b><small>${(at||[]).filter(Boolean).length}/6 ayak</small></div>`:""}</div>
        ${L.ayaklar.map((g,i)=>{ const w=S&&S.kazananlar?S.kazananlar[i]:null, ok=at?at[i]:null;
          return `<div class="al-a${ok===true?" ok":ok===false?" no":""}"><span class="al-i">${i+1}.<small>${esc(g.saat||"")}</small></span><span class="al-s">${g.secim.map(no=>{ const hh=(g.atlar||[]).find(x=>String(x[0])===String(no)); return `<span class="al-h${w!=null&&String(w)===String(no)?" w":""}" data-ah="${esc(X.hipodrom&&(AT.d+"/"+X.hipodrom+"/"+g.kosu))}|${esc(no)}">${esc(no)}${hh?` ${esc(String(hh[1]).slice(0,14))}`:""}</span>`; }).join("")}${g.banko?`<em class="al-b">🥇 tek at</em>`:""}</span><span class="al-p">%${Math.round(g.p_ayak*100)}${w!=null?`<small>kazanan ${esc(w)}</small>`:""}</span></div>`; }).join("")}
        <button type="button" class="at-share" data-als="${esc(X.id)}">📤 Bu 6'lı tahmini paylaş</button></div>`; }
    const kk=kar(sv); if(kk) h+=`<div class="at-gold"><div class="at-gh">📊 6'lı karnesi · ${SEV.find(x=>x[0]===sv)[1]}</div><p class="at-gn">${kk}</p></div>`;
    return h; }
  async function shareAlt(id){ const A=AT.alt&&AT.alt[AT.d]; const X=A&&A.altililar.find(x=>x.id===id); if(!X) return; const sv=AT.sev||"orta", L=X.seviyeler[sv];
    const t=`🎯 ${X.hipodrom} ${X.no}. 6'lı (${X.baslangic_kosu}.–${X.baslangic_kosu+5}. koşular) · OXXai ${SEV.find(x=>x[0]===sv)[1]} tahmini\n`+L.ayaklar.map((g,i)=>`${i+1}. ayak: ${g.secim.join("-")}${g.banko?" (tek at)":""}`).join("\n")+`\n6'yı birden tutma olasılığı %${(L.p*100).toFixed(1).replace(".",",")} · ${L.kombinasyon} kombinasyon\nHobi amaçlı olasılıktır, garanti değildir · 18+`;
    try{ if(navigator.share){ await navigator.share({text:t}); return; } }catch(e){ return; }
    try{ await navigator.clipboard.writeText(t); toast("📋 6'lı tahmini kopyalandı"); }catch(e){ location.href="https://wa.me/?text="+encodeURIComponent(t); } }
  function jokeyHtml(){ const J=AT.jok; if(!J||!(J.jokeyler||[]).length) return `<div class="panel"><p class="note" style="margin:0">Jokey istatistikleri hazırlanıyor. Laboratuvar her gece geçmiş koşulardan jokeylerin atın gücünden arındırılmış katkısını hesaplar.</p></div>`;
    const tr=t=>t==="yukseliyor"?"📈":t==="dusuyor"?"📉":"➖";
    const L=J.jokeyler.slice(0,25), mx=Math.max(...L.map(x=>Math.abs(+x.katki||0)),1e-9);
    const row=(x,i)=>`<div class="jk-r"><span class="jk-i">${i+1}</span><span class="jk-n"><b>${esc(x.ad)} ${tr(x.form_trend)}</b><small>${x.binis_90g} biniş · kazanma %${Math.round((x.kazanma_90g||0)*100)} · ilk 3 %${Math.round((x.ilk3_90g||0)*100)}${x.uzmanlik?` · ${esc([x.uzmanlik.pist,x.uzmanlik.mesafe,x.uzmanlik.hipodrom].filter(Boolean).join(", "))}`:""}</small>
      ${(x.bugun_binis||[]).length?`<span class="jk-b">${x.bugun_binis.slice(0,4).map(b=>`<button type="button" data-jb="${esc(b.kosu_id)}|${esc(b.at)}">${esc(b.kosu_id.split("/").slice(1).join(" "))}. koşu · ${esc(b.at)} ${b.p_kazanma!=null?"%"+Math.round(b.p_kazanma*100):""}</button>`).join("")}</span>`:""}</span>
      <span class="jk-k"><b>${(+x.katki>0?"+":"")+(+x.katki).toFixed(2).replace(".",",")}</b><i style="width:${Math.max(4,Math.abs(+x.katki)/mx*100)}%;${+x.katki<0?"background:#FF8A80":""}"></i></span></div>`;
    const tl=(J.antrenorler||[]).slice(0,15), ik=(J.ikililer||[]).slice(0,10);
    return `<div class="at-race"><div class="at-rh"><b>🏇 Jokey sıralaması</b><span>son 90 gün · atın gücünden arındırılmış katkı</span></div>
      <p class="note" style="margin:6px 0">"Katkı", jokeyin aynı atla beklenenden ne kadar iyi sonuç aldığını gösterir; yalnız kazanma sayısına bakmaz. 📈 formu yükselen, 📉 düşen.</p>${L.map(row).join("")}</div>
      ${tl.length?`<details class="sx"><summary>🧑‍🏫 Antrenörler <small>${tl.length}</small></summary><div class="sx-in"><div class="at-race">${tl.map(row).join("")}</div></div></details>`:""}
      ${ik.length?`<details class="sx"><summary>🤝 En uyumlu jokey–antrenör ikilileri <small>${ik.length}</small></summary><div class="sx-in"><div class="at-race">${ik.map((x,i)=>`<div class="jk-r"><span class="jk-i">${i+1}</span><span class="jk-n"><b>${esc(x.jokey)} + ${esc(x.antrenor)}</b><small>${x.binis} birliktelik · kazanma %${Math.round((x.kazanma||0)*100)}</small></span><span class="jk-k"><b>${(+x.katki>0?"+":"")+(+x.katki).toFixed(2).replace(".",",")}</b></span></div>`).join("")}</div></div></details>`:""}
      <p class="note">Dönem: ${esc((J.donem||[]).join(" – "))} · güncelleme ${esc(J.guncelleme||"")}. Kaynak: açık yarış sonuç arşivi; yalnız türetilmiş istatistik.</p>`; }
  function goldOfDay(D){ const out=[];
    for(const r of D.kosular||[]){ const A=(r.atlar||[]).slice().sort((a,b)=>b.p_kazanma-a.p_kazanma); if(A.length<2) continue;
      const a=A[0], gap=a.p_kazanma-A[1].p_kazanma; if(a.p_kazanma>=.35&&gap>=.12) out.push({r,h:a,s:a.p_kazanma+gap}); }
    return out.sort((x,y)=>y.s-x.s).slice(0,3); }
  function resOfDay(d){ const K=resOfDayK(d); const C=AT.canli&&AT.canli[d]; if(!C) return K; const have=new Set(K.map(x=>x.kosu_id));
    const ex=(C.kosular||[]).filter(c=>c.sonuc&&!have.has(c.kosu_id)).map(c=>({kosu_id:c.kosu_id,tarih:d,hipodrom:c.hipodrom,kosu:c.kosu,kazanan:c.sonuc.kazanan_ad||c.sonuc.kazanan,ilk_secim:(c.atlar||[]).find(h=>String(h.no)===String(c.sonuc.model_ilk))?.ad||c.sonuc.model_ilk,ilk_secim_tuttu:!!c.sonuc.tuttu,p_kazanan:((c.atlar||[]).find(h=>String(h.no)===String(c.sonuc.kazanan))||{}).p_sabah}));
    return K.concat(ex).sort((a,b)=>a.hipodrom.localeCompare(b.hipodrom,"tr")||a.kosu-b.kosu); }
  function resOfDayK(d){ return ((AT.karne&&AT.karne.kosular)||[]).map(x=>{ const k=String(x.kosu_id||"").split("/"); return Object.assign({tarih:k[0],hipodrom:k[1]||"",kosu:+k[2]||0},x); })
      .filter(x=>x.tarih===d).sort((a,b)=>a.hipodrom.localeCompare(b.hipodrom,"tr")||a.kosu-b.kosu); }
  function dLbl(d){ const t=dISO(0); return d===t?"Bugün":d===dISO(1)?"Yarın":d===dISO(-1)?"Dün":fD(d); }
  function hero(){ const M=AT.model&&AT.model.degerlendirme, me=M&&M.metrik||{}, h=me.harman||{}, f=me.favori||{}, mo=me.model||{}, n=(M&&M.kosu_sayisi&&M.kosu_sayisi.sinama)||0;
    const K=(AT.karne&&AT.karne.kosular||[]).filter(x=>x.kosudan_once!==false&&!x.mod_hatali); const kn=K.length, kh=K.filter(x=>x.ilk_secim_tuttu).length;
    return `<div class="at-hero"><div class="at-logo">${LOGO("h")}</div><div><h2>At Yarışı<span class="at-pill">DENEME</span></h2><p>OXXai at laboratuvarı: her gece geçmiş koşulardan yeniden öğrenir, yalnız isabeti artıran ayarı kabul eder.</p></div></div>
      <details class="sx" id="atOz"${(()=>{ try{ return localStorage.getItem("bx-at-oz")==="1"?" open":""; }catch(e){ return ""; } })()}><summary>Model ne kadar başarılı? <small>sınama ve karne</small></summary><div class="sx-in">
      <div class="at-km at-km4"><div><b>${pct(mo.ilk_secim_isabet)}</b><small>sabah tahmini<br>ilk seçim kazandı</small></div><div><b>${pct(h.ilk_secim_isabet)}</b><small>oranla harman<br>ilk seçim kazandı</small></div><div><b>${pct(f.ilk_secim_isabet)}</b><small>piyasa favorisi<br>aynı koşularda</small></div><div><b>${kn?"%"+Math.round(kh/kn*100):"–"}</b><small>kilitli karne<br>${kn?kn+" koşu":"birikiyor"}</small></div></div>
      <p class="at-note">🧪 Dürüst durum (son ${n.toLocaleString("tr-TR")} koşuda sınandı): burada gördüğün <b>sabah tahmini</b> oran açılmadan yapılır ve piyasa favorisinin gerisindedir. Koşu öncesi oranla harmanlanınca olasılık hatasında piyasayı az farkla geçiyor, ama ilk seçim isabetinde henüz favori seviyesinde. Model her gece yeniden öğrenir. Garanti değildir · 18+. Şans oyunu sitesine yönlendirme yoktur.</p></div></details>`; }
  // ---- 📋 Padok Notu: günün yarış öncesi açıklaması; her veri akışında (sabah kilidi, oran, sonuç, 6'lı ayağı) yeniden yazılır ----
  function padok(){ const d=AT.d, D=d&&AT.data[d]; if(!D||!(D.kosular||[]).length) return null;
    const C=AT.canli&&AT.canli[d], A=AT.alt&&AT.alt[d], L=[], now=Date.now(), day=dLbl(d);
    const P=x=>"%"+Math.round((x||0)*100), hm=s=>s?String(s).slice(11,16)||String(s).slice(0,5):"";
    const KS=D.kosular.slice().sort((a,b)=>(a.saat||"").localeCompare(b.saat||"")), hips=[...new Set(KS.map(r=>r.hipodrom))];
    const son=r=>{ const c=cRace(r); return c&&c.sonuc?c.sonuc:null; };
    const bitti=r=>!!son(r)||(()=>{ const t=Date.parse(d+"T"+(r.saat||"23:59")+":00+03:00"); return isFinite(t)&&t+20*60e3<now; })();
    const lnk=(r,h)=>`<span class="pd-h" data-ah="${esc(r.kosu_id)}|${esc(h.no)}" role="button">${esc(h.ad)}</span>`;
    const yer=r=>`${esc(r.hipodrom)} ${r.kosu}. koşu${r.saat?", saat "+esc(r.saat):""}`;
    // 1) program ve ilerleme
    const ilk=KS[0], biten=KS.filter(r=>son(r)), kalan=KS.filter(r=>!bitti(r));
    let p1=`${esc(day)} ${hips.length} hipodromda ${KS.length} koşu var: ${hips.map(h=>{ const R=KS.filter(r=>r.hipodrom===h); return `${esc(h)} ${R.length} koşu (${esc(R[0].saat||"")}–${esc(R[R.length-1].saat||"")})`; }).join(", ")}.`;
    if(biten.length){ const ok=biten.filter(r=>son(r).tuttu).length; p1+=` Şu ana kadar <b>${biten.length}</b> koşu bitti; modelin ilk seçimi <b>${ok}</b> tanesinde kazandı${kalan.length?`, ${kalan.length} koşu kaldı`:biten.length<KS.length?`; koşuları geçen ${KS.length-biten.length} koşunun sonucu arşive henüz gelmedi`:", günün tüm koşuları tamamlandı"}.`; }
    else if(ilk&&!bitti(ilk)) p1+=` İlk koşu: ${esc(ilk.hipodrom)}, saat ${esc(ilk.saat||"")}.`;
    L.push(["🗓️",p1]);
    // 2) altın atlar ve durumları
    const G=goldOfDay(D);
    if(G.length) L.push(["🥇",`Günün altın at${G.length>1?"ları":"ı"}: `+G.map(x=>{ const s=son(x.r); const st=s?(String(s.kazanan)===String(x.h.no)?" <b class=\"pd-ok\">✓ kazandı</b>":" <b class=\"pd-no\">✗ kazanamadı</b>"):""; return `${lnk(x.r,x.h)} · ${yer(x.r)} · kazanma şansı <b>${P(x.h.p_kazanma)}</b>${st}`; }).join("; ")+"."]);
    else L.push(["🥇","Bugün altın kuralına uyan at yok: model hiçbir koşuda yeterince emin değil, bu yüzden altın vermiyor."]);
    // 3) piyasa sinyali (oran açıldıysa): sabah tahminine göre en çok yükselen at
    if(C){ let best=null; for(const r of kalan){ const c=cRace(r); if(!c) continue; for(const h of c.atlar||[]){ const t0=(r.atlar||[]).find(x=>String(x.no)===String(h.no)); if(!t0||h.p_piyasa==null||h.p_piyasa<.12) continue; const df=h.p_piyasa-(t0.p_kazanma||0); if(!best||df>best.df) best={r,h:t0,pq:h.p_piyasa,df}; } }
      if(best&&best.df>=.06) L.push(["💹",`Oranlar açıldı. Piyasanın modelden çok daha fazla inandığı at: ${lnk(best.r,best.h)} (${yer(best.r)}). OXXai tahmini ${P(best.h.p_kazanma)}, piyasa oranına göre ${P(best.pq)}.${C.guncelleme_tsi?` <small>${esc(hm(C.guncelleme_tsi))} oranı</small>`:""}`]); }
    // 4) en açık koşu (henüz koşulmamış)
    const op=kalan.map(r=>({r,m:Math.max(...(r.atlar||[]).map(h=>h.p_kazanma||0))})).filter(x=>x.m>0).sort((a,b)=>a.m-b.m)[0];
    if(op&&op.m<.2) L.push(["🎲",`Günün en açık koşusu ${yer(op.r)}. Favori bile ${P(op.m)}, sürprize çok açık.`]);
    // 5) 6'lı tahmin
    if(A&&(A.altililar||[]).length){ const sv=AT.sev||"orta", SV=SEV.find(x=>x[0]===sv)[1];
      const t=A.altililar.map(X=>{ const S=X.seviyeler&&X.seviyeler[sv], R=X.sonuc, at=R&&R.ayak_tuttu&&R.ayak_tuttu[sv]; if(!S) return "";
        const b=(at||[]).filter(v=>v!=null).length, dus=(at||[]).some(v=>v===false), bk=(S.ayaklar||[]).map((a,i)=>a.banko?i+1:0).filter(Boolean);
        const st=R&&R.tamam?(R.tuttu&&R.tuttu[sv]?" <b class=\"pd-ok\">✓ tuttu</b>":` <b class="pd-no">✗ tutmadı</b> (${(at||[]).filter(Boolean).length}/6)`):b?(dus?` · ${b}/6 ayak bitti, <b class="pd-no">KUPO düştü</b>`:` · ${b}/6 ayak bitti, <b class="pd-ok">KUPO hâlâ ayakta</b>`):"";
        return `${esc(X.hipodrom)} ${X.no}. 6'lı (${esc(X.saat||"")}) <b>%${(S.p*100).toFixed(S.p<.1?1:0).replace(".",",")}</b>${bk.length?` · tek at ayak: ${bk.join(", ")}`:""}${st}`; }).filter(Boolean);
      if(t.length) L.push(["🎯",`6'lı tahminde 6 ayağı birden tutma şansı (${SV} KUPO): ${t.join("; ")}.`]); }
    // 6) formdaki jokey (bugün binişi olanlar arasında en yüksek katkı)
    const J=AT.jok&&(AT.jok.jokeyler||[]).filter(x=>(x.bugun_binis||[]).length&&+x.katki>0).sort((a,b)=>b.katki-a.katki)[0];
    if(J){ const bb=J.bugun_binis.slice().sort((a,b)=>(b.p_kazanma||0)-(a.p_kazanma||0))[0]; const r=bb&&D.kosular.find(x=>x.kosu_id===bb.kosu_id), h=r&&(r.atlar||[]).find(x=>x.ad===bb.at);
      L.push(["🏇",`Günün jokeyi: <b>${esc(J.ad)}</b>${J.form_trend==="yukseliyor"?" 📈":""}. Son 90 günde bindiği attan bağımsız en güçlülerden; bugün ${J.bugun_binis.length} binişi var${r&&h?`, en şanslısı ${lnk(r,h)} (${yer(r)}, kazanma şansı ${P(h.p_kazanma)})`:""}.`]); }
    // 7) dünün karnesi
    const kg=AT.karne&&AT.karne.gunler, yd=dISO(-1), yk=kg&&(Array.isArray(kg)?kg.find(x=>x.tarih===yd):kg[yd]);
    if(d===dISO(0)&&yk&&yk.kosu) L.push(["📊",`Dün kilitli tahminler ${yk.kosu} koşuda sınandı; ilk seçim %${Math.round((yk.ilk_secim_isabet||0)*100)} kazandı.`]);
    const up=[C&&C.guncelleme_tsi,A&&A.guncelleme_tsi,D.kilit_zamani_tsi].filter(Boolean).sort().pop();
    return {L,up:hm(up)}; }
  function padokHtml(){ const p=padok(); if(!p) return "";
    return `<div class="pd-card"><div class="pd-hd"><b>📋 Padok Notu</b><small>${esc(dLbl(AT.d))} · ${p.up?"güncellendi "+esc(p.up):"sabah tahmini"}</small></div>
      ${p.L.map(([ic,t])=>`<p class="pd-l"><span class="pd-i">${ic}</span><span>${t}</span></p>`).join("")}
      <p class="pd-f">Oran, sonuç ve 6'lı ayakları geldikçe kendiliğinden yeniden yazılır. Hobi amaçlı olasılıktır, garanti değildir · 18+</p></div>`; }
  window.BX_padok=()=>padok();
  // ---- gün içi canlı veri (data/at/canli/<gün>.json): oranla güncel olasılık + aynı akşam sonuç ----
  const FAV=(()=>{ try{ return new Set(JSON.parse(localStorage.getItem("bx-at-fav")||"[]")); }catch(e){ return new Set(); } })();
  const favSave=()=>{ try{ localStorage.setItem("bx-at-fav",JSON.stringify([...FAV].slice(-200))); }catch(e){} };
  function cRace(r){ const C=AT.canli&&AT.canli[AT.d]; return C?(C.kosular||[]).find(x=>x.kosu_id===r.kosu_id||(x.hipodrom===r.hipodrom&&x.kosu===r.kosu))||null:null; }
  function merged(r){ const c=cRace(r), byNo={}; if(c) for(const h of c.atlar||[]) byNo[h.no]=h;
    const A=(r.atlar||[]).map(h=>{ const x=byNo[h.no]||{}; const po=x.p_oran!=null?x.p_oran:null;
      return Object.assign({},h,{jokey:x.jokey??h.jokey??null,antrenor:x.antrenor??null,kilo:x.kilo??h.kilo??null,yas:x.yas??h.yas??null,form:x.form??h.form??null,son3:x.son3||null,oran:x.oran??null,p_oran:po,p_ilk3_oran:x.p_ilk3_oran??null,p_goster:po!=null?po:h.p_kazanma}); });
    return {A:A.sort((a,b)=>b.p_goster-a.p_goster), c, oranli:A.some(h=>h.p_oran!=null)}; }
  function stChip(r,M){ const c=M.c;
    if(c&&c.sonuc){ const S=c.sonuc; const ok=S.tuttu!=null?!!S.tuttu:(M.A[0]&&String(S.kazanan)===String(M.A[0].no));
      return `<span class="at-st ${ok?"ok":"no"}">🏁 Bitti · kazanan ${esc(S.kazanan)} ${esc(S.kazanan_ad||"")} · ${ok?"✓ ilk tahmin tuttu":"✗ ilk tahmin tutmadı"}</span>`; }
    if(M.oranli) return `<span class="at-st or">💹 Oranla güncel${AT.canli[AT.d]&&AT.canli[AT.d].guncelleme_tsi?" · "+esc(AT.canli[AT.d].guncelleme_tsi.slice(11)):""}</span>`;
    return ""; }
  function race(r){ const M=merged(r), A=M.A, mx=A.length?A[0].p_goster:1, id=r.kosu_id, op=AT.open.has(id), L=op?A:A.slice(0,4), win=M.c&&M.c.sonuc?String(M.c.sonuc.kazanan):null;
    const ik=r.ikili_onerisi; return `<div class="at-race" data-rid="${esc(id)}"><div class="at-rh"><b>${r.kosu}. Koşu</b><span>${esc(r.mesafe+" m · "+r.pist+" · "+r.sinif)}</span><span class="t">${esc(r.saat||"")}</span></div>
      ${stChip(r,M)}${r.kosudan_once===false?`<span class="at-tag">koşudan sonra kilitlendi · karneye sayılmaz</span>`:""}${!M.oranli&&r.mod&&/yalnız model/.test(r.mod)?` <span class="at-tag">sabah tahmini · piyasa oranı henüz yok</span>`:""}
      <div style="margin-top:6px">${L.map((h,i)=>`<div class="at-h${i===0?" top":""}${win&&String(h.no)===win?" win":""}" data-ah="${esc(id)}|${esc(h.no)}" role="button" tabindex="0"><span class="at-no">${esc(h.no)}</span><span class="at-n"><b>${FAV.has(h.ad)?"⭐ ":""}${esc(h.ad)}${win&&String(h.no)===win?" 🏁":""}</b><small>${esc([h.jokey,h.kilo?h.kilo+" kg":null,h.form?"form "+h.form:null].filter(Boolean).join(" · ")||h.gerekce||"")}</small></span><span class="at-p"><b>${pct(h.p_goster)}</b><small>${h.p_oran!=null?`sabah ${pct(h.p_kazanma)}${h.oran?" · oran "+(+h.oran).toFixed(2).replace(".",","):""}`:`ilk 2: ${pct(h.p_ilk2)}`}</small></span><span class="at-bar"><i style="width:${Math.max(3,h.p_goster/mx*100)}%"></i></span></div>`).join("")}</div>
      ${A.length>4?`<button type="button" class="at-more" data-at="${esc(id)}">${op?"Daralt":"Tüm atlar ("+A.length+")"}</button>`:""}
      ${ik&&ik.sira?`<div class="at-ik">İkili önerisi (sabah): <b>${ik.sira.map(esc).join(" - ")}</b> · tam bu sırayla gelme olasılığı <b>${pct(ik.p)}</b></div>`:""}
      <button type="button" class="at-share" data-sh="${esc(id)}">📤 Bu koşunun tahminini paylaş</button></div>`; }
  function horseSheet(rid,no){ const D=AT.data[AT.d]; const r=D&&D.kosular.find(x=>x.kosu_id===rid); if(!r) return; const M=merged(r), h=M.A.find(x=>String(x.no)===String(no)); if(!h) return;
    const old=$("atSheet"); if(old) old.remove(); const el=document.createElement("div"); el.className="gate g2"; el.id="atSheet";
    const s3=(h.son3||[]).map(k=>`<li>${esc(fD(k.tarih))} · ${esc(k.hipodrom)} ${esc(k.mesafe+" m "+k.pist)} → <b>${k.sira!=null?k.sira+".":"–"}</b></li>`).join("");
    el.innerHTML=`<div class="gbox" role="dialog" aria-modal="true" style="text-align:left"><h2 style="margin:0 0 4px">${esc(h.no)} · ${esc(h.ad)}</h2>
      <p class="note" style="margin:0 0 10px">${esc(r.hipodrom)} ${r.kosu}. koşu · ${esc(r.saat||"")} · ${esc(r.mesafe+" m "+r.pist)}</p>
      <div class="at-km at-km4" style="margin-bottom:10px"><div><b>${pct(h.p_kazanma)}</b><small>sabah<br>kazanma</small></div><div><b>${pct(h.p_oran)}</b><small>oranla<br>kazanma</small></div><div><b>${pct(h.p_ilk3_oran!=null?h.p_ilk3_oran:h.p_ilk3)}</b><small>ilk 3'e<br>girme</small></div><div><b>${h.oran?(+h.oran).toFixed(2).replace(".",","):"–"}</b><small>piyasa<br>oranı</small></div></div>
      <ul class="g2-l">${h.jokey?`<li><span>🏇</span><div>Jokey: <b>${esc(h.jokey)}</b></div></li>`:""}${h.antrenor?`<li><span>🧑‍🏫</span><div>Antrenör: <b>${esc(h.antrenor)}</b></div></li>`:""}${h.kilo||h.yas?`<li><span>⚖️</span><div>${h.kilo?esc(h.kilo)+" kg":""}${h.kilo&&h.yas?" · ":""}${h.yas?esc(h.yas)+" yaş":""}</div></li>`:""}${h.form?`<li><span>📈</span><div>Son koşu dizisi: <b>${esc(h.form)}</b></div></li>`:""}${h.gerekce?`<li><span>🧠</span><div>${esc(h.gerekce)}</div></li>`:""}</ul>
      ${s3?`<p class="note" style="margin:4px 0">Son 3 koşusu</p><ul style="margin:0 0 10px;padding-left:18px;font-size:13.5px;line-height:1.6">${s3}</ul>`:""}
      <button class="g2-go" type="button" id="atFav">${FAV.has(h.ad)?"⭐ Takipten çıkar":"☆ Bu atı takip et"}</button><button class="g2-no" type="button" id="atX">Kapat</button>
      <p class="g2-s">Olasılıklar OXXai modelinindir; garanti değildir · 18+</p></div>`;
    document.body.appendChild(el); const close=()=>{ el.classList.add("out"); setTimeout(()=>el.remove(),250); };
    $("atX").onclick=close; el.onclick=e=>{ if(e.target===el) close(); };
    $("atFav").onclick=()=>{ FAV.has(h.ad)?FAV.delete(h.ad):FAV.add(h.ad); favSave(); try{ buzz(8); }catch(e){} close(); render(); toast(FAV.has(h.ad)?"⭐ "+h.ad+" takipte":"Takipten çıkarıldı"); }; }
  async function shareRace(rid){ const D=AT.data[AT.d]; const r=D&&D.kosular.find(x=>x.kosu_id===rid); if(!r) return; const M=merged(r);
    const t=`🐎 ${r.hipodrom} ${r.kosu}. koşu · ${r.saat||""} (${r.mesafe} m ${r.pist})\nOXXai tahmini${M.oranli?" (oranla güncel)":" (sabah)"}:\n`+M.A.slice(0,3).map((h,i)=>`${i+1}) ${h.no} ${h.ad} %${Math.round(h.p_goster*100)}`).join("\n")+`\nHobi amaçlı olasılıktır, garanti değildir · 18+\nbulutoxx.github.io/#at`;
    try{ if(navigator.share){ await navigator.share({text:t}); return; } }catch(e){ return; }
    try{ await navigator.clipboard.writeText(t); toast("📋 Koşu tahmini kopyalandı"); }catch(e){ location.href="https://wa.me/?text="+encodeURIComponent(t); } }
  function render(){ const v=$("v-at"); if(!v||v.hidden) return; const box=$("atBox"); if(!box) return;
    let h=hero();
    if(!AT.d){ box.innerHTML=h+`<div class="panel"><p class="note" style="margin:0">${AT.busy?"Yükleniyor…":"Bugün ve yakın günler için kilitli at yarışı tahmini bulunamadı. Laboratuvar her sabah 05:23 ve öğlen 12:23'te yeni programı işler."}</p></div>`; return; }
    const D=AT.data[AT.d], hips=[...new Set(D.kosular.map(r=>r.hipodrom))]; if(!AT.hip||!hips.includes(AT.hip)) AT.hip=hips[0];
    const G=goldOfDay(D), S=resOfDay(AT.d);
    try{ h+=padokHtml(); }catch(e){}
    h+=`<div class="at-tabs" role="tablist"><button type="button" data-t="tah" aria-pressed="${AT.tab==="tah"}">Tahmin</button><button type="button" data-t="altin" aria-pressed="${AT.tab==="altin"}">🥇 Altın${G.length?` <small>${G.length}</small>`:""}</button><button type="button" data-t="sonuc" aria-pressed="${AT.tab==="sonuc"}">Sonuç${S.length?` <small>${S.length}</small>`:""}</button><button type="button" data-t="altili" aria-pressed="${AT.tab==="altili"}">6\'lı</button><button type="button" data-t="jokey" aria-pressed="${AT.tab==="jokey"}">Jokey</button></div>`;
    h+=`<div class="at-chips" role="group" aria-label="Gün">${AT.days.map(d=>`<button type="button" data-d="${d}" aria-pressed="${d===AT.d}">${dLbl(d)}</button>`).join("")}</div>`;
    const FT=[]; if(FAV.size) for(const r of D.kosular) for(const h of r.atlar||[]) if(FAV.has(h.ad)) FT.push({r,h});
    if(FT.length&&AT.tab==="tah") h+=`<div class="at-fav"><b>⭐ Takip ettiğin atlar bugün koşuyor</b>${FT.map(x=>`<div class="at-fr" data-ah="${esc(x.r.kosu_id)}|${esc(x.h.no)}" role="button">${esc(x.r.hipodrom)} ${x.r.kosu}. koşu ${esc(x.r.saat||"")} · <b>${esc(x.h.no)} ${esc(x.h.ad)}</b> · ${pct(merged(x.r).A.find(y=>y.no===x.h.no)?.p_goster)}</div>`).join("")}</div>`;
    if(AT.tab==="jokey"){ h+=jokeyHtml(); }
    else if(AT.tab==="altili"){ h+=altiliHtml(); }
    else if(AT.tab==="altin"){
      h+=`<div class="at-gold"><div class="at-gh">🥇 Günün Altın atları <small>${esc(dLbl(AT.d))} · tüm hipodromlar · en fazla 3</small></div>
        <p class="at-gn">Kural: koşusunda kazanma olasılığı en yüksek olan, en yakın rakibine en az 12 puan fark atan ve olasılığı %35+ olan at; günde en çok güvenilen 3 tanesi. Futboldaki Altın gibi temkinli seçilir.</p>
        ${G.length?G.map(x=>`<div class="at-gr"><span class="at-no">${esc(x.h.no)}</span><span class="at-n"><b>${esc(x.h.ad)}</b><small>${esc(x.r.hipodrom)} ${x.r.kosu}. koşu · ${esc(x.r.saat||"")} · ${esc(x.r.mesafe+" m "+x.r.pist)}</small></span><span class="at-p"><b>${pct(x.h.p_kazanma)}</b><small>ilk 3: ${pct(x.h.p_ilk3)}</small></span></div>`).join("")
          :`<p class="at-gn" style="margin:6px 0 0">Bu gün için Altın kuralına uyan at yok; model yeterince emin olmadığında Altın vermez.</p>`}</div>`;
    } else if(AT.tab==="sonuc"){
      h+=S.length?`<div class="at-race">${S.map(x=>`<div class="at-sr"><span class="at-no">${x.kosu}</span><span class="at-n"><b>${esc(x.hipodrom)} ${x.kosu}. koşu · kazanan: ${esc(x.kazanan||"–")}</b><small>Modelin ilk seçimi: ${esc(x.ilk_secim||"–")} · kazananın olasılığı ${pct(x.p_kazanan)}${x.kosudan_once===false?" · karneye sayılmaz":""}</small></span><span class="at-ok ${x.ilk_secim_tuttu?"y":"n"}">${x.ilk_secim_tuttu?"✓":"✗"}</span></div>`).join("")}</div>`
        :`<div class="panel"><p class="note" style="margin:0">Bu günün sonuçları henüz arşive gelmedi. Açık arşiv her gece güncellenir; laboratuvar sabah 05:23'te kilitli tahminleri sonuçla karşılaştırır.</p></div>`;
    } else {
      h+=`<div class="at-chips" role="group" aria-label="Hipodrom">${hips.map(x=>`<button type="button" data-h="${esc(x)}" aria-pressed="${x===AT.hip}">${esc(x)} · ${D.kosular.filter(r=>r.hipodrom===x).length}</button>`).join("")}</div>`;
      const KS=D.kosular.filter(r=>r.hipodrom===AT.hip).sort((a,b)=>a.kosu-b.kosu), now=Date.now();
      const bitti=r=>{ const c=cRace(r); if(c&&c.sonuc) return true; const t=Date.parse(AT.d+"T"+(r.saat||"23:59")+":00+03:00"); return isFinite(t)&&t+15*60e3<now; };
      const ac=KS.filter(r=>!bitti(r)), bt=KS.filter(bitti);
      h+=ac.map(race).join("")||`<div class="panel"><p class="note" style="margin:0">Bu hipodromda bugün başlamamış koşu kalmadı.</p></div>`;
      if(bt.length) h+=`<details class="sx"><summary>🏁 Biten koşular <small>${bt.length}</small></summary><div class="sx-in">${bt.map(race).join("")}</div></details>`;
    }
    h+=`<p class="note">Kilit: ${esc(D.kilit_zamani_tsi||"")} · model ${esc(D.model_surumu||"")}. Veri: herkese açık yarış sonuç arşivi (GitHub aynası); OXXai resmî yarış sitesine istek atmaz. ${esc(String(D.not||"").replace(/kosudan_once=false olan koşular canlı karneye sayılmaz\.?/,"Koşular başladıktan sonra eklenen tahminler karneye sayılmaz."))}</p>`;
    box.innerHTML=h;
    box.querySelectorAll("[data-d]").forEach(b=>b.onclick=()=>{ AT.d=b.dataset.d; buzz(6); render(); });
    const oz=$("atOz"); if(oz) oz.addEventListener("toggle",()=>{ try{ localStorage.setItem("bx-at-oz",oz.open?"1":"0"); }catch(e){} });
    box.querySelectorAll("[data-t]").forEach(b=>b.onclick=()=>{ AT.tab=b.dataset.t; buzz(6); try{ Sound.tap(); }catch(e){} render(); });
    box.querySelectorAll("[data-h]").forEach(b=>b.onclick=()=>{ AT.hip=b.dataset.h; buzz(6); render(); });
    box.querySelectorAll("[data-at]").forEach(b=>b.onclick=()=>{ const k=b.dataset.at; AT.open.has(k)?AT.open.delete(k):AT.open.add(k); render(); });
    box.querySelectorAll("[data-ah]").forEach(b=>b.onclick=()=>{ const [rid,no]=b.dataset.ah.split("|"); try{ buzz(6); }catch(e){} horseSheet(rid,no); });
    box.querySelectorAll("[data-sh]").forEach(b=>b.onclick=()=>shareRace(b.dataset.sh));
    box.querySelectorAll("[data-sev]").forEach(b=>b.onclick=()=>{ AT.sev=b.dataset.sev; try{ buzz(6); }catch(e){} render(); });
    box.querySelectorAll("[data-als]").forEach(b=>b.onclick=()=>shareAlt(b.dataset.als));
    box.querySelectorAll("[data-jb]").forEach(b=>b.onclick=()=>{ const [rid,ad]=b.dataset.jb.split("|"); const D=AT.data[AT.d]; const r=D&&D.kosular.find(x=>x.kosu_id===rid); const hh=r&&(r.atlar||[]).find(x=>x.ad===ad); if(hh) horseSheet(rid,hh.no); else toast("Bu koşu bugünkü listede yok"); }); }
  // görünüm + menü girişi
  const main=document.querySelector("main"); if(main&&!$("v-at")){ const s=document.createElement("section"); s.className="view"; s.id="v-at"; s.hidden=true;
    s.innerHTML=`<div class="bt-head cmp at-head"><div class="tb-row" id="atRow"></div></div><div class="ltitle"><div><h1>At Yarışı</h1><p>Deneme · kendini her gece eğiten olasılık modeli</p></div></div><div class="wrap"><div id="atBox"></div></div>`;
    main.appendChild(s); }
  function openAt(){ showSport("at"); }
  // ⚽ / 🏀 / 🐎 seçici: her seçiciye At düğmesi; At'a basınca tüm At bölümü (tahmin, Altın, sonuçlar) açılır
  const LOGO_S=`<img class="at-emb" src="icons/oxxai-at.webp" alt="" aria-hidden="true" decoding="async" onerror="this.onerror=null;this.src='icons/oxxai-at.png'">`;
  const ATB=`<button type="button" data-s="at" aria-pressed="false" class="sw-at"><span class="sw-logo">${LOGO_S}</span>At</button>`;
  function swMount(){ document.querySelectorAll(".sport-sw").forEach(sw=>{ if(!sw.querySelector('[data-s="at"]')) sw.insertAdjacentHTML("beforeend",ATB);
      sw.querySelectorAll("button").forEach(b=>{ if(b.dataset.s==="bk"&&!b.dataset.sh){ b.dataset.sh=1; b.innerHTML="🏀 Basket"; }
        b.onclick=()=>{ const s=b.dataset.s; const vid=s==="bk"?"basket":s==="at"?"at":"bulten"; if(SPORT.get()!==s||$("v-"+vid).hidden){ buzz(8); showSport(s); } }; });
      sw.querySelectorAll("button").forEach(b=>b.setAttribute("aria-pressed",b.dataset.s===SPORT.get())); });
    const row=$("atRow"); if(row&&!row.querySelector(".sport-sw")){ const src=document.querySelector("#v-bulten .sport-sw"); if(src){ const c=src.cloneNode(true); row.appendChild(c); swMount(); } } }
  const _ss=showSport;
  showSport=function(s){ if(s!=="at") return _ss.apply(this,arguments);
    if(SPORT.get&&SPORT.get()==="at") try{ window.scrollTo({top:0,behavior:"smooth"}); }catch(e){}
    SPORT.set("at"); swMount(); goView("at","bulten"); document.querySelectorAll(".sport-sw button").forEach(b=>b.setAttribute("aria-pressed",b.dataset.s==="at")); render(); load(); };
  swMount(); setTimeout(swMount,1500); setTimeout(swMount,5000);
  setTimeout(()=>{ const h=(location.hash||"").slice(1), q=new URLSearchParams(location.search); if(!h&&!q.get("m")&&SPORT.get()==="at") showSport("at"); },400);
  window.openAt=openAt;
  function mountMenu(){ const g=$("mg-analiz")||document.querySelector("#v-more .mlist"); if(!g||$("moreAt")) return;
    const c=document.createElement("button"); c.className="cell"; c.id="moreAt"; c.type="button";
    c.innerHTML=`<span class="ic">${LOGO("m")}</span><span class="tx"><b>At Yarışı <span class="at-pill" style="vertical-align:1px">DENEME</span></b><small>Koşu koşu kazanma olasılıkları · her gece öğrenir</small></span><span class="ar">›</span>`;
    c.onclick=openAt; g.appendChild(c); }
  mountMenu(); setTimeout(mountMenu,1600); setTimeout(mountMenu,5200);
  if((location.hash||"")==="#at") setTimeout(openAt,450);
  // v134+: yarış saatlerinde (koşuya 20 dk kala → başladıktan 90 dk sonrasına, sonuç gelene dek) yalnız canlı dosya 45 sn'de bir
  // tazelenir (önbelleksiz); tam yükleme 5 dk'da bir. Sayfa/sekme gizliyken çalışmaz (perf-v118 planlayıcısı).
  let lastFull=Date.now();
  const hotAt=()=>{ const d0=dISO(0), C=AT.canli&&AT.canli[d0], now=Date.now(); if(!C||!C.kosular) return false;
    return C.kosular.some(k=>{ if(k.sonuc||!k.saat) return false; const t=new Date(d0+"T"+k.saat+":00+03:00").getTime(); return isFinite(t)&&now>t-20*60e3&&now<t+90*60e3; }); };
  async function loadCanli(){ const ds=[...new Set([dISO(0),AT.d].filter(d=>d&&AT.days.includes(d)))]; if(!ds.length) return;
    const cs=await Promise.all(ds.map(d=>j("data/at/canli/"+d+".json"))); let ch=false; AT.canli=AT.canli||{};
    ds.forEach((d,i)=>{ const v=cs[i], o=AT.canli[d]; if(v&&v.kosular&&(!o||o.guncelleme_tsi!==v.guncelleme_tsi)){ AT.canli[d]=v; ch=true; } });
    if(ch){ render(); try{ if(window.BX_AT2) window.BX_AT2.paint(); }catch(e){} } }
  setInterval(()=>{ const v=$("v-at"); if(!v||v.hidden||document.hidden) return; if(Date.now()-lastFull>=5*60e3){ lastFull=Date.now(); load(); } else if(hotAt()) loadCanli().catch(()=>{}); },45e3);

  // ---------- OXXai: at yarışı soruları (yalnız telefondaki kilitli olasılıklardan; uydurma yok) ----------
  const NZ=t=>String(t||"").toLocaleLowerCase("tr").replace(/ç/g,"c").replace(/ğ/g,"g").replace(/ı/g,"i").replace(/ö/g,"o").replace(/ş/g,"s").replace(/ü/g,"u").replace(/[^a-z0-9 .]/g," ").replace(/\s+/g," ").trim();
  const VEN=["istanbul","ankara","izmir","bursa","adana","kocaeli","elazig","diyarbakir","sanliurfa","antalya"];
  const AKEY=/\b(at yarisi|at yarislari|atyarisi|kosu|kosular|kosusu|ganyan|hipodrom|jokey|altili ganyan|plase|veliefendi|atlar)\b|\bat (bolum|yaris)\w*/;
  async function ensure(){ if(!AT.days.length) await load(); return AT.d?AT.data[AT.d]:null; }
  function horseRow(h){ return `<b>${esc(h.no)} · ${esc(h.ad)}</b> — kazanma <b>${pct(h.p_kazanma)}</b>, ilk 3: ${pct(h.p_ilk3)}${h.gerekce?` <small>(${esc(h.gerekce)})</small>`:""}`; }
  const DISCf=()=>`<br><small>Sabah tahmini; piyasa favorisi seviyesinin gerisindedir (sınamada ilk seçim ${pct(((AT.model&&AT.model.degerlendirme&&AT.model.degerlendirme.metrik)||{}).model?.ilk_secim_isabet)}). Garanti değildir · 18+</small>`;
  // 6'lı tahmin: "bugün 6'lı", "altılı ganyan", "istanbul 6'lı" (futbol "altılı kupon" sorusu futbola kalır)
  const ALTK=/\b(6 ?li|altili)\b/, FUTK=/\b(kupon|kuponu|mac|maci|maclar|futbol|basket|iddaa|lig)\b/;
  function altiliAnswer(n,venue){ const A=AT.alt&&AT.alt[AT.d], K=AT.altK, day=dLbl(AT.d), sv=AT.sev||"orta", SV=SEV.find(x=>x[0]===sv)[1];
    const fx=(p,d)=>(p*100).toFixed(d).replace(".",",");
    const g=K&&K.geriye_donuk, gs=g&&g.seviyeler&&g.seviyeler[sv], si=g&&g.sinama&&g.sinama.seviyeler&&g.sinama.seviyeler[sv];
    const kar=gs&&gs.n?`<br>📊 Geriye dönük test (${esc((g.donem||[]).join(" – "))}, ${SV}): ${gs.n} altılıdan tutan <b>${gs.isabet}</b> (model beklentisi ${(+gs.beklenen).toFixed(1).replace(".",",")}); ayak isabeti %${Math.round((gs.ayak_isabet||0)*100)}${gs.altin_ayak&&gs.altin_ayak.n?`, altın ayak isabeti %${Math.round((gs.altin_ayak.isabet||0)*100)}`:""}${si&&si.n?`; son 1/3 sınama diliminde ${si.n} altılıdan tutan ${si.isabet} (beklenti ${(+si.beklenen).toFixed(1).replace(".",",")})`:""}.`:"";
    let L=(A&&A.altililar)||[]; if(venue) L=L.filter(X=>NZ(X.hipodrom).includes(venue));
    if(!L.length) return {html:`🎯 ${esc(day)} ${venue?esc(venue)+" için ":""}6'lı tahmin tahmini henüz hazır değil.${kar}<br><small>Hobi amaçlı olasılıktır · 18+</small>`,chips:["At bölümünü aç","Altın atlar"]};
    const h=L.slice(0,4).map(X=>{ const S=X.seviyeler[sv], R=X.sonuc;
      return `<b>${esc(X.hipodrom)} ${X.no}. 6'lı</b> (${X.baslangic_kosu}.–${X.baslangic_kosu+5}. koşular${X.saat?", "+esc(X.saat):""}) · ${S.kombinasyon} kombinasyon · 6'yı birden tutma olasılığı <b>%${fx(S.p,S.p<.1?1:0)}</b>`+
        (X.kosudan_once===false?" · <small>koşular başladıktan sonra kuruldu, karneye sayılmaz</small>":"")+(R&&R.tamam?` · sonuç: ${R.tuttu&&R.tuttu[sv]?"✓ tuttu":"✗ tutmadı"} (${(R.ayak_tuttu[sv]||[]).filter(Boolean).length}/6 ayak)`:"")+"<br>"+
        S.ayaklar.map((a,i)=>`${i+1}. ayak: ${a.secim.map(esc).join("-")}${a.banko?" 🥇":""} (%${Math.round(a.p_ayak*100)})`).join(" · "); }).join("<br><br>");
    return {html:`🎯 ${esc(day)} 6'lı tahmin · ${SV} kapsam:<br>${h}${kar}<br><small>Olasılıklar ayaklar bağımsız varsayılarak çarpılır; garanti değildir. Para tutarı gösterilmez · 18+</small>`,chips:["At bölümünü aç","Altın atlar"]}; }
  async function atAnswer(raw){ const n=NZ(raw); const hasKey=AKEY.test(n), venue=VEN.find(v=>n.includes(v));
    if(/\bpadok\b|\bgunun (at )?notu\b|\bat(lar)? (yarisi )?(gunun )?ozeti\b/.test(n)){ await ensure(); const p=padok();
      if(!p) return {html:"📋 Padok Notu: bugün için kilitli at yarışı tahmini henüz yok. Laboratuvar her sabah 05:23'te yeni programı işler.",chips:["At bölümünü aç"]};
      return {html:`📋 <b>Padok Notu</b> · ${esc(dLbl(AT.d))}${p.up?" · "+esc(p.up):""}<br>`+p.L.map(([ic,t])=>`${ic} ${t}`).join("<br>")+`<br><small>Hobi amaçlı olasılıktır, garanti değildir · 18+</small>`,chips:["At bölümünü aç","Bugün 6'lı","Altın atlar"]}; }
    if(ALTK.test(n)&&(hasKey||venue||!FUTK.test(n))){ await ensure(); if(/\b(ac|goster)\b/.test(n)){ AT.tab="altili"; setTimeout(()=>{ try{ openAt(); }catch(e){} },300); } return altiliAnswer(n,venue); }
    const D0=AT.d?AT.data[AT.d]:null; let horseHit=null;
    if(!hasKey&&D0){ for(const r of D0.kosular) for(const h of r.atlar||[]){ const hn=NZ(h.ad); if(hn.length>=7&&(" "+n+" ").includes(" "+hn+" ")) { horseHit={r,h}; break; } } }
    if(!hasKey&&!horseHit) return null;
    if(/\bat (bolum|yaris)\w* ac/.test(n)){ setTimeout(()=>{ try{ openAt(); }catch(e){} },300); return {html:"🐎 At Yarışı bölümünü açıyorum.",chips:["Altın atlar","Bugünkü koşular"]}; }
    const D=await ensure(); if(!D) return {html:"🐎 Bugün için kilitli at yarışı tahmini henüz yok. Laboratuvar her sabah 05:23 ve öğlen 12:23'te yeni programı işler.",chips:["At bölümünü aç"]};
    const day=dLbl(AT.d);
    if(horseHit){ const {r,h}=horseHit; return {html:`🐎 ${esc(day)} ${esc(r.hipodrom)} ${r.kosu}. koşu (${esc(r.saat||"")}, ${esc(r.mesafe+" m "+r.pist)}):<br>${horseRow(h)}${DISCf()}`,chips:[`${r.hipodrom} ${r.kosu}. koşu`,"Altın atlar"]}; }
    if(/\baltin\b/.test(n)){ const G=goldOfDay(D); return {html:G.length?`🥇 ${esc(day)} Altın atlar (en fazla 3):<br>`+G.map(x=>`• ${esc(x.r.hipodrom)} ${x.r.kosu}. koşu ${esc(x.r.saat||"")}: ${horseRow(x.h)}`).join("<br>")+DISCf():`🥇 ${esc(day)} Altın kuralına uyan at yok; model yeterince emin olmadığında Altın vermez.`,chips:["Bugünkü koşular","At bölümünü aç"]}; }
    const km=n.match(/\b(\d{1,2})\s*\.?\s*(?:kosu|ayak)/); const hips=[...new Set(D.kosular.map(r=>r.hipodrom))];
    if(km){ const k=+km[1]; let R=D.kosular.filter(r=>r.kosu===k); if(venue) R=R.filter(r=>NZ(r.hipodrom).includes(venue));
      if(!R.length) return {html:`${esc(day)} ${venue?esc(venue)+" ":""}${k}. koşu bulunamadı. Bugünkü hipodromlar: ${hips.map(esc).join(", ")}.`,chips:hips.map(h=>`${h} ${k}. koşu`).slice(0,3)};
      if(R.length>1&&!venue) return {html:`Bugün ${k}. koşu birden fazla hipodromda var; hangisi?`,chips:R.map(r=>`${r.hipodrom} ${k}. koşu`)};
      const r=R[0], A=(r.atlar||[]).slice().sort((a,b)=>b.p_kazanma-a.p_kazanma), ik=r.ikili_onerisi;
      return {html:`🐎 ${esc(day)} ${esc(r.hipodrom)} ${r.kosu}. koşu · ${esc(r.saat||"")} · ${esc(r.mesafe+" m "+r.pist)} · ${esc(r.sinif||"")}<br>`+A.slice(0,3).map((h,i)=>`${i+1}) ${horseRow(h)}`).join("<br>")+(ik&&ik.sira?`<br>İkili önerisi: <b>${ik.sira.map(esc).join(" - ")}</b> (tam sırayla %${Math.round((ik.p||0)*1000)/10})`:"")+DISCf(),chips:[`${r.hipodrom} ${k+1}. koşu`,"Altın atlar"]}; }
    let R=D.kosular; if(venue) R=R.filter(r=>NZ(r.hipodrom).includes(venue));
    const best=R.map(r=>({r,h:(r.atlar||[]).slice().sort((a,b)=>b.p_kazanma-a.p_kazanma)[0]})).filter(x=>x.h).sort((a,b)=>b.h.p_kazanma-a.h.p_kazanma).slice(0,3);
    return {html:`🐎 ${esc(day)} at yarışları: ${hips.map(h=>`${esc(h)} (${D.kosular.filter(r=>r.hipodrom===h).length} koşu)`).join(", ")}.<br>Modelin en emin olduğu atlar${venue?" ("+esc(venue)+")":""}:<br>`+best.map(x=>`• ${esc(x.r.hipodrom)} ${x.r.kosu}. koşu: ${horseRow(x.h)}`).join("<br>")+DISCf(),
      chips:[...hips.slice(0,2).map(h=>`${h} 1. koşu`),"Altın atlar","At bölümünü aç"]}; }
  if(typeof botAnswer==="function"){ const _ba=botAnswer; botAnswer=async function(raw){ try{ const r=await atAnswer(raw); if(r) return r; }catch(e){} return _ba.apply(this,arguments); }; }
  setTimeout(()=>{ if(!AT.days.length) load(); },8000);
  window.BX_AT={AT,merged,cRace,load,render,dLbl,goldOfDay,horseSheet,openAt,j,NZ,VEN};   // v98 at kuponu bu çekirdeği okur
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: at-v73 */
