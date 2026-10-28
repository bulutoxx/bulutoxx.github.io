#!/usr/bin/env python3
"""🎯 YH-03 · Şut tabanlı güç robotu (GAP / sözde-xG) laboratuvarı — oranlı ana ligler. Yalnız ölçüm; üretime yazmaz.

Robot: Wheatcroft (2020, 2021) GAP puanı. Her takımın ev ve deplasman için ayrı isabetli şut (HST/AST) üretme ve yeme puanı;
maç sonrası hata λ·φ (aynı saha) ve λ·(1−φ) (öteki saha) ile dağıtılır. Beklenen isabetli şut: Ŝ_ev = (a_ev^H + d_dep^A)/2,
Ŝ_dep = (a_dep^A + d_ev^H)/2. Girdi yığınlayıcıya: ln((Ŝ_ev+1)/(Ŝ_dep+1)) ve büyüklüğü (1X2), ln(Ŝ_ev+Ŝ_dep) (2,5 A/Ü).

Protokol (önceden kayıtlı, fb_guc_lab ile aynı):
  • Durumlar yalnız maçtan önceki maçlarla ilerler; uygunluk: ligde ≥45 eğitim maçı, iki takımın ≥3 önceki maçı, iki takımın ≥5 önceki şut kaydı.
  • Seçim dilimi S (< SINIR): GAP λ/φ ızgarası burada seçilir. Sınama dilimi T (≥ SINIR): yalnız rapor.
  • Yığınlayıcılar aylık genişleyen pencereyle yalnız GEÇMİŞ aylarla öğrenilir.
  • (A) Model yolu: referans = üretim topluluğu girdileri (Poisson + Elo + pi); aday = aynı + GAP. 1X2 ve 2,5 A/Ü.
  • (B) Piyasa üstü: referans = piyasa yığını (power marj logitleri); aday = piyasa + GAP (+ topluluk). 1X2 ve 2,5 A/Ü.
  • Kapı (SK): T'de ΔLL %95 GA üst < 0, iki yarıda ΔLL < 0, ΔBrier ≤ 0, isabet düşmüyor, tek yanlı p ≤ α_t (fb_model alfa yatırımı, salt okunur).
Veri: football-data.co.uk ana lig CSV'leri (motorun zaten kullandığı ücretsiz kaynak; atıf). Ham veri commit edilmez; önbellek yalnız --onbellek ile yerel.
Çıktı: data/sut_guc_lab.json (yalnız özet karne).

  python3 lab/sut_guc_lab.py [--sezon 6] [--sinir 2024-07-01] [--onbellek /tmp/fd.json]
"""
import argparse, collections, csv, io, json, os, sys, time
from datetime import date

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import update as U  # noqa: E402
import guc as G  # noqa: E402
import fb_guc_lab as FL  # noqa: E402

T0 = time.time()
GAP_IZ = [(lm, ph) for lm in (0.05, 0.1, 0.2) for ph in (0.4, 0.6, 0.8)]


def log(*a): print(f"[{time.time() - T0:6.0f} sn]", *a, flush=True)


def fnum(x):
    try: v = float(x); return v if v > 1.0 else None
    except (TypeError, ValueError): return None


