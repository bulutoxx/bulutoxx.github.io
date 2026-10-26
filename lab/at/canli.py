# BULUTOXX at yarışı laboratuvarı — GÜN İÇİ (canlı) robot.
# Yarış günü her 30 dakikada bir çalışır (at-canli.yml):
#  1) Aynayı (yalnız github.com/cenkozgur/tjk-data) sığ günceller; tjk.org'a / atyarisi.com'a istek YOK.
#  2) Kayıtlı yayın modelini yükler (yeniden eğitim YOK) ve bugünün (varsa yarının) koşuları için yalnız koşu
#     gününden ÖNCEKİ sonuçlarla durum kurar (sızıntısız; gece akışıyla aynı ozellik kodu).
#  3) p_sabah (yalnız model) + aynada güncel ganyan oranı varsa p_piyasa (marjı ayrılmış) ve p_oran (yayın harmanı,
#     gece ile aynı α/β) + indirimli Harville ilk-3 olasılıkları.
#  4) Sonucu aynaya düşen koşuları aynı akşam puanlar: data/at/canli/<tarih>.json içinde `sonuc`; sabah kilitli
#     tahminler (data/at/tahmin) gece.puanla ile karneye eklenir (kosu_id ile idempotent, çift sayım yok).
#  5) 6'lı ganyan (lab/at/altili.py): o günün 6'lılarını güncel p'lerle data/at/altili/<tarih>.json'a yazar; ilk ayak
#     başlayınca kupon kilitlenir, sonuçlar geldikçe ayak ayak puanlanır; altili_karne.json'un canlı bölümü tazelenir.
#  6) Oran izi: koşu öncesi ganyan oranlarını zaman damgalı biriktirir (data/at/oran_izi/<tarih>.json; yalnız değişince
#     yeni nokta, en çok son 2 gün). Arayüz koşu kartında ve at profilinde mini çizgi olarak gösterir.
# Depoya yalnız türetilmiş çıktılar yazılır (olasılıklar + koşu/at bilgisi özetleri); ham ayna dosyası yazılmaz.
import argparse, json, math, os, sys, time
from collections import defaultdict, deque
from datetime import date, datetime, timedelta, timezone

import numpy as np

BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import gece  # noqa: E402  (AT_KAYNAK varsayılanını da ayarlar)
import veri, ozellik, model as M  # noqa: E402
import altili  # noqa: E402  (6'lı ganyan: data/at/altili/<gün>.json)

CANLI = os.path.join(gece.CIKTI, "canli")
KAYNAK_ATIF = "açık TJK sonuç arşivi (github.com/cenkozgur/tjk-data)"


def tsi_simdi():
    return datetime.now(timezone.utc) + timedelta(hours=3)


def _r4(v):
    return None if v is None else round(float(v), 4)


