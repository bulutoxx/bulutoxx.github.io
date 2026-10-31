/* id: ses-v121 */ try {
// =====================================================================
// OXXai v121 · SES KİMLİĞİ — tamamen prosedürel (Web Audio), sıfır dosya, sıfır lisans yükü.
// • Palet: D majör "altın" (FM çan, oran 3,5) + "elektrik mavisi" (FM oran 2, parlak), sıcak brass, sentez kalabalık.
//   İmza motifi "O-X-X": D5 → A5 → F#6 (yükselen beşli + parlak onlu). Bütün olay sesleri bu tonalitede ve motifle kapanır.
// • Zincir: ses → (kuru + kendi ürettiğimiz kısa oda yankısı/konvolüsyon) → yüksek geçiren → yumuşak tiz rafı → yapıştırıcı kompresör
//   → ana ses düzeyi → limiter → yumuşak kırpıcı (tepe her koşulda ≤ −1,5 dBFS).
// • Kurallar: yalnız üst çubuktaki Ses modu "Ses ve titreşim" iken çalar (titreşim/sessiz modda yalnız titreşim);
//   Ayarlar › Sesler'de kategori anahtarları + ana ses düzeyi + "Sesleri dinle". Gol sesi yalnız yıldızla takip edilen maçta.
// • iOS: AudioContext ilk dokunuşta açılır (unlock). Uygulama arka plandayken ses çalınmaz (sistem bildirimi ayrı).
// • Pil: boşta AudioContext askıya alınır — zamanlayıcı yok; son sesin ardından biten sessiz bir kaynak (onended) askıya alır.
// • Olay kaynakları ayrı kalır: futbol (Live/IDL farkı), basket (IDL sp=2 + KUPO bacakları), at (at5 hatırlatma), KUPO (kxGrade).
//   Bu blok yalnız ortak ses motoru + futbol/basket maç olayı farkını ve arayüz kancalarını içerir.
// =====================================================================
(function(){
  "use strict";
  if(typeof Sound==="undefined"||typeof PREFS==="undefined") return;
  const W=window, D=document;
  const DEF={sesGol:true,sesKupo:true,sesAt:true,sesBasket:true,sesMenu:true,sesAnons:true,sesVol:.8};
  let chg=false; for(const k in DEF) if(PREFS[k]==null){ PREFS[k]=DEF[k]; chg=true; } if(chg) try{ savePrefs(); }catch(e){}
  const RM=()=>{ try{ return matchMedia("(prefers-reduced-motion: reduce)").matches; }catch(e){ return false; } };

  // ---------- nota tablosu (D majör) ----------
  const NT={D3:146.83,A3:220,D4:293.66,Eb4:311.13,E4:329.63,F4:349.23,Fs4:369.99,G4:392,A4:440,B4:493.88,Cs5:554.37,D5:587.33,E5:659.25,F5:698.46,Fs5:739.99,
    G5:783.99,A5:880,B5:987.77,Cs6:1108.73,D6:1174.66,E6:1318.51,Fs6:1479.98,A6:1760};
  const MOTIF=[NT.D5,NT.A5,NT.Fs6];
  const rng=seed=>{ let s=(seed>>>0)||1; return ()=>{ s=(Math.imul(s,1664525)+1013904223)>>>0; return s/4294967296; }; };

  // ---------- yapı taşları ----------
  const NB=new Map(), IRC=new Map();
  function nbuf(c){ const sr=c.sampleRate; let b=NB.get(sr); if(b) return b; const n=Math.floor(sr*2); b=c.createBuffer(1,n,sr); const x=b.getChannelData(0), r=rng(12345);
    for(let i=0;i<n;i++) x[i]=r()*2-1; NB.set(sr,b); return b; }
  function ir(c){ const sr=c.sampleRate; let b=IRC.get(sr); if(b) return b; const len=Math.floor(sr*1.1); b=c.createBuffer(2,len,sr); const r=rng(99);
    for(let ch=0;ch<2;ch++){ const x=b.getChannelData(ch); let lp=0;
      for(let i=0;i<len;i++){ const t=i/sr, env=Math.exp(-t/.17), a=.78-.62*Math.min(1,t/.9); lp+=((r()*2-1)-lp)*a; x[i]=lp*env*(t<.006?t/.006:1); }
      [[.011,.55],[.017,.4],[.026,.32],[.037,.24],[.049,.17],[.063,.12]].forEach(([d,a],j)=>{ const i=Math.floor((d+(ch?.0023*(j+1):0))*sr); if(i<len) x[i]+=a*((ch+j)%2?-1:1); }); }
    IRC.set(sr,b); return b; }
  function clipCurve(){ const n=4096, cu=new Float32Array(n), k=.5, h=.335;   // |x|≤0,5 doğrusal; üstü tanh ile 0,835'e (−1,57 dBFS) yaklaşır
    for(let i=0;i<n;i++){ const x=i/(n-1)*2-1, a=Math.abs(x); cu[i]=Math.sign(x)*(a<=k?a:k+h*Math.tanh((a-k)/h)); } return cu; }
  let CURVE=null;
  function chain(c,dest,vg){
    const inp=c.createGain(), send=c.createGain(), conv=c.createConvolver(), wet=c.createGain(), hp=c.createBiquadFilter(), sh=c.createBiquadFilter(),
      comp=c.createDynamicsCompressor(), vol=c.createGain(), lim=c.createDynamicsCompressor(), clip=c.createWaveShaper();
    conv.normalize=true; conv.buffer=ir(c); wet.gain.value=.3;
    hp.type="highpass"; hp.frequency.value=90; hp.Q.value=.7;
    sh.type="highshelf"; sh.frequency.value=6500; sh.gain.value=-4;
    comp.threshold.value=-20; comp.knee.value=10; comp.ratio.value=2.5; comp.attack.value=.008; comp.release.value=.2;
    lim.threshold.value=-7; lim.knee.value=0; lim.ratio.value=20; lim.attack.value=.001; lim.release.value=.09;
    clip.curve=CURVE||(CURVE=clipCurve()); clip.oversample="none";
    vol.gain.value=vg;
    inp.connect(hp); send.connect(conv); conv.connect(wet); wet.connect(hp);
    hp.connect(sh); sh.connect(comp); comp.connect(vol); vol.connect(lim); lim.connect(clip); clip.connect(dest);
    return {inp,send,vol}; }
  function sub(c,B,k){ const i=c.createGain(), s=c.createGain(); i.gain.value=k; s.gain.value=k; i.connect(B.inp); s.connect(B.send); return {inp:i,send:s,g:[i,s]}; }
  function out(c,B,n,pan,send){ let x=n; if(pan&&c.createStereoPanner){ const p=c.createStereoPanner(); p.pan.value=Math.max(-1,Math.min(1,pan)); x.connect(p); x=p; }
    x.connect(B.inp); if(send){ const s=c.createGain(); s.gain.value=send; x.connect(s); s.connect(B.send); } }
  function adsr(p,t,a,g,h,r){ p.setValueAtTime(.0001,t); p.exponentialRampToValueAtTime(Math.max(.00011,g),t+a); if(h>0) p.setValueAtTime(Math.max(.00011,g),t+a+h); p.exponentialRampToValueAtTime(.0001,t+a+h+r); return a+h+r; }
  // FM çan / elektrik: r=3,5 altın çan (inharmonik), r=2 parlak "mavi"
  function fm(c,B,t,f,d,g,o){ o=o||{}; const r=o.r||3.5, ix=o.i==null?1.5:o.i, a=o.a||.003;
    const car=c.createOscillator(), mod=c.createOscillator(), mg=c.createGain(), v=c.createGain();
    car.frequency.value=f; mod.frequency.value=f*r; if(o.dt) car.detune.value=o.dt;
    mg.gain.setValueAtTime(f*ix,t); mg.gain.exponentialRampToValueAtTime(Math.max(1,f*ix*.06),t+a+d*.75);
    mod.connect(mg); mg.connect(car.frequency); adsr(v.gain,t,a,g,o.h||0,d); car.connect(v); out(c,B,v,o.p||0,o.s==null?.18:o.s);
    const e=t+a+(o.h||0)+d+.03; car.start(t); mod.start(t); car.stop(e); mod.stop(e); return e; }
  // damla: perdesi düşen saf ton (menü dokunuşu)
  function drop(c,B,t,f0,f1,d,g,o){ o=o||{}; const x=c.createOscillator(), v=c.createGain(); x.frequency.setValueAtTime(f0,t); x.frequency.exponentialRampToValueAtTime(f1,t+d);
    adsr(v.gain,t,.0015,g,0,d); x.connect(v); out(c,B,v,o.p||0,o.s||0); x.start(t); x.stop(t+d+.03); }
  function nsrc(c,t,d,off){ const s=c.createBufferSource(); s.buffer=nbuf(c); s.loop=true; s.start(t,(off||0)%1.9); s.stop(t+d+.03); return s; }
  function nz(c,B,t,d,g,o){ o=o||{}; const a=o.a||.004, h=o.h||0, s=nsrc(c,t,a+h+d,o.off), f=c.createBiquadFilter(), v=c.createGain();
    f.type=o.type||"bandpass"; f.Q.value=o.q||1; f.frequency.setValueAtTime(o.f0||1000,t); if(o.f1) f.frequency.exponentialRampToValueAtTime(o.f1,t+a+h+d);
    adsr(v.gain,t,a,g,h,d); s.connect(f); f.connect(v); out(c,B,v,o.p||0,o.s||0); }
  // sıcak brass: 3 hafif ayrık testere + zarflı alçak geçiren + gecikmeli vibrato
  function brass(c,B,t,f,d,g,o){ o=o||{}; const v=c.createGain(), lp=c.createBiquadFilter(), br=o.br||6, a=o.a||.02, rel=o.rel||.14, e=t+d+rel+.04;
    lp.type="lowpass"; lp.Q.value=o.q||1.2;
    lp.frequency.setValueAtTime(Math.min(9000,f*1.1),t); lp.frequency.exponentialRampToValueAtTime(Math.min(9000,f*br),t+a+.03); lp.frequency.exponentialRampToValueAtTime(Math.min(9000,f*Math.max(1.3,br*.45)),t+d+rel);
    const lfo=c.createOscillator(), lg=c.createGain(); lfo.frequency.value=5.4; lg.gain.setValueAtTime(0,t); lg.gain.linearRampToValueAtTime(o.vib==null?6:o.vib,t+Math.min(.3,d+.01)); lfo.connect(lg);
    const det=o.mono?[0]:[-7,0,6];
    det.forEach(ct=>{ const x=c.createOscillator(); x.type="sawtooth"; x.frequency.value=f; x.detune.value=ct; lg.connect(x.detune); x.connect(lp); x.start(t); x.stop(e); });
    const gg=g/Math.sqrt(det.length); v.gain.setValueAtTime(.0001,t); v.gain.exponentialRampToValueAtTime(gg,t+a); v.gain.linearRampToValueAtTime(gg*.72,t+a+.1); v.gain.setValueAtTime(gg*.72,t+Math.max(a+.1,d)); v.gain.exponentialRampToValueAtTime(.0001,t+d+rel);
    lp.connect(v); out(c,B,v,o.p||0,o.s==null?.22:o.s); lfo.start(t); lfo.stop(e); return e; }
  function pad(c,B,t,f,d,g,o){ o=o||{}; const v=c.createGain(), lp=c.createBiquadFilter(); lp.type="lowpass"; lp.frequency.setValueAtTime(o.lp||1100,t); lp.frequency.exponentialRampToValueAtTime((o.lp||1100)*.55,t+d); lp.Q.value=.5;
    [-5,5].forEach(ct=>{ const x=c.createOscillator(); x.type="triangle"; x.frequency.value=f; x.detune.value=ct; x.connect(lp); x.start(t); x.stop(t+d+.05); });
    adsr(v.gain,t,o.a||.035,g,o.h||0,d); lp.connect(v); out(c,B,v,o.p||0,o.s==null?.2:o.s); }
  function boom(c,B,t,g){ [[150,55,1],[300,110,.32]].forEach(([f0,f1,k])=>{ const x=c.createOscillator(), v=c.createGain(); x.frequency.setValueAtTime(f0,t); x.frequency.exponentialRampToValueAtTime(f1,t+.22);
      adsr(v.gain,t,.004,g*k,0,.36); x.connect(v); out(c,B,v,0,.08); x.start(t); x.stop(t+.42); });
    nz(c,B,t,.05,g*.35,{type:"lowpass",f0:1800,q:.6,a:.001}); }
  function whistle(c,B,t,d,g){ const x=c.createOscillator(), tr=c.createOscillator(), tg=c.createGain(), v=c.createGain();
    x.frequency.value=2250; tr.frequency.value=26; tg.gain.value=95; tr.connect(tg); tg.connect(x.frequency);
    v.gain.setValueAtTime(.0001,t); v.gain.exponentialRampToValueAtTime(g,t+.014); v.gain.setValueAtTime(g,t+Math.max(.02,d-.035)); v.gain.exponentialRampToValueAtTime(.0001,t+d);
    x.connect(v); out(c,B,v,0,.16); x.start(t); tr.start(t); x.stop(t+d+.03); tr.stop(t+d+.03);
    nz(c,B,t,d-.02,g*.22,{type:"bandpass",f0:2250,q:2.5,a:.01}); }
  function claps(c,B,t,d,n,g,seed){ const r=rng(seed||7); for(let i=0;i<n;i++){ const tt=t+Math.max(.04,d)*Math.pow(r(),1.5);
      nz(c,B,tt,.035+r()*.03,g*(.35+.65*r()),{type:"bandpass",f0:1100+r()*1500,q:1.3,a:.001,p:r()*1.6-.8,off:r()*1.8,s:.12}); } }
  // sentez kalabalık: formant süzülmüş gürültü (iki kanal, dalgalanan) + "aaah" koro (testere sesler, yükselen perde) + alkış
  function crowd(c,B,t,d,g,o){ o=o||{}; const sw=o.sw==null?.35:o.sw, pk=o.pk==null?sw:o.pk, r=rng(o.seed||5);
    for(const [pan,off] of [[-.6,.13],[.6,.71]]){ const s=nsrc(c,t,d,off), sum=c.createGain(), am=c.createGain(), v=c.createGain();
      [[480,1.1,1],[1050,1.6,.62],[2450,2.2,.22]].forEach(([f,q,a])=>{ const bp=c.createBiquadFilter(); bp.type="bandpass"; bp.frequency.value=f*(pan<0?.97:1.03); bp.Q.value=q; const ga=c.createGain(); ga.gain.value=a; s.connect(bp); bp.connect(ga); ga.connect(sum); });
      am.gain.value=1; const l=c.createOscillator(), lg=c.createGain(); l.frequency.value=pan<0?3.3:4.3; lg.gain.value=.2; l.connect(lg); lg.connect(am.gain); l.start(t); l.stop(t+d+.03);
      const p=v.gain; p.setValueAtTime(.0001,t); if(sw>0) p.exponentialRampToValueAtTime(g*.26,t+sw); p.linearRampToValueAtTime(g,t+pk+.07);
      p.linearRampToValueAtTime(g*.5,t+pk+(d-pk)*.4); p.exponentialRampToValueAtTime(.0001,t+d);
      sum.connect(am); am.connect(v); out(c,B,v,pan,o.s==null?.25:o.s); }
    const nv=o.v==null?8:o.v; if(nv){ const fl=[[720,1.2],[1150,1.8],[2600,2.4]];
      for(let i=0;i<nv;i++){ const f=165+r()*230, x=c.createOscillator(), vl=c.createOscillator(), vg=c.createGain(), v=c.createGain(), mix=c.createGain(); x.type="sawtooth";
        x.frequency.setValueAtTime(f*.92,t); x.frequency.linearRampToValueAtTime(f*.96,t+Math.max(.01,pk)); x.frequency.exponentialRampToValueAtTime(f*1.14,t+pk+.12); x.frequency.exponentialRampToValueAtTime(f*1.02,t+d);
        vl.frequency.value=4.5+r()*2.5; vg.gain.value=f*.012; vl.connect(vg); vg.connect(x.frequency);
        fl.forEach(([ff,q])=>{ const bp=c.createBiquadFilter(); bp.type="bandpass"; bp.frequency.value=ff*(.95+r()*.1); bp.Q.value=q; x.connect(bp); bp.connect(mix); });
        const gv=g*.11, p=v.gain; p.setValueAtTime(.0001,t); if(sw>0) p.exponentialRampToValueAtTime(gv*.3,t+sw); p.linearRampToValueAtTime(gv,t+pk+.1); p.exponentialRampToValueAtTime(.0001,t+d*(.8+.2*r()));
        mix.connect(v); out(c,B,v,r()*1.4-.7,.3); x.start(t); vl.start(t); x.stop(t+d+.03); vl.stop(t+d+.03); } }
    if(o.claps) claps(c,B,t+pk,d-pk-.25,o.claps,g*.55,o.seed||7); }
  function hoof(c,B,t,g,pan){ nz(c,B,t,.06,g,{type:"lowpass",f0:850,q:.8,a:.002,p:pan,s:.06});
    const x=c.createOscillator(), v=c.createGain(); x.frequency.setValueAtTime(240,t); x.frequency.exponentialRampToValueAtTime(110,t+.05); adsr(v.gain,t,.002,g*.7,0,.07); x.connect(v); out(c,B,v,pan,0); x.start(t); x.stop(t+.1); }
  function gallop(c,B,t,d,g,acc){ const r=rng(3); let tt=t, per=.36; while(tt<t+d-.05){ const k=per/.36; [0,.07,.14].forEach((o,i)=>hoof(c,B,tt+o*k,g*(i===2?1:.72)*(.9+.2*r()),i===1?.22:-.18)); tt+=per; per=Math.max(.23,per*(acc||.92)); } }
  function swish(c,B,t,g){ nz(c,B,t,.2,g,{type:"bandpass",f0:6200,f1:1500,q:1.4,a:.05,p:-.25,s:.14}); nz(c,B,t+.21,.08,g*.5,{type:"highpass",f0:3000,q:.5,a:.002,p:.25,s:.1}); }
  function buzzer(c,B,t,d,g){ const lp=c.createBiquadFilter(), v=c.createGain(); lp.type="lowpass"; lp.frequency.value=1500; lp.Q.value=.7;
    [[220,"square",.5],[221.6,"sawtooth",.5],[441,"square",.16]].forEach(([f,ty,a])=>{ const x=c.createOscillator(), xa=c.createGain(); x.type=ty; x.frequency.value=f; xa.gain.value=a; x.connect(xa); xa.connect(lp); x.start(t); x.stop(t+d+.05); });
    v.gain.setValueAtTime(.0001,t); v.gain.exponentialRampToValueAtTime(g,t+.012); v.gain.setValueAtTime(g,t+d-.05); v.gain.exponentialRampToValueAtTime(.0001,t+d); lp.connect(v); out(c,B,v,0,.15); }
  function bugle(c,B,t,notes,g,o){ o=o||{}; let e=t; notes.forEach(([f,at,d])=>{ e=Math.max(e,brass(c,B,t+at,f,d,g,{br:o.br||8,q:1.6,vib:3,a:.014,rel:.08,s:o.s==null?.36:o.s,p:o.p||0})); }); return e; }
  function motif(c,B,t,g,o){ o=o||{}; MOTIF.forEach((f,i)=>fm(c,B,t+i*(o.st||.11),f,i===2?(o.last||.8):(o.d||.38),g*(i===2?1:.85),{r:3.5,i:1.35,s:o.s==null?.32:o.s,p:[-.25,.25,0][i]})); }

  // ---------- gerçek kayıtlar (CC0 / CC BY / kamu malı; ayrıntı: ses_kaynaklari.md) ----------
  // İlk dokunuştan sonra arka planda tembel yüklenir (ses/v121/*.webm, Opus desteklemeyen cihazda *.mp3); hazır değilse sentez yedeği çalar.
  // ses/ yolu data/ dışında: servis çalışanı bunu ilk istekten sonra önbellekten verir (data/ her seferinde ağdan gelir).
  const SM={base:"ses/v121/",ad:["gol_kalabalik","alkis","tezahurat","duduk","dortnala","buzzer","file"],buf:{},st:"yok",p:null};
  const has=a=>!!SM.buf[a];
  function fmt(){ try{ return new Audio().canPlayType('audio/webm; codecs="opus"')==="probably"?"webm":"mp3"; }catch(e){ return "mp3"; } }
  function dec(c,ab){ return new Promise((ok,no)=>{ let d=false; const y=b=>{ if(!d){ d=true; ok(b); } }, n=e=>{ if(!d){ d=true; no(e); } };
    try{ const r=c.decodeAudioData(ab,y,n); if(r&&r.then) r.then(y,n); }catch(e){ n(e); } }); }
  async function one(c,ad,ext){ const r=await fetch(SM.base+ad+"."+ext); if(!r.ok) throw new Error(r.status); return dec(c,await r.arrayBuffer()); }
  function loadSamples(c){ if(SM.p) return SM.p; if(!c) return Promise.resolve(); SM.st="yukleniyor"; const ext=fmt();
    SM.p=Promise.all(SM.ad.map(async ad=>{ try{ SM.buf[ad]=await one(c,ad,ext); }catch(e){ if(ext!=="mp3"){ try{ SM.buf[ad]=await one(c,ad,"mp3"); }catch(_){} } } }))
      .then(()=>{ SM.st=SM.ad.every(has)?"hazir":"eksik"; }); return SM.p; }
  // örnek çalar: iki kopya (sol/sağ, 17 ms) ile stadyum genişliği; isteğe bağlı perde kayması ve süzgeç
  function smp(c,B,t,ad,o){ const b=SM.buf[ad]; if(!b) return 0; o=o||{}; const rate=o.rate||1, off=Math.min(o.off||0,b.duration-.05), full=(b.duration-off)/rate, dur=Math.min(o.d||full,full);
    const mk=(pan,dl,gk,r2)=>{ const sN=c.createBufferSource(); sN.buffer=b; sN.playbackRate.setValueAtTime(rate*r2,t+dl); if(o.rate2) sN.playbackRate.linearRampToValueAtTime(o.rate2*r2,t+dl+dur);
      let n=sN; for(const [ty,f0,f1] of [["lowpass",o.lp,o.lp2],["highpass",o.hp,o.hp2]]){ if(!f0) continue; const f=c.createBiquadFilter(); f.type=ty; f.Q.value=.6; f.frequency.setValueAtTime(f0,t+dl); if(f1) f.frequency.exponentialRampToValueAtTime(f1,t+dl+dur); n.connect(f); n=f; }
      const v=c.createGain(), g=Math.max(.00011,(o.g||.5)*gk), a=o.a||.006, r=Math.min(o.r||.25,dur*.9), e=t+dl+dur;
      v.gain.setValueAtTime(.0001,t+dl); v.gain.exponentialRampToValueAtTime(g,t+dl+a); v.gain.setValueAtTime(g,Math.max(t+dl+a,e-r)); v.gain.exponentialRampToValueAtTime(.0001,e);
      n.connect(v); out(c,B,v,pan,o.s==null?.12:o.s); sN.start(t+dl,off,dur*rate*r2+.02); sN.stop(e+.03); };
    if(o.wide===false) mk(o.p||0,0,1,1); else { mk(-.45+(o.p||0),0,.78,1); mk(.45+(o.p||0),.017,.7,1.004); }
    return dur; }
  // hakem düdüğü: gerçek kayıt (uzun / kısa)
  function duduk(c,B,t,d,g){ if(has("duduk")) return smp(c,B,t,"duduk",{g:g||.55,d:d||.5,r:d&&d<.3?.05:.08,wide:false,s:.22}); whistle(c,B,t,d||.5,.055); return d||.5; }

  // ---------- sesler (her biri ≤3 sn; gerçek kayıtlı olaylar ≤4 sn) ----------
  const R={
    // ⚽ futbol
    gol(c,B,t,o){ const rm=o.rm;
      if(!rm) crowd(c,B,t,2.2,.26,{sw:.36,pk:.4,claps:30,v:9}); else crowd(c,B,t+.38,1.1,.14,{sw:0,pk:.04,v:0,claps:0});
      boom(c,B,t+.4,.34);
      [[NT.A4,-.3],[NT.Cs5,.3],[NT.E5,0]].forEach(([f,p])=>brass(c,B,t+.4,f,.09,.07,{p,br:7,rel:.05}));
      [[NT.D4,-.35],[NT.Fs4,.35],[NT.A4,-.1],[NT.D5,.12]].forEach(([f,p],i)=>brass(c,B,t+.54+i*.006,f,.46,.085,{p,br:7.5,rel:.22}));
      motif(c,B,t+1.02,.13,{st:.1,last:.75});
      fm(c,B,t+1.24,NT.D6,.6,.045,{r:2,i:.8,s:.4,p:.3}); return 2.3; },
    golRakip(c,B,t,o){ fm(c,B,t,NT.A5,.42,.07,{r:3.5,i:1.2,s:.2,p:-.15}); fm(c,B,t+.17,NT.F5,.6,.07,{r:3.5,i:1.2,s:.22,p:.15});
      brass(c,B,t+.02,NT.D4,.16,.045,{br:2.6,rel:.12,s:.1}); brass(c,B,t+.02,NT.F4,.16,.035,{br:2.6,rel:.12,s:.1});
      if(!o.rm) nz(c,B,t+.05,.75,.035,{type:"bandpass",f0:950,f1:420,q:1.1,a:.12,s:.2}); return 1.0; },
    macBasladi(c,B,t){ whistle(c,B,t,.5,.06); fm(c,B,t+.62,NT.D5,.32,.065,{r:3.5,i:1.2,s:.25,p:-.2}); fm(c,B,t+.72,NT.A5,.45,.06,{r:3.5,i:1.2,s:.28,p:.2}); return 1.25; },
    ilkYari(c,B,t){ whistle(c,B,t,.15,.055); whistle(c,B,t+.24,.2,.055); pad(c,B,t+.5,NT.D4,.5,.05,{p:-.2}); pad(c,B,t+.5,NT.A4,.5,.04,{p:.2}); return 1.05; },
    macBitti(c,B,t){ whistle(c,B,t,.14,.055); whistle(c,B,t+.21,.14,.055); whistle(c,B,t+.42,.58,.055);
      [[NT.D4,-.3],[NT.Fs4,.3],[NT.A4,0]].forEach(([f,p])=>brass(c,B,t+1.08,f,.42,.055,{p,br:3.6,a:.06,rel:.3,vib:3})); fm(c,B,t+1.12,NT.D5,.55,.05,{r:3.5,i:1.1,s:.3}); fm(c,B,t+1.22,NT.A5,.6,.045,{r:3.5,i:1.1,s:.3}); return 1.95; },
    kirmizi(c,B,t){ boom(c,B,t,.16); [0,.2].forEach((dt,i)=>{ brass(c,B,t+dt,NT.D4,i?.24:.12,.065,{br:5,rel:.08,p:-.2}); brass(c,B,t+dt,NT.Eb4,i?.24:.12,.055,{br:5,rel:.08,p:.2}); }); fm(c,B,t+.2,NT.D5,.3,.03,{r:1.4,i:2,s:.15}); return .7; },
    // 🏆 KUPO
    kupoEkle(c,B,t){ fm(c,B,t,NT.A5,.05,.05,{r:2,i:.8,s:.06,p:-.15}); fm(c,B,t+.032,NT.D6,.075,.045,{r:3.5,i:.9,s:.1,p:.15}); return .12; },
    kupoCikar(c,B,t){ fm(c,B,t,NT.D6,.04,.03,{r:2,i:.6,s:.04,p:.12}); fm(c,B,t+.03,NT.A5,.065,.034,{r:2,i:.5,s:.05,p:-.12}); return .11; },
    kupoTuttu(c,B,t,o){ [NT.D5,NT.Fs5,NT.A5,NT.D6,NT.Fs6,NT.A6].forEach((f,i)=>fm(c,B,t+i*.05,f,.5,.062*(1-i*.06),{r:3.5,i:1.3,s:.3,p:i%2?.3:-.3}));
      [[NT.D4,-.3],[NT.Fs4,.3],[NT.A4,0],[NT.D5,.1]].forEach(([f,p])=>brass(c,B,t+.32,f,.5,.06,{p,br:7,rel:.25}));
      if(!o.rm) crowd(c,B,t+.28,1.75,.15,{sw:0,pk:.05,claps:22,v:7,seed:11});
      motif(c,B,t+.95,.095,{st:.09,last:.6}); return 2.3; },
    bacak(c,B,t){ drop(c,B,t,2600,1900,.02,.02); fm(c,B,t+.02,NT.A5,.55,.06,{r:3.5,i:1.2,s:.3,p:-.15}); fm(c,B,t+.02,NT.E6,.5,.04,{r:3.5,i:1.1,s:.3,p:.15}); return .65; },
    tutmadi(c,B,t){ pad(c,B,t,NT.F5,.42,.05,{p:-.15,lp:1700}); pad(c,B,t+.2,NT.D5,.6,.05,{p:.15,lp:1500}); pad(c,B,t+.2,NT.A4,.6,.03,{p:0,lp:1200}); return .85; },
    // 🏀 basket
    bkTuttu(c,B,t,o){ swish(c,B,t,.16); buzzer(c,B,t+.31,.3,.042); if(!o.rm) crowd(c,B,t+.3,.9,.12,{sw:0,pk:.03,claps:10,v:4,seed:21}); fm(c,B,t+.62,NT.A5,.35,.04,{r:3.5,i:1.1,s:.25}); return 1.25; },
    bkBitti(c,B,t,o){ buzzer(c,B,t,.72,.05); if(!o.rm) crowd(c,B,t+.05,1.45,.15,{sw:.1,pk:.12,claps:14,v:5,seed:31}); fm(c,B,t+.85,NT.D5,.4,.05,{r:3.5,i:1.2,s:.3,p:-.2}); fm(c,B,t+.95,NT.A5,.55,.05,{r:3.5,i:1.2,s:.3,p:.2}); return 1.6; },
    // 🐎 at yarışı (kendi bestemiz: "OXX çağrısı", gerçek çağrıdan bağımsız)
    atCagri(c,B,t){ bugle(c,B,t,[[NT.A4,0,.1],[NT.A4,.14,.08],[NT.D5,.27,.08],[NT.Fs5,.4,.18],[NT.D5,.64,.08],[NT.Fs5,.76,.08],[NT.A5,.89,.42]],.07); return 1.45; },
    atStart(c,B,t,o){ for(let i=0;i<11;i++) fm(c,B,t+i*.045,1250,.05,.065,{r:3.5,i:1.4,s:.12,p:i%2?.2:-.2}); gallop(c,B,t+.52,o.rm?.6:1.05,.17,.9); return o.rm?1.15:1.6; },
    atSerit(c,B,t){ bugle(c,B,t,[[NT.A4,0,.08],[NT.D5,.12,.18]],.04,{s:.3}); return .45; },
    atKazandi(c,B,t,o){ gallop(c,B,t,.92,.17,.9);
      bugle(c,B,t+.94,[[NT.D5,0,.07],[NT.D5,.1,.07],[NT.Fs5,.2,.07],[NT.A5,.3,.5]],.07,{br:7});
      [[NT.D4,-.3],[NT.A4,.3]].forEach(([f,p])=>brass(c,B,t+1.24,f,.5,.05,{p,br:4,rel:.25}));
      if(!o.rm) crowd(c,B,t+1.2,1.35,.15,{sw:0,pk:.05,claps:14,v:5,seed:41});
      motif(c,B,t+1.6,.05,{st:.08,last:.55,d:.3}); return 2.6; },
    atKupoTuttu(c,B,t,o){ gallop(c,B,t,.6,.15,.88); [NT.D5,NT.Fs5,NT.A5,NT.D6].forEach((f,i)=>fm(c,B,t+.6+i*.05,f,.45,.06,{r:3.5,i:1.3,s:.3,p:i%2?.3:-.3}));
      [[NT.D4,-.3],[NT.Fs4,.3],[NT.A4,0],[NT.D5,.1]].forEach(([f,p])=>brass(c,B,t+.84,f,.5,.055,{p,br:7,rel:.25}));
      if(!o.rm) crowd(c,B,t+.8,1.5,.16,{sw:0,pk:.05,claps:16,v:5,seed:51}); motif(c,B,t+1.3,.055,{st:.08,last:.6,d:.3}); return 2.45; },
    // ✨ menü / arayüz (≤120 ms)
    tap(c,B,t){ drop(c,B,t,2300,1500,.03,.034,{s:.02}); fm(c,B,t,NT.A5,.035,.012,{r:2,i:.4,s:0}); return .05; },
    tab(c,B,t){ fm(c,B,t,NT.A5,.05,.045,{r:2,i:.7,s:.07,p:-.2}); fm(c,B,t+.035,NT.D6,.07,.04,{r:2,i:.6,s:.09,p:.2}); return .12; },
    acik(c,B,t){ fm(c,B,t,NT.D5,.05,.045,{r:1,i:1.1,s:.05}); fm(c,B,t+.032,NT.A5,.07,.045,{r:1,i:1,s:.07}); return .11; },
    kapali(c,B,t){ fm(c,B,t,NT.A5,.045,.034,{r:1,i:.9,s:.04}); fm(c,B,t+.03,NT.D5,.065,.034,{r:1,i:.8,s:.05}); return .1; },
    ac(c,B,t){ nz(c,B,t,.07,.03,{type:"bandpass",f0:700,f1:2600,q:1.2,a:.03,s:.06}); fm(c,B,t+.045,NT.Fs5,.06,.03,{r:2,i:.6,s:.08}); return .11; },
    kapa(c,B,t){ nz(c,B,t,.06,.025,{type:"bandpass",f0:2400,f1:700,q:1.2,a:.02,s:.04}); fm(c,B,t+.025,NT.D5,.05,.026,{r:2,i:.5,s:.05}); return .1; },
    kaydir(c,B,t){ drop(c,B,t,1700,1350,.02,.018); return .03; },
    power(c,B,t){ nz(c,B,t,.09,.03,{type:"bandpass",f0:1400,f1:6000,q:2,a:.02,s:.1}); MOTIF.forEach((f,i)=>fm(c,B,t+i*.028,f,i===2?.06:.04,.05,{r:2,i:1,s:.18,p:[-.25,.25,0][i]})); return .12; },
    msgIn(c,B,t){ fm(c,B,t,NT.Fs5,.06,.045,{r:3.5,i:1,s:.12,p:-.1}); fm(c,B,t+.045,NT.A5,.07,.04,{r:3.5,i:1,s:.14,p:.1}); return .12; },
    msgOut(c,B,t){ drop(c,B,t,1250,2250,.045,.04,{s:.03}); nz(c,B,t,.045,.01,{type:"bandpass",f0:900,f1:2200,q:1.4,a:.015}); return .07; },
    star(c,B,t){ fm(c,B,t,NT.A5,.05,.045,{r:3.5,i:1,s:.1,p:-.15}); fm(c,B,t+.04,NT.Fs6,.075,.04,{r:3.5,i:1,s:.14,p:.15}); return .12; },
    ready(c,B,t){ motif(c,B,t,.06,{st:.07,d:.26,last:.45,s:.25}); return .65; }
  };
  // gerçek kayıtlı sürümler (kayıt yoksa yukarıdaki sentez yedeği)
  const SY=Object.assign({},R);
  Object.assign(R,{
    gol(c,B,t,o){ if(!has("gol_kalabalik")) return SY.gol(c,B,t,o);
      smp(c,B,t,"gol_kalabalik",{g:.62,a:.02,r:1.3,d:o.rm?2.4:3.9,s:.16});
      if(has("alkis")) smp(c,B,t+.95,"alkis",{g:.34,a:.6,r:1.1,d:o.rm?1.4:2.9,s:.14});
      if(!o.rm&&has("tezahurat")) smp(c,B,t+1.7,"tezahurat",{g:.2,a:.5,r:.8,d:2.1,off:.5,s:.14});
      boom(c,B,t+.5,.16);
      [[NT.A4,-.3],[NT.Cs5,.3],[NT.E5,0]].forEach(([f,p])=>brass(c,B,t+.5,f,.08,.035,{p,br:6,rel:.05,s:.3}));
      [[NT.D4,-.35],[NT.Fs4,.35],[NT.A4,-.1],[NT.D5,.12]].forEach(([f,p],i)=>brass(c,B,t+.62+i*.006,f,.5,.045,{p,br:6,rel:.3,s:.35}));
      motif(c,B,t+1.3,.045,{st:.12,last:.9,s:.45}); return o.rm?2.6:3.95; },
    golRakip(c,B,t,o){ if(!has("gol_kalabalik")) return SY.golRakip(c,B,t,o);
      smp(c,B,t,"gol_kalabalik",{off:1.1,rate:.84,rate2:.7,lp:1500,lp2:550,g:.5,a:.1,r:.9,d:1.45,s:.2});
      fm(c,B,t+.35,NT.A5,.4,.035,{r:3.5,i:1.1,s:.35,p:-.15}); fm(c,B,t+.52,NT.F5,.6,.035,{r:3.5,i:1.1,s:.35,p:.15}); return 1.5; },
    macBasladi(c,B,t){ if(!has("duduk")) return SY.macBasladi(c,B,t); duduk(c,B,t,.5); fm(c,B,t+.62,NT.D5,.32,.04,{r:3.5,i:1.1,s:.3,p:-.2}); fm(c,B,t+.72,NT.A5,.45,.035,{r:3.5,i:1.1,s:.32,p:.2}); return 1.25; },
    ilkYari(c,B,t){ if(!has("duduk")) return SY.ilkYari(c,B,t); duduk(c,B,t,.2); duduk(c,B,t+.28,.26); if(has("alkis")) smp(c,B,t+.5,"alkis",{g:.12,a:.25,r:.5,d:.9,off:1,s:.12}); return 1.4; },
    macBitti(c,B,t){ if(!has("duduk")) return SY.macBitti(c,B,t); duduk(c,B,t,.17); duduk(c,B,t+.24,.17); duduk(c,B,t+.48,.5);
      if(has("alkis")) smp(c,B,t+.95,"alkis",{g:.22,a:.3,r:.9,d:1.7,s:.14});
      [[NT.D4,-.3],[NT.Fs4,.3],[NT.A4,0]].forEach(([f,p])=>brass(c,B,t+1.05,f,.45,.03,{p,br:3.4,a:.06,rel:.3,vib:3,s:.35})); return 2.7; },
    kirmizi(c,B,t){ if(!has("duduk")) return SY.kirmizi(c,B,t); duduk(c,B,t,.24,.5);
      if(has("gol_kalabalik")) smp(c,B,t+.12,"gol_kalabalik",{off:1.6,rate:.92,rate2:.82,lp:1800,lp2:700,g:.26,a:.12,r:.5,d:.9,s:.18});
      [.3,.48].forEach((dt,i)=>{ brass(c,B,t+dt,NT.D4,i?.22:.1,.04,{br:5,rel:.08,p:-.2}); brass(c,B,t+dt,NT.Eb4,i?.22:.1,.034,{br:5,rel:.08,p:.2}); }); return 1.1; },
    kupoTuttu(c,B,t,o){ if(!has("alkis")) return SY.kupoTuttu(c,B,t,o);
      [NT.D5,NT.Fs5,NT.A5,NT.D6,NT.Fs6,NT.A6].forEach((f,i)=>fm(c,B,t+i*.05,f,.5,.045*(1-i*.06),{r:3.5,i:1.2,s:.32,p:i%2?.3:-.3}));
      smp(c,B,t+.2,"alkis",{g:.42,a:.12,r:1,d:2.8,s:.14}); if(!o.rm&&has("tezahurat")) smp(c,B,t+.3,"tezahurat",{g:.26,a:.2,r:.9,d:2.5,s:.14});
      [[NT.D4,-.3],[NT.Fs4,.3],[NT.A4,0],[NT.D5,.1]].forEach(([f,p])=>brass(c,B,t+.32,f,.5,.035,{p,br:6,rel:.25,s:.3}));
      motif(c,B,t+1.05,.045,{st:.1,last:.7,s:.4}); return 3.1; },
    bacak(c,B,t){ SY.bacak(c,B,t); if(has("alkis")) smp(c,B,t+.06,"alkis",{g:.16,a:.06,r:.55,d:.95,off:.6,s:.12}); return 1.05; },
    bkTuttu(c,B,t,o){ if(!has("file")) return SY.bkTuttu(c,B,t,o); smp(c,B,t,"file",{g:.55,d:.4,r:.2,hp:500,s:.12});
      if(has("buzzer")) smp(c,B,t+.34,"buzzer",{g:.36,d:.34,r:.05,wide:false,s:.15}); if(!o.rm&&has("alkis")) smp(c,B,t+.4,"alkis",{g:.22,a:.08,r:.6,d:1.2,s:.12}); return 1.65; },
    bkBitti(c,B,t,o){ if(!has("buzzer")) return SY.bkBitti(c,B,t,o); smp(c,B,t,"buzzer",{g:.45,d:.76,r:.08,wide:false,s:.15});
      if(!o.rm&&has("tezahurat")) smp(c,B,t+.12,"tezahurat",{g:.34,a:.15,r:.8,d:2.1,s:.14}); fm(c,B,t+.95,NT.D5,.4,.035,{r:3.5,i:1.1,s:.35,p:-.2}); fm(c,B,t+1.05,NT.A5,.55,.035,{r:3.5,i:1.1,s:.35,p:.2}); return 2.3; },
    atStart(c,B,t,o){ if(!has("dortnala")) return SY.atStart(c,B,t,o); for(let i=0;i<11;i++) fm(c,B,t+i*.045,1250,.05,.045,{r:3.5,i:1.4,s:.12,p:i%2?.2:-.2});
      smp(c,B,t+.5,"dortnala",{hp:230,g:.5,d:o.rm?.8:1.45,r:.4,s:.1}); return o.rm?1.35:2.0; },
    atKazandi(c,B,t,o){ if(!has("dortnala")) return SY.atKazandi(c,B,t,o); smp(c,B,t,"dortnala",{hp:230,g:.5,d:1.5,r:.5,rate:1.05,s:.1});
      if(has("tezahurat")) smp(c,B,t+.85,"tezahurat",{g:.36,a:.25,r:.9,d:o.rm?1.4:2.5,s:.14}); if(!o.rm&&has("alkis")) smp(c,B,t+1.3,"alkis",{g:.2,a:.4,r:.8,d:1.9,s:.14});
      bugle(c,B,t+1.0,[[NT.D5,0,.07],[NT.D5,.1,.07],[NT.Fs5,.2,.07],[NT.A5,.3,.5]],.045,{br:7,s:.4});
      motif(c,B,t+1.75,.04,{st:.09,last:.6,d:.3,s:.45}); return 3.35; },
    atKupoTuttu(c,B,t,o){ if(!has("dortnala")) return SY.atKupoTuttu(c,B,t,o); smp(c,B,t,"dortnala",{hp:230,g:.46,d:1.05,r:.4,rate:1.05,s:.1});
      [NT.D5,NT.Fs5,NT.A5,NT.D6].forEach((f,i)=>fm(c,B,t+.7+i*.05,f,.45,.045,{r:3.5,i:1.2,s:.32,p:i%2?.3:-.3}));
      if(has("alkis")) smp(c,B,t+.75,"alkis",{g:.4,a:.15,r:.9,d:o.rm?1.3:2.3,s:.14});
      [[NT.D4,-.3],[NT.Fs4,.3],[NT.A4,0],[NT.D5,.1]].forEach(([f,p])=>brass(c,B,t+.9,f,.5,.035,{p,br:6,rel:.25,s:.3}));
      motif(c,B,t+1.4,.04,{st:.09,last:.6,d:.3,s:.45}); return 3.1; }
  });
  // hangi olay hangi kayda dayanıyor (kayıt hazırsa ayrı seviye tablosu)
  const PRI={gol:"gol_kalabalik",golRakip:"gol_kalabalik",macBasladi:"duduk",ilkYari:"duduk",macBitti:"duduk",kirmizi:"duduk",kupoTuttu:"alkis",bacak:"alkis",
    bkTuttu:"file",bkBitti:"buzzer",atStart:"dortnala",atKazandi:"dortnala",atKupoTuttu:"dortnala"};
  const LVR={gol:-1.5,golRakip:-6,macBasladi:-6,ilkYari:1,macBitti:-5,kirmizi:0,kupoTuttu:.5,bacak:1,bkTuttu:-3,bkBitti:-4,atStart:-4,atKazandi:0,atKupoTuttu:1};
  // seviye dengesi (dB): OfflineAudioContext + BS.1770 ölçümüyle ayarlandı (büyük olay ≈ −13, orta ≈ −17, küçük ≈ −22, menü ≈ −35 LUFS anlık; ana ses %100)
  const LV={gol:0,golRakip:3,macBasladi:-3.5,ilkYari:-1,macBitti:-2,kirmizi:1.5,kupoEkle:8,kupoCikar:10,kupoTuttu:3,bacak:6,tutmadi:1,bkTuttu:3.5,bkBitti:1.5,
    atCagri:1,atStart:8,atSerit:2.5,atKazandi:2.5,atKupoTuttu:2.8,tap:10,tab:6.5,acik:4,kapali:5,ac:6,kapa:8,kaydir:12,power:3.5,msgIn:6.5,msgOut:12,star:5.5,ready:0};
  const lv=n=>Math.pow(10,((PRI[n]&&has(PRI[n]))?(LVR[n]||0):(LV[n]||0))/20);
  const CAT={gol:"sesGol",golRakip:"sesGol",macBasladi:"sesGol",ilkYari:"sesGol",macBitti:"sesGol",kirmizi:"sesGol",
    kupoEkle:"sesKupo",kupoCikar:"sesKupo",kupoTuttu:"sesKupo",bacak:"sesKupo",tutmadi:"sesKupo",
    bkTuttu:"sesBasket",bkBitti:"sesBasket",atCagri:"sesAt",atStart:"sesAt",atSerit:"sesAt",atKazandi:"sesAt",atKupoTuttu:"sesAt"};
  const UI=new Set(["tap","tab","acik","kapali","ac","kapa","kaydir","power","msgIn","msgOut","star","ready"]);
  UI.forEach(n=>CAT[n]="sesMenu");
  const AD={gol:"Gol · takip ettiğin taraf",golRakip:"Gol · rakip",macBasladi:"Maç başladı",ilkYari:"İlk yarı bitti",macBitti:"Maç bitti",kirmizi:"Kırmızı kart",
    kupoEkle:"Seçim eklendi",kupoCikar:"Seçim çıkarıldı",kupoTuttu:"KUPO tuttu",bacak:"Bir maç tuttu",tutmadi:"Tutmadı",
    bkTuttu:"Basket seçimi tuttu",bkBitti:"Takip ettiğin maç bitti",atCagri:"Atım koşuyor · 30 dk",atStart:"Start",atSerit:"Hatırlatma şeridi",atKazandi:"At kazandı",atKupoTuttu:"At KUPO'su tuttu",
    tap:"Düğme",tab:"Sekme geçişi",acik:"Anahtar açık",kapali:"Anahtar kapalı",ac:"Pencere açıldı",kapa:"Pencere kapandı",kaydir:"Kaydırma",power:"Power Now",msgIn:"OXXai mesajı geldi",msgOut:"Mesaj gönderildi",star:"Takibe al",ready:"OXXai imza motifi"};

  // ---------- canlı motor ----------
  const DT=(()=>{ try{ return matchMedia("(hover:hover) and (pointer:fine)").matches; }catch(e){ return false; } })();   // v150: masaüstü (telefonda false)
  let ctx=null, bus=null, unlocked=false, lastAny=0, tapH=null, evEnd=0, sent=0;
  const lastN={}, LOG=[];
  const volG=v=>{ v=v==null?+PREFS.sesVol:+v; if(!isFinite(v)) v=.8; v=Math.max(0,Math.min(1,v)); return v<=0?0:Math.pow(v,1.6); };
  function mk(){ if(ctx) return ctx; const A=W.AudioContext||W.webkitAudioContext; if(!A) return null;
    try{ ctx=new A({latencyHint:"interactive"}); }catch(e){ try{ ctx=new A(); }catch(_){ return null; } }
    try{ bus=chain(ctx,ctx.destination,volG()); }catch(e){ ctx=null; return null; } return ctx; }
  function unlock(){ const c=mk(); if(!c) return;
    try{ const b=c.createBuffer(1,1,c.sampleRate), s=c.createBufferSource(); s.buffer=b; s.connect(c.destination); s.start(0); }catch(e){}
    const ok=()=>{ if(c.state==="running"){ unlocked=true; hold(c,c.currentTime); lazy(c); } };
    if(c.state!=="running"){ try{ c.resume().then(ok,()=>{}); }catch(e){} } else ok(); }
  // gerçek kayıtlar: açılışı yavaşlatmamak için ilk dokunuştan sonra, tarayıcı boşta kalınca bir kez
  function lazy(c){ if(SM.p) return; const go=()=>{ if(PREFS.sound&&!SM.p) loadSamples(c); };
    if("requestIdleCallback" in W) W.requestIdleCallback(go,{timeout:4000}); else setTimeout(go,1500); }
  ["pointerdown","touchend","keydown","click"].forEach(ev=>D.addEventListener(ev,()=>{ if(!unlocked) unlock(); },{capture:true,passive:true}));
  // boşta askıya al: zamanlayıcı yerine sessiz bir kaynak bitince (son sesten 1,5 sn sonra)
  function hold(c,end){ const id=++sent; try{ const o=c.createOscillator(), g=c.createGain(); g.gain.value=0; o.connect(g); g.connect(c.destination);
      o.onended=()=>{ try{ o.disconnect(); g.disconnect(); }catch(e){} if(id===sent&&c.state==="running") c.suspend().catch(()=>{}); };
      o.start(); o.stop(Math.max(c.currentTime,end)+1.5); }catch(e){} }
  D.addEventListener("visibilitychange",()=>{ if(D.hidden&&ctx&&ctx.state==="running"){ sent++; ctx.suspend().catch(()=>{}); } });
  function cancelTap(){ if(!tapH||!ctx) return; if(performance.now()-tapH.at<45){ const n=ctx.currentTime; tapH.B.g.forEach(g=>{ try{ g.gain.cancelScheduledValues(0); g.gain.setTargetAtTime(0,n,.003); }catch(e){} }); } tapH=null; }
  function trVoice(){ try{ if(!("speechSynthesis" in W)) return null; const vs=speechSynthesis.getVoices()||[]; return vs.find(v=>/^tr([-_]|$)/i.test(v.lang||""))||null; }catch(e){ return null; } }
  function speak(text,cos){ const v=trVoice(); if(!v) return; try{ speechSynthesis.cancel(); const u=new SpeechSynthesisUtterance(text); u.voice=v; u.lang=v.lang||"tr-TR";
      u.rate=cos?1.12:1; u.pitch=cos?1.25:.95; u.volume=Math.max(.25,Math.min(1,(+PREFS.sesVol||.8)+.15)); speechSynthesis.speak(u); }catch(e){} }
  function play(name,o){ const c=ctx; if(!c||!unlocked) return; if(!SM.p) lazy(c);
    const go=()=>{ if(c.state!=="running") return; try{ if(bus) bus.vol.gain.value=volG(); }catch(e){}
      const t=c.currentTime+.012, duck=UI.has(name)&&c.currentTime<evEnd, B=sub(c,bus,(duck?.5:1)*lv(name)); let d=0;
      try{ d=R[name](c,B,t,Object.assign({rm:RM()},o)); }catch(e){ return; }
      if(name==="tap") tapH={B,at:performance.now()}; if(!UI.has(name)) evEnd=Math.max(evEnd,t+d);
      hold(c,t+d+.9);
      if(o.say){ // anons: ses saatine bağlı — sessiz kaynak bitince başlar (zamanlayıcı yok)
        try{ const x=c.createOscillator(), g=c.createGain(); g.gain.value=0; x.connect(g); g.connect(c.destination); x.onended=()=>speak(o.say,o.cos); x.start(); x.stop(t+(o.sayAt||0)); }catch(e){ speak(o.say,o.cos); } } };
    if(c.state==="running") go(); else { try{ c.resume().then(go,()=>{}); }catch(e){} } }
  function olay(name,o){ o=o||{}; if(!R[name]) return false;
    if(!PREFS.sound) return false;                       // titreşim / sessiz modda ses yok
    if(!o.preview&&PREFS[CAT[name]]===false) return false;
    if(D.hidden&&!(DT&&!UI.has(name))) return false;  // v150: masaüstünde (fare + hover) maç olayı sesi başka sekmedeyken de çalar; menü sesleri susar
    const now=performance.now();
    if(UI.has(name)){ if(name==="tap"&&now-lastAny<45) return false; if(now-(lastN[name]||0)<(name==="kaydir"?240:70)) return false; if(name!=="tap") cancelTap(); }
    else { if(!o.preview&&now-(lastN[name]||0)<800) return false; if(!o.preview&&name==="atSerit"&&["atCagri","atStart","atKazandi"].some(n=>now-(lastN[n]||0)<3000)) return false; cancelTap(); }
    lastN[name]=now; lastAny=now; LOG.push({n:name,t:Date.now()}); if(LOG.length>60) LOG.shift();
    play(name,o); return true; }
  // takip edilen taraf: Takımlarım (★ favori takım) ya da OXXai'ye söylediğin takım
  function taraf(e,side){ try{ const fav=new Set(typeof FAVT!=="undefined"?[...FAVT]:[]);
      try{ const b=JSON.parse(localStorage.getItem("bx-bot70")||"{}"); if(b&&b.fav) fav.add(b.fav); }catch(_){}
      if(!fav.size) return "notr"; const nm=n=>{ try{ return bestTeamName(n); }catch(_){ return n; } };
      const sc=side==="h"?e.h:e.a, op=side==="h"?e.a:e.h, has=n=>fav.has(n)||fav.has(nm(n));
      if(has(sc)) return "biz"; if(has(op)) return "rakip"; }catch(e){} return "notr"; }
  function goal(o){ o=o||{}; const rak=o.taraf==="rakip", nm=rak?"golRakip":"gol";
    const can=!!(o.takim&&PREFS.sesAnons&&PREFS.sound&&PREFS.sesGol!==false&&trVoice());
    const say=can?(rak?`Gol, ${o.takim}. ${o.hs} ${o.as}.`:`Gol! ${o.takim}, ${o.hs} ${o.as}!`):null;
    const ok=olay(nm,{say,cos:!rak,sayAt:rak?.55:(RM()?.5:1.15)}); return !!(ok&&say); }
  async function renderOffline(name,o){ o=o||{}; const sr=o.sr||48000, OC=W.OfflineAudioContext||W.webkitOfflineAudioContext; if(!OC||!R[name]) return null;
    if(o.gercek!==false&&!SM.p) await loadSamples(new OC(1,1,sr)); else if(SM.p) await SM.p;
    const keep=SM.buf; if(o.gercek===false) SM.buf={};
    try{
    const c=new OC(2,Math.ceil(sr*(o.len||4)),sr), B=chain(c,c.destination,o.vol==null?1:o.vol), t=.02, d=R[name](c,sub(c,B,lv(name)),t,Object.assign({rm:false},o));
    const buf=await c.startRendering(); return {sr,d,L:buf.getChannelData(0),R:buf.getChannelData(1)}; } finally{ SM.buf=keep; } }

  // ---------- eski API korunur, genişletilir ----------
  Object.assign(Sound,{
    unlock, olay, taraf, goal, renderOffline,
    tap(){ olay("tap"); }, tab(){ olay("tab"); }, toggle(v){ olay(v?"acik":"kapali"); }, star(){ olay("star"); }, ready(){ olay("ready"); },
    names:()=>Object.keys(R), label:n=>AD[n]||n, kayit:()=>({st:SM.st,hazir:SM.ad.filter(has)}), yukle:()=>loadSamples(ctx||mk()), cat:n=>CAT[n], log:LOG, trVoice:()=>!!trVoice(),
    state:()=>({ctx:ctx?ctx.state:"yok",unlocked,vol:volG()})
  });

  // ---------- futbol / basket maç olayları (yalnız yıldızla takip edilenler) ----------
  // a) iddaa canlı (sp=1 futbol, sp=2 basket): FOLLOW "i"+id
  const IZ={1:new Map(),2:new Map()}, PR={1:false,2:false};
  const fol=k=>{ try{ return FOLLOW.has(k); }catch(e){ return false; } };
  const nmOf=m=>`${m.h} – ${m.a}`;
  function idlDiff(sp){ const L=(IDL.live&&IDL.live[sp])||[], M=IZ[sp], seen=new Set();
    for(const m of L){ const k="i"+m.id; seen.add(k); const rc=(m.rc||[0,0]).reduce((a,b)=>a+(+b||0),0), prev=M.get(k), cur={st:m.st,rc,min:m.min,q:Math.max((m.hq||[]).length,(m.aq||[]).length),h:m.h,a:m.a,hs:m.hs,as:m.as};
      M.set(k,cur); if(!PR[sp]||!fol(k)) continue;
      if(sp===1){ if(!prev){ if(m.st===2&&(m.min==null||m.min<=3)) ev("macBasladi",`⚽ ${nmOf(m)} başladı`); continue; }
        if(prev.st===2&&m.st!==2&&m.st!==3&&m.h1!=null) ev("ilkYari",`⏸ İlk yarı bitti · ${m.h} ${m.hs}-${m.as} ${m.a}`);
        if(rc>prev.rc) ev("kirmizi",`🟥 Kırmızı kart · ${nmOf(m)}`); } }
    if(PR[sp]) for(const [k,p] of M){ if(seen.has(k)) continue; M.delete(k); if(!fol(k)) continue;
      if(sp===1&&(p.st===3||(p.min||0)>=80)) ev("macBitti",`🏁 Maç bitti · ${p.h} ${p.hs}-${p.as} ${p.a}`);
      if(sp===2&&p.q>=4) ev("bkBitti",`🏀 Maç bitti · ${p.h} ${p.hs}-${p.as} ${p.a}`); }
    PR[sp]=true; }
  function ev(name,msg){ if(D.hidden){ if(DT){ olay(name); try{ if(W.oxxDtKacan) W.oxxDtKacan(name,msg); }catch(e){} } return; } try{ toast(msg); }catch(e){} try{ buzz(name==="kirmizi"?[50,40,50]:[20,40,20]); }catch(e){} olay(name); }
  try{ const _l=IDL.load; IDL.load=async function(sp,f){ const a0=this.at[sp]; const r=await _l.apply(this,arguments); try{ if((sp===1||sp===2)&&this.at[sp]!==a0&&this.ok[sp]) idlDiff(sp); }catch(e){} return r; }; }catch(e){}
  // b) ESPN canlı skor listesi (yıldız: bulutoxx-fav)
  const EZ=new Map(); let ePr=false;
  try{ const _u=W.onLiveUpdate; W.onLiveUpdate=function(evs){ let r; try{ if(typeof _u==="function") r=_u.apply(this,arguments); }finally{ try{ espnDiff(evs); }catch(e){} } return r; }; }catch(e){}
  function espnDiff(evs){ let fav; try{ fav=new Set(JSON.parse(localStorage.getItem("bulutoxx-fav")||"[]")); }catch(e){ fav=new Set(); }
    for(const id in evs){ const e=evs[id], prev=EZ.get(id), ht=/\bHT\b|Halftime|Devre/i.test(e.detail||""), rc=(e.rc||[0,0]).reduce((a,b)=>a+b,0);
      EZ.set(id,{state:e.state,ht,rc}); if(!ePr||!prev||!fav.has(id)) continue;
      if(prev.state==="pre"&&e.state==="in") ev("macBasladi",`⚽ ${e.h} – ${e.a} başladı`);
      else if(e.state==="in"&&ht&&!prev.ht) ev("ilkYari",`⏸ İlk yarı bitti · ${e.h} ${e.hs}-${e.as} ${e.a}`);
      else if(prev.state==="in"&&e.state==="post") ev("macBitti",`🏁 Maç bitti · ${e.h} ${e.hs}-${e.as} ${e.a}`);
      if(e.state==="in"&&rc>prev.rc) ev("kirmizi",`🟥 Kırmızı kart · ${e.h} – ${e.a}`); }
    ePr=true; }

  // ---------- KUPO seçim ekle / çıkar ----------
  try{ const _ct=cpToggle; cpToggle=function(m,mk){ let had=false, n0=0; try{ had=cpHas(m,mk); n0=CP.items.length; }catch(e){}
      const r=_ct.apply(this,arguments); try{ const now=cpHas(m,mk); if(now!==had) olay(now?"kupoEkle":"kupoCikar"); else if(CP.items.length!==n0) olay(CP.items.length>n0?"kupoEkle":"kupoCikar"); }catch(e){} return r; }; }catch(e){}

  // ---------- arayüz kancaları ----------
  D.addEventListener("click",e=>{ const t=e.target; if(t&&t.closest&&t.closest("#navPow")) olay("power"); },true);
  function watchHidden(el,onOpen,onClose){ if(!el) return; let was=el.hidden; try{ new MutationObserver(()=>{ if(el.hidden===was) return; was=el.hidden; (was?onClose:onOpen)(); }).observe(el,{attributes:true,attributeFilter:["hidden"]}); }catch(e){} }
  watchHidden(D.getElementById("sheet"),()=>olay("ac"),()=>olay("kapa"));
  try{ const _bo=botOpen; botOpen=function(){ const r=_bo.apply(this,arguments); olay("ac"); return r; }; const _bc=botClose; botClose=function(){ const el=D.getElementById("botSheet"), op=el&&!el.hidden; const r=_bc.apply(this,arguments); if(op) olay("kapa"); return r; }; }catch(e){}
  try{ const _bs=botSend; botSend=async function(){ olay("msgOut"); const r=await _bs.apply(this,arguments); olay("msgIn"); return r; }; }catch(e){}
  // yatay kaydırma (gün/lig şeritleri): kaydırma bitince çok ince bir tık
  D.addEventListener("scrollend",e=>{ const t=e.target; if(!t||t===D||!t.scrollWidth) return; if(t.scrollWidth>t.clientWidth+8&&t.scrollHeight<=t.clientHeight+8) olay("kaydir"); },true);

  // ---------- Ayarlar › Sesler ----------
  const GR=[["⚽ Futbol",["gol","golRakip","macBasladi","ilkYari","macBitti","kirmizi"]],["🏆 KUPO",["kupoEkle","kupoCikar","bacak","kupoTuttu","tutmadi"]],
    ["🏀 Basket",["bkTuttu","bkBitti"]],["🐎 At yarışı",["atCagri","atSerit","atStart","atKazandi","atKupoTuttu"]],
    ["✨ Menü ve OXXai",["tab","tap","acik","kapali","ac","kapa","kaydir","power","msgOut","msgIn","star","ready"]]];
  const E=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const swc=(k,ic,cls,b,s)=>`<div class="cell"><span class="ic ${cls}" aria-hidden="true">${ic}</span><span class="tx"><b>${b}</b><small>${s}</small></span><label class="sw"><input type="checkbox" data-ses="${k}" ${PREFS[k]!==false?"checked":""} aria-label="${E(b)}"><i></i></label></div>`;
  function setHtml(){ const v=Math.round((isFinite(+PREFS.sesVol)?+PREFS.sesVol:.8)*100);
    return `<div class="ses-h" id="sesHead"><h3>🎧 Sesler</h3><small>OXXai ses kimliği</small></div>
    <div class="group${PREFS.sound?"":" off"}" id="sesSet">
      <div class="cell ses-not" id="sesNot" ${PREFS.sound?"hidden":""}>Ses modu kapalı: yalnız titreşim. Üst çubuktaki Ses düğmesinden “Ses ve titreşim”e geç.</div>
      <div class="cell ses-vol"><span class="ic mix" aria-hidden="true">🔊</span><span class="tx"><b>Ana ses düzeyi</b><small id="sesVolTx">%${v}</small></span><input type="range" id="sesVol" min="0" max="100" step="5" value="${v}" style="--v:${v}%" aria-label="Ana ses düzeyi"></div>
      ${swc("sesGol","⚽","gold","Gol ve maç olayları","Yıldızla takip ettiğin maçta gol, başlama, devre, bitiş, kırmızı kart")}
      ${swc("sesKupo","🏆","gold","KUPO sesleri","Seçim ekle/çıkar, tutan maç, KUPO sonucu")}
      ${swc("sesAt","🐎","gold","At yarışı sesleri","Atım koşuyor çağrısı, start, kazanan at")}
      ${swc("sesBasket","🏀","blue","Basket sesleri","Takip ettiğin maç bitti, tutan seçim")}
      ${swc("sesMenu","✨","blue","Menü sesleri","Sekme, düğme, aç/kapa, kaydırma, OXXai mesajı")}
      ${swc("sesAnons","🎙","mix","Sesli gol anonsu",trVoice()?"Gol olunca kısa Türkçe anons":"Bu cihazda Türkçe ses bulunamadı; anons sessizce atlanır")}
    </div>
    <details class="ses-ls" id="sesDinle"><summary><span class="ic" aria-hidden="true">▶</span><span class="tx"><b>Sesleri dinle</b><small>${Object.keys(R).length} ses · her birini dene</small></span></summary>
      ${GR.map(([h,L])=>`<div class="ses-g"><h4>${h}</h4><div class="ses-row">${L.map(n=>`<button type="button" class="ses-p" data-sesp="${n}" aria-label="${E(AD[n])} sesini dinle"><i aria-hidden="true">▶</i><span>${E(AD[n])}</span></button>`).join("")}</div></div>`).join("")}
    </details>
    <p class="ses-kay" id="sesKay">Ses kaynakları (değiştirilerek kullanıldı): kalabalık “goal scored” jordiroquer · alkış Mike Koenig · tezahürat ve dörtnala Steffen Gerlach (C-evo) — CC BY 3.0; düdük cityrocker, file Electroviolence — CC0; buzzer TuxMath — kamu malı. Diğer sesler OXXai için sentezlendi. <a href="ses_kaynaklari.md" target="_blank" rel="noopener">Ayrıntı</a></p>`; }
  function wire(bx){ bx.querySelectorAll("input[data-ses]").forEach(inp=>inp.addEventListener("change",()=>{ PREFS[inp.dataset.ses]=inp.checked; try{ savePrefs(); }catch(e){} try{ buzz(6); }catch(e){} olay(inp.checked?"acik":"kapali",{preview:true}); }));
    const r=bx.querySelector("#sesVol"), tx=bx.querySelector("#sesVolTx");
    if(r){ r.addEventListener("input",()=>{ PREFS.sesVol=(+r.value)/100; if(tx) tx.textContent="%"+r.value; r.style.setProperty("--v",r.value+"%"); try{ if(bus) bus.vol.gain.value=volG(); }catch(e){} });
      r.addEventListener("change",()=>{ try{ savePrefs(); }catch(e){} olay("tab",{preview:true}); }); }
    bx.querySelectorAll("[data-sesp]").forEach(b=>b.addEventListener("click",e=>{ e.stopPropagation(); const n=b.dataset.sesp;
      if(!PREFS.sound){ try{ toast("Ses modu kapalı · üst çubuktaki Ses düğmesinden aç"); }catch(_){} return; }
      if(!unlocked) unlock();
      const o={preview:true}; if(n==="gol"&&PREFS.sesAnons&&trVoice()){ o.say="Gol! Galatasaray, 2 1!"; o.cos=true; o.sayAt=1.15; }
      lastN[n]=0; olay(n,o); b.classList.remove("on"); void b.offsetWidth; b.classList.add("on"); }));
    // ilk gruptaki "Ses efektleri" anahtarı değişirse uyarıyı güncelle
    const fx=bx.querySelector("#p-sound"); if(fx) fx.addEventListener("change",()=>paintOff(bx)); }
  function paintOff(bx){ const g=bx.querySelector("#sesSet"), n=bx.querySelector("#sesNot"); if(g) g.classList.toggle("off",!PREFS.sound); if(n) n.hidden=!!PREFS.sound; }
  const sh=D.getElementById("sheet");
  if(sh) new MutationObserver(()=>{ const bx=sh.querySelector('.box[aria-label="Ayarlar"]'); if(!bx||bx.querySelector("#sesSet")) return;
      const g=bx.querySelector(":scope > .group"); if(!g) return; g.insertAdjacentHTML("afterend",setHtml()); wire(bx); }).observe(sh,{childList:true});
  W.OXX_SES={olay,names:()=>Object.keys(R),log:LOG};
})();
} catch (e) { if (typeof reportError === "function") reportError(e); else setTimeout(function () { throw e; }); } /* /id: ses-v121 */
