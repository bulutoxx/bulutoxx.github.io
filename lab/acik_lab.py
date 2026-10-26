"""🌐 Açık veri laboratuvarı — yeni açık kaynakların tahmine katkısını "hiç oynanmamış gibi" sınar.

Kaynaklar: Club Elo (api.clubelo.com; atıf: clubelo.com) · openfootball/champions-league (CC0).
Taban (mevcut sistem) aynen üretim kodu: scripts/update.py learn_strength (kupa/ligler arası güç) ve
lab/fb_gelistir.py served_full (piyasa yolu, model.json ayarları).

Aday aileleri (her birinin varyantı YALNIZ seçim diliminde seçilir; karar sınama diliminde, iki ayrı alt dilimde):
  K1 — kupa güçlerini Club Elo'ya doğru büzme (scripts/acik_veri.py kupa_uygula ile aynı formül; ızgara w × beta).
  K2 — kupa güç öğrenmesine openfootball ile daha uzun kupa geçmişi (pencere 450 → 700 / 900 gün).
  L1 — lig maçlarında piyasa olasılığına Elo farkı düzeltmesi (z_k = ln q_k + θ·özellik; büzülmeli).
Zaman: seçim = 2023-07-01 … 2025-06-30 · sınama = 2025-07-01 sonrası (Elo bulunan maçlar), tarih ortancasından iki alt dilim.
Yürüyen pencere: her maç haftası için taban ve adaylar yalnız o haftanın pazartesisinden ÖNCEKİ maçlarla kurulur;
Elo, haftanın pazartesisinden bir gün önceki anlık görüntüdür (sızıntı yok).
Kapı (fb_gelistir kalıbı): her iki sınama alt diliminde MS log-kayıp Δ'sının eşleştirilmiş gün-blok bootstrap %95 GA üst
sınırı < 0, sınamada isabet düşmüyor (K1/K2: 2,5 A/Ü log-kaybı +0,002'den fazla bozulmuyor; L1: güçlü/Altın kuralları).
Çıktı: data/acik_lab.json (yalnız toplu metrik) ve kapıyı geçerse data/acik/elo_kupa.json (aktif=true, parametreler).
  ACIK_ONBELLEK=/geçici/klasör  ACIK_ELO_AYNA=/yol/clubelo-anlik.csv (isteğe bağlı: ağsız ortamda Elo geçmişi aynası)
"""
import bisect, collections, csv, glob, json, math, os, sys, time
from datetime import date, timedelta
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "lab"))
import update as U
import acik_veri as A
import fb_gelistir as FG

T0 = time.time()
BUDGET = float(os.environ.get("ACIK_BUDGET", "1500"))
SECIM = ("2023-07-01", "2025-07-01"); SINAMA0 = "2025-07-01"
OF_SEZON = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
EPS = 1e-9
W_IZGARA = (0.2, 0.4, 0.6, 0.8, 1.0); B_IZGARA = (0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6)   # 2. döngü: 1. döngüde en iyi sınırdaydı (0,4)


