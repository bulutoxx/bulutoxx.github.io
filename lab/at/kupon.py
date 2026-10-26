# OXXai at yarışı laboratuvarı — 🎟️ AT KUPONU modülü (Türkiye müşterek bahis türleri için olasılık + geri test).
# Hobi amaçlı: yalnız olasılık ve KOMBİNASYON SAYISI; para tutarı, bahis bağlantısı yok · 18+.
#
# Kurallar (açık kaynak araştırması, 2026-10-26; tjk.org'a istek atılmadı):
#   Ganyan        koşunun birincisi. Ekürili bir ata oynamak ekürinin o koşudaki tüm atlarına oynamaktır (tek birim).
#   Plase         at ilk İKİ dereceye girerse kazanır; en az 7 atlı koşularda açılır. (Ekürili: varsayım — tek birim.)
#   İkili         ilk iki at, sıra gözetmeksizin; en az 7 atlı koşu.
#   Sıralı İkili  ilk iki at, bitiş sırasıyla; en az 4 atlı koşu.
#   Çifte         art arda iki koşunun birincileri; ekürili kuralı geçerli (tek birim).
#   Sıralı Üçlü   ilk üç at, bitiş sırasıyla (kod "uclu"; TJK'da "3'lü Ganyan" ayrı bir bahistir: üç koşunun birincileri).
#   Tabela        ilk dört at; sıralı ya da sırasız (iki ayrı ikramiye). Burada ikisi de ölçülür.
#   6'lı Ganyan   lab/at/altili.py (data/at/altili_karne.json) — burada yalnız özet.
# Varsayımlar (kaynakta yok/çelişkili): ikili/sıralı ikili/üçlü/tabelada ekürili atlar AYRI at sayılır; plase'de
#   ekürili tek birim; sıralı üçlü en az 4, tabela en az 5 atlı koşu; çifte her ardışık koşu çiftinde açık sayılır
#   (aynada çifte bayrağı yok); 7+ atlı koşuda plase hep ilk 2 (bazı kaynaklardaki "kalabalık alanda ilk 3" teyit edilemedi).
#
# Olasılık: indirimli Harville (Henery üsleri):
#   P(i 1., j 2., k 3., l 4.) = p_i · p_j^γ/Σ_{≠i} p^γ · p_k^δ/Σ_{≠i,j} p^δ · p_l^δ/Σ_{≠i,j,k} p^δ
# Çok seçimli kupon: ayrık kombinasyonların olasılık toplamı (plase'de "en az bir at ilk 2'de" = 1 − P(hiçbiri)).
# Geri test: data/at/replay_kosular.json (sızıntısız gün gün yeniden oynatma); seçim YALNIZ p_sabah ile, sonuç yalnız
# puanlamada. γ, δ yalnız seçim diliminde (ilk 2/3 gün) öğrenilir; son 1/3 gün sınama olarak ayrı raporlanır.
#   python lab/at/kupon.py      # data/at/kupon_karne.json
import json, math, os, sys, time
from datetime import datetime, timezone
from itertools import permutations

import numpy as np

BURA = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.abspath(os.path.join(BURA, "..", ".."))
CIKTI = os.path.join(KOK, "data", "at")
KARNE = os.path.join(CIKTI, "kupon_karne.json")
REPLAY_KOSU = os.path.join(CIKTI, "replay_kosular.json")
ALTILI_KARNE = os.path.join(CIKTI, "altili_karne.json")
UYARI = "Hobi amaçlı olasılık; garanti değildir · 18+"
KOVA = [0.0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0000001]

KAYNAKLAR = [
    {"ad": "e-Bayi Yardım (müşterek bahis kuralları)", "url": "https://ebayi.org/yardim/36"},
    {"ad": "İstinye Ganyan — Sıkça Sorulan Sorular", "url": "https://istinyeganyan.com/ganyan/sikcaa-sorulan-sorular/"},
    {"ad": "İddaa Bülteni — TJK bahis türleri", "url": "https://xn--iddaablteni-yhb.com/at-yarisi/at-yarisi-tjk-nasil-oynanir-bahis-turleri-ve-oyunlarin-resmi-aciklamalari-tanimlari/"},
    {"ad": "UAT Racing — Yarışsever Sözlüğü", "url": "https://uatracing.com/sozluk.html"},
]

