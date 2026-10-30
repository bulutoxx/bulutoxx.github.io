#!/usr/bin/env python3
"""⏱️ YH-17 · Her an geçerli (sıralı) test laboratuvarı — gölgede, eski kapıyla paralel; üretime etkisi yok.

Kapı (yol haritası): (1) sıfır hipotezi altında 10.000 tekrarlık benzetimde, her blokta bakılsa bile yanlış red oranı ≤ 0,05;
(2) geçmiş kapı kararlarıyla ≥ %90 uyum. Ek rapor: karar süresi (sabit 14 blok kapıya göre), saf "her gün bak" sabit testin
şişen hata oranı, ilişkili blok (AR) duyarlılığı, koruyucunun (lab/guardian.py) geçmiş 14 gün izleme kararlarının sıralı tekrarı.

  python3 lab/siralik_lab.py [--tekrar 10000]   → data/siralik_lab.json
"""
import argparse, glob, json, math, os, sys, time
from collections import defaultdict
from datetime import date, timedelta

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "lab")); sys.path.insert(0, os.path.join(ROOT, "scripts"))
import siralik as S  # noqa: E402

ALFA, T_HEDEF, T_UFUK, T_MAX = 0.05, 14, 90, 42
Z_SABIT = 1.959964


def _gurultu(rng, R, T, ar=0.0):
    """Ağır kuyruklu (t, sd=3), değişken blok büyüklüklü (n_b ~ 5 + Poisson(40)) blok ortalaması gürültüsü; isteğe bağlı AR(1)."""
    nb = 5 + rng.poisson(40, size=(R, T))
    e = rng.standard_t(3, size=(R, T)) / math.sqrt(3.0) / np.sqrt(nb / 45.0)
    if ar:
        for j in range(1, T): e[:, j] = ar * e[:, j - 1] + math.sqrt(1 - ar * ar) * e[:, j]
    return e


def _cs_matris(x, alfa=ALFA, t_hedef=T_HEDEF):
    R, T = x.shape; t = np.arange(1, T + 1, dtype=float)
    ort, r = S.guven_matris(x, alfa, t_hedef)
    s2 = np.cumsum(x * x, 1); var = np.maximum(s2 / t - ort ** 2, 0) * t / np.maximum(t - 1, 1)
    se = np.sqrt(var / t); se[:, t < 2] = np.inf
    return ort, r, se


def benzetim_sifir(R, seed=101):   # geliştirme tohumu 17; kapı ölçümü ayrı tohumla
    rng = np.random.default_rng(seed); out = {}
    for ad, ar in (("bagimsiz", 0.0), ("ar0.3", 0.3)):
        x = _gurultu(rng, R, T_UFUK, ar)
        ort, r, se = _cs_matris(x)
        red_iki = np.any(np.abs(ort) > r, 1).mean()
        red_iyi = np.any(ort + r < 0, 1).mean()                     # yanlışlıkla "aday iyi" (tek yanlı yayın hatası)
        saf = np.any(np.abs(ort[:, 1:]) > Z_SABIT * se[:, 1:], 1).mean()   # her blok sabit %95 GA'ya bakmak
        saf14 = np.any(np.abs(ort[:, 1:T_HEDEF]) > Z_SABIT * se[:, 1:T_HEDEF], 1).mean()
        tek14 = (np.abs(ort[:, T_HEDEF - 1]) > Z_SABIT * se[:, T_HEDEF - 1]).mean()
        mc = 1.96 * math.sqrt(red_iki * (1 - red_iki) / R)
        out[ad] = {"tekrar": R, "bakis": T_UFUK, "yanlis_red_iki_yanli": round(float(red_iki), 4), "mc_ga95": [round(float(red_iki - mc), 4), round(float(red_iki + mc), 4)],
                   "yanlis_iyi_tek_yanli": round(float(red_iyi), 4), "saf_her_gun_bak_90": round(float(saf), 4), "saf_her_gun_bak_14": round(float(saf14), 4),
                   "sabit_tek_bakis_14": round(float(tek14), 4)}
    return out


