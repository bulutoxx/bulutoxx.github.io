#!/usr/bin/env python3
# OXXai at lab — YH-08: sabah (oransız, kilitli) model olasılığının KAPANIŞ piyasasına bilgi katkısı (at için CLV ölçümü).
# Ölçüm; üretimi değiştirmez. Kapı yok, karne satırı ("sabah modeli piyasaya bilgi ekliyor mu").
#   (b) Benter ikinci aşaması: koşu içi koşullu logit  p_i ∝ exp(a·ln p_sabah,i + b·ln q_kapanış,i).
#       a > 0 ve a'nın koşu-günü blok bootstrap %95 GA alt sınırı > 0 → "doğrulandı"; son 90 gün GA'sı 0'ı kapsıyorsa → alarm.
#       Ayrıca aylık ileri yürüyüş (yalnız önceki aylarla öğrenilen a, b) ile harman − kapanış ΔLL (sızıntısız, bilgi amaçlı).
#   (a) Yön: kapanış hareketi ln q_kapanış − ln q_erken'in, ln p_sabah − ln q_erken'e eğimi (erken = koşudan ≥ 30 dk önceki
#       son görüntü; yalnız aynanın odds-snapshots dosyaları ve bu deponun data/at/oran_izi/ günleri, varsa). Eğim > 0 →
#       piyasa sabah modelinin yönüne kayıyor.
# Girdi: data/at/replay_kosular.json (replay.py'nin gün gün, sızıntısız p_sabah'ı; ham, git'e girmez) + aynanın
#   data/results/*.json nihai oranları (AT_KAYNAK, varsayılan ./_tjk-data; tjk.org'a istek YOK). q = 1/oran, koşu içinde
#   normalize (marj orantılı ayrılır; oran_izi.py ile aynı). Çıktı yalnız türetilmiş özet: data/at/bilgi_katkisi.json ve
#   data/at/karne.json → "bilgi_katkisi". Ham oran / at adı yazılmaz.
# python3 lab/at/bilgi_katkisi.py [--ayna DİZİN] [--replay YOL] [--B 2000]
import argparse, collections, datetime as dt, glob, json, math, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CIKTI = os.path.join(ROOT, "data", "at", "bilgi_katkisi.json")
KARNE = os.path.join(ROOT, "data", "at", "karne.json")
ESIK_DK = 30
MIN_KOSU = 300           # bir pencerede a tahmini için en az koşu
SON_GUN = 90


def oku_sonuc(ayna):
    """k -> {at no: nihai oran}; koşmayanlar hariç."""
    out = {}
    for f in glob.glob(os.path.join(ayna, "data/results/*.json")):
        try:
            js = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for r in js if isinstance(js, list) else []:
            try:
                k = f"{r['date']}|{r['venue']}|{r['raceNo']}"
                out[k] = {str(h["no"]): (h.get("name"), h.get("odds")) for h in r["horses"] if not h.get("nonRunner")}
            except (KeyError, TypeError):
                continue
    return out


def post_ts(t, saat):
    return dt.datetime.fromisoformat(f"{t}T{saat}:00+03:00").timestamp()


def oku_erken(ayna):
    """k -> {at adı: erken oran} (koşudan ≥ ESIK_DK önceki SON görüntü). Kaynak: aynanın odds-snapshots/*.jsonl."""
    erken = {}
    for f in sorted(glob.glob(os.path.join(ayna, "data/odds-snapshots/*.jsonl"))):
        per = collections.defaultdict(lambda: collections.defaultdict(dict)); saat = {}
        try:
            for ln in open(f, encoding="utf-8"):
                r = json.loads(ln)
                k = f"{r['date']}|{r['venue']}|{r['raceNo']}"
                ts = dt.datetime.fromisoformat(r["ts"].replace("Z", "+00:00")).timestamp()
                per[k][ts][r["name"]] = r["odds"]; saat[k] = r.get("time")
        except (OSError, ValueError, KeyError, TypeError):
            continue
        for k, s in per.items():
            if not saat.get(k):
                continue
            try:
                p = post_ts(k.split("|")[0], saat[k])
            except ValueError:
                continue
            on = [t for t in s if t <= p - ESIK_DK * 60]
            if on:
                erken[k] = s[max(on)]
    return erken