def indir(sezon_say, onbellek=None):
    if onbellek and os.path.exists(onbellek):
        return json.load(open(onbellek))
    _, y = U.season_code(date.today())
    out = {}
    for lg, (kind, code, _n) in U.LEAGUES.items():
        if kind != "main": continue
        ms = []
        for s in range(y - sezon_say, y + 1):
            try: txt = U.fetch(f"https://www.football-data.co.uk/mmz4281/{s % 100:02d}{(s + 1) % 100:02d}/{code}.csv")
            except Exception as e: log(lg, s, e.__class__.__name__); continue
            for r in csv.DictReader(io.StringIO(txt)):
                d = U.parse_date(r.get("Date", "") or ""); h = (r.get("HomeTeam") or "").strip(); a = (r.get("AwayTeam") or "").strip()
                if not d or not h or not a or (r.get("FTHG") or "") == "": continue
                try: m = {"d": d, "h": h, "a": a, "ft": [int(float(r["FTHG"])), int(float(r["FTAG"]))], "season": s}
                except (ValueError, KeyError): continue
                try:
                    if (r.get("HST") or "") != "" and (r.get("AST") or "") != "": m["st"] = [int(float(r["HST"])), int(float(r["AST"]))]
                except ValueError: pass
                o = [fnum(r.get(k)) for k in ("AvgH", "AvgD", "AvgA")]
                if not all(o): o = [fnum(r.get(k)) for k in ("B365H", "B365D", "B365A")]
                if all(o): m["odds"] = [round(x, 2) for x in o]
                ou = [fnum(r.get("Avg>2.5")), fnum(r.get("Avg<2.5"))]
                if all(ou): m["ou"] = [round(x, 2) for x in ou]
                ms.append(m)
        out[lg] = sorted(ms, key=lambda m: (m["d"], m["h"]))
        log(lg, len(out[lg]), "maç", sum(1 for m in out[lg] if m.get("st")), "şutlu")
    if onbellek: json.dump(out, open(onbellek, "w"))
    return out


def gap_seq(ms, lam, phi, s0=4.0):
    """Maç öncesi (Ŝ_ev, Ŝ_dep, ev şut kayıt sayısı, dep şut kayıt sayısı). Sezon başında ortalamaya yarı çekilir."""
    aH = collections.defaultdict(lambda: s0); aA = collections.defaultdict(lambda: s0)
    dH = collections.defaultdict(lambda: s0); dA = collections.defaultdict(lambda: s0)
    n = collections.Counter(); out = []; cur = None
    for m in ms:
        if cur is not None and m.get("season") != cur:
            for R in (aH, aA, dH, dA):
                if R: mu = float(np.mean(list(R.values())))
                for t in list(R): R[t] = mu + 0.5 * (R[t] - mu)
        cur = m.get("season"); h, a = m["h"], m["a"]
        sh = (aH[h] + dA[a]) / 2; sa = (aA[a] + dH[h]) / 2
        out.append((sh, sa, n[h], n[a]))
        if m.get("st"):
            eh = m["st"][0] - sh; ea = m["st"][1] - sa
            aH[h] = max(aH[h] + lam * phi * eh, 0); aA[h] = max(aA[h] + lam * (1 - phi) * eh, 0)
            dH[h] = max(dH[h] + lam * phi * ea, 0); dA[h] = max(dA[h] + lam * (1 - phi) * ea, 0)
            aA[a] = max(aA[a] + lam * phi * ea, 0); aH[a] = max(aH[a] + lam * (1 - phi) * ea, 0)
            dA[a] = max(dA[a] + lam * phi * eh, 0); dH[a] = max(dH[a] + lam * (1 - phi) * eh, 0)
            n[h] += 1; n[a] += 1
    return np.array(out, float)


def gap_x(g):
    r = np.log((g[:, 0] + 1) / (g[:, 1] + 1)); return np.stack([r, np.abs(r)], 1), np.log(np.maximum(g[:, 0] + g[:, 1], .5))[:, None]