def _sayi(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


# ---------------------------------------------------------------- durum (yalnız geçmiş)
class Gecmis:
    """Sonuçları gün gün ileri saran durum: özellik durumu (ozellik.Durum) + atların son 3 koşusu.
    tablo_kur ile aynı güncelleme sırası (gün içindeki tüm koşular, sonra gun_sonu) ama özellik matrisi kurulmaz."""

    def __init__(self, kosular):
        self.kosular, self.i = kosular, 0
        self.durum = ozellik.Durum()
        self.son = defaultdict(lambda: deque(maxlen=3))

    def ilerlet(self, bitis):
        """tarih < bitis olan tüm günleri işler."""
        K = self.kosular
        while self.i < len(K) and K[self.i]["tarih"] < bitis:
            t = K[self.i]["tarih"]
            j = self.i
            while j < len(K) and K[j]["tarih"] == t:
                j += 1
            for k in K[self.i:j]:
                self.durum.guncelle(k)
                for a in k["atlar"]:
                    self.son[a["ad"]].append({"tarih": k["tarih"], "hipodrom": k["hipodrom"], "mesafe": k["mesafe"],
                                              "pist": k["pist"], "sira": a["sira"]})
            self.durum.gun_sonu()
            self.i = j

    def son3(self, ad_):
        return list(reversed(self.son.get(ad_, [])))   # en yeni önce


# ---------------------------------------------------------------- sonuçlar (gün içi)
def gun_sonuclari(tarih, kaynak):
    """data/results/<tarih>.json -> {(hipodrom, koşu no): {...}}; yalnız yerli hipodromlar."""
    f = os.path.join(kaynak, "data", "results", tarih + ".json")
    out = {}
    try:
        js = json.load(open(f, encoding="utf-8"))
    except Exception:
        return out
    for r in js:
        if r.get("venue") not in veri.YERLI:
            continue
        kos = [h for h in r.get("horses") or [] if not h.get("nonRunner") and h.get("position")]
        try:
            kos.sort(key=lambda h: int(h["position"]))
        except (TypeError, ValueError):
            continue
        if not kos or int(kos[0]["position"]) != 1:
            continue
        kaz = kos[0]
        poz = [int(h["position"]) for h in kos[:4]]
        out[(r["venue"], int(r.get("raceNo") or 0))] = {
            "sira": [str(h.get("no") or "") for h in kos[:4]], "kazanan": str(kaz.get("no") or ""),
            "kazanan_ad": veri.ad(kaz.get("name")), "ganyan": _sayi(kaz.get("odds")),
            # kupon puanlaması için: koşan at sayısı (plase/ikili alt sınırları) ve eşit derece (dead heat) bilgisi
            "kosan": sum(1 for h in r.get("horses") or [] if not h.get("nonRunner")) + len(r.get("unplaced") or []),
            "derece": poz, "esit": len(set(poz)) < len(poz),
            # koşmayan (start almayan) atlar: kupon satırında seçimden düşülür, kombinasyon yeniden sayılır
            "kosmayan": sorted({str(h.get("no")) for h in (r.get("nonRunners") or []) + [h for h in r.get("horses") or [] if h.get("nonRunner")]
                                if h.get("no") not in (None, "")}, key=lambda x: (len(x), x))}
    return out


# ---------------------------------------------------------------- tek koşu
def _ilk3(p, g, d):
    p = np.asarray(p, float)
    if len(p) <= 3:
        return np.ones(len(p))
    return M.sirali_olasiliklar(p, g, d)["ilk3"]


def kosu_canli(m, kosu, gecmis, yayin_modu, sonuc, ekuri=None):
    atlar = kosu["atlar"]
    n = len(atlar)
    X = gecmis.durum.ozellik(kosu, m.adlar)
    sifir = np.zeros(n)
    K = M.Kume(X, sifir, sifir, sifir, np.zeros(n, int))
    p_s = m.p_model(X, K)
    i3_s = _ilk3(p_s, m.gam_m, m.dlt_m)
    # güncel oran: 0/boş = henüz yok ya da koşmuyor (aynada koşmayan atın oranı 0). Alanın en az yarısında oran
    # varsa piyasa hesaplanır; oranı olmayan atlar piyasa/harman dışında kalır (null).
    oran = [a["oran"] for a in atlar]
    idx = np.array([i for i, o in enumerate(oran) if o is not None], int)
    oran_var = len(idx) >= 2 and len(idx) >= math.ceil(n / 2)
    q = p_o = i3_o = None
    if oran_var:
        inv = np.array([1.0 / oran[i] for i in idx])
        q = inv / inv.sum()
        if yayin_modu == "model+piyasa":
            Xs = X[idx]
            z = np.zeros(len(idx))
            p_o = m.p_harman(Xs, M.Kume(Xs, z, z, z, np.zeros(len(idx), int)), q)
            i3_o = _ilk3(p_o, m.gam, m.dlt)
        else:   # yayın modu yalnız piyasa: gece ile aynı kural
            p_o = q
            i3_o = _ilk3(q, m.gam, m.dlt)
    pos = {int(i): r for r, i in enumerate(idx)} if oran_var else {}
    cikti = []
    for i, a in enumerate(atlar):
        r = pos.get(i)
        cikti.append({
            "no": a["no"], "ad": a["ad"], "jokey": a.get("jokey") or None, "antrenor": a.get("antrenor") or None,
            "kilo": a.get("kilo"), "yas": gece._tam(a.get("yas")), "form": a.get("form") or None,
            "oran": a["oran"], "p_piyasa": _r4(q[r]) if r is not None else None,
            "p_sabah": _r4(p_s[i]), "p_oran": _r4(p_o[r]) if r is not None else None,
            "p_ilk3": _r4(min(i3_s[i], 1.0)), "p_ilk3_oran": _r4(min(i3_o[r], 1.0)) if r is not None else None,
            "son3": gecmis.son3(a["ad"])})
    s = None
    ek = {}
    if sonuc:
        ilk = max(range(n), key=lambda i: p_s[i])
        s = {"sira": sonuc["sira"], "kazanan": sonuc["kazanan"], "kazanan_ad": sonuc["kazanan_ad"],
             "ganyan": sonuc["ganyan"], "model_ilk": atlar[ilk]["no"], "tuttu": atlar[ilk]["ad"] == sonuc["kazanan_ad"]}
        # ek (geriye uyumlu) alanlar — arayüzün at kuponu puanlaması: sira = [1., 2., 3., 4. at no] (bilinen kadarı),
        # derece = sira'daki atların resmî dereceleri (eşit derece = dead heat), ekuri = koşan ekürili at grupları
        kos_no = {str(a["no"]) for a in atlar}
        s["ekuri"] = [g for g in ([str(x) for x in grp if str(x) in kos_no] for grp in (ekuri or [])) if len(g) > 1]
        for a_ in ("kosan", "derece", "esit", "kosmayan"):
            if a_ in sonuc:
                s[a_] = sonuc[a_]
        if oran_var:   # rapor için (dosyaya yazılmaz): harmanın ve piyasa favorisinin ilk seçimi
            ek["oran_tuttu"] = atlar[int(idx[int(np.argmax(p_o))])]["ad"] == sonuc["kazanan_ad"]
            ek["fav_tuttu"] = atlar[int(idx[int(np.argmax(q))])]["ad"] == sonuc["kazanan_ad"]
    durum = "bitti" if s else ("oran_var" if oran_var else "bekliyor")
    # koşu düzeyinde (koşu öncesi, programdan) ekürili at grupları: arayüz kurucuda ekürili atları tek birim sayar
    prog_no = {str(a["no"]) for a in atlar}
    ekuri_k = [g for g in ([str(x) for x in grp if str(x) in prog_no] for grp in (ekuri or [])) if len(g) > 1]
    return {"kosu_id": f'{kosu["tarih"]}/{kosu["hipodrom"]}/{kosu["kosu"]}', "hipodrom": kosu["hipodrom"],
            "kosu": kosu["kosu"], "saat": kosu.get("saat"), "mesafe": kosu["mesafe"], "pist": kosu["pist"],
            "sinif": kosu["sinif"], "durum": durum, "ekuri": ekuri_k, "atlar": cikti, "sonuc": s}, ek


# ---------------------------------------------------------------- dosya
def _icerik(d):
    return {k: v for k, v in d.items() if k != "guncelleme_tsi"}


def yaz_degisince(yol, veri_):
    eski = gece.joku(yol)
    if eski is not None and _icerik(eski) == json.loads(json.dumps(_icerik(veri_), ensure_ascii=False)):
        return False
    gece.jyaz(yol, veri_, sikisik=True)
    return True


# ---------------------------------------------------------------- oran izi (gün içi ganyan oranı zaman serisi)
ORAN_IZI = os.path.join(gece.CIKTI, "oran_izi")
IZ_MAX = 24   # koşu başına en çok nokta (ilk nokta korunur, aradakiler en eskiden düşer)


def _yakalama_saatleri(t, kaynak):
    """data/daily/<t>.json -> {(hipodrom, koşu): 'HH:MM' TSİ}: aynanın oranı yakaladığı an (snapshotRef.capturedAt)."""
    out = {}
    try:
        js = json.load(open(os.path.join(kaynak, "data", "daily", t + ".json"), encoding="utf-8"))
    except Exception:
        return out
    for r in js:
        ca = ((r.get("snapshotRef") or {}).get("capturedAt") or "")
        try:
            an = datetime.fromisoformat(ca.replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=3)))
        except ValueError:
            continue
        # başka günün yakalaması: oran o güne ait değil (koşu gününün izine yazılmaz) -> ""
        out[(r.get("venue"), int(r.get("raceNo") or 0))] = an.strftime("%H:%M") if an.date().isoformat() == t else ""
    return out


