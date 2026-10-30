#!/usr/bin/env python3
# OXXai at lab — YH-15: koşu belirsizliğine göre seçici gösterim (pas eşiği). Yalnız ölçüm; üretimi değiştirmez.
#   Her koşu için yalnız koşu öncesi bilinen bilgiden güven özellikleri: ilk olasılık p1, ilk iki farkı p1−p2,
#   normalize entropi H/ln n, alan büyüklüğü ln n. Aday puan = bu dört özellikten "ilk seçim kazanır" lojistik modeli
#   (aylık ileri yürüyüş: yalnız önceki aylarla öğrenilir). Eşik = eğitim aylarında puanın %25'lik dilimi (hedef kapsam %75).
#   Kapı (ön kayıtlı, yol haritası): sınama aylarında seçilen koşuların ilk seçim isabeti − tüm koşuların isabeti
#   (= aynı kapsamda rastgele seçimin beklenen isabeti) için koşu günü blok bootstrap %95 GA alt sınırı > 0,
#   iki zaman yarısında da fark > 0, tek yanlı p ≤ 0,025. Yalnız-model (sabah) birincil; harman ayrı raporlanır.
#   Ek (bilgi): aynı kapsamda yalnız p1 eşiği ve aday − p1 farkı (entropi/alan bilgisi p1'in üstüne bir şey katıyor mu).
# Girdi: data/at/replay_kosular.json (sızıntısız p_sabah; ham, git'e girmez) + aynanın data/results/*.json (nihai oran;
#   AT_KAYNAK, varsayılan ./_tjk-data; tjk.org'a istek YOK). Çıktı yalnız türetilmiş özet: data/at/secici_lab.json.
# python3 lab/at/secici_lab.py [--ayna DİZİN] [--replay YOL] [--B 2000] [--kapsam 0.75]
import argparse, datetime as dt, glob, json, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CIKTI = os.path.join(ROOT, "data", "at", "secici_lab.json")
BAYRAK = os.path.join(ROOT, "data", "at", "secici.json")   # uygulamanın okuduğu küçük parametre/bayrak dosyası
MIN_EGITIM = 600          # ilk sınama ayından önce en az bu kadar koşu
P_ESIK = 0.025


def oku_sonuc(ayna):
    out = {}
    for f in glob.glob(os.path.join(ayna, "data/results/*.json")):
        try:
            js = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for r in js if isinstance(js, list) else []:
            try:
                out[f"{r['date']}|{r['venue']}|{r['raceNo']}"] = {str(h["no"]): h.get("odds") for h in r["horses"]
                                                                 if not h.get("nonRunner")}
            except (KeyError, TypeError):
                continue
    return out


def kosular_kur(replay, sonuc):
    R = json.load(open(replay, encoding="utf-8"))["kosular"]
    S, atla = [], {}
    for kr in R:
        a = kr["a"]
        if len(a) < 2:
            atla["alan < 2"] = atla.get("alan < 2", 0) + 1; continue
        y = np.array([1.0 if x[3] == 1 else 0.0 for x in a])
        if y.sum() != 1:
            atla["kazanan yok"] = atla.get("kazanan yok", 0) + 1; continue
        ps = np.clip(np.array([float(x[1]) for x in a]), 1e-6, 1); ps /= ps.sum()
        q = None
        od = sonuc.get(f"{kr['t']}|{kr['h']}|{kr['k']}")
        if od:
            try:
                o = np.array([float(od[str(x[0])]) for x in a])
                if (o > 1.0).all():
                    q = 1 / o; q /= q.sum()
            except (KeyError, TypeError, ValueError):
                q = None
        S.append({"t": kr["t"], "ps": ps, "q": q, "y": y})
    S.sort(key=lambda s: s["t"])
    return S, atla


def ozellik(p):
    s = np.sort(p)[::-1]; n = len(p)
    H = float(-(p * np.log(np.clip(p, 1e-12, 1))).sum() / np.log(n))
    return [s[0], s[0] - s[1], H, np.log(n)]


def lojistik(X, y, lam=1.0, it=50):
    X1 = np.c_[np.ones(len(X)), X]; w = np.zeros(X1.shape[1])
    R = np.eye(X1.shape[1]) * lam; R[0, 0] = 0
    for _ in range(it):
        z = np.clip(X1 @ w, -30, 30); p = 1 / (1 + np.exp(-z))
        g = X1.T @ (p - y) + R @ w
        Hm = X1.T @ (X1 * (p * (1 - p))[:, None]) + R
        d = np.linalg.solve(Hm, g); w -= d
        if np.abs(d).max() < 1e-8:
            break
    return w


