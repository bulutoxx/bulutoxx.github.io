#!/usr/bin/env python3
"""🧪 Sürekli deney (2–3 saatte bir, .github/workflows/surekli-deney.yml). Robotlar gece beklemeden kendini sınar.

İKİ AŞAMA:
  deney <iş>   Paralel matris işleri (futbol, basket, at, autolab, fbguc). Her biri kendi deneyini çalıştırır ve sonucu yalnız
               data/deney/<iş>/<zaman>.json'a yazar (commit atmaz; karar işine yapıt olarak geçer).
                 futbol / basket / at : OXXai deney kuyruğu (lab/oxx_ogren.py: sinyal → aday → ileriye dönük sanal oynatma).
                   Kapı lab/oxx_ogren.sina'nın kendisidir (kopya yok): zaman sıralı seçim/sınama dilimi, eşleştirilmiş gün
                   bootstrap'ı, alfa yatırımı (Foster–Stine; mFDR ≤ 0,05), Altın/güçlü isabet koruması.
                   Ayrıca gölgedeki adaylar en güncel veriyle yeniden ölçülür (tam veri + yalnız gölge başladıktan sonraki günler).
                   at işi hafif moddadır: yalnız data/at/replay_kosular.json (ayna/eğitim gerekmez).
                 autolab : lab/auto_lab.py, dönen lig alt kümesiyle (her çalışmada farklı 4 lig) ve kısa bütçeyle; yalnız ölçüm.
                 fbguc   : oransız maç model yolu (Poisson ayarı, Elo, pi-rating, topluluk) yeniden ölçümü (lab/fb_guc_kapi.py olc);
                           karar ayrı adımda lab/fb_guc_kapi.py karar (kapı + 14 gün kilitli gölge A/B + geri alma).
  karar        Toplayıcı iş. Yapıtları içeri alır ve:
                 • kapıyı geçen aday hemen UYGULANMAZ, GÖLGEYE alınır (data/deney/golge.json): sonraki çalışmalar onu yeni
                   veriyle paralel ölçer. En az GOLGE_GUN gün ve GOLGE_OLCUM ölçüm boyunca kötüleşmezse uygulanır; herhangi bir
                   ölçümde kötüleşirse otomatik geri çekilir (uygulanmaz, 14 gün yeniden denenmez).
                 • uygulama lab/oxx_ogren.uygula ile data/oxx_ayar.json'a yazılır → mevcut izleme devreye girer: kupon robotu önceki
                   ayarla canlı gölge kupon kilitler, 14 gün sonra lab/oxx_ogren.yeniden_sina sınar, kötüleşirse oxx_rollback ile geri alır.
                 • koruyucu geri alma (data/rollback.json) aktifse ya da anahtar OXXai geri alma süresindeyse hiçbir şey uygulanmaz.
                 • her karar data/ogrenme_gunlugu.json'a, kısa Türkçe özet data/gelisim.json'a (lab/guardian.gelisim_ekle) düşer.
  python3 lab/surekli_deney.py deney futbol
  python3 lab/surekli_deney.py karar --kaynak <yapıt dizini> [--kuru]
Ortam: DENEY_BUDGET (sn, varsayılan 900), DENEY_N (iş başına en çok aday, varsayılan 1)."""
import argparse, collections, copy, glob, json, math, os, re, shutil, subprocess, sys, time
from datetime import date, datetime, timedelta, timezone

LAB = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(LAB)
DATA = os.path.join(ROOT, "data")
DENEY = os.path.join(DATA, "deney")
GOLGE = os.path.join(DENEY, "golge.json")
DURUM = os.path.join(DENEY, "durum.json")
GELISIM = os.path.join(DATA, "gelisim.json")
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(ROOT, "scripts"))

ISLER = ("futbol", "basket", "at", "autolab", "fbguc")
GOLGE_GUN, GOLGE_OLCUM, GOLGE_AZAMI_GUN, SAKLA_GUN = 3, 3, 10, 7
BUDGET = float(os.environ.get("DENEY_BUDGET", "900"))
ADAY_N = int(os.environ.get("DENEY_N", "1"))
T0 = time.time()