# kod: (ad, kisa, kural, koşu sayısı, sıralı, ilk, en az at, seviyeler (en olası K), kutu (at sayısı))
TUR = {
    "ganyan": ("Ganyan", "tek at kazanır",
               "Koşunun birincisini bil. Ekürili bir ata oynamak ekürinin o koşudaki tüm atlarına oynamaktır (tek birim).",
               1, True, 1, 2, [1, 2, 3], []),
    "plase": ("Plase", "at ilk 2'ye girer",
              "Seçilen at ilk iki dereceye girerse kazanır; en az 7 atlı koşularda açılır. Varsayım: ekürili atlar tek birim; "
              "7+ atlı her koşuda ilk 2 (kalabalık alanda ilk 3 kuralı teyit edilemedi).",
              1, False, 2, 7, [1, 2], []),
    "ikili": ("İkili", "ilk iki, sırasız",
              "Birinci ve ikinciyi sıra gözetmeksizin bil; en az 7 atlı koşu. Varsayım: ekürili atlar ayrı at.",
              1, False, 2, 7, [1, 3, 6, 10], [3, 4, 5]),
    "sirali_ikili": ("Sıralı İkili", "ilk iki, sıralı",
                     "Birinci ve ikinciyi bitiş sırasıyla bil; en az 4 atlı koşu. Varsayım: ekürili atlar ayrı at.",
                     1, True, 2, 4, [1, 3, 6, 10], [3, 4]),
    "cifte": ("Çifte", "art arda iki koşunun kazananları",
              "Ardışık iki koşunun birincilerini ayrı ayrı bil; ekürili kuralı geçerli (tek birim). Varsayım: aynı gün aynı "
              "hipodromdaki her ardışık koşu çifti (aynada çifte bayrağı yok).",
              2, True, 1, 2, [1, 3, 6, 10], [2, 3]),
    "uclu": ("Sıralı Üçlü", "ilk üç, sıralı",
             "Birinci, ikinci ve üçüncüyü bitiş sırasıyla bil. (TJK'nın '3'lü Ganyan'ı farklıdır: üç koşunun birincileri.) "
             "Varsayım: en az 4 atlı koşu; ekürili atlar ayrı at.",
             1, True, 3, 4, [1, 3, 6, 10, 24, 60], [3, 4, 5]),
    "tabela": ("Tabela", "ilk dört, sıralı",
               "İlk dört dereceyi bil: tam sıra 'sıralı', başka sıra 'sırasız' ikramiyesi alır (sırasız ayrıca ölçüldü). "
               "Varsayım: en az 5 atlı koşu; ekürili atlar ayrı at.",
               1, True, 4, 5, [1, 3, 6, 10, 24, 60, 120], [4, 5, 6]),
}


def jyaz(yol, veri_):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    tmp = yol + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(veri_, f, ensure_ascii=False, indent=1)
    os.replace(tmp, yol)


def joku(yol, vars_=None):
    try:
        return json.load(open(yol, encoding="utf-8"))
    except Exception:
        return vars_


def _r(v, n=4):
    return None if v is None else round(float(v), n)


# ---------------------------------------------------------------- olasılık çekirdeği
def harville(p, gam=1.0, dlt=1.0, derin=4):
    """p (kazanma, toplamı 1) -> [P1 (n), P12 (n,n), P123 (n,n,n), P1234 (n,n,n,n)] derin'e kadar; tekrar eden indeks 0."""
    p = np.clip(np.asarray(p, float), 1e-9, None)
    p = p / p.sum()
    n = len(p)
    pg, pd = p ** gam, p ** dlt
    out = [p]
    if derin >= 2 and n >= 2:
        P12 = p[:, None] * pg[None, :] / (pg.sum() - pg)[:, None]
        np.fill_diagonal(P12, 0.0)
        out.append(P12)
    if derin >= 3 and n >= 3:
        Sd = pd.sum()
        den = Sd - pd[:, None] - pd[None, :]
        with np.errstate(divide="ignore", invalid="ignore"):
            P123 = out[1][:, :, None] * pd[None, None, :] / den[:, :, None]
        I = np.arange(n)
        P123 = np.nan_to_num(P123, nan=0.0, posinf=0.0, neginf=0.0)
        P123[I, :, I] = 0.0; P123[:, I, I] = 0.0; P123[I, I, :] = 0.0
        out.append(P123)
        if derin >= 4 and n >= 4:
            den3 = Sd - pd[:, None, None] - pd[None, :, None] - pd[None, None, :]
            with np.errstate(divide="ignore", invalid="ignore"):
                P1234 = P123[..., None] * pd[None, None, None, :] / den3[..., None]
            P1234 = np.nan_to_num(P1234, nan=0.0, posinf=0.0, neginf=0.0)
            P1234[I, :, :, I] = 0.0; P1234[:, I, :, I] = 0.0; P1234[:, :, I, I] = 0.0
            P1234[P123 == 0] = 0.0
            out.append(P1234)
    return out