def kosular_kur(replay, sonuc, erken):
    R = json.load(open(replay, encoding="utf-8"))["kosular"]
    S, atla = [], collections.Counter()
    for kr in R:
        k = f"{kr['t']}|{kr['h']}|{kr['k']}"
        if k not in sonuc:
            atla["sonuç/oran yok"] += 1; continue
        a = kr["a"]; no2 = sonuc[k]
        try:
            o = np.array([float(no2[x[0]][1]) for x in a])
        except (KeyError, TypeError, ValueError):
            atla["oran eksik"] += 1; continue
        if (o <= 1.0).any() or len(a) < 2:
            atla["oran geçersiz"] += 1; continue
        y = np.array([1.0 if x[3] == 1 else 0.0 for x in a])
        if y.sum() != 1:
            atla["kazanan yok"] += 1; continue
        q = 1 / o; q /= q.sum()
        ps = np.clip(np.array([float(x[1]) for x in a]), 1e-6, 1); ps /= ps.sum()
        e = None
        if k in erken:
            try:
                e = np.array([1 / float(erken[k][no2[x[0]][0]]) for x in a]); e /= e.sum()
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                e = None
        S.append({"t": kr["t"], "ps": ps, "q": q, "e": e, "y": y})
    S.sort(key=lambda s: s["t"])
    return S, dict(atla)


class Duz:
    """Koşuları düz dizilere çevirir (vektörel koşullu logit)."""
    def __init__(self, S):
        self.n = len(S)
        lens = np.array([len(s["y"]) for s in S]); self.bas = np.r_[0, np.cumsum(lens)[:-1]]
        self.idx = np.repeat(np.arange(self.n), lens)
        self.X = np.c_[np.log(np.concatenate([s["ps"] for s in S])), np.log(np.concatenate([s["q"] for s in S]))]
        self.y = np.concatenate([s["y"] for s in S])
        gunler = sorted({s["t"] for s in S}); gi = {g: i for i, g in enumerate(gunler)}
        self.gun = np.array([gi[s["t"]] for s in S]); self.G = len(gunler)

    def olas(self, w):
        z = self.X @ w
        zm = np.maximum.reduceat(z, self.bas)[self.idx]
        ez = np.exp(z - zm); den = np.add.reduceat(ez, self.bas)
        return ez / den[self.idx]

    def uydur(self, kw=None, w0=None, it=25):
        """kw: koşu ağırlıkları (bootstrap sayımları). Newton, en çok olabilirlik."""
        kw = np.ones(self.n) if kw is None else kw
        w = np.array([0.0, 1.0]) if w0 is None else w0.copy()
        hw = kw[self.idx]
        for _ in range(it):
            p = self.olas(w)
            mu = np.c_[np.add.reduceat(p * self.X[:, 0], self.bas), np.add.reduceat(p * self.X[:, 1], self.bas)]
            g = ((self.y - p)[:, None] * self.X * hw[:, None]).sum(0)
            Xc = self.X - mu[self.idx]
            H = (Xc * (p * hw)[:, None]).T @ Xc + 1e-9 * np.eye(2)
            st = np.linalg.solve(H, g); w += st
            if np.abs(st).max() < 1e-7:
                break
        return w

    def ll_kosu(self, w):
        p = self.olas(w)
        return -np.log(np.maximum(np.add.reduceat(p * self.y, self.bas), 1e-12))


