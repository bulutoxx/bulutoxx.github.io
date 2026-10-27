#!/usr/bin/env python3
"""🩹 Kadro sinyali toplayıcı: ilk 11 / sakat / cezalı (API-Football ücretsiz katman, günde 100 istek; anahtar APISPORTS_KEY).

İlke: HAM VERİ YAYINLANMAZ. API yanıtları ve oyuncu düzeyindeki birikim (kimlik → ilk 11 sayısı) yalnız iş akışının
önbelleğinde (actions/cache; KADRO_ONBELLEK, varsayılan .kadro_onbellek/, .gitignore'da) durur. Depoya ve siteye yalnız
maç başına türetilmiş özet girer: data/kadro.json
  {"mac": {"lg|tarih|ev|dep": {"ev": [eksik, kilit_eksik, kayip], "dep": [...], "ilk11": 0|1, "t": "…Z"}}, "durum": {...}}
    eksik       : sakat/cezalı listesinde "Missing Fixture" olan oyuncu sayısı
    kilit_eksik : bunlardan son maçlarda ilk 11 payı ≥ KILIT_PAY olanlar (ilk 11 açıklandıysa: kilit oyuncunun ilk 11 dışında kalması)
    kayip       : tahmini güç kaybı = Σ(eksik kilit oyuncunun ilk 11 payı) × KAYIP_KATSAYI (gol beklentisi oranı; kapı öğrenir)
Bütçe (UTC günü, API sıfırlaması 00:00 UTC): GUNLUK_TAVAN (varsayılan 90 / 100). Sıra:
  1) günde bir: /fixtures?date=bugün ve yarın (eşleme; 2 istek)
  2) 6 saatte bir: /injuries?date=bugün (+ yarın günde bir)
  3) önce Altın aday ve en yüksek güvenli maçlar: başlama saatine ≤75 dk kalan maçlar için /fixtures?ids= (20'lik paket; ilk 11)
  4) kalan bütçe: biten öncelikli maçların ilk 11'i (/fixtures?ids=, 20'lik) → kilit oyuncu birikimi
Dakika sınırı için istekler arası ARALIK_SN bekler. Hata gövdesi (errors) varsa durur, durumu yazar; çıkış kodu 0 (bilgi adımı).
Ağ / anahtar yoksa sessizce atlar. tjk.org / atyarisi.com'a istek atılmaz; yalnız v3.football.api-sports.io.

  python3 scripts/kadro.py              # iş akışında (anahtar ortamdan)
  python3 scripts/kadro.py --kuru       # istek atmadan plan
Laboratuvar sınaması: lab/kadro_test.py (sahte yanıtlarla).
"""
import argparse, collections, json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CIKTI = os.path.join(DATA, "kadro.json")
ONBELLEK = os.environ.get("KADRO_ONBELLEK") or os.path.join(ROOT, ".kadro_onbellek")
API = "https://v3.football.api-sports.io"
GUNLUK_TAVAN = int(os.environ.get("KADRO_TAVAN", "90"))
CALISMA_TAVAN = int(os.environ.get("KADRO_CALISMA_TAVAN", "14"))
YEDEK_TAVAN = int(os.environ.get("KADRO_YEDEK", "40"))   # gün içinde sonra başlayacak maçların ilk 11'i için ayrılan istek   # tek çalışmada en çok istek (saatlik iş; günü dengeler)
ARALIK_SN = float(os.environ.get("KADRO_ARALIK", "6.5"))            # ücretsiz katman dakikada ~10 istek
KILIT_PAY, KILIT_MIN_MAC = 0.6, 4
KAYIP_KATSAYI = 0.05     # kilit oyuncu başına (ilk 11 payı 1 iken) gol beklentisi kaybı; başlangıç tahmini, kapı öğrenir
SAKLA_GUN = 4


def simdi(): return datetime.now(timezone.utc)
def z(t): return t.strftime("%Y-%m-%dT%H:%MZ")


def jl(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def jw(p, o, kisa=True):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, separators=(",", ":") if kisa else None, indent=None if kisa else 1)
    os.replace(tmp, p)


# ------------------------------------------------------------------ istek katmanı (sınamada değiştirilir)
class Durdur(Exception):
    pass