def birimler(nolar, ekuri):
    """Ekürili gruplar -> birim listesi (indeks listeleri)."""
    yer = {str(x): i for i, x in enumerate(nolar)}
    gorulen, U = set(), []
    for g in ekuri or []:
        ix = [yer[str(x)] for x in g if str(x) in yer]
        if len(ix) > 1:
            U.append(ix); gorulen.update(ix)
    U += [[i] for i in range(len(nolar)) if i not in gorulen]
    return U


def plase_birim(P12, U, m=2):
    """P(birimin en az bir atı ilk m'de), m=2 (Harville ikili matrisinden, içerme-dışlama)."""
    p1 = P12.sum(1)                      # i 1. olur (P12 satır toplamı = p_i)
    ilk2 = p1 + P12.sum(0)
    out = []
    for u in U:
        v = sum(ilk2[i] for i in u)
        for a in range(len(u)):
            for b in range(a + 1, len(u)):
                v -= P12[u[a], u[b]] + P12[u[b], u[a]]
        out.append(min(v, 1.0))
    return np.array(out)


def kume_plase(P12, idx):
    """Seçilen atlardan en az biri ilk 2'de: 1 − Σ_{i,j ∉ S} P12[i,j]."""
    m = np.ones(len(P12), bool); m[list(idx)] = False
    return float(1.0 - P12[np.ix_(m, m)].sum())


# ---------------------------------------------------------------- Henery üsleri (seçim diliminde)
class _K:
    def __init__(self, kosular, sutun=1):
        self.n = np.array([len(k["a"]) for k in kosular]); self.R = len(kosular)
        self.bas = np.concatenate([[0], np.cumsum(self.n)[:-1]])
        self.sira = np.array([(a[3] if a[3] is not None else 99) for k in kosular for a in k["a"]])
        p = []
        for k in kosular:
            v = np.array([a[sutun] for a in k["a"]], float); p.extend(v / v.sum())
        self.p = np.array(p)


def henery(kosular, sutun=1):
    sys.path.insert(0, BURA)
    import model as M
    K = _K(kosular, sutun)
    return M.henery_ussu(K.p, K, 2), M.henery_ussu(K.p, K, 3), M.henery_ussu(K.p, K, 4)


# ---------------------------------------------------------------- geri test
def _sonuc_sira(k):
    """Bitiş sırası (indeks) ilk 4; eşit/eksik derece varsa o derinlikten itibaren None."""
    pos = [a[3] for a in k["a"]]
    out = []
    for d in (1, 2, 3, 4):
        ix = [i for i, x in enumerate(pos) if x == d]
        if len(ix) != 1:
            break
        out.append(ix[0])
    return out


class Topla:
    def __init__(self):
        self.sat = {}          # seviye -> [(t, p, hit)]
        self.kova = np.zeros((3, len(KOVA) - 1))     # n, Σp, Σhit (tüm tekil kombinasyonlar)
        self.kova_s = np.zeros((3, len(KOVA) - 1))   # aynı, yalnız sınama
        self.atlanan = 0

    def ekle(self, sev, t, p, h):
        self.sat.setdefault(sev, []).append((t, float(p), int(h)))

    def kova_ekle(self, vals, hit_flat, sinama):
        b = np.clip(np.digitize(vals, KOVA) - 1, 0, len(KOVA) - 2)
        for K in ([self.kova, self.kova_s] if sinama else [self.kova]):
            K[0] += np.bincount(b, minlength=len(KOVA) - 1)
            K[1] += np.bincount(b, weights=vals, minlength=len(KOVA) - 1)
            if hit_flat is not None and len(hit_flat):
                np.add.at(K[2], b[np.asarray(hit_flat, int)], 1)


