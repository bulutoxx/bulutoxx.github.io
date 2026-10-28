"""OXXai · YH-10 · Canlı piyasa olasılığı + CG harmanı (futbol) — zaman sıralı sınama + kapı + gece yeniden sınama + 14 gün izleme.

Veri (yalnız deponun kendi kayıtları, türetilmiş sayılar):
  • data/archive/live/*.json   canlı anlık görüntüler; v144'ten beri "mk" = marjı ayrılmış canlı piyasa olasılığı
                               (ms [1,X,2] · ou [ana çizgi, Üst] · ng [sıradaki gol ev, olmaz, dep.]; 3 hane, ham oran yok)
  • data/archive/GGGG-AA-GG.json   maç sonu skoru (lab/canli_guc_lab.load ile aynı)
Modeller (aynı anlık görüntüde):
  CG      = üretimdeki canlı güç modeli (scripts/canli_guc.py); sınama günü D için parametreler yalnız D'den önce sonucu kesin maçlarla
            öğrenilir (canli_guc_lab.fit — uygulamadaki gibi).
  piyasa  = yalnız canlı piyasa olasılığı.
  harman  = p_i ∝ exp(a·ln p_CG,i + b·ln p_piyasa,i); (a, b) pazar ve dakika dilimine göre (0–30, 30–60, 60–75, 75+) aynı zaman sıralı eğitim
            kümesinde öğrenilir (önsel: CG aynen, a=1, b=0; Gauss std 0,5). Dilimde < 50 eğitim satırı → CG aynen.
Hedefler: MS 1/X/2 (3 sınıf), ana çizgi Alt/Üst (maç sonu toplam > çizgi), "başka gol olmaz" (sıradaki gol pazarının ikili özeti).
Birleşik kayıp = anlık görüntüde piyasası olan pazarların log-kayıp toplamı (piyasası olmayan pazarda harman = CG, fark 0).
KAPI (YH-10 · standart kapı): n ≥ 600 anlık görüntü / ≥ 120 maç; birleşik ΔLL (harman − CG) lig×gün blok bootstrap %95 GA üst < 0;
  sınamanın iki zaman yarısında ΔLL < 0; birleşik ΔBrier ≤ 0; her pazarda ΔLL ≤ 0; tek yanlı p ≤ α_t (alfa yatırımı, lab/oxx_ogren).
Bayrak: data/canli_piyasa.json  kullan=true → uygulama (canli-piyasa-v144) ve sunucu (scripts/collector.py) harmanı kullanır.
  Gece (auto-lab) yeniden sınanır: açıkken kapı tutmazsa → kullan=false (geri alma, durum "geri_alindi"); 14 gün izleme sonunda "kalici".
  Kapalıyken "golge_W" (tüm veriyle öğrenilmiş ağırlık) canlı kayda gölge harman olasılığı ("ph") yazmak için kullanılır.
Kullanım: python3 lab/canli_piyasa_lab.py [--uygula]
"""
import json, math, os, sys, collections
from datetime import datetime, timezone, date, timedelta
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import canli_guc as CG
import canli_guc_lab as CGL
DATA = os.path.join(ROOT, "data"); FLAG = os.path.join(DATA, "canli_piyasa.json")
MIN_N, MIN_M, MIN_DILIM, PRIOR_SD, IZLEME_GUN = 600, 120, 50, 0.5, 14
PAZAR = ("ms", "ou", "ng")


# ---------------------------------------------------------------- satırlar
def satir(r, P):
    """Anlık görüntü → pazar başına (p_CG, p_piyasa, y_indeks) listeleri."""
    mk = r.get("mk") or {}
    if not mk: return None
    Pr = CG.probs(r["lam"][0], r["lam"][1], r["hs"], r["as"], r["t"], r["rc"], r["pd_"], P)
    fh, fa, cur = r["fh"], r["fa"], r["hs"] + r["as"]; out = {}
    if mk.get("ms"): out["ms"] = ([Pr["H"], Pr["D"], Pr["A"]], list(mk["ms"]), 0 if fh > fa else 1 if fh == fa else 2)
    if mk.get("ou"):
        L = float(mk["ou"][0]); po = CG.over(Pr, L, cur)
        if 0 < po < 1: out["ou"] = ([po, 1 - po], [mk["ou"][1], 1 - mk["ou"][1]], 0 if fh + fa > L else 1)
    if mk.get("ng"):
        # sıradaki gol üçlüsü harmanlanır, sonuç "başka gol olmaz" ikilisinde ölçülür (ev/dep. ayrımı her zaman belirlenemez)
        out["ng"] = ([Pr["nh"], Pr["none"], Pr["na"]], list(mk["ng"]), None if fh + fa == cur else 0)
    return out or None


