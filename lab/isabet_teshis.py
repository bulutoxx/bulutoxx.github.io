"""🩺 İsabet teşhisi (YH-53): kilitli tahmin kayıtlarından son 30 / 60 gün karnesi. Yalnız ölçüm, üretimi değiştirmez.

Kaynaklar (yalnız türetilmiş, depoda olanlar):
  data/predlog.json  : motorun lig maçları için kilitli tahmini. p/o = model yolu (açılış), mp/mo = piyasa payı (açılış),
                       ps/pso = uygulamanın oranlı maçta gösterdiği (açılış); pc/pco, mpc/mpco, psc/psco = kapanış kilidi (≤75 dk).
                       Oransız maçta uygulamanın gösterdiği = p/o (topluluk ya da Poisson).
  data/archive/*.json: iddaa bülteni kilitli kaydı (yalnız oranlı). p/o25/kg = ham piyasa yolu, sk/sp = uygulamanın öneri seçeneği ve
                       olasılığı, sok = sonucu; ms/ou/kgo = oranlar.
ÖNEMLİ: predlog.json'da aynı kimlik birden çok kez bulunabiliyor (gonder.py birleştirme hatası, YH-53). Teşhis kimlik başına TEK kayıt sayar
(tekilleştirme: scripts/predlog_tekil.py ile aynı kural).

Çıktı: data/isabet_teshis_lab.json
"""
import glob, json, math, os, sys
from collections import Counter, defaultdict
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from predlog_tekil import tekillestir   # noqa: E402

EPS = 1e-9


def s3(r): return 0 if r[0] > r[1] else 1 if r[0] == r[1] else 2


def ll3(q, y): return -math.log(max(q[y], EPS))


def br3(q, y): return sum((q[k] - (k == y)) ** 2 for k in range(3))


def ll2(p, y): return -math.log(max(p if y else 1 - p, EPS))


def ece(pairs, kova=10):
    """pairs: (olasılık, 0/1). Eşit genişlikli kova ECE."""
    if not pairs: return None
    B = defaultdict(list)
    for p, y in pairs: B[min(kova - 1, int(p * kova))].append((p, y))
    return round(sum(abs(sum(p for p, _ in v) - sum(y for _, y in v)) for v in B.values()) / len(pairs), 4)


def ozet3(rows, k):
    v = [(e[k], s3(e["r"])) for e in rows if isinstance(e.get(k), list) and len(e[k]) == 3]
    if not v: return None
    top = [(max(q), int(max(range(3), key=lambda i: q[i]) == y)) for q, y in v]
    return {"n": len(v), "isabet": round(sum(t for _, t in top) / len(v), 4), "ll": round(sum(ll3(q, y) for q, y in v) / len(v), 4),
            "brier": round(sum(br3(q, y) for q, y in v) / len(v), 4), "ece_top": ece(top)}


def ozet2(rows, k, yf):
    v = [(float(e[k]), int(yf(e))) for e in rows if isinstance(e.get(k), (int, float))]
    if not v: return None
    return {"n": len(v), "isabet": round(sum((p >= .5) == bool(y) for p, y in v) / len(v), 4), "ll": round(sum(ll2(p, y) for p, y in v) / len(v), 4),
            "brier": round(sum((p - y) ** 2 for p, y in v) / len(v), 4), "ece": ece(v)}


def fark(rows, ka, kb, ikili=None):
    """Aynı alt kümede a − b log-kayıp farkı (+ = a kötü), gün bloklu bootstrap %95 GA."""
    if ikili:
        v = [(e["d"], ll2(e[ka], ikili(e)) - ll2(e[kb], ikili(e))) for e in rows
             if isinstance(e.get(ka), (int, float)) and isinstance(e.get(kb), (int, float))]
    else:
        v = [(e["d"], ll3(e[ka], s3(e["r"])) - ll3(e[kb], s3(e["r"]))) for e in rows
             if isinstance(e.get(ka), list) and isinstance(e.get(kb), list)]
    if len(v) < 20: return {"n": len(v)}
    import random
    rnd = random.Random(7); G = defaultdict(list)
    for d, x in v: G[d].append(x)
    gl = list(G.values()); bs = []
    for _ in range(1000):
        s = [x for _ in gl for x in rnd.choice(gl)]; bs.append(sum(s) / len(s))
    bs.sort()
    return {"n": len(v), "fark": round(sum(x for _, x in v) / len(v), 4), "ga": [round(bs[25], 4), round(bs[974], 4)]}