def _ozet(L):
    n = len(L)
    if not n:
        return {"n": 0, "isabet": 0, "beklenen": 0.0}
    h = sum(x[2] for x in L); e = sum(x[1] for x in L); v = sum(x[1] * (1 - x[1]) for x in L)
    return {"n": n, "isabet": h, "beklenen": _r(e, 2), "isabet_orani": _r(h / n), "beklenen_oran": _r(e / n),
            "z": _r((h - e) / math.sqrt(v), 2) if v > 0 else None}


def _kova_json(K):
    out = []
    for b in range(len(KOVA) - 1):
        if K[0][b] > 0:
            out.append({"aralik": f"{KOVA[b]:.3f}-{min(KOVA[b + 1], 1.0):.3f}", "n": int(K[0][b]),
                        "tahmin": _r(K[1][b] / K[0][b]), "gercek": _r(K[2][b] / K[0][b])})
    return out


def _topk(v, K):
    K = min(K, len(v))
    ix = np.argpartition(-v, K - 1)[:K]
    return ix[np.argsort(-v[ix])]


_D4 = {}


def _dortlu(n):
    """n atlı koşuda i<j<k<l dörtlülerinin düz indeksleri ve kendileri (önbellekli)."""
    if n not in _D4:
        I = np.arange(n)
        ii = np.stack(np.meshgrid(I, I, I, I, indexing="ij"), -1).reshape(-1, 4)
        m = np.flatnonzero((ii[:, 0] < ii[:, 1]) & (ii[:, 1] < ii[:, 2]) & (ii[:, 2] < ii[:, 3]))
        _D4[n] = (m, ii[m])
    return _D4[n]


def _kutu(T, b, r):
    """Kutu (virgüllü) olasılığı: b atlarının tüm r'li sıralı dizilişleri (T ilgili Harville tensörü)."""
    return float(T[np.ix_(*([b] * r))].sum())