def kayip(pc, pm, y, a, b, mkt):
    p = CG._hk(pc, pm, a, b) if (a, b) != (1.0, 0.0) else list(pc)
    if mkt == "ng":
        q = min(max(p[1], 1e-6), 1 - 1e-6); yy = 1.0 if y is None else 0.0
        return -(yy * math.log(q) + (1 - yy) * math.log(1 - q)), (q - yy) ** 2
    q = min(max(p[y], 1e-6), 1.0); br = sum((p[i] - (1.0 if i == y else 0.0)) ** 2 for i in range(len(p)))
    return -math.log(q), br


def NOTR(): return {m: {str(d): (1.0, 0.0) for d in CG.DILIMLER} for m in PAZAR}


def ogren(S_by_dilim):
    """Pazar × dilim başına (a, b): log-kayıp + Gauss önsel (CG'ye doğru). Dilimde < MIN_DILIM satır → CG aynen (1, 0)."""
    W = NOTR()
    for m in PAZAR:
        for d in CG.DILIMLER:
            S = [s[m] for s in S_by_dilim.get(str(d), []) if m in s]
            if len(S) < MIN_DILIM: continue
            f = lambda v: sum(kayip(pc, pm, y, min(2, max(0, v[0])), min(2, max(0, v[1])), m)[0] for pc, pm, y in S) + 0.5 * ((v[0] - 1) ** 2 + v[1] ** 2) / PRIOR_SD ** 2
            v, _ = CGL.nelder_mead(f, np.array([1.0, 0.0]), step=.3, it=300)
            v, _ = CGL.nelder_mead(f, v, step=.05, it=200)
            W[m][str(d)] = (round(float(min(2, max(0, v[0]))), 4), round(float(min(2, max(0, v[1]))), 4))
    return W


def wj(W): return {m: {d: list(v) for d, v in W[m].items()} for m in W}


def blok_boot(d, blk, B=2000, seed=11):
    uid = sorted(set(blk)); ix = collections.defaultdict(list)
    for i, u in enumerate(blk): ix[u].append(i)
    ix = {u: np.array(v) for u, v in ix.items()}; rng = np.random.default_rng(seed); out = []
    for _ in range(B):
        sm = np.concatenate([ix[u] for u in rng.choice(uid, len(uid))]); out.append(d[sm].mean())
    out = np.array(out)
    return [round(float(np.percentile(out, 2.5)), 5), round(float(np.percentile(out, 97.5)), 5)], round(float(np.mean(out >= 0)), 4)


# ---------------------------------------------------------------- sınama
def sinama(fin, snaps, h1, verbose=True):
    mk_snaps = [r for r in snaps if r.get("mk")]
    days = sorted({r["d"] for r in mk_snaps}); R = []; gunler = []
    for D in days:
        t0 = CGL.day_start(D)
        tr_ids = {k for k, M in fin.items() if M["ts"] + 2.5 * 3600 < t0}
        tr_live = {r["id"] for r in snaps if r["id"] in tr_ids}
        te = [r for r in mk_snaps if r["d"] == D]
        tr = [r for r in mk_snaps if r["id"] in tr_ids]
        if len(tr_live) < 30 or not te or not tr: continue
        P, _ = CGL.fit(CGL.rows_of(snaps, fin, tr_ids, extra=True), dict(CG.DEF, h1=h1))
        Sd = collections.defaultdict(list)
        for r in tr:
            s = satir(r, P)
            if s: Sd[CG.dilim(r["t"])].append(s)
        W = ogren(Sd)
        for r in te:
            s = satir(r, P)
            if not s: continue
            dl = CG.dilim(r["t"])
            row = {"t": r["t"], "ts": r.get("ts") or r["kts"], "id": r["id"], "blk": f"{r.get('c')}|{D}", "d": D}
            for nm, ab in (("cg", lambda m: (1.0, 0.0)), ("piyasa", lambda m: (0.0, 1.0)), ("harman", lambda m: W[m][dl])):
                row[nm] = {mkt: kayip(pc, pm, y, *ab(mkt), mkt) for mkt, (pc, pm, y) in s.items()}
            R.append(row)
        gunler.append({"gun": D, "egitim_mk": len(tr), "sinama": len(te), "W": wj(W)})
        if verbose: print(D, "eğitim (piyasalı)", len(tr), "sınama", len(te), W, flush=True)
    return R, gunler