KAYNAKLAR = [   # 2026-10-26 değerlendirmesi (erişim · lisans · karar). Yasaklı/şartları belirsiz kaynaklar bilerek alınmaz.
    {"kaynak": "Club Elo (api.clubelo.com)", "icerik": "Avrupa kulüpleri günlük Elo", "lisans": "açık API, anahtarsız; atıf clubelo.com", "karar": "entegre (K1, L1 sınandı)"},
    {"kaynak": "openfootball/champions-league", "icerik": "UEFA kupa sonuçları 2021-26", "lisans": "CC0", "karar": "entegre (sınama geçmişi, K2)"},
    {"kaynak": "football-data.co.uk", "icerik": "sonuç + oran + şut/korner CSV", "lisans": "ücretsiz", "karar": "zaten kullanılıyor"},
    {"kaynak": "ESPN açık uçlar / EuroLeague resmi akış", "icerik": "kupa, ek ligler, basket + oran", "lisans": "resmî olmayan açık uç", "karar": "zaten kullanılıyor"},
    {"kaynak": "StatsBomb open-data", "icerik": "olay verisi (seçili turnuvalar)", "lisans": "kullanıcı sözleşmesi + atıf", "karar": "alınmadı: güncel sezon yok"},
    {"kaynak": "Understat / FBref xG", "icerik": "xG", "lisans": "kazıma; FBref gelişmiş veriyi 2026'da kaldırdı", "karar": "alınmadı: şartlar/kazıma"},
    {"kaynak": "martj42/international_results", "icerik": "milli maç sonuçları", "lisans": "CC0", "karar": "alınmadı: motorda milli takım ligi yok"},
    {"kaynak": "openfootball/football.json", "icerik": "lig sonuçları", "lisans": "CC0", "karar": "alınmadı: football-data ile örtüşüyor"},
    {"kaynak": "xgabora/Club-Football-Match-Data", "icerik": "football-data + Elo birleşik", "lisans": "MIT", "karar": "alınmadı: 2025-06 sonrası Elo kendi tahmini (ClubElo değil)"},
    {"kaynak": "tonyelhabr/club-rankings (Club Elo/Opta)", "icerik": "günlük sıralama anlık görüntüleri", "lisans": "belirtilmemiş; Opta kazıma", "karar": "yalnız yerel sınamada Club Elo aynası; üretimde kullanılmaz"},
    {"kaynak": "cenkozgur/tjk-data memory/ ve odds-snapshots", "icerik": "at özetleri, gün içi oran", "lisans": "belirtilmemiş ayna", "karar": "alınmadı: memory geleceği içerir, oran görüntüleri 2026-06'da durdu"},
    {"kaynak": "Diğer GitHub TJK depoları (bilaleren/tjk-api vb.)", "icerik": "TJK istemcileri", "lisans": "çoğu belirtilmemiş", "karar": "alınmadı: tjk.org'a istek atar / veri seti değil"},
    {"kaynak": "NBA stats / basketball-reference", "icerik": "NBA istatistik", "lisans": "kullanım şartları kazımayı kısıtlıyor", "karar": "alınmadı"},
]


def jl(p, d=None):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d


def log(*a): print(f"[{time.time() - T0:5.0f} sn]", *a, flush=True)


# ------------------------------------------------------------------ Elo kaynağı (ayna → API, haftalık anlık görüntü)
class Elo:
    def __init__(self):
        self.seri = {}; self.ulke = {}; self.son = ""; self.api = {}
        p = os.environ.get("ACIK_ELO_AYNA") or os.path.join(A.ONBELLEK, "clubelo_tony.csv")
        if os.path.exists(p):
            tmp = collections.defaultdict(list)
            for r in csv.DictReader(open(p, encoding="utf-8")):
                try: tmp[r["Club"]].append((r["date"], float(r["Elo"]))); self.ulke[r["Club"]] = r["Country"]
                except (KeyError, ValueError): continue
            for k, v in tmp.items():
                v.sort(); self.seri[k] = ([x[0] for x in v], [x[1] for x in v])
            self.son = max(v[0][-1] for v in self.seri.values()) if self.seri else ""
            log(f"Elo aynası: {len(self.seri)} kulüp, son {self.son}")
        self.kaynak = "ayna+api" if self.seri else "api"

    def gun(self, g):
        """g günü (ve öncesi) bilinen Elo: {kulüp: elo}. Aynanın kapsamı dışında API (ağ yoksa {})."""
        if self.seri and g <= self.son:
            out = {}
            for k, (ds, es) in self.seri.items():
                i = bisect.bisect_right(ds, g) - 1
                if i >= 0 and (date.fromisoformat(g) - date.fromisoformat(ds[i])).days <= 21: out[k] = es[i]
            return out
        if g not in self.api:
            E = A.clubelo_gun(g); self.api[g] = {k: v[1] for k, v in E.items()}
            for k, v in E.items(): self.ulke.setdefault(k, v[0])
        return self.api[g]