def benzetim_sure(R, seed=29):
    """Sabit kapı: 14. blokta tek bakış (iki yanlı %95). Sıralı: 5. bloktan itibaren her blok, en çok 42 blok."""
    rng = np.random.default_rng(seed); x0 = _gurultu(rng, R, T_MAX)
    sig = float(np.std(x0)); mu1 = (1.959964 + 0.841621) * sig / math.sqrt(T_HEDEF)   # sabit kapıda %80 güç
    sat = []
    for k in (0.5, 1.0, 1.5, 2.0, 3.0):
        x = x0 - k * mu1                                             # negatif = aday iyi
        ort, r, se = _cs_matris(x)
        kes = (ort + r < 0) | (ort - r > 0); ilk = np.where(kes.any(1), kes.argmax(1) + 1, T_MAX)
        dogru = ((ort + r < 0) & kes).any(1)
        ilk_iyi = np.where((ort + r < 0).any(1), (ort + r < 0).argmax(1) + 1, 10 ** 6)
        ilk_kotu = np.where((ort - r > 0).any(1), (ort - r > 0).argmax(1) + 1, 10 ** 6)
        yanlis_yon = (ilk_kotu < ilk_iyi).mean()
        sabit_guc = (ort[:, T_HEDEF - 1] + Z_SABIT * se[:, T_HEDEF - 1] < 0).mean()
        g14 = ((ort + r < 0)[:, :T_HEDEF]).any(1).mean()
        sat.append({"etki_kat": k, "sabit_guc_14": round(float(sabit_guc), 3), "siralik_guc_14": round(float(g14), 3), "siralik_guc_42": round(float(dogru.mean()), 3),
                    "ort_karar_blok": round(float(ilk.mean()), 2), "medyan_karar_blok": float(np.median(ilk)), "yanlis_yon": round(float(yanlis_yon), 4),
                    "sure_orani_14e": round(float(ilk.mean()) / T_HEDEF, 3)})
    return {"tasarim_etki_sd": round(mu1 / sig, 4), "satirlar": sat}


# ─── geçmiş kapı kararları (lab özetleri) ───
_DLL = ("dll", "dLL", "d_ll", "fark"); _GA = ("ga95", "ga", "d_ll_ga")


def _ozet(d):
    for k in _DLL:
        if isinstance(d.get(k), (int, float)):
            for g in _GA:
                v = d.get(g)
                if isinstance(v, list) and len(v) == 2 and all(isinstance(a, (int, float)) for a in v) and v[1] > v[0]:
                    return float(d[k]), float(v[0]), float(v[1])
    return None


def gecmis_kararlar():
    dosyalar = sorted(set(glob.glob(os.path.join(DATA, "*lab*.json")) + glob.glob(os.path.join(DATA, "at", "*lab*.json"))
                          + [os.path.join(DATA, f) for f in ("fb_gelistir.json", "bk_gelistir.json", "keskin_piyasa.json")]))
    kay = []

    def gez(x, yol, f):
        if isinstance(x, dict):
            if isinstance(x.get("gecti"), bool):
                o = _ozet(x)
                if o is None:
                    for c in ("tum", "ll", "kiyas"):
                        if isinstance(x.get(c), dict): o = _ozet(x[c])
                        if o: break
                if o: kay.append({"dosya": os.path.relpath(f, DATA), "yol": yol, "dll": o[0], "ga": [o[1], o[2]], "gecti": x["gecti"]})
            for k, v in x.items(): gez(v, yol + "/" + str(k), f)
        elif isinstance(x, list):
            for i, v in enumerate(x): gez(v, f"{yol}[{i}]", f)

    for f in dosyalar:
        if os.path.exists(f) and not f.endswith("siralik_lab.json"):
            try: gez(json.load(open(f, encoding="utf-8")), "", f)
            except Exception: pass
    sonuc = {}
    for oran in (0.5, 1.0, 2.0):
        c = S.katsayi(oran, ALFA); uy = uy_tam = gec_kayip = 0; ust_alt = 0
        for k in kay:
            sm = (k["ga"][1] - k["ga"][0]) / (2 * Z_SABIT)
            sabit_ll = k["ga"][1] < 0; sir_ll = k["dll"] + c * sm < 0
            sir_kotu = k["dll"] - c * sm > 0
            uy += sabit_ll == sir_ll
            sir_tam = k["gecti"] and sir_ll; uy_tam += sir_tam == k["gecti"]; gec_kayip += k["gecti"] and not sir_ll
            ust_alt += sir_kotu
            if oran == 1.0: k.update({"sabit_ll_gecti": sabit_ll, "siralik_ll_gecti": sir_ll, "siralik_kotu": sir_kotu})
        n = len(kay)
        sonuc[f"t/t*={oran}"] = {"katsayi": round(c, 3), "n": n, "uyum_ll": round(uy / n, 4) if n else None, "uyum_tam": round(uy_tam / n, 4) if n else None,
                                 "gecen_kaybi": gec_kayip, "erken_ret_kotu": ust_alt}
    gec = [k for k in kay if k["gecti"]]
    return {"kararlar": sonuc, "n_gecti": len(gec), "gecenler": [{"dosya": k["dosya"], "yol": k["yol"], "dll": round(k["dll"], 5), "ga": [round(v, 5) for v in k["ga"]],
                                                                  "siralik_ll_gecti": k.get("siralik_ll_gecti")} for k in gec][:30]}