def ozet(R):
    def ms(rows, nm, mkt=None):
        L = [sum(v[0] for k, v in r[nm].items() if mkt in (None, k)) for r in rows if mkt is None or mkt in r[nm]]
        B = [sum(v[1] for k, v in r[nm].items() if mkt in (None, k)) for r in rows if mkt is None or mkt in r[nm]]
        return {"n": len(L), "ll": round(float(np.mean(L)), 5) if L else None, "brier": round(float(np.mean(B)), 5) if B else None}
    T = {nm: {"birlesik": ms(R, nm), **{m: ms(R, nm, m) for m in PAZAR}} for nm in ("cg", "piyasa", "harman")}
    dil = {}
    for d in CG.DILIMLER:
        rr = [r for r in R if CG.dilim(r["t"]) == str(d)]
        if rr: dil[str(d)] = {nm: ms(rr, nm) for nm in ("cg", "piyasa", "harman")}
    return T, dil


def fark(R):
    d = np.array([sum(v[0] for v in r["harman"].values()) - sum(v[0] for v in r["cg"].values()) for r in R])
    db = np.array([sum(v[1] for v in r["harman"].values()) - sum(v[1] for v in r["cg"].values()) for r in R])
    blk = [r["blk"] for r in R]; ci, p_tek = blok_boot(d, blk)
    o = np.argsort([r["ts"] for r in R], kind="stable"); h = len(o) // 2
    per = {m: round(float(np.mean([r["harman"][m][0] - r["cg"][m][0] for r in R if m in r["cg"]])), 5) if any(m in r["cg"] for r in R) else None for m in PAZAR}
    return {"n": len(R), "mac": len({r["id"] for r in R}), "d_ll": round(float(d.mean()), 5), "ga95": ci, "p_tek": p_tek,
            "yari1": round(float(d[o[:h]].mean()), 5) if h else None, "yari2": round(float(d[o[h:]].mean()), 5) if h else None,
            "d_brier": round(float(db.mean()), 5), "d_ll_pazar": per}


# ---------------------------------------------------------------- karar + bayrak
def karar(A, F, W_all, gs, O=None):
    """A: önceki bayrak (yerinde güncellenir; kullan dahil). F: fark() ya da None. Dönüş: (kullan, not)."""
    k, notu = _karar(A, F, W_all, gs, O); A["kullan"] = bool(k)
    return k, notu


def _karar(A, F, W_all, gs, O=None):
    gun = date.fromisoformat(gs); onceki = bool(A.get("kullan"))
    yeter = bool(F and F["n"] >= MIN_N and F["mac"] >= MIN_M)
    yon = bool(yeter and F["d_ll"] < 0 and (F["yari1"] or 0) < 0 and (F["yari2"] or 0) < 0 and F["d_brier"] <= 0
               and all(v is None or v <= 0 for v in F["d_ll_pazar"].values()))
    if onceki:                                            # yayında: gece yeniden sınama — kapı tutmazsa geri al
        if yeter and yon and F["ga95"][1] < 0:
            if A.get("durum") == "deneme" and A.get("bitis") and gs >= A["bitis"]: A["durum"] = "kalici"
            A["W"] = wj(W_all)
            return True, "yeniden sınama geçti"
        A["onceki"] = {"W": A.get("W"), "durum": A.get("durum"), "baslangic": A.get("baslangic"), "geri_alma": gs}
        A["durum"] = "geri_alindi"; A.pop("W", None)
        return False, "yeniden sınamada kapı tutmadı → geri alındı"
    A.pop("W", None)
    if not yeter:
        A["durum"] = "golge"; return False, f"veri birikiyor: {F['n'] if F else 0}/{MIN_N} piyasalı anlık görüntü, {F['mac'] if F else 0}/{MIN_M} maç"
    if not yon:
        A["durum"] = "golge"; return False, "ön eleme: sınamada yön iyileşme göstermiyor (alfa harcanmadı)"
    if A.get("son_test_n") and F["n"] < 1.5 * A["son_test_n"]:
        A["durum"] = "golge"; return False, f"yeniden sınama için veri büyümesi bekleniyor ({F['n']}/{int(1.5 * A['son_test_n'])})"
    A["son_test_n"] = F["n"]; alan = f"canli-piyasa-{gun.year}"
    if O is None:
        try: import oxx_ogren as O  # noqa
        except Exception: O = None
    alfa = O.yatirim_alfa(A, alan, {"anahtar": "yh10", "sinyal": {"kaynak": "ön kayıtlı yol haritası adayı"}}) if O else 0.01
    istat = bool(F["p_tek"] <= alfa); gecti = bool(istat and F["ga95"][1] < 0)
    if O: O.yatirim_guncelle(A, alan, alfa, istat)
    A["kapi_son"] = {"tarih": gs, "alfa": round(alfa, 5), "p_tek": F["p_tek"], "gecti": gecti}
    if gecti:
        A.update(durum="deneme", baslangic=gs, bitis=(gun + timedelta(days=IZLEME_GUN)).isoformat(), W=wj(W_all))
        return True, "kapı geçti → yayında (14 gün izleme)"
    A["durum"] = "golge"; return False, "kapı geçilmedi"