def ust(e): return sum(e["r"]) > 2


def kg_(e): return e["r"][0] > 0 and e["r"][1] > 0


def predlog_teshis(log, bas, bit):
    es = [e for e in log if isinstance(e.get("r"), list) and len(e["r"]) == 2 and bas <= e["d"] <= bit]
    oranli = [e for e in es if e.get("mp")]; oransiz = [e for e in es if not e.get("mp")]
    for e in es:   # uygulamanın gösterdiği: oranlıda ps/psc, oransızda p
        e["_s"] = e.get("ps") if e.get("mp") else e["p"]
        e["_so"] = e.get("pso") if e.get("mp") else e.get("o")
        e["_sc"] = e.get("psc") if e.get("mp") else e.get("pc")
        e["_kg"] = (e["pz"][6] / 1000) if isinstance(e.get("pz"), list) and len(e["pz"]) > 6 else None
    out = {"n": len(es), "n_oranli": len(oranli), "n_oransiz": len(oransiz),
           "beraberlik_gercek": round(sum(s3(e["r"]) == 1 for e in es) / len(es), 4) if es else None,
           "ms_1x2": {"sunulan_acilis": ozet3(es, "_s"), "model_acilis": ozet3(es, "p"), "piyasa_acilis": ozet3(oranli, "mp"),
                      "oranli_sunulan_acilis": ozet3([e for e in oranli if e.get("ps")], "ps"),
                      "oranli_sunulan_kapanis": ozet3([e for e in oranli if e.get("psc")], "psc"),
                      "oranli_piyasa_kapanis": ozet3([e for e in oranli if e.get("mpc")], "mpc"),
                      "oranli_model_kapanis": ozet3([e for e in oranli if e.get("pc") and e.get("mpc")], "pc"),
                      "oransiz_sunulan": ozet3(oransiz, "p")},
           "ou25": {"model_acilis": ozet2(es, "o", ust), "piyasa_acilis": ozet2(oranli, "mo", ust),
                    "oranli_sunulan_acilis": ozet2(oranli, "pso", ust), "oranli_piyasa_kapanis": ozet2(oranli, "mpco", ust),
                    "oranli_sunulan_kapanis": ozet2(oranli, "psco", ust), "oransiz_sunulan": ozet2(oransiz, "o", ust)},
           "kg": {"pazar_motoru": ozet2([e for e in es if e["_kg"] is not None], "_kg", kg_)},
           "farklar": {"1x2_model_eksi_piyasa_acilis": fark(oranli, "p", "mp"),
                       "1x2_model_eksi_piyasa_kapanis": fark([e for e in oranli if e.get("pc") and e.get("mpc")], "pc", "mpc"),
                       "1x2_sunulan_eksi_piyasa_kapanis": fark([e for e in oranli if e.get("psc") and e.get("mpc")], "psc", "mpc"),
                       "1x2_sunulan_eksi_piyasa_acilis": fark([e for e in oranli if e.get("ps")], "ps", "mp"),
                       "ou_model_eksi_piyasa_acilis": fark(oranli, "o", "mo", ikili=ust),
                       "ou_model_eksi_piyasa_kapanis": fark(oranli, "pco", "mpco", ikili=ust),
                       "ou_sunulan_eksi_piyasa_kapanis": fark(oranli, "psco", "mpco", ikili=ust)}}
    # lig kırılımı (oranlı, açılış model − piyasa) ve oransız lig karnesi
    L = defaultdict(list)
    for e in es: L[e["lg"]].append(e)
    lig = {}
    for lg, rows in L.items():
        o_ = [e for e in rows if e.get("mp")]
        z = {"n": len(rows), "n_oranli": len(o_)}
        if o_:
            z["ll_model"] = round(sum(ll3(e["p"], s3(e["r"])) for e in o_) / len(o_), 4)
            z["ll_piyasa"] = round(sum(ll3(e["mp"], s3(e["r"])) for e in o_) / len(o_), 4)
            z["fark"] = round(z["ll_model"] - z["ll_piyasa"], 4)
        n_ = [e for e in rows if not e.get("mp")]
        if n_: z["oransiz_ll"] = round(sum(ll3(e["p"], s3(e["r"])) for e in n_) / len(n_), 4); z["oransiz_isabet"] = round(sum(max(range(3), key=lambda i: e["p"][i]) == s3(e["r"]) for e in n_) / len(n_), 4)
        lig[lg] = z
    out["lig"] = dict(sorted(lig.items(), key=lambda kv: -kv[1]["n"]))
    # güven kovası (sunulan en olası seçenek, açılış)
    kv = defaultdict(lambda: [0, 0, 0.0])
    for e in es:
        q = e["_s"]
        if not isinstance(q, list): continue
        m = max(q); k = "<0,45" if m < .45 else "0,45-0,58" if m < .58 else "0,58-0,70" if m < .70 else "0,70-0,78" if m < .78 else "≥0,78"
        kv[k][0] += 1; kv[k][1] += int(max(range(3), key=lambda i: q[i]) == s3(e["r"])); kv[k][2] += m
    out["guven_kovasi_1x2"] = {k: {"n": v[0], "isabet": round(v[1] / v[0], 4), "ort_olasilik": round(v[2] / v[0], 4)} for k, v in sorted(kv.items())}
    return out