def oran_izi_guncelle(t, ks, kaynak, simdi):
    """Koşu öncesi ganyan oranlarını zaman damgalı biriktirir: data/at/oran_izi/<t>.json.
    Biçim: kosular["<hipodrom>/<koşu>"] = {"t": ["HH:MM", …], "o": {"<at no>": [oran|null, …]}}.
    Nokta yalnız oranlar bir öncekinden farklıysa eklenir (kompakt); koşu saatinden sonra yakalanan oran yazılmaz.
    Zaman, aynanın yakalama anı (snapshotRef.capturedAt), yoksa bu çalışmanın saati. Uydurma/ara değer yok."""
    yol = os.path.join(ORAN_IZI, t + ".json")
    eski = gece.joku(yol) or {}
    K = dict(eski.get("kosular") or {})
    yakala = _yakalama_saatleri(t, kaynak)
    an_simdi = simdi.strftime("%H:%M") if simdi.date().isoformat() == t else None
    degisti = False
    for k in ks:
        if k.get("sonuc"):
            continue
        an = yakala.get((k["hipodrom"], k["kosu"]), an_simdi)
        saat = k.get("saat") or "99:99"
        if not an or an > saat:
            continue
        o = {str(a["no"]): round(float(a["oran"]), 2) for a in k["atlar"]
             if a.get("oran") is not None and 1.0 < float(a["oran"]) < 999}
        if len(o) < 2 or len(o) < math.ceil(len(k["atlar"]) / 2):   # canlı ile aynı kural: alanın en az yarısında oran
            continue
        anah = f'{k["hipodrom"]}/{k["kosu"]}'
        z = K.get(anah) or {"t": [], "o": {}}
        T, O = list(z.get("t") or []), {n: list(v) for n, v in (z.get("o") or {}).items()}
        son = {n: v[-1] for n, v in O.items() if v and v[-1] is not None}
        if T and (an <= T[-1] or son == o):   # aynı yakalama ya da oran değişmedi: dosyaya dokunulmaz (gereksiz commit yok)
            continue
        for n in set(O) | set(o):
            O.setdefault(n, [None] * len(T)).append(o.get(n))
        T.append(an)
        if len(T) > IZ_MAX:   # ilk nokta (sabah) korunur
            dus = len(T) - IZ_MAX
            T = T[:1] + T[1 + dus:]
            O = {n: v[:1] + v[1 + dus:] for n, v in O.items()}
        K[anah] = {"t": T, "o": O}
        degisti = True
    if degisti:
        gece.jyaz(yol, {"tarih": t, "guncelleme_tsi": simdi.strftime("%Y-%m-%d %H:%M"), "kaynak": KAYNAK_ATIF,
                        "aciklama": "koşu öncesi ganyan oranı; nokta yalnız oran değişince eklenir; t = aynanın yakalama saati (TSİ)",
                        "kosular": K}, sikisik=True)
    return degisti