class Istemci:
    def __init__(self, anahtar, durum, kuru=False):
        self.anahtar, self.D, self.kuru = anahtar, durum, kuru
        self.calisma = 0; self._son = 0.0

    def kalan(self):
        return min(GUNLUK_TAVAN - self.D["istek_bugun"], CALISMA_TAVAN - self.calisma)

    def al(self, yol, **prm):
        if self.kalan() <= 0: raise Durdur("bütçe")
        if self.kuru:
            self.calisma += 1; self.D["istek_bugun"] += 1; return {"response": []}
        bekle = ARALIK_SN - (time.time() - self._son)
        if bekle > 0: time.sleep(bekle)
        url = f"{API}/{yol}?" + urllib.parse.urlencode(prm)
        req = urllib.request.Request(url, headers={"x-apisports-key": self.anahtar, "User-Agent": "OXXai-kadro/1"})
        self.calisma += 1; self.D["istek_bugun"] += 1; self._son = time.time()
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                j = json.loads(r.read().decode("utf-8"))
                kal = r.headers.get("x-ratelimit-requests-remaining")
                if kal is not None:
                    try: self.D["api_kalan"] = int(kal)
                    except ValueError: pass
        except Exception as e:
            self.D["son_hata"] = f"{z(simdi())} {yol}: {e.__class__.__name__}"
            raise Durdur("ağ")
        err = j.get("errors")
        if err and (isinstance(err, dict) and err or isinstance(err, list) and len(err)):
            msg = json.dumps(err, ensure_ascii=False)[:200]
            self.D["son_hata"] = f"{z(simdi())} {yol}: {msg}"
            if "limit" in msg.lower() or "request" in msg.lower(): self.D["istek_bugun"] = GUNLUK_TAVAN
            raise Durdur("api")
        return j


# ------------------------------------------------------------------ eşleme ve öncelik
def _sim():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import iddaa as ID
    return ID.sim


def mac_anahtari(f): return f"{f['lg']}|{f['d']}|{f['h']}|{f['a']}"


def baslama_ts(f):
    try:
        from zoneinfo import ZoneInfo
        hh, mm = (f.get("t") or "12:00").split(":")[:2]
        return datetime.fromisoformat(f["d"]).replace(hour=int(hh), minute=int(mm), tzinfo=ZoneInfo("Europe/London")).timestamp()
    except Exception:
        return None


def guven(f):
    """Öncelik puanı: Altın aday (≥0,78) önce; sonra en yüksek güven. kp (topluluk) > pz > piyasa."""
    c = []
    if isinstance(f.get("kp"), list): c += f["kp"]
    pz = f.get("pz") or {}
    for k in ("1", "X", "2", "U25", "A25"):
        if isinstance(pz.get(k), (int, float)): c.append(pz[k])
    if isinstance(f.get("odds"), list) and len(f["odds"]) == 3:
        inv = [1 / o for o in f["odds"]]; s = sum(inv); c += [x / s for x in inv]
    p = max(c) if c else 0.0
    return (1 if p >= .78 else 0, p)


def esle(fx, api_fx, sim):
    """Bizim fikstür ↔ API-Football fikstür kimliği. Başlama saati ±3 sa ve iki takım adı benzerliği."""
    by_gun = collections.defaultdict(list)
    for a in api_fx:
        by_gun[a["d"]].append(a)
    out = {}
    kullanilan = set()
    for f in fx:
        t = baslama_ts(f)
        best, bs = None, 0
        for gun in {f["d"], (datetime.fromisoformat(f["d"]) + timedelta(days=1)).date().isoformat(),
                    (datetime.fromisoformat(f["d"]) - timedelta(days=1)).date().isoformat()}:
            for a in by_gun.get(gun, []):
                if a["id"] in kullanilan: continue
                if t and a.get("ts") and abs(a["ts"] - t) > 3 * 3600: continue
                sh, sa = sim(f["h"], a["h"]), sim(f["a"], a["a"])
                if min(sh, sa) < 0.55 or sh + sa < 1.4: continue
                if sh + sa > bs: best, bs = a, sh + sa
        if best:
            kullanilan.add(best["id"]); out[mac_anahtari(f)] = {"id": best["id"], "ts": best.get("ts"), "th": best["th"], "ta": best["ta"]}
    return out


