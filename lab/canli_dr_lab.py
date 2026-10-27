"""v117 · Canlı kalan süre modeli laboratuvarı (salt okunur; ağ kullanmaz).

1) Parametre seçimi (e1, e2, ξ): yalnız ZAMANCA İLK %50 maçta ham Brier ile seçilir (sonraki yarı görülmez).
2) Kapı: scripts/collector.py → live_model_gate (toplayıcının her çalışmada kullandığı fonksiyonun aynısı):
   eski doğrusal model + kendi Platt'ı ↔ v117 + kendi Platt'ı, zaman sıralı genişleyen pencere, maç-blok bootstrap %95 GA.
3) Seçim yanlılığı denetimi: kayıtlı her anda MS 1/X/2'nin ÜÇÜ birden (maç sonu skoru arşivden) ham Brier/LL.
Kullanım: python3 lab/canli_dr_lab.py [--json çıktı.json]
"""
import json, glob, os, sys, math, itertools
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "scripts"))
import collector as CO, canli_istat as CI


def load():
    st = []
    for f in sorted(glob.glob(os.path.join(CO.LIVE, "*.json")))[-30:]:
        d = os.path.basename(f)[:10]
        st += [dict(r, _d=d) for r in json.load(open(f, encoding="utf-8")).values() if r.get("ok") is not None]
    return st