def harman_uydur(ps_list, q_list, y_list):
    best, ab = -1e18, (1.0, 0.0)
    for a in np.arange(0, 1.51, 0.1):
        for b in np.arange(0, 1.51, 0.1):
            ll = 0.0
            for ps, q, y in zip(ps_list, q_list, y_list):
                l = a * np.log(ps) + b * np.log(q); l -= l.max(); p = np.exp(l); p /= p.sum()
                ll += np.log(max(p[y.argmax()], 1e-12))
            if ll > best:
                best, ab = ll, (a, b)
    return ab


def ay(t):
    return t[:7]


def ileri_yuruyus(S, yol, kapsam):
    """yol: 'sabah' ya da 'harman'. Dönüş: sınama kayıtları (t, isabet, seçildi_aday, seçildi_p1)."""
    if yol == "harman":
        S = [s for s in S if s["q"] is not None]
    aylar = sorted({ay(s["t"]) for s in S}); kayit = []
    for m in aylar:
        egit = [s for s in S if ay(s["t"]) < m]; test = [s for s in S if ay(s["t"]) == m]
        if len(egit) < MIN_EGITIM or not test:
            continue
        if yol == "harman":
            a, b = harman_uydur([s["ps"] for s in egit], [s["q"] for s in egit], [s["y"] for s in egit])

            def P(s):
                l = a * np.log(s["ps"]) + b * np.log(s["q"]); l -= l.max(); p = np.exp(l); return p / p.sum()
        else:
            def P(s):
                return s["ps"]
        Xe = np.array([ozellik(P(s)) for s in egit]); ye = np.array([float(s["y"][P(s).argmax()]) for s in egit])
        mu, sd = Xe.mean(0), Xe.std(0) + 1e-9
        w = lojistik((Xe - mu) / sd, ye)
        puan = lambda X: np.c_[np.ones(len(X)), (X - mu) / sd] @ w
        esik_c = np.quantile(puan(Xe), 1 - kapsam); esik_p = np.quantile(Xe[:, 0], 1 - kapsam)
        Xt = np.array([ozellik(P(s)) for s in test]); pt = puan(Xt)
        for s, x, c in zip(test, Xt, pt):
            p = P(s); kayit.append((s["t"], float(s["y"][p.argmax()]), bool(c >= esik_c), bool(x[0] >= esik_p)))
    return kayit


def uretim_param(S, yol, kapsam):
    """Tüm geçmişle (yalnız biten koşular) güven puanı katsayıları ve eşik; uygulama yeni koşulara uygular."""
    if yol == "harman":
        S = [s for s in S if s["q"] is not None]
        a, b = harman_uydur([s["ps"] for s in S], [s["q"] for s in S], [s["y"] for s in S])
        P = lambda s: (lambda l: np.exp(l - l.max()) / np.exp(l - l.max()).sum())(a * np.log(s["ps"]) + b * np.log(s["q"]))
    else:
        P = lambda s: s["ps"]
    X = np.array([ozellik(P(s)) for s in S]); y = np.array([float(s["y"][P(s).argmax()]) for s in S])
    mu, sd = X.mean(0), X.std(0) + 1e-9
    w = lojistik((X - mu) / sd, y)
    esik = float(np.quantile(np.c_[np.ones(len(X)), (X - mu) / sd] @ w, 1 - kapsam))
    r = lambda v: [round(float(x), 6) for x in v]
    return {"w": r(w), "mu": r(mu), "sd": r(sd), "esik": round(esik, 6), "n": len(S)}


def fark(kayit, sec_idx):
    h = np.array([k[1] for k in kayit]); s = np.array([k[sec_idx] for k in kayit])
    return float(h[s].mean() - h.mean()) if s.any() else 0.0


def fark_ab(kayit):
    h = np.array([k[1] for k in kayit]); a = np.array([k[2] for k in kayit]); b = np.array([k[3] for k in kayit])
    return float((h[a].mean() if a.any() else 0) - (h[b].mean() if b.any() else 0))


def boot(kayit, f, B, rng):
    gunler = sorted({k[0] for k in kayit}); G = {g: [k for k in kayit if k[0] == g] for g in gunler}
    v = []
    for _ in range(B):
        ornek = [x for g in rng.choice(len(gunler), len(gunler)) for x in G[gunler[g]]]
        v.append(f(ornek))
    v = np.array(v)
    return [round(float(np.quantile(v, 0.025)), 4), round(float(np.quantile(v, 0.975)), 4)], round(float((v <= 0).mean()), 4)