def arsiv_kayitlar():
    R = []
    for f in sorted(glob.glob(os.path.join(DATA, "archive", "*.json"))) + sorted(glob.glob(os.path.join(DATA, "archive", "eski", "*.json"))):
        g = os.path.basename(f)[:10]
        try: D = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        if not isinstance(D, dict): continue
        for k, r in D.items():
            if isinstance(r, dict) and isinstance(r.get("hs"), int) and isinstance(r.get("as"), int):
                r = dict(r); r["d"] = g; r["kim"] = k; R.append(r)
    return R


def pay(o):
    inv = [1 / x for x in o]; s = sum(inv); return [x / s for x in inv]


def arsiv_teshis(R, bas, bit):
    rs = [r for r in R if bas <= r["d"] <= bit]
    for r in rs: r["r"] = [r["hs"], r["as"]]
    ms = [r for r in rs if isinstance(r.get("ms"), list) and len(r["ms"]) == 3 and all(x and x > 1 for x in r["ms"])]
    for r in ms: r["_mp"] = pay(r["ms"])
    ou = [r for r in rs if isinstance(r.get("ou"), list) and len(r["ou"]) == 2 and all(x and x > 1 for x in r["ou"])]
    for r in ou: r["_mo"] = pay(r["ou"])[0]
    kg = [r for r in rs if isinstance(r.get("kgo"), list) and len(r["kgo"]) == 2 and all(x and x > 1 for x in r["kgo"])]
    for r in kg: r["_mk"] = pay(r["kgo"])[0]
    out = {"n": len(rs), "ms_1x2": {"ham_piyasa_yolu": ozet3(ms, "p"), "oran_payi": ozet3(ms, "_mp")},
           "ou25": {"ham_piyasa_yolu": ozet2(ou, "o25", ust), "oran_payi": ozet2(ou, "_mo", ust)},
           "kg": {"ham_piyasa_yolu": ozet2(kg, "kg", kg_), "oran_payi": ozet2(kg, "_mk", kg_)}}
    sv = [r for r in rs if r.get("sk") and isinstance(r.get("sok"), bool)]
    kv = defaultdict(list)
    for r in sv:
        p = r["sp"]; k = "<0,58 (pas)" if p < .58 else "0,58-0,70" if p < .70 else "0,70-0,78" if p < .78 else "≥0,78"
        kv[k].append((p, int(r["sok"])))
        kv["tur_" + ("ms" if r["sk"] in "1X2" else "ou")].append((p, int(r["sok"])))
    out["oneri"] = {"n": len(sv), "isabet": round(sum(r["sok"] for r in sv) / len(sv), 4) if sv else None,
                    "ece": ece([(r["sp"], int(r["sok"])) for r in sv]),
                    "kova": {k: {"n": len(v), "isabet": round(sum(y for _, y in v) / len(v), 4), "ort_olasilik": round(sum(p for p, _ in v) / len(v), 4)}
                             for k, v in sorted(kv.items())}}
    sec = defaultdict(list)
    for r in sv: sec[r["sk"]].append((r["sp"], int(r["sok"])))
    out["oneri"]["secenek"] = {k: {"n": len(v), "isabet": round(sum(y for _, y in v) / len(v), 4), "ort_olasilik": round(sum(p for p, _ in v) / len(v), 4)} for k, v in sorted(sec.items())}
    return out


