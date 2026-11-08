"""⚽ YH-55 · KG (karşılıklı gol) olasılığına iddaa KG oranının katılması — bayrak, motor ayarı ve 14 gün izleme / otomatik geri alma.

Kanıt: lab/kg_piyasa_lab.py → data/kg_piyasa_lab.json (önceden kayıtlı kapı geçti, 2026-11-08). Uygulama (js/katmanlar.js `kg-piyasa-v165`)
oranlı ve KG oranı olan maçta KG Var = σ(w·logit q + (1−w)·logit p_dist); q = KG oranının oransal payı. w motor tarafından
model.json params.kg_piyasa'ya yazılır; bayrak kapalıysa alan yazılmaz ve uygulama eski dist() KG'sini gösterir (geri alınabilir).

Bayrak: data/kg_piyasa.json {aktif, w, baslangic, izleme_bitis, durum: izleniyor | kalici | geri_alindi, izleme: {...}}.
İzleme (motor her çalışmada, yalnız kilitli bülten arşivinden; iki yol da kilitli orandan yeniden hesaplanabildiği için karşı-olgusal):
  başlangıçtan sonraki günlerde Δ = LL(uygulanan) − LL(eski dist). En az 5 gün ve 300 maç olunca Δ > 0 ve gün-blok %95 GA alt sınırı > 0
  ise → aktif false, durum "geri_alindi" (otomatik). 14 gün dolunca ve geri alınmadıysa durum "kalici". Ağ yok, ücretsiz.
"""
import json, math, os, random
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
YOL = os.path.join(DATA, "kg_piyasa.json")
MIN_GUN, MIN_MAC = 5, 300


def _jl(p, d=None):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d


def ayar():
    """Yayındaysa {"w": w, "devig": "oransal"}; değilse None."""
    A = _jl(YOL)
    if not A or not A.get("aktif") or A.get("durum") == "geri_alindi": return None
    try: w = float(A.get("w"))
    except Exception: return None
    if not 0 < w <= 1: return None
    o = {"w": round(w, 3), "devig": "oransal", "v": A.get("v", 1)}
    if A.get("pazar_aktif"): o["pazar"] = True   # YH-56: pazar motoru KGV / MS&KG (scripts/pazar.py enrich)
    return o


def _ll(p, y):
    p = min(max(p, 1e-9), 1 - 1e-9); return -math.log(p if y else 1 - p)


def izle(U, bugun=None):
    """Bayrak izleniyorsa karşı-olgusal izleme ölçer; gerekirse geri alır. Dönüş: kısa özet ya da None."""
    A = _jl(YOL)
    if not A or A.get("durum") not in ("izleniyor",) or not A.get("aktif"): return None
    bugun = (bugun or date.today()).isoformat()
    try:
        import sys
        sys.path.insert(0, os.path.join(ROOT, "lab"))
        import kg_piyasa_lab as L
        R = [r for r in L.kayitlar() if r["d"] > A["baslangic"]]
        oz = {"tarih": bugun, "n": len(R), "gun": len({r["d"] for r in R})}
        if R:
            p0, _ = L.uretim_btts(R); w = float(A["w"])
            G = {}
            for r, p in zip(R, p0):
                inv = (1 / r["kgo"][0], 1 / r["kgo"][1]); q = inv[0] / sum(inv)
                lg = lambda x: math.log(min(max(x, 1e-6), 1 - 1e-6) / (1 - min(max(x, 1e-6), 1 - 1e-6)))
                pa = 1 / (1 + math.exp(-(w * lg(q) + (1 - w) * lg(p))))
                G.setdefault(r["d"], []).append(_ll(pa, r["y"]) - _ll(p, r["y"]))
            v = [x for g in G.values() for x in g]; oz["delta_ll"] = round(sum(v) / len(v), 5)
            gl = list(G.values()); rnd = random.Random(5); bs = []
            for _ in range(1000):
                s = [x for _ in gl for x in rnd.choice(gl)]; bs.append(sum(s) / len(s))
            bs.sort(); oz["ga95"] = [round(bs[25], 5), round(bs[974], 5)]
            if oz["gun"] >= MIN_GUN and oz["n"] >= MIN_MAC and oz["delta_ll"] > 0 and oz["ga95"][0] > 0:
                A["aktif"] = False; A["durum"] = "geri_alindi"; A["geri_alma"] = {"tarih": bugun, "neden": "izlemede KG log-kaybı belirgin kötüleşti", **oz}
        if A.get("durum") == "izleniyor" and bugun >= A.get("izleme_bitis", "9999"): A["durum"] = "kalici"
        A["izleme"] = oz
        json.dump(A, open(YOL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return oz
    except Exception as e:
        return {"hata": f"{e.__class__.__name__}: {e}"}