def logit2(p): p = np.clip(p, 1e-4, 1 - 1e-4); return np.log(p) - np.log(1 - p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sezon", type=int, default=6); ap.add_argument("--sinir", default="2024-07-01")
    ap.add_argument("--onbellek", default=None); ap.add_argument("--min-n", type=int, default=3000); ap.add_argument("--cikti", default=os.path.join(DATA, "sut_guc_lab.json"))
    ar = ap.parse_args()
    M = json.load(open(os.path.join(DATA, "model.json"), encoding="utf-8")); P = dict(M["params"]); rho = P.get("rho", -0.06)
    Lg = indir(ar.sezon, ar.onbellek)
    R = collections.defaultdict(list)
    for lg, ms in Lg.items():
        if len(ms) < 300: continue
        U.market_xg([m for m in ms if m.get("odds")])
        hafta, uy = FL.uygun_ve_hafta(ms, 540)
        L = FL.poisson_wf(ms, hafta, uy, P, 540)
        E = np.array(G.elo_seq(ms, {"K": 20, "eta": 1.0})[0]); PI = np.array(G.pi_seq(ms, {"lam": 0.06, "gam": 0.7})[0])
        gaps = {k: gap_seq(ms, *k) for k in GAP_IZ}
        g0 = gaps[GAP_IZ[0]]
        ok = uy & (g0[:, 2] >= 5) & (g0[:, 3] >= 5) & np.array([bool(m.get("odds") and m.get("ou")) for m in ms])
        tot = np.array([sum(m["ft"]) for m in ms], float); cs = np.concatenate([[0], np.cumsum(tot)])
        og = np.array([(cs[i] - cs[max(0, i - 300)]) / max(1, i - max(0, i - 300)) if i else 2.6 for i in range(len(ms))])
        ii = np.where(ok)[0]
        for i in ii:
            m = ms[i]; R["lg"].append(lg); R["d"].append(m["d"]); R["y"].append(FL.sonuc(m["ft"])); R["yo"].append(float(sum(m["ft"]) > 2))
            R["pm"].append(U.power_devig(m["odds"])); R["pmo"].append(U.power_devig(m["ou"])[0]); R["og"].append(og[i])
        R["L"].append(L[ii]); R["E"].append(E[ii]); R["PI"].append(PI[ii])
        for k, g in gaps.items(): R[("gap",) + k].append(g[ii])
        log(lg, "uygun", len(ii))
    for k in list(R):
        if k in ("L", "E", "PI") or isinstance(k, tuple): R[k] = np.concatenate(R[k])
    y = np.array(R["y"]); yo = np.array(R["yo"]); d = np.array(R["d"]); lgs = np.array(R["lg"]); n = len(y)
    pm = np.array(R["pm"]); pmo = np.array(R["pmo"]); og = np.array(R["og"])
    blok = np.array([f"{a}|{b}" for a, b in zip(lgs, d)])
    p1, o1, _, _ = U.outcome_probs(R["L"][:, 0], R["L"][:, 1], rho)
    Ssel = d < ar.sinir
    aylar = sorted({x[:7] for x in d})

    def yig(X, ou=False, min_n=ar.min_n):
        out = np.full(n, np.nan) if ou else np.full((n, 3), np.nan)
        for ay in aylar:
            tr = d < ay + "-01"; te = np.array([x[:7] == ay for x in d])
            if tr.sum() < min_n: continue
            if ou: out[te] = G.logit_pred(X[te], G.logit_fit(X[tr], yo[tr]))
            else: out[te] = G.mlogit_pred(X[te], G.mlogit_fit(X[tr], y[tr]))
        return out

    # GAP λ/φ seçimi: S'de (aylık yığın, yalnız Poisson+GAP 1X2 + A/Ü toplam LL)
    X4 = G.ozellik_1x2(p1, R["E"], R["PI"]); Xo = G.ozellik_ou(o1, R["PI"], og)
    sk = {}
    for k in GAP_IZ:
        gx, gt = gap_x(R[("gap",) + k])
        q = yig(np.concatenate([X4, gx], 1)); qo = yig(np.concatenate([Xo, gt], 1), ou=True)
        m_ = Ssel & ~np.isnan(q[:, 0]) & ~np.isnan(qo)
        sk[k] = float(FL.ll3(q[m_], y[m_]).mean() + FL.ll2(qo[m_], yo[m_]).mean())
    kg = min(sk, key=sk.get); gx, gt = gap_x(R[("gap",) + kg])
    log("GAP ızgarası (S):", {f"{a}/{b}": round(v, 5) for (a, b), v in sk.items()}, "→", kg)

    lpm = np.log(np.clip(pm, 1e-6, 1)); Xm = np.stack([np.ones(n), lpm[:, 0] - lpm[:, 2], lpm[:, 1] - (lpm[:, 0] + lpm[:, 2]) / 2], 1)
    Xmo = np.stack([np.ones(n), logit2(pmo)], 1)
    yarislar = {
        "A1x2": ("model yolu 1X2: topluluk → topluluk+GAP", yig(X4), yig(np.concatenate([X4, gx], 1)), False),
        "Aou": ("model yolu 2,5 A/Ü: topluluk → topluluk+GAP", yig(Xo, True), yig(np.concatenate([Xo, gt], 1), True), True),
        "B1x2": ("piyasa üstü 1X2: piyasa yığını → piyasa+GAP", yig(Xm), yig(np.concatenate([Xm, gx], 1)), False),
        "B1x2t": ("piyasa üstü 1X2: piyasa+topluluk → +GAP", yig(np.concatenate([Xm, X4[:, 1:]], 1)), yig(np.concatenate([Xm, X4[:, 1:], gx], 1)), False),
        "Bou": ("piyasa üstü 2,5 A/Ü: piyasa yığını → piyasa+GAP", yig(Xmo, True), yig(np.concatenate([Xmo, gt], 1), True), True),
    }
    try:
        import oxx_ogren as O
        A = json.load(open(os.path.join(DATA, "fb_guc.json"), encoding="utf-8"))
        alfa = O.yatirim_alfa(json.loads(json.dumps(A)), f"fb_model-{date.today().year}", {"anahtar": "yh03_gap", "sinyal": {"kaynak": "ön kayıtlı laboratuvar adayı"}})
    except Exception as e:
        log("alfa okunamadı:", e); alfa = 0.01
    karne = {"madde": "YH-03", "tarih": date.today().isoformat(), "sinir": ar.sinir, "n_satir": int(n), "ligler": sorted(set(lgs.tolist())),
             "gap_secim": {"lam": kg[0], "phi": kg[1]}, "gap_izgara": {f"{a}/{b}": round(v, 5) for (a, b), v in sk.items()}, "alfa": round(alfa, 5), "yarislar": {}}
    for key, (ad, ref, ady, ou) in yarislar.items():
        okm = ~Ssel & (~np.isnan(ref) if ou else ~np.isnan(ref[:, 0])) & (~np.isnan(ady) if ou else ~np.isnan(ady[:, 0]))
        dT = d[okm]; s2 = sorted(dT)[len(dT) // 2]; h2 = dT >= s2
        if ou:
            l0, l1 = FL.ll2(ref[okm], yo[okm]), FL.ll2(ady[okm], yo[okm]); b0, b1 = FL.br2(ref[okm], yo[okm]), FL.br2(ady[okm], yo[okm])
            i0, i1 = ((ref[okm] >= .5) == yo[okm]).mean(), ((ady[okm] >= .5) == yo[okm]).mean()
        else:
            l0, l1 = FL.ll3(ref[okm], y[okm]), FL.ll3(ady[okm], y[okm]); b0, b1 = FL.br3(ref[okm], y[okm]), FL.br3(ady[okm], y[okm])
            i0, i1 = (ref[okm].argmax(1) == y[okm]).mean(), (ady[okm].argmax(1) == y[okm]).mean()
        dl = l1 - l0; bl = FL.blok_boot(dl, blok[okm]); bb = FL.blok_boot(b1 - b0, blok[okm])
        r = {"ad": ad, "n": int(okm.sum()), "ll_ref": round(float(l0.mean()), 5), "ll_aday": round(float(l1.mean()), 5), "dLL": bl, "dBrier": bb["fark"],
             "yari1": round(float(dl[~h2].mean()), 5), "yari2": round(float(dl[h2].mean()), 5), "isabet_ref": round(float(i0), 4), "isabet_aday": round(float(i1), 4)}
        r["gecti"] = bool(bl["ga95"][1] < 0 and r["yari1"] < 0 and r["yari2"] < 0 and r["dBrier"] <= 0 and i1 >= i0 - 1e-9 and bl["p_tek"] <= alfa)
        karne["yarislar"][key] = r
        log(f"{key:6s} {ad}: n {r['n']} ΔLL {bl['fark']:+.5f} {bl['ga95']} yarılar {r['yari1']:+.5f}/{r['yari2']:+.5f} ΔBrier {r['dBrier']:+.5f} "
            f"isabet {i0:.4f}→{i1:.4f} p {bl['p_tek']} α {alfa:.4f} → {'GEÇTİ' if r['gecti'] else 'geçmedi'}")
    json.dump(karne, open(ar.cikti, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("yazıldı", ar.cikti)


if __name__ == "__main__":
    main()