def oynat(R, kes, gam, dlt, log=print):
    A = {k: Topla() for k in TUR}
    A["tabela_sirasiz"] = Topla()
    ollu = {k: [] for k in TUR}    # p_oran ile seçim (bilgi; kapanış oranı sabah bilgisi değildir)
    ll = {"indirimli": {"ikili": [], "uclu": [], "tabela": []}, "duz": {"ikili": [], "uclu": [], "tabela": []}}
    onceki = {}
    kosu_ix = {(k["t"], k["h"], k["k"]): k for k in R}
    for k in R:
        t, sn = k["t"], k["t"] >= kes
        nolar = [a[0] for a in k["a"]]
        n = len(nolar)
        p = np.array([a[1] for a in k["a"]], float); p /= p.sum()
        S = _sonuc_sira(k)
        H = harville(p, gam, dlt, 4)
        U = birimler(nolar, k["e"])
        # --- ganyan (birim)
        pu = np.array([p[u].sum() for u in U])
        if S:
            wu = next(i for i, u in enumerate(U) if S[0] in u)
            o = np.argsort(-pu)
            for K in TUR["ganyan"][7]:
                A["ganyan"].ekle(K, t, pu[o[:K]].sum(), wu in o[:K])
            A["ganyan"].kova_ekle(pu, np.array([wu]), sn)
        else:
            A["ganyan"].atlanan += 1
        # --- plase
        if n >= TUR["plase"][6]:
            if len(S) >= 2:
                P12 = H[1]
                pp = plase_birim(P12, U)
                o = np.argsort(-pp)
                hitu = np.array([any(i in S[:2] for i in u) for u in U])
                for K in TUR["plase"][7]:
                    idx = [i for u in o[:K] for i in U[u]]
                    A["plase"].ekle(K, t, kume_plase(P12, idx), hitu[o[:K]].any())
                A["plase"].kova_ekle(pp, np.flatnonzero(hitu), sn)
            else:
                A["plase"].atlanan += 1
        # --- ikili / sıralı ikili
        for kod, sirali in (("ikili", False), ("sirali_ikili", True)):
            if n < TUR[kod][6]:
                continue
            if len(S) < 2:
                A[kod].atlanan += 1; continue
            P12 = H[1]
            if sirali:
                M_ = P12; iu = np.flatnonzero(~np.eye(n, dtype=bool).ravel())
                hit = S[0] * n + S[1]
            else:
                M_ = np.triu(P12 + P12.T, 1); iu = np.flatnonzero(np.triu(np.ones((n, n), bool), 1).ravel())
                a_, b_ = sorted(S[:2]); hit = a_ * n + b_
            v = M_.ravel()[iu]
            hpos = np.flatnonzero(iu == hit)
            o = np.argsort(-v)
            for K in TUR[kod][7]:
                A[kod].ekle(K, t, v[o[:K]].sum(), hpos[0] in o[:K])
            A[kod].kova_ekle(v, hpos, sn)
            top = list(np.argsort(-p))
            for b in TUR[kod][8]:
                if b <= n:
                    bx = top[:b]
                    ph = _kutu(P12, bx, 2) / (1 if sirali else 1)
                    A[kod].ekle(("kutu", b), t, ph, S[0] in bx and S[1] in bx)
        # --- sıralı üçlü
        if n >= TUR["uclu"][6]:
            if len(S) >= 3:
                T3 = H[2]; v = T3.ravel(); hit = (S[0] * n + S[1]) * n + S[2]
                nz = np.flatnonzero(v > 0)
                vv = v[nz]; hpos = np.flatnonzero(nz == hit)
                kmax = max(TUR["uclu"][7]); o = _topk(vv, kmax)
                for K in TUR["uclu"][7]:
                    A["uclu"].ekle(K, t, vv[o[:K]].sum(), len(hpos) and hpos[0] in o[:K])
                A["uclu"].kova_ekle(vv, hpos, sn)
                top = list(np.argsort(-p))
                for b in TUR["uclu"][8]:
                    if b <= n:
                        bx = top[:b]
                        A["uclu"].ekle(("kutu", b), t, _kutu(T3, bx, 3), all(s in bx for s in S[:3]))
            else:
                A["uclu"].atlanan += 1
        # --- tabela (sıralı + sırasız)
        if n >= TUR["tabela"][6]:
            if len(S) >= 4:
                T4 = H[3]; v = T4.ravel(); hit = ((S[0] * n + S[1]) * n + S[2]) * n + S[3]
                nz = np.flatnonzero(v > 0); vv = v[nz]; hpos = np.flatnonzero(nz == hit)
                kmax = max(TUR["tabela"][7]); o = _topk(vv, kmax)
                for K in TUR["tabela"][7]:
                    A["tabela"].ekle(K, t, vv[o[:K]].sum(), len(hpos) and hpos[0] in o[:K])
                A["tabela"].kova_ekle(vv, hpos, sn)
                top = list(np.argsort(-p))
                for b in TUR["tabela"][8]:
                    if b <= n:
                        bx = top[:b]
                        A["tabela"].ekle(("kutu", b), t, _kutu(T4, bx, 4), all(s in bx for s in S[:4]))
                # sırasız: 4'lü kümeler
                Ssym = sum(np.transpose(T4, pr) for pr in permutations(range(4)))
                m, cs = _dortlu(n)
                vs = Ssym.ravel()[m]
                hs = tuple(sorted(S[:4]))
                hpos = np.flatnonzero((cs == np.array(hs)).all(1))
                o = _topk(vs, max(TUR["tabela"][7]))
                for K in TUR["tabela"][7]:
                    A["tabela_sirasiz"].ekle(K, t, vs[o[:K]].sum(), hpos[0] in o[:K])
                A["tabela_sirasiz"].kova_ekle(vs, hpos, sn)
            else:
                A["tabela"].atlanan += 1
        # --- log-loss (indirimli vs düz Harville), sınama
        if sn and len(S) >= 2:
            D = harville(p, 1.0, 1.0, 4)
            for ad, HH in (("indirimli", H), ("duz", D)):
                ll[ad]["ikili"].append(-math.log(max(HH[1][S[0], S[1]], 1e-12)))
                if len(S) >= 3 and n >= 3:
                    ll[ad]["uclu"].append(-math.log(max(HH[2][S[0], S[1], S[2]], 1e-12)))
                if len(S) >= 4 and n >= 4:
                    ll[ad]["tabela"].append(-math.log(max(HH[3][S[0], S[1], S[2], S[3]], 1e-12)))
        # --- p_oran ile en olası tek kombinasyon (bilgi)
        if S and all(a[2] is not None for a in k["a"]):
            q = np.array([a[2] for a in k["a"]], float); q /= q.sum()
            Hq = harville(q, gam, dlt, 3)
            qu = np.array([q[u].sum() for u in U]); w = int(np.argmax(qu))
            ollu["ganyan"].append((t, qu[w], S[0] in U[w]))
            if len(S) >= 2:
                if n >= 7:
                    pp = plase_birim(Hq[1], U); w = int(np.argmax(pp))
                    ollu["plase"].append((t, pp[w], any(i in S[:2] for i in U[w])))
                    Mi = np.triu(Hq[1] + Hq[1].T, 1); i, j = np.unravel_index(np.argmax(Mi), Mi.shape)
                    ollu["ikili"].append((t, Mi[i, j], {i, j} == set(S[:2])))
                if n >= 4:
                    i, j = np.unravel_index(np.argmax(Hq[1]), Hq[1].shape)
                    ollu["sirali_ikili"].append((t, Hq[1][i, j], [i, j] == S[:2]))
            if len(S) >= 3 and n >= 4:
                i, j, l_ = np.unravel_index(np.argmax(Hq[2]), Hq[2].shape)
                ollu["uclu"].append((t, Hq[2][i, j, l_], [i, j, l_] == S[:3]))
        # --- çifte: önceki koşu (aynı gün, aynı hipodrom, koşu no − 1)
        onc = kosu_ix.get((t, k["h"], k["k"] - 1))
        if onc is not None:
            pa = np.array([a[1] for a in onc["a"]], float); pa /= pa.sum()
            Ua = birimler([a[0] for a in onc["a"]], onc["e"])
            pua = np.array([pa[u].sum() for u in Ua])
            Sa = _sonuc_sira(onc)
            if Sa and S:
                wa = next(i for i, u in enumerate(Ua) if Sa[0] in u)
                wb = next(i for i, u in enumerate(U) if S[0] in u)
                Mc = pua[:, None] * pu[None, :]
                v = Mc.ravel(); hpos = np.array([wa * len(U) + wb])
                o = np.argsort(-v)
                for K in TUR["cifte"][7]:
                    A["cifte"].ekle(K, t, v[o[:K]].sum(), hpos[0] in o[:K])
                A["cifte"].kova_ekle(v, hpos, sn)
                oa, ob = np.argsort(-pua), np.argsort(-pu)
                for b in TUR["cifte"][8]:
                    xa, xb = oa[:b], ob[:b]
                    A["cifte"].ekle(("kutu", b), t, pua[xa].sum() * pu[xb].sum(), wa in xa and wb in xb)
            else:
                A["cifte"].atlanan += 1
    return A, ollu, ll


