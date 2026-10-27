# OXXai at yarışı — arayüz için koşu içi GÖRELİ sinyal özeti (v6 özellikleri: idman, handikap puanı, start,
# hava, mesafe profili, Kalman hız figürü, gelişim, yaşa göre kilo).
#
# Girdi: kilit anındaki özellik matrisi X (N at x d) ve özellik adları (gece.kosu_tahmini). Sızıntı yok: X zaten
# yalnız koşudan önce bilinen bilgiden kurulur. Çıktı YALNIZ göreli ifadedir: alan içi sıra [sıra, kaç at],
# iç/orta/dış, var/yok bayrakları. Ham derece, ham puan, ham kilo/start numarası ya da kaynak adı yazılmaz.
#   at   -> {"id": [s, n], "hp": [s, n], "st": "ic|orta|dis", "km": [s, n], "ms": "uygun|uzak",
#            "gl": "ust|alt", "wfa": "avantaj", "hv": "iyi|zayif"}      (verisi olmayan anahtar yazılmaz)
#   koşu -> {"hava": "yagisli|kuru"}                                       (hava verisi yoksa boş)
# Özellik modelde yoksa (ör. eski tarif) ilgili sinyal hiç yazılmaz; arayüz o öğeyi göstermez.
import math

ISLAK_ESIK = math.log1p(3.0)      # at6.ISLAK_ESIK ile aynı (ağırlıklı yağış ≥ 3 mm)
K_ONSEL_SD = math.sqrt(3500.0) / 30.0   # at6: Kalman geçmişi olmayan atın a6_k_sd değeri


def _sira(degerler, buyuk_iyi=True):
    """[(i, değer)] -> {i: [sıra, n]} (1 = en iyi; eşitler aynı sırayı alır)."""
    if len(degerler) < 3:
        return {}
    v = sorted((d for _, d in degerler), reverse=buyuk_iyi)
    out = {}
    for i, d in degerler:
        out[i] = [v.index(d) + 1, len(degerler)]
    return out


def ozet(X, adlar):
    """(at sinyalleri listesi, koşu sinyali). X: satırlar (liste ya da numpy), adlar: sütun adları."""
    ix = {a: k for k, a in enumerate(adlar)}
    N = len(X)
    if not N:
        return [], {}

    def col(ad):
        k = ix.get(ad)
        return None if k is None else [float(X[i][k]) for i in range(N)]
    atlar = [dict() for _ in range(N)]
    kosu = {}
    yuv = lambda x: round(x, 6)   # noqa: E731  (kayan nokta eşitlikleri için)

    # idman/galop: son idman derecesi alan ortancasından farkı (düşük = hızlı); idmanı olan atlar arasında
    var, d4, d6 = col("a6_e_id_var"), col("a6_e_id_400"), col("a6_e_id_600")
    if var and (d4 or d6):
        dd = [(i, yuv(d4[i] if d4 and d4[i] != 0 else (d6[i] if d6 else 0.0))) for i in range(N) if var[i] > 0]
        for i, s in _sira(dd, buyuk_iyi=False).items():
            atlar[i]["id"] = s
    # handikap puanı (alan içi sıra; puansız atlar dışarıda)
    hp, hy = col("a6_e_hp"), col("a6_e_hp_yok")
    if hp and hy:
        for i, s in _sira([(i, yuv(hp[i])) for i in range(N) if hy[i] == 0], True).items():
            atlar[i]["hp"] = s
    # start/kulvar: (start-1)/(alan-1) - 0.5
    st, sy = col("a6_e_st"), col("a6_e_st_yok")
    if st and sy:
        for i in range(N):
            if sy[i] == 0:
                atlar[i]["st"] = "ic" if st[i] < -1 / 6 else ("dis" if st[i] > 1 / 6 else "orta")
    # Kalman hız figürü eğilimi (yalnız figür geçmişi olan atlar)
    km, ksd = col("a6_k_m"), col("a6_k_sd")
    if km and ksd:
        for i, s in _sira([(i, yuv(km[i])) for i in range(N) if ksd[i] < K_ONSEL_SD - 1e-6], True).items():
            atlar[i]["km"] = s
    # mesafe profili: en iyi figürünü bu mesafeye yakın yapmış mı (figür geçmişi olanlar)
    my, mu = col("a6_m_yakin"), col("a6_m_uzak")
    if my and ksd:
        for i in range(N):
            if ksd[i] >= K_ONSEL_SD - 1e-6:
                continue
            if my[i] >= -0.05:
                atlar[i]["ms"] = "uygun"
            elif my[i] <= -0.999 and mu and mu[i] > 0.15:
                atlar[i]["ms"] = "uzak"
    # gelişim beklentisi (yaş × ara tablosu; alan ortalamasına göre)
    ga, gp = col("a6_g_alan"), col("a6_g_proj")
    if ga and gp and sum(1 for x in gp if x != 0) >= 3:
        for i in range(N):
            if gp[i] != 0 and abs(ga[i]) >= 0.05:
                atlar[i]["gl"] = "ust" if ga[i] > 0 else "alt"
    # yaşa göre kilo (WFA): alan ortalamasına göre belirgin avantaj (≥ 1 kg)
    wf = col("gl_wfa_av")
    if wf:
        for i in range(N):
            if wf[i] >= 1.0:
                atlar[i]["wfa"] = "avantaj"
    # hava: koşu düzeyi yağış beklentisi + ıslak pist formu
    hi, hyok, hu = col("a6_h_islak"), col("a6_h_yok"), col("a6_h_uyum")
    if hi and hyok and any(x == 0 for x in hyok):
        i0 = next(i for i in range(N) if hyok[i] == 0)
        islak = hi[i0] >= ISLAK_ESIK
        kosu["hava"] = "yagisli" if islak else "kuru"
        if islak and hu:
            for i in range(N):
                if abs(hu[i]) >= 0.03:
                    atlar[i]["hv"] = "iyi" if hu[i] > 0 else "zayif"
    return atlar, kosu