# ------------------------------------------------------------------ veri
def domestic():
    """Lig maçları (derin arşiv + season.json): {lg: [maç]} — learn_strength'in beklediği biçim."""
    S = jl(os.path.join(DATA, "season.json"), {}) or {}
    out = collections.defaultdict(dict); sez = {}
    for f in sorted(glob.glob(os.path.join(DATA, "derin", "*-*.json"))):
        D = jl(f, {}) or {}; lg = D.get("lg")
        for r in D.get("m", []):
            if r[3] is None: continue
            m = {"d": r[0], "h": r[1], "a": r[2], "ft": [r[3], r[4]], "season": D["sezon"]}
            if r[5] and r[6] and r[7]: m["odds"] = [r[5], r[6], r[7]]
            if r[8] and r[9]: m["ou"] = [r[8], r[9]]
            out[lg][(m["d"], m["h"], m["a"])] = m
    for lg, d in S.items():
        if d.get("cup") or d.get("src") == "espn": continue
        for m in d["matches"]:
            if m.get("ft"): out[lg][(m["d"], m["h"], m["a"])] = {k: m[k] for k in ("d", "h", "a", "ft", "season", "odds", "ou") if k in m}
    return {lg: sorted(v.values(), key=lambda m: m["d"]) for lg, v in out.items()}


def kanon_tablo(dom, elo):
    """Lig takım adlarımız → Club Elo adı (ülke ipucuyla)."""
    ad = dict(elo.ulke); out = {}
    for lg, ms in dom.items():
        c = A.CE_ULKE.get(lg)
        if not c: continue
        for t in {m["h"] for m in ms} | {m["a"] for m in ms}:
            k = A.eslestir(t, ad, c)
            if k: out.setdefault(t, k)
    return out


def kupalar(dom, kanon, elo):
    """Kupa maçları: openfootball (2025-07 öncesi) + season.json ESPN kupaları (2025-07 sonrası; üretimdeki veri).
    Takım kimliği: lig takımımızsa lig adımız (iç lig gücü için), değilse Club Elo adı (yoksa kaynak adı)."""
    ad = dict(elo.ulke); ters = collections.defaultdict(list)
    for t, k in kanon.items(): ters[k].append(t)
    son_lig = {}
    for lg, ms in dom.items():
        for m in ms: son_lig[m["h"]] = lg; son_lig[m["a"]] = lg
    def kimlik(t, c_ce, lg_ipucu=None):
        k = A.eslestir(t, ad, c_ce)
        if k and ters.get(k):
            cand = ters[k]
            if lg_ipucu: cand = [x for x in cand if son_lig.get(x) == lg_ipucu] or cand
            return cand[0], k
        return (k or t), k
    out = []
    for s in OF_SEZON[:-1]:
        for kod in ("cl", "el", "conf"):
            for m in A.openfootball_kupa(s, kod):
                if m["d"] >= SINAMA0: continue
                h, hk = kimlik(m["h"], A.OF_ULKE.get(m["hc"], m["hc"]), A.OF_LIG.get(m["hc"]))
                a, ak = kimlik(m["a"], A.OF_ULKE.get(m["ac"], m["ac"]), A.OF_LIG.get(m["ac"]))
                out.append({"d": m["d"], "h": h, "a": a, "ft": m["ft"], "hk": hk, "ak": ak, "kaynak": "openfootball", "season": U.season_of(m["d"])})
    S = jl(os.path.join(DATA, "season.json"), {}) or {}
    for ck in ("ucl", "uel", "uecl"):
        for m in (S.get(ck) or {}).get("matches", []):
            if not m.get("ft") or None in m["ft"][:2] or m["d"] < SINAMA0: continue
            def kk(t, lg):
                if lg: return t, kanon.get(t) or A.eslestir(t, ad, A.CE_ULKE.get(lg))
                k = A.eslestir(t, ad); return (k or t), k
            h, hk = kk(m["h"], m.get("hl")); a, ak = kk(m["a"], m.get("al"))
            out.append({"d": m["d"], "h": h, "a": a, "ft": m["ft"][:2], "hk": hk, "ak": ak, "kaynak": "espn", "season": m["season"]})
    out.sort(key=lambda m: (m["d"], m["h"]))
    for i, m in enumerate(out): m["i"] = i
    return out