def _tur_json(kod, T, kes, ad=None):
    seviye = sorted(k for k in T.sat if not isinstance(k, tuple))
    kutu = sorted(k for k in T.sat if isinstance(k, tuple))

    def blok(L):
        tum = _ozet(L)
        sec = _ozet([x for x in L if x[0] < kes])
        sin = _ozet([x for x in L if x[0] >= kes])
        return tum, sec, sin
    out = {}
    s1 = seviye[0]
    tum, sec, sin = blok(T.sat[s1])
    out.update({**tum, "secim": sec, "sinama": sin, "atlanan_esit_derece": T.atlanan,
                "kovalar": _kova_json(T.kova), "kovalar_sinama": _kova_json(T.kova_s)})
    out["seviyeler"] = []
    for s in seviye:
        tum, sec, sin = blok(T.sat[s])
        out["seviyeler"].append({"kombinasyon": s, "kural": f"en olası {s} kombinasyon (p_sabah)", **tum,
                                 "sinama": {x: sin[x] for x in ("n", "isabet", "beklenen")}})
    if kutu:
        out["kutu"] = []
        for s in kutu:
            b = s[1]
            komb = {"ikili": b * (b - 1) // 2, "sirali_ikili": b * (b - 1), "uclu": b * (b - 1) * (b - 2),
                    "tabela": b * (b - 1) * (b - 2) * (b - 3), "cifte": b * b}[kod]
            tum, sec, sin = blok(T.sat[s])
            out["kutu"].append({"at": b, "kombinasyon": komb,
                                "kural": (f"her iki koşuda en olası {b} at ({b}×{b})" if kod == "cifte"
                                          else f"en olası {b} atın tüm dizilişleri (virgüllü/kutu)"),
                                **tum, "sinama": {x: sin[x] for x in ("n", "isabet", "beklenen")}})
    return out


