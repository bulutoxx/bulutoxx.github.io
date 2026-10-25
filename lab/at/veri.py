# BULUTOXX at yarışı laboratuvarı — veri katmanı.
# Herkese açık aynayı (github.com/cenkozgur/tjk-data) yalnız OKUR. tjk.org'a hiçbir istek atmaz.
# Ham veri depoya kopyalanmaz: ayna çalışma anında ./_tjk-data altına sığ klonlanır (gitignore'da).
import json, os, re, unicodedata

KAYNAK = os.environ.get("AT_KAYNAK", "./_tjk-data")
AYNA_URL = "https://github.com/cenkozgur/tjk-data"

# Yalnız Türkiye hipodromları (yabancı simulcast koşularında at geçmişi yok, ayrı bir evren).
YERLI = {"İstanbul", "İzmir", "Bursa", "Adana", "Ankara", "Şanlıurfa", "Antalya", "Elazığ", "Kocaeli", "Diyarbakır"}


def ad(s):
    """İsimleri karşılaştırılabilir hale getirir (boşluk, büyük harf, Unicode biçimi)."""
    s = unicodedata.normalize("NFC", str(s or "")).strip()
    return re.sub(r"\s+", " ", s).upper()


def sure_sn(t):
    """'2.14.11' -> 134.11 sn ; '58.20' -> 58.2 ; okunamazsa None."""
    if not t or not isinstance(t, str):
        return None
    p = t.strip().split(".")
    try:
        if len(p) == 3:
            return int(p[0]) * 60 + int(p[1]) + int(p[2]) / 100.0
        if len(p) == 2:
            return int(p[0]) + int(p[1]) / 100.0
    except ValueError:
        return None
    return None


def sinif_anahtari(rc):
    return re.sub(r"\s*/.*", "", str(rc or "")).strip().upper() or "?"


def _kosu(r, sonuc=True):
    atlar = []
    for h in r.get("horses") or []:
        if h.get("nonRunner"):
            continue
        try:
            kilo = float(h.get("weight") or 0) or None
        except (TypeError, ValueError):
            kilo = None
        o = h.get("odds")
        try:
            o = float(o) if o else None
        except (TypeError, ValueError):
            o = None
        if o is not None and o <= 1.0:
            o = None
        atlar.append({
            "ad": ad(h.get("name")), "no": str(h.get("no") or ""), "jokey": ad(h.get("jockey")),
            "antrenor": ad(h.get("trainer")), "kilo": kilo, "yas": h.get("age") or None, "oran": o,
            "sira": (int(h["position"]) if sonuc and h.get("position") else None),
            "sure": sure_sn(h.get("finishTime")) if sonuc else None,
            "form": h.get("form"),
        })
    return {
        "tarih": r["date"], "kosu": int(r.get("raceNo") or 0), "hipodrom": r.get("venue") or "",
        "mesafe": int(r.get("distance") or 0), "pist": r.get("surface") or "", "sinif": r.get("raceClass") or "",
        "sinif_k": sinif_anahtari(r.get("raceClass")), "atlar": atlar,
        "saat": r.get("time"), "hava": r.get("weatherCondition"), "nem": r.get("humidity"),
    }


def sonuclari_yukle(kaynak=None):
    """Tüm sonuç dosyalarını okur; yerli, en az 2 koşan ve tek kazananı olan koşuları zaman sırasıyla döner."""
    d = os.path.join(kaynak or KAYNAK, "data", "results")
    out, atilan = [], {"yabanci": 0, "kazanansiz": 0, "az_at": 0}
    for f in sorted(os.listdir(d)):
        if not re.match(r"\d{4}-\d{2}-\d{2}\.json$", f):
            continue
        try:
            js = json.load(open(os.path.join(d, f), encoding="utf-8"))
        except Exception:
            continue
        for r in js:
            if r.get("venue") not in YERLI:
                atilan["yabanci"] += 1
                continue
            k = _kosu(r)
            if len(k["atlar"]) < 2:
                atilan["az_at"] += 1
                continue
            if sum(1 for a in k["atlar"] if a["sira"] == 1) != 1:
                atilan["kazanansiz"] += 1
                continue
            out.append(k)
    out.sort(key=lambda k: (k["tarih"], k["hipodrom"], k["kosu"]))
    return out, atilan


def program_yukle(tarih, kaynak=None):
    """data/daily/<tarih>.json (varsa) -> yerli koşu programları (sonuç alanları boş)."""
    f = os.path.join(kaynak or KAYNAK, "data", "daily", tarih + ".json")
    if not os.path.exists(f):
        return []
    try:
        js = json.load(open(f, encoding="utf-8"))
    except Exception:
        return []
    out = [_kosu(r, sonuc=False) for r in js if r.get("venue") in YERLI]
    return [k for k in out if len(k["atlar"]) >= 2]


def piyasa_q(oranlar):
    """Nihai ganyan oranından marjı ayrılmış olasılık. Eksik oran varsa None döner."""
    if not oranlar or any(o is None for o in oranlar):
        return None
    inv = [1.0 / o for o in oranlar]
    s = sum(inv)
    return [x / s for x in inv]


def kapsam(kosular):
    if not kosular:
        return {}
    hip = {}
    for k in kosular:
        hip[k["hipodrom"]] = hip.get(k["hipodrom"], 0) + 1
    return {"ilk_tarih": kosular[0]["tarih"], "son_tarih": kosular[-1]["tarih"], "kosu": len(kosular),
            "kosan_at": sum(len(k["atlar"]) for k in kosular),
            "tam_oranli_kosu": sum(1 for k in kosular if piyasa_q([a["oran"] for a in k["atlar"]])),
            "hipodrom": dict(sorted(hip.items(), key=lambda x: -x[1]))}