def benter(S, B, rng):
    if len(S) < MIN_KOSU:
        return {"n_kosu": len(S), "yeterli": False}
    D = Duz(S); w = D.uydur()
    gk = np.bincount(D.gun, minlength=D.G)  # gün başına koşu
    bs = []
    for _ in range(B):
        c = np.bincount(rng.integers(0, D.G, D.G), minlength=D.G)   # gün sayımı
        bs.append(D.uydur(kw=c[D.gun].astype(float), w0=w, it=8))
    bs = np.array(bs)
    ga_a = np.percentile(bs[:, 0], [2.5, 97.5]); ga_b = np.percentile(bs[:, 1], [2.5, 97.5])
    llq = D.ll_kosu(np.array([0.0, 1.0])).mean(); llh = D.ll_kosu(w).mean()
    return {"n_kosu": D.n, "n_gun": int(D.G), "donem": [S[0]["t"], S[-1]["t"]], "yeterli": True,
            "a": round(float(w[0]), 4), "a_ga95": [round(float(x), 4) for x in ga_a],
            "b": round(float(w[1]), 4), "b_ga95": [round(float(x), 4) for x in ga_b],
            "ll_kapanis": round(float(llq), 4), "ll_harman_orneklem_ici": round(float(llh), 4),
            "p_a_sifir_alti": round(float((bs[:, 0] <= 0).mean()), 4), "ort_kosu_gun": round(float(gk.mean()), 2)}


def ileri_yuruyus(S, B, rng):
    """Aylık: yalnız önceki aylarla (a, b) öğren, ayı tahmin et; harman − kapanış ΔLL, gün-blok bootstrap."""
    aylar = sorted({s["t"][:7] for s in S}); d, gun, aylik = [], [], []
    for ay in aylar:
        egit = [s for s in S if s["t"][:7] < ay]; test = [s for s in S if s["t"][:7] == ay]
        if len(egit) < MIN_KOSU or not test:
            continue
        w = Duz(egit).uydur(); T = Duz(test)
        fark = T.ll_kosu(w) - T.ll_kosu(np.array([0.0, 1.0]))
        d.extend(fark.tolist()); gun.extend([s["t"] for s in test])
        aylik.append({"ay": ay, "n": len(test), "a": round(float(w[0]), 4), "b": round(float(w[1]), 4),
                      "dll": round(float(fark.mean()), 4)})
    if not d:
        return {"n_kosu": 0}
    d = np.array(d); gl = sorted(set(gun)); gi = {g: i for i, g in enumerate(gl)}; gix = np.array([gi[g] for g in gun])
    top = np.bincount(gix, weights=d, minlength=len(gl)); say = np.bincount(gix, minlength=len(gl))
    bs = []
    for _ in range(B):
        c = np.bincount(rng.integers(0, len(gl), len(gl)), minlength=len(gl))
        bs.append((c * top).sum() / max((c * say).sum(), 1))
    h = len(d) // 2
    return {"n_kosu": int(len(d)), "dll": round(float(d.mean()), 5), "ga95": [round(float(x), 5) for x in np.percentile(bs, [2.5, 97.5])],
            "yarilar": [round(float(d[:h].mean()), 5), round(float(d[h:].mean()), 5)], "aylik": aylik}