def altili_ozet():
    a = joku(ALTILI_KARNE) or {}
    g = a.get("geriye_donuk") or {}
    if not g:
        return None
    sev = g.get("seviyeler") or {}
    sin = (g.get("sinama") or {}).get("seviyeler") or {}
    but = g.get("butce") or {}
    L = []
    for ad_, B in sorted(but.items(), key=lambda x: x[1]):
        s = sev.get(ad_) or {}
        L.append({"kombinasyon": B, "seviye": ad_, "kural": "ayak ayak tam DP dağıtım (altili.py)",
                  "n": s.get("n"), "isabet": s.get("isabet"), "beklenen": s.get("beklenen"),
                  "sinama": {x: (sin.get(ad_) or {}).get(x) for x in ("n", "isabet", "beklenen")}})
    ilk = L[0] if L else {}
    return {"ad": "6'lı Ganyan", "kisa": "art arda 6 koşunun kazananları",
            "kural": "Ganyan başlangıcı işaretli koşudan itibaren ardışık 6 koşunun birincileri; ekürili atlar bir ayakta tek "
                     "seçim. Ayrıntı ve canlı karne: altili_karne.json.",
            "koşu_sayisi": 6, "kosu_sayisi": 6, "sirali": True, "ilk": 1, "kaynak": "altili_karne.json",
            "n": ilk.get("n"), "isabet": ilk.get("isabet"), "beklenen": ilk.get("beklenen"), "sinama": ilk.get("sinama"),
            "seviyeler": L, "donem": g.get("donem")}


def dogrulama_ornegi(gam, dlt):
    """Arayüz uygulaması (JS) için sınama vektörü: aynı girdiyle aynı sayılar çıkmalı."""
    p = [0.40, 0.25, 0.15, 0.10, 0.06, 0.04]
    H = harville(p, gam, dlt, 4)
    U = birimler(["1", "2", "3", "4", "5", "6"], [])
    return {"p": p, "gamma": gam, "delta": dlt, "at_no": ["1", "2", "3", "4", "5", "6"],
            "ganyan_1": _r(H[0][0], 6), "plase_1": _r(plase_birim(H[1], U)[0], 6),
            "sirali_ikili_1_2": _r(H[1][0, 1], 6), "ikili_1_2": _r(H[1][0, 1] + H[1][1, 0], 6),
            "uclu_1_2_3": _r(H[2][0, 1, 2], 6), "tabela_1_2_3_4": _r(H[3][0, 1, 2, 3], 6),
            "tabela_sirasiz_1_2_3_4": _r(_kutu(H[3], [0, 1, 2, 3], 4), 6),
            "sirali_ikili_kolon_1.[1,2]_2.[3,4]": _r(H[1][np.ix_([0, 1], [2, 3])].sum(), 6),
            "plase_ekuri_1+2": _r(plase_birim(H[1], birimler(["1", "2", "3", "4", "5", "6"], [["1", "2"]]))[0], 6)}