def oran_izi_temizle(bugun):
    """En çok son 2 günün izi tutulur (bugün ve dün; yarının programı varsa o da)."""
    sinir = (date.fromisoformat(bugun) - timedelta(days=1)).isoformat()
    try:
        for f in os.listdir(ORAN_IZI):
            if f.endswith(".json") and f[:10] < sinir:
                os.remove(os.path.join(ORAN_IZI, f))
    except FileNotFoundError:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guncelleme-yok", action="store_true", help="aynayı güncelleme (yerel kopya)")
    ap.add_argument("--bugun", default=None, help="YYYY-MM-DD (varsayılan: İstanbul saatiyle bugün)")
    ar = ap.parse_args()
    t0 = time.time()
    kaynak = os.environ["AT_KAYNAK"]
    print("ayna:", "güncellenmedi (yerel kopya)" if ar.guncelleme_yok else gece.ayna_guncelle(kaynak), kaynak)
    simdi = tsi_simdi()
    bugun = ar.bugun or simdi.date().isoformat()
    b = date.fromisoformat(bugun)
    gunler = [bugun, (b + timedelta(days=1)).isoformat()]
    if not ar.bugun and simdi.hour < 6:   # gece yarısından sonraki çalışma: dünün geç sonuçlarını da tamamla
        gunler.insert(0, (b - timedelta(days=1)).isoformat())
    progs = {t: veri.program_yukle(t, kaynak) for t in gunler}
    progs = {t: p for t, p in progs.items() if p}
    print("program:", {t: len(p) for t, p in progs.items()})

    kosular, _ = veri.sonuclari_yukle(kaynak)
    print(f"sonuçlar yüklendi: {len(kosular)} koşu ({time.time() - t0:.1f} sn)")
    mj = gece.joku(os.path.join(gece.CIKTI, "model.json"))
    if not mj:
        print("model.json yok; çıkılıyor")
        return
    m = gece.model_yukle(mj["uretim_modeli"])
    yayin_modu = mj.get("yayin_modu", "model+piyasa")

    gecmis = Gecmis(kosular)
    ozet = {}
    for t in sorted(progs):
        gecmis.ilerlet(t)     # yalnız t gününden ÖNCEKİ sonuçlar
        sonuclar = gun_sonuclari(t, kaynak)
        try:
            gprog = altili.gun_programi(t, kaynak)   # (hipodrom, koşu) -> (isGanyanStart, ekürili gruplar)
        except Exception:
            gprog = {}
        ks, ekler = [], []
        for k in progs[t]:
            kc, ek = kosu_canli(m, k, gecmis, yayin_modu, sonuclar.get((k["hipodrom"], k["kosu"])),
                                (gprog.get((k["hipodrom"], k["kosu"])) or (None, []))[1])
            ks.append(kc); ekler.append(ek)
        ks.sort(key=lambda k: (k.get("saat") or "99:99", k["hipodrom"], k["kosu"]))
        out = {"tarih": t, "guncelleme_tsi": simdi.strftime("%Y-%m-%d %H:%M"), "model_surumu": mj.get("surum", "?"),
               "kaynak": KAYNAK_ATIF, "kosular": ks}
        degisti = yaz_degisince(os.path.join(CANLI, t + ".json"), out)
        try:   # gün içi oran izi (arayüzde mini çizgi); hata ana canlı akışı durdurmaz
            iz = oran_izi_guncelle(t, ks, kaynak, simdi)
        except Exception as e:
            iz = f"hata ({type(e).__name__})"
        bitti = [k for k in ks if k["durum"] == "bitti"]
        ozet[t] = {"kosu": len(ks), "oran_var": sum(k["durum"] == "oran_var" for k in ks), "bitti": len(bitti),
                   "model_ilk_tuttu": sum(k["sonuc"]["tuttu"] for k in bitti),
                   "oran_ilk_tuttu": sum(1 for e in ekler if e.get("oran_tuttu")),
                   "favori_tuttu": sum(1 for e in ekler if e.get("fav_tuttu")),
                   "oranli_bitti": sum(1 for e in ekler if "oran_tuttu" in e), "yazildi": degisti, "oran_izi": iz}
        try:
            A = altili.gun_guncelle(t, kaynak, simdi=simdi.replace(tzinfo=None))
            ozet[t]["altili"] = len(A["altililar"]) if A else 0
        except Exception as e:   # 6'lı modülü ana canlı akışı asla durdurmaz
            print("6'lı güncellenemedi:", type(e).__name__, e)
    oran_izi_temizle(bugun)
    print("canlı:", json.dumps(ozet, ensure_ascii=False))
    _, puanlanan = gece.puanla(kosular, yalniz_degisince=True)
    print("karneye eklenen gün(ler):", puanlanan)
    try:
        k = altili.joku(altili.KARNE, {}) or {}
        altili.jyaz(altili.KARNE, {**k, "canli": altili.canli_karne()}, sikisik=False)
    except Exception as e:
        print("6'lı karnesi güncellenemedi:", type(e).__name__, e)
    print(f"tamam ({time.time() - t0:.1f} sn)")


if __name__ == "__main__":
    main()