# ------------------------------------------------------------------ taban: üretim learn_strength (fit çağrıları yakalanır)
def kupa_tabani(dom, cups, cut, P, pencere=450):
    lo = (date.fromisoformat(cut) - timedelta(days=pencere)).isoformat(); lo_d = (date.fromisoformat(cut) - timedelta(days=450)).isoformat()
    ps = {}
    for lg, ms in dom.items():
        sub = [m for m in ms if lo_d <= m["d"] < cut]
        if len(sub) < 20: continue
        ps[lg] = {"matches": sub, "season": max(m["season"] for m in sub)}
    ps["_kupa"] = {"cup": True, "matches": [m for m in cups if lo <= m["d"] < cut]}
    yak = {}
    asil = U.fit
    def fit2(ms, ref, P_, init=None, iters=25):
        r = asil(ms, ref, P_, init, iters); yak[id(ms)] = r; return r
    U.fit = fit2
    try: C = U.learn_strength(ps, P, date.fromisoformat(cut))
    finally: U.fit = asil
    # iç lig puanları (learn_strength'teki dom seçimiyle aynı kural) → kupa takımı olmayanlar için absRating yedeği
    dom_r = {}; ncur = {}
    for lg, d in ps.items():
        if d.get("cup"): continue
        f = yak.get(id(d["matches"]))
        if not f: continue
        cur = [m for m in d["matches"] if m["season"] == d["season"]]
        cnt = collections.Counter([m["h"] for m in cur] + [m["a"] for m in cur])
        for t, (a, de) in f["t"].items():
            if cnt[t] and cnt[t] > ncur.get(t, 0): dom_r[t] = (lg, a, de); ncur[t] = cnt[t]
    return C, dom_r


def puan(C, dom_r, t):
    if t in C["teams"]: return C["teams"][t][0], C["teams"][t][1]
    if t in dom_r:
        lg, a, de = dom_r[t]; k = C["strength"].get(lg, U.STRENGTH_PRIOR.get(lg, U.UNKNOWN_PRIOR))
        return a * math.exp(k), de * math.exp(-k)
    return None


def olas(lh, la, rho):
    p, pO, _, _ = U.outcome_probs(np.array(lh, float), np.array(la, float), rho)
    return p, pO


# ------------------------------------------------------------------ K1/K2 yürüyen pencere
def kupa_kos(dom, cups, P, elo, pencere=450, ust=None):
    """Her maç haftası: taban güçleri + (Elo varsa) her (w, beta) için büzülmüş güçler. Satır: maç ve λ'lar."""
    rho = P.get("rho", -0.06); rows = []
    haftalar = collections.OrderedDict()
    for m in cups:
        if ust and m["d"] >= ust: continue
        if m["d"] < SECIM[0]: continue
        d = date.fromisoformat(m["d"]); haftalar.setdefault((d - timedelta(days=d.weekday())).isoformat(), []).append(m)
    for i, (cut, ms) in enumerate(haftalar.items()):
        if time.time() - T0 > BUDGET: log("süre bütçesi doldu (kupa)"); break
        C, dom_r = kupa_tabani(dom, cups, cut, P, pencere)
        eg = (date.fromisoformat(cut) - timedelta(days=1)).isoformat()
        E = elo.gun(eg) if elo else {}
        # Elo yalnız kupa 'teams' sözlüğündeki takımlara uygulanır (üretimdeki kupa_uygula ile aynı)
        kmap = {}
        for m in cups:
            if m["d"] < cut: kmap[m["h"]] = m["hk"]; kmap[m["a"]] = m["ak"]
        for m in ms: kmap.setdefault(m["h"], m["hk"]); kmap.setdefault(m["a"], m["ak"])
        elo_t = {t: E[kmap[t]] for t in C["teams"] if kmap.get(t) in E}
        r = {t: math.log(v[0]) - math.log(v[1]) for t, v in C["teams"].items()}
        for m in ms:
            H, Aw = puan(C, dom_r, m["h"]), puan(C, dom_r, m["a"])
            if not H or not Aw: continue
            lh = C["mu"] * C["gamma"] * H[0] * Aw[1]; la = C["mu"] * Aw[0] * H[1]
            row = {"i": m["i"], "d": m["d"], "ft": m["ft"], "lh": lh, "la": la, "kaynak": m["kaynak"],
                   "elo": m["h"] in elo_t and m["a"] in elo_t, "dh": None}
            row["E"] = [elo_t.get(m["h"]), elo_t.get(m["a"])]
            row["r"] = [r.get(m["h"]), r.get(m["a"])]
            row["n_elo"] = len(elo_t)
            if len(elo_t) >= 8:
                rb = sum(r[t] for t in elo_t) / len(elo_t); eb = sum(elo_t.values()) / len(elo_t)
                row["rb"], row["eb"] = rb, eb
            rows.append(row)
        if i % 10 == 0: log(f"kupa haftası {cut}: {len(rows)} satır, Elo eşleşen {len(elo_t)}/{len(C['teams'])}")
    return rows


