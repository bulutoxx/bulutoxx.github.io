"""🧾 Sonuç eşleme (futbol kilitli tahmin günlüğü): sezon verisinde sonucu olmayan maçlar iddaa sonuçlarından tamamlanır.

Neden: football-data / ESPN bazı ligleri (İngiltere 3.–5. lig, İtalya, İskoçya … hafta içi turları) birkaç gün geç yayınlıyor;
o maçların kilitli tahmini (data/predlog.json) r alanı olmadan bekliyor, karneye girmiyordu (27 Ekim: 29 maç).

Kaynaklar (sırayla, ikisi de ücretsiz):
  1) toplayıcı arşivi data/archive/GGGG-AA-GG.json — iddaa kimliği, takım adları (h/a), başlama ts, biten maçta hs/as, h1/a1
     (collector.py zaten live-results'tan doldurur; ağ gerekmez)
  2) https://statisticsv2.iddaa.com/live-results?sportId=1&date=GGGG-AA-GG (collector.py'nin kullandığı uç nokta):
     events[{eventId, phase, homeTeam, awayTeam, eventDate}], sc{id: {ht: {c, ht}, at: {c, ht}}}; phase 2 = bitti.
Eşleme: kilit kaydında iid varsa doğrudan; yoksa takım adı benzerliği (iddaa.sim; merge_iddaa ile aynı eşik: ikisi ≥ 0,55 ve
toplam ≥ 1,45) + tarih (maç günü ±1, İngiltere/Türkiye saat farkı). Tek aday şartı: en iyi ikinciden belirgin üstün olmalı.
Yalnız r (tam skor), varsa rh (ilk yarı) ve rs = "iddaa" (sonuç kaynağı) yazılır; p ve diğer kilit alanları değişmez.
Son GERI_GUN gün (bugün hariç). Sezon verisi sonradan gelirse r zaten dolu olduğundan dokunulmaz.
"""
import json, os, re, urllib.request
from datetime import date, datetime, timedelta, timezone

GERI_GUN = 7
URL = "https://statisticsv2.iddaa.com/live-results?sportId=1&date={}"
ESIK_TEK, ESIK_TOP, FARK = 0.55, 1.45, 0.15


def _ag_getir(d):
    import iddaa as ID
    req = urllib.request.Request(URL.format(d), headers=ID.UA)
    return json.loads(urllib.request.urlopen(req, timeout=40).read().decode("utf-8"))


def _uk_gun(ts):
    try:
        from zoneinfo import ZoneInfo
        return datetime.fromtimestamp(float(ts), ZoneInfo("Europe/London")).date().isoformat()
    except Exception: return None


def adaylar_arsiv(DATA, gunler):
    out = []
    for g in gunler:
        try: A = json.load(open(os.path.join(DATA, "archive", f"{g}.json"), encoding="utf-8"))
        except Exception: continue
        for k, r in A.items():
            if not isinstance(r, dict) or r.get("hs") is None or r.get("as") is None: continue
            rh = [int(r["h1"]), int(r["a1"])] if r.get("h1") is not None and r.get("a1") is not None else None
            out.append({"iid": str(k), "h": r.get("h") or "", "a": r.get("a") or "", "d": _uk_gun(r["ts"]) if r.get("ts") else g,
                        "r": [int(r["hs"]), int(r["as"])], "rh": rh, "kay": "arsiv"})
    return out


def adaylar_canli(gunler, getir=None):
    getir = getir or _ag_getir; out = []; hata = 0
    for g in gunler:
        try: data = (getir(g) or {}).get("data") or {}
        except Exception as ex:
            hata += 1; print("iddaa sonuç alınamadı", g, ex.__class__.__name__, flush=True); continue
        sc = data.get("sc") or {}
        for ev in data.get("events") or []:
            if ev.get("phase") != 2: continue
            k = str(ev.get("eventId")); s = sc.get(k) or {}
            ht, at = s.get("ht") or {}, s.get("at") or {}
            if ht.get("c") is None or at.get("c") is None: continue
            rh = [int(ht["ht"]), int(at["ht"])] if ht.get("ht") is not None and at.get("ht") is not None else None
            out.append({"iid": k, "h": ev.get("homeTeam") or "", "a": ev.get("awayTeam") or "",
                        "d": _uk_gun(ev["eventDate"]) if ev.get("eventDate") else g, "r": [int(ht["c"]), int(at["c"])], "rh": rh, "kay": "canli"})
    return out, hata


