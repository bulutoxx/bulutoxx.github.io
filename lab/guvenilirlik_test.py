#!/usr/bin/env python3
"""🧪 scripts/guvenilirlik.py birim testi (YH-09; ağ yok, depo dosyalarına yazmaz).
Denetlenenler: güvenilirlik − çözünürlük + belirsizlik + kova_ici = Brier (±1e-9) rastgele ve uç verilerde, kova içinde
tek değerli tahminde kova_ici = 0 (klasik Murphy), ECE elle hesapla aynı, Wilson aralığı, çok sonuçlu düzleştirme ve
gerçek karne dosyalarındaki yuvarlanmış alanlarla tutarlılık.
  python3 lab/guvenilirlik_test.py"""
import json, math, os, random, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import guvenilirlik as GV  # noqa: E402

TOL = 1e-9


def toplam(A):
    return A["guvenilirlik"] - A["cozunurluk"] + A["belirsizlik"] + A["kova_ici"]


def main():
    rng = random.Random(7); hata = 0
    def kontrol(ad, kosul):
        nonlocal hata
        if not kosul: hata += 1; print("HATA:", ad)
    # 1) ayrışım toplamı = Brier, çeşitli dağılımlar
    for t in range(300):
        n = rng.choice([1, 2, 5, 37, 500, 4000])
        p = [rng.random() ** rng.choice([0.3, 1, 3]) for _ in range(n)]
        y = [int(rng.random() < (q if t % 3 else 1 - q)) for q in p]
        if t % 50 == 0: p = [1.0 if i % 2 else 0.0 for i in range(n)]
        A = GV.ayrisim(p, y)
        kontrol(f"toplam #{t}", abs(toplam(A) - A["brier"]) <= TOL)
        kontrol(f"ece #{t}", abs(A["ece"] - sum(b["n"] * abs(b["tahmin"] - b["gercek"]) for b in A["kovalar"]) / n) <= TOL)
        kontrol(f"n #{t}", sum(b["n"] for b in A["kovalar"]) == n)
    # 2) kova içinde tek değerli tahmin → kova_ici = 0 ve klasik Murphy özdeşliği
    p = [0.05, 0.05, 0.35, 0.35, 0.35, 0.75, 0.75, 0.95]; y = [0, 1, 0, 1, 0, 1, 1, 1]
    A = GV.ayrisim(p, y)
    kontrol("kova_ici 0", abs(A["kova_ici"]) <= TOL)
    kontrol("murphy", abs(A["guvenilirlik"] - A["cozunurluk"] + A["belirsizlik"] - A["brier"]) <= TOL)
    # 3) Wilson: bilinen değer (k=8, n=10 → [0,4902, 0,9433])
    lo, hi = GV.wilson(8, 10)
    kontrol("wilson", abs(lo - 0.4902) < 1e-4 and abs(hi - 0.9433) < 1e-4)
    # 4) çok sonuçlu: düzleştirilmiş Brier = çok sınıflı Brier / K
    P = [[.5, .3, .2], [.2, .2, .6], [.7, .2, .1]]; Y = [0, 2, 1]
    R = GV.coklu(P, Y); bs = sum(sum((q - (j == yi)) ** 2 for j, q in enumerate(ps)) for ps, yi in zip(P, Y)) / 3 / 3
    kontrol("coklu", abs(R["brier"] - round(bs, 6)) <= 1e-6)
    # 5) gerçek karneler: yuvarlanmış alanlar 6 haneye kadar tutarlı (varsa)
    def jl(f):
        try: return json.load(open(os.path.join(ROOT, f), encoding="utf-8"))
        except Exception: return None
    D, B, K, PK = jl("data/daily.json"), jl("data/basket.json"), jl("data/at/karne.json"), jl("data/pazar_karne.json")
    bloklar = [("futbol", (D or {}).get("guvenilirlik", {}).get("tum")), ("canli", ((D or {}).get("canli") or {}).get("guvenilirlik")),
               ("basket", ((B or {}).get("live") or {}).get("guvenilirlik")), ("at", (K or {}).get("guvenilirlik")),
               ("1x2", (((PK or {}).get("canli") or {}).get("guvenilirlik") or {}).get("model"))]
    for ad, g in bloklar:
        if not g or not g.get("n"): continue
        kontrol(f"dosya {ad} toplam", abs(toplam(g) - g["brier"]) <= 5e-6)
        kontrol(f"dosya {ad} n", sum(b["n"] for b in g["kovalar"]) == g["n"])
    print("guvenilirlik_test:", "TAMAM" if not hata else f"{hata} hata")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