def k1_lam(row, w, beta):
    """Satır için Elo büzülmeli λ (acik_veri.kupa_uygula ile aynı formül; δ yalnız Elo'su olan takıma)."""
    lh, la = row["lh"], row["la"]
    if "rb" not in row: return lh, la
    dh = dA = 0.0
    if row["E"][0] is not None and row["r"][0] is not None: dh = w * (beta * (row["E"][0] - row["eb"]) / 100 - (row["r"][0] - row["rb"]))
    if row["E"][1] is not None and row["r"][1] is not None: dA = w * (beta * (row["E"][1] - row["eb"]) / 100 - (row["r"][1] - row["rb"]))
    # hücum·e^(δ/2), savunma·e^(−δ/2): λ_ev ∝ hücum_ev·savunma_dep → e^((δh − δa)/2)
    return lh * math.exp((dh - dA) / 2), la * math.exp((dA - dh) / 2)


def kayip(rows, lam, rho):
    lh = np.array([lam(r)[0] for r in rows]); la = np.array([lam(r)[1] for r in rows])
    p, pO = olas(np.clip(lh, .15, 4.5), np.clip(la, .1, 4), rho)
    res = np.array([0 if r["ft"][0] > r["ft"][1] else 1 if r["ft"][0] == r["ft"][1] else 2 for r in rows])
    ov = np.array([sum(r["ft"]) > 2 for r in rows], float)
    ll = -np.log(np.clip(p[np.arange(len(rows)), res], EPS, 1))
    llo = FG.bll(pO, ov)
    hit = (p.argmax(1) == res).astype(float)
    return ll, llo, hit