def karne_guncelle(log=print):
    t0 = time.time()
    RJ = joku(REPLAY_KOSU)
    if not RJ:
        log("kupon: replay_kosular.json yok"); return None
    R = RJ["kosular"]
    gunler = sorted({k["t"] for k in R})
    kes = gunler[int(round(len(gunler) * 2 / 3))]
    sec_k = [k for k in R if k["t"] < kes]
    gam, dlt, eps = henery(sec_k, 1)
    sec_o = [k for k in sec_k if all(a[2] is not None for a in k["a"])]
    gam_o, dlt_o, eps_o = henery(sec_o, 2)
    log(f"kupon: {len(R)} koşu, kesim {kes}; γ={gam} δ={dlt} (4. sıra üssü {eps}); oran γ={gam_o} δ={dlt_o}")
    A, ollu, ll = oynat(R, kes, gam, dlt, log)
    mj = joku(os.path.join(CIKTI, "model.json")) or {}
    um = mj.get("uretim_modeli") or {}
    turler = {}
    for kod, (ad, kisa, kural, ks, sirali, ilk, enaz, _, _) in TUR.items():
        d = {"ad": ad, "kisa": kisa, "kural": kural, "koşu_sayisi": ks, "kosu_sayisi": ks, "sirali": sirali, "ilk": ilk,
             "en_az_at": enaz, **_tur_json(kod, A[kod], kes)}
        if ollu.get(kod):
            o = _ozet(ollu[kod])
            d["oranli_bilgi"] = {**{x: o[x] for x in ("n", "isabet", "beklenen")},
                                 "not": "en olası tek kombinasyon, kapanış oranıyla harman p_oran (sabah bilinmez; yalnız bilgi)"}
        turler[kod] = d
    ts = _tur_json("tabela", A["tabela_sirasiz"], kes)
    turler["tabela"]["sirasiz"] = {"kisa": "ilk dört, sırasız", **{k: v for k, v in ts.items() if k != "kutu"}}
    al = altili_ozet()
    if al:
        turler["altili"] = al
    llo = {ad: {k: _r(np.mean(v), 4) if v else None for k, v in d.items()} for ad, d in ll.items()}
    llo["kosu"] = len(ll["indirimli"]["ikili"])
    out = {
        "v": 1, "guncelleme": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "donem": [gunler[0], gunler[-1]],
        "bolum": {"secim": [gunler[0], gunler[gunler.index(kes) - 1]], "sinama": [kes, gunler[-1]]},
        "kaynak": ("Geri test: data/at/replay_kosular.json (gün gün sızıntısız yeniden oynatma, açık TJK sonuç arşivi "
                   "github.com/cenkozgur/tjk-data). Her geçmiş koşu 'hiç oynanmamış gibi' yalnız p_sabah ile seçildi; sonuç "
                   "yalnız puanlamada kullanıldı. γ, δ yalnız seçim diliminde (ilk 2/3 gün) öğrenildi; 'sinama' son 1/3 gün."),
        "uyari": UYARI,
        "harville": {"gamma": gam, "delta": dlt, "p_kaynak": "p_kazanma (sabah) / p_oran",
                     "gamma_oran": gam_o, "delta_oran": dlt_o, "dorduncu_sira_ussu_olculen": eps,
                     "formul": "P(i,j,k,l) = p_i · p_j^γ/Σ_{≠i}p^γ · p_k^δ/Σ_{≠i,j}p^δ · p_l^δ/Σ_{≠i,j,k}p^δ",
                     "kullanim": "p_sabah ile gamma/delta; p_oran (oranla harman) varsa gamma_oran/delta_oran",
                     "model_json": {"gamma_model": um.get("henery_gamma_model"), "delta_model": um.get("henery_delta_model"),
                                    "gamma_harman": um.get("henery_gamma"), "delta_harman": um.get("henery_delta")},
                     "sinama_log_loss": llo},
        "kurallar_kaynak": KAYNAKLAR,
        "varsayimlar": [
            "Plase: 7+ atlı koşuda ilk 2 (kalabalık alanda ilk 3 kuralı teyit edilemedi); 7'den az atlı koşuda plase yok.",
            "Plase'de ekürili atlar tek birim (Ganyan/Çifte kuralına benzetildi).",
            "İkili, Sıralı İkili, Sıralı Üçlü, Tabela'da ekürili atlar ayrı at.",
            "Sıralı Üçlü en az 4, Tabela en az 5 atlı koşu (kaynakta alt sınır yok).",
            "Çifte: aynı gün aynı hipodromda her ardışık koşu çifti (aynada çifte bayrağı yok).",
            "Eşit derece (dead heat) olan koşular ilgili türün geri testinden çıkarıldı (atlanan_esit_derece).",
            "Koşular bağımsız (Çifte, 6'lı): olasılık = koşu olasılıklarının çarpımı."],
        "dogrulama_ornegi": dogrulama_ornegi(gam, dlt),
        "turler": turler,
        "sure_sn": round(time.time() - t0, 1),
    }
    jyaz(KARNE, out)
    log(f"kupon_karne.json yazıldı ({os.path.getsize(KARNE) // 1024} KB, {out['sure_sn']} sn)")
    return out


def main():
    out = karne_guncelle()
    if not out:
        return
    for kod, d in out["turler"].items():
        print(f"{kod:13s} n={d['n']} isabet={d['isabet']} beklenen={d['beklenen']} | sınama {d['sinama']}")
        for s in d.get("seviyeler", []):
            print(f"    K={s['kombinasyon']:<4} n={s['n']} isabet={s['isabet']} beklenen={s['beklenen']} z={s.get('z')} | sınama {s['sinama']}")
        for s in d.get("kutu", []):
            print(f"    kutu {s['at']} at ({s['kombinasyon']}) isabet={s['isabet']} beklenen={s['beklenen']} z={s.get('z')} | sınama {s['sinama']}")


if __name__ == "__main__":
    main()
