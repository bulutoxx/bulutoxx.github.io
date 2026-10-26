# BULUTOXX at yarışı laboratuvarı — hipodrom havası (Open-Meteo; veri lisansı CC BY 4.0, atıf: https://open-meteo.com/).
# Anahtarsız, ücretsiz (ticari olmayan kullanım) API; tjk.org / atyarisi.com ile hiçbir ilgisi yok.
# Çıktı: _hava/gunluk.csv (gitignore'da; ham indirilen veri depoya YAZILMAZ). Sütunlar: hipodrom,tarih,yagis_mm,
# yagmur_mm,sicaklik (lab/at/at6.py okur). Geçmiş günler arşivden (ERA5 tabanlı, ~5 gün gecikmeli), son 14 gün +
# yarın yeniden analiz/tahmin uç noktasından (sabah kilidindeki yarış günü değeri TAHMİNDİR).
#   python lab/at/hava.py            # _hava/gunluk.csv'yi oluşturur/günceller (GitHub Actions'ta çalışır)
# Yalnız a6_hava grubu yayındaysa (at6.A6_SECILI) gece.py/canli.py çağırır; erişilemezse eski dosya korunur,
# hiç yoksa özellikler "hava yok" (a6_h_yok=1) olur — yayın durmaz.
import csv, json, os, sys, time, urllib.request
from datetime import date, timedelta

BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import at6  # noqa: E402

# Hipodrom koordinatları (≈0,05° hassasiyet yeterli: model ızgarası ~10 km)
YER = {"istanbul": (40.99, 28.88), "izmir": (38.39, 27.14), "adana": (37.00, 35.40), "bursa": (40.21, 29.02),
       "ankara": (39.96, 32.74), "sanliurfa": (37.15, 38.80), "antalya": (36.92, 30.72), "elazig": (38.67, 39.20),
       "kocaeli": (40.76, 29.95), "diyarbakir": (37.92, 40.21)}
BAS = "2024-12-01"
ARSIV = "https://archive-api.open-meteo.com/v1/archive"
TAHMIN = "https://api.open-meteo.com/v1/forecast"
ALAN = "precipitation_sum,rain_sum,temperature_2m_mean"
ATIF = "Hava verisi: Open-Meteo.com (CC BY 4.0) — https://open-meteo.com/"


def _al(url, deneme=3):
    for i in range(deneme):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "bulutoxx-at-lab"}), timeout=60) as r:
                return json.load(r)["daily"]
        except Exception as e:
            print("hava:", type(e).__name__, str(e)[:120])
            time.sleep(5 * (i + 1))
    return None


def guncelle(yol=None, bugun=None):
    yol = yol or at6.hava_yolu()
    bugun = bugun or date.today()
    eski = {}
    if os.path.exists(yol):
        with open(yol, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                eski[(r["hipodrom"], r["tarih"])] = r
    son_arsiv = (bugun - timedelta(days=6)).isoformat()
    yeni = dict(eski)
    basari = 0
    for h, (la, lo) in YER.items():
        # arşiv: yalnız eksik aralık (dosyada olan en son arşiv gününden sonrası)
        var = sorted(t for (hh, t), r in eski.items() if hh == h and r.get("kaynak") == "arsiv")
        bas = (date.fromisoformat(var[-1]) + timedelta(days=1)).isoformat() if var else BAS
        parcalar = []
        if bas <= son_arsiv:
            d = _al(f"{ARSIV}?latitude={la}&longitude={lo}&start_date={bas}&end_date={son_arsiv}&daily={ALAN}"
                    f"&timezone=Europe%2FIstanbul")
            if d:
                parcalar.append(("arsiv", d))
        d = _al(f"{TAHMIN}?latitude={la}&longitude={lo}&past_days=14&forecast_days=2&daily={ALAN}&timezone=Europe%2FIstanbul")
        if d:
            parcalar.append(("tahmin", d))
        for kaynak, d in parcalar:
            basari += 1
            for t, p, r, s in zip(d["time"], d["precipitation_sum"], d["rain_sum"], d["temperature_2m_mean"]):
                if p is None:
                    continue
                k = (h, t)
                if kaynak == "tahmin" and yeni.get(k, {}).get("kaynak") == "arsiv":
                    continue   # arşiv değeri tahmini ezer, tersi değil
                yeni[k] = {"hipodrom": h, "tarih": t, "yagis_mm": p, "yagmur_mm": r if r is not None else "",
                           "sicaklik": s if s is not None else "", "kaynak": kaynak}
        time.sleep(1)
    if not basari:
        print("hava: Open-Meteo'ya erişilemedi; eski dosya korunuyor" if eski else "hava: veri yok")
        return len(eski)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    tmp = yol + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["hipodrom", "tarih", "yagis_mm", "yagmur_mm", "sicaklik", "kaynak"])
        w.writeheader()
        for k in sorted(yeni):
            w.writerow(yeni[k])
    os.replace(tmp, yol)
    print(f"hava: {len(yeni)} hipodrom-gün ({ATIF})")
    return len(yeni)


if __name__ == "__main__":
    guncelle()