# ─── koruyucu 14 gün izleme tekrarı (kilitli öneri Brier'i) ───
def koruyucu_tekrar():
    import arsiv
    log = (json.load(open(os.path.join(DATA, "changes.json"), encoding="utf-8")) or {}).get("degisiklikler", [])
    MARJ, MIN_N = 0.01, 400; z_once = 2.2414   # %97,5 iki yanlı (α 0,025 önceye, 0,025 sıralı diziye: birleşim ≤ 0,05)
    out = []
    for i, ch in enumerate(log):
        if i == 0 or not ch.get("durum") or ch["durum"] == "başlangıç": continue
        d = ch["tarih"]; d0 = date.fromisoformat(d)
        once = [r for _, r in arsiv.kayitlar(DATA, (d0 - timedelta(days=14)).isoformat(), d)]
        sonra = list(arsiv.kayitlar(DATA, d, (d0 + timedelta(days=14)).isoformat()))
        srv = sum(1 for r in once if r.get("sp") is not None and r.get("sok") is not None) >= MIN_N and \
            sum(1 for _, r in sonra if r.get("sp") is not None and r.get("sok") is not None) >= MIN_N
        bk = (lambda r: (r["sp"] - r["sok"]) ** 2) if srv else (lambda r: (r["rp"] - r["ok"]) ** 2)
        ok = (lambda r: r.get("sp") is not None and r.get("sok") is not None) if srv else (lambda r: r.get("rp") is not None and r.get("ok") is not None)
        b0 = np.array([bk(r) for r in once if ok(r)])
        if len(b0) < 50: continue
        gun = defaultdict(list)
        for g, r in sonra:
            if ok(r): gun[g].append(bk(r))
        gunler = sorted(gun); x = np.array([np.mean(gun[g]) - b0.mean() for g in gunler])
        se0 = b0.std(ddof=1) / math.sqrt(len(b0))
        t, ort, lo, hi = S.guven_dizisi(x, ALFA / 2, T_HEDEF)
        lo = lo - z_once * se0; hi = hi + z_once * se0
        kum = np.cumsum([len(gun[g]) for g in gunler]) if gunler else np.array([])
        kar, kgun = "devam", None
        for j in range(len(t)):
            if lo[j] > 0: kar, kgun = "kotu (erken geri al)", j + 1; break
            if hi[j] < MARJ: kar, kgun = "esdeger (erken kalıcı)", j + 1; break
        g400 = int(np.argmax(kum >= MIN_N) + 1) if len(kum) and kum[-1] >= MIN_N else None
        uyum = (kar.startswith("kotu") and ch["durum"] == "GERİ ALINDI") or (not kar.startswith("kotu") and ch["durum"] != "GERİ ALINDI")
        out.append({"tarih": d, "fark": list((ch.get("fark") or {}).keys()), "koruyucu": ch["durum"], "olcut": "sunulan" if srv else "ham", "n_once": int(len(b0)),
                    "gun": len(gunler), "n_sonra": int(kum[-1]) if len(kum) else 0, "siralik": kar, "siralik_gun": kgun, "koruyucu_400_gun": g400,
                    "son_ort": round(float(ort[-1]), 4) if len(t) else None, "son_ust": round(float(hi[-1]), 4) if len(t) and np.isfinite(hi[-1]) else None, "uyum": uyum})
    n = len(out)
    return {"n": n, "uyum": round(sum(o["uyum"] for o in out) / n, 4) if n else None, "degisiklikler": out,
            "not": "birim = gün; önce dönemi sabit (14 gün), α 0,025 + 0,025 birleşim; eşdeğerlik marjı 0,01 Brier (koruyucu eşiğiyle aynı)."}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tekrar", type=int, default=10000); a = ap.parse_args()
    t0 = time.time()
    sifir = benzetim_sifir(a.tekrar); print("sıfır:", json.dumps(sifir, ensure_ascii=False), flush=True)
    sure = benzetim_sure(a.tekrar); print("süre:", json.dumps(sure, ensure_ascii=False), flush=True)
    gec = gecmis_kararlar(); print("geçmiş:", json.dumps(gec["kararlar"], ensure_ascii=False), gec["n_gecti"], flush=True)
    try: kor = koruyucu_tekrar()
    except Exception as e: kor = {"hata": str(e)[:200]}
    print("koruyucu:", json.dumps({k: v for k, v in kor.items() if k != "degisiklikler"}, ensure_ascii=False), flush=True)
    k1 = sifir["bagimsiz"]["yanlis_red_iki_yanli"] <= ALFA
    uy = gec["kararlar"]["t/t*=1.0"]["uyum_ll"] or 0
    k2 = uy >= 0.90 and (kor.get("uyum") is None or kor["uyum"] >= 0.90)
    R = {"madde": "YH-17", "tarih": date.today().isoformat(), "yontem": "asimptotik güven dizisi (Robbins normal karışımı, blok ortalaması, σ̂ eklentili), "
         f"α={ALFA} iki yanlı, ρ t*={T_HEDEF} bloka ayarlı, ısınma {S.T_MIN} blok", "sifir_benzetim": sifir, "karar_suresi": sure, "gecmis_kapi": gec,
         "koruyucu_tekrar": kor, "kapi": {"yanlis_red_le_0.05": k1, "uyum_ge_0.90": k2, "gecti": bool(k1 and k2)}, "uretime_etki": "yok (gölge; eski kapı karar verir)",
         "sure_sn": round(time.time() - t0, 1)}
    json.dump(R, open(os.path.join(DATA, "siralik_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("KAPI:", R["kapi"])


if __name__ == "__main__":
    main()