def main(argv):
    try: h1 = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8"))["params"].get("h1", .4428)
    except Exception: h1 = .4428
    try: A = json.load(open(FLAG, encoding="utf-8"))
    except Exception: A = {}
    fin, snaps = CGL.load()
    n_mk = sum(1 for r in snaps if r.get("mk")); n_mk_all = 0
    import glob
    for f in glob.glob(os.path.join(DATA, "archive", "live", "*.json")):
        try: n_mk_all += sum(1 for r in json.load(open(f, encoding="utf-8")).values() if r.get("mk"))
        except Exception: pass
    print(f"sonuçlu canlı anlık görüntü {len(snaps)} · piyasalı (sonuçlu) {n_mk} · piyasalı (tümü) {n_mk_all}", flush=True)
    R, gunler = sinama(fin, snaps, h1) if n_mk else ([], [])
    F = fark(R) if len(R) >= 20 else None
    T, dil = ozet(R) if R else ({}, {})
    # tüm veriyle ağırlıklar (yayında W, gölgede golge_W)
    W_all = NOTR()
    if n_mk:
        Pall = CG.ayar(DATA) or dict(CG.DEF, h1=h1); Sd = collections.defaultdict(list)
        for r in snaps:
            s = satir(r, Pall)
            if s: Sd[CG.dilim(r["t"])].append(s)
        W_all = ogren(Sd)
    gs = datetime.now(timezone.utc).date().isoformat()
    kullan, notu = karar(A, F, W_all, gs)
    learned = W_all != NOTR()
    A.update({"v": 1, "kullan": bool(kullan), "zaman": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
              "model": "YH-10: p ∝ exp(a·ln p_CG + b·ln p_piyasa) — MS, ana çizgi Alt/Üst, sıradaki gol; (a,b) dakika dilimine göre",
              "golge_W": wj(W_all) if learned else wj(CG.HARMAN_GOLGE),
              "golge_kaynak": "tüm piyasalı kayıtlarla öğrenildi" if learned else "önsel (veri yok)",
              "veri": {"piyasali_sonuclu": n_mk, "piyasali_tum": n_mk_all, "sonuclu_anlik": len(snaps)},
              "sinama": {"yontem": "genişleyen pencere, gün bazlı; eğitim = sınama günü başlamadan sonucu kesin maçlar (CG parametreleri ve harman ağırlıkları)",
                         "fark": F, "tablo": T, "dilim": dil, "gunler": gunler},
              "kapi": {"min_n": MIN_N, "min_mac": MIN_M, "kural": "birleşik ΔLL (harman − CG) lig×gün blok bootstrap %95 GA üst < 0; iki zaman yarısında ΔLL < 0; ΔBrier ≤ 0; her pazarda ΔLL ≤ 0; tek yanlı p ≤ α_t",
                       "not": notu}})
    print(json.dumps({k: v for k, v in A.items() if k != "sinama"}, ensure_ascii=False, indent=1))
    print(json.dumps({"fark": F, "tablo": T, "dilim": dil}, ensure_ascii=False, indent=1))
    if "--uygula" in argv:
        json.dump(A, open(FLAG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("yazıldı: data/canli_piyasa.json")
    return A


if __name__ == "__main__":
    main(sys.argv[1:])