# ------------------------------------------------------------------ türetme
def ilk11_paket(I, OB, ids, durum):
    """20'lik /fixtures?ids= paketi; ücretsiz plan 'ids' açmıyorsa maç başı /fixtures/lineups'a düşer."""
    if not ids: return
    if not OB.get("ids_yok"):
        try:
            j = I.al("fixtures", ids="-".join(str(x) for x in ids))
            ilk11_isle(OB, j.get("response") or []); return
        except Durdur as e:
            if str(e) == "api" and "Ids" in (I.D.get("son_hata") or ""):
                OB["ids_yok"] = True; I.D["son_hata"] = None
            else: raise
    for x in ids:
        if I.kalan() <= 2: break
        j = I.al("fixtures/lineups", fixture=x)
        ilk11_isle(OB, [{"fixture": {"id": x, "date": "", "status": {"short": durum}}, "lineups": j.get("response") or []}])


def ilk11_isle(OB, fx_yanit):
    """/fixtures?ids= yanıtındaki ilk 11'leri takım→oyuncu ilk 11 sayısına işle (yalnız önbellek; kimlikler, ad yok)."""
    T = OB.setdefault("takim", {})
    yeni = 0
    for r in fx_yanit:
        fid = str(((r.get("fixture") or {}).get("id")))
        if fid in OB.setdefault("islenen", {}): continue
        lu = r.get("lineups") or []
        if len(lu) < 2: continue
        for L in lu:
            tid = str(((L.get("team") or {}).get("id")))
            st = T.setdefault(tid, {"mac": 0, "o": {}})
            st["mac"] += 1
            for x in L.get("startXI") or []:
                pid = str(((x.get("player") or {}).get("id")))
                if pid and pid != "None": st["o"][pid] = st["o"].get(pid, 0) + 1
        OB["islenen"][fid] = (r.get("fixture") or {}).get("date", "")[:10]
        if ((r.get("fixture") or {}).get("status") or {}).get("short") in ("NS", "TBD"):
            OB.setdefault("ilk11_mac", {})[fid] = {str(((L.get("team") or {}).get("id"))): [str(((x.get("player") or {}).get("id"))) for x in L.get("startXI") or []] for L in lu}
            # maç öncesi açıklanan ilk 11 sayılır ama aynı maç bitince ikinci kez sayılmasın diye islenen'de kalır
        yeni += 1
    return yeni


def pay(OB, tid, pid):
    st = (OB.get("takim") or {}).get(str(tid))
    if not st or st["mac"] < KILIT_MIN_MAC: return None
    return st["o"].get(str(pid), 0) / st["mac"]


def ozet_takim(OB, tid, sakat, ilk11=None):
    """sakat: [oyuncu_id] (Missing Fixture); ilk11: [oyuncu_id] ya da None. Dönüş: [eksik, kilit_eksik, kayip]."""
    eksik = len(set(sakat)); kilit = 0; kay = 0.0
    ad = set(sakat)
    if ilk11:     # ilk 11 açıklandıysa: ilk 11'de olmayan kilit oyuncular (sakat, cezalı ya da rotasyon)
        st = (OB.get("takim") or {}).get(str(tid)) or {"mac": 0, "o": {}}
        if st["mac"] >= KILIT_MIN_MAC:
            ad = {p for p, c in st["o"].items() if c / st["mac"] >= KILIT_PAY} - set(ilk11)
    for p in ad:
        s = pay(OB, tid, p)
        if s is not None and s >= KILIT_PAY: kilit += 1; kay += s
    return [eksik, kilit, round(kay * KAYIP_KATSAYI, 4)]