def degerlendir(kayit, B, rng):
    if not kayit:
        return None
    h = np.array([k[1] for k in kayit]); a = np.array([k[2] for k in kayit]); b = np.array([k[3] for k in kayit])
    gunler = sorted({k[0] for k in kayit}); orta = gunler[len(gunler) // 2]
    y1 = [k for k in kayit if k[0] < orta]; y2 = [k for k in kayit if k[0] >= orta]
    fa = lambda K: fark(K, 2); fp = lambda K: fark(K, 3)
    ga, p = boot(kayit, fa, B, rng); ga_p1, _ = boot(kayit, fp, B, rng); ga_ab, p_ab = boot(kayit, fark_ab, B, rng)
    return {"n": len(kayit), "gun": len(gunler), "donem": [gunler[0], gunler[-1]],
            "isabet_tum": round(float(h.mean()), 4),
            "aday": {"kapsam": round(float(a.mean()), 4), "isabet": round(float(h[a].mean()), 4),
                     "isabet_pas": round(float(h[~a].mean()), 4) if (~a).any() else None,
                     "fark": round(fa(kayit), 4), "ga95": ga, "p_tek": p,
                     "yari1": round(fa(y1), 4), "yari2": round(fa(y2), 4)},
            "p1_esigi": {"kapsam": round(float(b.mean()), 4), "isabet": round(float(h[b].mean()), 4),
                         "fark": round(fp(kayit), 4), "ga95": ga_p1},
            "aday_eksi_p1": {"fark": round(fark_ab(kayit), 4), "ga95": ga_ab, "p_tek": p_ab}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ayna", default=os.environ.get("AT_KAYNAK", os.path.join(ROOT, "_tjk-data")))
    ap.add_argument("--replay", default=os.path.join(ROOT, "data", "at", "replay_kosular.json"))
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--kapsam", type=float, default=0.75)
    A = ap.parse_args()
    if not os.path.exists(A.replay):
        print("girdi yok (replay_kosular); atlandı"); return 0
    sonuc = oku_sonuc(A.ayna) if os.path.isdir(os.path.join(A.ayna, "data", "results")) else {}
    S, atla = kosular_kur(A.replay, sonuc)
    rng = np.random.default_rng(15)
    R = {}
    for yol in ("sabah", "harman"):
        R[yol] = degerlendir(ileri_yuruyus(S, yol, A.kapsam), A.B, rng)
    b = R["sabah"]
    gecti = bool(b and b["aday"]["ga95"][0] > 0 and b["aday"]["yari1"] > 0 and b["aday"]["yari2"] > 0
                 and b["aday"]["p_tek"] <= P_ESIK)
    out = {"olusturma": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "madde": "YH-15",
           "aciklama": "Seçici gösterim (pas eşiği): güven puanı = lojistik(p1, p1−p2, normalize entropi, ln alan), aylık ileri "
                       "yürüyüş; eşik eğitimde %25'lik dilim (hedef kapsam %75). Fark = seçilenlerin ilk seçim isabeti − tüm koşular "
                       "(aynı kapsamda rastgele seçimin beklentisi). Kapı (sabah): koşu günü blok bootstrap GA alt > 0, iki yarıda > 0, "
                       "p ≤ 0,025. Üretimi değiştirmez.",
           "kapsam_hedef": A.kapsam, "B": A.B, "kosu": len(S), "oranli_kosu": sum(s["q"] is not None for s in S),
           "atlanan": atla, "sonuc": R, "kapi_gecti": gecti}
    os.makedirs(os.path.dirname(CIKTI), exist_ok=True)
    json.dump(out, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    # Bayrak: kapı geçtiyse uygulama "belirsiz koşu" etiketini gösterir; geçmezse aktif=false (etiket kendiliğinden kalkar).
    hb = R["harman"]
    bay = {"guncelleme": out["olusturma"], "madde": "YH-15", "aktif": gecti, "kapsam_hedef": A.kapsam,
           "ozellik": ["p1", "p1-p2", "H/ln n", "ln n"],
           "sabah": uretim_param(S, "sabah", A.kapsam),
           "harman": uretim_param(S, "harman", A.kapsam) if out["oranli_kosu"] >= MIN_EGITIM else None,
           "olcum": {"sabah": {k: b["aday"][k] for k in ("kapsam", "isabet", "isabet_pas", "fark", "ga95")} | {"isabet_tum": b["isabet_tum"], "n": b["n"]},
                     "harman": ({k: hb["aday"][k] for k in ("kapsam", "isabet", "isabet_pas", "fark", "ga95")} | {"isabet_tum": hb["isabet_tum"], "n": hb["n"]}) if hb else None}}
    json.dump(bay, open(BAYRAK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("BAYRAK " + json.dumps(bay, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
