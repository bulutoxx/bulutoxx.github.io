# v3 bilgi deneyi: hız figürünün gün değişkeni "sinif" yöntemiyle (kazanan − par − sınıf ofseti) hesaplanırsa?
# Yayın tarifi "projeksiyon"dur; bu betik yalnız kıyas için (data/at/deneyler_v3.json'a "hz_sinif_kiyas" ekler).
import json, os, sys

import numpy as np

BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import veri, ozellik as O  # noqa: E402
import deney3 as D  # noqa: E402


def main():
    kosular, _ = veri.sonuclari_yukle()
    gr = list(O.SECILI_GRUPLAR) + ["hiz3"]
    sonuc = {}
    for yontem in ("projeksiyon", "sinif"):
        O.HZ_YONTEM = yontem
        T, _ = O.tablo_kur(kosular, adlar=O.TUM_ADLAR)
        r, v = D.olc(T, kosular, gr, henery=False)
        sonuc[yontem] = (r, v)
        print(yontem, r["model"], r["harman"], flush=True)
    (rp, vp), (rs, vs) = sonuc["projeksiyon"], sonuc["sinif"]
    yol = os.path.join(BURA, "..", "..", "data", "at", "deneyler_v3.json")
    dj = json.load(open(yol, encoding="utf-8"))
    dj["hz_sinif_kiyas"] = {"aciklama": "gün değişkeni 'sinif' yöntemi − 'projeksiyon' (yayın) farkı; + = sinif kötü",
                            "sinif_model": rs["model"], "sinif_harman": rs["harman"],
                            "fark_model": D.fark(vs, vp, "model"), "fark_harman": D.fark(vs, vp, "harman")}
    json.dump(dj, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(dj["hz_sinif_kiyas"])


if __name__ == "__main__":
    main()
