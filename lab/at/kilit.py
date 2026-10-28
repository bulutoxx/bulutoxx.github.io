# OXXai at yarışı laboratuvarı — kilit ve piyasa (oran) olgunluk kapısı.
# 26 Ekim 2026 hatası: kilit 13:04 TSİ'de, aynanın 09:49'da yakaladığı programla atıldı. O saatte havuzda işlem görmeyen
# atların oranı 999.99 (yer tutucu) idi; veri katmanı bunu geçerli oran saydı, gece.kosu_tahmini de "alanın tamamında oran
# var" diye harmanladı (ör. Şanlıurfa 5: tek atta 1.05, 15 atta 999.99 -> o ata %96; sabah modeli %28).
# Kurallar (bu modül):
#  1) Sabah kilidi HER ZAMAN yalnız modeldir (mod "model"); kilide o anki geçerli oranlar ve yakalama zamanı yazılır (`oran_an`).
#  2) Piyasa harmanı (gün içi robot) yalnız kapı geçince: oran yakalandığında koşuya <= 15 dk kalmış, koşan atların >= %80'inde
#     geçerli oran (999.99 / boş / <= 1 geçersiz), toplam olasılık (sum 1/oran) 1,05-1,60. Geçmezse yalnız model.
#  3) Koruyucu: havuz küçük ya da bilinmiyorsa (ayna distributableAmount'u boş veriyor) hiçbir atın harman olasılığı modelden
#     0,40'tan fazla sapamaz.
#  4) Karne: piyasa moduyla kapısız atılmış eski kilitler `mod_hatali: true`; toplam hem "hariç" hem "dahil" tutulur.
import json, os
from datetime import datetime, timedelta, timezone

import numpy as np

ORAN_UST = 999.0          # >= bu değer: aynanın "henüz oran yok" yer tutucusu (999.99)
KAPI_DK = 15              # oran yakalandığında koşuya en çok kaç dakika kalmış olmalı
KAPSAM_MIN = 0.80         # koşan atların en az bu kadarında geçerli oran
OV_ALT, OV_UST = 1.05, 1.60
SAPMA_MAX = 0.40          # koruyucu: harman - model farkı (olasılık) üst sınırı
HAVUZ_MIN = 100000.0      # TL; bunun altında ya da bilinmiyorsa havuz "küçük" sayılır


def gecerli(o):
    """Geçerli ganyan oranı ya da None (boş, sayı değil, <= 1, >= 999 yer tutucu)."""
    try:
        o = float(o)
    except (TypeError, ValueError):
        return None
    return o if 1.0 < o < ORAN_UST else None


