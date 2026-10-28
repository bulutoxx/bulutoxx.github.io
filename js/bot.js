/* id: bot-v69 */ try {
// =====================================================================
// OXXai v69: OXXai 2.0 — daha iyi anlayan, hatırlayan ve somut cevap veren sohbet asistanı (tamamen telefonda, yapay zekâ servisi yok)
// • Anlama: Türkçe karaktersiz yazım, kısaltma/argo (yrn, bgn, eyw, kpn), takım lakapları (cimbom, fener, bjk, barça, juve…), derbi / El Clásico
// • Tarih: cumartesi, 2 gün sonra, öbür gün, 27 ekim, 31.10, hafta sonu, bu hafta
// • Beceriler: en güvenli N maç, 🥇 Altın / Hazır tahminler, maç analizi (1X2, skor, İY, KG, alt/üst), olasılığı en yüksek liste,
//   listeye sıra ile ekle/çıkar ("2.sini ekle", "ilkini çıkar", "listeyi temizle"), karne/isabet, terim sözlüğü, uygulama yardımı
// • Bağlam: son konuşulan maç / gün / lig / liste hatırlanır ("peki yarın?", "kg var mı?", "neden?", "bunu ekle", "başka")
// • Dürüstlük: tüm rakamlar uygulamadaki gerçek veriden; uydurma istatistik yok; tahmin garanti değildir
// Mevcut fonksiyonlar sarmalanır; anlayamadığı mesajı eski zincire (🧠 Akıllı mod dahil) devreder.
// =====================================================================
(function(){
  if(typeof botAnswer!=="function") return;
  const V=window.BOT69={};
  BOT.v69=BOT.v69||{};
  // ---------- metin ----------
  const N=s=>String(s||"").toLocaleLowerCase("tr").replace(/ç/g,"c").replace(/ğ/g,"g").replace(/ı/g,"i").replace(/ö/g,"o").replace(/ş/g,"s").replace(/ü/g,"u")
    .normalize("NFD").replace(/[̀-ͯ]/g,"").replace(/[^a-z0-9]+/g," ").trim();
  const fold=s=>N(s).replace(/ /g,"");
  // kısaltma / argo / lakap → standart yazım (kelime başında, Türkçe ekleriyle: "fenerin", "gsnin", "cimbomun")
  const SL={yrn:"yarın",yarn:"yarın",yarim:"yarın",bgn:"bugün",bugn:"bugün",bgun:"bugün",mc:"maç",mclar:"maçlar",maclr:"maçlar",macl:"maçlar",mclr:"maçlar",
    kpn:"kupon",kupn:"kupon",kpon:"kupon",eyw:"eyvallah",eyv:"eyvallah",eywallah:"eyvallah",tsk:"teşekkür",tskler:"teşekkürler",tsklr:"teşekkürler",tsks:"teşekkürler",sgl:"sağol",sglm:"sağol",
    slm:"selam",slmlar:"selamlar",mrb:"merhaba",mrhb:"merhaba",mrhaba:"merhaba",nbr:"naber",cnli:"canlı",tahmn:"tahmin",thmn:"tahmin",bnk:"banko",nsl:"nasıl",nasi:"nasıl",
    pzt:"pazartesi",prs:"perşembe",cmt:"cumartesi",cts:"cumartesi",crs:"çarşamba",gvnli:"güvenli",guvnli:"güvenli",
    gs:"galatasaray",cimbom:"galatasaray",galatasray:"galatasaray",galatsaray:"galatasaray",glatasaray:"galatasaray",galata:"galatasaray",
    fb:"fenerbahçe",fener:"fenerbahçe",fenerbahce:"fenerbahçe",fenerbace:"fenerbahçe",kanarya:"fenerbahçe",
    bjk:"beşiktaş",besiktas:"beşiktaş",besiktaş:"beşiktaş",kartal:"beşiktaş",ts:"trabzonspor",trabzon:"trabzonspor",ibfk:"başakşehir",basaksehir:"başakşehir",
    barca:"barcelona",barça:"barcelona",barsa:"barcelona",barselona:"barcelona",barcelonanin:"barcelona",juve:"juventus",munih:"bayern",bvb:"dortmund",
    psg:"paris saint germain",manu:"manchester united",mancity:"manchester city",realmadrid:"real madrid",
    aslan:"galatasaray",aslanlar:"galatasaray",sarikirmizi:"galatasaray",sarilacivert:"fenerbahçe",karakartal:"beşiktaş",bordomavi:"trabzonspor",
    marsilya:"marseille",monako:"monaco",lil:"lille",sevilya:"sevilla",valensiya:"valencia",vilyareal:"villarreal",atletiko:"atletico",celsi:"chelsea",çelsi:"chelsea",
    mancester:"manchester",mançester:"manchester",totenham:"tottenham",tottenam:"tottenham",liverpul:"liverpool",benfika:"benfica",ayaks:"ajax",feyenord:"feyenoord",
    lizbon:"lisbon",napoli:"napoli",juventus:"juventus",leverkuzen:"leverkusen",dortmunt:"dortmund",bayernmunih:"bayern"};
  const SL_SUF=["","in","un","nin","nun","e","a","ye","ya","de","da","den","dan","te","ta","ten","tan","i","u","yi","yu","li","lu","ci","cu","la","le","yla","yle","nda","nde","ndan","nden"];
  const PH=[[/\bman\s+utd\b|\bman\s+united\b/g,"manchester united"],[/\bman\s+city\b/g,"manchester city"],[/\bel\s*clasico\b|\bel\s*klasiko\b|\belclasico\b/g,"barcelona real madrid"],[/\bbayern\s+munih\b/g,"bayern"],[/\bsari\s+kirmizi\w*/g,"galatasaray"],[/\bsari\s+lacivert\w*|\bsari\s+kanarya\w*/g,"fenerbahce"],[/\bkara\s+kartal\w*|\bsiyah\s+beyaz\w*/g,"besiktas"],[/\bbordo\s+mavi\w*/g,"trabzonspor"]];
  V.rewrite=function(raw){ let out=String(raw||"").split(/(\s+)/).map(w=>{ if(!w.trim()) return w; const n=N(w); if(!n||n.includes(" ")) return w;
      if(SL[n]) return SL[n];
      for(const k in SL){ if(k.length>=3&&n.startsWith(k)&&SL_SUF.includes(n.slice(k.length))&&!/\d/.test(k)) return SL[k]; }
      return w; }).join("");
    let s=N(out); for(const [re,to] of PH) s=s.replace(re,to);
    return {raw:out, s}; };
  // ---------- tarih ----------
  const DAYMS=864e5, d0=d=>Date.parse(d+"T00:00:00+03:00"), today=()=>istDay(new Date());
  const addD=(d,k)=>istDay(new Date(d0(d)+k*DAYMS+12*3600e3));
  const wdOf=d=>new Date(d0(d)+12*3600e3).getUTCDay();
  const dLbl=d=>d===today()?"Bugün":d===addD(today(),1)?"Yarın":ist(new Date(d0(d)+12*3600e3),{day:"numeric",month:"long",weekday:"long"});
  const MON={ocak:1,subat:2,mart:3,nisan:4,mayis:5,haziran:6,temmuz:7,agustos:8,eylul:9,ekim:10,kasim:11,aralik:12};
  const NUMW={bir:1,iki:2,uc:3,dort:4,bes:5,alti:6,yedi:7};
  const WD=[["pazartesi",1],["sali",2],["carsamba",3],["persembe",4],["cumartesi",6],["cuma",5],["pazar",0]];
  V.day=function(s,raw){ const now=Date.now(), T=today(), mk=(d,key)=>({key:key||"d",d,from:Math.max(now,d0(d)),to:d0(d)+DAYMS,label:dLbl(d)});
    if(/\b(obur gun|ertesi gun|yarindan sonra)\b/.test(s)) return mk(addD(T,2));
    let r=/\b(\d{1,2}|bir|iki|uc|dort|bes|alti|yedi)\s*gun\s*sonra\w*/.exec(s); if(r){ const k=NUMW[r[1]]||+r[1]; if(k>=1&&k<=14) return mk(addD(T,k)); }
    r=/\b(\d{1,2})\s*(ocak|subat|mart|nisan|mayis|haziran|temmuz|agustos|eylul|ekim|kasim|aralik)\b/.exec(s);
    let dotted=false;
    if(!r){ const q=/(?:^|[^\d.,])(\d{1,2})[.\/](\d{1,2})(?:[.\/](\d{2,4}))?(?![\d.,]*\d)/.exec(String(raw||"")); if(q&&+q[2]>=1&&+q[2]<=12&&!(+q[2]===5&&+q[1]<=4)){ r=[0,q[1],+q[2]]; dotted=true; } }
    if(r){ const mo=typeof r[2]==="number"?r[2]:MON[r[2]], dd=+r[1], y=+T.slice(0,4); if(dd>=1&&dd<=31&&mo){ let d=`${y}-${String(mo).padStart(2,"0")}-${String(dd).padStart(2,"0")}`;
        if(d0(d)<d0(T)-40*DAYMS) d=`${y+1}${d.slice(4)}`; const diff=(d0(d)-d0(T))/DAYMS; if(diff>=0&&diff<=30) return mk(d); if(diff<0&&!dotted) return {key:"past",d,label:dLbl(d)}; } }
    if(/\bhafta ?sonu\w*/.test(s)){ const w=wdOf(T); if(w===0) return Object.assign(mk(T),{label:"Hafta sonu (bugün)"}); const sat=w===6?T:addD(T,6-w); return {key:"hs",from:Math.max(now,d0(sat)),to:d0(sat)+2*DAYMS,label:"Hafta sonu"}; }
    if(/\bbu hafta\b/.test(s)) return {key:"hafta",from:now,to:now+7*DAYMS,label:"Bu hafta"};
    for(const [w,n] of WD){ const re=w==="pazar"?/\bpazar(?!tesi)(\s+(gunu|aksami|maclari|maci|icin|gunku|ki)|$|\s*\?)/:w==="cuma"?/\bcuma(?!rtesi)\w*/:new RegExp("\\b"+w+"\\w*"); if(re.test(s)){ const k=(n-wdOf(T)+7)%7; return mk(addD(T,k)); } }
    if(/\byarin\w*/.test(s)) return Object.assign(mk(addD(T,1),"yarin"));
    if(/\b(bu aksam|bu gece|aksam|gece)\b/.test(s)){ const W=botWindow("aksam"); return {key:"aksam",from:W.from,to:W.to,label:"Bu akşam"}; }
    if(/\bbugun\w*|\bbu gun\b/.test(s)) return Object.assign(mk(T,"bugun"));
    return null; };
  // ---------- varlıklar ----------
  const STOPW=new Set(("mac maci macin macini maclari maclar maclarin maclarini macta macinda macindan macina maclik maclarda ne zaman olur mu mi mi misin musun kazanir kazanacak kazanan kazanmasi kim kac biter bitecek bitirir skor skoru skorlar "+
    "tahmin tahmini tahminler tahminleri tahminin analiz analizi yorum yorumu sence gol goller gollu golsuz var yok kg ust alt ilk yari yarida yarisi iy ms oran orani oranli oranlar liste listeye listeden listem listemi kupon kupona kupondan kuponum ekle cikar sil "+
    "neden niye bunu bunun sunu peki olsun icin hangi hangisi hangileri guvenli saglam banko kesin altin hazir bugun bugunku yarin yarinki aksam gece hafta sonu sonra gun gunu "+
    "pazartesi sali carsamba persembe cuma cumartesi pazar ocak subat mart nisan mayis haziran temmuz agustos eylul ekim kasim aralik lig ligi ligde ligden ligin super premier canli live "+
    "oxxai oxx bulut bulutox bulutoxx selam merhaba naber ver oner onerir goster yap hazirla oynar oynayalim nasil nedir demek uygulama yardim takim takimi ev sahibi deplasman beraberlik berabere "+
    "favori yener yenilir kaybeder durum olacak olsa acaba bana bize lutfen abi kanka hocam reis bro dostum ile vs karsi karsisinda derbi derby clasico ilk yari devre ikinci "+
    "tahmininiz ihtimal ihtimali olasilik olasiligi yuzde garanti dur hadi bakalim bak bakar mi musun misin ver verir ister istiyorum oyna oynanir oynanacak program fikstur bulten "+
    "oynanan oynaniyor devam eden suan simdi ici icinde skorlar skorlari neler gore hangileri hangisi sirada siradaki tane adet olan olanlar gunun gunku ust alt ustu alti "+
    "bunlar bunlari onlar sence nedir hepsi hepsini tumu toplam civari civarinda kadar olsun olmasin uzerinde altinda").split(" "));
  function stopSet(){ if(V._stop) return V._stop; const S=new Set(STOPW); try{ for(const k of Object.keys(BOT_LG)) N(k).split(" ").forEach(w=>S.add(w)); for(const c of nluCountries()) S.add(c); }catch(e){} try{ NLU_STOP.forEach(w=>S.add(w)); }catch(e){} V._stop=S; return S; }
  const TOP=new Set(["tr1","tr2","en","es","it","de","fr","pt","nl","ucl","uel","uecl","be"]);
  const GENX=/\(k\)|\bwomen\b|\bkadin\b|\bu ?1\d\b|\bu ?2\d\b|\bii\b|\breserves?\b| b$/;
  function tTok(name){ try{ return tmTok(name); }catch(e){ return N(name).split(" ").filter(w=>w.length>=3); } }
  function wScore(w,t){ if(w===t) return 3; if(t.startsWith(w)&&(w.length>=5||w.length/t.length>=.75)) return 2;
    if(w.startsWith(t)&&t.length>=4&&t.length/w.length>=.6) return 2; if(w.length>=5&&t.length>=5&&qLev(w,t.slice(0,w.length+1))<=(w.length>=8?2:1)) return 1; return 0; }
  V.teams=function(s){ const S=stopSet(), words=s.split(" ").filter(w=>w.length>=3&&!S.has(w)&&!/^\d+$/.test(w)); if(!words.length) return null;
    const qK=/\bkadin|\(k\)|women/.test(s), now=Date.now(); let best=null;
    for(const m of Pick.list()){ const t=m.dt.getTime(); if(t>now+8*DAYMS) continue;
      const sc=nm=>{ let b=0,bw=null; const T=tTok(nm); for(const w of words) for(const x of T){ const v=wScore(w,x); if(v>b){ b=v; bw=w; } } return [b,bw]; };
      const [hs,hw]=sc(m.h), [as,aw]=sc(m.a); if(!hs&&!as) continue;
      let v=hs+as; if(hs&&as&&hw===aw) v=Math.max(hs,as);
      const both=hs>0&&as>0&&hw!==aw;
      if(s.includes(N(m.h))) v+=1.5; if(s.includes(N(m.a))) v+=1.5;
      if(!qK&&(GENX.test(N(m.h)+" ")||GENX.test(N(m.a)+" ")||/\(k\)/i.test(m.h+m.a))) v-=2.5;
      if(TOP.has(m.lg)) v+=.6;
      if(m.started&&!m.live) v-=.3;
      const cand={m,v,both,hs,as,t};
      if(!best||v>best.v+1e-9||(Math.abs(v-best.v)<1e-9&&t<best.t)) best=cand; }
    if(!best||best.v<2||Math.max(best.hs,best.as)<2&&!best.both) return null;
    return best; };
  V.isTeamWord=function(s){ const S=stopSet(); for(const w of s.split(" ")) if(w.length>=4&&!S.has(w)){ try{ const t=findTeam(w); if(t) return t.name; }catch(e){} } return null; };
  function entities(s,raw){ const toks=s.split(" ").filter(Boolean); let lg=null,cn=null,market=null;
    try{ for(const [k,v] of Object.entries(BOT_LG)) if(LEAGUES[v]&&nluPhrase(toks,N(k))){ lg=v; break; } }catch(e){}
    if(!lg){ try{ const C=nluCountries(), S=stopSet(); for(const t of toks){ if(t.length<4) continue; for(const c of C) if(t.startsWith(c)&&!["super","premier"].includes(t)){ cn=c; break; } if(cn) break; } }catch(e){} }
    try{ for(const [k,phs] of NLU_MK){ if(phs.some(ph=>nluPhrase(toks,ph))){ market=k; break; } } }catch(e){}
    if(/\bkg\b/.test(s)&&!market) market="kg_var";
    if(/\b(ilk yari|iy|devre)\b/.test(s)&&/\bgol\b/.test(s)&&!/\bms\b/.test(s)) market="iy05";
    const low=String(raw||"").toLocaleLowerCase("tr");
    const mp=/%\s?(\d{2})|y[uü]zde\s?(\d{2})/.exec(low); const minP=mp?(+(mp[1]||mp[2]))/100:null;
    if(minP&&(market==="ust"||market==="alt")&&/\b\d{2}\s*(ustu|uzeri|uzerinde|ve ustu|alti)\b/.test(s)&&!/\b2 5\b|\bgol/.test(s)) market=null;
    const od=/oran[ıi]?\s*(\d+(?:[.,]\d+)?)|oranl[ıi]\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*oran/.exec(low.replace(/ı/g,"i")); const target=od?parseFloat((od[1]||od[2]||od[3]).replace(",",".")):null;
    let n=0; const nr=/\b(\d{1,2})\s*(?:l[iu]k?|lik|luk|lı|lü|mac\w*|tane|adet)\b/.exec(s); if(nr) n=+nr[1];
    if(!n){ const WN={tekli:1,ikili:2,uclu:3,dortlu:4,besli:5,altili:6}; for(const t of toks) if(WN[t]){ n=WN[t]; break; } }
    if(!n){ const r=/\b(iki|uc|dort|bes|alti)\s+(mac|tane)/.exec(s); if(r) n=NUMW[r[1]]; }
    if(n>8) n=0;
    let ord=null; const o1=/\b(ilk|ilki|ilkini|ilkine|birinci\w*)\b/.exec(s), o2=/\b(ikinci\w*)\b/.exec(s), o3=/\b(ucuncu\w*)\b/.exec(s), o4=/\b(dorduncu\w*)\b/.exec(s),
      od2=/\b(\d)\s*(?:si|su|sini|sunu|ncisi|nci|inci|uncu|unu|ni|nu|yi|yu|ye|ya|e|a)\b/.exec(s);
    if(od2) ord=+od2[1]-1; else if(o1&&!/\bilk yari/.test(s)) ord=0; else if(o2) ord=1; else if(o3) ord=2; else if(o4) ord=3; else if(/\b(sonuncu\w*|en sondaki)\b/.test(s)) ord=-1;
    return {lg,cn,market,minP,target,n,ord,day:V.day(s,raw)}; }
  // ---------- terim sözlüğü (genel tanımlar + uygulamanın kendi kuralları) ----------
  const pct=x=>`%${Math.round((x||0)*100)}`;
  function karneStr(){ const T=DAILY&&DAILY.toplam; return T&&T.guclu_n?` Kilitli arşivde güçlü (%70+) tahminlerin isabeti <b>${pct(T.guclu_hit)}</b> (${Math.round(T.guclu_hit*T.guclu_n)}/${T.guclu_n}).`:""; }
  const TERMS=[
    ["kgyok",/\bkg yok\b|karsilikli gol yok/,()=>`<b>KG Yok</b>: takımlardan en az biri gol atamaz. 1-0, 0-0, 2-0 tutar; 1-1 tutmaz. Tersi <b>KG Var</b>: iki takımın da en az birer gol atması.`],
    ["kg",/\bkg\b|karsilikli gol|kg var/,()=>`<b>KG Var</b> (karşılıklı gol var): maçta iki takımın da gol atması (her biri en az 1 gol). 1-1, 2-1 tutar; 1-0, 0-0 tutmaz. <b>KG Yok</b> tersidir: en az bir takım gol atamaz.`],
    ["iy05",/\b0 5\b|ilk yari gol/,()=>`<b>İY 0,5 Üst</b>: ilk yarıda en az 1 gol olması. İlk yarı 0-0 biterse tutmaz.`],
    ["u15",/\b1 5\b/,()=>`<b>1,5 Üst</b>: maçta toplam en az 2 gol (1-1, 2-0…). <b>1,5 Alt</b>: en fazla 1 gol.`],
    ["alt",/\b2 5 alt\b|\balt\b|az gol/,()=>`<b>2,5 Alt</b>: maçta toplam <b>en fazla 2 gol</b> olması (0-0, 1-1, 2-0). 3. gol gelirse tutmaz. Tersi <b>2,5 Üst</b>: 3 veya daha fazla gol.`],
    ["ust",/\b2 5\b|\bust\b|bol gol|cok gol/,()=>`<b>2,5 Üst</b>: maçta toplam <b>3 veya daha fazla gol</b> olması (2-1, 3-0, 2-2…). 2 golde kalırsa tutmaz. Tersi <b>2,5 Alt</b>: en fazla 2 gol.`],
    ["iyms",/\biy ?ms\b|\biy\b.*\bms\b|ilk yari.*mac sonu|\b2y\b/,()=>`<b>İY</b> = ilk yarı (ilk 45 dakikanın sonucu), <b>2Y</b> = ikinci yarı, <b>MS</b> = maç sonu (normal süre + uzatma dakikaları). <b>İY/MS</b> ikisini birlikte tahmin eder: ör. <b>1/1</b> = ev sahibi ilk yarıyı da maç sonunu da önde bitirir, <b>X/2</b> = ilk yarı berabere, maçı deplasman kazanır. OXXai'nin "Maç tahmini" ekranı İY · 2Y · MS olasılıklarını ayrı ayrı gösterir.`],
    ["ms",/\bms ?(1|x|2)\b|\bms\b|mac sonucu|\b1x2\b/,()=>`<b>MS 1</b>: ev sahibi kazanır · <b>MS X</b>: beraberlik · <b>MS 2</b>: deplasman takımı kazanır. "MS" maç sonucu demektir (normal süre sonu).`],
    ["cifte",/cifte sans|\b1x\b|\bx2\b/,()=>`<b>Çifte şans</b>: iki sonucu birden kapsar (1X: ev sahibi kaybetmez, X2: deplasman kaybetmez, 12: beraberlik olmaz). OXXai bu pazar için ayrı öneri vermiyor; MS olasılıklarını toplayarak kendin bakabilirsin (ör. 1X = MS 1 + MS X).`],
    ["handikap",/handikap/,()=>`<b>Handikap</b>: bir takıma sanal gol avantajı/dezavantajı verilerek sonuç hesaplanır. OXXai handikap pazarı için tahmin üretmiyor; uydurmamak için bu pazarı önermem.`],
    ["adil",/adil oran/,()=>`<b>Adil oran</b> = 1 ÷ olasılık. Ör. %80 tahminin adil oranı 1,25'tir. Kartlarda oran yoksa "adil" oranı gösteririm; bu bir oyun teklifi değil, olasılığın başka bir yazılışıdır.`],
    ["birlikte",/birlikte tutma|toplam olasilik|liste olasilig/,()=>`<b>Birlikte tutma olasılığı</b>: listedeki tüm tahminlerin aynı anda tutma olasılığı; tek tek olasılıkların çarpımıdır. Ör. %80 × %80 × %80 ≈ %51. Bu yüzden maç eklendikçe hızla düşer; 2-3 maçlık listeler çok daha sık tutar.`],
    ["oran",/\boran\w*/,()=>`<b>Oran</b>, piyasanın bir sonuca biçtiği ödeme katsayısıdır. <b>1 ÷ oran</b> kabaca piyasanın o sonuca verdiği olasılıktır: 1,50 → yaklaşık %67 (şirket marjı dahil, gerçeği biraz daha düşüktür). OXXai'de oranlar bilgi içindir; asıl ölçü <b>tutma olasılığı</b>dır.`],
    ["banko",/banko|kesin mac|garanti mac/,()=>`<b>"Kesin maç"</b> diye bir şey yok. Dürüst olayım: futbolda kesinlik olmaz. OXXai'de en yakın karşılığı <b>Güçlü (%70+)</b> ve <b>🥇 Altın</b> tahminlerdir; onlar bile güven seviyesine göre her 4-5 maçtan birinde tutmayabilir.${karneStr()}`],
    ["altin",/altin/,()=>`<b>🥇 Altın tahmin</b>: OXXai'nin en güvendiği seçim. Kural: olasılık <b>%${Math.round(GOLD.thr*100)}+</b>, oran ${GOLD.omin.toFixed(2).replace(".",",")}–${GOLD.omax.toFixed(2).replace(".",",")} arası, günde en fazla ${GOLD.perDay}. Hak eden maç yoksa rozet verilmez.${GOLD.karne&&GOLD.karne.n?` Kurala uyan geçmiş tahminler: ${GOLD.karne.h}/${GOLD.karne.n} tuttu.`:""}`],
    ["guclu",/guclu/,()=>`<b>Güçlü tahmin</b>: OXXai'nin tutma olasılığını <b>%70 ve üstü</b> gördüğü seçim (🔥 işareti). %58–69 arası "Tahmin", %58 altı "Pas" sayılır.${karneStr()}`],
    ["pas",/\bpas\b/,()=>`<b>Pas</b>: en olası sonucun bile olasılığı <b>%58'in altında</b>; maç dengeli, net tahmin yok. OXXai bu maçları önermez, pas geçmeni söyler.`],
    ["yuzde",/yuzde|olasilik|nasil hesap|neye gore|nereden biliyor|mantig/,()=>`Yüzdeler şöyle çıkar: <b>model</b> (lig gol ortalaması, iç/dış saha gücü, son form) ile <b>piyasa</b> (iddaa oranlarından marjı ayıklanmış olasılık) birleştirilir; sonra maç başlamadan kilitlenen <b>arşivdeki gerçek sonuçlara göre kalibre</b> edilir. Yani %80 dediğim seçimler geçmişte gerçekten yaklaşık %80 tutmuş seviyededir — yine de garanti değildir.`],
    ["skor",/tahmini skor|en olasi skor/,()=>`<b>Tahmini skor</b>: modelin gol beklentisine göre en olası tek skor. Tek bir skorun olasılığı genelde %8-15'tir; o yüzden skoru değil, MS / alt-üst / KG olasılıklarını esas al.`],
    ["kupon",/\bkupon\w*|\bliste\w*|kombine/,()=>`OXXai'de <b>tahmin listesi</b> (KUPO): seçtiğin tahminleri toplar ve <b>birlikte tutma olasılığını</b> hesaplar. Bana "3 maçlık liste yap" dersen olasılığı en yüksek maçlardan kurarım; kartlardaki <b>+ KUPO</b> ile ekler, "listem" ile görürsün.`],
    ["canli",/canli/,()=>`<b>Canlı tahmin</b>: oynanan maçta skor, dakika ve canlı oranlara göre hesaplanan seçimler. "canlı" yazarsan şu an %72+ olanları getiririm; canlı oranlar saniyeler içinde değişir.`],
  ];
  V.term=function(s){ for(const [k,re,f] of TERMS) if(re.test(s)) return {k,html:f()}; return null; };
  // ---------- uygulama yardımı ----------
  const HELP=[
    ["ekle",s=>/(liste|kupon)\w*/.test(s)&&/ekle\w*|ekler/.test(s),()=>`KUPO'ya eklemenin 3 yolu: <ul class="bt-ul"><li>Bültende tahmin oranına dokun (seçili olur).</li><li>Benim kartlarımdaki <b>+ KUPO</b> düğmesi, ya da bana "bunu ekle", "2.sini ekle", "hepsini ekle" yaz.</li><li>Maç sayfasında istediğin seçeneğe dokun.</li></ul>Listen alt menüdeki <b>KUPO</b> sekmesinde; "listem" yazarsan burada da gösteririm.`,["Listeyi aç","3 maçlık liste yap"]],
    ["install",s=>/ana ekran|yukle|kurul|kurar|kurmak|indir|telefona ekle|uygulama olarak/.test(s),()=>`OXXai'yi <b>ana ekrana</b> eklemek için: <ul class="bt-ul"><li><b>Menü › Uygulama › Uygulamayı yükle</b></li><li>iPhone: Safari'de <b>Paylaş</b> › <b>Ana Ekrana Ekle</b></li><li>Android: Chrome menüsü (⋮) › <b>Uygulamayı yükle</b> / Ana ekrana ekle</li></ul>`,["Uygulamayı yükle"]],
    ["bildirim",s=>/bildirim|uyari|\bses\b|titres|alarm|\bayar\w*/.test(s),()=>`Gol uyarısı, ses ve titreşim <b>Menü › Uygulama › Ayarlar</b> bölümünde (ses, titreşim, gol uyarısı, ligler). Takip ettiğin maçlarda gol olunca haber verir.`,["Ayarları aç"]],
    ["karne",s=>/karne|isabet|basari/.test(s),()=>`Tüm isabet bilgisi tek yerde: <b>Menü › Karne › Tahmin karnesi</b> (maç öncesi, canlı, 🥇 Altın ve senin takip ettiklerin). Bana "dünkü karne" ya da "altın tahminler ne kadar tutuyor" da diyebilirsin.`,["Karneyi aç","Dünkü karne"]],
    ["hazir",s=>/altin|hazir/.test(s),()=>`<b>🥇 Hazır tahminler</b>: <b>Menü › Analiz › Maç tahmini yap</b> açılınca en üstte; Bugün / Yarın / takvimden gün seçebilirsin. Bültende de <b>🥇 Altın</b> filtresi var. Bana "altın tahminler" yazman da yeter.`,["Hazır tahminleri aç","Altın tahminler"]],
    ["takip",s=>/sonuc takib|oynadik|takip/.test(s),()=>`Oynadığın listelerin sonucu <b>KUPO › Sonuç takibim</b> sekmesinde otomatik puanlanır; kişisel isabetin de orada.`,["Listeyi aç"]],
    ["feedback",s=>/oneri|gorus|hata|sikayet|geri bildirim/.test(s),()=>`Fikrini veya hata bildirimini <b>Menü › Uygulama › Öneri ve görüşler</b> bölümünden geliştiriciye iletebilirsin.`,["Öneri gönder"]],
    ["brain",s=>/akilli mod|yapay zeka/.test(s),()=>`<b>🧠 Akıllı mod</b>: sohbet penceresinin üstündeki 🧠 düğmesi. Telefonda çalışan açık kaynak bir dil modelini indirir; serbest cümleleri daha iyi anlar. İsteğe bağlıdır; rakamlar yine OXXai motorundan gelir.`,null],
    ["analiz",s=>/analiz|tahmin yap|mac tahmini|iki takim/.test(s),()=>`Ayrıntılı analiz için <b>Menü › Analiz › Maç tahmini yap</b>: iki takımı seç, İY · 2Y · MS olasılıklarını, skor dağılımını ve önerileri görürsün. Bana da yazabilirsin: "Galatasaray Fenerbahçe ne olur", "PSG Lyon KG var mı".`,["Maç tahmini aç"]],
    ["app",s=>/uygulama|oxxai|bulutox|bu ne|ne ise yarar|ne yapar|amaci/.test(s),()=>`<b>OXXai</b> hobi amaçlı bir futbol (ve basketbol) <b>tahmin ve takip</b> uygulamasıdır: bülteni tarar, her maç için model + piyasa birleşik <b>olasılık</b> hesaplar, en güvenilirleri 🥇 Altın / Güçlü diye işaretler, tahmin listeni ve sonuçlarını takip eder, isabetini karnede dürüstçe gösterir. Şans oyunu değildir · 18+`,["Altın tahminler","Dünkü karne","Yardım"]],
  ];
  V.help=function(s){ for(const [k,t,f,ch] of HELP) if(t(s)) return {k,html:f(),chips:ch}; return null; };
  // ---------- dürüstlük notu: ilk seferde açık, sonra kısa ----------
  function note(){ if(!BOT.v69.noted){ BOT.v69.noted=1; return `<div class="bt-note">Olasılıklar OXXai modelinin tahminidir, garanti değildir · 18+</div>`; } return `<small class="v69-g">Tahmindir, garanti değildir.</small>`; }
  // ---------- yardımcılar ----------
  const fxOf=m=>m.src==="fx"?FIXTURES.find(x=>x.lg===m.lg&&x.h===m.h&&x.a===m.a):fxOdds(m);
  const lgOf=(m,f)=>(f&&(f.cn||f.ln))||botLgName(m.lg);
  const when=m=>ist(m.dt,{weekday:"long",hour:"2-digit",minute:"2-digit"});
  function bultenN(W,o){ o=o||{}; return Pick.list().filter(m=>!m.started&&!m.live&&m.dt.getTime()>=W.from&&m.dt.getTime()<W.to&&(!o.lg||m.lg===o.lg)).length; }
  function defWin(E){ return E.day?{from:E.day.from,to:E.day.to}:(E.lg||E.cn)?{from:Date.now(),to:Date.now()+4*DAYMS}:{from:Date.now(),to:Date.now()+36*3600e3}; }
  function whenLbl(E){ return E.day?E.day.label:(E.lg||E.cn)?"Önümüzdeki günlerde":"Önümüzdeki saatlerde"; }
  function lgTxt(E){ return E.lg?botLgName(E.lg):E.cn?E.cn.charAt(0).toLocaleUpperCase("tr")+E.cn.slice(1):""; }
  const MKN={ms1:"MS 1",msx:"beraberlik",ms2:"MS 2",ust:"2,5 Üst",alt:"2,5 Alt",kg_var:"KG Var",kg_yok:"KG Yok",iy05:"İY 0,5 Üst",u15:"1,5 Üst"};
  const cards=L=>`<div class="bt-cards">${L.map(botCard).join("")}</div>`;
  const inCp=x=>CP.items.some(c=>c.k===cpKey(x.m)&&c.mk===x.R.k);
  function addCp(x){ if(inCp(x)) return 0; cpToggle(x.m,x.R.k,+(x.R.o||(1/x.R.cp).toFixed(2)),x.R.cp); try{ botLearnPick(x.m); }catch(e){} return 1; }
  function dayChips(E){ const T=today(); return E.day&&E.day.d===addD(T,1)?["Bugün",dLbl(addD(T,2))]:["Yarın","Cumartesi maçları"]; }
  // iddaa oranı henüz açılmamış ileri günler: yalnız model tahmini (açıkça etiketlenir)
  function modelOnly(W,E){ const out=[]; if(E.market) return out;
    for(const m of Pick.list()){ if(m.live||m.started) continue; const t=m.dt.getTime(); if(t<W.from||t>=W.to) continue; if(E.lg&&m.lg!==E.lg) continue;
      const f=fxOf(m); if(f&&f.odds) continue; if(E.cn&&!N((f&&(f.cn||f.ln)||"")+" "+((LEAGUES[m.lg]||{}).n||"")).includes(E.cn)) continue;
      let p=null; try{ p=quickPred(m,f); }catch(e){} const pm=p&&(p.pm||p.p); if(!pm) continue;
      const R=recOf({H:pm[0],D:pm[1],A:pm[2],o25:p.o25m!=null?p.o25m:p.o25},f); if(!R||R.tier==="w") continue; if(E.minP&&R.cp<E.minP) continue;
      out.push({m,f,R,p,sc:R.cp,mo:true}); }
    return out.sort((a,b)=>b.R.cp-a.R.cp); }
  const MO_NOTE=`<small class="v69-g">Bu maçlar için iddaa oranları henüz açılmadı; aşağıdakiler <b>yalnız OXXai modelinin</b> tahmini (piyasa verisi yok, daha belirsiz). Oranlar açılınca tahminler güncellenir.</small>`;
  // ---------- beceriler ----------
  function sOner(E,more){ const W=defWin(E); let L=botPre(Object.assign({lg:E.lg,cn:E.cn,market:E.market,minP:E.minP},W)); const cnt=bultenN(W,E), what=[lgTxt(E),E.market?MKN[E.market]:"",E.minP?`%${Math.round(E.minP*100)} üstü`:""].filter(Boolean).join(" · ");
    let mo=false; if(L.length<4&&E.day){ const M=modelOnly(W,E); if(M.length){ L=L.concat(M); mo=!botPre(Object.assign({lg:E.lg,cn:E.cn,market:E.market,minP:E.minP},W)).length; } }
    const top=L.slice(more||0,(more||0)+4);
    if(!top.length) return {html:more?`Bu kadar${botName()}; ${whenLbl(E).toLocaleLowerCase("tr")} için daha fazla sağlam seçim yok. Kalitesizi önermem 😎`:`${whenLbl(E)}${what?" ("+esc(what)+")":""} için %58 üstü güvenli tahmin bulamadım${cnt?` (bültende ${cnt} maç var ama hepsi dengeli ya da oransız)`:" — bültende bu aralıkta maç yok"}. Pas geçmek de bir stratejidir 😎`,chips:dayChips(E).concat(["En güvenli maçlar"]),pre:[]};
    return {html:`${more?"Devam ediyorum 👇 sıradaki seçimler":`<b>${esc(whenLbl(E))}</b>${what?" ("+esc(what)+")":""}: ${cnt?`bültendeki ${cnt} maçtan `:""}tutma olasılığı en yüksek ${top.length} seçim 👇`}${top.some(x=>x.mo)?MO_NOTE:""}${cards(top)}${note()}`,
      chips:["Neden bunlar?","Başka","Hepsini ekle","Bunlardan liste yap"],pre:top}; }
  function sSafe(E,more){ const W=E.day?{from:E.day.from,to:E.day.to}:(E.lg||E.cn)?defWin(E):{from:Date.now(),to:Date.now()+48*3600e3}; const minP=E.minP||.70;
    const L=botPre(Object.assign({lg:E.lg,cn:E.cn,market:E.market,minP,minO:1.12},W)).sort((a,b)=>b.R.cp-a.R.cp); const n=Math.min(Math.max(E.n||4,1),8);
    const top=L.slice(more||0,(more||0)+n);
    if(!top.length) return {html:more?`Bu kadar${botName()}, %${Math.round(minP*100)} üstünde başka seçim yok.`:`${E.day?esc(E.day.label)+" ":""}%${Math.round(minP*100)} ve üstü olasılıklı seçim bulamadım${botName()}. Zorlamıyorum — "kesin maç" diye bir şey yok.`,chips:["Altın tahminler","Yarın","Sıradaki maçı öner"],pre:[]};
    const p=top.reduce((a,x)=>a*x.R.cp,1);
    return {html:`${more?"Sıradaki en güvenli seçimler":`🛡️ ${E.day?esc(E.day.label)+" en":"En"} güvenli ${top.length} seçim`} (olasılığa göre sıralı, %${Math.round(minP*100)}+)${lgTxt(E)?" · "+esc(lgTxt(E)):""}:${cards(top)}${top.length>=2?`<div class="bt-tot"><span>Hepsi birlikte tutma olasılığı <b>%${pc9(p)}</b></span></div>`:""}<small>Dürüst not: %80 bile her 5 maçtan birinde tutmaz; "kesin" yok.</small>`,
      chips:["Neden bunlar?","Başka","Hepsini ekle","Altın tahminler"],pre:top}; }
  function sGold(E,raw){ const hz=/hazir/.test(raw); let G=[]; try{ G=[...goldCalc().values()]; }catch(e){}
    G.sort((a,b)=>a.m.dt-b.m.dt); let alt="";
    if(E.day){ const all=G; G=G.filter(x=>x.m.dt.getTime()>=E.day.from&&x.m.dt.getTime()<E.day.to);
      if(!G.length&&all.length){ const nd=istDay(all[0].m.dt); G=all.filter(x=>istDay(x.m.dt)===nd); alt=`${esc(E.day.label)} için Altın tahmin yok; en yakın Altın günü <b>${esc(dLbl(nd))}</b>. `; E=Object.assign({},E,{day:null}); } }
    const k=GOLD.karne&&GOLD.karne.n?` Kurala uyan geçmiş tahminler: <b>${GOLD.karne.h}/${GOLD.karne.n}</b> tuttu.`:"";
    let S=[]; if(hz||!G.length){ try{ const now=Date.now(); S=tpCands().filter(x=>!x.gold&&!goldOf(x.m)&&!x.on&&x.m.dt.getTime()<(E.day?E.day.to:now+36*3600e3)&&x.m.dt.getTime()>=(E.day?E.day.from:now)).sort((a,b)=>b.R.cp-a.R.cp).slice(0,hz?4:3); }catch(e){} }
    const head=`🥇 <b>Altın kuralı</b>: olasılık %${Math.round(GOLD.thr*100)}+, oran ${GOLD.omin.toFixed(2).replace(".",",")}–${GOLD.omax.toFixed(2).replace(".",",")}, günde en fazla ${GOLD.perDay}.${k}`;
    const L=G.slice(0,6).concat(S);
    if(!L.length) return {html:`${head}<br>${E.day?esc(E.day.label)+" için ":"Şu an "}kurala uyan Altın ya da Güçlü tahmin yok. Hak eden yoksa OXXai zorlamaz.`,chips:["Yarın","En güvenli maçlar"],pre:[]};
    return {html:`${alt}${hz?"<b>Hazır tahminler</b> — ":""}${G.length?`${E.day?esc(E.day.label)+" ":""}${G.length} Altın tahmin`:`${E.day?esc(E.day.label)+" ":"Şu an "}Altın tahmin yok; en yakın Güçlü (%70+) tahminler`}${G.length&&S.length?` + ${S.length} Güçlü tahmin`:""} 👇${cards(L)}<small>${head}</small>${note()}`,
      chips:["Hepsini ekle","Neden bunlar?","Altın tahminler ne kadar tutuyor","Hazır tahminleri aç"],pre:L}; }
  function sListe(E,raw){ const n=Math.min(Math.max(E.n||3,2),6), W=defWin(E);
    let L=botPre(Object.assign({lg:E.lg,cn:E.cn,market:E.market,minP:E.minP},W)); const sel=[], seen=new Set();
    if(L.length<n&&E.day) L=L.concat(modelOnly(W,E));
    for(const x of L){ if(sel.length>=n) break; const k=cpKey(x.m); if(seen.has(k)) continue; seen.add(k); sel.push(x); }
    const odd=E.target||/\boran\w*/.test(N(raw))&&/kupon|liste|kombin/.test(N(raw));
    const pre=odd?`OXXai bir şans oyunu aracı değil${botName()}; hedef orana göre liste kurmuyorum. Bunun yerine <b>birlikte tutma olasılığı en yüksek</b> ${n} maçı seçtim:<br>`:"";
    if(sel.length<2) return {html:`${pre}${esc(whenLbl(E))}${lgTxt(E)?" ("+esc(lgTxt(E))+")":""}${E.market?" "+MKN[E.market]:""} için listeye koyacak kadar sağlam maç bulamadım${botName()}. Başka gün ya da lig deneyelim mi?`,chips:dayChips(E).concat(["Canlı"]),pre:[]};
    const p=sel.reduce((a,x)=>a*x.R.cp,1);
    return {html:`${pre}İşte ${sel.length} maçlık tahmin listen${botName()} 📋${sel.some(x=>x.mo)?MO_NOTE:""}${E.day||lgTxt(E)||E.market?` (${esc([E.day?E.day.label:"",lgTxt(E),E.market?MKN[E.market]:""].filter(Boolean).join(" · "))})`:""}${cards(sel)}
      <div class="bt-tot"><span>Birlikte tutma olasılığı <b>%${pc9(p)}</b></span></div><button type="button" class="bt-all" data-ba="all">+ Hepsini KUPO'ya ekle</button>
      ${p<.35?`<div class="bt-note">Dürüst not: ${sel.length} maç birlikte zor tutar (10 listeden ~${trEk(Math.max(1,Math.round(p*10)))}). 2 maçlık liste olasılığı belirgin artırır.</div>`:`<small class="v69-g">10 benzer listeden yaklaşık ${trEk(Math.round(p*10))} tutar; garanti değildir.</small>`}`,
      chips:["Neden bunlar?",`${sel.length>2?2:3} maçlık olsun`,"Hepsini ekle","Yarın için olsun"],pre:sel}; }
  function htft1(r){ const H=r&&r.htft; if(!Array.isArray(H)) return null; const o={1:0,X:0,2:0}; for(const [k,v] of H){ const a=String(k).split("/")[0]; if(a in o) o[a]+=v; } const s=o[1]+o.X+o[2]; return s>.5?[o[1]/s,o.X/s,o[2]/s]:null; }
  function sMatch(m,E,flags){ const f=fxOf(m); let p=null; try{ p=quickPred(m,f); }catch(e){}
    if(!p||!(p.pm||p.p)){ try{ BT.cache.delete(m.lg+"|"+m.h+"|"+m.a+"|"+(MODEL&&MODEL.updated)); p=quickPred(m,f); }catch(e){} }   // veri geç geldiyse önbellekteki boş sonucu at, yeniden hesapla
    const head=`<b>${esc(m.h)} - ${esc(m.a)}</b><br><small>📅 ${esc(when(m))}${istDay(m.dt)!==today()?" · "+esc(ist(m.dt,{day:"numeric",month:"long"})):""} · ${esc(lgOf(m,f))}</small>`;
    if(m.live) return {html:`${head}<br>🔴 Maç şu an oynanıyor${m.hs!=null?`: <b>${m.hs}-${m.as}</b>`:""}. Canlı tahmin için "canlı" yaz ya da maçı aç.`,chips:["Canlı"],pre:[],match:m};
    if(!p||!(p.pm||p.p)) return {html:`${head}<br>Bu maç için tahmin verisi şu an hazır değil (veriler yükleniyor olabilir) ya da yetersiz; tahmin uydurmam 🤷 Birkaç saniye sonra tekrar sor ya da maçı aç.`,chips:[`${m.h} ${m.a}`,"Sıradaki maçı öner"],pre:[],match:m};
    const pm=p.pm||p.p, r=p.r||{}, L=[head];
    L.push(`📊 ${esc(m.h)} <b>%${pc9(pm[0])}</b> · Beraberlik <b>%${pc9(pm[1])}</b> · ${esc(m.a)} <b>%${pc9(pm[2])}</b>`);
    if(p.ft) L.push(`🎯 Tahmini skor <b>${esc(p.ft)}</b>`);
    const fav=pm[0]>=pm[2]?0:2, mx=pm[fav], gap=mx-Math.max(pm[1],pm[2-fav]);
    if(flags.win) L.push(mx>=.55?`🏆 Favori <b>${esc(fav?m.a:m.h)}</b> (%${pc9(mx)}).`:gap<.08?`⚖️ Dengeli maç: favori yok, beraberlik de güçlü ihtimal.`:`🏆 Hafif favori <b>${esc(fav?m.a:m.h)}</b> (%${pc9(mx)}), ama kesin değil.`);
    if(flags.iy){ const h=htft1(r); if(h) L.push(`⏱️ <b>İlk yarı</b>: ${esc(m.h)} önde %${pc9(h[0])} · berabere %${pc9(h[1])} · ${esc(m.a)} önde %${pc9(h[2])}${(()=>{ const t=Array.isArray(r.topH1)&&r.topH1.slice().sort((x,y)=>y.p-x.p)[0]; return t?` · İY'de en olası skor ${esc(t.s)} (%${pc9(t.p)})`:""; })()}${r.h1o05!=null?` · İY'de gol (İY 0,5 Üst) %${pc9(r.h1o05)}`:""}.`); else if(p.ht) L.push(`⏱️ İlk yarı en olası skor ${esc(p.ht)}.`); }
    const pre=[]; let mk=E.market;
    if(flags.gol&&!mk) mk="ust";
    if(mk){ const Rr=mktPick(p,f,mk); if(Rr){ L.push(`${Rr.cp>=.58?"✅":"⚠️"} <b>${esc(Rr.n)}</b>: <b>%${pc9(Rr.cp)}</b>${Rr.o?` (oran ${fO(Rr.o)})`:""}. ${Rr.cp>=.7?"Güçlü görünüyor.":Rr.cp>=.58?"Makul.":Rr.cp>=.45?"Yazı tura gibi, dikkat.":"Olası değil, önermem."}`); if(Rr.cp>=.5) pre.push({m,f,R:Rr,p}); }
      else L.push(`Bu pazar (${esc(MKN[mk]||mk)}) için bu maçta veri yok.`); }
    const R0=recOf({H:pm[0],D:pm[1],A:pm[2],o25:p.o25m!=null?p.o25m:p.o25},f);
    if(R0&&R0.tier!=="w"&&!pre.some(x=>x.R.k===R0.k)) pre.push({m,f,R:R0,p});
    else if(R0&&R0.tier==="w") L.push(`⏸️ Net öneri yok, maç dengeli (en olası ${esc(R0.n)} %${pc9(R0.cp)}). Pas geçmeni öneririm.`);
    else if(R0) L.push(`💡 OXXai önerisi: <b>${esc(R0.n)}</b> %${pc9(R0.cp)}`);
    const P2=pre;
    let html=L.join("<br>");
    if(P2.length) html+=cards(P2);
    html+=note();
    try{ BOT.st.tm[N(m.h)]=(BOT.st.tm[N(m.h)]||0)+.5; BOT.st.tm[N(m.a)]=(BOT.st.tm[N(m.a)]||0)+.5; }catch(e){}
    return {html,chips:["Neden?","KG var mı?","Gol olur mu?","İlk yarı ne olur","Bunu ekle"],pre:P2,match:m}; }
  function sKuponum(s){ const I=CP.items; if(!I.length) return {html:`Listen boş${botName()}. "3 maçlık liste yap" ya da "en güvenli 2 maç" dersen hemen hazırlarım 📋`,chips:["3 maçlık liste yap","En güvenli maçlar"]};
    const p=I.reduce((a,c)=>a*(c.p||.5),1), unk=I.filter(c=>!c.p).length;
    const rows=I.map((c,i)=>`<li>${i+1}. <b>${esc(c.h)} - ${esc(c.a)}</b> · ${esc(mkName(c.mk))}${c.p?` · %${pc9(c.p)}`:""}</li>`).join("");
    const tut=/tutar|tutma|olasilig|kazandirir|gelir mi/.test(s);
    return {html:`📋 Listende <b>${I.length} maç</b> var:<ul class="bt-ul">${rows}</ul>Birlikte tutma olasılığı OXXai'ye göre <b>%${pc9(p)}</b>${unk?` (${unk} seçimin olasılığı bilinmiyor, %50 sayıldı)`:""}.${tut?` Yani 10 benzer listeden yaklaşık <b>${Math.round(p*10)}</b>'${trSfx(Math.round(p*10))} tutar — garanti değil.`:""}${I.length>4?" Çok maçlı liste zor tutar; 2-3 maçta kalmak olasılığı ciddi artırır.":""}`,
      chips:["Listeyi aç","İlkini çıkar","Listeyi temizle"]}; }
  function sEkle(E,s,ctx){ const L=(ctx&&ctx.pre)||[]; if(!L.length) return {html:`Ekleyecek bir öneri yok${botName()}; önce "maç öner", "en güvenli 3 maç" ya da bir takım adı yaz 📋`,chips:["En güvenli maçlar","3 maçlık liste yap"]};
    const all=/\b(hepsi\w*|tumu\w*|hepsini)\b/.test(s); let A;
    if(all) A=L; else { const i=E.ord==null?0:E.ord<0?L.length-1:E.ord; if(!L[i]) return {html:`Son mesajımda ${L.length} öneri vardı; "${E.ord+1}." diye bir sıra yok 🙂`,chips:["Hepsini ekle"]}; A=[L[i]]; }
    let n=0; for(const x of A) n+=addCp(x); try{ paintCoupon(); }catch(e){}
    const nm=A.length===1?` (<b>${esc(A[0].m.h)} - ${esc(A[0].m.a)}</b> · ${esc(A[0].R.n)})`:"";
    return {html:n?`${n} seçim KUPO'ya eklendi 📋${nm} KUPO'nda artık ${CP.items.length} maç var.`:`Bunlar zaten KUPO'nda 😉 KUPO'nda ${CP.items.length} maç var.`,chips:["Listem","Listeyi aç","Neden?"]}; }
  function sCikar(E,s,ctx){ if(!CP.items.length) return {html:`Listen zaten boş 🙂`,chips:["3 maçlık liste yap"]};
    if(/\b(temizle\w*|bosalt\w*|hepsini|tumunu|hepsi)\b/.test(s)){ const n=CP.items.length; CP.items.length=0; cpSave(); return {html:`Listeni temizledim 🧹 ${n} maç çıkarıldı.`,chips:["3 maçlık liste yap","En güvenli maçlar"]}; }
    let idx=-1; const w=s.split(" ").filter(x=>x.length>=4&&!stopSet().has(x));
    if(w.length){ idx=CP.items.findIndex(c=>w.some(x=>tTok(c.h).concat(tTok(c.a)).some(t=>wScore(x,t)>=2))); }
    if(idx<0&&E.ord!=null&&ctx&&ctx.pre&&ctx.pre.length&&!/\blist(em|emde|emdeki)\b/.test(s)){ const x=ctx.pre[E.ord<0?ctx.pre.length-1:E.ord]; if(x) idx=CP.items.findIndex(c=>c.k===cpKey(x.m)); }
    if(idx<0&&E.ord!=null){ const i=E.ord<0?CP.items.length-1:E.ord; if(CP.items[i]) idx=i; }
    if(idx<0) return {html:`Listende hangisini çıkarayım? Takım adını ya da sırasını yaz ("2.sini çıkar"). "listeyi temizle" hepsini siler.`,chips:["Listem","Listeyi temizle"]};
    const c=CP.items.splice(idx,1)[0]; cpSave();
    return {html:`<b>${esc(c.h)} - ${esc(c.a)}</b> (${esc(mkName(c.mk))}) KUPO'dan çıkarıldı. KUPO'nda ${CP.items.length} maç kaldı.`,chips:["Listem","Listeyi aç"]}; }
  async function sKarne(s){ try{ await botGrade(); }catch(e){}
    const T=DAILY&&DAILY.toplam, Lf=typeof lastFull==="function"?lastFull():null, C=DAILY&&DAILY.canli, k=BOT.st.karne||{n:0}, rows=[];
    const yd=istDay(new Date(Date.now()-DAYMS));
    if(Lf){ const g=Lf.guclu&&Lf.guclu.n?Lf.guclu:null; rows.push(`🗓️ <b>${Lf.d===yd?"Dün":esc(dLbl(Lf.d))}</b>: ${Lf.n} öneri, isabet <b>%${Math.round(Lf.hit*100)}</b>${g?` · güçlü (%70+) önerilerde <b>%${Math.round(g.hit*100)}</b> (${Math.round(g.hit*g.n)}/${g.n})`:""}.`); }
    if(T&&T.n&&(!Lf||T.n!==Lf.n)) rows.push(`📒 Kilitli arşivde toplam ${T.n} öneri: <b>%${Math.round(T.hit*100)}</b> tuttu${T.guclu_n?`; güçlülerde <b>%${Math.round(T.guclu_hit*100)}</b>`:""}.`);
    if(GOLD.karne&&GOLD.karne.n) rows.push(`🥇 Altın kuralına uyan geçmiş tahminler: <b>${GOLD.karne.h}/${GOLD.karne.n}</b> tuttu (%${Math.round(GOLD.karne.h/GOLD.karne.n*100)})${GOLD.karne.n<20?" — örnek az, temkinli oku":""}.`);
    else if(/altin/.test(s)) rows.push(`🥇 Altın tahminlerin kilitli arşivde henüz yeterli puanlanmış örneği yok.`);
    if(TP.karne&&TP.karne.n>=10) rows.push(`💪 Güçlü + anlamlı oranlı (${GOLD.omin.toFixed(2).replace(".",",")}–${GOLD.omax.toFixed(2).replace(".",",")}) tahminler, ${TP.karne.g==null?"son 30 gün":TP.karne.g<=1?"şimdilik 1 günlük kilitli kayıt (örnek az)":"son "+TP.karne.g+" günün kilitli kayıtları"}: <b>${TP.karne.h}/${TP.karne.n}</b> tuttu (%${Math.round(TP.karne.h/TP.karne.n*100)}).`);
    if(C&&C.n) rows.push(`🔴 Canlı seçimler: ${C.n} seçimde isabet <b>%${Math.round(C.hit*100)}</b>.`);
    if(k.n) rows.push(`🤖 Sana önerdiklerim: ${Math.round(k.hit*k.n)}/${k.n} tuttu (%${Math.round(k.hit*100)}).`);
    try{ const O=oynStats(); if(O.n) rows.push(`📋 Takip ettiğin listeler: ${O.n} seçimden ${O.h} tanesi tuttu (%${Math.round(O.h/O.n*100)}), ${O.sl} listenin ${trEk(O.slw,"nde")} tüm tahminler tuttu.`); }catch(e){}
    if(!rows.length) return {html:`Henüz puanlanmış öneri yok; maçlar bittikçe kilitli arşivden puanlanıyor 📒`,chips:["Karneyi aç"]};
    return {html:`<b>📒 Karne</b> — tahminler maç başlamadan kilitlenir, sonuçla puanlanır:<ul class="bt-ul">${rows.map(r=>`<li>${r}</li>`).join("")}</ul><small>Geçmiş isabet geleceği garanti etmez.</small>`,chips:["Karneyi aç","Altın tahminler","En güvenli maçlar"]}; }
  function sNeden(E,ctx){ const L=(ctx&&ctx.pre)||[]; const i=E.ord==null?0:E.ord<0?L.length-1:E.ord; const x=L[i];
    if(!x) return null; let h=botWhyHtml(x); if(L.length>1&&E.ord==null) h+=`<br><small>Diğerleri için "2.si neden" yazabilirsin.</small>`; return {html:h,chips:L.length>1?["2.si neden","Bunu ekle","Başka"]:["Bunu ekle","Başka"]}; }
  function sYardim(){ return {html:`Bana böyle yazabilirsin (yazım hatası, kısaltma, Türkçe karaktersiz yazım olsa da anlarım):<ul class="bt-ul">
      <li>📅 <b>bugün / yarın / cumartesi / 2 gün sonra / 31.10</b> maçları</li><li>🛡️ <b>en güvenli 3 maç</b> · <b>%80 üstü</b></li><li>🥇 <b>altın tahminler</b> · <b>hazır tahminler</b></li>
      <li>⚔️ <b>GS FB ne olur</b> · <b>barça maçı</b> · <b>PSG Lyon KG var mı</b> · sonra <b>ilk yarı?</b> <b>kim kazanır?</b></li><li>📋 <b>3 maçlık liste</b> · <b>bunu ekle</b> · <b>2.sini ekle</b> · <b>listem</b> · <b>ilkini çıkar</b> · <b>listeyi temizle</b></li>
      <li>📒 <b>dünkü karne</b> · <b>altın tahminler ne kadar tutuyor</b></li><li>📖 <b>KG var ne demek</b> · <b>oran nedir</b> · <b>2,5 üst</b> · <b>neden?</b></li><li>🔴 <b>canlı</b> · ❔ <b>ana ekrana nasıl eklerim</b></li></ul>`,
      chips:["Bugün hangi maçlar var","En güvenli 3 maç","Altın tahminler","Dünkü karne"]}; }
  function sDerbi(){ const BIG=/^(galatasaray|fenerbahce|besiktas|trabzonspor)/; const now=Date.now();
    return Pick.list().filter(m=>m.dt.getTime()>now-2*3600e3&&m.dt.getTime()<now+8*DAYMS&&BIG.test(N(m.h))&&BIG.test(N(m.a))&&!/\(k\)/i.test(m.h+m.a)).sort((a,b)=>a.dt-b.dt)[0]||null; }
  // ---------- niyet ----------
  const RX={
    kayip:/\b(yatti\w*|yandi\w*|batti\w*|tutmadi\w*|kaybet\w*|patladi\w*|kazandim|vurdum|hepsi tuttu|kuponum tuttu|tuttu ya)\b/,
    terim:/\b(ne demek\w*|nedir|ne anlama|anlami\w*|ne ifade|aciklar misin|acikla\w*|ne demektir|nasil hesap\w*|neye gore|manasi|nereden biliyor\w*|mantigi)\b/,
    help:/\b(nerede|nereden|nereye|ne ise yarar|ne yapar|hangi menu|bulamiyorum|acamiyorum)\b|\bnasil\b.*\b(acil|acar|ac|ekle|eklen|kur|yukle|kullan|bul|gor|yapil|yapar|degis|kapat|ayarla)\w*/,
    cikar:/\b(cikar\w*|cikart\w*|sil|silin|sileyim|kaldir\w*|temizle\w*|bosalt\w*)\b/,
    ekle:/\bekle\w*\b/,
    kuponum:/\b(kuponum\w*|listem\w*|kuponumu|kuponumdaki|kupon(um)? tutar)\b/,
    karne:/\b(karne\w*|isabet\w*|basari\w*|performans\w*|tutuyor mu|tutuyormu|tuttu mu|kac (mac |tane )?tut\w*|ne kadar tut\w*|tutma oran\w*|tutturuyor|gecmis\w*|dun ne yaptin|nasil gitti|nasil gecti|ne kadar dogru|dogruluk\w*|isabetli mi|guvenilir mi|guvenebilir miyim)\b/,
    neden:/\b(neden|niye|nicin|gerekce\w*|sebep\w*)\b/,
    canli:/\b(canli\w*|live|su an|suan|simdi oynanan|oynanan|oynaniyor|devam eden|mac ici|kac kac|canli skor\w*)\b/,
    win:/\b(kim kazan\w*|kazanir\w*|kazanacak|kazanan|favori\w*|yener|galip)\b/,
    iy:/\b(ilk yari\w*|\biy\b|devre\w*)\b/,
    gol:/\b(gol olur\w*|gol olacak|gollu|gol cikar\w*|bol gol|kac gol)\b/,
    altin:/\b(altin\w*|hazir tahmin\w*)\b/,
    liste:/\b(kupon\w*|liste\w*|kombine\w*|kombin)\b|\b\d\s*(l[iu]k?|lik|luk)\b|\b\d+\s*maclik\b|\b(ikili|uclu|dortlu|besli)\b/,
    safe:/\b(en guvenli\w*|en saglam\w*|banko\w*|kesin\w*|garanti\w*|yatmaz|guvenli\w*|saglam\w*|en emin|en garanti)\b/,
    oner:/\b(mac\w*|tahmin\w*|oner\w*|bulten\w*|ne oynay\w*|neler var|ne var|program\w*|fikstur\w*|oyna\w*|firsat\w*)\b/,
    more:/^(baska\w*|diger\w*|daha|devam\w*|sonraki\w*|baska var mi|daha var mi)\b/,
    next:/\b(sirad\w*|en yakin mac\w*|ilk mac)\b/,
    yardim:/^(yardim\w*|help|neler yapabilirsin\w*|ne yapabilirsin\w*|komutlar|ne biliyorsun)\b/,
    mode:/\b(mod\w*|risk\w*|cesur|surpriz\w*|yuksek oran\w*)\b/,
    derbi:/\b(derbi\w*|derby)\b/,
    sel:/^(selam\w*|merhaba\w*|naber|gunaydin|iyi aksamlar|iyi geceler|hey|sa|slm|selamun|hello|hi|alo)\b/,
  };
  const OFF=/\b(hava\w*|yagmur|kar yag\w*|yemek|pizza|tarif|film|dizi|muzik|sarki|siyaset|secim|borsa|dolar|euro kur|altin fiyat\w*|bitcoin|kripto|seviyorum|sevgili|ask|evlen\w*|okul|odev|saat kac)\b/;
  const FOOT=/\b(mac\w*|tahmin\w*|kupon\w*|liste\w*|gol\w*|lig\w*|takim\w*|oran\w*|banko|skor\w*|bulten|kg|ust|alt|iddaa)\b/;
  V.parse=function(raw,ctx){ const W=V.rewrite(raw), s=W.s; if(!s||!/[a-z]{2}/.test(s)) return null;
    if(RX.kayip.test(s)||/\b(adim|ismim)\b/.test(s)) return null;
    const E=entities(s,W.raw); const I=(t,o)=>Object.assign({t,E,s},o||{});
    if(RX.sel.test(s)&&s.split(" ").length<=3&&!/\b(mac|tahmin|kupon|liste)\w*/.test(s)) return I("selam");
    if(OFF.test(s)&&!FOOT.test(s)) return I("konudisi");
    if(RX.yardim.test(s)) return I("yardim");
    if(RX.terim.test(s)){ const t=V.term(s); if(t) return I("terim",{term:t}); }
    if(RX.help.test(s)&&!RX.win.test(s)&&!/\bne olur\b/.test(s)){ const h=V.help(s); if(h) return I("apphelp",{help:h}); }
    if(RX.cikar.test(s)&&!/\bgol\b/.test(s)&&(/\b(list|kupon)\w*/.test(s)||E.ord!=null||(ctx&&ctx.pre)||CP.items.length)) return I("cikar");
    if(RX.ekle.test(s)) return I("ekle");
    if(RX.kuponum.test(s)) return I("kuponum");
    if(RX.karne.test(s)) return I("karne");
    if(RX.neden.test(s)&&ctx&&ctx.pre&&ctx.pre.length) return I("neden");
    if(RX.next.test(s)&&!E.day) return null;   // "sıradaki maç": eski motor saat sırasıyla verir
    let TM=V.teams(s); if(!TM&&RX.derbi.test(s)){ const m=sDerbi(); if(m) TM={m}; }
    const flags={win:RX.win.test(s),iy:RX.iy.test(s),gol:RX.gol.test(s)};
    if(TM) return I("analiz",{m:TM.m,flags});
    if(RX.canli.test(s)) return I("canli");
    if(ctx&&ctx.match&&(E.market||flags.win||flags.iy||flags.gol)&&!E.day&&!E.lg&&!E.cn) return I("analiz",{m:ctx.match,flags});
    if(RX.mode.test(s)&&!RX.safe.test(s)) return null;
    const s2=s.replace(/\b\d+\s*mac\w*/g," "), explicit=RX.oner.test(s2)||RX.safe.test(s2)||RX.altin.test(s2)||/\b(kupon\w*|liste\w*|kombin\w*)\b/.test(s2);
    const ent=!!(E.day||E.lg||E.cn||E.n||E.market||E.minP);
    if(ctx&&ctx.kind&&ent&&!explicit&&!/\b(maclari|maclar)\b/.test(s)) return I("follow");
    if(ctx&&ctx.kind&&RX.more.test(s)) return I("more");
    if(RX.altin.test(s)) return I("altin");
    if(RX.liste.test(s)||E.target) return I("liste");
    if(RX.safe.test(s)||E.minP) return I("guvenli");
    if(E.day&&E.day.key==="past") return I("past");
    if(RX.oner.test(s)||E.day||E.lg||E.cn||E.market) return I("oner");
    const tw=V.isTeamWord(s); if(tw) return I("yokmac",{team:tw});
    return null; };
  // ---------- cevap ----------
  async function run(I,raw,ctx){ const E=I.E, s=I.s; let R=null, kind=null, keep=null;
    switch(I.t){
      case "yardim": R=sYardim(); break;
      case "selam": { const R0=await V.prev("selam"); return R0; }
      case "konudisi": R={html:`Ben yalnızca futbol tahminlerinde iyiyim${botName()} ⚽ Bu konuda yardımcı olamam ama maçlarla ilgili her şeyi sorabilirsin.`,chips:["Bugün hangi maçlar var","En güvenli 3 maç","Yardım"]}; break;
      case "terim": R={html:`📖 ${I.term.html}`,chips:["Altın tahminler","En güvenli maçlar","Başka bir terim: oran nedir"]}; break;
      case "apphelp": R={html:I.help.html,chips:I.help.chips||["Yardım"]}; break;
      case "cikar": R=sCikar(E,s,ctx); keep=1; break;
      case "ekle": R=sEkle(E,s,ctx); keep=1; break;
      case "kuponum": R=sKuponum(s); break;
      case "karne": R=await sKarne(s); break;
      case "neden": R=sNeden(E,ctx); if(!R) return null; keep=1; break;
      case "analiz": R=sMatch(I.m,E,I.flags); kind="analiz"; break;
      case "canli": { let pre="";
        if(/kac kac|skor/.test(s)){ const L=Pick.list().filter(m=>m.live).slice(0,8);
          pre=L.length?`🔴 Canlı skorlar:<ul class="bt-ul">${L.map(m=>`<li><b>${esc(m.h)} ${m.hs??"-"}-${m.as??"-"} ${esc(m.a)}</b>${m.clock?` · ${esc(m.clock)}`:""}</li>`).join("")}</ul>`:`Şu an skorunu gösterebileceğim canlı maç yok. `; }
        const R0=await V.prev("canlı"); R=Object.assign({},R0,{html:pre+(R0.html||"")}); BOT.ctx=Object.assign({},BOT.ctx||{},{kind:null}); return R; }
      case "altin": R=sGold(E,s); kind="altin"; break;
      case "liste": R=sListe(E,raw); kind="liste"; break;
      case "guvenli": R=sSafe(E); kind="guvenli"; break;
      case "oner": R=sOner(E); kind="oner"; break;
      case "past": R={html:`${esc(E.day.label)} geçmişte kaldı; o günün sonuçları için <b>Sonuçlar</b>a, isabet için karneye bak. "dünkü karne" de yazabilirsin.`,chips:["Sonuçlar","Dünkü karne"]}; break;
      case "yokmac": R={html:`<b>${esc(I.team)}</b> için önümüzdeki 8 günde bültende maç bulamadım${botName()} 🤷 Maç eklenince sorarsan hemen analiz ederim.`,chips:["Bugün hangi maçlar var","Yarın"]}; break;
      case "follow": case "more": { const c=ctx; const E2={day:E.day||c.E.day,lg:E.lg||(E.cn?null:c.E.lg),cn:E.cn||(E.lg?null:c.E.cn),n:E.n||c.E.n,market:E.market||c.E.market,minP:E.minP||c.E.minP,target:null};
        const more=I.t==="more"?(c.more||0)+(c.kind==="guvenli"?(c.E.n||4):4):0; kind=c.kind==="analiz"?"oner":c.kind;
        R=kind==="liste"?sListe(E2,""):kind==="guvenli"?sSafe(E2,more):kind==="altin"?sGold(E2,""):sOner(E2,more);
        BOT.ctx={t:kind==="liste"?"kupon":"oner",kind,E:E2,more,pre:R.pre||[],day:E2.day&&["bugun","yarin","aksam"].includes(E2.day.key)?E2.day.key:undefined,lg:E2.lg,cn:E2.cn,n:E2.n,market:E2.market};
        if(R.pre&&R.pre.length) try{ botRemember(R.pre); }catch(e){}
        return {html:R.html,chips:R.chips,ctx:{pre:R.pre||[]}}; }
    }
    if(!R) return null;
    if(kind){ BOT.ctx={t:kind==="liste"?"kupon":kind==="analiz"?"takim":"oner",kind,E,more:0,pre:R.pre||[],match:R.match||null,L:R.match?[R.match]:undefined,
        day:E.day&&["bugun","yarin","aksam"].includes(E.day.key)?E.day.key:undefined,lg:E.lg,cn:E.cn,n:E.n,market:E.market};
      if(R.pre&&R.pre.length) try{ botRemember(R.pre); }catch(e){} }
    else if(!keep&&R.pre) BOT.ctx=Object.assign({},BOT.ctx||{},{pre:R.pre});
    return {html:R.html,chips:R.chips||null,ctx:R.pre?{pre:R.pre}:(ctx&&keep?{pre:ctx.pre||[]}:null)}; }
  // ---------- anlaşılmayan mesaj: tahmin yürüt ve öneri çipleri sun ----------
  function fallback(raw,R){ const s=V.rewrite(raw).s, ch=[];
    if(/gol|kg|ust|alt/.test(s)) ch.push("Gol olacak maçlar"); if(/kupon|liste/.test(s)) ch.push("3 maçlık liste yap"); if(/takim|lig/.test(s)) ch.push("Süper Lig maçları");
    ["Bugün hangi maçlar var","En güvenli 3 maç","Altın tahminler","Yardım"].forEach(x=>{ if(ch.length<4&&!ch.includes(x)) ch.push(x); });
    return Object.assign({},R,{html:`Bunu tam anlayamadım${botName()} 🤔 Şunlardan birini mi demek istedin? Bir takım adı (ör. <b>"barça maçı"</b>), bir gün (<b>"cumartesi"</b>) ya da <b>"KG var ne demek"</b> gibi bir soru da yazabilirsin.`,chips:ch}); }
  // ---------- bağlama ----------
  const _prev=botAnswer; V.prev=q=>_prev(q);
  // quickPred zaman bütçeli: önbellek soğukken 250 ms'den sonra null döner ve hesaplamayı erteler.
  // Sohbet cevabı eksik kalmasın diye cevap hesaplanırken tam hesap zorlanır (QP_FORCE), sonra eski haline döner.
  botAnswer=async function(raw){ const qf=window.QP_FORCE; window.QP_FORCE=true;
    try{ return await answer69(raw); } finally{ window.QP_FORCE=qf; } };
  async function answer69(raw){ let R=null, I=null;
    try{ I=V.parse(raw,BOT.ctx); if(I){ BOT.st.n=(BOT.st.n||0)+1; BOT.st.son=istDay(new Date()); if(I.E&&I.E.lg) BOT.st.lg[I.E.lg]=(BOT.st.lg[I.E.lg]||0)+1; R=await run(I,raw,BOT.ctx); } }catch(e){ console.warn("bot-v69",e); R=null; }
    if(R){ BOT.hist=(BOT.hist||[]).concat([{role:"user",content:String(raw).slice(0,200)},{role:"assistant",content:String(R.html||"").replace(/<[^>]+>/g," ").replace(/\s+/g," ").slice(0,160)}]).slice(-6); botSave(); return R; }
    const W=V.rewrite(raw); R=await _prev(W.raw);
    if(R&&/tam anlayamadım|kafası biraz karıştı/.test(R.html||"")) R=fallback(raw,R);
    if(BOT.ctx&&!BOT.ctx.kind){ const c=BOT.ctx; if(c.t==="takim"&&c.L&&c.L.length===1) BOT.ctx=Object.assign({},c,{kind:"analiz",match:c.L[0],E:{}}); else if(c.t==="oner"||c.t==="kupon") BOT.ctx=Object.assign({},c,{kind:c.t==="kupon"?"liste":"oner",E:{lg:c.lg,cn:c.cn,n:c.n,market:c.market,minP:c.minP,day:c.day?V.day(c.day==="aksam"?"bu aksam":c.day,""):null}}); }
    return R; };
  // ---------- çipler: yeni kısayollar ----------
  document.addEventListener("click",e=>{ const b=e.target.closest&&e.target.closest("#botChips button"); if(!b) return; const t=b.dataset.q;
    const go={"Karneyi aç":()=>goView("karne","more"),"Ayarları aç":()=>{ const x=document.querySelector('[data-act="settings"]'); if(x) x.click(); },"Hazır tahminleri aç":()=>{ const x=document.querySelector('[data-go="tahmin"]'); if(x) x.click(); },
      "Maç tahmini aç":()=>{ const x=document.querySelector('[data-go="tahmin"]'); if(x) x.click(); },"Uygulamayı yükle":()=>{ try{ doInstall(); }catch(_){} },"Öneri gönder":()=>{ try{ openFeedback(); }catch(_){} }}[t];
    if(!go) return; e.stopPropagation(); e.preventDefault(); botThen(go); },true);
  // giriş kutusu ipucu
  const _botOpen69=botOpen; botOpen=function(){ _botOpen69(); const q=$("botQ"); if(q) q.placeholder="Sor: yarın en güvenli 3 maç, GS FB ne olur, KG ne demek…"; };
  const st=document.createElement("style"); st.id="bot-v69-css"; st.textContent=`.bt-msg .v69-g{display:block;opacity:.7;margin-top:6px;font-size:11px}.bt-msg .bt-ul li{margin:3px 0}`; document.head.appendChild(st);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: bot-v69 */
/* id: bot-v70 */ try {
// =====================================================================
// OXXai v70: OXXai her gün kendini geliştirir
// • Gece koçu (lab/bot_coach.mjs, GitHub Actions, her gece): yalnız uygulama verisinden (fikstür, lig adları, karne) takım takma adları,
//   lig adları, eş anlamlı kelimeler, yazım hataları, kalıp cümleler, terimler ve öne çıkan maçlar çıkarır; test kümesini büyütür,
//   yeni bilgiyi telefondaki bu bot üzerinde sınar. Test başarısı (niyet ve faydalı cevap) düşmüyorsa data/bot_kb.json yayınlanır.
// • Telefonda öğrenme (yalnız bu cihazda, localStorage "bx-bot70"; yazdıkların hiçbir yere gönderilmez):
//   anlaşılmayan mesajdan sonra dokunulan çip / yeniden yazılan cümle eşlenir; 👍/👎 cevap tercihlerini ayarlar; favori takım hatırlanır.
// • Komutlar: "ne öğrendin?", "öğrendiklerini sıfırla", "takımım Galatasaray".
// =====================================================================
(function(){
  if(typeof botAnswer!=="function"||!window.BOT69) return;
  const V=window.BOT69, X=window.BOT70={kb:null,kbState:"loading",coach:null,test:false,meta:null,lastT:null};
  const N=s=>String(s||"").toLocaleLowerCase("tr").replace(/ç/g,"c").replace(/ğ/g,"g").replace(/ı/g,"i").replace(/ö/g,"o").replace(/ş/g,"s").replace(/ü/g,"u")
    .normalize("NFD").replace(/[̀-ͯ]/g,"").replace(/[^a-z0-9]+/g," ").trim();
  const SUF=["","in","un","nin","nun","e","a","ye","ya","de","da","den","dan","te","ta","ten","tan","i","u","yi","yu","li","lu","la","le","yla","yle","nda","nde","ndan","nden",
    "lar","ler","lari","leri","larin","lerin","lara","lere","larda","lerde","si","su","sini","sunu","ki","nin","daki","deki"];
  const UNK=/tam anlayamadım|kafası biraz karıştı|anlayamadım|anlamadım/i;
  const today=()=>istDay(new Date());
  // ---------- 1) gece koçunun bilgi bankası (data/bot_kb.json) ----------
  let W=Object.create(null), PH=[], PARA=Object.create(null), GL=[];
  const LG0=Object.entries(BOT_LG);
  function setLG(extra){ for(const k of Object.keys(BOT_LG)) delete BOT_LG[k];
    const add=[]; for(const [k,v] of Object.entries(extra||{})){ const nk=N(k); if(nk&&typeof v==="string"&&!LG0.some(([a])=>N(a)===nk)) add.push([nk,v]); }
    const multi=add.filter(x=>x[0].includes(" ")).sort((a,b)=>b[0].split(" ").length-a[0].split(" ").length||b[0].length-a[0].length), single=add.filter(x=>!x[0].includes(" "));
    for(const [k,v] of multi.concat(single).concat(LG0)) BOT_LG[k]=v; }
  function applyKB(kb){ W=Object.create(null); PH=[]; PARA=Object.create(null); GL=[];
    const ok=(k,v)=>typeof v==="string"&&v.length&&v.length<=60&&k&&k.length<=40;
    if(kb){ for(const sec of ["takim","esanlam","yazim"]) for(const [k,v] of Object.entries(kb[sec]||{})){ const nk=N(k); if(!ok(nk,v)) continue; if(nk.includes(" ")) PH.push([nk.split(" "),v]); else W[nk]=v; }
      PH.sort((a,b)=>b[0].length-a[0].length);
      for(const [k,v] of Object.entries(kb.para||{})){ const nk=N(k); if(ok(nk,v)) PARA[nk]=v; }
      for(const g of (kb.sozluk||[])){ try{ if(g&&g.re&&g.html) GL.push({k:g.k,re:new RegExp(g.re),html:String(g.html)}); }catch(e){} } }
    try{ setLG(kb&&kb.lig); }catch(e){}
    V._stop=null; }
  // kelime/ifade eşlemesi: "spurs" → "Tottenham Hotspur", Türkçe ekleriyle ("spurs'un", "karşılaşmaları")
  function kbRewrite(raw){ raw=String(raw||""); if(!PH.length&&!Object.keys(W).length) return raw;
    let words=raw.split(/\s+/).filter(Boolean);
    if(PH.length){ let nw=words.map(N);
      for(const [p,to] of PH){ for(let i=0;i+p.length<=nw.length;i++){ let hit=true;
          for(let j=0;j<p.length;j++){ const a=nw[i+j]||"", b=p[j]; if(a===b) continue; if(j===p.length-1&&a.startsWith(b)&&SUF.includes(a.slice(b.length))) continue; hit=false; break; }
          if(hit){ words.splice(i,p.length,to); nw.splice(i,p.length,N(to)); } } } }
    words=words.map(w=>{ if(/\d/.test(w)) return w; const n=N(w); if(!n) return w; const parts=n.split(" "), base=parts[0];
      if(parts.length>1&&!parts.slice(1).every(x=>SUF.includes(x))) return w;
      if(W[base]) return W[base];
      for(let L=base.length-1;L>=3;L--){ const k=base.slice(0,L); if(W[k]&&SUF.includes(base.slice(L))) return W[k]; }
      return w; });
    return words.join(" "); }
  const _rw=V.rewrite; V.rewrite=function(raw){ return _rw(kbRewrite(raw)); };
  const _parse=V.parse; V.parse=function(raw,ctx){ const r=_parse(raw,ctx); X.lastT=r?r.t:null; return r; };
  // ---------- 2) bu telefonda öğrenilenler (yalnız localStorage) ----------
  const KEY="bx-bot70";
  const blank=()=>({v:1,map:{},neg:{},fb:{},fav:"",pend:null});
  let ST=(()=>{ try{ return Object.assign(blank(),JSON.parse(localStorage.getItem(KEY)||"{}")); }catch(e){ return blank(); } })();
  function save(){ try{
      const M=Object.entries(ST.map); if(M.length>80){ M.sort((a,b)=>(b[1].ok||0)-(a[1].ok||0)||(b[1].at||0)-(a[1].at||0)); ST.map=Object.fromEntries(M.slice(0,80)); }
      const G=Object.entries(ST.neg); if(G.length>80) ST.neg=Object.fromEntries(G.slice(-80));
      let s=JSON.stringify(ST); while(s.length>16000&&Object.keys(ST.map).length){ delete ST.map[Object.keys(ST.map)[0]]; s=JSON.stringify(ST); }
      localStorage.setItem(KEY,s); }catch(e){} }
  function learn(p,q){ if(!p||!q||p.length>80||N(q)===p) return false; ST.map[p]={q:String(q).slice(0,120),at:Date.now(),ok:(ST.map[p]&&ST.map[p].q===q)?ST.map[p].ok||0:0,n:0}; delete ST.neg[p]; save(); return true; }
  function favTeam(x){ const s=N(kbRewrite(x)); if(!s||s.length<3) return null;
    try{ const t=findTeam(s); if(t&&t.name) return t.name; }catch(e){}
    try{ const m=V.teams(s); if(m&&m.m) return m.hs>=m.as?m.m.h:m.m.a; }catch(e){}
    return null; }
  // ---------- 3) cevap katmanı ----------
  const TERMQ=/\b(ne demek\w*|nedir|ne anlama|anlami\w*|ne ifade|aciklar misin|acikla\w*|ne demektir|manasi|nasil calisir|ne manaya)\b/;
  function gloss(s){ if(!GL.length||!TERMQ.test(s)) return null; try{ if(V.term(s)) return null; }catch(e){}
    for(const g of GL) if(g.re.test(s)) return {html:`📖 ${g.html}`,chips:["Başka bir terim: oran nedir","En güvenli maçlar","Yardım"],_t:"sozluk"};
    return null; }
  const ONQ=/\b(onemli mac\w*|buyuk mac\w*|gunun maci\w*|haftanin maci\w*|macin maci|dev mac\w*|one cikan mac\w*|kritik mac\w*|derbiler)\b/;
  async function notable(s,_ans){ const L=X.kb&&X.kb.onemli; if(!L||!L.length||!ONQ.test(s)) return null;
    const now=Date.now(), P=Pick.list().filter(m=>!m.started&&m.dt.getTime()>now-2*3600e3);
    const hit=L.map(o=>P.find(m=>m.h===o.h&&m.a===o.a)).filter(Boolean); if(!hit.length) return null;
    const m=hit[0], R=await _ans(`${m.h} ${m.a}`); if(!R||UNK.test(R.html||"")) return null;
    const others=hit.slice(1,4).map(x=>`${x.h} ${x.a}`);
    return Object.assign({},R,{html:`⭐ <b>Öne çıkan maç</b> (büyük takımlar / üst lig, gece koçunun seçimi):<br>${R.html}`,chips:others.length?others.concat(["En güvenli maçlar"]):R.chips,_t:"onemli"}); }
  function alts(){ const ch=["Bugün hangi maçlar var","En güvenli 3 maç","Altın tahminler","Yardım"];
    const best=Object.entries(ST.fb).filter(([k,v])=>v.u>v.d&&{oner:1,guvenli:1,altin:1,liste:1,karne:1}[k]).sort((a,b)=>b[1].u-a[1].u)[0];
    if(best){ const q={oner:"Bugün hangi maçlar var",guvenli:"En güvenli 3 maç",altin:"Altın tahminler",liste:"3 maçlık liste yap",karne:"Dünkü karne"}[best[0]]; const i=ch.indexOf(q); if(i>0){ ch.splice(i,1); ch.unshift(q); } }
    return ch; }
  function nowKbLine(short){ const c=X.coach&&X.coach.son; if(!c) return "";
    const gece=c.tarih===today()?"Bu gece":c.tarih===istDay(new Date(Date.now()-864e5))?"Dün gece":`${ist(new Date(c.tarih+"T12:00:00+03:00"),{day:"numeric",month:"long"})} gecesi`;
    const y=X.coach.yayin||c; const b=`test başarısı <b>%${y.faydali}</b>${short?"":` <small>(${y.n} soru)</small>`}`;
    return c.yayin?`🌙 ${gece} ${c.yeni?`<b>${c.yeni}</b> yeni şey öğrendim`:"yeni bir şey öğrenmedim"} · ${b}`:`🌙 ${gece} yeni bilgiler testi geçemedi, önceki sürümle devam · ${b}`; }
  function view(){ const kb=X.kb, c=X.coach&&X.coach.son, rows=[];
    if(c){ const y=X.coach.yayin||c; rows.push(`🌙 <b>Gece koçu</b> (yalnız uygulama verisinden, sunucuda): ${nowKbLine().replace(/^🌙 /,"")}.${kb&&kb.sayim?` Bilgi bankasında ${kb.sayim.toplam} kayıt var: ${kb.sayim.takim} takım adı, ${kb.sayim.lig} lig adı, ${kb.sayim.esanlam+kb.sayim.yazim} kelime, ${kb.sayim.para} kalıp cümle, ${kb.sayim.sozluk} terim.`:""} Testte niyet doğruluğu %${y.niyet}, faydalı cevap %${y.faydali}.`); }
    else rows.push(`🌙 Gece koçunun raporu henüz yok; ilk rapor bu gece.`);
    const M=Object.entries(ST.map);
    rows.push(`📱 <b>Bu telefonda senden öğrendiklerim</b>: ${M.length?`${M.length} ifade (ör. ${M.slice(-3).map(([p,v])=>`"${esc(p)}" → "${esc(v.q)}"`).join(", ")})`:"henüz yok — anlamadığım bir şeyden sonra çiplerden birine dokunursan ya da başka türlü yazarsan öğrenirim"}.`);
    const F=Object.values(ST.fb).reduce((a,v)=>(a.u+=v.u||0,a.d+=v.d||0,a),{u:0,d:0}); if(F.u||F.d) rows.push(`👍 ${F.u} · 👎 ${F.d} geri bildirim (beğenmediğin cevaplarda sana alternatif sunarım).`);
    const tm=Object.entries(BOT.st.tm||{}).sort((a,b)=>b[1]-a[1]).slice(0,3).map(x=>x[0]), lg=Object.entries(BOT.st.lg||{}).sort((a,b)=>b[1]-a[1]).slice(0,2).map(x=>{ try{ return botLgName(x[0]); }catch(e){ return x[0]; } });
    rows.push(`⭐ <b>Favorilerin</b>: ${ST.fav?`takımın <b>${esc(ST.fav)}</b>; `:""}${tm.length?`en çok sorduğun takımlar ${tm.map(esc).join(", ")}`:"henüz belirgin bir takım yok"}${lg.length?`; ligler ${lg.map(esc).join(", ")}`:""}.${ST.fav?"":` "takımım Galatasaray" yazarsan "takımımın maçı" dediğinde anlarım.`}`);
    return {html:`<b>🧠 OXXai'nin öğrendikleri</b><ul class="bt-ul">${rows.map(r=>`<li>${r}</li>`).join("")}</ul><small class="v70-g">Bu telefonda öğrendiklerim yalnız bu cihazda saklanır, hiçbir yere gönderilmez. "öğrendiklerini sıfırla" yazarsan silerim.</small>`,chips:["Öğrendiklerini sıfırla","Yardım","Bugün hangi maçlar var"]}; }
  function command(s,raw){
    if(/^(ne ogrendin|neler ogrendin|ne ogrendin bugun|bugun ne ogrendin|ogrendiklerin\w*( neler| ne)?|ogrendiklerini goster|oxxai( nin)? ogrendikleri|oxx( un)? ogrendikleri|bulutun ogrendikleri|hafizan|hafizani goster|beni ne kadar taniyorsun)$/.test(s)) return view();
    if(/^(ogrendiklerini|ogrendiklerin\w*|hafizani|hafizan\w*)\s*(sifirla|sil|temizle|unut)\w*$|^(her seyi unut|beni unut)$/.test(s)){ X.confirm=Date.now(); return {html:`Bu telefonda senden öğrendiklerimi (ifade eşlemeleri, 👍/👎, favori takım ve ligler) silmemi istiyor musun? Gece koçunun herkes için öğrendikleri silinmez.`,chips:["Evet, sıfırla","Hayır"]}; }
    if(/^evet sifirla$/.test(s)){ if(!X.confirm||Date.now()-X.confirm>5*60e3) return {html:`Neyi sıfırlayayım? "öğrendiklerini sıfırla" yazabilirsin.`,chips:["Ne öğrendin?"]};
      X.confirm=0; ST=blank(); save(); try{ BOT.st.tm={}; BOT.st.lg={}; botSave(); }catch(e){} return {html:`Tamam 🧹 Bu telefonda senden öğrendiklerimi sildim. Baştan öğrenmeye hazırım.`,chips:["Bugün hangi maçlar var","Yardım"]}; }
    if(/^hayir$/.test(s)&&X.confirm){ X.confirm=0; return {html:`Tamam, hiçbir şeyi silmedim 🙂`,chips:["Ne öğrendin?"]}; }
    let m=/^(?:benim )?(?:takimim|tuttugum takim|favori takimim)(?: da| de)? (?!maci|macin|mac\b|ne|nin|in)(.{3,40})$/.exec(s)||/^(.{3,40}?) (?:taraftariyim|tutuyorum|liyim)$/.exec(s);
    if(m){ const t=favTeam(m[1]); if(t){ ST.fav=t; save(); return {html:`Not aldım ⭐ Takımın <b>${esc(t)}</b>. Artık "takımımın maçı ne olur" dersen onu anlarım. (Yalnız bu telefonda saklanır.)`,chips:["Takımımın maçı ne olur","Ne öğrendin?"]}; } }
    return null; }
  const _ans=botAnswer;
  botAnswer=async function(raw){ const q0=String(raw||""), n0=N(q0); X.lastT=null; X.meta=null;
    const C=command(n0,q0); if(C){ X.meta={t:"komut",phrase:n0}; return C; }
    let q=q0, via=null, L=null;
    if(!X.test&&ST.fav&&/\b(benim )?takimim\w*\b/.test(n0)) q=n0.replace(/\b(benim )?takimim\w*\b/g,ST.fav);
    else if(!X.test&&(L=ST.map[n0])&&L.q){ q=L.q; via="cihaz"; L.n=(L.n||0)+1; }
    else if(PARA[n0]){ q=PARA[n0]; via="kb"; }
    const nq=N(kbRewrite(q));
    let R=gloss(nq); if(!R) R=await notable(nq,_ans);
    if(R) X.lastT=R._t; else R=await _ans(q);
    const t=X.lastT||null, ok=!!(R&&R.html&&!UNK.test(R.html));
    let extra="", chips=null;
    if(!X.test){
      if(!ok){ if(/[a-z]{2}/.test(n0)&&!via) ST.pend={p:n0,at:Date.now()}; }
      else if(ST.pend&&Date.now()-ST.pend.at<3*60e3&&ST.pend.p!==n0&&!via){ const p=ST.pend.p; ST.pend=null; if(learn(p,q0)) extra+=`<small class="v70-g">📌 Öğrendim: bundan sonra "${esc(p)}" yazınca bunu anlayacağım. ("ne öğrendin?" ile görebilirsin)</small>`; }
      if(via==="cihaz") extra+=`<small class="v70-g">📌 Bunu senden öğrenmiştim: "${esc(L.q)}" olarak anladım. Yanlışsa 👎'ye dokun.</small>`;
      else if(ok&&ST.neg[n0]){ extra+=`<small class="v70-g">Geçen sefer bu soruya verdiğim cevabı beğenmemiştin; istersen aşağıdan başka bir şey seç ya da farklı yaz, öğrenirim.</small>`; chips=alts(); ST.pend={p:n0,at:Date.now(),neg:1}; }
      save(); }
    X.meta={phrase:n0,q,via,t:t||(ok?"eski":"anlamadi"),ok};
    return (extra||chips)?Object.assign({},R,{html:(R.html||"")+extra,chips:chips||R.chips}):R; };
  // ---------- 4) arayüz: 👍/👎, başlıkta gece koçu satırı, Motor › Otonom ekip satırı ----------
  const _send=botSend;
  botSend=async function(q){ await _send(q);
    try{ const log=$("botLog"), w=log&&log.lastElementChild, M=X.meta; if(!w||!M||M.t==="komut"||!w.classList.contains("bot")||w.querySelector(".v70-fb")) return;
      const d=document.createElement("div"); d.className="v70-fb"; d.innerHTML=`<button type="button" data-fb="1" aria-label="Faydalı cevap">👍</button><button type="button" data-fb="-1" aria-label="Faydalı değil">👎</button>`; d._m=M; w.appendChild(d); }catch(e){} };
  document.addEventListener("click",e=>{ const b=e.target.closest&&e.target.closest(".v70-fb button"); if(!b) return; e.stopPropagation(); const box=b.parentNode, M=box._m; if(!M||box.dataset.done) return;
    box.dataset.done=1; b.classList.add("on"); box.querySelectorAll("button").forEach(x=>x.disabled=true); try{ buzz(8); }catch(_){}
    const f=ST.fb[M.t]=ST.fb[M.t]||{u:0,d:0};
    if(b.dataset.fb==="1"){ f.u++; if(M.via==="cihaz"&&ST.map[M.phrase]) ST.map[M.phrase].ok=(ST.map[M.phrase].ok||0)+1; delete ST.neg[M.phrase]; save(); try{ toast("Teşekkürler 👍 Not ettim"); }catch(_){} return; }
    f.d++; if(M.via==="cihaz") delete ST.map[M.phrase]; ST.neg[M.phrase]=(ST.neg[M.phrase]||0)+1; ST.pend={p:M.phrase,at:Date.now(),neg:1}; save();
    try{ botPush("bot",`Üzgünüm 😕 Ne demek istediğini aşağıdan seçersen ya da başka türlü yazarsan, bir dahaki sefere doğrudan onu anlarım. <small class="v70-g">(Bu öğrenme yalnız bu telefonda kalır.)</small>`); botChips(alts()); }catch(_){} },true);
  function kbChip(){ const sh=$("botSheet"); if(!sh) return; let el=$("botKb"); const line=nowKbLine(true);
    if(!line){ if(el) el.remove(); return; }
    if(!el){ const h=sh.querySelector(".bt-h"); if(!h) return; el=document.createElement("button"); el.type="button"; el.id="botKb"; el.className="v70-kb"; el.setAttribute("aria-label","OXXai'nin öğrendikleri"); h.after(el); el.onclick=()=>botSend("ne öğrendin?"); }
    el.innerHTML=line; }
  const _open=botOpen; botOpen=function(){ _open.apply(this,arguments); try{ kbChip(); }catch(e){} };
  if(typeof renderKarne==="function"){ const _rk=renderKarne; renderKarne=function(){ _rk.apply(this,arguments);
    try{ const p=$("teamPanel"), c=X.coach&&X.coach.son; if(!p||!c||p.querySelector(".v70-row")) return; const d=document.createElement("div"); d.className="tm-r v70-row";
      d.innerHTML=`<span class="tm-ic">💬</span><div><b>Sohbet koçu</b><small>her gece: OXXai'ye yeni takım adları, lig adları, kalıplar ve terimler öğretir; testi düşüren bilgi yayınlanmaz</small><p>${nowKbLine()}</p></div>`; p.appendChild(d); }catch(e){} }; }
  // ---------- 5) yükleme (önbelleksiz; hata olursa sessizce eski bilgiyle devam) ----------
  function load(){ const g=u=>fetch(u+"?t="+Date.now(),{cache:"no-store"}).then(r=>r.ok?r.json():null).catch(()=>null);
    return Promise.all([g("data/bot_kb.json"),g("data/bot_coach.json")]).then(([kb,c])=>{ X.coach=c&&typeof c==="object"&&c.son?c:null;
      if(kb&&typeof kb==="object"&&kb.v){ try{ applyKB(kb); X.kb=kb; }catch(e){ applyKB(X.kb); } }
      X.kbState=X.kb?"ok":"none"; try{ kbChip(); }catch(e){} }).catch(()=>{ X.kbState=X.kb?"ok":"none"; }); }
  X.ready=load(); setInterval(()=>{ if(!document.hidden) load(); },6*3600e3);
  // test yardımcıları (gece koçu kullanır): bilgi bankasını değiştir, cihazda öğrenmeyi kapat
  X.setKB=kb=>{ applyKB(kb||null); X.kb=kb||null; X.kbState=X.kb?"ok":"none"; };
  X.testMode=b=>{ X.test=!!b; }; X.resetSession=()=>{ ST.pend=null; X.meta=null; X.confirm=0; }; X.store=()=>JSON.parse(JSON.stringify(ST)); X.N=N; X.rewrite=kbRewrite;
  const st=document.createElement("style"); st.id="bot-v70-css";
  st.textContent=`.bt-msg .v70-g{display:block;opacity:.72;margin-top:6px;font-size:11px}.v70-fb{display:flex;gap:6px;margin-top:6px}.v70-fb button{border:1px solid var(--line);background:transparent;border-radius:99px;padding:2px 9px;font-size:13px;line-height:1.5;opacity:.75;color:inherit}.v70-fb button.on{opacity:1;border-color:var(--cyan);background:rgba(34,211,255,.12)}.v70-fb button:disabled:not(.on){opacity:.35}
.v70-kb{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid var(--line);background:rgba(34,211,255,.07);color:var(--ink2,inherit);font:500 12px var(--font,inherit);padding:7px 14px;line-height:1.4}.v70-kb b{color:var(--cyan)}.v70-kb small{opacity:.7}`;
  document.head.appendChild(st);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: bot-v70 */
