#!/usr/bin/env python3
# OXXai at lab — YH-28: Bolton–Chapman / Benter çok aşamalı birleşim, KOŞULLU ikinci aşama (yalnız ölçüm; üretimi değiştirmez).
#   Taban (mevcut harman, YH-08):  p_i ∝ exp(a·ln p_sabah,i + b·ln q_i)            — tek (a, b), aylık ileri yürüyüş.
#   Aday:  p_i ∝ exp((a + Σ_j δa_j·d_j)·ln p_sabah,i + (b + Σ_j δb_j·d_j)·ln q_i)   — d_j: koşu kovası göstergeleri
#          (alan büyüklüğü, koşu türü, piyasa derinliği = favori q, büyük/küçük hipodrom); δ'lar L2 ile 0'a (= taban) küçültülür.
#   Kovalar yalnız koşu öncesi bilinen bilgiden (alan, sınıf adı, hipodrom, piyasa oranı) — kapanış sonrası bilgi yok.
#   Kapı (ön kayıtlı, birincil aday K4 = tüm kovalar, λ = 30): aylık ileri yürüyüş (yalnız önceki aylarla öğren), aday − taban ΔLL;
#   koşu-günü blok bootstrap %95 GA üst < 0 ve iki yarıda ΔLL < 0. Diğer adaylar (tek kova ailesi) yalnız bilgi amaçlı.
# Girdi: data/at/replay_kosular.json (sızıntısız p_sabah; ham, git'e girmez) + aynanın data/results/*.json (nihai oran, sınıf,
#   AT_KAYNAK, varsayılan ./_tjk-data; tjk.org'a istek YOK). Çıktı yalnız türetilmiş özet: data/at/benter_kosullu_lab.json.
# python3 lab/at/benter_kosullu_lab.py [--ayna DİZİN] [--replay YOL] [--B 2000]
import argparse, datetime as dt, glob, json, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CIKTI = os.path.join(ROOT, "data", "at", "benter_kosullu_lab.json")
MIN_KOSU = 300
BUYUK_HIP = {"İstanbul", "Ankara", "İzmir", "Bursa", "Adana"}
LAMBDA = 30.0
LAMBDALAR = [5.0, 30.0, 150.0]


def tur_kovasi(sinif):
    s = (sinif or "").lower()
    if "maiden" in s:
        return "maiden"
    if "handikap" in s or "kısa vade" in s:
        return "handikap"
    if "şartl" in s or "sartl" in s or "satış" in s:
        return "sartli"
    if s.startswith("kv") or "g 1" in s or "g 2" in s or "g 3" in s or "grup" in s:
        return "kv_grup"
    return "diger"


def alan_kovasi(n):
    return "n<=7" if n <= 7 else ("n8-10" if n <= 10 else ("n11-13" if n <= 13 else "n14+"))


def derinlik_kovasi(qmax):
    return "fav<.25" if qmax < 0.25 else ("fav.25-.40" if qmax < 0.40 else "fav>=.40")


AILELER = {"alan": ["n<=7", "n8-10", "n11-13", "n14+"],
           "tur": ["maiden", "handikap", "sartli", "kv_grup", "diger"],
           "derinlik": ["fav<.25", "fav.25-.40", "fav>=.40"],
           "hipodrom": ["buyuk", "kucuk"]}
ADAYLAR = {"K1 alan": ["alan"], "K2 tür": ["tur"], "K3 derinlik": ["derinlik"], "K5 hipodrom": ["hipodrom"],
           "K4 tümü (birincil)": ["alan", "tur", "derinlik", "hipodrom"]}
BIRINCIL = "K4 tümü (birincil)"


def oku_sonuc(ayna):
    out = {}
    for f in glob.glob(os.path.join(ayna, "data/results/*.json")):
        try:
            js = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for r in js if isinstance(js, list) else []:
            try:
                k = f"{r['date']}|{r['venue']}|{r['raceNo']}"
                out[k] = ({str(h["no"]): h.get("odds") for h in r["horses"] if not h.get("nonRunner")},
                          r.get("raceClass"), r.get("venue"))
            except (KeyError, TypeError):
                continue
    return out