def _tsi(iso):
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=3))).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def yakalama_tablosu(t, kaynak=None):
    """data/daily/<t>.json -> {(hipodrom, koşu no): {"an": TSİ datetime|None, "havuz": float|None}}."""
    kaynak = kaynak or os.environ.get("AT_KAYNAK", "./_tjk-data")
    try:
        js = json.load(open(os.path.join(kaynak, "data", "daily", t + ".json"), encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for r in js:
        try:
            h = float(r.get("distributableAmount")) if r.get("distributableAmount") not in (None, "") else None
        except (TypeError, ValueError):
            h = None
        out[(r.get("venue"), int(r.get("raceNo") or 0))] = {"an": _tsi((r.get("snapshotRef") or {}).get("capturedAt")), "havuz": h}
    return out


def kapi(oranlar, tarih, saat, yakalama):
    """Oran olgunluk kapısı. yakalama: yakalama_tablosu() satırı (ya da None). Döner: kompakt sözlük, `gecti` bool."""
    n = len(oranlar)
    g = [gecerli(o) for o in oranlar]
    v = [o for o in g if o is not None]
    kapsam = len(v) / n if n else 0.0
    ov = sum(1.0 / o for o in v) if v else 0.0
    an = (yakalama or {}).get("an")
    kalan = None
    if an and saat:
        try:
            kalan = round((datetime.fromisoformat(f"{tarih} {saat}") - an).total_seconds() / 60)
        except ValueError:
            kalan = None
    d = {"gecti": False, "kapsam": round(kapsam, 2), "ov": round(ov, 3), "kalan_dk": kalan}
    if not v:
        d["neden"] = "geçerli oran yok"
    elif kalan is None:
        d["neden"] = "oran yakalama zamanı ya da koşu saati bilinmiyor"
    elif an.date().isoformat() != tarih:
        d["neden"] = "oran başka güne ait"
    elif kalan > KAPI_DK:
        d["neden"] = f"oran koşudan {kalan} dk önce (> {KAPI_DK})"
    elif kapsam < KAPSAM_MIN:
        d["neden"] = f"geçerli oran kapsamı %{round(100 * kapsam)} (< %{round(100 * KAPSAM_MIN)})"
    elif not (OV_ALT <= ov <= OV_UST):
        d["neden"] = f"toplam olasılık {ov:.2f} ({OV_ALT}-{OV_UST} dışı)"
    else:
        d["gecti"], d["neden"] = True, "geçti"
    return d


def koruyucu(p, p_model, havuz=None, sinir=SAPMA_MAX):
    """Havuz küçük/bilinmiyorsa her atın olasılığını modelin ±sinir bandına kırpar (yeniden ölçekleyerek).
    p, p_model aynı atlar için (p_model yeniden ölçeklenir). Döner: (p, kırpılan at sayısı)."""
    p = np.asarray(p, float).copy()
    if havuz is not None and havuz >= HAVUZ_MIN:
        return p, 0
    pm = np.asarray(p_model, float)
    pm = pm / pm.sum()
    alt, ust = np.clip(pm - sinir, 0.0, 1.0), np.clip(pm + sinir, 0.0, 1.0)
    kirp = int(np.sum((p < alt - 1e-9) | (p > ust + 1e-9)))
    if not kirp:
        return p, 0
    for _ in range(50):
        p = np.clip(p, np.maximum(alt, 1e-6), ust)
        p = p / p.sum()
        if np.all(p >= alt - 1e-4) and np.all(p <= ust + 1e-4):
            break
    return p, kirp


def oran_kaydi(atlar, yakalama):
    """Kilide yazılan kompakt oran anlık görüntüsü: t = aynanın yakalama zamanı (TSİ), o = yalnız geçerli oranlar."""
    an = (yakalama or {}).get("an")
    return {"t": an.strftime("%Y-%m-%dT%H:%M") if an else None,
            "o": {str(a["no"]): round(o, 2) for a in atlar for o in [gecerli(a.get("oran"))] if o is not None}}


def sabah_tahmini(kosu_tahmini, m, kosu, durum, yakalama):
    """Sabah kilidi: oranlar modele hiç verilmez (yalnız model); o anki oranlar yalnız kayda yazılır."""
    k0 = dict(kosu, atlar=[dict(a, oran=None) for a in kosu["atlar"]])
    kt = kosu_tahmini(m, k0, durum, "model")
    kt["mod"] = "model"
    kt["oran_an"] = oran_kaydi(kosu["atlar"], yakalama)
    return kt


# ---------------------------------------------------------------- karne
def mod_hatali(satir):
    """Piyasa içeren ama oran kapısından geçmemiş kilit (26 Ekim 2026 öncesi kod) -> True."""
    mod = str(satir.get("mod") or "")
    return ("piyasa" in mod and not mod.startswith("yalnız model")) and not satir.get("kapi_gecti")


KAL_KOVA = [0.0, 0.10, 0.20, 0.30, 0.50, 1.0001]   # karne kalibrasyon kovaları: %0–10, 10–20, 20–30, 30–50, 50+


def kal_kovalari(satir):
    pw = np.array([v for x in satir for v in x.get("pw") or []], float)
    out = []
    if not len(pw):
        return out
    for lo, hi in zip(KAL_KOVA[:-1], KAL_KOVA[1:]):
        m = (pw[:, 0] >= lo) & (pw[:, 0] < hi)
        out.append({"aralik": f"%{round(lo * 100)}–{round(min(hi, 1) * 100)}" if hi <= 1 else f"%{round(lo * 100)}+",
                    "at": int(m.sum()), "ort_tahmin": round(float(pw[m, 0].mean()), 4) if m.any() else None,
                    "gercek": round(float(pw[m, 1].mean()), 4) if m.any() else None})
    return out


def _ozet(satir):
    if not satir:
        return None
    pk = [x["log_loss"] for x in satir]
    i3 = [x["ilk3_tuttu"] for x in satir if "ilk3_tuttu" in x]
    return {"kosu": len(satir), "log_loss": round(float(np.mean(pk)), 4),
            "brier": round(float(np.mean([sum((p - y) ** 2 for p, y in x["pw"]) for x in satir if x.get("pw")])), 4)
            if any(x.get("pw") for x in satir) else None,
            "ilk_secim_isabet": round(float(np.mean([x["ilk_secim_tuttu"] for x in satir])), 4),
            "ilk3_isabet": round(float(np.mean(i3)), 4) if i3 else None, "ilk3_n": len(i3),
            "ikili_isabet": round(float(np.mean([x["ikili_tuttu"] for x in satir])), 4)}


def karne_ek(karne):
    """Karneyi yerinde işaretler (geçmiş silinmez): satırlara mod_hatali, gün özetine ve toplama 'hariç' sütunu."""
    for x in karne.get("kosular", []):
        if mod_hatali(x):
            x["mod_hatali"] = True
        else:
            x.pop("mod_hatali", None)
    canli = [x for x in karne.get("kosular", []) if x.get("kosudan_once", True)]
    for t, g in (karne.get("gunler") or {}).items():
        gs = [x for x in canli if x["kosu_id"].startswith(t + "/")]
        h = sum(1 for x in gs if x.get("mod_hatali"))
        g["mod_hatali"] = h
        g["haric"] = _ozet([x for x in gs if not x.get("mod_hatali")])
    karne["mod_hatali_sayisi"] = sum(1 for x in canli if x.get("mod_hatali"))
    temiz = [x for x in canli if not x.get("mod_hatali")]
    karne["toplam_haric"] = _ozet(temiz)
    # canlı karne (yayın ölçüsü): YALNIZ koşudan önce atılmış ve doğru modda kilitler; dışarıda kalanlar ayrıca sayılır
    t = _ozet(temiz)
    if t:
        t.update({"mod_hatali": 0, "gecikmeli_kilit": 0, "kovalar": kal_kovalari(temiz),
                  "not": "yalnız koşudan önce, oran kapısına uygun modda kilitlenmiş tahminler"})
    karne["toplam"] = t
    karne["toplam_tum"] = _ozet(karne.get("kosular", []))
    karne["disarida"] = {"mod_hatali": karne["mod_hatali_sayisi"],
                         "gecikmeli_kilit": sum(1 for x in karne.get("kosular", []) if not x.get("kosudan_once", True))}
    karne["mod_hatali_not"] = ("mod_hatali=true: 26 Ekim 2026 kilitleri erken havuz oranıyla (999.99 yer tutucuları geçerli "
                               "sayılarak) 'model+piyasa' modunda atıldı. 'toplam' bunları içerir, 'toplam_haric' içermez.")
    return karne


def karne_satirlari(karne):
    """RAPOR.md için iki sütunlu (etkilenenler hariç / dahil) canlı karne satırları."""
    dahil = _ozet([x for x in karne.get("kosular", []) if x.get("kosudan_once", True)])
    if not dahil:
        return ["- Henüz puanlanmış kilitli tahmin yok (sonuçlar aynaya düştükçe her gece puanlanır)."]
    haric = karne.get("toplam_haric")
    y = lambda v: "–" if v is None else f"%{100 * v:.1f}"
    s = lambda d, k, f: "–" if not d else f(d[k])
    L = [f"Koşudan önce kilitlenmiş tahminler. {karne.get('mod_hatali_sayisi', 0)} koşu `mod_hatali` (26 Ekim: erken havuz "
         "oranıyla 'model+piyasa' kilidi); geçmiş silinmedi, iki sütunda gösteriliyor.", "",
         "| | etkilenenler hariç | dahil |", "|---|---|---|",
         f"| koşu | {s(haric, 'kosu', str)} | {dahil['kosu']} |",
         f"| log-loss | {s(haric, 'log_loss', str)} | {dahil['log_loss']} |",
         f"| ilk seçim isabeti | {s(haric, 'ilk_secim_isabet', y)} | {y(dahil['ilk_secim_isabet'])} |",
         f"| ikili isabeti | {s(haric, 'ikili_isabet', y)} | {y(dahil['ikili_isabet'])} |", "",
         "| gün | hariç: koşu / LL / ilk seçim | dahil: koşu / LL / ilk seçim |", "|---|---|---|"]
    for t, g in sorted((karne.get("gunler") or {}).items())[-7:]:
        h = g.get("haric")
        L.append(f"| {t} | " + (f"{h['kosu']} / {h['log_loss']} / {y(h['ilk_secim_isabet'])}" if h else "– (hepsi etkilendi)")
                 + f" | {g['kosu']} / {g['log_loss']} / {y(g['ilk_secim_isabet'])} |")
    return L
