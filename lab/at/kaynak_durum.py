# OXXai at yarışı — KAYNAK GECİKMESİ izleyicisi (at-canli.yml her turda canli.py içinden çağırır).
# Açık sonuç/program arşivinin (GitHub aynası) ne zaman güncellendiğini ve bugünün programının gelip gelmediğini izler:
#   • data/saglik/at-kaynak.json  → sağlık kaydı (kurtarıcı okur; kaynak gecikmesi yeniden tetiklemeyle düzelmez, yalnız raporlanır)
#   • data/at/kaynak_durum.json   → arayüzün okuduğu küçük özet (yalnız durum değişince değişir; gereksiz commit yok)
# Ayrıca ayna programı GEÇ yayınladıysa (sabah kilidinden sonra) at-lab.yml'yi günde en çok bir kez tetikler
# (`python3 lab/at/kaynak_durum.py --gec-kilit`, GH_TOKEN gerekir), böylece bugünün kilitli tahmini aynı gün hazırlanır.
# Yalnız yerel ayna kopyasının dosya adlarına ve commit zamanına bakar; ağ isteği yapmaz (gh tetiklemesi hariç),
# ham üçüncü taraf verisi yazmaz, Ek kaynak A adresini hiçbir yere yazmaz.
import glob, json, os, subprocess, sys
from datetime import date, datetime, timedelta, timezone

BURA = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(os.path.dirname(BURA))
SAGLIK = os.path.join(KOK, "data", "saglik", "at-kaynak.json")
UI = os.path.join(KOK, "data", "at", "kaynak_durum.json")
CANLI = os.path.join(KOK, "data", "at", "canli")
TAHMIN = os.path.join(KOK, "data", "at", "tahmin")
EK_DURUM = os.path.join(KOK, "data", "at", "ek_ozellik", "_sonuc_durum.json")
TSI = timezone(timedelta(hours=3))
PROGRAM_SAAT = 11      # ayna programı normalde TSİ 09–10 arası yayınlar; 11:00'e kadar gelmediyse gecikme alarmı
SONUC_ORAN = 0.75      # dünün koşularının en az %75'inin sonucu sabah 09:00'a kadar gelmiş olmalı


