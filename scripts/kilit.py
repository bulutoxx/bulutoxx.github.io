"""🔒 Kilit karnesi (açılış + kapanış). Yalnız standart kütüphane; motor (update.py), toplayıcı (collector.py) ve OXXai karnesi
(oxx_kupon.py) aynı hesabı kullanır. Hiçbir tahmini değiştirmez.

Alanlar (data/predlog.json):
  açılış  : p / o (model, ilk kilit — asla değişmez), mp (piyasa payı), mo (piyasa 2,5 Üst payı), ps / pso (uygulamanın gösterdiği), ts
  kapanış : maça ≤ 75 dk kala bir kez yazılır, sonra değişmez — pc / pco (model), mpc / mpco (piyasa payı, marj ayıklanmış),
            psc / psco (uygulamanın gösterdiği), pcts (yazıldığı an), pcdk (maça kalan dakika)
"""
import math
from datetime import datetime, timezone


def _sonuc3(r): return 0 if r[0] > r[1] else 1 if r[0] == r[1] else 2

def kilit_karne(log):
    """Açılış ve kapanış kilidi karnesi (canlı karnenin eski alanları değişmez; bu yeni blok). Her blokta aynı maç alt kümesinde
    model / piyasa / uygulamanın gösterdiği olasılık: n, 1X2 log-kayıp, Brier; 2,5 Üst için ayrıca."""
    es = [e for e in log if isinstance(e.get("r"), list) and len(e["r"]) == 2]
    def ll(q, y): return -math.log(max(q[y], 1e-9))
    def br(q, y): return sum((q[k] - (k == y)) ** 2 for k in range(3))
    def blok(rows, alanlar):
        out = {"n": len(rows)}
        if not rows: return out
        for ad, k in alanlar:
            v = [(e[k], _sonuc3(e["r"])) for e in rows if isinstance(e.get(k), list) and len(e[k]) == 3]
            if len(v) == len(rows):
                out[ad] = {"ll": round(sum(ll(q, y) for q, y in v) / len(v), 4), "brier": round(sum(br(q, y) for q, y in v) / len(v), 4),
                           "beraberlik": round(sum(q[1] for q, _ in v) / len(v), 4)}
        out["beraberlik_gercek"] = round(sum(_sonuc3(e["r"]) == 1 for e in rows) / len(rows), 4)
        if out.get("model") and out.get("piyasa"): out["fark_ll"] = round(out["model"]["ll"] - out["piyasa"]["ll"], 4)
        return out
    def blok_ou(rows, km, kp):
        v = [(e[km], e[kp], sum(e["r"]) > 2) for e in rows if isinstance(e.get(km), (int, float)) and isinstance(e.get(kp), (int, float))]
        if not v: return {"n": 0}
        l = lambda p, y: -math.log(max(p if y else 1 - p, 1e-9))
        return {"n": len(v), "model_ll": round(sum(l(a, y) for a, _, y in v) / len(v), 4), "piyasa_ll": round(sum(l(b, y) for _, b, y in v) / len(v), 4),
                "model_brier": round(sum((a - y) ** 2 for a, _, y in v) / len(v), 4), "piyasa_brier": round(sum((b - y) ** 2 for _, b, y in v) / len(v), 4)}
    ac = [e for e in es if e.get("mp")]; kp_ = [e for e in es if e.get("pc")]; kpm = [e for e in kp_ if e.get("mpc")]
    out = {"acilis": dict(blok(es, (("model", "p"),)), oranli=blok(ac, (("model", "p"), ("piyasa", "mp"))),
                          oranli_sunulan=blok([e for e in ac if e.get("ps")], (("model", "p"), ("piyasa", "mp"), ("sunulan", "ps"))),
                          ou=blok_ou(es, "o", "mo")),
           "kapanis": dict(blok(kp_, (("model", "pc"), ("acilis_model", "p"))),
                           oranli=blok(kpm, (("model", "pc"), ("piyasa", "mpc"), ("acilis_model", "p"), ("acilis_piyasa", "mp"))),
                           oranli_sunulan=blok([e for e in kpm if e.get("psc")], (("model", "pc"), ("piyasa", "mpc"), ("sunulan", "psc"))),
                           ou=blok_ou(kp_, "pco", "mpco")),
           "kapsam": round(len(kp_) / len(es), 4) if es else None}
    try:   # kilit maçtan ne kadar önce? (saat; yalnız kilit anı bilinen kayıtlar)
        h = []
        for e in es:
            if not e.get("ts"): continue
            t0 = datetime.strptime(e["ts"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
            h.append((datetime.fromisoformat(e["d"] + "T12:00:00+00:00") - t0).total_seconds() / 3600)
        if h: h.sort(); out["acilis_kilit_saat"] = {"ortanca": round(h[len(h) // 2], 1), "p90": round(h[int(len(h) * .9)], 1), "n": len(h)}
        pdk = sorted(e["pcdk"] for e in es if isinstance(e.get("pcdk"), int))
        if pdk: out["kapanis_kilit_dk"] = {"ortanca": pdk[len(pdk) // 2], "n": len(pdk)}
    except Exception: pass
    out["aciklama"] = ("acilis = maçtan önceki ilk kilit (p, mp, ps); kapanis = maça ≤75 dk kala bir kez yazılan ikinci kilit (pc, mpc, psc). "
                       "model = motorun model yolu, piyasa = oran payı, sunulan = uygulamanın oranlı maçta gösterdiği. fark_ll = model − piyasa.")
    return out


def bacak_kapanis(bacaklar, log):
    """OXXai karnesi için: sonuçlanmış futbol 1X2 tahminlerinin (mac = predlog kimliği) açılış ve kapanış kilidindeki olasılığı.
    bacaklar: [{mac, kod, p, tuttu}]. Dönüş: n, isabet, ort. açılış p, ort. kapanış model / piyasa olasılığı (aynı alt küme)."""
    ix = {e.get("id"): e for e in log}; K = {"1": 0, "X": 1, "2": 2}; v = []; gor = set()
    for b in bacaklar:
        e = ix.get(b.get("mac")); k = K.get(b.get("kod"))
        if (b.get("mac"), k) in gor: continue   # aynı tahmin birden çok listede: bir kez sayılır
        gor.add((b.get("mac"), k))
        if e is None or k is None or b.get("tuttu") is None or not isinstance(e.get("pc"), list): continue
        v.append((float(b.get("p") or 0), e["pc"][k], e["mpc"][k] if isinstance(e.get("mpc"), list) else None, bool(b["tuttu"])))
    if not v: return {"n": 0}
    m = [x for x in v if x[2] is not None]
    out = {"n": len(v), "isabet": round(sum(x[3] for x in v) / len(v), 4), "acilis_p": round(sum(x[0] for x in v) / len(v), 4),
           "kapanis_model": round(sum(x[1] for x in v) / len(v), 4)}
    if m: out.update(n_piyasa=len(m), kapanis_piyasa=round(sum(x[2] for x in m) / len(m), 4), isabet_piyasa_alt=round(sum(x[3] for x in m) / len(m), 4))
    return out
