"""🧹 predlog.json tekilleştirme (YH-53). Yalnız standart kütüphane.

Sorun: lab/gonder.py'nin 3 yollu JSON birleştirmesi kimlikli listeyi yalnız kimlikler TEKİLSE kimlik kimlik birleştiriyordu; bir kez
çift kimlik oluşunca (2026-10-27) liste "küme birleşimi"ne düşüyor, iki tarafta da değişen her kayıt ikiye katlanıyordu
(2026-11-08: 3.047 kaydın 1.227'si fazlalık; tek maç 128 kopya). Karneler, drift alarmı ve öğrenme bu fazlalığı ağırlık sanıyordu.

Kural (kilitli tahmin DEĞİŞMEZ): aynı kimliğin tüm kopyalarında p aynıdır (doğrulandı). Kimlik başına tek kayıt:
  * açılış alanları (p, o, mp, ps, ts, v …) ilk kilitlenen kopyadan (en erken ts; yoksa listedeki ilk) alınır;
  * kapanış kilidi alanları (pc, pco, mpc, mpco, psc, psco, pcts, pcdk) en erken pcts'li kopyadan — "bir kez yazılır" ilkesi;
  * eksik alanlar (sonuç r/rh/rs, kadro kd …) diğer kopyalardan liste sırasıyla tamamlanır. Sıra: kimliğin ilk göründüğü yer.
"""

KAPANIS = ("pc", "pco", "mpc", "mpco", "psc", "psco", "pcts", "pcdk")


def tekillestir(log):
    """Dönüş: (tekil liste, özet {n_ham, n_tekil, fazla, cift_kimlik, p_farkli})."""
    grup, sira = {}, []
    for e in log:
        k = e.get("id") if isinstance(e, dict) else None
        if k is None:
            sira.append(("_", e)); continue
        if k not in grup: grup[k] = []; sira.append(("k", k))
        grup[k].append(e)
    out, cift, pf = [], 0, 0
    for tur, x in sira:
        if tur == "_": out.append(x); continue
        L = grup[x]
        if len(L) == 1: out.append(L[0]); continue
        cift += 1
        if len({repr(e.get("p")) for e in L}) > 1: pf += 1
        ilk = min(L, key=lambda e: (e.get("ts") is None, e.get("ts") or ""))
        r = dict(ilk)
        kap = [e for e in L if e.get("pc") is not None]
        if kap:
            k0 = min(kap, key=lambda e: (e.get("pcts") is None, e.get("pcts") or ""))
            for a in KAPANIS:
                if a in k0: r[a] = k0[a]
                else: r.pop(a, None)
        for e in L:
            for a, v in e.items():
                if a in KAPANIS and kap: continue
                if r.get(a) is None and v is not None: r[a] = v
        out.append(r)
    return out, {"n_ham": len(log), "n_tekil": len(out), "fazla": len(log) - len(out), "cift_kimlik": cift, "p_farkli": pf}