def _jl(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:   # noqa: BLE001
        return d


def _jw(p, v):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(v, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(p + ".tmp", p)


def _son_gun(kaynak, alt):
    gs = [os.path.basename(f)[:10] for f in glob.glob(os.path.join(kaynak, "data", alt, "*.json"))]
    gs = [g for g in gs if len(g) == 10 and g[4] == "-" and g[7] == "-"]
    return max(gs) if gs else None


def _ayna_commit(kaynak):
    try:
        r = subprocess.run(["git", "-C", kaynak, "log", "-1", "--format=%cI"], capture_output=True, text=True, timeout=30)
        s = r.stdout.strip()
        return datetime.fromisoformat(s).astimezone(timezone.utc) if s else None
    except Exception:   # noqa: BLE001
        return None


def hesapla(kaynak, bugun, bugun_kosu, simdi_utc=None):
    simdi = simdi_utc or datetime.now(timezone.utc)
    tr = simdi.astimezone(TSI)
    ac = _ayna_commit(kaynak)
    dun = (date.fromisoformat(bugun) - timedelta(days=1)).isoformat()
    dc = _jl(os.path.join(CANLI, dun + ".json"), {}) or {}
    dk = dc.get("kosular") or []
    dun_kosu, dun_sonuclu = len(dk), sum(1 for k in dk if k.get("sonuc"))
    ayna_bugun = bool(ac and ac.astimezone(TSI).date().isoformat() >= bugun)
    sorunlar = []
    if bugun_kosu:
        durum = "normal"
    elif ayna_bugun:
        durum = "program_yok"          # ayna bugün güncellendi ama bugün yerli koşu yok (dinlenme günü)
    elif tr.hour < PROGRAM_SAAT:
        durum = "bekleniyor"
    else:
        durum = "gecikme"
        sorunlar.append(f"bugünün ({bugun}) programı aynada yok; ayna son güncelleme "
                        f"{ac.astimezone(TSI).strftime('%Y-%m-%d %H:%M') + ' TSİ' if ac else 'bilinmiyor'}")
    if dun_kosu and tr.hour >= 9 and dun_sonuclu < SONUC_ORAN * dun_kosu:
        sorunlar.append(f"dünün ({dun}) sonuçları eksik: {dun_sonuclu}/{dun_kosu} koşu")
    ek = _jl(EK_DURUM, {}) or {}
    tahmin_var = os.path.exists(os.path.join(TAHMIN, bugun + ".json"))
    ui = {"bugun": bugun, "durum": durum, "bugun_kosu": bugun_kosu, "tahmin_var": tahmin_var,
          "ayna_son_guncelleme": ac.strftime("%Y-%m-%dT%H:%MZ") if ac else None,
          "son_program_gunu": _son_gun(kaynak, "daily"), "son_sonuc_gunu": _son_gun(kaynak, "results"),
          "dun": dun, "dun_kosu": dun_kosu, "dun_sonuclu": dun_sonuclu,
          "aciklama": "Açık yarış arşivinin (GitHub aynası) tazeliği; lab/at/kaynak_durum.py. Ham veri içermez."}
    s = {"is_akisi": "at-canli.yml", "guncelleme": simdi.strftime("%Y-%m-%dT%H:%M:%SZ"),
         "ayna_gecikme_saat": round((simdi - ac).total_seconds() / 3600, 2) if ac else None,
         **{k: v for k, v in ui.items() if k != "aciklama"},
         "ek_kaynak_son_tarih": ek.get("son_tarih"), "alarm": bool(sorunlar), "sorunlar": sorunlar,
         "gec_kilit_gerek": bool(bugun_kosu and not tahmin_var and 6 <= tr.hour <= 22),
         "adimlar": {},
         "aciklama": "Kaynak gecikmesi alarmı (lab/at/kaynak_durum.py). Yeniden tetikleme düzeltmez; kaynak yayınlayınca "
                     "akış kendiliğinden toparlar (canli.py son 3 günü yeniden dener, geç program için at-lab bir kez tetiklenir)."}
    s["imza"] = f"{durum}|{bugun}|{ui['son_program_gunu']}|{ui['son_sonuc_gunu']}|{dun_sonuclu}/{dun_kosu}|{int(s['alarm'])}|{int(s['gec_kilit_gerek'])}"
    return s, ui


def yaz(kaynak, bugun, bugun_kosu, simdi_utc=None):
    s, ui = hesapla(kaynak, bugun, bugun_kosu, simdi_utc)
    eski = _jl(SAGLIK, {}) or {}
    if eski.get("gec_kilit_tetik"):
        s["gec_kilit_tetik"] = eski["gec_kilit_tetik"]
    _jw(SAGLIK, s)
    if (_jl(UI, {}) or {}) != ui:
        _jw(UI, ui)
    print("kaynak durumu:", json.dumps({k: s[k] for k in ("durum", "ayna_son_guncelleme", "ayna_gecikme_saat",
                                                          "son_program_gunu", "alarm", "sorunlar")}, ensure_ascii=False))
    return s


def gec_kilit():
    """Ayna programı sabah kilidinden sonra geldiyse at-lab.yml'yi günde en çok bir kez tetikler."""
    s = _jl(SAGLIK, {}) or {}
    if not s.get("gec_kilit_gerek") or s.get("gec_kilit_tetik") == s.get("bugun"):
        return 0
    if os.path.exists(os.path.join(TAHMIN, (s.get("bugun") or "") + ".json")):
        return 0
    r = subprocess.run(["gh", "workflow", "run", "at-lab.yml", "--ref", "main"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print("geç kilit tetiklenemedi:", r.stderr.strip()[:160])
        return 1
    s["gec_kilit_tetik"] = s.get("bugun")
    _jw(SAGLIK, s)
    print("geç gelen program: at-lab.yml tetiklendi (bugünün kilitli tahmini için)")
    return 0


if __name__ == "__main__":
    if "--gec-kilit" in sys.argv:
        sys.exit(gec_kilit())
    k = os.environ.get("AT_KAYNAK", "./_tjk-data")
    b = datetime.now(TSI).date().isoformat()
    sys.path.insert(0, BURA)
    import veri  # noqa: E402
    yaz(k, b, len(veri.program_yukle(b, k)))