def kosular_kur(replay, sonuc):
    R = json.load(open(replay, encoding="utf-8"))["kosular"]
    S, atla = [], {}
    for kr in R:
        k = f"{kr['t']}|{kr['h']}|{kr['k']}"
        if k not in sonuc:
            atla["sonuç yok"] = atla.get("sonuç yok", 0) + 1; continue
        oranlar, sinif, hip = sonuc[k]; a = kr["a"]
        try:
            o = np.array([float(oranlar[x[0]]) for x in a])
        except (KeyError, TypeError, ValueError):
            atla["oran eksik"] = atla.get("oran eksik", 0) + 1; continue
        if (o <= 1.0).any() or len(a) < 2:
            atla["oran geçersiz"] = atla.get("oran geçersiz", 0) + 1; continue
        y = np.array([1.0 if x[3] == 1 else 0.0 for x in a])
        if y.sum() != 1:
            atla["kazanan yok"] = atla.get("kazanan yok", 0) + 1; continue
        q = 1 / o; q /= q.sum()
        ps = np.clip(np.array([float(x[1]) for x in a]), 1e-6, 1); ps /= ps.sum()
        kova = {"alan": alan_kovasi(len(a)), "tur": tur_kovasi(sinif), "derinlik": derinlik_kovasi(float(q.max())),
                "hipodrom": "buyuk" if (hip or kr["h"]) in BUYUK_HIP else "kucuk"}
        S.append({"t": kr["t"], "ps": ps, "q": q, "y": y, "kova": kova})
    S.sort(key=lambda s: s["t"])
    return S, atla


def tasarim(S, aileler):
    """Kova sütunları (her ailede tüm düzeyler; L2 tanımlılığı sağlar). Dönüş: koşu × m gösterge matrisi, adlar."""
    adlar = [(f, d) for f in aileler for d in AILELER[f]]
    Z = np.array([[1.0 if s["kova"][f] == d else 0.0 for (f, d) in adlar] for s in S]).reshape(len(S), len(adlar))
    return Z, [f"{f}:{d}" for f, d in adlar]


class Kosullu:
    """Koşu içi koşullu logit; X sütunları: ln p, ln q, (ln p)·Z, (ln q)·Z. Ceza yalnız etkileşimlerde (λ/2·‖δ‖²)."""
    def __init__(self, S, Z):
        self.n = len(S)
        lens = np.array([len(s["y"]) for s in S]); self.bas = np.r_[0, np.cumsum(lens)[:-1]]
        self.idx = np.repeat(np.arange(self.n), lens)
        lp = np.log(np.concatenate([s["ps"] for s in S])); lq = np.log(np.concatenate([s["q"] for s in S]))
        Zh = Z[self.idx]
        self.X = np.c_[lp, lq, lp[:, None] * Zh, lq[:, None] * Zh] if Z.shape[1] else np.c_[lp, lq]
        self.y = np.concatenate([s["y"] for s in S])
        self.k = self.X.shape[1]

    def olas(self, w):
        z = self.X @ w
        zm = np.maximum.reduceat(z, self.bas)[self.idx]
        ez = np.exp(z - zm); den = np.add.reduceat(ez, self.bas)
        return ez / den[self.idx]

    def uydur(self, lam, it=30):
        w = np.zeros(self.k); w[1] = 1.0
        P = np.full(self.k, lam); P[:2] = 0.0
        for _ in range(it):
            p = self.olas(w)
            mu = np.stack([np.add.reduceat(p * self.X[:, j], self.bas) for j in range(self.k)], 1)
            g = ((self.y - p)[:, None] * self.X).sum(0) - P * w
            Xc = self.X - mu[self.idx]
            H = (Xc * p[:, None]).T @ Xc + np.diag(P) + 1e-9 * np.eye(self.k)
            st = np.linalg.solve(H, g); w += st
            if np.abs(st).max() < 1e-7:
                break
        return w

    def ll_kosu(self, w):
        p = self.olas(w)
        return -np.log(np.maximum(np.add.reduceat(p * self.y, self.bas), 1e-12))


def ileri_yuruyus(S, aileler, lam):
    """Aylık: yalnız önceki aylarla öğren; aday ve taban (tek a, b) koşu LL'leri. Dönüş: fark listesi, gün listesi, aylık özet."""
    aylar = sorted({s["t"][:7] for s in S}); d, gun, aylik, son_w = [], [], [], None
    for ay in aylar:
        egit = [s for s in S if s["t"][:7] < ay]; test = [s for s in S if s["t"][:7] == ay]
        if len(egit) < MIN_KOSU or not test:
            continue
        Ze, ad = tasarim(egit, aileler); Zt, _ = tasarim(test, aileler)
        E0 = Kosullu(egit, Ze[:, :0]); T0 = Kosullu(test, Zt[:, :0]); w0 = E0.uydur(0.0)
        E1 = Kosullu(egit, Ze); T1 = Kosullu(test, Zt); w1 = E1.uydur(lam)
        fark = T1.ll_kosu(w1) - T0.ll_kosu(w0)
        d.extend(fark.tolist()); gun.extend([s["t"] for s in test]); son_w = (w1, ad)
        aylik.append({"ay": ay, "n": len(test), "dll": round(float(fark.mean()), 5)})
    return np.array(d), gun, aylik, son_w


