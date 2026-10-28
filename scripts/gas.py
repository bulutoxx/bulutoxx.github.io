"""📈 Skor güdümlü (GAS) dinamik Poisson robotu — YH-11 (Koopman & Lit 2015 JRSS-A; 2019 IJF).

Her takımın hücum (a) ve savunma (b) gücü her maçtan SONRA Poisson log-olabilirliğinin gradyanıyla (skor) güncellenir:
    log λ_ev  = c + h + a_ev  − b_dep          log λ_dep = c + a_dep − b_ev
    skor s_ev = x − λ_ev,  s_dep = y − λ_dep   (birim ölçekleme; Koopman–Lit'in tercih ettiği yalın sürüm)
    a_ev ← B·a_ev + A·s_ev     b_dep ← B·b_dep − A·s_ev
    a_dep ← B·a_dep + A·s_dep  b_ev ← B·b_ev − A·s_dep
    c, h (lig gol düzeyi ve ev avantajı) küçük adımla (κ) çevrimiçi öğrenilir; sezon başında güçler ortalamaya çekilir (rev).
A (adım) ve B (kalıcılık) laboratuvarda seçim diliminde ızgarayla seçilir (lab/fb_guc_lab.py). Maç öncesi λ yalnız o maçtan
ÖNCEKİ sonuçlarla kurulur (sızıntısız). Yalnız numpy/math; motor (scripts/guc.py) ve laboratuvar ortak kullanır.
"""
import math

GAS_VARSAYILAN = {"A": 0.03, "B": 0.999, "kappa": 0.004, "rev": 0.2, "yeni": -0.08, "c0": 0.27, "h0": 0.22}


def gas_seq(ms, prm=None):
    """ms: tarih sıralı, ft dolu maçlar. Dönüş: (maç öncesi [(λ_ev, λ_dep)], durum)."""
    p = dict(GAS_VARSAYILAN, **(prm or {}))
    A, B, k, rev, yeni = p["A"], p["B"], p["kappa"], p["rev"], p["yeni"]
    a, b = {}, {}; c, h = p["c0"], p["h0"]; out = []; cur = None
    for m in ms:
        s = m.get("season")
        if cur is not None and s != cur and a:
            for t in a: a[t] *= (1 - rev); b[t] *= (1 - rev)
        cur = s
        H, D = m["h"], m["a"]
        for t in (H, D):
            if t not in a: a[t] = yeni; b[t] = yeni
        lh = math.exp(min(2.0, max(-3.0, c + h + a[H] - b[D]))); la = math.exp(min(2.0, max(-3.0, c + a[D] - b[H])))
        out.append((lh, la))
        x, y = m["ft"][0], m["ft"][1]
        sh, sa = x - lh, y - la
        a[H] = B * a[H] + A * sh; b[D] = B * b[D] - A * sh
        a[D] = B * a[D] + A * sa; b[H] = B * b[H] - A * sa
        c += k * (sh + sa) / 2; h += k * (sh - sa) / 2
    return out, {"a": a, "b": b, "c": c, "h": h, "yeni": yeni}


def gas_lam(st, H, D):
    y = st["yeni"]; a, b = st["a"], st["b"]
    lh = math.exp(min(2.0, max(-3.0, st["c"] + st["h"] + a.get(H, y) - b.get(D, y))))
    la = math.exp(min(2.0, max(-3.0, st["c"] + a.get(D, y) - b.get(H, y))))
    return lh, la