def drift_kontrol(log):
    D = json.load(open(os.path.join(DATA, "drift.json"), encoding="utf-8"))
    ham = json.load(open(os.path.join(DATA, "predlog.json"), encoding="utf-8"))
    c = Counter(e["lg"] for e in ham if isinstance(e.get("r"), list) and e.get("mp"))
    t = Counter(e["lg"] for e in log if isinstance(e.get("r"), list) and e.get("mp"))
    alarm = {}
    for lg, v in D.get("ligler", {}).items():
        if v.get("durum") == "alarm" or v.get("agirlik_1x2", 1) < 1 or v.get("agirlik_ou", 1) < 1:
            alarm[lg] = {"agirlik_1x2": v.get("agirlik_1x2"), "agirlik_ou": v.get("agirlik_ou"), "n_drift": v.get("1x2", {}).get("n"),
                         "oranli_puanli_ham": c.get(lg, 0), "oranli_puanli_tekil": t.get(lg, 0)}
    return {"canli_alarm": D.get("canli", {}).get("alarm"), "dusuk_agirlik": D.get("dusuk_agirlik"), "alarmlar": alarm}


def main():
    ham = json.load(open(os.path.join(DATA, "predlog.json"), encoding="utf-8"))
    log, oz = tekillestir(ham)
    bugun = date.today()
    R = arsiv_kayitlar()
    out = {"v": 1, "guncelleme": bugun.isoformat(), "predlog_tekillestirme": oz,
           "kapsam": {"predlog_ilk": min(e["d"] for e in log), "arsiv_ilk": min(r["d"] for r in R) if R else None},
           "donem": {}}
    for ad, g in (("son30", 30), ("son60", 60)):
        bas = (bugun - timedelta(days=g)).isoformat(); bit = bugun.isoformat()
        out["donem"][ad] = {"bas": bas, "predlog": predlog_teshis([dict(e) for e in log], bas, bit), "arsiv": arsiv_teshis([dict(r) for r in R], bas, bit)}
    # çiftli (ham) kayıtla aynı karne: yanılmanın büyüklüğü
    b30 = (bugun - timedelta(days=30)).isoformat()
    out["ham_ciftli_son30"] = {k: v for k, v in predlog_teshis([dict(e) for e in ham], b30, bugun.isoformat()).items() if k in ("n", "beraberlik_gercek", "farklar")}
    out["drift"] = drift_kontrol(log)
    json.dump(out, open(os.path.join(DATA, "isabet_teshis_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False)[:200])


if __name__ == "__main__":
    main()
