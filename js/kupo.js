/* id: kupon-v93 */ try {
// v93: (1) Tahmin listem'e eski kupondaki "Toplam oran" ve "Değerlendirme" satırları geri geldi (kullanıcı kararı)
//      (2) takım adı eşleştirme koruması: U17–U23, B/II, rezerv, akademi, kadın (K) takımları ana takımla eşleşmez
//      (3) "Günün en olası tahminlerini getir": bültenle aynı oranla harmanlı ve kalibre olasılığı kullanır (yalnız-model değil)
(function(){
  const VAR=s=>{ const t=String(s||"").toLowerCase().replace(/ı/g,"i").replace(/[()\[\].,_-]/g," ").replace(/\s+/g," ").trim(), w=t.split(" "), m=new Set();
    for(const x of w){ if(/^u ?(1[5-9]|2[0-3])$/.test(x)) m.add(x);
      else if(/^(reserves?|res)$/.test(x)) m.add("res"); else if(/^(academy|akademi|youth)$/.test(x)) m.add("y");
      else if(/^(women|womens|kadın|kadin|femenino|feminino|frauen|dames|ladies)$/.test(x)) m.add("k"); }
    const last=w[w.length-1]||"", prev=w[w.length-2]||"";   // tek harfli işaretler yalnız sonda: "Real Madrid B", "Jong Ajax II", "Cruzeiro (K)"
    for(const z of [last, /^u ?\d\d$/.test(last)?prev:""]){ if(z==="b"||z==="ii") m.add("b"); else if(z==="k"||z==="w") m.add("k"); }
    return [...m].sort().join(","); };
  try{ const _b=bestTeamName; bestTeamName=function(n){ const r=_b.apply(this,arguments); try{ if(r&&r!==n&&VAR(n)!==VAR(r)) return n; }catch(e){} return r; }; }catch(e){}
  try{ if(typeof BT!=="undefined"&&BT.cache) BT.cache.clear(); }catch(e){}
  // ekranda ayrıca belirt: "Arsenal FC U21" → Arsenal FC [U21], "Cruzeiro EC (K)" → Cruzeiro EC [Kadın]
  const RX=/\s*(\(K\)|\bU ?(?:1[5-9]|2[0-3])\b)/g, SKIP=/^(SCRIPT|STYLE|TEXTAREA|INPUT|OPTION|TITLE)$/;
  function tagNode(tn){ const v=tn.nodeValue; RX.lastIndex=0; if(!RX.test(v)) return; RX.lastIndex=0;
    const fr=document.createDocumentFragment(); let i=0, m;
    while((m=RX.exec(v))){ fr.appendChild(document.createTextNode(v.slice(i,m.index)+" ")); const b=document.createElement("span");
      const k=/\(K\)/.test(m[1]); b.className="tvar"+(k?" k":""); b.textContent=k?"Kadın":m[1].replace(/\s/g,"").toUpperCase(); fr.appendChild(b); i=m.index+m[0].length; }
    fr.appendChild(document.createTextNode(v.slice(i))); tn.parentNode.replaceChild(fr,tn); }
  function tagAll(root){ try{ const w=document.createTreeWalker(root||document.body,NodeFilter.SHOW_TEXT,{acceptNode:n=>{ const p=n.parentNode; if(!p||SKIP.test(p.nodeName)||p.closest(".tvar,[contenteditable],#botQ,.bt-in")) return 2; return /\(K\)|U ?(1[5-9]|2[0-3])|Women|Kadın/.test(n.nodeValue)?1:2; }});
      const L=[]; while(w.nextNode()) L.push(w.currentNode); L.forEach(tagNode); }catch(e){} }
  // v118: gözlemci artık yalnız eklenen/değişen düğümleri işler (eskiden her değişimde <main>'in tüm metin düğümleri taranıyordu)
  const inScope=n=>{ const e=n.nodeType===1?n:n.parentNode; return !!(e&&e.closest&&e.closest("main,#botLog,#sheet")); };
  const PEND=new Set(); let tq=0;
  const flush=()=>{ tq=0; const L=[...PEND]; PEND.clear(); for(const n of L){ if(!n.isConnected||!inScope(n)) continue;
      if(n.nodeType===3){ const p=n.parentNode; if(p&&!SKIP.test(p.nodeName)&&!p.closest(".tvar,[contenteditable],#botQ,.bt-in")&&/\(K\)|U ?(1[5-9]|2[0-3])|Women|Kadın/.test(n.nodeValue)) tagNode(n); }
      else if(n.nodeType===1&&!SKIP.test(n.nodeName)) tagAll(n); } };
  const tsched=recs=>{ for(const r of recs){ if(r.type==="characterData") PEND.add(r.target); else r.addedNodes.forEach(n=>{ if(n.nodeType===1||n.nodeType===3) PEND.add(n); }); }
    if(PEND.size&&!tq){ tq=1; requestAnimationFrame(flush); } };
  try{ new MutationObserver(tsched).observe(document.body,{childList:true,subtree:true,characterData:true}); }catch(e){}
  requestAnimationFrame(()=>{ tagAll(document.querySelector("main")||document.body); const bl=document.getElementById("botLog"); if(bl) tagAll(bl); const sh=document.getElementById("sheet"); if(sh) tagAll(sh); });
  // öneri düğmesi: önümüzdeki 36 saatte oranı ≥1,20 olan, bülten/Power Now ile aynı (harmanlı + kalibre) olasılığı en yüksek 3 seçim, farklı maçlardan
  suggestCoupon=function(){ window.QP_FORCE=true;
    try{ const now=Date.now(), picks=[];
      for(const m of Pick.list()){ if(m.live||m.dt.getTime()<now||m.dt.getTime()>now+36*3600e3) continue;
        const f=FIXTURES.find(x=>x.lg===m.lg&&x.h===m.h&&x.a===m.a); if(!f||!f.odds) continue;
        let p=null; try{ p=quickPred(m,f); }catch(e){} if(!p||!p.pm) continue;
        const R=recOf({H:p.pm[0],D:p.pm[1],A:p.pm[2],o25:p.o25m},f); if(!R||!R.o||R.o<1.2||!(R.cp>0)) continue;
        picks.push({m,R}); }
      picks.sort((a,b)=>b.R.cp-a.R.cp); const used=new Set(); CP.items=[];
      for(const x of picks){ const k=cpKey(x.m); if(used.has(k)) continue; used.add(k); cpToggle(x.m,x.R.k,+x.R.o,x.R.cp); if(used.size>=3) break; }
      if(!CP.items.length) toast("Şu an öneri için yeterli oranlı maç yok");
    }finally{ window.QP_FORCE=false; }
    renderKupon(); };
  // Toplam oran + Değerlendirme (v63'teki gibi)
  function patch(){ try{ const box=$("cpBox"); const L=box&&box.querySelector(".cpsum .list"); if(!L||L.querySelector(".kp-odd")) return; const st=cpStats(); if(!st.n) return;
      const rating=st.ev>=1.05?["Değerli görünüyor","g"]:st.ev>=.92?["Adil","m"]:["Oran olasılığa göre düşük","x"];
      const rows=[...L.children]; const first=rows[0];
      const o=document.createElement("div"); o.className="kp-odd"; o.innerHTML=`<span>Toplam oran</span><span><b>${fO(st.odd)}</b></span>`;
      if(first) first.after(o); else L.appendChild(o);
      const d=document.createElement("div"); d.className="kp-ev"; d.innerHTML=`<span>Değerlendirme</span><span class="pill ${rating[1]}">${rating[0]}</span>`; L.appendChild(d);
    }catch(e){} }
  try{ const _r=renderKupon; renderKupon=function(){ const r=_r.apply(this,arguments); patch(); return r; }; }catch(e){}
  try{ const _k=kuponTab; kuponTab=function(){ const r=_k.apply(this,arguments); patch(); return r; }; }catch(e){}
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: kupon-v93 */
/* id: derbi-v95 */ try {
// v95: Derbi tanıma ve gösterim
//  • DERBI_DATA: takım çiftleri ve ad varyantları (Türkçe/İngilizce/yerel yazım). "=" ile başlayan ad yalnız birebir eşleşir,
//    diğerleri ad başı eşleşmesidir ("Fenerbahçe Beko", "Olympiacos Piraeus" gibi sponsor/şehir ekleri kabul).
//  • Ad normalleştirme: Türkçe karakter + aksan, FC/SK/AŞ/JK/AC/AS/SL/SV/Club ekleri atılır; "(URU)" gibi ülke etiketi farklı takım sayılır.
//  • kupon-v93 VAR() ile aynı: U17–U23, B/II, rezerv, akademi, kadın (K/W/kadın ligi) ana takım DEĞİLDİR. İki taraf aynı genç/kadın
//    varyantındaysa "Genç derbi"/"Kadın derbi", farklıysa derbi sayılmaz.
//  • Ekran: bülten, canlı, Power Now, sonuçlar, Tahmin listem, OXXai kartları, maç penceresi ve basket satırlarında şerit + rozet.
//  • Ölçüm: lab/derbi_karne.py → data/derbi_karne.json (maç penceresindeki not gerçek rakamla yazılır).
(function(){
  const DERBI_DATA=/*DERBI_JSON*/{"v":1,"teams":{"gs":["Galatasaray","Cimbom"],"fb":["Fenerbahçe","Fenerbahce","Fener"],"bjk":["Beşiktaş","Besiktas","=BJK"],"ts":["Trabzonspor"],"goz":["Göztepe","Goztepe","=Goztep"],"ksk":["Karşıyaka","Karsiyaka"],"alt":["=Altay"],"bur":["Bursaspor"],"esk":["Eskişehirspor","Eskisehirspor"],"koc":["Kocaelispor"],"sak":["Sakaryaspor"],"ads":["Adana Demirspor"],"adn":["=Adanaspor"],"ank":["Ankaragücü","MKE Ankaragücü","Ankaragucu"],"gnc":["Gençlerbirliği","Genclerbirligi"],"sam":["Samsunspor"],"efes":["Anadolu Efes","=Efes"],"rm":["Real Madrid"],"fcb":["Barcelona","FC Barcelona","Barça","Barca"],"atm":["Atlético Madrid","Atletico de Madrid","Atl. Madrid","=Atleti"],"esp":["Espanyol","RCD Espanyol"],"sev":["=Sevilla","=Sevilla FC"],"bet":["Real Betis","=Betis"],"ath":["Athletic Bilbao","=Athletic Club"],"rso":["Real Sociedad"],"int":["=Inter","Inter Milan","Inter Milano","Internazionale"],"mil":["=Milan","=AC Milan","=Milan AC"],"rom":["=Roma","=AS Roma"],"laz":["=Lazio","=SS Lazio"],"juv":["=Juventus"],"tor":["=Torino"],"gen":["=Genoa","=Genoa CFC"],"smp":["Sampdoria"],"mu":["Manchester United","Man United","Man Utd","Manchester Utd","=UtdOfManch"],"mc":["Manchester City","Man City"],"liv":["=Liverpool"],"eve":["=Everton"],"ars":["=Arsenal"],"tot":["Tottenham","=Spurs"],"new":["Newcastle United","=Newcastle"],"sun":["=Sunderland","=Sunderland AFC"],"cel":["=Celtic","=Celtic Glasgow"],"ran":["=Rangers","=Glasgow Rangers"],"bay":["Bayern"],"bvb":["Borussia Dortmund","=Dortmund","=B. Dortmund","=BVB"],"s04":["Schalke"],"hsv":["=Hamburger SV","=Hamburg","=HSV"],"stp":["St. Pauli"],"kol":["=Köln","=1. FC Köln","=Cologne"],"bmg":["Borussia Mönchengladbach","Mönchengladbach","=Gladbach"],"psg":["Paris Saint-Germain","=PSG","=Paris SG"],"om":["=Marseille","Olympique de Marseille","Olympique Marseille"],"ol":["=Lyon","Olympique Lyonnais","=OL Lyonnes"],"ase":["=Saint-Étienne","=AS Saint-Étienne","=St Etienne"],"aja":["Ajax"],"fey":["Feyenoord"],"psv":["PSV"],"ben":["Benfica","SL Benfica"],"por":["=Porto","=FC Porto"],"scp":["=Sporting","Sporting CP","Sporting Lisbon","Sporting Lizbon","=Sp Lisbon","Sporting Clube de Portugal"],"oly":["Olympiakos","Olympiacos"],"pao":["Panathinaikos"],"ari":["=Aris","Aris Thessaloniki"],"paok":["PAOK"],"boc":["Boca Juniors"],"riv":["River Plate"],"rac":["=Racing Club","=Racing Club de Avellaneda"],"ind":["=Independiente","=CA Independiente"],"fla":["Flamengo"],"flu":["Fluminense"],"cor":["Corinthians"],"pal":["Palmeiras"],"gre":["Grêmio","Gremio"],"inr":["=Internacional","=SC Internacional"],"cam":["=Atletico-MG","=Atlético Mineiro","=Atletico Mineiro"],"cru":["=Cruzeiro","=Cruzeiro EC"],"nac":["=Nacional (URU)","=Nacional","=Club Nacional"],"pen":["Peñarol","Penarol"],"col":["Colo Colo","Colo-Colo"],"uch":["Universidad de Chile"],"ame":["=América","=Club América","=CF América"],"chv":["Guadalajara","=Chivas","=Chivas Guadalajara"],"ahl":["Al Ahly"],"zam":["Zamalek"],"par":["Partizan"],"czv":["Crvena Zvezda","Kızılyıldız","Kızıl Yıldız","Red Star Belgrade","=Red Star"],"dzg":["Dinamo Zagreb"],"haj":["Hajduk Split"],"spa":["Sparta Prague","Sparta Praha"],"sla":["Slavia Prague","Slavia Praha"],"aus":["Austria Wien","Austria Vienna"],"rap":["=Rapid","Rapid Wien","Rapid Vienna"],"and":["Anderlecht"],"std":["=Standard","Standard Liège","Standard Liege"],"cbr":["=Club Brugge"],"cer":["Cercle Brugge"],"dyk":["Dynamo Kyiv","Dinamo Kiev","Dynamo Kiev"],"shk":["Shakhtar Donetsk"],"spm":["Spartak Moscow","Spartak Moskova"],"csm":["CSKA Moscow","CSKA Moskova"],"lev":["Levski Sofia","Levski Sofya"],"css":["CSKA Sofia","CSKA Sofya"],"mta":["Maccabi Tel Aviv","Maccabi Rapyd Tel Aviv"],"hta":["Hapoel Tel Aviv","Hapoel IBI Tel Aviv"]},"pairs":[["gs","fb","Kıtalar arası derbi"],["gs","bjk","İstanbul derbisi"],["fb","bjk","İstanbul derbisi"],["gs","ts","Büyük derbi"],["fb","ts","Büyük derbi"],["bjk","ts","Büyük derbi"],["goz","ksk","İzmir derbisi"],["goz","alt","İzmir derbisi"],["alt","ksk","İzmir derbisi"],["bur","esk","Bursa–Eskişehir rekabeti"],["koc","sak","Doğu Marmara derbisi"],["ads","adn","Adana derbisi"],["ank","gnc","Ankara derbisi"],["sam","ts","Karadeniz derbisi"],["fb","efes","İstanbul basket derbisi"],["gs","efes","İstanbul basket derbisi"],["rm","fcb","El Clásico"],["rm","atm","Madrid derbisi"],["fcb","esp","Barcelona derbisi"],["sev","bet","Sevilla derbisi"],["ath","rso","Bask derbisi"],["int","mil","Derby della Madonnina"],["rom","laz","Derby della Capitale"],["juv","tor","Derby della Mole"],["juv","int","Derby d'Italia"],["gen","smp","Derby della Lanterna"],["mu","mc","Manchester derbisi"],["liv","eve","Merseyside derbisi"],["ars","tot","Kuzey Londra derbisi"],["liv","mu","Kuzeybatı derbisi"],["new","sun","Tyne-Wear derbisi"],["cel","ran","Old Firm"],["bay","bvb","Der Klassiker"],["bvb","s04","Revier derbisi"],["hsv","stp","Hamburg derbisi"],["kol","bmg","Ren derbisi"],["psg","om","Le Classique"],["ol","ase","Rhône derbisi"],["aja","fey","De Klassieker"],["aja","psv","Ajax–PSV"],["ben","por","O Clássico"],["ben","scp","Lizbon derbisi"],["por","scp","Clássico"],["oly","pao","Ezeli rakipler derbisi"],["ari","paok","Selanik derbisi"],["boc","riv","Superclásico"],["rac","ind","Avellaneda derbisi"],["fla","flu","Fla-Flu"],["cor","pal","Derby Paulista"],["gre","inr","Gre-Nal"],["cam","cru","Clássico Mineiro"],["nac","pen","Uruguay klasiği"],["col","uch","Şili Superclásico"],["ame","chv","Clásico Nacional"],["ahl","zam","Kahire derbisi"],["par","czv","Ebedi derbi"],["dzg","haj","Ebedi derbi"],["spa","sla","Prag derbisi"],["aus","rap","Viyana derbisi"],["and","std","Belçika klasiği"],["cbr","cer","Brugge derbisi"],["dyk","shk","Ukrayna klasiği"],["spm","csm","Moskova derbisi"],["lev","css","Ebedi derbi"],["mta","hta","Tel Aviv derbisi"]]}/*/DERBI_JSON*/;
  // data/derbi_karne.json yüklenemezse kullanılacak son ölçüm (lab/derbi_karne.py çıktısı)
  let DXK={"n_derbi":495,"n_derbi_olmayan":66136,"favori_kazanma_derbi":0.4606,"favori_kazanma_diger":0.5218,"favori_beklenen_derbi":0.4858,"beraberlik_derbi":0.2889,"beraberlik_diger":0.2611,"surpriz_derbi":0.2505,"surpriz_diger":0.2171,"model_isabet_derbi":0.4606,"model_isabet_diger":0.5211,"favori_beklenen_diger":0.5095,"favori_fark_oran":-0.0252,"favori_fark_z":-1.14,"oranlara_gore_anlamli":false,"az_veri":false,"uyari":"Derbi örneği orta büyüklükte; derbide favori diğer maçlardan daha az kazanıyor, ancak farkın çoğunu oranlar zaten fiyatlıyor (derbiler daha dengeli). Oranların beklentisine göre kalan fark istatistiksel olarak anlamlı değil. Kilitli arşivde (son günler) çok az derbi var; o satır yalnız bilgi amaçlıdır."};
  const WOM_LG=new Set(["wsl","esw","frw","mxw","nlw","ausw","nwsl","ncaaw","wnba"]);
  const WOM_TAG=/^(k|w|wsl|esw|frw|nlw|mxw|ausw|kadin|women|f)$/, NOISE=new Set(["fc","cf","sk","jk","fk","kk","bc","as","ac","afc","sl","rcd","ssc","ss","sv","club"]), DENY=new Set(["sc","cd","ec"]);
  const base=s=>String(s||"").replace(/[İI]/g,"i").toLowerCase().replace(/ı/g,"i").normalize("NFD").replace(/[\u0300-\u036f]/g,"");
  function dxNz(name,lg){ let s=base(name); const v=new Set();
    s=s.replace(/\(([^)]*)\)/g,(_,c)=>{ c=c.replace(/[^a-z0-9]+/g,""); if(WOM_TAG.test(c)){ v.add("k"); return " "; } return c?" @"+c+" ":" "; });
    s=s.replace(/\ba\.s\.?/g," as ").replace(/\bu[\s-]+(1[5-9]|2[0-3])\b/g,"u$1");
    const t=s.replace(/[^a-z0-9@]+/g," ").split(" ").filter(Boolean); let out=[];
    t.forEach((x,i)=>{ if(/^u(1[5-9]|2[0-3])$/.test(x)) v.add(x);
      else if(/^(reserves|reserve|res)$/.test(x)) v.add("res"); else if(/^(academy|akademi|youth|primavera)$/.test(x)) v.add("y");
      else if(/^(women|womens|kadin|femenino|feminino|frauen|dames|ladies|feminine)$/.test(x)) v.add("k");
      else if(/^(castilla|atletic)$/.test(x)&&i>0) v.add("b"); else if(x==="jong"&&i===0) v.add("b"); else out.push(x); });
    while(out.length&&/^(b|ii|k|w|2)$/.test(out[out.length-1])){ const z=out.pop(); v.add(z==="k"||z==="w"?"k":"b"); }
    if(lg&&WOM_LG.has(lg)) v.add("k");
    if(out[0]==="1") out=out.slice(1);
    out=out.filter(x=>!NOISE.has(x));
    return {t:out, v:[...v].sort().join(",")}; }
  const IDX=[]; for(const [k,al] of Object.entries(DERBI_DATA.teams)) for(const a of al){ const ex=a[0]==="="; const z=dxNz(ex?a.slice(1):a); if(z.t.length) IDX.push({k,t:z.t,ex}); }
  const PAIRS=new Map(); for(const [a,b,n] of DERBI_DATA.pairs) PAIRS.set([a,b].sort().join("|"),n);
  function dxTeam(name,lg){ const z=dxNz(name,lg); let best=null;
    for(const e of IDX){ const a=e.t;
      if(e.ex){ if(z.t.length!==a.length||a.some((x,i)=>z.t[i]!==x)) continue; }
      else { if(z.t.length<a.length||a.some((x,i)=>z.t[i]!==x)) continue; if(z.t.slice(a.length).some(x=>x[0]==="@"||DENY.has(x))) continue; }
      if(!best||a.length>best.t.length) best=e; }
    return best?{k:best.k,v:z.v}:null; }
  const CACHE=new Map();
  function derbiOf(h,a,lg){ if(!h||!a) return null; const key=h+"\u0001"+a+"\u0001"+(lg||""); if(CACHE.has(key)) return CACHE.get(key);
    let r=null; try{ const A=dxTeam(h,lg), B=dxTeam(a,lg);
      if(A&&B&&A.k!==B.k){ const n=PAIRS.get([A.k,B.k].sort().join("|"));
        if(n&&A.v===B.v){ const kind=!A.v?"ana":A.v.split(",").includes("k")?"kadin":"genc"; r={n,kind,label:kind==="ana"?"Derbi":kind==="kadin"?"Kadın derbi":"Genç derbi"}; } } }catch(e){}
    if(CACHE.size>4000) CACHE.clear(); CACHE.set(key,r); return r; }
  window.derbiOf=derbiOf; window.DERBI_DATA=DERBI_DATA;
  try{ fetch("data/derbi_karne.json",{cache:"no-cache"}).then(r=>r.ok?r.json():null).then(j=>{ if(j&&j.ozet&&j.ozet.n_derbi) DXK=j.ozet; }).catch(()=>{}); }catch(e){}
  const pc=x=>Math.round(x*100);
  function noteHtml(d,bk){ const K=DXK;
    if(bk) return `⚔️ <b>${esc(d.label)}</b> · ${esc(d.n)}<br>Rekabet maçı: favori her zamanki kadar rahat olmayabilir.<small>Derbi ölçümü (lab/derbi_karne) yalnız futbol maçlarıyla yapıldı; basket derbileri için ayrı istatistik yok. Garanti değildir.</small>`;
    if(d.kind!=="ana") return `⚔️ <b>${esc(d.label)}</b> · ${esc(d.n)}<small>Genç/kadın takımları arasında; ana takım derbisi istatistiği bu maça uygulanmaz.</small>`;
    if(!K||!K.n_derbi) return `⚔️ <b>Derbi</b> · ${esc(d.n)}<br>Derbi: favori bu maçlarda daha sık kaybeder; sürpriz olasılığı normalden yüksek.`;
    const fd=pc(K.favori_kazanma_derbi), fo=pc(K.favori_kazanma_diger), sd=pc(K.surpriz_derbi), so=pc(K.surpriz_diger), bd=pc(K.beraberlik_derbi), bo=pc(K.beraberlik_diger);
    const weaker=K.favori_kazanma_derbi<K.favori_kazanma_diger, upset=K.surpriz_derbi>K.surpriz_diger;
    const lead=weaker&&upset?"favori bu maçlarda daha sık kaybeder; sürpriz olasılığı normalden yüksek."
      :weaker?"favori bu maçlarda daha az kazanır; beraberlik daha sık."
      :"favori derbilerde de diğer maçlar kadar kazanıyor; fark küçük.";
    return `⚔️ <b>Derbi</b> · ${esc(d.n)}<br>${lead.charAt(0).toLocaleUpperCase("tr")+lead.slice(1)}`
      +`<small>Geçmiş ${K.n_derbi} derbi: favori %${fd} kazandı (diğer maçlar %${fo}) · sürpriz %${sd} (%${so}) · beraberlik %${bd} (%${bo}).${K.az_veri?" Örnek küçük.":""} Farkın çoğu orana zaten yansıyor; garanti değildir.</small>`; }
  // ---------- ekranda işaretle ----------
  const clean=el=>{ if(!el) return ""; const c=el.cloneNode(true); c.querySelectorAll(".tvar.d,.lclk,.k70-tag,.note,.pill,img,svg").forEach(x=>x.remove()); return c.textContent.replace(/\s+/g," ").trim(); };
  const split=s=>{ let m=/^(.+?)\s+\d+\s*-\s*\d+\s+(.+)$/.exec(s); if(m) return [m[1],m[2]]; m=/^(.+?)\s+[-–—]\s+(.+)$/.exec(s); return m?[m[1],m[2]]:null; };
  // [satır seçici, ad taşıyıcı, kip]  kip "t" = "A - B" metni, "p" = iki ayrı öğe
  const SPEC=[[".ib-r",".ib-tm","t"],[".rs-r",".ib-tm","t"],[".pw-r",".pw-m>b","t"],[".tp-r",".tp-m>b","t"],[".bt-card",".bt-cm>b","t"],[".cprow",".l>b","t"],
    [".lv-c",".lv-tm>span","p"],[".bk-row",".bk-tm em","p"],[".br",".br-tm em","p"],["#msheet .ms-hd",".ms-t>b","p"],["#bkd .bk-vs",":scope>div>b","p"],[".match",".t","t"]];
  const SEL=SPEC.map(x=>x[0]).join(",");
  function lgOf(row){ try{ const om=row.getAttribute("data-om"); if(om&&typeof OMR!=="undefined"){ const m=OMR.get(om); if(m) return m.lg||null; }
      if(row.classList.contains("ib-r")&&typeof IB!=="undefined"&&IB.rows){ const x=IB.rows[+row.dataset.i]; if(x&&x.m) return x.m.lg; }
      if(row.dataset.ck) return row.dataset.ck.split("|")[0];
      if(row.dataset.cpi!=null&&typeof CP!=="undefined"){ const x=CP.items[+row.dataset.cpi]; if(x) return x.lg; }
      if(row.classList.contains("ms-hd")&&typeof MS!=="undefined"&&MS.m) return MS.m.lg||null;
      if(row.classList.contains("bk-row")&&typeof BK!=="undefined"&&BK.rows){ const f=BK.rows[+row.dataset.i]; if(f) return f.lg; } }catch(e){} return null; }
  function mark(row){ const sp=SPEC.find(s=>row.matches(s[0])); if(!sp) return;
    const hosts=[...row.querySelectorAll(sp[1])]; if(!hosts.length) return;
    const raw=hosts.map(h=>h.textContent).join("\u0001");
    if(row.dataset.dxs===raw&&(!row.classList.contains("dx")||row.querySelector(".tvar.d"))) return;
    let names=null; if(sp[2]==="t") names=split(clean(hosts[0])); else if(hosts.length>=2) names=[clean(hosts[0]),clean(hosts[1])];

    const d=names?derbiOf(names[0],names[1],lgOf(row)):null;
    row.classList.toggle("dx",!!d); row.classList.toggle("dx-g",!!d&&d.kind==="genc"); row.classList.toggle("dx-k",!!d&&d.kind==="kadin");
    row.querySelectorAll(".tvar.d").forEach(x=>x.remove());
    if(!d){ row.removeAttribute("data-dx"); row.dataset.dxs=raw; return; }
    row.setAttribute("data-dx",d.n);
    const b=document.createElement("span"); b.className="tvar d"; b.textContent=d.label; b.title=d.n;
    if(row.classList.contains("ms-hd")){ const w=row.querySelector(".ms-when"); if(w){ w.appendChild(document.createTextNode(" ")); w.appendChild(b); } }
    else if(row.matches("#bkd .bk-vs")){ const mid=row.querySelector(".mid"); (mid||hosts[0]).appendChild(document.createElement("br")); (mid||hosts[0]).appendChild(b); }
    else { const h=hosts[0], nx=row.matches(".cprow")?row.querySelector(".l>small"):h.nextElementSibling;
      if(row.matches(".cprow,.pw-r,.tp-r,.bt-card")&&nx&&nx.tagName==="SMALL"){ nx.prepend(b,document.createTextNode(" ")); }
      else if(row.matches(".ib-r,.rs-r,.bk-row,.br")) h.after(b);
      else h.appendChild(b); }
    // maç penceresi notu
    const box=row.matches("#msheet .ms-hd")?$("msheet"):row.matches("#bkd .bk-vs")?row.closest(".panel"):null;
    if(box&&!box.querySelector(".dx-note")){ const n=document.createElement("div"); n.className="dx-note"; n.innerHTML=noteHtml(d,row.matches("#bkd .bk-vs"));
      if(row.classList.contains("ms-hd")) row.after(n); else box.appendChild(n); }
    row.dataset.dxs=hosts.map(h=>h.textContent).join("\u0001"); }
  function scan(){ try{ document.querySelectorAll(SEL).forEach(mark); }catch(e){} }
  let q=0; const sched=()=>{ if(q) return; q=1; setTimeout(()=>requestAnimationFrame(()=>{ q=0; scan(); }),60); };
  try{ new MutationObserver(sched).observe(document.body,{childList:true,subtree:true}); }catch(e){} sched();
  // ---------- OXXai: "derbi var mı", "bugün derbi", "derbiler" ----------
  const NZ=t=>String(t||"").toLocaleLowerCase("tr").replace(/ç/g,"c").replace(/ğ/g,"g").replace(/ı/g,"i").replace(/ö/g,"o").replace(/ş/g,"s").replace(/ü/g,"u").replace(/[^a-z0-9 ]/g," ").replace(/\s+/g," ").trim();
  try{ ["derbi","derbisi","derbiler","derbileri","derbide","derby","derbiyi"].forEach(w=>NLU_STOP.add(w)); }catch(e){}
  const DXQ=/\b(derbi\w*|derby)\b/, ANQ=/\b(ne olur|kim kazan\w*|kazanir\w*|kazanacak|skor\w*|analiz\w*|kac kac|kg|ust|alt|ilk yari\w*|iy|yorum\w*|tahmin\w*|biter|olur mu|favori\w*|oran\w*)\b/;
  const BKX=[];
  function derbiList(){ const now=Date.now(), d0=istDay(new Date()), d1=istDay(new Date(now+864e5)), out=[], seen=new Set();
    let pool=[]; try{ pool=omPool(); }catch(e){}
    for(const m of pool){ const dt=m.dt?m.dt:new Date(m.ts); if(!dt||isNaN(dt)) continue; const day=istDay(dt), live=!!(m.sp||m.live);
      if(!live&&(day!==d0&&day!==d1||dt.getTime()<now-2.5*3600e3)) continue;
      const d=derbiOf(m.h,m.a,m.lg); if(!d) continue; const k=(m.sp===2?"b":"f")+NZ(m.h)+"|"+NZ(m.a); if(seen.has(k)) continue; seen.add(k);
      out.push({m,d,dt,day,live,bk:m.sp===2}); }
    try{ for(const f of bkList()){ const day=istDay(f.t); if(day!==d0&&day!==d1) continue; const lv=bkLiveOf(f); if(lv&&lv.state==="post") continue;
      const d=derbiOf(f.h,f.a,f.lg); if(!d) continue; const k="b"+NZ(f.h)+"|"+NZ(f.a); if(seen.has(k)) continue; seen.add(k);
      out.push({f,m:f,d,dt:f.t,day,live:!!(lv&&lv.state==="in"),bk:true,lv}); } }catch(e){}
    return out.sort((x,y)=>(y.live-x.live)||(x.dt-y.dt)); }
  function line(x,d0){ const m=x.m, when=x.live?`<em style="color:#FF5A5A;font-style:normal">● ${esc(String(m.hs??(x.lv&&x.lv.hs)??0))}-${esc(String(m.as??(x.lv&&x.lv.as)??0))}</em>`:esc((x.day===d0?"":"Yarın ")+ist(x.dt,{hour:"2-digit",minute:"2-digit"}));
    let attr=""; if(x.f){ BKX.push(x.f); attr=` data-dxbk="${BKX.length-1}"`; } else { try{ attr=omA(m); }catch(e){} }
    const lgn=x.bk?"🏀 "+(m.comp||(typeof bkLg==="function"?bkLg(m.lg):"")||"Basketbol"):((m.comp)||(LEAGUES[m.lg]||{n:""}).n||"");
    return `<div class="dx-li"${attr}><span class="dx-t">${when}</span><span class="dx-m"><b>${esc(m.h)} – ${esc(m.a)}</b><small>${esc(x.d.n)}${x.d.kind!=="ana"?" · "+esc(x.d.label):""}${lgn?" · "+esc(lgn):""}</small></span></div>`; }
  document.addEventListener("click",e=>{ const r=e.target.closest(".dx-li[data-dxbk]"); if(!r) return; const f=BKX[+r.dataset.dxbk]; if(f){ try{ buzz(8); }catch(_){} try{ if($("botSheet")&&!$("botSheet").hidden&&typeof botThen==="function") botThen(()=>bkOpen(f)); else bkOpen(f); }catch(_){} } });
  function answer(raw){ const n=" "+NZ(raw)+" "; if(!DXQ.test(n)||ANQ.test(n)) return null;
    // takım adı geçiyorsa (ör. "galatasaray derbisi") eski analiz yolu çalışsın
    try{ const tw=n.trim().split(" ").filter(w=>w.length>=4&&!DXQ.test(w)&&!/^(bugun|yarin|aksam|hangi|neler|maclari?|maclar|varmi|bugunku|yarinki|listele|goster)$/.test(w));
      if(tw.length&&IDX.some(e=>e.t.some(t=>t.length>=4&&tw.some(w=>w.startsWith(t)||t.startsWith(w))))) return null; }catch(e){}
    const L=derbiList(), d0=istDay(new Date()), wantT=/\byarin\w*\b/.test(n)&&!/\bbugun\w*\b/.test(n), wantB=/\bbugun\w*\b/.test(n)&&!/\byarin\w*\b/.test(n);
    const S=L.filter(x=>wantT?x.day!==d0&&!x.live:wantB?(x.day===d0||x.live):true), K=DXK;
    const stat=K&&K.n_derbi?`<small>📊 Geçmiş ${K.n_derbi} derbide favori %${pc(K.favori_kazanma_derbi)} kazandı (diğer maçlarda %${pc(K.favori_kazanma_diger)}); sürpriz olasılığı derbide daha yüksek. Garanti değildir.</small>`:"";
    const when=wantT?"Yarın":wantB?"Bugün":"Bugün ve yarın";
    if(!S.length) return {html:`⚔️ ${when} bültende derbi yok${botName()}. ${L.length&&!wantT?"Yarın "+L.filter(x=>x.day!==d0).length+" derbi var.":""}<br><small>Tanıdığım derbiler: Galatasaray–Fenerbahçe, El Clásico, Manchester, Milano, Old Firm, Superclásico gibi ${PAIRS.size} eşleşme; genç/kadın takımları ayrı sayılır.</small>`,chips:["Bugün hangi maçlar var","En güvenli 3 maç"]};
    const h=`⚔️ ${when} <b>${S.length} derbi</b> var${botName()}:`+S.slice(0,8).map(x=>line(x,d0)).join("")+(S.length>8?`<small>+${S.length-8} derbi daha (bültende turuncu şeritle işaretli)</small><br>`:"")+stat;
    const f=S.find(x=>!x.bk&&x.d.kind==="ana")||S[0];
    return {html:h,chips:[`${f.m.h} ${f.m.a} ne olur`,"Bugün hangi maçlar var","En güvenli 3 maç"]}; }
  // "derbi ne olur" / "derbide kim kazanır": takım adı yoksa sıradaki ANA derbiyi (genç/kadın değil) analiz et.
  // Öncelik Türk büyükleri (GS/FB/BJK/TS), sonra canlı, sonra en yakın saat; 8 gün içinde.
  const BIG4=new Set(["gs","fb","bjk","ts"]);
  function nextDerbi(){ const now=Date.now(); let pool=[]; try{ pool=omPool(); }catch(e){}
    const L=[]; for(const m of pool){ if(m.sp===2) continue; const dt=m.dt?m.dt:new Date(m.ts); if(!dt||isNaN(dt)) continue; const live=!!(m.sp||m.live);
      if(!live&&(dt.getTime()<now-2*3600e3||dt.getTime()>now+8*864e5)) continue; const d=derbiOf(m.h,m.a,m.lg); if(!d||d.kind!=="ana") continue;
      const A=dxTeam(m.h,m.lg), B=dxTeam(m.a,m.lg); L.push({m,dt,live,big:!!(A&&B&&BIG4.has(A.k)&&BIG4.has(B.k))}); }
    L.sort((x,y)=>(y.big-x.big)||(y.live-x.live)||(x.dt-y.dt)); return L[0]||null; }
  function rewrite(raw){ const n=" "+NZ(raw)+" "; if(!DXQ.test(n)||!ANQ.test(n)) return null;
    try{ const tw=n.trim().split(" ").filter(w=>w.length>=4&&!DXQ.test(w)); if(tw.length&&IDX.some(e=>e.t.some(t=>t.length>=4&&tw.some(w=>w.startsWith(t)||t.startsWith(w))))) return null; }catch(e){}
    const x=nextDerbi(); if(!x) return null;
    return `${x.m.h} ${x.m.a} `+n.replace(/\b(derbi\w*|derby)\b/g," ").replace(/\s+/g," ").trim(); }
  window.derbiAnswer=answer;
  if(typeof botAnswer==="function"){ const _ba=botAnswer; botAnswer=async function(raw){ try{ const r=answer(raw); if(r) return r; }catch(e){}
      try{ const q=rewrite(raw); if(q){ const args=[...arguments]; args[0]=q; return _ba.apply(this,args); } }catch(e){}
      return _ba.apply(this,arguments); }; }
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: derbi-v95 */
/* id: kuponum-v95 */ try {
// =====================================================================
// v95 · KUPONUM — sınırsız kupon (Kuponum 1, 2, 3… ya da kendi adın), altın aslan kimliği
// • Veri: localStorage "bx-kuponlar" = [{id,ad,items,olusturma,durum:"acik"|"bitti"|"arsiv",upd,bitti,arsivAt}] + "bx-kupon-aktif"
//   CP.items artık AKTİF kuponun items dizisidir (getter/setter) → cpToggle, pwAdd, OXXai "bunu ekle/hepsini ekle", bülten hücreleri
//   ve maç sayfası hiç değişmeden aktif kupona yazar. cpSave aktif kuponu da kaydeder; eski "bx-coupon" anahtarı yazılmaya devam eder.
// • Geriye uyum: ilk açılışta mevcut "bx-coupon" içeriği "Kuponum 1"e taşınır.
// • Sonuç: OYN'un kullandığı RS.load (iddaa sonuç servisi, gün önbellekli) yeniden kullanılır; oynGrade bitince aynı önbellekten
//   kupon maçları puanlanır (yeni ağ isteği yok). Basket maçları BK canlı verisinden. Tüm maçları biten kupon "Eski KUPO'larım"a geçer.
// • Bilgi mimarisi: Kuponum ekranı = Kuponlarım · Eski KUPO'larım · Takip (eski "Sonuç takibim"; içinde "Kayıtlı tahminler" bağlantısı)
// • Maç satırları (bülten, canlı, ligler fikstürü, basket, maç sayfası): "＋ Kupon / ✓ KUPO'da"; basılı tut → "Hangi KUPO'ya?"
// =====================================================================
(function(){
  const LSK="bx-kuponlar", LSA="bx-kupon-aktif", NOW=()=>Date.now();
  const uid=()=>Date.now().toString(36)+Math.random().toString(36).slice(2,6);
  const KX=window.KX={L:[],aktif:null};
  const pct=p=>p==null||isNaN(p)?"–":p<.1&&p>0?(p*100).toLocaleString("tr-TR",{maximumFractionDigits:1}):String(Math.round(p*100));
  const f2=x=>(+x||0).toLocaleString("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2});
  const f1=x=>(+x||0).toLocaleString("tr-TR",{maximumFractionDigits:1});
  const tms=d=>{ const t=Date.parse(d instanceof Date?d.toISOString():d); return isNaN(t)?0:t; };
  // ---------- altın aslan (özgün, geometrik): 16 köşeli faset yele + koyu kalkan yüz + altın çizgi hatlar ----------
  let LN=0;
  // yele: yanlarda geniş, altta sakal ucuna inen, tutam tutam (dönüşümlü uzun/kısa) faset çokgen — güneş değil, aslan silueti
  function mane(cx,cy,R0,r0,n,rot,k){ const P=[]; for(let i=0;i<n*2;i++){ const a=rot+i*Math.PI/n, sd=Math.pow(Math.sin(a),2), bt=Math.pow(Math.max(0,-Math.cos(a)),3);
      const tuft=(i%4===0?1.6:i%4===2?-0.4:0)*k; const q=i%2?r0+sd*2.2+bt*3:R0+sd*3+bt*5.5+tuft; P.push((cx+q*Math.sin(a)).toFixed(2)+","+(cy-q*Math.cos(a)).toFixed(2)); } return P.join(" "); }
  const MANE=mane(32,32.5,24.5,19,14,0,1), MANE2=mane(32,32.5,20.5,16.5,14,Math.PI/14,.6);
  function lion(cls){ const u="kxl"+(++LN);   // v99: KUPO kimliği — özgün geometrik altın kupa (fonksiyon adı geriye uyum için aynı)
    return `<svg class="kx-lion kx-cup ${cls||""}" viewBox="0 0 64 64" aria-hidden="true" focusable="false"><defs>
<linearGradient id="${u}a" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFF6D0"/><stop offset=".35" stop-color="#F0CF6A"/><stop offset=".7" stop-color="#C9962A"/><stop offset="1" stop-color="#8A6118"/></linearGradient>
<linearGradient id="${u}b" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#9C7220"/><stop offset=".45" stop-color="#FFE9A0"/><stop offset=".6" stop-color="#F3D47A"/><stop offset="1" stop-color="#A57A22"/></linearGradient>
<linearGradient id="${u}d" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3A2C10"/><stop offset="1" stop-color="#120D05"/></linearGradient>
<radialGradient id="${u}g" cx=".5" cy=".35" r=".6"><stop offset="0" stop-color="#FFE7A0" stop-opacity=".55"/><stop offset="1" stop-color="#FFE7A0" stop-opacity="0"/></radialGradient></defs>
<circle cx="32" cy="27" r="24" style="fill:url(#${u}g)"/>
<path d="M19.5 15.5H12.6C12.6 24.5 16 29.6 22.6 30.6" style="fill:none;stroke:url(#${u}a);stroke-width:2.6;stroke-linecap:round;stroke-linejoin:round"/>
<path d="M44.5 15.5H51.4C51.4 24.5 48 29.6 41.4 30.6" style="fill:none;stroke:url(#${u}a);stroke-width:2.6;stroke-linecap:round;stroke-linejoin:round"/>
<path d="M18.6 11.6H45.4V20.5C45.4 30.4 39.6 37.4 32 37.4S18.6 30.4 18.6 20.5Z" style="fill:url(#${u}b)"/>
<path d="M18.6 11.6H45.4" style="stroke:#FFF3C4;stroke-width:1.4;stroke-linecap:round;opacity:.9"/>
<path d="M24.2 15.8V21.4C24.2 26.6 26.6 30.6 30 32.4" style="fill:none;stroke:#FFF6D8;stroke-width:1.6;stroke-linecap:round;opacity:.7"/>
<path d="M32 17.6 33.6 21 37.3 21.4 34.5 23.8 35.3 27.4 32 25.6 28.7 27.4 29.5 23.8 26.7 21.4 30.4 21Z" style="fill:url(#${u}d);opacity:.82"/>
<path d="M29.4 37.2H34.6L35.6 44.2H28.4Z" style="fill:url(#${u}a)"/>
<path d="M23.4 44.2H40.6L42.6 49.6H21.4Z" style="fill:url(#${u}b)"/>
<rect x="19.4" y="49.6" width="25.2" height="4.8" rx="1.6" style="fill:url(#${u}d);stroke:url(#${u}a);stroke-width:1.1"/>
<path d="M27.6 52H36.4" style="stroke:url(#${u}a);stroke-width:1.2;stroke-linecap:round"/></svg>`; }
  window.kxLion=lion;
  const IC={
    pen:`<svg viewBox="0 0 24 24"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/></svg>`,
    share:`<svg viewBox="0 0 24 24"><path d="M12 3v12M8 7l4-4 4 4"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg>`,
    copy:`<svg viewBox="0 0 24 24"><rect x="8" y="8" width="12" height="12" rx="2.5"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></svg>`,
    arch:`<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="5" rx="1.5"/><path d="M5 9v9a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9M10 13h4"/></svg>`,
    del:`<svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg>`,
    back:`<svg viewBox="0 0 24 24"><path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/></svg>`};
  // ---------- Türkçe ekler (yönelme / ayrılma) ----------
  function sfx(s,abl){ s=String(s||"").trim(); const m=/(\d+)$/.exec(s);
    if(!m) return `“${s}” KUPO'${abl?"sundan":"suna"}`;
    const n=+m[1]; const D=abl?{1:"den",2:"den",3:"ten",4:"ten",5:"ten",6:"dan",7:"den",8:"den",9:"dan"}:{1:"e",2:"ye",3:"e",4:"e",5:"e",6:"ya",7:"ye",8:"e",9:"a"};
    const T=abl?{1:"dan",2:"den",3:"dan",4:"tan",5:"den",6:"tan",7:"ten",8:"den",9:"dan"}:{1:"a",2:"ye",3:"a",4:"a",5:"ye",6:"a",7:"e",8:"e",9:"a"};
    const x=n===0?(abl?"dan":"a"):n%10?D[n%10]:n%100?T[Math.floor(n/10)%10]:(abl?"den":"e"); return s+"'"+x; }
  window.kxSfx=sfx;
  function acc(n){ n=Math.round(+n)||0; const L={1:"i",2:"si",3:"ü",4:"ü",5:"i",6:"sı",7:"si",8:"i",9:"u"}, T={1:"u",2:"si",3:"u",4:"ı",5:"si",6:"ı",7:"i",8:"i",9:"ı"};
    return n+"'"+(n===0?"ı":n%10?L[n%10]:n%100?T[Math.floor(n/10)%10]:n%1000?"ü":"i"); }
  const accP=p=>"%"+acc(Math.round((p||0)*100));
  // ---------- depo ----------
  // İki sekme güvenliği: yazmadan önce diskteki listeyle id'ye göre birleştir (yeni olan kazanır); bu sekmede silinenler geri gelmez
  const DEL=(()=>{ try{ return new Set(JSON.parse(localStorage.getItem("bx-kuponlar-sil")||"[]")); }catch(e){ return new Set(); } })();
  const ts=c=>c.upd||c.bitti||c.arsivAt||c.olusturma||0;
  function saveL(){ try{
      let D=null; try{ D=JSON.parse(localStorage.getItem(LSK)||"null"); }catch(e){}
      try{ const ds=JSON.parse(localStorage.getItem("bx-kuponlar-sil")||"[]"); if(Array.isArray(ds)) ds.forEach(x=>DEL.add(x)); }catch(e){}
      if(Array.isArray(D)){ const M=new Map(KX.L.map(c=>[c.id,c]));
        for(const d of D){ if(!d||!d.id||!Array.isArray(d.items)||DEL.has(d.id)) continue; const m=M.get(d.id);
          if(!m){ d.items=d.items.filter(x=>x&&x.h&&x.a); atFix(d); KX.L.push(d); } else if(ts(d)>ts(m)){ Object.assign(m,d); m.items=d.items.filter(x=>x&&x.h&&x.a); atFix(m); } } }
      KX.L=KX.L.filter(c=>!DEL.has(c.id));
      // sınır: arşiv/biten kuponlardan en eski olanlar 300'ü aşarsa düşer (açık kuponlara dokunulmaz)
      const P=KX.L.filter(c=>c.durum!=="acik").sort((a,b)=>ts(b)-ts(a)); if(P.length>300){ const drop=new Set(P.slice(300).map(c=>c.id)); KX.L=KX.L.filter(c=>!drop.has(c.id)); }
      localStorage.setItem(LSK,JSON.stringify(KX.L)); localStorage.setItem(LSA,KX.aktif||"");
      localStorage.setItem("bx-kuponlar-sil",JSON.stringify([...DEL].slice(-500)));
    }catch(e){} }
  function kxDel(id){ DEL.add(id); KX.L=KX.L.filter(z=>z.id!==id); }
  // at kuponu satırları (v98): bozuk/eksik satır yüklemede düşer; spor:"at" olup at dizisi yoksa [] sayılır
  const AT_TUR=new Set(["ganyan","plase","ikili","sirali_ikili","cifte","uclu","tabela","altili"]);
  function atFix(c){ if(c&&c.spor==="at") c.at=(Array.isArray(c.at)?c.at:[]).filter(x=>x&&AT_TUR.has(x.tur)&&Array.isArray(x.kid)&&x.kid.length&&Array.isArray(x.sec)&&x.sec.every(Array.isArray)); }
  function nextNo(){ let mx=0; for(const c of KX.L){ const m=/^(?:Kupon(?:um)?|KUPO) (\d+)$/.exec(c.ad||""); if(m) mx=Math.max(mx,+m[1]); } return Math.max(mx,0)+1; }
  function kxNew(ad,items){ const c={id:uid(),ad:ad||("KUPO "+nextNo()),items:items||[],olusturma:NOW(),durum:"acik"}; KX.L.push(c); return c; }
  // KUPO: uygulamanın verdiği eski varsayılan adlar ("Kupon 3", "Kuponum 2", "At Kuponu 1") yeni adla gösterilir; kullanıcının kendi verdiği adlar korunur
  function kupoAd(a){ const s=String(a==null?"":a); let m=/^Kupon(?:um)? (\d+)$/.exec(s); if(m) return "KUPO "+m[1]; m=/^At Kuponu (\d+)$/.exec(s); if(m) return "At KUPO'su "+m[1]; return a; }
  function load(){ let L=null, raw=null; try{ raw=localStorage.getItem(LSK); L=JSON.parse(raw||"null"); }catch(e){}
    if(raw&&!Array.isArray(L)){ try{ localStorage.setItem("bx-kuponlar-bozuk",raw); }catch(e){} }   // bozuk kayıt silinmeden önce yedeklenir
    if(!Array.isArray(L)){ let old=[]; try{ old=JSON.parse(localStorage.getItem("bx-coupon")||"[]"); }catch(e){} if(!Array.isArray(old)) old=[];
      KX.L=[]; const c=kxNew("KUPO 1",old.filter(x=>x&&x.h&&x.a)); c.tasindi=old.length?1:0; KX.aktif=c.id; saveL(); }
    else { KX.L=L.filter(c=>c&&c.id&&Array.isArray(c.items)&&!DEL.has(c.id)); KX.L.forEach(c=>{ c.items=c.items.filter(x=>x&&x.h&&x.a); atFix(c); c.ad=kupoAd(c.ad); }); try{ KX.aktif=localStorage.getItem(LSA)||null; }catch(e){} } }
  function act(){ let c=null; for(const x of KX.L) if(x.id===KX.aktif){ c=x; break; }
    if(!c||c.durum!=="acik"){ c=KX.L.filter(x=>x.durum==="acik").sort((a,b)=>(b.upd||b.olusturma)-(a.upd||a.olusturma))[0]||kxNew(); KX.aktif=c.id; saveL(); }
    return c; }
  const byId=id=>KX.L.find(c=>c.id===id);
  const open=()=>KX.L.filter(c=>c.durum==="acik").sort((a,b)=>a.olusturma-b.olusturma);
  const past=()=>KX.L.filter(c=>c.durum!=="acik").sort((a,b)=>(b.bitti||b.arsivAt||b.olusturma)-(a.bitti||a.arsivAt||a.olusturma));
  load(); act();
  Object.defineProperty(CP,"items",{configurable:true,enumerable:true,get(){ return act().items; },set(v){ act().items=Array.isArray(v)?v:[]; }});
  window.kxAct=act; window.kxSave=saveL;
  function kxSetActive(id){ const c=byId(id); if(!c||c.durum!=="acik") return; KX.aktif=id; saveL(); try{ localStorage.setItem("bx-coupon",JSON.stringify(c.items)); }catch(e){} try{ paintCoupon(); }catch(e){} }
  // ---------- hesaplar ----------
  const kOdd=c=>c.items.reduce((a,x)=>a*(+x.odd||1),1), kP=c=>c.items.reduce((a,x)=>a*(x.p||.5),1);
  const done=i=>i.ok!=null||!!i.need;
  function kxSt(c){ const I=c.items; if(!I.length) return "e"; if(I.some(i=>i.ok===false)) return "x"; if(I.every(i=>i.ok===true)) return "g"; if(I.every(done)) return "q"; return "w"; }
  const ST={e:"Boş",w:"Bekliyor",g:"Tuttu",x:"Tutmadı",q:"Sonuç eksik"};
  const stPill=c=>{ const s=kxSt(c); return `<span class="kx-st ${s}">${s==="g"?"✓ ":s==="x"?"✗ ":""}${ST[s]}</span>`; };
  function rating(p,odd){ const ev=p*odd; return ev>=1.05?["Değerli görünüyor","g"]:ev>=.92?["Adil","m"]:["Oran olasılığa göre düşük","x"]; }
  window.kxSt=kxSt;
  // ---------- sonuçlar: OYN ile aynı kaynak (RS.load gün önbelleği) ----------
  let gBusy=false;
  async function kxGrade(){ if(gBusy) return; gBusy=true; let ch=0; const sH=[], sM=[];   // v121: yeni tutan / tutmayan bacaklar (ses)
    try{ const t=NOW(), due=[];
      for(const c of KX.L) for(const it of c.items) if(it.ok==null&&!it.man&&!it.need&&t-tms(it.dt)>100*60e3) due.push(it);
      for(const it of due.filter(i=>i.sp==="bk")){ try{ const f=(BK.data&&BK.data.fixtures||[]).find(x=>x.h===it.h&&x.a===it.a); const lv=f&&bkLiveOf(f);
          if(lv&&lv.state==="post"&&lv.hs!=null){ it.s=`${lv.hs}-${lv.as}`; const ok=mkHit(it.mk,+lv.hs,+lv.as,null,null,null); if(ok!=null){ it.ok=ok; ch++; (ok?sH:sM).push(it); } }
          else if(t-tms(it.dt)>30*3600e3){ it.need=1; ch++; } }catch(e){} }
      const fb=due.filter(i=>i.sp!=="bk"), days=[...new Set(fb.map(it=>istDay(new Date(tms(it.dt)))))].slice(0,8);
      for(const d of days){ let R=null; try{ R=await RS.load(d); }catch(e){} if(!R||!R.list) continue;
        for(const it of fb){ if(istDay(new Date(tms(it.dt)))!==d) continue;
          const m=(it.iid&&R.list.find(x=>x.id===it.iid))||R.list.find(x=>tmEq(x.h,it.h)&&tmEq(x.a,it.a));
          if(!m){ if(t-tms(it.dt)>30*3600e3){ it.need=1; ch++; } continue; }
          it.s=`${m.hs}-${m.as}`; it.s1=m.h1!=null?`${m.h1}-${m.a1}`:null; it.at=t;
          const ok=mkHit(it.mk,m.hs,m.as,m.h1,m.a1,it.s0); if(ok!=null){ it.ok=ok; (ok?sH:sM).push(it); } else it.need=1; ch++; } }
    }catch(e){}
    gBusy=false; if(ch){ const nf=settle(); saveL(); kxRefresh();
      if(!nf&&sH.length){ const x=sH[sH.length-1]; try{ toast(`✓ KUPO'nda ${sH.length>1?sH.length+" maç":esc(x.h)+" – "+esc(x.a)} tuttu`); }catch(e){} try{ Sound.olay&&Sound.olay(sH.some(i=>i.sp==="bk")?"bkTuttu":"bacak"); }catch(e){} } }
    return ch; }
  window.kxGrade=kxGrade;
  function settle(){ const fin=[];
    for(const c of KX.L){ if(c.durum!=="acik"||!c.items.length||!c.items.every(done)) continue; c.durum="bitti"; c.bitti=NOW(); fin.push(c); }
    if(!fin.length) return 0; act();
    const c=fin[0], s=kxSt(c), h=c.items.filter(i=>i.ok).length;
    try{ toast(fin.length>1?`🏆 ${fin.length} KUPO'n sonuçlandı · Eski KUPO'larım`:`🏆 ${c.ad} sonuçlandı: ${ST[s]} (${h}/${c.items.length}) · Eski KUPO'larım`);
      if(Sound.olay){ const w=fin.some(x=>kxSt(x)==="g"); if(w||s==="x") Sound.olay(w?"kupoTuttu":"tutmadi"); } else Sound.toggle(s==="g"); }catch(e){}
    return fin.length; }
  try{ const _og=oynGrade; oynGrade=async function(){ let r; try{ r=await _og.apply(this,arguments); }finally{ kxGrade(); } return r; }; }catch(e){}
  setTimeout(kxGrade,5000);
  // ---------- pazar seçenekleri + OXXai önerisi ----------
  function optsFor(m){ if(!m) return null;
    try{ if(m.sp===1){ const P=idlPred(m), K=idlPick(m,P); if(!K) return null; const mm={lg:"i"+m.ci,h:m.h,a:m.a,dt:new Date(m.ts)};
        const lc=v=>{ try{ return typeof liveCal==="function"?Math.min(.99,liveCal(v).p):v; }catch(e){ return v; } };
        const fx=x=>({k:(x.k==="U"||x.k==="A")?x.k+String(P.line):x.k,n:x.n,o:x.o||null,p:lc(x.p)});
        return {mm,ex:{live:1,s0:`${m.hs}-${m.as}`,iid:m.id},opts:K.all.concat(K.ext||[]).filter(x=>x.p>0).map(fx),rec:fx(K.best)}; } }catch(e){ return null; }
    if(m.sp) return null;
    if(m.bk) return bkOpts(m.bk);
    try{ const t0=tms(m.dt); if(m.live||(t0&&t0<NOW()-5*60e3&&t0>NOW()-150*60e3)){ const lv=(typeof IDL!=="undefined"&&IDL.live&&IDL.live[1]||[]).find(x=>tmEq(x.h,m.h)&&tmEq(x.a,m.a));
        if(lv) return optsFor(lv); } }catch(e){}
    const qf=window.QP_FORCE; window.QP_FORCE=true;
    try{ const f=m.src==="fx"?FIXTURES.find(x=>x.lg===m.lg&&x.h===m.h&&x.a===m.a):fxOdds(m); const p=quickPred(m,f); if(!p) return null;
      const pq=p.pm?{H:p.pm[0],D:p.pm[1],A:p.pm[2],o25:p.o25m!=null?p.o25m:p.o25}:{H:p.p[0],D:p.p[1],A:p.p[2],o25:p.o25};
      const o=f&&f.odds, ou=f&&f.ou;
      const opts=[{k:"1",n:"MS 1",p:pq.H,o:o&&o[0]},{k:"X",n:"MS X",p:pq.D,o:o&&o[1]},{k:"2",n:"MS 2",p:pq.A,o:o&&o[2]},{k:"A",n:"2,5 Alt",p:1-pq.o25,o:ou&&ou[1]},{k:"U",n:"2,5 Üst",p:pq.o25,o:ou&&ou[0]}]
        .filter(x=>x.p!=null&&!isNaN(x.p)).map(x=>Object.assign(x,{o:x.o?+x.o:null}));
      const R=recOf(pq,f); const rec=R?{k:R.k,n:R.n,o:R.o?+R.o:null,p:R.cp}:opts.slice().sort((a,b)=>b.p-a.p)[0];
      return {mm:m,ex:{iid:m.iid||(f&&f.iid)||null},opts,rec};
    }catch(e){ return null; } finally{ window.QP_FORCE=qf; } }
  function bkOpts(f){ try{ const p=bkPredict(f); if(!p) return null; const io=f.io||[];
      const mm={lg:"bk-"+f.lg,h:f.h,a:f.a,dt:new Date(f.dt||f.t)};
      const opts=[{k:"1",n:"MS 1",p:p.pH,o:io[0]?+io[0]:null},{k:"2",n:"MS 2",p:p.pA,o:io[1]?+io[1]:null}];
      return {mm,ex:{sp:"bk"},opts,rec:opts.slice().sort((a,b)=>b.p-a.p)[0]}; }catch(e){ return null; } }
  function matchOfItem(it){ if(it.sp==="bk"){ const f=(BK.data&&BK.data.fixtures||[]).find(x=>x.h===it.h&&x.a===it.a); return f?{bk:f}:null; }
    try{ return findMatchByTeams(it.h,it.a); }catch(e){ return null; } }
  // ---------- ekle / çıkar ----------
  const inAct=(h,a,k)=>CP.items.find(c=>(k&&c.k===k)||(tmEq(c.h,h)&&tmEq(c.a,a)));
  function kxAdd(O,opt,quiet){ if(!O||!opt) return false; const mm=O.mm, ex=O.ex||{}, t=tms(mm.dt), c=act();
    if(!ex.live&&t&&t<NOW()-5*60e3){ toast(t<NOW()-110*60e3?"Bu maç bitmiş; KUPO'ya eklenemez":"Bu maç başladı; maç öncesi tahmini KUPO'ya eklenemez"); return false; }
    const I=CP.items, k=cpKey(mm);
    // v133: canlı seçim → canlı cpToggle yolu (aynı maça ek canlı tahmin; ekleme/çıkarma bildirimini o verir)
    if(ex.live){ const odd=opt.o?+opt.o:+(1/Math.max(.02,opt.p||.5)).toFixed(2), nz=v=>{ v=String(v); return v==="U"||v==="A"?v+"2.5":v; };
      cpToggle(mm,opt.k,odd,opt.p); kxPaint(); return CP.items.some(x=>x.live&&tmEq(x.h,mm.h)&&tmEq(x.a,mm.a)&&nz(x.mk)===nz(opt.k)); }
    const dup=I.findIndex(x=>x.k!==k&&!x.live&&tmEq(x.h,mm.h)&&tmEq(x.a,mm.a)); let repl=dup>=0; if(dup>=0) I.splice(dup,1);
    const had=I.find(x=>x.k===k); if(had&&had.mk!==opt.k) repl=true;
    const odd=opt.o?+opt.o:+(1/Math.max(.02,opt.p||.5)).toFixed(2);
    cpToggle(mm,opt.k,odd,opt.p);
    const it=CP.items.find(x=>x.k===k);
    if(it){ if(ex.sp) it.sp=ex.sp; if(ex.live){ it.live=1; it.s0=ex.s0; } if(ex.iid) it.iid=ex.iid; if(!opt.o) it.fair=1; cpSave(); }
    if(!quiet){ const n=CP.items.length;
      if(!it) toast(`${sfx(c.ad,1)} çıkarıldı · ${n} maç`);
      else if(repl) toast(`Aynı maçtan tek seçim: ${mkName(opt.k)} olarak güncellendi · ${sfx(c.ad)} ${n} maç`);
      else toast(`${sfx(c.ad)} eklendi · ${n} maç${!ex.live&&t&&t<NOW()?" · maç başladı, maç öncesi oranla":""}`); }
    kxPaint(); return !!it; }
  function kxRemoveMatch(h,a){ const I=CP.items, i=I.findIndex(x=>tmEq(x.h,h)&&tmEq(x.a,a)); if(i<0) return false; I.splice(i,1); cpSave(); toast(`${sfx(act().ad,1)} çıkarıldı · ${I.length} maç`); try{ Sound.olay?Sound.olay("kupoCikar"):Sound.toggle(false); }catch(e){} kxPaint(); return true; }
  window.kxAdd=kxAdd;
  // ---------- maç satırlarına ＋ Kupon ----------
  function ctxOf(el){ const r=el.closest("[data-kxr]"); if(!r) return null; const kind=r.dataset.kxr;
    try{ if(kind==="ib"){ const x=IB.rows[+r.dataset.i]; return x?optsFor(x.m):null; }
      if(kind==="lv"){ const id=+r.dataset.id; const m=(IDL.byId[1]||{})[id]; return m?optsFor(m):null; }
      if(kind==="bk"){ const f=BK.rows&&BK.rows[+r.dataset.i]; if(f) return bkOpts(f); const em=[...r.querySelectorAll(".bk-tm em")].map(e=>e.textContent.trim()); const g=(BK.data&&BK.data.fixtures||[]).find(x=>x.h===em[0]&&x.a===em[1]); return g?bkOpts(g):null; }
      if(kind==="fx"){ const b=[...r.querySelectorAll(".tm b")].map(e=>e.textContent.trim()); const m=b.length===2?findMatchByTeams(b[0],b[1]):null; return m?optsFor(m):null; }
      if(kind==="ms"){ const m=MS.m; return m?optsFor(m):null; } }catch(e){} return null; }
  function btn(on){ return `<button type="button" class="kx-add${on?" on":""}" data-kxa="1" aria-pressed="${!!on}" aria-label="${on?"KUPO'dan çıkar (basılı tut: hangi KUPO)":"Aktif KUPO'ya ekle (basılı tut: hangi KUPO'ya)"}">${on?"✓ KUPO'da":"<b>＋</b> KUPO"}</button>`; }
  const namesOf=r=>{ const k=r.dataset.kxr;
    if(k==="ib"){ const x=IB.rows[+r.dataset.i]; return x?[x.m.h,x.m.a]:null; }
    if(k==="lv"){ const m=(IDL.byId[1]||{})[+r.dataset.id]; return m?[m.h,m.a]:null; }
    if(k==="bk"){ const em=[...r.querySelectorAll(".bk-tm em")].map(e=>e.textContent.trim()); return em.length===2?em:null; }
    if(k==="fx"){ const b=[...r.querySelectorAll(".tm b")].map(e=>e.textContent.trim()); return b.length===2?b:null; }
    if(k==="ms"){ return MS.m?[MS.m.h,MS.m.a]:null; } return null; };
  function scanRows(){ try{
    document.querySelectorAll(".ib-r:not([data-kxr])").forEach(r=>{ const x=IB.rows[+r.dataset.i]; r.dataset.kxr="ib"; if(!x||!x.m) return; const top=r.querySelector(".ib-top"); if(top) top.insertAdjacentHTML("beforeend",btn(!!inAct(x.m.h,x.m.a))); });
    document.querySelectorAll(".lv-c:not([data-kxr])").forEach(r=>{ r.dataset.kxr="lv"; const m=(IDL.byId[1]||{})[+r.dataset.id]; if(!m) return; r.insertAdjacentHTML("beforeend",`<div class="kx-lvb">${btn(!!inAct(m.h,m.a))}</div>`); });
    document.querySelectorAll(".bk-row:not([data-kxr])").forEach(r=>{ r.dataset.kxr="bk"; const n=namesOf(r), bp=r.querySelector(".bk-p"); if(!n||!bp) return;
      const f=BK.rows&&BK.rows[+r.dataset.i]; const lv=f&&bkLiveOf(f); if(lv&&lv.state==="post") return; bp.insertAdjacentHTML("beforeend",btn(!!inAct(n[0],n[1]))); });
    document.querySelectorAll("#lgBox .fxrow:not([data-kxr])").forEach(r=>{ r.dataset.kxr="-"; const b=[...r.querySelectorAll(".tm b")].map(e=>e.textContent.trim()); if(b.length!==2) return;
      let m=null; try{ m=findMatchByTeams(b[0],b[1]); }catch(e){} if(!m||m.sp===2) return; if(!m.sp&&m.dt&&m.dt.getTime()<NOW()-5*60e3&&!m.live) return;
      const w=document.createElement("div"); w.className="kx-fxw"; w.dataset.kxr="fx"; r.before(w); w.appendChild(r); w.insertAdjacentHTML("beforeend",btn(!!inAct(b[0],b[1]))); });
    const ms=$("msheet"); if(ms&&MS.m){ const ad=ms.querySelectorAll(".rb-add"); ad.forEach(b=>{ const t=b.classList.contains("sel")?"✓ KUPO'da":"＋ KUPO"; if(b.textContent!==t) b.textContent=t; });
      const rb=ms.querySelector(".recbig"); if(rb&&!ms.querySelector(".kx-which")){ ms.dataset.kxr="ms"; rb.insertAdjacentHTML("afterend",`<button type="button" class="kx-which" data-kxw="1">${lion()}<span>Aktif KUPO: <b>${esc(act().ad)}</b> · değiştir ›</span></button>`); } }
  }catch(e){} }
  let sq=0; const sched=()=>{ if(sq) return; sq=1; setTimeout(()=>requestAnimationFrame(()=>{ sq=0; scanRows(); }),40); };
  try{ new MutationObserver(sched).observe(document.body,{childList:true,subtree:true}); }catch(e){} sched();
  function kxPaint(){ try{
    document.querySelectorAll("[data-kxr] .kx-add").forEach(b=>{ const r=b.closest("[data-kxr]"), n=namesOf(r); if(!n) return; const on=!!inAct(n[0],n[1]);
      if(b.classList.contains("on")!==on){ b.classList.toggle("on",on); b.setAttribute("aria-pressed",on); b.innerHTML=on?"✓ KUPO'da":"<b>＋</b> KUPO"; } });
    document.querySelectorAll(".ib-r[data-i]").forEach(r=>{ const x=IB.rows[+r.dataset.i]; if(!x||!x.m) return; const k=cpKey(x.m);
      r.querySelectorAll(".ib-od span[data-mk]").forEach(z=>z.classList.toggle("sel",CP.items.some(c=>c.k===k&&c.mk===z.dataset.mk))); });
    const w=document.querySelector(".kx-which b"); if(w) w.textContent=act().ad;
    const ms=$("msheet"); if(ms&&MS.m) ms.querySelectorAll(".rb-add").forEach(b=>{ const on=CP.items.some(c=>c.k===cpKey(MS.m.sp?{lg:"i"+MS.m.ci,h:MS.m.h,a:MS.m.a}:MS.m)&&c.mk===b.dataset.mk); b.classList.toggle("sel",on); b.textContent=on?"✓ KUPO'da":"＋ KUPO"; });
    hdrPaint();
  }catch(e){} }
  window.kxPaint=kxPaint;
  // dokun: ekle/çıkar · basılı tut / sağ tık: Hangi KUPO'ya?
  let lpT=0, lpFired=false;
  document.addEventListener("pointerdown",e=>{ const b=e.target.closest("[data-kxr] .kx-add"); if(!b) return; lpFired=false; clearTimeout(lpT);
    lpT=setTimeout(()=>{ lpFired=true; try{ buzz(12); }catch(_){} openPick(ctxOf(b)); },480); },true);
  ["pointerup","pointercancel","pointerleave"].forEach(t=>document.addEventListener(t,()=>clearTimeout(lpT),true));
  document.addEventListener("scroll",()=>clearTimeout(lpT),{passive:true,capture:true});
  document.addEventListener("contextmenu",e=>{ const b=e.target.closest("[data-kxr] .kx-add"); if(!b) return; e.preventDefault(); clearTimeout(lpT); if(!lpFired){ lpFired=true; openPick(ctxOf(b)); } },true);
  document.addEventListener("click",e=>{ const b=e.target.closest("[data-kxr] .kx-add,[data-kxw]"); if(!b) return; e.preventDefault(); e.stopPropagation();
    if(b.dataset.kxw){ openPick(ctxOf(b),true); return; }
    if(lpFired){ lpFired=false; return; }
    const r=b.closest("[data-kxr]"), n=namesOf(r); try{ buzz(8); }catch(_){}
    if(n&&inAct(n[0],n[1])){ kxRemoveMatch(n[0],n[1]); return; }
    const O=ctxOf(b); if(!O||!O.rec){ toast("Bu maç için seçim bulunamadı; oran kutusuna dokunarak ekleyebilirsin"); return; }
    kxAdd(O,O.rec); },true);
  // bülten oran hücresi / maç sayfası kutusu ile ekleme → kısa bilgi
  document.addEventListener("click",e=>{ const ob=e.target.closest(".ib-od span[data-mk],#msheet .mo"); if(!ob) return;
    if(!ob.closest(".ib-r")&&MS.m&&(MS.live||MS.m.sp)) return;   // v133: canlı pencere → bildirim canlı cpToggle'dan
    const row=ob.closest(".ib-r"); let key=null; try{ if(row){ const x=IB.rows[+row.dataset.i]; key=x&&cpKey(x.m); } else if(MS.m) key=cpKey(MS.m.sp?{lg:"i"+MS.m.ci,h:MS.m.h,a:MS.m.a}:MS.m); }catch(_){} const mk=ob.dataset.mk;
    setTimeout(()=>{ try{ const c=act(); const on=key?c.items.some(z=>z.k===key&&z.mk===mk):ob.classList.contains("sel"); toast(on?`${sfx(c.ad)} eklendi · ${c.items.length} maç`:`${sfx(c.ad,1)} çıkarıldı · ${c.items.length} maç`); kxPaint(); }catch(_){} },0); });
  // ---------- Hangi KUPO'ya? ----------
  function closePick(){ const s=$("kxSheet"); if(s) s.remove(); }
  function openPick(O,switchOnly){ closePick(); const L=open(); const c0=act();
    const has=c=>O&&c.items.some(x=>tmEq(x.h,O.mm.h)&&tmEq(x.a,O.mm.a));
    const s=document.createElement("div"); s.id="kxSheet"; s.className="kx-sh"; s.setAttribute("role","dialog"); s.setAttribute("aria-modal","true"); s.setAttribute("aria-label","Hangi KUPO'ya?");
    s.innerHTML=`<div><div class="gr"></div><h3>${O?"Hangi KUPO'ya?":"Aktif KUPO"}</h3><p>${O?`${esc(O.mm.h)} – ${esc(O.mm.a)} · OXXai önerisi <b>${esc(O.rec?mkName(O.rec.k):"")}</b> %${pct(O.rec&&O.rec.p)}`:"Eklediğin maçlar aktif KUPO'ya gider."}</p>
      <div class="ls">${L.map(c=>`<button type="button" data-pk="${c.id}"><span>${esc(c.ad)}<small>${c.items.length} maç${c.items.length?` · OXXai %${pct(kP(c))}`:""}${c.id===c0.id?" · aktif":""}</small></span>${has(c)?"<i>✓ KUPO'da</i>":c.id===c0.id?"<i>●</i>":""}</button>`).join("")}
      <button type="button" data-pk="new"><span>＋ Yeni KUPO<small>KUPO ${nextNo()} olarak açılır; adını sonra değiştirebilirsin</small></span></button></div>
      <button type="button" class="btn ghost" data-pk="x">Vazgeç</button></div>`;
    document.body.appendChild(s);
    s.addEventListener("click",e=>{ if(e.target===s){ closePick(); return; } const b=e.target.closest("[data-pk]"); if(!b) return; e.stopPropagation(); const id=b.dataset.pk; closePick(); if(id==="x") return;
      const c=id==="new"?kxNew():byId(id); if(!c) return; kxSetActive(c.id); saveL();
      if(O&&!switchOnly){ if(has(c)) toast(`Bu maç zaten ${c.ad} içinde`); else kxAdd(O,O.rec); }
      else if(O&&switchOnly){ toast(`Aktif KUPO: ${c.ad}`); }
      kxPaint(); kxRefresh(); });
    const f=s.querySelector("[data-pk]"); if(f) try{ f.focus({preventScroll:true}); }catch(_){} }
  document.addEventListener("keydown",e=>{ if(e.key==="Escape"&&$("kxSheet")) closePick(); });
  // ---------- üst çubuk: Kuponum ----------
  function hdr(){ const tin=document.querySelector(".topbar .in"); if(!tin) return; let b=$("hdrKup");
    if(!b){ b=document.createElement("button"); b.className="iconbtn"; b.id="hdrKup"; b.type="button";
      b.innerHTML=`${lion()}<span class="tbl">KUPO</span><span class="kx-bd" hidden></span>`;
      b.onclick=()=>{ try{ buzz(6); }catch(e){} kxOpen("cp"); }; }
    const bot=$("hdrBot"); if(bot&&b.nextElementSibling!==bot) bot.before(b); else if(!bot&&!b.parentElement) tin.appendChild(b);
    hdrPaint(); }
  function hdrPaint(){ const b=$("hdrKup"); if(!b) return; const c=act(), n=c.items.length, bd=b.querySelector(".kx-bd");
    if(bd){ bd.hidden=!n; bd.textContent=n; } b.setAttribute("aria-label",`KUPO: ${c.ad}, ${n} maç`); }
  hdr(); setTimeout(hdr,1300); setTimeout(hdr,4200);
  function kxOpen(tab){ KP.tab=tab||"cp"; const b=document.querySelector('nav.tabs button[data-v="kupon"]'); if(b) b.click(); setTimeout(()=>{ try{ kuponTab(KP.tab); }catch(e){} },30); }
  window.kxOpen=kxOpen;
  // görünüm açıkken üst düğme seçili
  document.addEventListener("click",()=>setTimeout(()=>{ const v=$("v-kupon"), b=$("hdrKup"); if(!b) return; if(v&&!v.hidden) b.setAttribute("aria-current","page"); else b.removeAttribute("aria-current"); },40));
  // ---------- Kuponum ekranı ----------
  const UI={edit:false,cf:null,mk:-1,od:null,ocf:null};
  function shell(){ const v=$("v-kupon"); if(!v) return null;
    if(!$("kxHero")){ const lt=v.querySelector(".ltitle");
      const h=`<div class="kx-hero" id="kxHero">${lion()}<div><h1>KUPO</h1><p id="kxSub"></p></div></div>
        <div class="seg" role="group" id="kxSeg" aria-label="KUPO"><button type="button" data-kt="cp">KUPO'larım</button><button type="button" data-kt="eski">Eski KUPO'larım<small id="kxN2"></small></button><button type="button" data-kt="oyn">Takip</button></div>`;
      lt?lt.insertAdjacentHTML("afterend",h):v.insertAdjacentHTML("afterbegin",h);
      $("kxSeg").onclick=e=>{ const b=e.target.closest("[data-kt]"); if(!b) return; try{ buzz(6); Sound.tap(); }catch(_){} UI.od=null; kuponTab(b.dataset.kt); window.scrollTo({top:0}); }; }
    const cb=$("cpBox");
    if(!$("kxChips")&&cb){ cb.insertAdjacentHTML("beforebegin",`<div class="kx-chips" id="kxChips" role="group" aria-label="KUPO seç"></div>`);
      $("kxChips").onclick=e=>{ const b=e.target.closest("[data-kc]"); if(!b) return; try{ buzz(6); }catch(_){} UI.edit=false; UI.cf=null; UI.mk=-1;
        if(b.dataset.kc==="new"){ const c=kxNew(); kxSetActive(c.id); saveL(); toast(`${c.ad} açıldı · eklediğin maçlar buraya gelir`); }
        else kxSetActive(b.dataset.kc);
        renderKupon(); }; }
    if(!$("kxOld")){ const ob=$("oynBox"), anchor=ob||cb; const d=document.createElement("div"); d.id="kxOld"; d.className="wrap"; d.hidden=true; if(anchor) anchor.after(d); else v.appendChild(d); }
    if(!$("kxSnc")){ const d=document.createElement("button"); d.type="button"; d.id="kxSnc"; d.className="btn ghost"; d.hidden=true; d.textContent="Kayıtlı tahminler (maç analizlerin) ›";
      d.onclick=()=>{ const b=document.querySelector('nav.tabs button[data-v="sonuc"]'); if(b) b.click(); }; $("kxOld").after(d); }
    return v; }
  function applyTab(t){ const cb=$("cpBox"), ob=$("oynBox"), od=$("kxOld"), ch=$("kxChips"), sn=$("kxSnc"); if(!od) return;
    if(cb) cb.hidden=t!=="cp"; if(ob) ob.hidden=t!=="oyn"; od.hidden=t!=="eski"; if(ch) ch.hidden=t!=="cp"; if(sn) sn.hidden=t!=="oyn";
    const sg=$("kxSeg"); if(sg) sg.querySelectorAll("[data-kt]").forEach(b=>b.setAttribute("aria-pressed",b.dataset.kt===t));
    const n2=$("kxN2"), P=past(); if(n2) n2.textContent=P.length?String(P.length):"";
    const sub=$("kxSub"), c=act();
    if(sub) sub.innerHTML=t==="eski"?"Biten ve arşivlediğin KUPO'lar, isabet özetin":t==="oyn"?"Takip ettiğin listeler ve kişisel istatistiğin":`Aktif KUPO: <b>${esc(c.ad)}</b> · ${c.items.length} maç · ${open().length} açık KUPO`;
    if(t==="eski") renderOld(); }
  const _kt=kuponTab; kuponTab=function(t){ if(t==="snc") return _kt.apply(this,arguments); shell(); const r=_kt.call(this,t==="eski"?"cp":t); KP.tab=t; applyTab(t); return r; };
  function chipsHtml(){ const c0=act();
    return open().map(c=>{ const s=kxSt(c); return `<button type="button" data-kc="${c.id}" aria-pressed="${c.id===c0.id}">${s!=="e"?`<i class="kx-dot ${s==="q"?"w":s}"></i>`:""}${esc(c.ad)}<small>${c.items.length||""}</small></button>`; }).join("")
      +`<button type="button" class="kx-new" data-kc="new" aria-label="Yeni KUPO">＋ Yeni KUPO</button>`; }
  function rowHtml(x,i,opt){ const O=opt.O, weak=opt.weak===i, started=tms(x.dt)<NOW(), canSw=O&&O.opts&&O.opts.length>1&&!started&&x.ok==null;
    const lgN=x.sp==="bk"?"🏀 Basketbol":(LEAGUES[x.lg]?LEAGUES[x.lg].n:x.live?"Canlı":"");
    const res=x.ok===true?`<span class="kx-res g" role="img" aria-label="Tuttu"><i>✓</i></span>`:x.ok===false?`<span class="kx-res x" role="img" aria-label="Tutmadı"><i>✗</i></span>`
      :`<button class="rm" type="button" data-kx="rm" data-i="${i}" aria-label="${esc(x.h)} – ${esc(x.a)} maçını KUPO'dan çıkar">✕</button>`;
    const rec=O&&O.rec&&O.rec.k!==x.mk&&x.ok==null&&!started?`<div class="kx-hint">OXXai önerisi: <b>${esc(mkName(O.rec.k))} %${pct(O.rec.p)}</b><button type="button" class="kx-lnk" data-kx="use" data-i="${i}">Uygula</button></div>`:"";
    const man=x.need&&x.ok==null?`<div class="kx-hint">Sonuç otomatik bulunamadı:<span class="kx-man"><button type="button" data-kx="man" data-i="${i}" data-v="1" aria-label="Tuttu olarak işaretle">✓</button><button type="button" data-kx="man" data-i="${i}" data-v="0" aria-label="Tutmadı olarak işaretle">✗</button></span></div>`:"";
    const ops=UI.mk===i&&canSw?`<div class="kx-opts" role="group" aria-label="Seçimi değiştir">${O.opts.map(o=>`<button type="button" data-kx="sw" data-i="${i}" data-k="${o.k}" aria-pressed="${o.k===x.mk}" class="${O.rec&&O.rec.k===o.k?"rec":""}">${esc(mkName(o.k))}<small>${o.o?f2(o.o):"–"} · %${pct(o.p)}</small></button>`).join("")}</div>`:"";
    return `<div class="cprow kx-r${weak?" weak":""}" data-cpi="${i}"><div class="l"><small>${x.sp==="bk"?"":(FLAG[x.lg]||"")} ${lgN?esc(lgN)+" · ":""}${esc(ist(new Date(tms(x.dt)),{weekday:"short",hour:"2-digit",minute:"2-digit"}))}${x.live?" · canlı eklendi":""}</small>
      <b>${esc(x.h)} – ${esc(x.a)}</b><span class="kx-line"><button type="button" class="kx-mk" data-kx="mk" data-i="${i}" ${canSw?`aria-expanded="${UI.mk===i}"`:"disabled"} aria-label="Seçim: ${esc(mkName(x.mk))}${canSw?", değiştir":""}">${esc(mkName(x.mk))}${canSw?`<span class="cv">▾</span>`:""}</button><span>OXXai <span class="kx-pp">%${pct(x.p)}</span></span>${weak&&x.ok==null?`<span class="kx-weak">En zayıf halka</span>`:""}${x.s?`<span class="kx-sc">Skor ${esc(x.s)}${x.s1?` (İY ${esc(x.s1)})`:""}</span>`:started&&x.ok==null?`<span class="kx-sc">${tms(x.dt)>NOW()-110*60e3?"oynanıyor":"sonuç bekleniyor"}</span>`:""}</span>${rec}${man}${ops}</div>
      <span class="o">${f2(x.odd)}${x.fair?`<small style="display:block;font:500 10.5px var(--font);color:var(--ink3)">adil</small>`:""}</span>${res}</div>`; }
  function sumHtml(c){ const I=c.items, n=I.length, odd=kOdd(c), p=kP(c), mkt=1/odd, avgO=I.reduce((a,x)=>a+(+x.odd||1),0)/n, avgP=I.reduce((a,x)=>a+(x.p||.5),0)/n, exp=I.reduce((a,x)=>a+(x.p||.5),0);
    const wi=I.reduce((b,x,i)=>(x.p||.5)<(I[b].p||.5)?i:b,0), w=I[wi], R=rating(p,odd), diff=Math.round((p-mkt)*100);
    const g=I.filter(x=>x.ok===true).length, x=I.filter(x=>x.ok===false).length, wt=n-g-x;
    return `<div class="panel cpsum kx-sum"><div class="list">
      <div><span>Seçim</span><span>${n} maç</span></div>
      <div class="kp-odd"><span>Toplam oran</span><span><b>${f2(odd)}</b></span></div>
      <div><span>OXXai birlikte tutma olasılığı</span><span><b>%${pct(p)}</b></span></div>
      <div><span>Piyasa olasılığı<span class="kx-sub">1 / toplam oran</span></span><span>%${pct(mkt)}<span class="kx-sub">${n?(Math.abs(diff)<1?"OXXai ile aynı":`OXXai ${Math.abs(diff)} puan ${diff>0?"daha iyimser":"daha temkinli"}`):""}</span></span></div>
      <div><span>Ortalama oran</span><span>${f2(avgO)}</span></div>
      <div><span>Ortalama OXXai olasılığı</span><span>%${pct(avgP)}</span></div>
      <div><span>Beklenen tutan maç<span class="kx-sub">olasılıklar toplamı</span></span><span>${f1(exp)} / ${n}</span></div>
      ${n>1?`<div><span>En zayıf halka</span><span>${esc(w.h)} – ${esc(w.a)}<span class="kx-sub">${esc(mkName(w.mk))} · %${pct(w.p)}</span></span></div>`:""}
      ${g||x?`<div><span>Sonuç</span><span>${g} tuttu · ${x} tutmadı${wt?` · ${wt} bekliyor`:""}</span></div>`:""}
      <div class="kp-ev"><span>Değerlendirme</span><span class="pill ${R[1]}">${R[0]}</span></div></div>
      <p class="note">Birlikte tutma olasılığı, her seçimin OXXai olasılığının çarpımıdır (maçlar bağımsız sayılır). Maç sayısı arttıkça olasılık hızla düşer. Değerlendirme: olasılık × toplam oran 1,05 üstü değerli, 0,92–1,05 adil.</p>
      <div class="actions"><button class="btn ghost" type="button" id="cpClear">Temizle</button></div></div>`; }
  function actsHtml(c){ const n=c.items.length;
    if(UI.cf==="del") return `<div class="kx-cf" role="alertdialog" aria-label="KUPO'yu sil"><p><b>${esc(c.ad)}</b> silinsin mi? İçindeki ${n} maç da silinir; bu geri alınamaz.</p><div><button type="button" class="btn ghost" data-kx="cfno">Vazgeç</button><button type="button" class="btn dng" data-kx="cfdel">Sil</button></div></div>`;
    if(UI.cf==="clr") return `<div class="kx-cf" role="alertdialog" aria-label="KUPO'yu temizle"><p><b>${esc(c.ad)}</b> içindeki ${n} maç çıkarılsın mı? KUPO boş olarak kalır.</p><div><button type="button" class="btn ghost" data-kx="cfno">Vazgeç</button><button type="button" class="btn dng" data-kx="cfclr">Temizle</button></div></div>`;
    return `<div class="kx-acts"><button type="button" data-kx="share" ${n?"":"disabled"}>${IC.share}Paylaş</button><button type="button" data-kx="dup" ${n?"":"disabled"}>${IC.copy}Çoğalt</button><button type="button" data-kx="arch" ${n?"":"disabled"}>${IC.arch}Arşive kaldır</button><button type="button" class="dng" data-kx="del">${IC.del}Sil</button></div>`; }
  function kxRenderCp(){ const box=$("cpBox"); if(!box) return; const c=act(), I=c.items;
    const ch=$("kxChips"); if(ch) ch.innerHTML=chipsHtml();
    const head=`<div class="kx-ch"><div class="kx-nm">${UI.edit?`<input class="kx-in" id="kxIn" maxlength="32" value="${esc(c.ad)}" aria-label="KUPO adı" enterkeyhint="done"><button type="button" class="kx-ic" data-kx="rok" aria-label="Adı kaydet">✓</button>`
        :`<h2>${esc(c.ad)}</h2><button type="button" class="kx-ic" data-kx="ren" aria-label="KUPO adını değiştir">${IC.pen}</button>`}</div>${UI.edit?"":stPill(c)}</div>
      <div class="kx-meta">${I.length} maç · ${esc(ist(new Date(c.olusturma),{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}))} açıldı${c.tasindi?" · önceki listenden taşındı":""}</div>`;
    if(!I.length){ box.innerHTML=`<div class="panel kx-card">${head}<div class="kx-empty panel" style="background:none;border:0;padding:8px 0">${lion()}<b>${esc(c.ad)} boş</b><p>Bültende, canlıda ya da fikstürde maç satırındaki <b>＋ KUPO</b>'ya dokun; OXXai'nin önerdiği seçim eklenir. Kendi seçimin için oran kutusuna dokun.</p></div>
        <button class="btn" type="button" id="cpSuggest">Günün en olası tahminlerini getir</button><button class="btn ghost" type="button" id="cpGo">Bültene git</button></div>${actsHtml(c)}
        <p class="kx-tip">İpucu: ＋ KUPO düğmesine basılı tutarsan hangi KUPO'ya ekleneceğini seçebilirsin.</p>`;
      $("cpGo").onclick=goHome; $("cpSuggest").onclick=()=>{ suggestCoupon(); try{ paintCoupon(); }catch(e){} };
    } else {
      const O=I.map(x=>x.ok==null&&tms(x.dt)>NOW()?(x.sp==="bk"?(()=>{ const m=matchOfItem(x); return m?bkOpts(m.bk):null; })():optsFor(matchOfItem(x))):null);
      const wi=I.length>1?I.reduce((b,x,i)=>(x.p||.5)<(I[b].p||.5)?i:b,0):-1;
      box.innerHTML=`<div class="panel kx-card">${head}${I.map((x,i)=>rowHtml(x,i,{O:O[i],weak:wi})).join("")}</div>${sumHtml(c)}${actsHtml(c)}
        <p class="kx-tip">Maçlar bitince her satırda ✓/✗ görünür; tüm maçlar bitince KUPO sonucuyla <b>Eski KUPO'larım</b> bölümüne geçer. Kayıtlar yalnızca bu telefonda tutulur.</p>
        <p class="disc">OXXai yalnızca hobi amaçlı maç tahmini ve takip aracıdır; şans oyunu değildir, oyun almaz ve hiçbir siteye yönlendirmez · 18+</p>`;
      box._O=O; }
    const inp=$("kxIn"); if(inp){ inp.focus(); inp.select(); inp.onkeydown=e=>{ if(e.key==="Enter"){ e.preventDefault(); rename(inp.value); } else if(e.key==="Escape"){ UI.edit=false; kxRenderCp(); } }; inp.onblur=()=>setTimeout(()=>{ if(UI.edit) rename(inp.value); },120); }
    const cl=$("cpClear"); if(cl) cl.onclick=()=>{ UI.cf="clr"; kxRenderCp(); };
    applyTab(KP.tab||"cp"); }
  function rename(v){ const c=act(); v=String(v||"").replace(/\s+/g," ").trim().slice(0,32); UI.edit=false; if(v&&v!==c.ad){ c.ad=v; c.upd=NOW(); saveL(); toast("KUPO adı: "+v); } kxRenderCp(); hdrPaint(); }
  function shareText(c){ const I=c.items, st=kxSt(c);
    return `🏆 OXXai · ${c.ad}${st==="g"||st==="x"?" · "+ST[st]:""}\n`+I.map((x,i)=>`${i+1}) ${x.sp==="bk"?"🏀":"⚽"} ${x.h} – ${x.a}: ${mkName(x.mk)} · oran ${f2(x.odd)} · OXXai %${pct(x.p)}${x.ok===true?" ✓":x.ok===false?" ✗":""}${x.s?" ("+x.s+")":""}`).join("\n")
      +`\nToplam oran ${f2(kOdd(c))} · OXXai birlikte tutma olasılığı %${pct(kP(c))}\n${LEGAL_SHARE}`; }
  function dupOf(c){ const up=c.items.filter(x=>tms(x.dt)>NOW()).map(x=>{ const y=Object.assign({},x); ["ok","s","s1","need","man","at"].forEach(k=>delete y[k]); return y; });
    if(!up.length){ toast("Çoğaltılacak, henüz başlamamış maç yok"); return null; }
    const n=kxNew(`${c.ad} kopya`.slice(0,32),up); kxSetActive(n.id); saveL(); toast(`${n.ad} açıldı · ${up.length} maç`); return n; }
  document.addEventListener("click",e=>{ const b=e.target.closest("#cpBox [data-kx],#kxOld [data-kx]"); if(!b) return; e.stopPropagation(); const a=b.dataset.kx, c=act(), i=+b.dataset.i;
    try{ buzz(6); }catch(_){}
    if(a==="rm"){ const x=c.items[i]; if(!x) return; c.items.splice(i,1); UI.mk=-1; cpSave(); toast(`${sfx(c.ad,1)} çıkarıldı · ${c.items.length} maç`); renderKupon(); return; }
    if(a==="mk"){ UI.mk=UI.mk===i?-1:i; kxRenderCp(); return; }
    if(a==="sw"||a==="use"){ const O=($("cpBox")._O||[])[i]; if(!O) return; const o=a==="use"?O.rec:O.opts.find(z=>z.k===b.dataset.k); if(!o) return; UI.mk=-1;
      const x=c.items[i]; if(x&&x.mk===o.k){ kxRenderCp(); return; } kxAdd(O,o,true); toast(`Seçim: ${mkName(o.k)} · OXXai %${pct(o.p)}`); renderKupon(); return; }
    if(a==="man"){ const x=c.items[i]; if(!x) return; x.ok=b.dataset.v==="1"; x.man=1; settle(); saveL(); renderKupon(); return; }
    if(a==="ren"){ UI.edit=true; kxRenderCp(); return; }
    if(a==="rok"){ const inp=$("kxIn"); rename(inp?inp.value:c.ad); return; }
    if(a==="share"){ openShare({title:"KUPO'yu paylaş",text:shareText(c),url:appLink()}); return; }
    if(a==="dup"){ if(dupOf(c)) renderKupon(); return; }
    if(a==="arch"){ c.durum="arsiv"; c.arsivAt=NOW(); saveL(); act(); toast(`${c.ad} Eski KUPO'larıma taşındı`); try{ paintCoupon(); }catch(_){} renderKupon(); return; }
    if(a==="del"){ UI.cf="del"; kxRenderCp(); const cf=document.querySelector("#cpBox .kx-cf"); if(cf) cf.scrollIntoView({block:"nearest",behavior:"smooth"}); return; }
    if(a==="cfno"){ UI.cf=null; kxRenderCp(); return; }
    if(a==="cfclr"){ UI.cf=null; c.items.length=0; cpSave(); toast(`${c.ad} temizlendi`); renderKupon(); return; }
    if(a==="cfdel"){ UI.cf=null; const ad=c.ad; kxDel(c.id); KX.aktif=null; act(); saveL(); try{ paintCoupon(); }catch(_){} toast(`${ad} silindi`); renderKupon(); return; }
    // Eski KUPO'larım
    if(a==="oo"){ UI.od=UI.od===b.dataset.c?null:b.dataset.c; UI.ocf=null; renderOld(); return; }
    const oc=byId(b.dataset.c);
    if(a==="ocp"&&oc){ if(dupOf(oc)){ KP.tab="cp"; renderKupon(); } return; }
    if(a==="oback"&&oc){ oc.durum="acik"; delete oc.arsivAt; kxSetActive(oc.id); saveL(); toast(`${oc.ad} KUPO'larıma geri alındı`); KP.tab="cp"; renderKupon(); return; }
    if(a==="osh"&&oc){ openShare({title:"KUPO'yu paylaş",text:shareText(oc),url:appLink()}); return; }
    if(a==="odel"&&oc){ UI.ocf=oc.id; renderOld(); return; }
    if(a==="ocfno"){ UI.ocf=null; renderOld(); return; }
    if(a==="ocfdel"&&oc){ kxDel(oc.id); UI.ocf=null; UI.od=null; saveL(); toast(`${oc.ad} silindi`); renderOld(); applyTab("eski"); return; }
    if(a==="oman"&&oc){ const x=oc.items[i]; if(!x) return; x.ok=b.dataset.v==="1"; x.man=1; saveL(); renderOld(); return; }
  },true);
  // ---------- Eski KUPO'larım + istatistik ----------
  function kxStats(){ const P=past().filter(c=>c.items.length), D=P.filter(c=>{ const s=kxSt(c); return s==="g"||s==="x"; }), W=D.filter(c=>kxSt(c)==="g");
    const _u=new Map(); KX.L.flatMap(c=>c.items).filter(i=>i&&i.ok!=null).forEach(i=>_u.set((i.k||i.h+"|"+i.a)+"|"+i.mk,i)); const items=[..._u.values()], ih=items.filter(i=>i.ok).length, ip=items.filter(i=>i.p);
    const seq=D.slice().sort((a,b)=>(a.bitti||a.arsivAt||0)-(b.bitti||b.arsivAt||0)).map(c=>kxSt(c)==="g");
    let cur=0; for(let i=seq.length-1;i>=0&&seq[i]===seq[seq.length-1];i--) cur++;
    let best=0,run=0; for(const s of seq){ run=s?run+1:0; best=Math.max(best,run); }
    const top=W.slice().sort((a,b)=>kOdd(b)-kOdd(a))[0]||null;
    return {nP:P.length,n:D.length,w:W.length,ni:items.length,ih,avgN:D.length?D.reduce((a,c)=>a+c.items.length,0)/D.length:0,avgO:D.length?D.reduce((a,c)=>a+kOdd(c),0)/D.length:0,
      predC:D.length?D.reduce((a,c)=>a+kP(c),0)/D.length:0,predI:ip.length?ip.reduce((a,i)=>a+i.p,0)/ip.length:0,hitI:ip.length?ip.filter(i=>i.ok).length/ip.length:0,
      cur,curW:seq.length?seq[seq.length-1]:null,best,top}; }
  window.kxStats=kxStats;
  function statsHtml(S){ if(!S.n&&!S.ni) return "";
    const wr=S.n?S.w/S.n:0, hr=S.ni?S.ih/S.ni:0;
    return `<div class="panel"><div class="kx-kh"><b>${S.n} KUPO'dan ${acc(S.w)} tuttu</b><small>${S.nP>S.n?`${S.nP-S.n} KUPO'nun sonucu eksik`:"yalnızca bu telefonda"}</small></div>
      <div class="kx-tiles">
        <div class="kx-tile gd"><small>KUPO kazanma oranı</small><b>%${pct(wr)}</b><div class="kx-bar"><i style="width:${Math.round(wr*100)}%"></i></div></div>
        <div class="kx-tile"><small>Maç bazında isabet</small><b>%${pct(hr)}</b><i>${S.ih} / ${S.ni} seçim tuttu</i></div>
        <div class="kx-tile"><small>Ortalama KUPO</small><b>${f1(S.avgN)} maç</b><i>ort. toplam oran ${f2(S.avgO)}</i></div>
        <div class="kx-tile"><small>Seri</small><b>${S.cur?`${S.cur} ${S.curW?"tuttu":"tutmadı"}`:"–"}</b><i>en uzun tutan seri ${S.best}</i></div>
        ${S.n?`<div class="kx-tile w2"><small>OXXai kalibrasyonu · KUPO</small><i>OXXai bu KUPO'lar için ortalama <b>%${pct(S.predC)}</b> demişti; gerçekte <b>${accP(wr)}</b> tuttu.${S.n<10?" Örnek az, temkinli oku.":""}</i></div>`:""}
        ${S.ni?`<div class="kx-tile w2"><small>OXXai kalibrasyonu · maç</small><i>Seçimlerde OXXai ortalama <b>%${pct(S.predI)}</b> demişti; gerçekte <b>${accP(S.hitI)}</b> tuttu.</i></div>`:""}
        ${S.top?`<div class="kx-tile w2 gd"><small>En iyi KUPO</small><b>${esc(S.top.ad)}</b><i>${S.top.items.length} maç · toplam oran ${f2(kOdd(S.top))} · OXXai %${pct(kP(S.top))} demişti</i></div>`:""}
      </div></div>`; }
  function renderOld(){ const box=$("kxOld"); if(!box) return; const P=past(), S=kxStats();
    if(!P.length){ box.innerHTML=`<div class="panel kx-empty">${lion()}<b>Henüz eski KUPO yok</b><p>KUPO'ndaki tüm maçlar bitince KUPO sonucuyla birlikte buraya taşınır. İstersen bir KUPO'yu “Arşive kaldır” ile de taşıyabilirsin. Kayıtlar yalnızca bu telefonda tutulur.</p></div>`; return; }
    box.innerHTML=statsHtml(S)+`<div class="kx-old">${P.map(c=>{ const I=c.items, s=kxSt(c), h=I.filter(i=>i.ok).length, opn=UI.od===c.id;
      return `<div class="kx-oc"><button type="button" class="kx-oh" data-kx="oo" data-c="${c.id}" aria-expanded="${opn}"><b>${esc(c.ad)}</b>${stPill(c)}<small>${esc(ist(new Date(c.bitti||c.arsivAt||c.olusturma),{day:"numeric",month:"short",year:"numeric"}))} · ${I.length} maç · ${h}/${I.length} tuttu · oran ${f2(kOdd(c))} · OXXai %${pct(kP(c))}${c.durum==="arsiv"&&s==="w"?" · arşivde, sonuç bekliyor":""}</small></button>
        ${opn?`<div class="kx-od">${I.map((x,i)=>`<div class="cprow"><div class="l"><small>${esc(ist(new Date(tms(x.dt)),{weekday:"short",day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}))}</small><b>${esc(x.h)} – ${esc(x.a)}</b><span class="kx-line"><span>${esc(mkName(x.mk))}</span><span>OXXai <span class="kx-pp">%${pct(x.p)}</span></span>${x.s?`<span class="kx-sc">Skor ${esc(x.s)}${x.s1?` (İY ${esc(x.s1)})`:""}</span>`:""}</span>${x.need&&x.ok==null?`<div class="kx-hint">Sonuç bulunamadı:<span class="kx-man"><button type="button" data-kx="oman" data-c="${c.id}" data-i="${i}" data-v="1" aria-label="Tuttu">✓</button><button type="button" data-kx="oman" data-c="${c.id}" data-i="${i}" data-v="0" aria-label="Tutmadı">✗</button></span></div>`:""}</div>
            <span class="o">${f2(x.odd)}</span>${x.ok===true?`<span class="kx-res g" role="img" aria-label="Tuttu"><i>✓</i></span>`:x.ok===false?`<span class="kx-res x" role="img" aria-label="Tutmadı"><i>✗</i></span>`:`<span class="kx-res w" role="img" aria-label="Bekliyor"><i>⏳</i></span>`}</div>`).join("")}
          ${UI.ocf===c.id?`<div class="kx-cf"><p><b>${esc(c.ad)}</b> kalıcı olarak silinsin mi?</p><div><button type="button" class="btn ghost" data-kx="ocfno">Vazgeç</button><button type="button" class="btn dng" data-kx="ocfdel" data-c="${c.id}">Sil</button></div></div>`
            :`<div class="kx-acts"><button type="button" data-kx="osh" data-c="${c.id}">${IC.share}Paylaş</button>${c.durum==="arsiv"?`<button type="button" data-kx="oback" data-c="${c.id}">${IC.back}Geri al</button>`:`<button type="button" data-kx="ocp" data-c="${c.id}">${IC.copy}Çoğalt</button>`}<button type="button" class="dng" data-kx="odel" data-c="${c.id}">${IC.del}Sil</button></div>`}</div>`:""}</div>`; }).join("")}</div>`; }
  // ---------- renderKupon / paintCoupon zinciri ----------
  const _rk=renderKupon; renderKupon=function(){ shell(); const r=_rk.apply(this,arguments); try{ kxRenderCp(); }catch(e){ console.error(e); } try{ kxGrade(); }catch(e){} return r; };
  const _pc=paintCoupon; paintCoupon=function(){ const r=_pc.apply(this,arguments); try{ hdrPaint(); kxPaintLite(); }catch(e){} return r; };
  let pq=0; function kxPaintLite(){ if(pq) return; pq=1; requestAnimationFrame(()=>{ pq=0; kxPaint(); }); }
  const _cs=cpSave; cpSave=function(){ try{ const c=act(); c.upd=NOW(); saveL(); }catch(e){} const r=_cs.apply(this,arguments); try{ settle(); }catch(e){} return r; };
  function kxRefresh(){ try{ hdrPaint(); kxPaint(); if(UI.edit) return; const v=$("v-kupon"); if(v&&!v.hidden){ if(KP.tab==="eski") renderOld(); else kxRenderCp(); } }catch(e){} }
  window.kxRefresh=kxRefresh;
  window.kxShareText=c=>shareText(c);   // v129: KUPO paylaş listesi (tek tek / çoklu seçim)
  window.addEventListener("storage",e=>{ if(e.key===LSK||e.key===LSA||e.key==="bx-kuponlar-sil"){ try{ if(e.key==="bx-kuponlar-sil"){ JSON.parse(e.newValue||"[]").forEach(x=>DEL.add(x)); } load(); kxRefresh(); }catch(_){} } });
  // v133: canlı maçta aynı maça birden çok canlı tahmin (farklı pazar) eklenebilir; her canlı kalemin anahtarı benzersizdir
  //   (temel anahtar|pazar|dakika, bk = temel anahtar). Maç öncesi "aynı maçtan tek seçim" kuralı yalnız maç öncesi kalemlerde geçerli.
  //   Canlı oran kapalıysa / hiç yoksa (ör. lig modeli ve canlı oranı olmayan kupa maçı) OXXai olasılığından adil oranla eklenir.
  const LVN={IO05:"İlk yarı 0,5 Üst (İY'de gol olur)",IU05:"İlk yarı 0,5 Alt (İY golsüz biter)",IO15:"İlk yarı 1,5 Üst (İY'de 2+ gol)",IU15:"İlk yarı 1,5 Alt (İY'de en çok 1 gol)"};
  const lvNz=v=>{ v=String(v); return v==="U"||v==="A"?v+"2.5":v; };
  try{ const _ct=cpToggle; cpToggle=function(m,mk,odd,p){ try{ const k=cpKey(m), I=CP.items, had=I.find(x=>x.k===k&&x.mk===mk);
        if(!had){ const t=tms(m.dt);
          const lv=!m.live&&m.sp!==1&&t&&t<NOW()?((typeof IDL!=="undefined"&&IDL.live&&IDL.live[1]||[]).find(x=>tmEq(x.h,m.h)&&tmEq(x.a,m.a))||null):null;
          if(!m.live&&m.sp!==1&&t&&(t<NOW()-5*60e3||lv)){
            // başlamış maç: canlı eşi varsa seçim canlı oran (yoksa adil oran) + canlı OXXai olasılığıyla eklenir
            if(!lv){ toast(t<NOW()-150*60e3?"Bu maç bitmiş; KUPO'ya eklenemez":"Bu maç başladı: canlı tahmini Canlı sekmesinden ya da ＋ KUPO ile ekleyebilirsin"); return; }
            try{ const P=idlPred(lv), K=idlPick(lv,P); if(!K){ toast("Canlı tahmin şu an hesaplanamadı"); return; }
              const smk=String(mk), base=/^[UA][\d.]+$/.test(smk)?smk.charAt(0):smk, ou=base==="U"||base==="A";
              const mm={lg:"i"+lv.ci,h:lv.h,a:lv.a,dt:new Date(lv.ts)}, k2=cpKey(mm), fl=v=>String(v).replace(".",",");
              const sameM=x=>x.k===k2||x.bk===k2||(x.live&&tmEq(x.h,mm.h)&&tmEq(x.a,mm.a));
              // ikinci dokunuş: aynı canlı seçim zaten KUPO'da → yalnız o çıkar (aynı maçın diğer canlı tahminleri kalır)
              const hi=I.findIndex(x=>sameM(x)&&lvNz(x.mk)===lvNz(smk));
              if(hi>=0){ I.splice(hi,1); cpSave(); try{ Sound.toggle(false); }catch(_){} toast("Canlı seçim KUPO'dan çıkarıldı"); return; }
              // Üst/Alt: istenen çizgi canlı çizgiyle aynı değilse sessizce başka çizgiye çevirme
              if(ou){ const want=smk.length>1?+smk.slice(1):2.5, line=+P.line;
                if(!isFinite(line)){ toast("Bu seçim canlı bültende yok"); return; }
                if(line!==want){ toast(`Canlı çizgi şu an ${fl(line)}; ${fl(want)} ${base==="U"?"Üst":"Alt"} canlı bültende yok`); return; } }
              const c=K.all.concat(K.ext||[]).find(z=>z.k===base);
              if(!c){ toast(/^I[OU](05|15)$/.test(base)?"İlk yarı bitti ya da bu seçim kesinleşti; artık eklenemez":"Bu seçim canlı bültende yok"); return; }
              const pp=Math.max(.01,Math.min(.99,typeof liveCal==="function"?liveCal(c.p).p:c.p)), fair=!c.o, o=fair?+(1/pp).toFixed(2):+c.o;
              const mn=(()=>{ try{ const s=idlSecs(lv); return s==null?(+lv.min||0):Math.floor(s/60); }catch(_){ return +lv.min||0; } })();
              // eski sürümden kalan (benzersiz anahtarsız) canlı kalem temel cpToggle'da yer değiştirmesin diye taşınır
              I.forEach(x=>{ if(x.k===k2&&x.live){ x.bk=k2; x.k=k2+"|"+x.mk+"|"+(x.mn!=null?x.mn:"e"); } });
              const r=_ct.call(this,mm,smk,o,pp); const it=CP.items.find(x=>x.k===k2&&x.mk===smk);
              if(it){ it.live=1; it.bk=k2; it.mn=mn; it.k=k2+"|"+smk+"|"+mn; it.s0=`${lv.hs}-${lv.as}`; it.iid=lv.id; if(fair) it.fair=1; else delete it.fair; cpSave(); }
              const n=CP.items.filter(x=>tmEq(x.h,mm.h)&&tmEq(x.a,mm.a)).length, nm=LVN[smk]||mkName(smk);
              toast(`${n>1?n+". canlı tahmin eklendi":"Canlı eklendi"} · ${nm} %${Math.round(pp*100)} · ${fair?"adil oran":"oran"} ${fO(o)}`); return r; }catch(e){ toast("Canlı tahmin şu an hesaplanamadı"); return; } }
          // maç öncesi seçim: aynı maçtan tek maç öncesi seçim (canlı tahminlere dokunulmaz)
          const d=I.findIndex(x=>x.k!==k&&!x.live&&tmEq(x.h,m.h)&&tmEq(x.a,m.a)); if(d>=0) I.splice(d,1); } }catch(e){}
      return _ct.apply(this,arguments); }; }catch(e){}
  // ---------- adlar: Menü, sekme, Power Now, Kayıtlı ----------
  try{ TAB_NAMES.kupon="KUPO"; }catch(e){}
  try{ for(const g of MENU_PLAN) for(const it of g[1]) if(it[0]==="#moreCp"){ it[1]="KUPO"; it[2]="KUPO'ların, sonuçları ve eski KUPO'ların"; } menuOrganize(); }catch(e){}
  function menuIc(){ const c=$("moreCp"); if(!c) return; const ic=c.querySelector(".ic"); if(ic&&!ic.classList.contains("kx-ic2")){ ic.classList.add("kx-ic2"); ic.innerHTML=lion(); }
    c.onclick=()=>kxOpen("cp"); }
  menuIc(); setTimeout(menuIc,1600);
  try{ oynBadge=(f=>function(){ const r=f.apply(this,arguments); try{ const c=$("moreCp"), s=c&&c.querySelector(".tx small"); if(s){ const n=open().length, w=OYN.L.filter(sl=>oynSt(sl)==="w").length; s.textContent=`${n} KUPO · aktif: ${act().ad}${w?` · ${w} takip bekliyor`:""}`; } }catch(e){} return r; })(oynBadge); oynBadge(); }catch(e){}
  try{ const sg=$("sncSeg"); if(sg){ const L={cp:"KUPO",oyn:"Takip",snc:"Kayıtlı"}; sg.querySelectorAll("[data-k]").forEach(b=>{ if(L[b.dataset.k]) b.textContent=L[b.dataset.k]; }); } }catch(e){}
  try{ const _rp=renderPower; renderPower=function(){ const r=_rp.apply(this,arguments); try{ const b=$("pwCp"); if(b){ const c=act(); b.innerHTML=`${lion()}${esc(c.ad)} · <b>${c.items.length} maç</b><span>Aç ›</span>`; b.onclick=()=>kxOpen("cp"); } }catch(e){} return r; }; }catch(e){}
  // Kuponum ekranındayken "Kuponum" görünümünü yeni kabukla aç
  document.querySelector('nav.tabs button[data-v="kupon"]').addEventListener("click",()=>{ shell(); });
  // ---------- OXXai: kuponum · kuponlarım · yeni kupon · eski kuponlarım ----------
  const NZ=t=>String(t||"").toLocaleLowerCase("tr").replace(/ç/g,"c").replace(/ğ/g,"g").replace(/ı/g,"i").replace(/ö/g,"o").replace(/ş/g,"s").replace(/ü/g,"u").replace(/[^a-z0-9 ]/g," ").replace(/\s+/g," ").trim();
  const RX_ESKI=/\b(eski|gecmis|biten|bitmis|onceki|arsiv\w*|sonuclanan) kupon\w*|\bkupon (gecmis\w*|arsiv\w*|karne\w*)|\bkupon\w* (istatistig\w*|karnesi|isabet\w*)/;
  const RX_YENI=/\b(yeni|baska|ikinci|bir daha) (bir )?kupon\w*( ac\w*| olustur\w*| baslat\w*| yap\w*)?$|^kupon ac\w*$|\byeni kupon ac\w*/;
  const RX_LAR=/\bkuponlar(im|imi|imda|imin|ima)?\b|\bkac kupon\w*|\btum kupon\w*|\bkuponlarimi goster\b/;
  function kxBot(raw){ const s=NZ(raw); if(!s) return null;
    if(RX_ESKI.test(s)){ const P=past(), S=kxStats(); if(!P.length) return {html:`🏆 Eski KUPO'ların henüz boş${botName()}. KUPO'ndaki tüm maçlar bitince sonuçla birlikte <b>Eski KUPO'larım</b> bölümüne taşınır.`,chips:["KUPO'yu aç","Yeni KUPO","3 maçlık liste yap"]};
      return {html:`🏆 <b>Eski KUPO'larım</b>: ${S.n} sonuçlanan KUPO'dan <b>${S.w}</b> tanesi tuttu (kazanma oranı %${pct(S.n?S.w/S.n:0)}).${S.ni?` Maç bazında ${S.ni} seçimin ${acc(S.ih)} tuttu (%${pct(S.ih/S.ni)}).`:""}${S.n?` OXXai bu KUPO'lara ortalama %${pct(S.predC)} birlikte tutma olasılığı vermişti.`:""}${S.top?` En iyi KUPO'n <b>${esc(S.top.ad)}</b> (toplam oran ${f2(kOdd(S.top))}).`:""}<br><small>Kayıtlar yalnızca bu telefonda. Geçmiş isabet geleceği garanti etmez.</small>`,chips:["Eski KUPO'larım","KUPO'yu aç","Yeni KUPO"]}; }
    if(RX_YENI.test(s)&&!/\d|maclik|ikili|uclu|dortlu|besli|liste/.test(s)){ const c=kxNew(); kxSetActive(c.id); saveL(); kxRefresh();
      return {html:`🏆 Yeni KUPO açtım: <b>${esc(c.ad)}</b>. Bundan sonra eklediğin maçlar buraya gelir; listen şimdilik boş. Toplam ${open().length} açık KUPO'n var.`,chips:["En güvenli 3 maç","3 maçlık liste yap","KUPO'yu aç"]}; }
    if(RX_LAR.test(s)&&!/\b(yatti|tuttu|tutmadi|yandi|patladi)\b/.test(s)){ const L=open(), c0=act();
      return {html:`🏆 ${L.length} açık KUPO'n var${botName()}:<ul class="bt-ul">${L.map(c=>`<li><b>${esc(c.ad)}</b>${c.id===c0.id?" (aktif)":""} · ${c.items.length} maç${c.items.length?` · toplam oran ${f2(kOdd(c))} · OXXai %${pct(kP(c))} · ${ST[kxSt(c)]}`:""}</li>`).join("")}</ul>${past().length?`Eski KUPO'larında ${past().length} KUPO var.`:""} Eklediğin maçlar aktif KUPO'ya gider.`,chips:["KUPO'yu aç","Yeni KUPO","Eski KUPO'larım"]}; }
    return null; }
  window.kxBot=kxBot;
  if(typeof botAnswer==="function"){ const _ba=botAnswer; botAnswer=async function(raw){ try{ const r=kxBot(raw); if(r) return r; }catch(e){}
      const R=await _ba.apply(this,arguments);
      try{ if(R&&typeof R==="object"){ if(Array.isArray(R.chips)) R.chips=[...new Set(R.chips.map(c=>c==="Listeyi aç"?"KUPO'yu aç":c))];
          const c=act(), h=R.html||"";
          if(/📋 Listende <b>/.test(h)){ const odd=kOdd(c), p=kP(c); R.html=h.replace("📋 Listende",`🏆 <b>${esc(c.ad)}</b> · Listende`)+`<br>Toplam oran <b>${f2(odd)}</b> · piyasa olasılığı %${pct(1/odd)} · OXXai birlikte tutma olasılığı <b>%${pct(p)}</b>.${open().length>1?` <small>${open().length} açık KUPO'n var; "KUPO'larım" yaz.</small>`:""}`; }
          else if(/^Listen boş/.test(h)){ R.html=`🏆 <b>${esc(c.ad)}</b> · `+h; R.chips=[...new Set([...(R.chips||[]),"KUPO'yu aç",...(open().length>1?["KUPO'larım"]:[])])]; }
          else if(/listeye eklendi|listeden çıkarıldı|KUPO'ya eklendi|KUPO'dan çıkarıldı|Listeni temizledim/.test(h)) R.html=h+` <small>(${esc(c.ad)})</small>`; } }catch(e){}
      return R; }; }
  document.addEventListener("click",e=>{ const b=e.target.closest("#botChips button[data-q]"); if(!b) return; const t=b.dataset.q;
    const go=tab=>{ e.preventDefault(); e.stopPropagation(); try{ botThen(()=>kxOpen(tab)); }catch(_){ kxOpen(tab); } };
    if(t==="KUPO'yu aç"||t==="Kuponumu aç"||t==="Listeyi aç") return go("cp"); if(t==="Eski KUPO'larım") return go("eski"); },true);
  // ilk boyama
  setTimeout(()=>{ try{ paintCoupon(); }catch(e){} },300);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: kuponum-v95 */
/* id: gollu-v97 */ try {
// v97: gollü skor yalnız Alt/Üst oranı olan maçlarda (oransız maçta gol beklentisi yalnız formdan gelir, şişkin çıkar)
(function(){ try{ const _p=predict; predict=function(inp){ const prev=window.__BX_OU; window.__BX_OU=!!(inp&&inp.odds&&inp.odds.oo&&inp.odds.ou); try{ return _p.apply(this,arguments); } finally{ window.__BX_OU=prev; } }; }catch(e){}
  try{ if(typeof BT!=="undefined"&&BT.cache) BT.cache.clear(); }catch(e){} })();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: gollu-v97 */
/* id: onarim-v100 */ try {
// v100 · Yenile = veriler + program güncellemesi + acil onarım
// • Yeni sürüm varsa: tüm önbellekler silinir, servis çalışanı güncellenir, sayfa önbelleği atlayarak (?v=) yeniden açılır.
// • Yeni servis çalışanı devreye girince sayfa bir kez kendiliğinden yenilenir (iki kez kapat-aç gerekmez).
// • Yenile'ye basılı tut (≈1 sn) ya da Menü → "Uygulamayı onar": tam baştan kurulum (kuponlar ve ayarlar silinmez).
(function(){
  async function bxRepair(nv, hard){
    try{ sessionStorage.setItem("bx-repair", String(Date.now())); }catch(e){}
    try{ if(window.caches){ const ks=await caches.keys(); await Promise.all(ks.map(k=>caches.delete(k))); } }catch(e){}
    try{ if(navigator.serviceWorker&&navigator.serviceWorker.getRegistrations){ const rs=await navigator.serviceWorker.getRegistrations(); await Promise.all(rs.map(r=>hard?r.unregister():r.update().catch(()=>{}))); } }catch(e){}
    location.replace(location.pathname+"?v="+encodeURIComponent(nv||Date.now())+location.hash);
  }
  window.bxRepair=bxRepair;
  try{ const q=new URLSearchParams(location.search); if(q.has("v")){ q.delete("v"); const qs=q.toString(); history.replaceState(null,"",location.pathname+(qs?"?"+qs:"")+location.hash);
      const t=+sessionStorage.getItem("bx-repair")||0; if(t&&Date.now()-t<120000){ sessionStorage.removeItem("bx-repair"); setTimeout(()=>{ try{ toast("✅ Güncel sürüm yüklendi · v"+APP_V.split(".").pop()); }catch(e){} },1500); } } }catch(e){}
  try{ if(navigator.serviceWorker){ let done=false; const had=!!navigator.serviceWorker.controller;
      navigator.serviceWorker.addEventListener("controllerchange",()=>{ if(done||!had) return; done=true;
        const ae=document.activeElement; if(ae&&/^(INPUT|TEXTAREA)$/.test(ae.tagName)) return;   // yazı yazarken yenileme yapma; güncelleme şeridi zaten görünür
        try{ toast("✨ Yeni sürüm yüklendi, yenileniyor…"); }catch(e){} setTimeout(()=>bxRepair(),900); }); } }catch(e){}
  function bind(){ const rf=document.getElementById("hdrRefresh"); if(!rf||rf.dataset.rp) return; rf.dataset.rp="1"; let t=0, fired=false;
    const start=()=>{ fired=false; t=setTimeout(()=>{ t=0; fired=true; try{ buzz(30); toast("🛠️ Acil onarım: uygulama baştan yükleniyor…"); }catch(e){} bxRepair(null,true); },900); };
    const end=()=>{ if(t){ clearTimeout(t); t=0; } };
    rf.addEventListener("pointerdown",start); ["pointerup","pointerleave","pointercancel"].forEach(ev=>rf.addEventListener(ev,end));
    rf.addEventListener("click",e=>{ if(fired){ e.stopImmediatePropagation(); e.preventDefault(); } },true);
    rf.addEventListener("contextmenu",e=>e.preventDefault()); }
  bind(); setTimeout(bind,1500); setTimeout(bind,5000);
  function menu(){ const ml=document.querySelector("#v-more .mlist"); if(!ml||document.getElementById("moreFix")) return; const c=document.createElement("button"); c.className="cell"; c.id="moreFix"; c.type="button";
    c.innerHTML=`<span class="ic" style="background:linear-gradient(135deg,#3A4A63,#24324A)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/></svg></span><span class="tx"><b>Uygulamayı onar</b><small>Sürüm ${APP_V.split(".").pop()} · takılırsa en yeni sürümü baştan yükler; KUPO'ların ve ayarların silinmez</small></span><span class="ar">›</span>`;
    c.onclick=()=>{ try{ toast("🛠️ Onarılıyor…"); }catch(e){} bxRepair(null,true); }; ml.appendChild(c); }
  menu(); setTimeout(menu,1600); setTimeout(menu,5200);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: onarim-v100 */
/* id: kupo-canli-v101 */ try {
// v101 · KUPO'da canlı maç: başlamış maç canlı tahminle eklenebilir; kupondaki canlı maçlarda dakika, skor ve OXXai'nin o anki olasılığı
(function(){
  const LV=()=>(typeof IDL!=="undefined"&&IDL.live&&IDL.live[1])||[];
  function liveFor(x){ return LV().find(m=>(x.iid&&String(m.id)===String(x.iid))||(tmEq(m.h,x.h)&&tmEq(m.a,x.a)))||null; }
  // maç öncesi "U"/"A" kalemi 2,5 çizgisidir: yalnız canlı çizgi 2,5 iken eşleşir; değilse null → "canlı tahmin bekleniyor"
  function nowP(m,mk){ try{ const P=idlPred(m), K=idlPick(m,P); if(!K) return null; const key=k=>(k==="U"||k==="A")?k+String(P.line):k;
      let want=String(mk); if(want==="U"||want==="A") want+="2.5";
      const c=K.all.find(z=>key(z.k)===want); if(!c) return null; return typeof liveCal==="function"?Math.min(.99,liveCal(c.p).p):c.p; }catch(e){ return null; } }
  function deco(){ try{ const box=document.getElementById("cpBox"); if(!box) return; const I=CP.items||[];
      box.querySelectorAll(".cprow[data-cpi]").forEach(r=>{ const x=I[+r.dataset.cpi]; const old=r.querySelector(".kx-lv"); if(old) old.remove(); if(!x||x.ok!=null) return;
        const m=liveFor(x); if(!m) return; const pn=nowP(m,x.mk), l=r.querySelector(".l")||r;
        const d=document.createElement("div"); d.className="kx-lv";
        const ck=(()=>{ try{ return idlClockTxt(m); }catch(e){ return "canlı"; } })();
        d.innerHTML=`<span class="d">${esc(ck)} · ${m.hs}-${m.as}</span>`+(pn!=null?`<span class="n">OXXai şimdi <b class="${pn<(x.p||0)-.03?"dn":""}">%${Math.round(pn*100)}</b>${x.p?` · eklerken %${Math.round(x.p*100)}`:""}</span>`:`<span class="n">canlı tahmin bekleniyor</span>`);
        l.appendChild(d); }); }catch(e){} }
  window.kxLiveDeco=deco;
  try{ const _r=renderKupon; renderKupon=function(){ const r=_r.apply(this,arguments); deco(); return r; }; }catch(e){}
  try{ const _k=window.kxRefresh; if(_k) window.kxRefresh=function(){ const r=_k.apply(this,arguments); deco(); return r; }; }catch(e){}
  try{ new MutationObserver(()=>{ const b=document.getElementById("cpBox"); if(b&&!b.querySelector(".kx-lv")&&(CP.items||[]).some(x=>x.ok==null&&liveFor(x))) deco(); }).observe(document.getElementById("cpBox")||document.body,{childList:true,subtree:false}); }catch(e){}
  const tms=d=>{ const t=Date.parse(d instanceof Date?d.toISOString():d); return isNaN(t)?0:t; };
  setInterval(()=>{ try{ const v=document.getElementById("v-kupon"); if(!v||v.hidden||document.hidden) return; if(!(CP.items||[]).some(x=>x.ok==null&&(x.live||(tms(x.dt)&&tms(x.dt)<Date.now())))) return;
      if(typeof IDL!=="undefined"&&IDL.load) IDL.load(1).then(deco).catch(()=>{}); }catch(e){} },20000);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: kupo-canli-v101 */