_GENC = re.compile(r"\((k|w)\)|\bu ?(17|18|19|20|21|23)\b|\b(ii|b|res|reserves?|women|kad[ıi]n)\b", re.I)


def _benzer(sim):
    """iddaa.sim + tam kelime kuralı ("AIK" ~ "AIK Solna": kısa adın tüm kelimeleri uzun adda)."""
    def f(a, b):
        r = sim(a, b)
        x, y = set(re.split(r"[^a-z0-9]+", a.lower())) - {""}, set(re.split(r"[^a-z0-9]+", b.lower())) - {""}
        if x and y and (x <= y or y <= x) and min(len(" ".join(x)), len(" ".join(y))) >= 3: r = max(r, 0.8)
        return r
    return f


def _esle(e, C, sim):
    if e.get("iid") is not None:
        for c in C:
            if c["iid"] == str(e["iid"]): return c
    d0 = date.fromisoformat(e["d"]); sk = []
    for c in C:
        try:
            if abs((date.fromisoformat(c["d"]) - d0).days) > 1: continue
        except Exception: continue
        sh, sa = sim(e["h"], c["h"]), sim(e["a"], c["a"])
        if min(sh, sa) < ESIK_TEK or sh + sa < ESIK_TOP: continue
        sk.append((sh + sa + (0.2 if c["d"] == e["d"] else 0), c))
    if not sk:   # 2. kademe: bir takım çok benzer (≥ 0,9), öteki zayıf (≥ 0,3) — "Ind. Rivadavia" ~ "Ind. Mendoza"; genç/kadın/yedek takımı değil
        for c in C:
            try:
                if abs((date.fromisoformat(c["d"]) - d0).days) > 1: continue
            except Exception: continue
            if bool(_GENC.search(c["h"] + " " + c["a"])) != bool(_GENC.search(e["h"] + " " + e["a"])): continue
            sh, sa = sim(e["h"], c["h"]), sim(e["a"], c["a"])
            if max(sh, sa) >= 0.9 and min(sh, sa) >= 0.3: sk.append((sh + sa - 1 + (0.2 if c["d"] == e["d"] else 0), c))
        if len(sk) != 1: return None
    sk.sort(key=lambda x: -x[0])
    if len(sk) > 1 and sk[0][1]["iid"] != sk[1][1]["iid"] and sk[0][0] - sk[1][0] < FARK: return None   # belirsiz
    return sk[0][1]


def tamamla(plog, today, DATA, cevrimici=True, getir=None, sim=None):
    """plog içinde (yerinde) r alanını doldurur. Dönüş: özet sözlüğü."""
    if sim is None:
        import iddaa as ID
        sim = ID.sim
    sim = _benzer(sim)
    bas = (today - timedelta(days=GERI_GUN)).isoformat(); bug = today.isoformat()
    bek = [e for e in plog if e.get("r") is None and bas <= e.get("d", "") < bug]
    oz = {"bekleyen": len(bek), "arsiv": 0, "canli": 0, "kalan": 0}
    if not bek: return oz
    gunler = sorted({(date.fromisoformat(e["d"]) + timedelta(days=k)).isoformat() for e in bek for k in (-1, 0, 1)})
    gunler = [g for g in gunler if g <= bug]
    C = adaylar_arsiv(DATA, gunler)
    kalan = []
    for e in bek:
        c = _esle(e, C, sim)
        if c: _yaz(e, c); oz["arsiv"] += 1
        else: kalan.append(e)
    if kalan and cevrimici:
        gk = sorted({(date.fromisoformat(e["d"]) + timedelta(days=k)).isoformat() for e in kalan for k in (0, 1)})
        C2, oz["ag_hata"] = adaylar_canli([g for g in gk if g <= bug], getir)
        k2 = []
        for e in kalan:
            c = _esle(e, C2, sim)
            if c: _yaz(e, c); oz["canli"] += 1
            else: k2.append(e)
        kalan = k2
    oz["kalan"] = len(kalan)
    return oz


def _yaz(e, c):
    e["r"] = list(c["r"]); e["rs"] = "iddaa"
    if c.get("rh") and c["rh"][0] <= c["r"][0] and c["rh"][1] <= c["r"][1]: e["rh"] = list(c["rh"])