# ------------------------------------------------------------------ ana akış
def calis(kuru=False, istemci=None, fx=None, an=None):
    an = an or simdi()
    os.makedirs(ONBELLEK, exist_ok=True)
    OBp = os.path.join(ONBELLEK, "durum.json")
    OB = jl(OBp, {}) or {}
    gun = an.date().isoformat()
    D = OB.setdefault("butce", {})
    if D.get("gun") != gun: D.update({"gun": gun, "istek_bugun": 0}); D.pop("son_hata", None)
    cik = jl(CIKTI, {}) or {}
    cik.setdefault("mac", {})
    anahtar = os.environ.get("APISPORTS_KEY", "").strip()
    if not anahtar and istemci is None and not kuru:
        cik["durum"] = {"guncelleme": z(an), "not": "APISPORTS_KEY tanımlı değil; atlandı"}
        jw(CIKTI, cik); print("kadro: anahtar yok, atlandı"); return 0
    I = istemci or Istemci(anahtar, D, kuru)
    I.D = D
    fx = fx if fx is not None else (jl(os.path.join(DATA, "fixtures.json"), []) or [])
    now_ts = an.timestamp()
    fx = [f for f in fx if f.get("lg") and f.get("d") and baslama_ts(f) and baslama_ts(f) > now_ts - 4 * 3600]
    sim = _sim()
    nedeni = None
    try:
        # 1) eşleme listesi: günde bir bugün + yarın
        AF = OB.setdefault("api_fx", {})
        for g in (gun, (an + timedelta(days=1)).date().isoformat()):
            if AF.get(g, {}).get("alindi") == gun: continue
            j = I.al("fixtures", date=g, timezone="UTC")
            L = []
            for r in j.get("response") or []:
                fxx = r.get("fixture") or {}; tm = r.get("teams") or {}
                L.append({"id": fxx.get("id"), "ts": fxx.get("timestamp"), "d": (fxx.get("date") or g)[:10],
                          "h": (tm.get("home") or {}).get("name", ""), "a": (tm.get("away") or {}).get("name", ""),
                          "th": (tm.get("home") or {}).get("id"), "ta": (tm.get("away") or {}).get("id")})
            AF[g] = {"alindi": gun, "m": L}
        api_list = [a for g in AF.values() for a in g.get("m", [])]
        ES = OB.setdefault("esleme", {})
        ES.update(esle([f for f in fx if mac_anahtari(f) not in ES], api_list, sim))
        # 2) sakat / cezalı: bugün 6 saatte bir, yarın günde bir
        INJ = OB.setdefault("sakat", {})
        for g, aralik in ((gun, 6 * 3600), ((an + timedelta(days=1)).date().isoformat(), 24 * 3600)):
            son = INJ.get(g, {}).get("ts", 0)
            if now_ts - son < aralik: continue
            j = I.al("injuries", date=g)
            byfx = collections.defaultdict(lambda: collections.defaultdict(list))
            for r in j.get("response") or []:
                if ((r.get("player") or {}).get("type") or "") != "Missing Fixture": continue
                fid = str(((r.get("fixture") or {}).get("id"))); tid = str(((r.get("team") or {}).get("id")))
                byfx[fid][tid].append(str(((r.get("player") or {}).get("id"))))
            INJ[g] = {"ts": now_ts, "fx": {k: dict(v) for k, v in byfx.items()}}
        # 3) yaklaşan öncelikli maçların ilk 11'i (başlamaya ≤75 dk)
        sira = sorted(fx, key=lambda f: guven(f), reverse=True)
        yakin = [ES[mac_anahtari(f)]["id"] for f in sira if mac_anahtari(f) in ES
                 and 0 <= (ES[mac_anahtari(f)].get("ts") or baslama_ts(f)) - now_ts <= 75 * 60
                 and str(ES[mac_anahtari(f)]["id"]) not in (OB.get("ilk11_mac") or {})]
        for i in range(0, len(yakin), 20):
            if I.kalan() <= 2: break
            ilk11_paket(I, OB, yakin[i:i + 20], "NS")
        # 4) kalan bütçe: biten öncelikli maçların ilk 11'i (kilit oyuncu birikimi)
        biten = [ES[k]["id"] for k in sorted(ES, key=lambda k: -(ES[k].get("ts") or 0))
                 if ES[k].get("ts") and now_ts - ES[k]["ts"] > 2.5 * 3600 and str(ES[k]["id"]) not in OB.get("islenen", {})]
        # Akşam maçlarının ilk 11'i için gün sonuna kadar yedek bırak (biten maçlar yedeğe dokunamaz)
        gun_sonu = datetime(an.year, an.month, an.day, tzinfo=timezone.utc).timestamp() + 86400
        sonraki = sum(1 for k in ES if ES[k].get("ts") and now_ts + 75 * 60 < ES[k]["ts"] < gun_sonu
                      and str(ES[k]["id"]) not in (OB.get("ilk11_mac") or {}))
        yedek = min(YEDEK_TAVAN, sonraki)
        D["yedek"] = yedek
        biten = biten[:max(0, GUNLUK_TAVAN - D["istek_bugun"] - yedek - 2)] if OB.get("ids_yok") else biten
        for i in range(0, len(biten), 20):
            if I.kalan() <= 2 or GUNLUK_TAVAN - D["istek_bugun"] - yedek <= 2: break
            ilk11_paket(I, OB, biten[i:i + 20], "FT")
    except Durdur as e:
        nedeni = str(e)
    # türetilmiş özet (yalnız sayılar; oyuncu kimliği / adı yazılmaz)
    INJ = OB.get("sakat", {}); ES = OB.get("esleme", {}); L11 = OB.get("ilk11_mac", {})
    n_yaz = 0
    for f in fx:
        k = mac_anahtari(f); e = ES.get(k)
        if not e: continue
        fid = str(e["id"])
        sak = next((v["fx"].get(fid) for v in INJ.values() if fid in v.get("fx", {})), None) or {}
        l11 = L11.get(fid)
        if not sak and not l11: continue
        th, ta = str(e["th"]), str(e["ta"])
        cik["mac"][k] = {"ev": ozet_takim(OB, th, sak.get(th, []), (l11 or {}).get(th)),
                         "dep": ozet_takim(OB, ta, sak.get(ta, []), (l11 or {}).get(ta)),
                         "ilk11": 1 if l11 else 0, "t": z(an), "bt": int(e.get("ts") or baslama_ts(f) or 0)}
        n_yaz += 1
    sinir = (an - timedelta(days=SAKLA_GUN)).date().isoformat()
    cik["mac"] = {k: v for k, v in cik["mac"].items() if k.split("|")[1] >= sinir}
    for g in [g for g in list(INJ) if g < sinir]: INJ.pop(g, None)
    for g in [g for g in list(OB.get("api_fx", {})) if g < sinir]: OB["api_fx"].pop(g, None)
    OB["esleme"] = {k: v for k, v in ES.items() if k.split("|")[1] >= sinir}
    OB["islenen"] = {k: v for k, v in (OB.get("islenen") or {}).items() if v >= (an - timedelta(days=60)).date().isoformat()}
    OB["ilk11_mac"] = {k: v for k, v in L11.items() if k in OB["islenen"]}
    cik["durum"] = {"guncelleme": z(an), "istek_bugun": D["istek_bugun"], "tavan": GUNLUK_TAVAN, "bu_calisma": I.calisma, "yedek": D.get("yedek"),
                    "eslesen_mac": len(OB["esleme"]), "takim_birikimi": len(OB.get("takim", {})),
                    "kilit_hazir_takim": sum(1 for s in (OB.get("takim") or {}).values() if s["mac"] >= KILIT_MIN_MAC),
                    "ozet_yazilan": n_yaz, "durma_nedeni": nedeni, "son_hata": D.get("son_hata"),
                    "aciklama": "Türetilmiş kadro özeti (ham API verisi yayınlanmaz). ev/dep = [eksik, kilit_eksik, tahmini_kayip]."}
    if not kuru:
        jw(OBp, OB); jw(CIKTI, cik)
    print(f"kadro: {I.calisma} istek (bugün {D['istek_bugun']}/{GUNLUK_TAVAN}), {len(OB['esleme'])} eşleşme, {n_yaz} maç özeti"
          + (f", durdu: {nedeni}" if nedeni else ""))
    return 0


def predlog_isle(plog, now=None):
    """Kilitli tahmin kaydına maç başlamadan önceki son kadro özetini ekler (p kilitli kalır; kd ayrı alan, kapı sınaması için)."""
    K = (jl(CIKTI, {}) or {}).get("mac") or {}
    if not K: return 0
    now = now or simdi(); n = 0
    for e in plog:
        if e.get("r") is not None: continue
        k = K.get(e.get("id"))
        if not k: continue
        t = k.get("bt")
        if not t or t < now.timestamp() - 600: continue      # yalnız maç başlamadan önce (10 dk tolerans: saatlik iş gecikmesi değil, saat farkı)
        e["kd"] = k["ev"] + k["dep"] + [k.get("ilk11", 0)]; e["kdt"] = k.get("t"); n += 1
    return n


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--kuru", action="store_true")
    ar = ap.parse_args()
    try:
        return calis(kuru=ar.kuru)
    except Exception as e:
        import traceback; traceback.print_exc()
        print("kadro toplayıcı hata:", e.__class__.__name__); return 1


if __name__ == "__main__":
    sys.exit(main())