def kapi_kupa(rows_te, f0, f1, rho):
    """İki alt dilim (tarih ortancası): MS ΔLL GA üst < 0 her ikisinde; isabet düşmüyor; 2,5 LL +0,002'den fazla bozulmuyor."""
    ds = sorted(r["d"] for r in rows_te); med = ds[len(ds) // 2]
    out = {"dilimler": []}; ok = True
    for nm, sub in (("T1", [r for r in rows_te if r["d"] < med]), ("T2", [r for r in rows_te if r["d"] >= med])):
        l0, o0, h0 = kayip(sub, f0, rho); l1, o1, h1 = kayip(sub, f1, rho)
        m, lo, hi = FG.boot_ci(l1 - l0, [r["d"] for r in sub])
        R = {"ad": nm, "n": len(sub), "aralik": [sub[0]["d"], sub[-1]["d"]], "ll_mevcut": round(float(l0.mean()), 5),
             "ll_aday": round(float(l1.mean()), 5), "dll": round(m, 5), "ga95": [round(lo, 5), round(hi, 5)],
             "isabet_mevcut": round(float(h0.mean()), 4), "isabet_aday": round(float(h1.mean()), 4),
             "ou_ll_mevcut": round(float(o0.mean()), 5), "ou_ll_aday": round(float(o1.mean()), 5)}
        R["gecti"] = bool(hi < 0)
        ok = ok and R["gecti"]; out["dilimler"].append(R)
    l0, o0, h0 = kayip(rows_te, f0, rho); l1, o1, h1 = kayip(rows_te, f1, rho)
    m, lo, hi = FG.boot_ci(l1 - l0, [r["d"] for r in rows_te])
    out["toplam"] = {"n": len(rows_te), "dll": round(m, 5), "ga95": [round(lo, 5), round(hi, 5)],
                     "isabet_mevcut": round(float(h0.mean()), 4), "isabet_aday": round(float(h1.mean()), 4),
                     "ou_dll": round(float((o1 - o0).mean()), 5)}
    out["kabul"] = bool(ok and h1.mean() >= h0.mean() - 1e-9 and (o1 - o0).mean() <= 0.002)
    return out


# ------------------------------------------------------------------ L1: lig maçlarında piyasa + Elo
def lig_satirlari(dom, kanon, elo, P):
    H = []
    for lg, ms in dom.items():
        if lg not in A.CE_ULKE: continue
        for m in ms:
            if m["d"] < SECIM[0] or not m.get("odds") or not all(m["odds"]): continue
            kh, ka = kanon.get(m["h"]), kanon.get(m["a"])
            if not kh or not ka: continue
            H.append(dict(m, lg=lg, kh=kh, ka=ka))
    H.sort(key=lambda m: m["d"])
    out = []; cache = {}
    for m in H:
        d = date.fromisoformat(m["d"]); g = (d - timedelta(days=d.weekday() + 1)).isoformat()   # haftanın pazartesisinden önceki gün
        if g not in cache: cache[g] = elo.gun(g)
        E = cache[g]
        if m["kh"] in E and m["ka"] in E: out.append(dict(m, dE=(E[m["kh"]] - E[m["ka"]]) / 100.0))
    S = FG.served_full([m["odds"] for m in out], [m.get("ou") for m in out], P)
    return out, S


def l1_ozellik(rows, var):
    dE = np.array([m["dE"] for m in rows]); n = len(rows)
    if var == "fark":
        F = np.zeros((n, 3, 1)); F[:, 0, 0] = dE; F[:, 2, 0] = -dE
    else:
        F = np.zeros((n, 3, 2)); F[:, 0, 0] = dE; F[:, 2, 0] = -dE; F[:, 1, 1] = -np.abs(dE)
    return F


def l1_uygula(q, F, th):
    z = np.log(np.clip(q, EPS, 1)) + F @ th; z -= z.max(1, keepdims=True); p = np.exp(z); return p / p.sum(1, keepdims=True)


# ------------------------------------------------------------------ çalıştırıcı
def main():
    P = (jl(os.path.join(DATA, "model.json"), {}) or {}).get("params", {}); rho = P.get("rho", -0.06)
    R = {"tarih": date.today().isoformat(), "motor": (jl(os.path.join(DATA, "model.json"), {}) or {}).get("engine"),
         "kaynak_atfi": [A.ATIF["clubelo"], A.ATIF["openfootball"]],
         "yontem": "Yürüyen pencere (haftalık; yalnız önceki maçlar + önceki günün Elo'su). Varyant seçimi yalnız seçim "
                   f"diliminde ({SECIM[0]}…{SECIM[1]}); karar {SINAMA0} sonrası sınamada, tarih ortancasıyla iki alt dilimde: "
                   "MS log-kayıp Δ eşleştirilmiş gün-blok bootstrap %95 GA üst sınırı < 0 (ikisinde de), isabet düşmüyor.",
         "aileler": {}, "kaynaklar": KAYNAKLAR}
    elo = Elo()
    dom = domestic(); log("lig maçı:", sum(len(v) for v in dom.values()))
    kanon = kanon_tablo(dom, elo) if elo.ulke else {}
    cups = kupalar(dom, kanon, elo)
    R["veri"] = {"kupa_maci": len(cups), "kupa_openfootball": sum(1 for m in cups if m["kaynak"] == "openfootball"),
                 "kupa_espn": sum(1 for m in cups if m["kaynak"] == "espn"), "elo_kaynagi": elo.kaynak,
                 "elo_ayna_son": elo.son or None, "lig_takimi_elo_eslesen": len(kanon)}
    log("kupa maçı:", R["veri"])
    deneme = collections.Counter()
    # ---------------- K1 (Club Elo → kupa güçleri)
    rows = kupa_kos(dom, cups, P, elo)
    sel = [r for r in rows if SECIM[0] <= r["d"] < SECIM[1] and r["elo"]]
    te = [r for r in rows if r["d"] >= SINAMA0 and r["elo"]]
    f0 = lambda r: (r["lh"], r["la"])
    izgara = []
    for w in W_IZGARA:
        for b in B_IZGARA:
            l1, _, _ = kayip(sel, lambda r, w=w, b=b: k1_lam(r, w, b), rho); izgara.append((float(l1.mean()), w, b)); deneme["K1"] += 1
    l0s, _, h0s = kayip(sel, f0, rho)
    best = min(izgara)
    R["aileler"]["K1"] = {"ad": "Club Elo ile kupa/ligler arası güç büzülmesi (model.json cup.teams)",
                          "secim": {"n": len(sel), "ll_mevcut": round(float(l0s.mean()), 5), "en_iyi": {"ll": round(best[0], 5), "w": best[1], "beta": best[2]},
                                    "izgara_deneme": len(izgara), "ilk5": [{"ll": round(x[0], 5), "w": x[1], "beta": x[2]} for x in sorted(izgara)[:5]]},
                          "sinama_elo_yok_atlanan": sum(1 for r in rows if r["d"] >= SINAMA0 and not r["elo"])}
    if te:
        R["aileler"]["K1"]["sinama"] = kapi_kupa(te, f0, lambda r: k1_lam(r, best[1], best[2]), rho)
    log("K1", json.dumps(R["aileler"]["K1"], ensure_ascii=False)[:900])
    # ---------------- K2 (openfootball daha uzun kupa geçmişi)
    k2 = {}
    for pen in (700, 900):
        if time.time() - T0 > BUDGET: break
        rr = kupa_kos(dom, cups, P, None, pencere=pen); k2[pen] = rr; deneme["K2"] += 1
    if k2:
        by0 = {r["i"]: r for r in rows}
        sec = {}
        for pen, rr in k2.items():
            ss = [(by0[c["i"]], c) for c in rr if c["i"] in by0]          # iki tarafta da puanlanabilen aynı maçlar
            s_sel = [x for x in ss if SECIM[0] <= x[0]["d"] < SECIM[1]]
            l0, _, _ = kayip([x[0] for x in s_sel], f0, rho); l1, _, _ = kayip([x[1] for x in s_sel], f0, rho)
            sec[pen] = (float(l1.mean() - l0.mean()), ss)
        pen_b = min(sec, key=lambda k: sec[k][0])
        R["aileler"]["K2"] = {"ad": "openfootball (CC0) ile daha uzun kupa geçmişi (learn_strength penceresi)",
                              "secim": {str(k): {"dll": round(v[0], 5)} for k, v in sec.items()}, "secilen_pencere": pen_b}
        ss = [x for x in sec[pen_b][1] if x[0]["d"] >= SINAMA0]
        if ss:
            pair = [dict(b, lh2=c["lh"], la2=c["la"]) for b, c in ss]
            R["aileler"]["K2"]["sinama"] = kapi_kupa(pair, f0, lambda r: (r["lh2"], r["la2"]), rho)
        log("K2", json.dumps(R["aileler"]["K2"], ensure_ascii=False)[:700])
    # ---------------- L1 (lig: piyasa + Elo farkı)
    if time.time() - T0 < BUDGET:
        Lr, S = lig_satirlari(dom, kanon, elo, P)
        d = np.array([m["d"] for m in Lr]); hs = np.array([m["ft"][0] for m in Lr]); as_ = np.array([m["ft"][1] for m in Lr])
        res = np.where(hs > as_, 0, np.where(hs == as_, 1, 2)); ov = (hs + as_) > 2
        si = np.where((d >= SECIM[0]) & (d < SECIM[1]))[0]; ti = np.where(d >= SINAMA0)[0]
        cand = []
        if len(si) > 500:
            # seçim diliminin kendi içinde ileriye dönük: ilk yarıda öğren, ikinci yarıda ölç
            mid = si[len(si) // 2]
            a_, b_ = si[si < mid], si[si >= mid]
            for var in ("fark", "fark+beraberlik"):
                for lam in (10.0, 100.0):
                    F = l1_ozellik([Lr[i] for i in a_], var)
                    th = FG.softmax_fit(F, res[a_], base=np.log(np.clip(S["q"][a_], EPS, 1)), lam=lam)
                    p1 = l1_uygula(S["q"][b_], l1_ozellik([Lr[i] for i in b_], var), th)
                    l0 = -np.log(np.clip(S["q"][b_][np.arange(len(b_)), res[b_]], EPS, 1)); l1 = -np.log(np.clip(p1[np.arange(len(b_)), res[b_]], EPS, 1))
                    cand.append((float((l1 - l0).mean()), var, lam)); deneme["L1"] += 1
            best = min(cand)
            R["aileler"]["L1"] = {"ad": "Lig maçlarında piyasa olasılığına Club Elo farkı düzeltmesi",
                                  "secim": {"n": int(len(si)), "varyantlar": [{"dll": round(c[0], 5), "var": c[1], "lam": c[2]} for c in cand],
                                            "secilen": {"var": best[1], "lam": best[2]}}}
            if len(ti) > 200:
                F = l1_ozellik([Lr[i] for i in si], best[1])
                th = FG.softmax_fit(F, res[si], base=np.log(np.clip(S["q"][si], EPS, 1)), lam=best[2])
                q0 = S["q"][ti]; q1 = l1_uygula(q0, l1_ozellik([Lr[i] for i in ti], best[1]), th)
                med = np.median(d[ti].astype("datetime64[D]").astype(int))
                dd = d[ti].astype("datetime64[D]").astype(int)
                dil = []
                for nm, mk in (("T1", dd < med), ("T2", dd >= med)):
                    ix = np.where(mk)[0]
                    r = FG.slice_eval(list(d[ti][ix]), list(d[ti][ix]), q0[ix], S["O"][ti][ix], q1[ix], S["O"][ti][ix],
                                      [Lr[ti[i]]["odds"] for i in ix], [Lr[ti[i]].get("ou") for i in ix], res[ti][ix], ov[ti][ix], "ms")
                    r["ad"] = nm; r["aralik"] = [str(d[ti][ix][0]), str(d[ti][ix][-1])]; dil.append(r)
                R["aileler"]["L1"]["sinama"] = {"theta": [round(float(x), 4) for x in th], "dilimler": dil,
                                                "kabul": all(x["gecti"] for x in dil)}
            log("L1", json.dumps(R["aileler"]["L1"], ensure_ascii=False)[:900])
    R["deneme_sayisi"] = dict(deneme); R["deneme_toplam"] = sum(deneme.values())
    R["karar_sayisi"] = sum(1 for k in R["aileler"].values() if "sinama" in k)
    # ---------------- üretim bayrağı (yalnız K1 üretime bağlanabilir: model.json cup.teams)
    k1 = R["aileler"].get("K1", {}); kabul = bool(k1.get("sinama", {}).get("kabul"))
    ayar_p = os.path.join(DATA, "acik", "elo_kupa.json"); eski = jl(ayar_p, {}) or {}
    ayar = {"aktif": kabul, "w": k1.get("secim", {}).get("en_iyi", {}).get("w"), "beta": k1.get("secim", {}).get("en_iyi", {}).get("beta"),
            "karar_tarihi": R["tarih"], "kanit": "data/acik_lab.json → aileler.K1", "kaynak": A.ATIF["clubelo"],
            "geri_alma": "aktif=false yaz (ya da ACIK_ELO=0); scripts/acik_veri.py bir sonraki çalışmada kupa güçlerini ham hale döndürür"}
    if te and (len(te) >= 150 or not eski):     # yeterli sınama yoksa eski karar korunur
        os.makedirs(os.path.dirname(ayar_p), exist_ok=True)
        json.dump(ayar, open(ayar_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    R["uretim"] = {"K1_elo_kupa": ayar if te else eski}
    R["sure_sn"] = round(time.time() - T0)
    json.dump(R, open(os.path.join(DATA, "acik_lab.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, allow_nan=False)
    log("bitti", R["deneme_sayisi"], "K1 kabul" if kabul else "K1 red")


if __name__ == "__main__":
    main()