def main():
    h1 = json.load(open(os.path.join(CO.DATA, "model.json"), encoding="utf-8"))["params"].get("h1", .4428)
    stats = load(); lam = CO._live_lam_map()
    rs = [dict(r) for r in stats if r.get("lam") or lam.get(str(r["id"]))]; CO._infer_pd(rs)
    f6 = CO._match_folds(rs, 6); y = np.array([float(r["ok"]) for r in rs]); fo = np.array([f6[r["id"]] for r in rs])
    print(f"puanlı canlı seçim {len(stats)} · lam eşleşen {len(rs)} · maç {len({r['id'] for r in rs})} · h1 {h1}")
    print(f"devre çıkarımı (45–50 dk): {sum(1 for r in rs if 45 <= r['t'] < 50 and r['_pd'] == 1)} ilk yarı uzatması, "
          f"{sum(1 for r in rs if 45 <= r['t'] < 50 and r['_pd'] == 2)} ikinci yarı, {sum(1 for r in rs if 45 <= r['t'] < 50 and r['_pd'] is None)} bilinmiyor")
    L = lambda r: r.get("lam") or lam[str(r["id"])]

    def post(p, folds):        # zaman sıralı Platt sonrası Brier (k. dilim yalnız önceki dilimlerle öğrenilir)
        b = []
        for k in folds:
            tr = fo < k; te = fo == k; ab = CO._platt_fit(p[tr], y[tr]); b.append((np.minimum(CO._platt(p[te], ab), .99) - y[te]) ** 2)
        return float(np.mean(np.concatenate(b)))
    p0 = np.array([CO.live_p_of(r, L(r), h1, None) for r in rs])
    print("\n1) Parametre seçimi: zamanca ilk yarı (dilim 0–2; Platt dilim 1–2'de sınanır). Dilim 3–5 seçimde HİÇ kullanılmaz.")
    print(f"   eski doğrusal              seçim Brier {post(p0, [1, 2]):.5f}   (bilgi: 3–5 {post(p0, [3, 4, 5]):.5f})")
    grid = []
    for e1, e2, xi in itertools.product((1.0, 2.0, 3.0), (3.0, 5.0, 7.0), (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)):
        Z = dict(CI.ZDEF, e1=e1, e2=e2, xi=xi); p = np.array([CO.live_p_of(r, L(r), h1, Z) for r in rs])
        grid.append((post(p, [1, 2]), post(p, [3, 4, 5]), e1, e2, xi))
    grid.sort()
    for g in grid[:6]: print(f"   e1={g[2]:g} e2={g[3]:g} ξ={g[4]:.1f}          seçim Brier {g[0]:.5f}   (bilgi: 3–5 {g[1]:.5f})")
    print(f"   → seçilen: e1={grid[0][2]:g} e2={grid[0][3]:g} ξ={grid[0][4]:.1f} · kodda ZDEF: e1={CI.ZDEF['e1']:g} e2={CI.ZDEF['e2']:g} ξ={CI.ZDEF['xi']}")

    for tf, ad in ((3, "BEKLETİLEN dilimler 3–5 (seçimde görülmedi)"), (1, "tüm dilimler 1–5 (toplayıcının çevrimiçi kapısı)")):
        G = CO.live_model_gate([dict(r) for r in stats], h1, test_from=tf); G = G[0] if isinstance(G, tuple) else G
        report(G, ad)
    if "--json" in sys.argv: json.dump(G, open(sys.argv[sys.argv.index("--json") + 1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sel_bias(rs, L, h1)


def report(G, ad):
    print(f"\n2) Kapı · {ad}: eski + uygulama kalibrasyonu ↔ v117 + uygulama kalibrasyonu (dilim başına yalnız geçmişle seçilir), maç-blok bootstrap")
    T = G.get("tablo", {})
    print(f"   sınama: {G.get('sinama_n')} seçim / {G.get('sinama_mac')} maç, {G.get('dilim')} dilim, v117 kazanılan dilim {G.get('kazanilan_dilim')}; gerçek isabet {G.get('gercek')}")
    print(f"   {'':26s} {'Brier':>7s} {'log-kayıp':>9s} {'ort p':>6s}")
    NM = {"ham0": "eski model, ham", "q0": "eski + kalibrasyon", "ham1": "v117, ham", "q1": "v117 + kalibrasyon"}
    for k in ("ham0", "q0", "ham1", "q1"):
        if k in T: print(f"   {NM[k]:26s} {T[k]['brier']:7.4f} {T[k]['ll']:9.4f} {T[k]['ort_p']:6.3f}")
    print(f"   ΔBrier (v117+kal − eski+kal)    {G.get('d_brier'):+.5f}  %95 GA {G.get('d_brier_ga95')}")
    print(f"   ΔLL                              {G.get('d_ll'):+.5f}  %95 GA {G.get('d_ll_ga95')}")
    print(f"   bilgi (karar dışı): v117 ham − eski+kal ΔBrier {G['bilgi_v117_ham_vs_eski_kal']['d_brier']:+.5f} %95 GA {G['bilgi_v117_ham_vs_eski_kal']['ga95']}")
    print(f"   dilim başına kalibrasyon [eski, v117]: {G.get('kalibrasyon_secimi')}")
    print(f"   KAPI: {'GEÇTİ' if G.get('kabul') else 'KALDI'}")
    print("\n   Güven bandı sapması (gerçek − ort tahmin), sınama kümesi:")
    print(f"   {'bant':10s} " + "  ".join(f"{NM[k]:>22s}" for k in ("ham0", "q0", "ham1", "q1")))
    bands = sorted({(b[0], b[1]) for k in T for b in T[k]["bant"]})
    for lo, hi in bands:
        cells = []
        for k in ("ham0", "q0", "ham1", "q1"):
            b = next((b for b in T[k]["bant"] if b[0] == lo and b[1] == hi), None)
            cells.append(f"{'—':>22s}" if not b else f"n{b[2]:4d} {b[3]:.3f}→{b[4]:.3f} {b[5]:+.3f}".rjust(22))
        print(f"   {lo:.1f}–{min(hi,1):.1f}    " + "  ".join(cells))



def sel_bias(rs, L, h1):
    print("\n3) Seçim yanlılığı denetimi: her kayıtta MS 1/X/2'nin üçü (maç sonu skoru arşivden), ham olasılık")
    fin = {}
    for f in glob.glob(os.path.join(CO.ARC, "*.json")):
        for k, r in json.load(open(f, encoding="utf-8")).items():
            if isinstance(r, dict) and r.get("hs") is not None: fin[k] = (r["hs"], r["as"])
    rows = [r for r in rs if str(r["id"]) in fin]
    for nm, Z in (("eski doğrusal", None), ("v117", CI.ZDEF)):
        B = []; LL = []; O = []
        for r in rows:
            Lm = L(r); P = CO.live_pred(Lm[0], Lm[1], r["hs"], r["as"], r["t"], r.get("rc") or [0, 0], h1, r["_pd"], Z); fh, fa = fin[str(r["id"])]
            o = [float(fh > fa), float(fh == fa), float(fh < fa)]; q = [P["H"], P["D"], P["A"]]
            B.append(sum((a - b) ** 2 for a, b in zip(q, o))); LL.append(-math.log(max(1e-9, q[o.index(1.0)])))
        print(f"   {nm:14s} n {len(rows)}  çok sınıflı Brier {np.mean(B):.4f}  log-kayıp {np.mean(LL):.4f}")


if __name__ == "__main__":
    main()
