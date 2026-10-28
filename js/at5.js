/* id: at5-v116 */ try {
// =====================================================================
// v116 · AT YARIŞI 2.0 — lab/at/TASARIM.md Aşama 5 (at2-v106 ve at3-v109'u SARAR; onların kodu değişmez)
// • 🔍 Arama: At başlık satırına düğme → #at/ara. At, jokey, antrenör adıyla; Türkçe harf duyarsız (İ/ı/ş/ğ/ü/ö/ç), kısmi
//   eşleşme, küçük yazım hatası toleransı. Önce bugünün/yarının programı (saat + hipodrom + koşu no → At profili / jokey
//   profili), sonra geçmiş dizin data/at/dizin.json (lab/at/dizin.py; son 365 gün, yalnız türetilmiş özet). Sonuçtan takip.
// • "Atım koşuyor" hatırlatması: takip edilen at/jokey/antrenör bugün koşuyorsa koşudan 30 dk önce At Bugün ekranında kart
//   ve uygulamanın üstünde ince, kapatılabilir şerit (yalnız bir cümle; futbol/basket verisine karışmaz). Menü'de ve Ayarlar'da anahtar
//   (varsayılan açık, uygulama içi). Sistem bildirimi YALNIZ kullanıcı ayrı düğmeye basıp izin verirse, uygulama açıkken yerel
//   (registration.showNotification / new Notification). Push sunucusu yok; izin istemi kendiliğinden çıkmaz.
// • OXX: "X atı bugün koşuyor mu", "jokey Y bugün nerede" → program + dizin (mevcut at niyetlerinden önce, dar kalıpla).
// Kullanıcı verisi yalnız localStorage: bx-at-hatirlat {on,sys} · bx-at-hatirlat-iz {d,k[],x[]} · bx-at-ara-son [..].
// tjk.org / atyarisi.com'a istek yok, şans oyunu sitesi bağlantısı yok, para tutarı yok · 18+.
// =====================================================================
(function(){
  const X=window.BX_AT, A2=window.BX_AT2; if(!X||!X.AT||!A2) return;
  const AT=X.AT, sec=$("v-at"), box=$("at2Box"), nav=$("at2Nav"); if(!sec||!box||!nav) return;
  // ---------- yardımcılar ----------
  const E=s=>s==null?"":esc(s), enc=encodeURIComponent;
  const K=kid=>String(kid).split("/").map(enc).join("~");
  const lsJ=(k,d)=>{ try{ const v=JSON.parse(localStorage.getItem(k)); return v==null?d:v; }catch(e){ return d; } };
  const lsS=(k,v)=>{ try{ localStorage.setItem(k,JSON.stringify(v)); }catch(e){} };
  const NOW=()=>Date.now(), today=()=>istDay(new Date(NOW()));
  const tsOf=(d,s)=>Date.parse(d+"T"+(s||"23:59")+":00+03:00"), dayOf=kid=>String(kid||"").split("/")[0];
  const P=x=>x==null||!isFinite(x)?"–":"%"+Math.round(x*100);
  const tap=()=>{ try{ buzz(6); }catch(e){} };
  const F=s=>String(s||"").toLocaleLowerCase("tr").replace(/ç/g,"c").replace(/ğ/g,"g").replace(/ı/g,"i").replace(/ö/g,"o").replace(/ş/g,"s").replace(/ü/g,"u")
    .normalize("NFD").replace(/[̀-ͯ]/g,"").replace(/[^a-z0-9]+/g," ").trim();
  const TK=()=>A2.TK||{at:[],jokey:[],antrenor:[]};
  const isTk=(k,v)=>!!v&&(TK()[k]||[]).includes(v);
  const KND={at:"At",jokey:"Jokey",antrenor:"Antrenör"}, AV={jokey:"🏇",antrenor:"🧑‍🏫"};
  const IC={lu:`<svg class="lu" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/></svg>`,
    lu2:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/></svg>`,
    x:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>`,
    star:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8L3.5 9.7l5.9-.9z"/></svg>`,
    starF:`<svg viewBox="0 0 24 24" fill="#E9C766" stroke="#E9C766" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8L3.5 9.7l5.9-.9z"/></svg>`};
  // saatin Türkçe bulunma eki: 20:30'da, 14:00'te, 17:15'te
  function ekDa(s){ const m=/^(\d{1,2})[:.](\d{2})$/.exec(String(s||"")); if(!m) return "'de"; const h=+m[1], mi=+m[2], n=mi||h;
    const W={0:"a",1:"e",2:"e",3:"e",4:"e",5:"e",6:"a",7:"e",8:"e",9:"a"}, T={10:"a",20:"e",30:"a",40:"a",50:"e"}, SERT=new Set([3,4,5,40]);
    let v, sert; if(n===0){ v="a"; sert=false; } else if(n%10){ v=W[n%10]; sert=SERT.has(n%10); } else if(n%100===0){ v="e"; sert=false; } else { v=T[n%100]; sert=SERT.has(n%100); }
    return "'"+(sert?"t":"d")+v; }
  const ddmm=d=>{ try{ return new Date(d+"T12:00:00+03:00").toLocaleDateString("tr-TR",{day:"numeric",month:"short",timeZone:"Europe/Istanbul"}); }catch(e){ return d; } };
  const dLbl=d=>{ try{ const l=X.dLbl(d); return /^\d/.test(l)?ddmm(d):l; }catch(e){ return d; } };

  // =====================================================================
  // Eşleştirme (Türkçe harf duyarsız, kısmi, küçük yazım hatası toleransı)
  // =====================================================================
  function ed(a,b,mx){ if(Math.abs(a.length-b.length)>mx) return mx+1; const n=b.length; let p2=null, p=Array.from({length:n+1},(_,j)=>j);
    for(let i=1;i<=a.length;i++){ const c=[i]; let lo=i; for(let j=1;j<=n;j++){ let v=Math.min(p[j]+1,c[j-1]+1,p[j-1]+(a[i-1]===b[j-1]?0:1));
        if(i>1&&j>1&&a[i-1]===b[j-2]&&a[i-2]===b[j-1]) v=Math.min(v,p2[j-2]+1); c[j]=v; if(v<lo) lo=v; } if(lo>mx) return mx+1; p2=p; p=c; } return p[n]; }
  const tolOf=n=>n>=8?2:n>=4?1:0;
  function tokS(t,W){ let b=0; const tol=tolOf(t.length);
    for(const w of W){ let s=0; if(w===t) s=3; else if(w.startsWith(t)) s=2.5; else if(t.length>=3&&w.includes(t)) s=1.8;
      else if(tol){ let d=ed(t,w,tol); if(d>tol&&w.length>t.length) d=Math.min(d,ed(t,w.slice(0,t.length),tol)); if(d<=tol) s=1.3-d*.2; }
      if(s>b){ b=s; if(b===3) break; } } return b; }
  // q: {f, T[], j}  ·  o: {f, W[], j}  →  0 = eşleşmedi
  function score(q,o){ if(!q.f) return 0; let s=0, fz=false;
    for(const t of q.T){ const v=tokS(t,o.W); if(!v){ if(q.j.length>=4&&o.j.includes(q.j)) return 2.2+(o.j.startsWith(q.j)?.5:0); return 0; } if(v<1.5) fz=true; s+=v; }
    if(o.f===q.f) s+=2; else if(o.f.startsWith(q.f)) s+=1; return fz?s-.1:s; }
  const Q=raw=>{ const f=F(raw); return {f,T:f?f.split(" "):[],j:f.replace(/ /g,"")}; };
  const O=ad=>{ const f=F(ad); return {f,W:f.split(" "),j:f.replace(/ /g,"")}; };

  // =====================================================================
  // Kaynak 1 · program (bugün/yarın; jokey ve antrenör canlı dosyasından)
  // =====================================================================
  let PG={sig:"",at:[],kisi:{jokey:new Map(),antrenor:new Map()}};
  function prog(){ const t0=today(), days=(AT.days||[]).filter(d=>d>=t0).sort(), sig=days.join(",")+"|"+days.map(d=>{ const C=AT.canli&&AT.canli[d]; return (C&&C.guncelleme_tsi)||""; }).join(",")+"|"+t0;
    if(sig===PG.sig) return PG; const at=[], kisi={jokey:new Map(),antrenor:new Map()};
    for(const d of days){ const D=AT.data[d]; if(!D) continue; const C=(AT.canli||{})[d], cb={}; for(const c of (C&&C.kosular)||[]) cb[c.kosu_id]=c;
      for(const r of D.kosular||[]){ const c=cb[r.kosu_id]||null, byNo={}; for(const h of (c&&c.atlar)||[]) byNo[String(h.no)]=h;
        for(const h of r.atlar||[]){ const x=byNo[String(h.no)]||{}, no=String(h.no);
          const it={k:"at",ad:h.ad,o:O(h.ad),d,r,c,no,jokey:x.jokey||h.jokey||"",antrenor:x.antrenor||"",p:x.p_oran!=null?x.p_oran:h.p_kazanma,t:tsOf(d,r.saat)};
          at.push(it);
          for(const kd of ["jokey","antrenor"]){ const ad=it[kd]; if(!ad) continue; let z=kisi[kd].get(ad); if(!z){ z={k:kd,ad,o:O(ad),L:[]}; kisi[kd].set(ad,z); } z.L.push(it); } } } }
    for(const kd in kisi) for(const z of kisi[kd].values()) z.L.sort((a,b)=>a.t-b.t||a.r.kosu-b.r.kosu);
    at.sort((a,b)=>a.t-b.t); PG={sig,at,kisi}; return PG; }
  function stOf(it){ const c=it.c, S=c&&c.sonuc;
    if(S){ const i=(S.sira||[]).map(String).indexOf(it.no); return {s:"bitti",t:i>=0?`Bitti · ${(S.derece&&S.derece[i])||i+1}.`:(S.kosmayan||[]).map(String).includes(it.no)?"Koşmadı":"Bitti"}; }
    if(c&&(c.kosmayan||[]).map(String).includes(it.no)) return {s:"kosmaz",t:"Koşmuyor"};
    const mn=Math.round((it.t-NOW())/6e4); if(isFinite(it.t)&&mn<=0) return {s:"basladi",t:"Başladı"};
    if(it.d===today()&&mn<=90) return {s:"yakin",t:mn+" dk"}; return {s:"bekliyor",t:it.r.saat||""}; }

  // =====================================================================
  // Kaynak 2 · geçmiş dizin (data/at/dizin.json; tembel yüklenir)
  // =====================================================================
  const DZ={v:undefined,p:null,at:null,jokey:null,antrenor:null};
  function dzLoad(){ if(DZ.v!==undefined||DZ.p) return DZ.p; DZ.p=X.j("data/at/dizin.json").then(v=>{ DZ.p=null; DZ.v=v&&Array.isArray(v.atlar)?v:null; if(DZ.v) dzIndex(); return DZ.v; }); return DZ.p; }
  function dzIndex(){ const v=DZ.v, g0=Date.parse(v.gun0+"T12:00:00Z"), gd=g=>new Date(g0+g*864e5).toISOString().slice(0,10), hp=i=>v.hip[i]||"";
    DZ.at=v.atlar.map(a=>({k:"at",ad:a[0],o:O(a[0]),son:gd(a[1]),n:a[2],der:a[3],hip:hp(a[4]),antrenor:v.an[a[5]]||"",jokey:v.jk[a[6]]||""}));
    const ks=(L,names,kd)=>(L||[]).map(z=>{ const ad=names[z[0]]||""; return {k:kd,ad,o:O(ad),son:gd(z[1]),n90:z[2],w90:z[3],i90:z[4],hip:hp(z[5]),n:z[6]}; }).filter(z=>z.ad);
    DZ.jokey=ks(v.jokeyler,v.jk,"jokey"); DZ.antrenor=ks(v.antrenorler,v.an,"antrenor"); }

  // =====================================================================
  // Arama (ortak: ekran + OXX)
  // =====================================================================
  function find(raw,kinds){ const q=Q(raw), out={prog:[],gec:[]}; if(!q.f) return out; kinds=kinds||["at","jokey","antrenor"]; const pg=prog(), seen=new Set();
    if(kinds.includes("at")){ const by=new Map(); for(const it of pg.at){ const s=score(q,it.o); if(!s) continue; const z=by.get(it.ad); if(z) z.L.push(it); else by.set(it.ad,{k:"at",ad:it.ad,s,L:[it]}); }
      for(const z of by.values()){ out.prog.push(z); seen.add("at|"+z.ad); } }
    for(const kd of ["jokey","antrenor"]) if(kinds.includes(kd)) for(const z of pg.kisi[kd].values()){ const s=score(q,z.o); if(s){ out.prog.push({k:kd,ad:z.ad,s,L:z.L}); seen.add(kd+"|"+z.ad); } }
    if(DZ.at) for(const kd of kinds) for(const z of DZ[kd]||[]){ if(seen.has(kd+"|"+z.ad)) continue; const s=score(q,z.o); if(s) out.gec.push({k:kd,ad:z.ad,s,z}); }
    const kw={at:0,jokey:.05,antrenor:.1};
    out.prog.sort((a,b)=>b.s-a.s||a.L[0].t-b.L[0].t||kw[a.k]-kw[b.k]);
    out.gec.sort((a,b)=>b.s-a.s||(b.z.son>a.z.son?1:b.z.son<a.z.son?-1:0)||kw[a.k]-kw[b.k]);
    return out; }

  // =====================================================================
  // Arama ekranı (#at/ara)
  // =====================================================================
  const U={q:"",k:"tum",nP:12,nG:20,foc:false,lastTk:null,t:null};
  const recent=()=>{ const L=lsJ("bx-at-ara-son",[]); return Array.isArray(L)?L.filter(x=>typeof x==="string").slice(0,6):[]; };
  function remember(q){ q=String(q||"").replace(/\s+/g," ").trim().slice(0,40); if(q.length<2) return; const L=recent().filter(x=>F(x)!==F(q)); L.unshift(q); lsS("bx-at-ara-son",L.slice(0,6)); }
  function mark(ad,q){ const f=F(ad); if(!q.f) return E(ad); // eşleşen kelime başlarını vurgula (harf sayısı korunur: tek tek karakter katlanır)
    const ch=[...String(ad)], fz=ch.map(c=>F(c)||" "); const words=[]; let i=0; while(i<ch.length){ if(fz[i]===" "){ i++; continue; } let j=i; while(j<ch.length&&fz[j]!==" ") j++; words.push([i,j]); i=j; }
    const on=new Array(ch.length).fill(false);
    for(const t of q.T){ for(const [a,b] of words){ const w=fz.slice(a,b).join(""); const at=w.indexOf(t); if(at>=0&&t.length){ let c=0, k=a; while(k<b&&c<at+t.length){ if(c>=at) on[k]=true; c+=fz[k].length; k++; } break; } } }
    let h="", o=false; ch.forEach((c,k)=>{ if(on[k]&&!o){ h+='<b class="a5-mark">'; o=true; } if(!on[k]&&o){ h+="</b>"; o=false; } h+=E(c); }); if(o) h+="</b>"; return h; }
  const tkBtn=(k,ad)=>{ const on=isTk(k,ad); return `<button class="a2-ib a5-tk" type="button" data-tk="${k}|${E(ad)}" aria-pressed="${on}" aria-label="${E(ad)}: ${on?"takipten çıkar":"takip et"}">${on?IC.starF:IC.star}</button>`; };
  const pill=st=>`<span class="a2-pill${st.s==="bitti"?"":st.s==="yakin"?" w":st.s==="basladi"?" or":""}">${E(st.t)}</span>`;
  const where=it=>`${E(dLbl(it.d))} <b>${E(it.r.saat||"")}</b> · ${E(it.r.hipodrom)} ${it.r.kosu}. koşu`;
  function rowProg(z,q){ const tg=`<span class="a5-tg g">${KND[z.k]}</span>`;
    if(z.k==="at"){ const it=z.L[0], more=z.L.length>1?` · ${z.L.length-1} koşu daha`:"";
      return `<div class="a2-hrow a5-r"><a class="a5-l" href="#at/at/${K(it.r.kosu_id)}/${enc(it.no)}" data-a5r="${E(z.ad)}"><span class="a2-no">${E(it.no)}</span><span class="a2-hn"><b>${mark(z.ad,q)}</b><small>${tg}${where(it)}${more}</small><small>${it.jokey?"Jokey "+E(it.jokey):""}${it.jokey&&it.p!=null?" · ":""}${it.p!=null?"OXX "+P(it.p):""}</small></span>${pill(stOf(it))}</a>${tkBtn("at",z.ad)}</div>`; }
    const L=z.L, nx=L.find(it=>{ const s=stOf(it).s; return s==="bekliyor"||s==="yakin"; })||L[L.length-1], dd=[...new Set(L.map(it=>it.d))];
    const cnt=dd.map(d=>`${dLbl(d)} ${L.filter(it=>it.d===d).length} ${z.k==="jokey"?"biniş":"at"}`).join(" · ");
    return `<div class="a2-hrow a5-r"><a class="a5-l" href="#at/${z.k}/${enc(z.ad)}" data-a5r="${E(z.ad)}"><span class="a5-av" aria-hidden="true">${AV[z.k]}</span><span class="a2-hn"><b>${mark(z.ad,q)}</b><small>${tg}${E(cnt)}</small><small>${nx===L[L.length-1]&&stOf(nx).s==="bitti"?"Son":"Sıradaki"}: ${where(nx)} · ${E(nx.ad)}</small></span>${pill(stOf(nx))}</a>${tkBtn(z.k,z.ad)}</div>`; }
  function rowGec(o,q){ const z=o.z, tg=`<span class="a5-tg">${KND[o.k]}</span>`;
    if(o.k==="at") return `<div class="a2-hrow a5-r"><div class="a5-l"><span class="a5-av" aria-hidden="true">🐎</span><span class="a2-hn"><b>${mark(o.ad,q)}</b><small>${tg}Son koşu <b>${E(ddmm(z.son))}</b> · ${E(z.hip)}${z.der?` · ${z.der}.`:""} · ${z.n} koşu</small><small>${z.antrenor?"Antrenör "+E(z.antrenor):""}${z.antrenor&&z.jokey?" · ":""}${z.jokey?"son jokey "+E(z.jokey):""}</small></span></div>${tkBtn("at",o.ad)}</div>`;
    return `<div class="a2-hrow a5-r"><a class="a5-l" href="#at/${o.k}/${enc(o.ad)}" data-a5r="${E(o.ad)}"><span class="a5-av" aria-hidden="true">${AV[o.k]}</span><span class="a2-hn"><b>${mark(o.ad,q)}</b><small>${tg}Son 90 gün ${z.n90} ${o.k==="jokey"?"biniş":"koşu"}${z.n90?` · ${z.w90} birincilik · ilk 3 ${P(z.i90/z.n90)}`:""}</small><small>Son koşu ${E(ddmm(z.son))} · ${E(z.hip)}</small></span></a>${tkBtn(o.k,o.ad)}</div>`; }
  function results(){ const q=Q(U.q), kinds=U.k==="tum"?null:[U.k];
    if(!q.f){ const R=recent(); let h=R.length?`<h2 class="a2-sec">Son aramalar</h2><div class="a2-chips" role="group" aria-label="Son aramalar">${R.map(x=>`<button class="a2-chip" type="button" data-a5q="${E(x)}">${E(x)}</button>`).join("")}<button class="a2-chip" type="button" data-a5x="1" aria-label="Son aramaları temizle">Temizle</button></div>`:"";
      h+=`<div class="a2-card a5-hint"><p class="a2-note">At, jokey ya da antrenör adının bir kısmını yaz. Türkçe harf gerekmez (<b>ozcelik</b> → ÖZÇELİK), küçük yazım hataları da bulunur.</p><p class="a2-note">Önce <b>bugünün ve yarının programı</b> (saat, hipodrom, koşu no), sonra <b>son 1 yılın arşivi</b>. ☆ ile takip listene ekle; takip ettiğin at koşmadan 30 dk önce hatırlatırım.</p></div>`;
      return h+dzNote(); }
    const R=find(U.q,kinds); let h="";
    h+=`<h2 class="a2-sec">📅 Program · bugün ve yarın <span class="a2-mut" style="text-transform:none;letter-spacing:0;font-weight:600">· ${R.prog.length}</span></h2>`;
    h+=R.prog.length?`<div class="a2-card">${R.prog.slice(0,U.nP).map(z=>rowProg(z,q)).join("")}${R.prog.length>U.nP?`<button class="a2-btn q a5-more" type="button" data-a5m="p">${R.prog.length-U.nP} sonuç daha</button>`:""}</div>`
      :`<div class="a2-card"><p class="a2-note" style="margin:0">${(prog().at.length?"Bugün ve yarın programında bu adla eşleşen yok.":"Bugün ve yarın için program henüz yüklenmedi.")}</p></div>`;
    h+=`<h2 class="a2-sec">🗂️ Arşiv · son 1 yıl <span class="a2-mut" style="text-transform:none;letter-spacing:0;font-weight:600">· ${DZ.at?R.gec.length:"…"}</span></h2>`;
    if(DZ.v===undefined) h+=`<div class="a2-card"><div class="a2-sk" style="height:52px;margin:0"></div><p class="a2-sr">Arşiv yükleniyor</p></div>`;
    else if(!DZ.v) h+=`<div class="a2-card"><p class="a2-note" style="margin:0">Arşiv dizini şu an yüklenemedi; program sonuçları yukarıda.</p></div>`;
    else h+=R.gec.length?`<div class="a2-card">${R.gec.slice(0,U.nG).map(o=>rowGec(o,q)).join("")}${R.gec.length>U.nG?`<button class="a2-btn q a5-more" type="button" data-a5m="g">${R.gec.length-U.nG} sonuç daha</button>`:""}</div>`
      :`<div class="a2-card"><p class="a2-note" style="margin:0">${R.prog.length?"Arşivde başka eşleşme yok.":"Arşivde de eşleşme yok. Adın bir kısmını ya da başka yazımını dene."}</p></div>`;
    return h+dzNote(); }
  function dzNote(){ const v=DZ.v; return v?`<p class="a5-st">Arşiv: ${v.atlar.length.toLocaleString("tr-TR")} at · ${v.jk.length} jokey · ${v.an.length} antrenör · son sonuç ${E(ddmm(v.son_sonuc))}. Kaynak: açık yarış sonuç arşivi, yalnız türetilmiş özet. Para tutarı yok · 18+</p>`:""; }
  function screen(){ return `<div class="a5-ara"><div class="a5-sf" role="search">${IC.lu}<input id="a5q" type="search" value="${E(U.q)}" placeholder="At, jokey ya da antrenör adı" aria-label="At, jokey ya da antrenör ara" autocomplete="off" autocapitalize="characters" spellcheck="false" enterkeyhint="search" aria-describedby="a5cnt"><button class="a5-cl" type="button" data-a5c="1" aria-label="Aramayı temizle"${U.q?"":" hidden"}>${IC.x}</button></div>
      <div class="a2-chips a5-k" role="group" aria-label="Ne aranıyor">${[["tum","Tümü"],["at","At"],["jokey","Jokey"],["antrenor","Antrenör"]].map(([k,l])=>`<button class="a2-chip" type="button" data-a5k="${k}" aria-pressed="${U.k===k}">${l}</button>`).join("")}</div>
      <span id="a5cnt" class="a2-sr"></span><div id="a5res">${results()}</div></div>`; }
  function paintRes(){ const r=$("a5res"); if(!r) return; r.innerHTML=results(); const c=$("a5cnt"); if(c){ const q=Q(U.q); if(q.f){ const R=find(U.q,U.k==="tum"?null:[U.k]); c.textContent=`${R.prog.length} program, ${R.gec.length} arşiv sonucu`; } else c.textContent=""; }
    const cl=box.querySelector(".a5-cl"); if(cl) cl.hidden=!U.q; }
  let mine=false;
  function openAra(){ mine=true; box.innerHTML=screen(); const bt=nav.querySelector(".a2-bt"); if(bt){ bt.textContent="Ara"; bt.classList.remove("hid"); }
    const inp=$("a5q"); dzLoad(); if(DZ.p) DZ.p.then(()=>{ if(route().v==="ara") paintRes(); });
    if(inp){ inp.addEventListener("input",()=>{ U.q=inp.value; U.nP=12; U.nG=20; clearTimeout(U.t); U.t=setTimeout(paintRes,110); });
      inp.addEventListener("focus",()=>{ U.foc=true; }); inp.addEventListener("blur",()=>{ setTimeout(()=>{ if(document.activeElement!==$("a5q")) U.foc=false; },0); });
      inp.addEventListener("keydown",e=>{ if(e.key==="Enter"){ e.preventDefault(); clearTimeout(U.t); paintRes(); remember(U.q); try{ inp.blur(); }catch(_){} }
        else if(e.key==="Escape"){ if(inp.value){ e.preventDefault(); inp.value=""; U.q=""; paintRes(); } }
        else if(e.key==="ArrowDown"){ const f=box.querySelector("#a5res a.a5-l, #a5res button"); if(f){ e.preventDefault(); f.focus(); } } }); }
    // odak: ilk açılışta ve yeniden boyamada (takip düğmesine basılınca at2 ekranı tazeler) yerinde kalsın
    if(U.lastTk){ const b=[...box.querySelectorAll("[data-tk]")].find(x=>x.dataset.tk===U.lastTk); U.lastTk=null; if(b){ try{ b.focus({preventScroll:true}); }catch(_){} return; } }
    if(inp&&(U.foc||U.first)){ U.first=false; try{ inp.focus({preventScroll:true}); const n=inp.value.length; inp.setSelectionRange(n,n); }catch(_){} } }
  box.addEventListener("click",e=>{ const b=e.target.closest("[data-a5k],[data-a5q],[data-a5x],[data-a5c],[data-a5m],[data-tk],a[data-a5r]"); if(!b||!box.contains(b)||route().v!=="ara") return;
    const d=b.dataset;
    if(d.tk!=null){ U.lastTk=d.tk; remember(U.q); return; }            // takip: at2 işler (toast + yeniden boyama)
    if(b.matches("a[data-a5r]")){ remember(U.q); return; }              // profil: at2 yönlendirir
    e.preventDefault(); e.stopPropagation(); tap();
    if(d.a5k){ U.k=d.a5k; U.nP=12; U.nG=20; box.querySelectorAll("[data-a5k]").forEach(x=>x.setAttribute("aria-pressed",x.dataset.a5k===U.k)); paintRes(); return; }
    if(d.a5q!=null){ U.q=d.a5q; const i=$("a5q"); if(i){ i.value=U.q; } paintRes(); return; }
    if(d.a5x){ lsS("bx-at-ara-son",[]); paintRes(); const i=$("a5q"); if(i) i.focus(); return; }
    if(d.a5c){ U.q=""; const i=$("a5q"); if(i){ i.value=""; i.focus(); } paintRes(); return; }
    if(d.a5m){ if(d.a5m==="p") U.nP+=24; else U.nG+=40; paintRes(); return; } },true);
  // kısayol: At bölümünde "/" → arama
  document.addEventListener("keydown",e=>{ if(e.key!=="/"||e.ctrlKey||e.metaKey||e.altKey||sec.hidden) return; const t=e.target; if(t&&(t.isContentEditable||/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
    if(!$("sheet")||$("sheet").hidden){ e.preventDefault(); goAra(); } });
  function goAra(){ U.first=true; A2.go("ara",true); }

  // =====================================================================
  // "Atım koşuyor" hatırlatması
  // =====================================================================
  const PR=()=>{ const p=lsJ("bx-at-hatirlat",{}); return {on:p.on!==false,sys:p.sys===true}; };
  const setPR=o=>{ lsS("bx-at-hatirlat",Object.assign(PR(),o)); refresh(); };
  const IZ=()=>{ const z=lsJ("bx-at-hatirlat-iz",{}), t=today(); return z&&z.d===t?{d:t,k:Array.isArray(z.k)?z.k:[],x:Array.isArray(z.x)?z.x:[]}:{d:t,k:[],x:[]}; };
  const setIZ=z=>lsS("bx-at-hatirlat-iz",{d:z.d,k:z.k.slice(-200),x:z.x.slice(-200)});
  const WIN=30;   // dakika
  // bugün koşan takipler (başlamamış koşular), en yakın önce
  function followed(){ const t0=today(), tk=TK(); if(!(tk.at.length+tk.jokey.length+tk.antrenor.length)) return [];
    const out=[]; for(const it of prog().at){ if(it.d!==t0) continue; const st=stOf(it); if(st.s!=="bekliyor"&&st.s!=="yakin") continue;
      const why=isTk("at",it.ad)?"at":isTk("jokey",it.jokey)?"jokey":isTk("antrenor",it.antrenor)?"antrenor":null; if(!why) continue;
      out.push({it,why,key:it.r.kosu_id+"|"+it.no,mn:Math.max(0,Math.ceil((it.t-NOW())/6e4))}); }
    return out.sort((a,b)=>a.it.t-b.it.t); }
  const due=()=>followed().filter(o=>o.mn<=WIN);
  function sentence(o){ const it=o.it, s=E(it.r.saat)+ekDa(it.r.saat);
    if(o.why==="jokey") return `Takip ettiğin jokey <b>${E(it.jokey)}</b> ${s} koşuyor <small>· ${E(it.ad)}</small>`;
    if(o.why==="antrenor") return `Takip ettiğin antrenörün atı <b>${E(it.ad)}</b> ${s} koşuyor`;
    return `Takip ettiğin at <b>${E(it.ad)}</b> ${s} koşuyor`; }
  const plain=o=>sentence(o).replace(/<[^>]+>/g,"").replace(/&#39;/g,"'").replace(/&amp;/g,"&");
  const hrefOf=o=>`at/${K(o.it.r.kosu_id)}/${enc(o.it.no)}`;
  // ---- uygulama geneli ince şerit ----
  const strip=document.createElement("div"); strip.id="a5Strip"; strip.hidden=true; strip.setAttribute("role","status");
  (function(){ const pg=document.querySelector("main.page"); if(pg) pg.insertBefore(strip,pg.firstChild); else document.body.appendChild(strip); })();
  function openTarget(path){ try{ if($("v-at").hidden) showSport("at"); }catch(e){} try{ A2.go(path,true); }catch(e){ location.hash="#"+path.replace(/^#?/,""); } }
  strip.addEventListener("click",e=>{ const b=e.target.closest("button"); if(!b) return; tap();
    if(b.classList.contains("x")){ const z=IZ(); for(const o of due()) if(!z.x.includes(o.key)) z.x.push(o.key); setIZ(z); strip.hidden=true; toast("Hatırlatma kapatıldı · At › Bugün'de görünmeye devam eder"); return; }
    const k=b.dataset.k, o=due().find(x=>x.key===k); if(o) openTarget(hrefOf(o)); else openTarget("bugun"); });
  function atBugun(){ return !sec.hidden&&route().v==="bugun"; }
  function paintStrip(D){ const pr=PR(), z=IZ(), L=(D||[]).filter(o=>!z.x.includes(o.key));
    if(!pr.on||!L.length||atBugun()){ if(!strip.hidden) strip.hidden=true; return; }
    const o=L[0], more=L.length>1?` · +${L.length-1}`:"";
    const html=`<div class="in"><button class="go" type="button" data-k="${E(o.key)}" aria-label="${E(plain(o))}, ${o.mn} dakika sonra. At bölümünde aç"><span aria-hidden="true">🐎</span><span>${sentence(o)}</span><span class="m">${o.mn} dk${more}</span></button><button class="x" type="button" aria-label="Hatırlatmayı kapat">${IC.x}</button></div>`;
    if(strip.innerHTML!==html) strip.innerHTML=html; if(strip.hidden){ strip.hidden=false; if(!SES_SR.has(o.key)){ SES_SR.add(o.key); try{ Sound.olay&&Sound.olay("atSerit"); }catch(e){} } } }
  const SES_SR=new Set();   // v121: şerit sesi her koşu için oturumda bir kez
  // ---- At Bugün kartı ----
  function dueCard(D){ if(!PR().on||!D.length) return "";
    return `<div class="a2-card gold a5-due" data-a5d><div class="a2-ch"><h2><i aria-hidden="true">🔔</i> Atım koşuyor</h2><small>${WIN} dk içinde</small></div>${D.slice(0,5).map(o=>`<a class="a2-hrow" href="#${hrefOf(o)}"><span class="a2-no">${E(o.it.no)}</span><span class="a2-hn"><b>${E(o.it.ad)}</b><small>${E(o.it.r.hipodrom)} ${o.it.r.kosu}. koşu · ${E(o.it.r.saat)}${o.why!=="at"?" · "+(o.why==="jokey"?"jokey ":"antrenör ")+E(o.it[o.why]):""}</small></span><span class="a2-pill">${o.mn} dk</span></a>`).join("")}
      <p class="a2-note">Takip listendekiler koşudan ${WIN} dk önce burada ve uygulamanın üstünde görünür. Ayarlar › At yarışı bölümünden kapatabilirsin.</p></div>`; }
  function decoBugun(D){ if(box.querySelector("[data-a5d]")) return; const h=dueCard(D); if(!h) return; const first=box.querySelector(":scope > .a2-card, :scope > .a2-sec"); if(first) first.insertAdjacentHTML("beforebegin",h); }
  // ---- uygulama içi hatırlatma (toast) + isteğe bağlı sistem bildirimi; her koşu için bir kez ----
  function fire(D){ if(!PR().on||!D.length) return; const z=IZ(), yeni=D.filter(o=>!z.k.includes(o.key)); if(!yeni.length) return;
    yeni.forEach(o=>z.k.push(o.key)); setIZ(z); const o=yeni[0];
    if(!document.hidden){ try{ toast("🐎 "+plain(o)+` · ${o.mn} dk`); }catch(e){} try{ buzz([10,40,10]); }catch(e){} try{ Sound.olay&&Sound.olay("atCagri"); }catch(e){} }
    sysNote(o,yeni.length); }
  function sysNote(o,n){ const pr=PR(); if(!pr.sys||!("Notification" in window)||Notification.permission!=="granted") return;
    const title="🐎 Atım koşuyor", body=plain(o)+` · ${o.it.r.hipodrom} ${o.it.r.kosu}. koşu · ${o.mn} dk sonra`+(n>1?` (+${n-1})`:""), url="./#"+hrefOf(o);
    const opt={body,icon:"icons/oxxai-192.png",badge:"icons/oxxai-192.png",tag:"at-"+o.key,data:{url}};
    const fb=()=>{ try{ const x=new Notification(title,opt); x.onclick=()=>{ try{ window.focus(); }catch(_){} openTarget(hrefOf(o)); x.close(); }; }catch(_){} };
    try{ if(navigator.serviceWorker&&navigator.serviceWorker.controller) navigator.serviceWorker.ready.then(r=>r.showNotification(title,opt)).catch(fb); else fb(); }catch(_){ fb(); } }
  // v121: takip edilen at start aldı / kazandı → ses + ekran uyarısı (mevcut 30 sn denetimine biner; yeni zamanlayıcı yok)
  function sesTara(){ if(!window.Sound||!Sound.olay) return; let L=[]; const t0=today();
    try{ const tk=TK(); if(!tk.at.length) return; L=prog().at.filter(it=>it.d===t0&&isTk("at",it.ad)); }catch(e){ return; }
    const z=lsJ("bx-ses-at",{}), k=z&&z.d===t0&&Array.isArray(z.k)?z.k:[]; let ch=false;
    for(const it of L){ const key=it.r.kosu_id+"|"+it.no, st=stOf(it), age=(NOW()-it.t)/6e4;
      if(st.s==="basladi"&&!k.includes("s"+key)){ k.push("s"+key); ch=true; if(age<=3&&!document.hidden){ try{ toast(`🐎 ${it.ad} koşuya çıktı · ${it.r.hipodrom} ${it.r.kosu}. koşu`); }catch(e){} Sound.olay("atStart"); } }
      if(st.s==="bitti"&&!k.includes("w"+key)){ k.push("w"+key); ch=true; const S=it.c&&it.c.sonuc;
        if(S&&String((S.sira||[])[0])===String(it.no)&&age<=120&&!document.hidden){ try{ toast(`🏆 Takip ettiğin at ${it.ad} kazandı! · ${it.r.hipodrom} ${it.r.kosu}. koşu`); buzz([30,40,30,40,120]); }catch(e){} Sound.olay("atKazandi"); } } }
    if(ch) lsS("bx-ses-at",{d:t0,k:k.slice(-200)}); }
  function refresh(){ let D=[]; try{ D=due(); }catch(e){} paintStrip(D); fire(D); try{ sesTara(); }catch(e){} try{ const mi=$("a5MenuOn"); if(mi) mi.checked=PR().on; }catch(e){}
    if(atBugun()){ const c=box.querySelector("[data-a5d]"); if(c) c.remove(); decoBugun(D); } }
  setInterval(()=>{ if(!document.hidden||PR().sys) refresh(); },30000);
  document.addEventListener("visibilitychange",()=>{ if(!document.hidden) refresh(); });
  window.addEventListener("storage",e=>{ if(!e.key||/^bx-at-(fav|takip|hatirlat)/.test(e.key)) refresh(); });
  const _ld=X.load; X.load=async function(){ const r=await _ld.apply(this,arguments); try{ refresh(); }catch(e){} return r; };
  // takipte biri varsa ve veri henüz yüklenmediyse (futbol tarafında açılış) at verisini sessizce yükle — yalnız depodaki dosyalar
  setTimeout(()=>{ try{ const tk=TK(); if(PR().on&&(tk.at.length+tk.jokey.length+tk.antrenor.length)&&!(AT.days||[]).length&&!AT.busy) X.load(); }catch(e){} },2500);
  // ---- Ayarlar sayfası: anahtar + ayrı "sistem bildirimi" düğmesi ----
  const sysTxt=()=>{ const pr=PR(); if(!("Notification" in window)) return "Bu tarayıcı desteklemiyor · uygulama içi hatırlatma çalışır";
    if(Notification.permission==="denied") return "Tarayıcı izni kapalı · telefon ayarlarından açılabilir";
    if(Notification.permission==="granted"&&pr.sys) return "Açık · uygulama açıkken telefon bildirimi de gelir";
    return "Kapalı · istersen uygulama açıkken telefon bildirimi de gelsin"; };
  const sysBtnTxt=()=>{ const pr=PR(); return ("Notification" in window)&&Notification.permission==="granted"&&pr.sys?"Kapat":"İzin ver"; };
  async function sysToggle(){ if(!("Notification" in window)){ toast("Bu tarayıcı bildirim desteklemiyor"); return; }
    const pr=PR(); if(pr.sys&&Notification.permission==="granted"){ setPR({sys:false}); toast("At sistem bildirimi kapatıldı"); return; }
    let p=Notification.permission; if(p==="default"){ try{ p=await Notification.requestPermission(); }catch(e){ p=Notification.permission; } }
    if(p==="granted"){ setPR({sys:true,on:true}); toast("🔔 Atın koşmadan 30 dk önce telefon bildirimi de gelir (uygulama açıkken)"); }
    else toast(p==="denied"?"Bildirim izni kapalı; telefon ayarlarından açabilirsin":"İzin verilmedi"); }
  function setRows(){ const pr=PR();
    return `<div class="lg-h" id="a5SetH"><h3>🐎 At yarışı</h3></div><div class="group" id="a5Set"><label class="cell a5-mc"><span class="ic" style="background:#B8892B;font-size:15px;display:grid;place-items:center" aria-hidden="true">🐎</span><span class="tx"><b>Atım koşuyor hatırlatması</b><small>Takip ettiğin at, jokey ya da antrenör koşudan 30 dk önce, uygulama içinde</small></span>
      <span class="sw"><input type="checkbox" id="a5On" ${pr.on?"checked":""} aria-label="Atım koşuyor hatırlatması"><i></i></span></label>
      <div class="cell"><span class="ic" style="background:#FF375F"><svg viewBox="0 0 24 24"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0"/></svg></span><span class="tx"><b>At için telefon bildirimi</b><small id="a5SysSt">${E(sysTxt())}</small></span><button class="btn sm ghost" type="button" id="a5SysBtn">${sysBtnTxt()}</button></div></div>`; }
  function wireSet(root){ const on=root.querySelector("#a5On"), sb=root.querySelector("#a5SysBtn");
    if(on) on.addEventListener("change",()=>{ setPR({on:on.checked}); try{ buzz(6); }catch(e){} toast(on.checked?"🐎 Atım koşuyor hatırlatması açık":"Atım koşuyor hatırlatması kapalı"); });
    if(sb) sb.addEventListener("click",async()=>{ await sysToggle(); const s=root.querySelector("#a5SysSt"); if(s) s.textContent=sysTxt(); sb.textContent=sysBtnTxt(); }); }
  const sh=$("sheet");
  if(sh) new MutationObserver(()=>{ const bx=sh.querySelector('.box[aria-label="Ayarlar"]'); if(!bx||bx.querySelector("#a5Set")) return;
      const groups=bx.querySelectorAll(":scope > .group"), at=groups[1]||groups[0]; if(!at) return; at.insertAdjacentHTML("afterend",setRows()); wireSet(bx); }).observe(sh,{childList:true});
  // ---- Takip ekranındaki "yakında" kartı → çalışan denetim ----
  function decoTakip(){ const c=[...box.querySelectorAll(":scope > .a2-card")].find(x=>/Atım koşuyor/.test((x.querySelector("h2")||{}).textContent||"")); if(!c||c.dataset.a5t) return;
    const pr=PR(), D=followed(); c.dataset.a5t="1";
    c.innerHTML=`<div class="a2-ch"><h2>🔔 “Atım koşuyor” hatırlatması</h2>${D.length?`<small>bugün ${D.length} koşu</small>`:""}</div>
      <div class="a5-ctl"><span class="tx"><b>Uygulama içi hatırlatma</b><small>Koşudan ${WIN} dk önce At › Bugün'de ve uygulamanın üstünde ince şerit</small></span><button class="a5-sw" type="button" role="switch" aria-checked="${pr.on}" data-a5on="1" aria-label="Atım koşuyor hatırlatması"></button></div>
      <div class="a5-ctl"><span class="tx"><b>Telefon bildirimi</b><small data-a5ss>${E(sysTxt())}</small></span><button class="a2-btn q a5-nb" type="button" data-a5sys="1">${sysBtnTxt()}</button></div>
      <p class="a2-note" style="margin:8px 2px 0">${D.length?`Sıradaki: ${E(plain(D[0]))}.`:"Bugün başlamamış koşularda takip listenden kimse yok."} Bildirim yalnız uygulama açıkken gelir; sunucuya hiçbir şey gönderilmez, ayar bu telefonda kalır.</p>`; }
  box.addEventListener("click",async e=>{ const b=e.target.closest("[data-a5on],[data-a5sys]"); if(!b||!box.contains(b)) return; e.preventDefault(); e.stopPropagation(); tap();
    if(b.dataset.a5on){ const v=b.getAttribute("aria-checked")!=="true"; setPR({on:v}); b.setAttribute("aria-checked",v); toast(v?"🐎 Atım koşuyor hatırlatması açık":"Atım koşuyor hatırlatması kapalı"); return; }
    await sysToggle(); b.textContent=sysBtnTxt(); const s=box.querySelector("[data-a5ss]"); if(s) s.textContent=sysTxt(); },true);

  // =====================================================================
  // Boyama kancası: at2 #at2Box'u her yazdığında
  // =====================================================================
  function route(){ try{ return A2.route(); }catch(e){ return {v:"bugun",a:[]}; } }
  function searchBtn(){ const hd=box.querySelector(":scope > .a2-hd"); if(!hd||hd.querySelector(".a5-sb")) return;
    const a=document.createElement("a"); a.className="a2-ib a5-sb"; a.href="#at/ara"; a.setAttribute("aria-label","Ara: at, jokey ya da antrenör"); a.innerHTML=IC.lu2;
    const f=hd.querySelector(".a2-ib"); if(f) hd.insertBefore(a,f); else hd.appendChild(a); }
  function enhance(){ const rt=route(); try{
      if(rt.v==="ara"){ if(!box.querySelector(":scope > .a5-ara")) openAra(); return; }
      searchBtn();
      if(rt.v==="bugun"){ let D=[]; try{ D=due(); }catch(e){} decoBugun(D); paintStrip(D); }
      else if(rt.v==="takip") decoTakip();
    }catch(e){ console.error(e); } }
  new MutationObserver(()=>{ if(mine){ mine=false; return; } enhance(); }).observe(box,{childList:true});
  // 🔍 bağlantısı: at2'nin bağlantı yakalayıcısı #at/ara'yı pushState ile açar; ilk açılışta giriş kutusuna odaklan
  box.addEventListener("click",e=>{ const a=e.target.closest("a.a5-sb"); if(a) U.first=true; },true);
  // At'tan çıkınca / At'a girince şerit görünürlüğü
  new MutationObserver(()=>refresh()).observe(sec,{attributes:true,attributeFilter:["hidden"]});
  window.addEventListener("hashchange",()=>setTimeout(()=>{ try{ paintStrip(due()); }catch(e){} },40));

  // =====================================================================
  // OXX: "X atı bugün koşuyor mu" · "jokey Y bugün nerede" (dar kalıp; eşleşme yoksa sıradaki at niyetine bırakır)
  // =====================================================================
  const STOP=new Set(("at ati atin atim atlar atlari atlarim atlarin adli isimli isminde jokey jokeyi jokeyin jokeyim antrenor antrenoru antrenorun antrenorum "+
    "bugun yarin bu aksam aksamki gece sabah kosuyor kosacak kosar kosarmi kosuyormu kosacakmi kostu kosmuyor kosmayacak kosu kosusu kosuda kosulari kosulara "+
    "mu mi mı var mii ne zaman saat kacta kac nerede nerde neredee hangi hangisi biniyor binecek biniyormu binis binisi binisleri binisler bindigi atlari atlarini "+
    "hipodrom hipodromda yaris yarisi yarisinda acaba bana soyle goster bak bakar misin musun takip ettigim ettigin benim program programda icin de da ile olan kim neler gun "+
    "istanbul ankara izmir bursa adana sanliurfa urfa elazig diyarbakir kocaeli izmit antalya veliefendi").split(" "));
  function botTokens(n){ return n.split(" ").filter(w=>w&&!STOP.has(w)&&!/^\d+$/.test(w)); }
  async function a5Bot(raw){ const n=F(raw); if(!n||n.length>90) return null;
    const horseQ=/\bkos(uyor|acak|ar|ma|tu|uyo)\w*/.test(n)||/\bne zaman kos/.test(n);
    const kJ=/\bjokey\w*/.test(n), kA=/\bantrenor\w*/.test(n), whereQ=/\b(nerede|nerde|biniyor\w*|binecek\w*|binis\w*|bindigi|hangi (at|kosu|hipodrom)\w*|atlari\w*)\b/.test(n);
    if(!horseQ&&!((kJ||kA)&&whereQ)) return null;
    if(/\b(mac\w*|gol\w*|takim\w*|lig|ligi|futbol|basket\w*|oynuyor\w*|iddaa|kupon\w*|6 ?li|altili|ganyan|plase|ikili|tabela)\b/.test(n)) return null;
    const T=botTokens(n), mineQ=/\b(atim|atlarim|takip)\b/.test(n);
    if(!(AT.days||[]).length){ try{ await X.load(); }catch(e){} }
    try{ await dzLoad(); }catch(e){}
    const tail=`<br><small>Hobi amaçlı olasılıktır, garanti değildir · 18+</small>`, ch=["At bölümünü aç","Altın atlar"];
    if(!T.length){ if(!mineQ) return null; const L=followed(); const tk=TK();
      if(!(tk.at.length+tk.jokey.length+tk.antrenor.length)) return {html:"⭐ Takip listende henüz at, jokey ya da antrenör yok. At profilindeki ☆ Takip et ile ekle; koşmadan 30 dk önce hatırlatırım.",chips:ch};
      return {html:L.length?`🐎 Bugün takip listenden koşanlar:<ul class="bt-ul">${L.slice(0,6).map(o=>`<li><b>${E(o.it.r.saat)}</b> · ${E(o.it.r.hipodrom)} ${o.it.r.kosu}. koşu · ${E(o.it.ad)}${o.why!=="at"?` (${o.why==="jokey"?"jokey":"antrenör"} ${E(o.it[o.why])})`:""}</li>`).join("")}</ul>`+tail
        :"🐎 Bugün başlamamış koşularda takip listenden kimse yok.",chips:ch}; }
    const qs=T.join(" "), kinds=kJ&&!kA?["jokey"]:kA&&!kJ?["antrenor"]:(kJ&&kA)?["jokey","antrenor"]:(/\bat(i|in)?\b/.test(n)?["at"]:["at","jokey","antrenor"]);
    const R=find(qs,kinds), q=Q(qs), strong=s=>s>=q.T.length*1.0;
    const P0=R.prog.filter(z=>strong(z.s)), G0=R.gec.filter(o=>strong(o.s));
    const best=P0[0]&&(!G0[0]||P0[0].s>=G0[0].s-.6)?{src:"p",z:P0[0]}:G0[0]?{src:"g",z:G0[0]}:null;
    if(!best){ if(!(kJ||kA||/\bati\b/.test(n))) return null; return {html:`🔎 “${E(qs.toLocaleUpperCase("tr"))}” adıyla bugünün programında da son 1 yılın arşivinde de ${kJ?"jokey":kA?"antrenör":"at"} bulamadım. At Yarışı › 🔍 Ara'da adın bir kısmıyla deneyebilirsin.`,chips:ch}; }
    const tD=today();
    if(best.src==="p"){ const z=best.z;
      if(z.k==="at"){ const L=z.L, Lt=L.filter(it=>it.d===tD), it0=(Lt[0]||L[0]), st=stOf(it0);
        const li=L.map(it=>{ const s=stOf(it); return `<li>${E(dLbl(it.d))} <b>${E(it.r.saat)}</b> · ${E(it.r.hipodrom)} ${it.r.kosu}. koşu · ${E(it.r.mesafe)} m ${E(it.r.pist)} · no ${E(it.no)}${it.jokey?" · jokey "+E(it.jokey):""}${it.p!=null?` · OXX kazanma <b>${P(it.p)}</b>`:""}${s.s==="bitti"||s.s==="kosmaz"||s.s==="basladi"?" · "+E(s.t.toLocaleLowerCase("tr")):""}</li>`; }).join("");
        const ev=Lt.length?(st.s==="bitti"?`🐎 <b>${E(z.ad)}</b> bugün koştu:`:st.s==="kosmaz"?`🐎 <b>${E(z.ad)}</b> bugün programdaydı ama koşmuyor:`:`🐎 Evet, <b>${E(z.ad)}</b> bugün koşuyor:`):`🐎 <b>${E(z.ad)}</b> bugün yok, ${E(dLbl(it0.d).toLocaleLowerCase("tr"))} koşuyor:`;
        return {html:`${ev}<ul class="bt-ul">${li}</ul>${isTk("at",z.ad)?"⭐ Takip listende; koşmadan 30 dk önce hatırlatırım.":"At profilinden ☆ Takip et dersen koşmadan 30 dk önce hatırlatırım."}${tail}`,chips:ch}; }
      const L=z.L, kd=z.k==="jokey"?"Jokey":"Antrenör", Lt=L.filter(it=>it.d===tD), LL=Lt.length?Lt:L, gun=Lt.length?"bugün":dLbl(L[0].d).toLocaleLowerCase("tr");
      const hips=[...new Set(LL.map(it=>it.r.hipodrom))];
      return {html:`${z.k==="jokey"?"🏇":"🧑‍🏫"} ${kd} <b>${E(z.ad)}</b> ${Lt.length?"":"bugün programda yok; "}${E(gun)} <b>${E(hips.join(", "))}</b>'da ${LL.length} ${z.k==="jokey"?"binişte":"atla"}:<ul class="bt-ul">${LL.slice(0,10).map(it=>{ const s=stOf(it); return `<li><b>${E(it.r.saat)}</b> · ${E(it.r.hipodrom)} ${it.r.kosu}. koşu · ${E(it.ad)} (no ${E(it.no)})${it.p!=null?` · OXX ${P(it.p)}`:""}${s.s==="bitti"||s.s==="kosmaz"?" · "+E(s.t.toLocaleLowerCase("tr")):""}</li>`; }).join("")}</ul>${tail}`,chips:ch}; }
    const o=best.z, z=o.z;
    if(o.k==="at") return {html:`🐎 <b>${E(o.ad)}</b> bugün ve yarın programda yok. Son koşusu <b>${E(ddmm(z.son))}</b> ${E(z.hip)}${z.der?`, ${z.der}. oldu`:""}; arşivde ${z.n} koşusu var${z.antrenor?` · antrenör ${E(z.antrenor)}`:""}.<br>At profilinden ya da 🔍 Ara'dan ☆ ile takip edersen programa girdiği gün hatırlatırım.`,chips:ch};
    return {html:`${o.k==="jokey"?"🏇":"🧑‍🏫"} ${o.k==="jokey"?"Jokey":"Antrenör"} <b>${E(o.ad)}</b> bugün ve yarın programda yok. Son 90 günde ${z.n90} ${o.k==="jokey"?"biniş":"koşu"}${z.n90?`, ${z.w90} birincilik (ilk 3 ${P(z.i90/z.n90)})`:""}; son koşusu ${E(ddmm(z.son))} ${E(z.hip)}.`,chips:ch}; }
  window.BX_AT5={find,prog,dzLoad,due,followed,refresh,bot:a5Bot,F,ekDa};
  if(typeof botAnswer==="function"){ const _ba=botAnswer; botAnswer=async function(raw){ try{ const r=await a5Bot(raw); if(r) return r; }catch(e){ console.error(e); } return _ba.apply(this,arguments); }; }
  enhance(); setTimeout(refresh,1200);
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: at5-v116 */