def blok_ga(d, gun, B, rng):
    gl = sorted(set(gun)); gi = {g: i for i, g in enumerate(gl)}; gix = np.array([gi[g] for g in gun])
    top = np.bincount(gix, weights=d, minlength=len(gl)); say = np.bincount(gix, minlength=len(gl))
    bs = []
    for _ in range(B):
        c = np.bincount(rng.integers(0, len(gl), len(gl)), minlength=len(gl))
        bs.append((c * top).sum() / max((c * say).sum(), 1))
    return [round(float(x), 5) for x in np.percentile(bs, [2.5, 97.5])], len(gl)


def degerlendir(S, aileler, lam, B, rng):
    d, gun, aylik, son = ileri_yuruyus(S, aileler, lam)
    if not len(d):
        return {"n_kosu": 0, "gecti": False}
    ga, ng = blok_ga(d, gun, B, rng); h = len(d) // 2
    yar = [round(float(d[:h].mean()), 5), round(float(d[h:].mean()), 5)]
    out = {"n_kosu": int(len(d)), "n_gun": ng, "lambda": lam, "dll": round(float(d.mean()), 5), "ga95": ga, "yarilar": yar,
           "gecti": bool(ga[1] < 0 and yar[0] < 0 and yar[1] < 0), "aylik": aylik}
    if son is not None:
        w, ad = son; m = len(ad)
        out["son_agirlik"] = {"a": round(float(w[0]), 4), "b": round(float(w[1]), 4),
                              "da": {ad[j]: round(float(w[2 + j]), 4) for j in range(m)},
                              "db": {ad[j]: round(float(w[2 + m + j]), 4) for j in range(m)}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ayna", default=os.environ.get("AT_KAYNAK", os.path.join(ROOT, "_tjk-data")))
    ap.add_argument("--replay", default=os.path.join(ROOT, "data", "at", "replay_kosular.json"))
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--cikti", default=CIKTI)
    A = ap.parse_args()
    if not os.path.exists(A.replay) or not os.path.isdir(os.path.join(A.ayna, "data", "results")):
        print("girdi yok (replay_kosular veya ayna sonuçları); atlandı"); return 0
    rng = np.random.default_rng(28)
    S, atla = kosular_kur(A.replay, oku_sonuc(A.ayna))
    print("koşu:", len(S), "atlanan:", atla)
    if len(S) < 2 * MIN_KOSU:
        print("koşu yetersiz; atlandı"); return 0
    say = {f: {d: sum(1 for s in S if s["kova"][f] == d) for d in AILELER[f]} for f in AILELER}
    adaylar = {}
    for ad, aileler in ADAYLAR.items():
        adaylar[ad] = degerlendir(S, aileler, LAMBDA, A.B, rng)
        print(ad, {k: adaylar[ad][k] for k in ("n_kosu", "dll", "ga95", "yarilar", "gecti") if k in adaylar[ad]})
    duyarlilik = {}
    for lam in LAMBDALAR:
        if lam == LAMBDA:
            continue
        r = degerlendir(S, ADAYLAR[BIRINCIL], lam, A.B // 2, rng)
        duyarlilik[str(lam)] = {k: r.get(k) for k in ("dll", "ga95", "yarilar", "gecti")}
        print("λ", lam, duyarlilik[str(lam)])
    b = adaylar[BIRINCIL]
    durum = "geçti (gölgede üretim adayı)" if b.get("gecti") else "geçmedi"
    out = {"olusturma": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "madde": "YH-28",
           "aciklama": "Benter ikinci aşamasının koşullu sürümü: (a, b) koşu kovalarına göre (alan, tür, favori q, hipodrom) "
                       "L2 küçültmeyle öğrenilir; taban = tek (a, b) harman (YH-08). Aylık ileri yürüyüş, koşu-günü blok bootstrap. "
                       "Kapı: birincil aday (K4, λ=30) ΔLL GA üst < 0 ve iki yarıda < 0. Üretimi değiştirmez.",
           "durum": durum, "birincil": BIRINCIL, "B": A.B, "atlanan": atla, "kova_sayilari": say,
           "donem": [S[0]["t"], S[-1]["t"]], "adaylar": adaylar, "lambda_duyarlilik": duyarlilik}
    os.makedirs(os.path.dirname(A.cikti), exist_ok=True)
    json.dump(out, open(A.cikti, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("durum:", durum)
    return 0


if __name__ == "__main__":
    sys.exit(main())