def kalan(): return BUDGET - (time.time() - T0)


def jl(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def jw(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=1, default=float)
    os.replace(tmp, p)


def utc_damga(): return datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")


def tr_bugun():
    return (datetime.now(timezone.utc) + timedelta(hours=3)).date()


def temiz(s):
    """Görünür metinde 'bahis' kelimesi geçmesin."""
    return re.sub(r"(?i)bahis", "tahmin", str(s or ""))


# ------------------------------------------------------------------ deney: OXXai kuyruğu (futbol / basket / at)
def _gunler(V, alan):
    if alan == "futbol": return list(V.fb()[0].keys())
    if alan == "basket": return list(V.bk()[0].keys())
    return list(V.at().keys())


def _sina_ozet(rap, c=None):
    s = rap.get("sinama") or {}
    o = {"karar": rap.get("karar"), "neden": rap.get("neden"), "fark": s.get("fark"), "alt_sinir": s.get("alt_sinir"),
         "n_taban": (s.get("taban") or {}).get("n"), "n_aday": (s.get("aday") or {}).get("n"), "alfa": rap.get("alfa")}
    if c is not None and c.get("tur") == "pazar": o["deger"] = c.get("deger")
    return o


def deney_oxx(alan):
    import oxx_ogren as O
    K = O.K
    bugun = tr_bugun()
    J = K.jl(K.AYAR, None) or {"params": {}, "izlenen": [], "gecmis": []}
    A = K.ayar_yukle(J)
    GL = K.jl(O.GUNLUK, {}) or {"sayac": {}, "kayitlar": []}
    G = jl(GOLGE, {}) or {}; GA = G.get("adaylar") or {}
    son_ret = {k["anahtar"]: k["tarih"] for k in GL.get("kayitlar", []) if k.get("karar") in ("ret", "veri_yetersiz")}
    izlenen = {i["anahtar"] for i in J.get("izlenen", [])}

    def yakin_ret(k):
        r = son_ret.get(k)
        return bool(r) and (bugun - date.fromisoformat(r)).days < O.BEKLEME

    def uygun(c):
        k = c["anahtar"]
        if c["alan"] != alan or k in GA or k in izlenen or yakin_ret(k): return False
        if c.get("deger") is not None and O.al(J.get("params") or {}, c["yol"]) == c["deger"]: return False   # zaten uygulanmış
        return True

    adaylar = sorted([c for c in O.sinyaller(bugun, A) if uygun(c)], key=lambda c: -abs((c.get("sinyal") or {}).get("z") or 0))
    # keşif (sinyal yokken eşik ±0,02): sürekli deneyde alan başına günde en çok 1 (deneme sayısı gereksiz büyümesin)
    kesif_bugun = any(k.get("kaynak") == "surekli-deney" and k.get("tarih") == bugun.isoformat() and k.get("alan") == alan
                      and str((k.get("sinyal") or {}).get("kaynak", "")).startswith("keşif") for k in GL.get("kayitlar", []))
    if not adaylar and not kesif_bugun and alan in ("futbol", "basket"):
        haric = {k for k in son_ret if yakin_ret(k)} | set(GA) | izlenen
        for _ in range(40):
            c = O.kesif(bugun, A, haric)
            if not c: break
            if c["alan"] == alan and uygun(c): adaylar.append(c); break
            haric.add(c["anahtar"])
    V = O.Veri(bugun)
    m = GL.get("sayac", {}).get(f"{alan}-{bugun.year}", 0)
    denenen = []
    alan_k = f"{alan}-{bugun.year}"
    for c in adaylar[:ADAY_N]:
        if kalan() < 60: break
        m += 1; t1 = time.time()
        a_t = O.yatirim_alfa(GL, alan_k, c)          # alfa yatırımı (servet karar işinde kalıcı güncellenir)
        try:
            rap = O.sina(c, V, J, A, m, alfa=a_t)
        except Exception as e:
            rap = {"karar": "hata", "neden": repr(e)[:300]}
        if rap.get("test_yapildi"):                  # aynı çalışmada ikinci aday güncel servetle sınansın (yalnız bellekte)
            O.yatirim_guncelle(GL, alan_k, rap["alfa_ham"], rap["istatistik_gecti"])
        denenen.append({"aday": c, "m": m, "rap": rap, "sure_sn": round(time.time() - t1, 1)})
        print(f"[{alan}] {c['anahtar']} → {rap.get('karar')} ({rap.get('neden')})", flush=True)
    olcum = []
    for k, g in GA.items():
        if g["aday"].get("alan") != alan: continue
        if kalan() < 45: break
        try:
            ga = g.get("alfa")                     # gölge doğrulaması yeni harcama yapmaz: girişteki α ile ölçülür
            c1 = copy.deepcopy(g["aday"]); tam = O.sina(c1, V, J, A, g.get("m", 1), alfa=ga)
            yeni_g = {d for d in _gunler(V, alan) if d >= g["baslangic_gun"]}
            yeni = None
            if yeni_g:
                c2 = copy.deepcopy(g["aday"]); yeni = O.sina(c2, V, J, A, g.get("m", 1), gunler_filtre=yeni_g, alfa=ga)
            o = {"anahtar": k, "tam": _sina_ozet(tam, c1), "yeni_gun_sayisi": len(yeni_g)}
            if yeni:
                s = yeni.get("sinama") or {}
                o["yeni"] = {"fark": s.get("fark"), "n": (s.get("taban") or {}).get("n"), "aday_n": (s.get("aday") or {}).get("n")}
            olcum.append(o)
            print(f"[{alan}] gölge {k}: tam {tam.get('karar')}, yeni günler {o.get('yeni')}", flush=True)
        except Exception as e:
            olcum.append({"anahtar": k, "hata": repr(e)[:200]})
    return {"denenen": denenen, "golge_olcum": olcum, "bugun": bugun.isoformat()}


# ------------------------------------------------------------------ deney: auto_lab (dönen lig alt kümesi)
def deney_autolab():
    S = jl(os.path.join(DATA, "season.json"), {}) or {}
    ligler = []
    for lg, d in S.items():
        n = sum(1 for m in (d or {}).get("matches", []) if m.get("ft") and m.get("odds"))
        if n >= 300: ligler.append(lg)
    del S
    ligler.sort()
    if not ligler: return {"hata": "oranlı ligi olan sezon verisi yok"}
    grup = 4; parca = max(1, math.ceil(len(ligler) / grup))
    sira = int(time.time() // (3 * 3600)) % parca
    secim = ligler[sira * grup:(sira + 1) * grup] or ligler[:grup]
    tmp = os.path.join(DENEY, "autolab", "_gecici.json")
    env = dict(os.environ, LAB_LEAGUES=",".join(secim), LAB_BUDGET=str(int(max(120, kalan() - 60))), LAB_CIKTI=tmp)
    r = subprocess.run([sys.executable, os.path.join(LAB, "auto_lab.py")], env=env, capture_output=True, text=True,
                       timeout=max(180, int(kalan())))
    print(r.stdout[-1500:], r.stderr[-800:], flush=True)
    out = jl(tmp)
    try: os.remove(tmp)
    except Exception: pass
    if out is None:
        return {"ligler": secim, "hata": f"auto_lab çıktı üretmedi (çıkış {r.returncode})", "_rc": r.returncode or 1}
    sonuc = out.get("sonuc") or {}
    gecen = []
    sezonlar = [str(s) for s in out.get("sezonlar", [])]
    for ad, res in sonuc.items():
        if ad == "piyasa (mevcut)" or not sezonlar: continue
        son = res.get(sezonlar[-1]) or {}
        if all((res.get(s) or {}).get("kazanc", -1) > 0.0005 for s in sezonlar) and (son.get("kazanc_alt95") or -1) > 0:
            gecen.append({"aday": ad, "son_sezon_kazanc": son.get("kazanc"), "alt95": son.get("kazanc_alt95")})
    return {"ligler": secim, "n": out.get("n"), "sezonlar": sezonlar, "sonuc": sonuc, "kapidan_gecen": gecen,
            "not": "Yalnız ölçüm: dönen lig alt kümesiyle açık kaynak modellerin piyasaya katkısı. Motor ayarını gece "
                   "laboratuvarı (auto-lab.yml) ve koruyucu yönetir; burada bir şey uygulanmaz."}


# ------------------------------------------------------------------ deney: oransız model yolu (lab/fb_guc_kapi.py)
def deney_fbguc():
    """⚖️ Güç puanları + topluluk: zaman sıralı yeniden ölçüm (son 180 gün sınama, lig×gün blok bootstrap'ı). Karar ve
    14 günlük gölge A/B izlemesi karar işinde lab/fb_guc_kapi.py karar ile verilir (gölgedeki adaylar her çalışmada yeniden ölçülür)."""
    import fb_guc_kapi as FK
    k = FK.olc()
    if not k: return {"hata": "oransız lig verisi yok", "_rc": 1}
    return {"karne": k}


def deney(is_):
    if is_ not in ISLER: raise SystemExit(f"bilinmeyen iş: {is_}")
    t = utc_damga()
    try:
        sonuc = deney_autolab() if is_ == "autolab" else deney_fbguc() if is_ == "fbguc" else deney_oxx(is_)
        rc = sonuc.pop("_rc", 0)
    except Exception as e:
        import traceback; traceback.print_exc()
        sonuc, rc = {"hata": repr(e)[:300]}, 1
    D = {"is": is_, "zaman": t, "sure_sn": round(time.time() - T0, 1), **sonuc}
    p = os.path.join(DENEY, is_, f"{t}.json")
    jw(p, D)
    print(f"deney {is_}: {p} ({D['sure_sn']} sn)")
    return 1 if rc or "hata" in sonuc else 0


# ------------------------------------------------------------------ karar
def ice_al(kaynak):
    """Yapıt dizinindeki deney ve sağlık dosyalarını depo yerlerine kopyalar."""
    n = 0
    if not kaynak or not os.path.isdir(kaynak): return 0
    for p in glob.glob(os.path.join(kaynak, "**", "*.json"), recursive=True):
        ust = os.path.basename(os.path.dirname(p)); ust2 = os.path.basename(os.path.dirname(os.path.dirname(p)))
        if ust2 == "deney" and ust in ISLER and not os.path.basename(p).startswith("_"):
            hedef = os.path.join(DENEY, ust, os.path.basename(p))
        elif ust == "saglik":
            hedef = os.path.join(DATA, "saglik", os.path.basename(p))
        else:
            continue
        os.makedirs(os.path.dirname(hedef), exist_ok=True); shutil.copyfile(p, hedef); n += 1
    return n


def gelisim_yaz(Gel, tur, baslik, detay, anahtar, tarih, guncelle=False):
    import guardian
    baslik, detay = temiz(baslik), temiz(detay)
    if guncelle:
        for e in Gel.get("olaylar", []):
            if e.get("anahtar") == anahtar:
                e.update({"baslik": baslik, "detay": detay}); return
    guardian.gelisim_ekle(Gel, tur, baslik, detay, anahtar, tarih)


def strateji_adi(K, c):
    ss = c.get("stratejiler") or []
    if len(ss) == 1 and ss[0] in K.STRATEJI: return K.STRATEJI[ss[0]][1]
    return {"futbol": "Futbol", "basket": "Basketbol", "at": "At yarışı"}.get(c.get("alan"), c.get("alan", ""))


def karar(kaynak, kuru=False):
    import oxx_ogren as O
    K = O.K
    bugun = tr_bugun(); simdi = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    alinan = ice_al(kaynak)
    J = K.jl(K.AYAR, None) or {"v": 1, "surum": "varsayilan", "params": {}, "izlenen": [], "gecmis": []}
    Q = K.jl(O.KUYRUK, {}) or {"adaylar": []}
    GL = K.jl(O.GUNLUK, {}) or {"v": 1, "sayac": {}, "kayitlar": []}
    GL.setdefault("sayac", {}); GL.setdefault("kayitlar", [])
    rb = K.jl(O.OXX_RB, {}) or {}
    donmus = {k for k, v in (rb.get("donmus") or {}).items() if v >= bugun.isoformat()}
    donuk = bool((K.jl(os.path.join(DATA, "rollback.json"), {}) or {}).get("aktif"))
    G = jl(GOLGE, {}) or {}; G.setdefault("adaylar", {})
    DU = jl(DURUM, {}) or {}; islenen = list(DU.get("islenen") or [])
    Gel = jl(GELISIM, {"olaylar": []}) or {"olaylar": []}
    var = {a["anahtar"]: a for a in Q.get("adaylar", [])}
    sayim = collections.Counter(); notlar = []

    def kayit(c, kar, neden, ek=None, tarih=None, uygulandi=False):
        GL["kayitlar"].append(dict({"tarih": tarih or bugun.isoformat(), "anahtar": c["anahtar"], "tur": c.get("tur"), "alan": c.get("alan"),
                                    "aciklama": c.get("aciklama"), "sinyal": c.get("sinyal"), "deger": c.get("deger"), "uygulandi": uygulandi,
                                    "kaynak": "surekli-deney"}, **(ek or {}), karar=kar, neden=neden))
        a = var.get(c["anahtar"])
        if a is None:
            a = dict(c, eklenme=bugun.isoformat(), oncelik=round(abs((c.get("sinyal") or {}).get("z") or 0), 2)); var[c["anahtar"]] = a
        a.update({"durum": "denendi", "son_deneme": tarih or bugun.isoformat(), "sonuc": kar})

    dosyalar = []
    for is_ in ISLER:
        for p in sorted(glob.glob(os.path.join(DENEY, is_, "*.json"))):
            ad = f"{is_}/{os.path.basename(p)}"
            if os.path.basename(p).startswith("_") or ad in islenen: continue
            dosyalar.append((os.path.basename(p), is_, ad, p))
    dosyalar.sort()                                     # zaman sırası
    son_autolab = None
    for _, is_, ad, p in dosyalar:
        D = jl(p, {}) or {}
        islenen.append(ad); sayim["dosya"] += 1
        if is_ == "autolab":
            if D.get("sonuc"): son_autolab = D
            continue
        if is_ == "fbguc": continue          # karar: lab/fb_guc_kapi.py karar (ayrı adım; kendi kapısı ve izlemesi)
        tarih = D.get("bugun") or bugun.isoformat()
        for d in D.get("denenen", []):
            c, rap = d["aday"], d.get("rap") or {}
            kar = rap.get("karar"); sayim[kar] += 1
            alan_k = f"{c['alan']}-{tarih[:4]}"
            if kar in ("kabul", "ret"): GL["sayac"][alan_k] = max(GL["sayac"].get(alan_k, 0), d.get("m", 0))
            if rap.get("test_yapildi"):                       # alfa yatırımı servetini kalıcı güncelle (dosya sırasıyla)
                rap["servet_sonra"] = O.yatirim_guncelle(GL, alan_k, rap["alfa_ham"], rap["istatistik_gecti"])["servet"]
            ek = {k: v for k, v in rap.items() if k not in ("karar", "neden")}
            ek["sure_sn"] = d.get("sure_sn")
            if kar == "kabul":
                if donuk:
                    kayit(c, "dondurulmus", "koruyucu geri alma aktif (data/rollback.json); gölgeye alınmadı", ek, tarih); continue
                if c["anahtar"] in donmus:
                    kayit(c, "dondurulmus", "bu anahtar OXXai geri alma süresinde", ek, tarih); continue
                G["adaylar"][c["anahtar"]] = {"aday": c, "m": d.get("m", 1), "alfa": rap.get("alfa_ham"), "baslangic": D.get("zaman"), "baslangic_gun": tarih,
                                             "ilk": _sina_ozet(rap, c), "olcumler": []}
                kayit(c, "golge", "kapı geçildi → gölge ölçüme alındı (henüz uygulanmadı)", ek, tarih)
                s = rap.get("sinama") or {}
                gelisim_yaz(Gel, "ogrenme", f"Yeni ayar adayı gölge denemede: {strateji_adi(K, c)}",
                            f"{c.get('aciklama')}; sınamada fark {s.get('fark')}, alt sınır {s.get('alt_sinir')}. "
                            f"En az {GOLGE_GUN} gün paralel ölçülecek, kötüleşirse uygulanmayacak.", f"golge-{c['anahtar']}-{tarih}", tarih)
            else:
                kayit(c, kar or "hata", rap.get("neden") or "", ek, tarih)
        for o in D.get("golge_olcum", []):
            g = G["adaylar"].get(o.get("anahtar"))
            if g is None or "hata" in o: continue
            t = o.get("tam") or {}
            g["olcumler"].append({"zaman": D.get("zaman"), "tam_karar": t.get("karar"), "tam_fark": t.get("fark"), "tam_alt": t.get("alt_sinir"),
                                  "tam_neden": t.get("neden"), "deger": t.get("deger"), "yeni": o.get("yeni"), "yeni_gun": o.get("yeni_gun_sayisi")})
            g["olcumler"] = g["olcumler"][-20:]

    # gölge değerlendirmesi: kötüleşirse geri çek, yeterince ölçülüp tutarsa uygula
    for k, g in list(G["adaylar"].items()):
        c = g["aday"]; ol = g.get("olcumler", [])
        yas = (bugun - date.fromisoformat(g["baslangic_gun"])).days
        kotu = [o for o in ol if o.get("tam_karar") == "ret"
                or ((o.get("yeni") or {}).get("fark") is not None and ((o.get("yeni") or {}).get("n") or 0) >= 10 and o["yeni"]["fark"] < 0)]
        if kotu:
            o = kotu[-1]
            neden = (f"gölge ölçümde kötüleşti ({o.get('zaman')}: tam veri kararı {o.get('tam_karar')}"
                     + (f", gölge sonrası fark {o['yeni']['fark']}" if (o.get("yeni") or {}).get("fark") is not None else "") + ")")
            kayit(c, "ret", neden, {"tur_asama": "golge", "olcum_sayisi": len(ol)})
            gelisim_yaz(Gel, "geri", f"Gölge denemedeki ayar geri çekildi: {strateji_adi(K, c)}",
                        f"{c.get('aciklama')} — {neden}. Uygulanmadı; 14 gün yeniden denenmeyecek.", f"golge-geri-{k}-{bugun}", bugun.isoformat())
            del G["adaylar"][k]; sayim["golge_geri"] += 1
        elif yas >= GOLGE_GUN and len(ol) >= GOLGE_OLCUM:
            if donuk or k in donmus:
                g["bekleme"] = "koruyucu / OXXai geri alma aktif; uygulama bekletiliyor"
                if yas > GOLGE_AZAMI_GUN:
                    kayit(c, "dondurulmus", "gölge süresi doldu, geri alma aktif olduğu için uygulanmadı"); del G["adaylar"][k]
                continue
            son_deger = next((o.get("deger") for o in reversed(ol) if o.get("deger") is not None), None)
            if c.get("tur") == "pazar" and son_deger is not None: c["deger"] = son_deger
            O.uygula(J, c, bugun)
            if J.get("izlenen"): J["izlenen"][-1]["kaynak"] = "surekli-deney"
            kayit(c, "kabul", f"kapı + gölge A/B geçti ({len(ol)} ölçüm, {yas} gün); uygulandı, 14 gün izlenecek", {"tur_asama": "uygulama"},
                  uygulandi=True)
            gelisim_yaz(Gel, "gelisme", f"Sürekli deney yeni ayarı uyguladı: {strateji_adi(K, c)}",
                        f"{c.get('aciklama')}. {len(ol)} gölge ölçümde kötüleşmedi. Önceki ayar gölgede ölçülmeye devam eder; "
                        f"kötüleşirse otomatik geri alınır.", f"uygula-{k}-{bugun}", bugun.isoformat())
            del G["adaylar"][k]; sayim["uygulandi"] += 1
        elif yas > GOLGE_AZAMI_GUN:
            kayit(c, "veri_yetersiz", f"gölge süresi ({GOLGE_AZAMI_GUN} gün) doldu, yeterli ölçüm yok ({len(ol)})")
            del G["adaylar"][k]

    if son_autolab:
        gec = son_autolab.get("kapidan_gecen") or []
        detay = (f"Ligler: {', '.join(son_autolab.get('ligler') or [])}; {son_autolab.get('n')} maç. "
                 + (f"Piyasayı iki sezonda da geçen: {', '.join(x['aday'] for x in gec)} (yalnız ölçüm)." if gec
                    else "Hiçbir açık kaynak karışımı piyasayı iki sezonda da geçemedi; mevcut sistem korunur."))
        gelisim_yaz(Gel, "olcum", "Sürekli laboratuvar ölçümü", detay, f"{bugun}-surekli-autolab", bugun.isoformat(), guncelle=True)
    bugun_k = [k for k in GL["kayitlar"] if k.get("kaynak") == "surekli-deney" and k.get("tarih") == bugun.isoformat()]
    if bugun_k:
        sc = collections.Counter(k.get("karar") for k in bugun_k)
        gelisim_yaz(Gel, "ogrenme", "Sürekli deney: bugünkü denemeler",
                    f"{len(bugun_k)} karar: {sc.get('ret', 0)} ret, {sc.get('golge', 0)} gölgeye alındı, {sc.get('kabul', 0)} uygulandı; "
                    f"gölgede bekleyen {len(G['adaylar'])}.", f"{bugun}-surekli-ozet", bugun.isoformat(), guncelle=True)

    # eski deney dosyalarını depodan kaldır (geçmişte durur; yalnız son SAKLA_GUN gün tutulur)
    sinir = (datetime.now(timezone.utc) - timedelta(days=SAKLA_GUN)).strftime("%Y%m%dT%H%MZ")
    silinen = 0
    for is_ in ISLER:
        for p in glob.glob(os.path.join(DENEY, is_, "*.json")):
            if os.path.basename(p) < sinir and not kuru:
                os.remove(p); silinen += 1
    GL["kayitlar"] = GL["kayitlar"][-300:]
    GL["guncelleme"] = simdi
    Q["adaylar"] = sorted(var.values(), key=lambda a: (a.get("durum") != "bekliyor", -a.get("oncelik", 0)))[-200:]
    G["guncelleme"] = simdi
    G["kurallar"] = {"giris": "lab/oxx_ogren.sina kapısı (zaman sıralı seçim/sınama, gün bootstrap'ı, alfa yatırımı α_t, Altın/güçlü koruması)",
                     "golge": f"en az {GOLGE_GUN} gün ve {GOLGE_OLCUM} ölçüm; tam veride ret ya da gölge sonrası günlerde fark < 0 (n ≥ 10) → geri çekilir",
                     "uygulama": "lab/oxx_ogren.uygula → data/oxx_ayar.json izlenen; 14 gün sonra yeniden sınama + canlı gölge kupon, kötüleşirse oxx_rollback",
                     "dondurma": "data/rollback.json aktif ya da anahtar oxx_rollback donmus listesinde ise uygulanmaz"}
    DU.update({"islenen": islenen[-400:], "son_karar": simdi, "son_ozet": dict(sayim, alinan_dosya=alinan, silinen_eski=silinen,
                                                                             golgede=len(G["adaylar"]))})
    Gel["olaylar"] = (Gel.get("olaylar") or [])[-150:]
    print(f"karar: {dict(sayim)}; gölgede {len(G['adaylar'])}; {alinan} yapıt dosyası alındı; {silinen} eski deney dosyası silindi")
    if kuru:
        print(json.dumps({"golge": G["adaylar"], "ozet": DU["son_ozet"]}, ensure_ascii=False, indent=1, default=float)[:3000]); return 0
    K.jw_degisince(K.AYAR, J, haric=(), indent=1)
    K.jw(O.KUYRUK, Q); K.jw(O.GUNLUK, GL)
    jw(GOLGE, G); jw(DURUM, DU)
    json.dump(Gel, open(GELISIM, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("komut", choices=["deney", "karar"]); ap.add_argument("is_", nargs="?")
    ap.add_argument("--kaynak", default=None); ap.add_argument("--kuru", action="store_true")
    ar = ap.parse_args()
    if ar.komut == "deney":
        return deney(ar.is_)
    return karar(ar.kaynak, ar.kuru)


if __name__ == "__main__":
    sys.exit(main())