def yon(S, B, rng):
    """(a) ln q_kapanış − ln q_erken  ~  c · (ln p_sabah − ln q_erken); at düzeyinde OLS (koşu içi merkezli), gün-blok GA."""
    T = [s for s in S if s["e"] is not None]
    if len(T) < 50:
        return {"n_kosu": len(T), "yeterli": False, "not": "erken oran görüntüsü yetersiz (aynanın odds-snapshots dosyaları / kendi izimiz)"}
    xs, ys, gun = [], [], []
    gl = sorted({s["t"] for s in T}); gi = {g: i for i, g in enumerate(gl)}
    for s in T:
        le = np.log(s["e"]); x = np.log(s["ps"]) - le; y = np.log(s["q"]) - le
        xs.append(x - x.mean()); ys.append(y - y.mean()); gun.append(np.full(len(x), gi[s["t"]]))
    x = np.concatenate(xs); y = np.concatenate(ys); g = np.concatenate(gun)
    sxy = np.bincount(g, weights=x * y, minlength=len(gl)); sxx = np.bincount(g, weights=x * x, minlength=len(gl))
    c = sxy.sum() / sxx.sum()
    bs = []
    for _ in range(B):
        k = np.bincount(rng.integers(0, len(gl), len(gl)), minlength=len(gl))
        bs.append((k * sxy).sum() / max((k * sxx).sum(), 1e-12))
    return {"n_kosu": len(T), "n_at": int(len(x)), "yeterli": True, "egim": round(float(c), 4),
            "ga95": [round(float(v), 4) for v in np.percentile(bs, [2.5, 97.5])], "donem": [T[0]["t"], T[-1]["t"]]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ayna", default=os.environ.get("AT_KAYNAK", os.path.join(ROOT, "_tjk-data")))
    ap.add_argument("--replay", default=os.path.join(ROOT, "data", "at", "replay_kosular.json"))
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--cikti", default=CIKTI)
    ap.add_argument("--karne", default=KARNE)
    A = ap.parse_args()
    if not os.path.exists(A.replay) or not os.path.isdir(os.path.join(A.ayna, "data", "results")):
        print("girdi yok (replay_kosular veya ayna sonuçları); atlandı"); return 0
    rng = np.random.default_rng(8)
    sonuc = oku_sonuc(A.ayna); erken = oku_erken(A.ayna)
    S, atla = kosular_kur(A.replay, sonuc, erken)
    print("koşu:", len(S), "atlanan:", atla)
    if not S:
        print("eşleşen koşu yok; atlandı"); return 0
    son_t = S[-1]["t"]
    esik = (dt.date.fromisoformat(son_t) - dt.timedelta(days=SON_GUN)).isoformat()
    h = len(S) // 2
    tum = benter(S, A.B, rng)
    son90 = benter([s for s in S if s["t"] > esik], A.B, rng)
    yarilar = [benter(S[:h], A.B // 4, rng), benter(S[h:], A.B // 4, rng)]
    iy = ileri_yuruyus(S, A.B, rng)
    yn = yon(S, A.B, rng)
    dogru = bool(tum.get("yeterli") and tum["a_ga95"][0] > 0 and son90.get("yeterli") and son90["a_ga95"][0] > 0)
    alarm = bool(son90.get("yeterli") and son90["a_ga95"][0] <= 0)
    durum = "doğrulandı" if dogru else ("alarm: son 90 günde a'nın GA'sı 0'ı kapsıyor" if alarm else "belirsiz (veri az)")
    out = {"olusturma": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "madde": "YH-08",
           "aciklama": "Benter ikinci aşaması: koşu içi koşullu logit p ∝ exp(a·ln p_sabah + b·ln q_kapanış). p_sabah: replay.py'nin "
                       "gün gün sızıntısız oransız sabah olasılığı; q_kapanış: aynanın nihai oranı, marjı orantılı ayrılmış. "
                       "a > 0 (GA alt sınırı > 0) → sabah modeli kapanış piyasasına bilgi ekliyor. GA: koşu-günü blok bootstrap.",
           "durum": durum, "dogrulandi": dogru, "alarm": alarm, "B": A.B, "atlanan": atla,
           "tum": tum, "son90": son90, "yarilar": yarilar, "ileri_yuruyus": iy, "yon": yn}
    os.makedirs(os.path.dirname(A.cikti), exist_ok=True)
    json.dump(out, open(A.cikti, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    try:
        k = json.load(open(A.karne, encoding="utf-8"))
        k["bilgi_katkisi"] = {"satir": "Sabah modeli piyasaya bilgi ekliyor mu", "durum": durum, "a": tum.get("a"),
                              "a_ga95": tum.get("a_ga95"), "a_son90": son90.get("a"), "a_son90_ga95": son90.get("a_ga95"),
                              "n_kosu": tum.get("n_kosu"), "ileri_dll": iy.get("dll"), "ileri_ga95": iy.get("ga95"),
                              "guncelleme": out["olusturma"], "kaynak": "data/at/bilgi_katkisi.json"}
        json.dump(k, open(A.karne, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except (OSError, ValueError) as e:
        print("karne güncellenemedi:", e)
    print(json.dumps({x: out[x] for x in ("durum",)}, ensure_ascii=False), "a", tum.get("a"), tum.get("a_ga95"),
          "son90", son90.get("a"), son90.get("a_ga95"), "ileri", iy.get("dll"), iy.get("ga95"), "yön", yn.get("egim"), yn.get("ga95"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
