"""🗄️ Derin arşiv botu (her gece, GitHub Actions — otonom ekip).
Motorun season.json'u yalnız son ~450 günü tutar. Bu bot, ZATEN kullandığımız ücretsiz kaynaktan (football-data.co.uk)
BİTMİŞ eski sezonları bir kez indirir ve data/derin/<lig>-<sezon>.json olarak saklar (sonuç + ortalama oranlar).
  - Bitmiş sezon dosyası bir kez yazılır, bir daha değişmez (git'te günlük büyüme yok).
  - Ağ yoksa season.json'daki bitmiş sezonlardan geçici ('tam': false) dosya kurar; ağ gelince kaynaktan tamamlanır.
  - Anahtar/ücretli API kullanılmaz; ham API-Football yanıtı yazılmaz.
Kullanan: scripts/update.py → calibrate_served() (olasılık kalibrasyonu daha çok maçla öğrenilir; ml80'den beri kabul, derin arşiv + sezon üzerinde yıllık yürüyen pencere katlarıyla)."""
import json, os, sys, time, collections
from datetime import date
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data"); OUT = os.path.join(DATA, "derin")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
SEZON = int(os.environ.get("DERIN_SEZON", "5"))          # kaç bitmiş sezon geriye
BUDGET = float(os.environ.get("DERIN_BUDGET", "900"))    # sn
T0 = time.time()

def row(m):
    o = m.get("odds") or [None, None, None]; ou = m.get("ou") or [None, None]
    return [m["d"], m["h"], m["a"], m["ft"][0], m["ft"][1], o[0], o[1], o[2], ou[0], ou[1]]

def jl(p):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return None

def write_shard(lg, s, ms, kaynak, tam):
    """Yalnız içerik değiştiyse yaz. Tam (kaynaktan) dosya, geçici dosyanın yerini alır; tersi olmaz."""
    p = os.path.join(OUT, f"{lg}-{s}.json"); old = jl(p)
    rows = sorted({(r[0], r[1], r[2]): r for r in (row(m) for m in ms if m.get("ft"))}.values())
    if not rows: return False
    if old and (old.get("tam") and not tam): return False
    if old and old.get("tam") == tam and old.get("n", 0) >= len(rows): return False
    os.makedirs(OUT, exist_ok=True)
    json.dump({"lg": lg, "sezon": s, "kaynak": kaynak, "tam": tam, "n": len(rows),
               "alanlar": ["tarih", "ev", "deplasman", "ev_gol", "dep_gol", "o1", "oX", "o2", "o2.5ust", "o2.5alt"], "m": rows},
              open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    return True

def main():
    import update as U
    S = jl(os.path.join(DATA, "season.json")) or {}
    today = date.today(); _, y = U.season_code(today)
    log = {}; wrote = 0; net_ok = True
    for lg, (kind, code, name) in U.LEAGUES.items():
        d = S.get(lg, {}); ms = d.get("matches", [])
        known = sorted({m["h"] for m in ms} | {m["a"] for m in ms})
        bys = collections.defaultdict(list)
        for m in ms: bys[m["season"]].append(m)
        cur = y if kind == "main" else (max(bys) if bys else today.year)
        want = list(range(cur - SEZON, cur))
        have = {s for s in want if (jl(os.path.join(OUT, f"{lg}-{s}.json")) or {}).get("tam")}
        todo = [s for s in want if s not in have]
        # 1) kaynaktan (bir kez)
        if todo and net_ok and time.time() - T0 < BUDGET:
            try:
                if kind == "main":
                    for s in todo:
                        if time.time() - T0 > BUDGET: break
                        try:
                            got = U.download(lg, f"{s % 100:02d}{(s + 1) % 100:02d}", s, known)
                            if len(got) >= 50: wrote += write_shard(lg, s, got, "football-data", True); log[f"{lg}-{s}"] = len(got)
                        except Exception as e:
                            log[f"{lg}-{s}"] = f"hata: {e.__class__.__name__}"
                            if e.__class__.__name__ in ("URLError", "TimeoutError", "ProxyError"): net_ok = False; break
                else:
                    got = U.download_new(lg, known, "2000-01-01")
                    g2 = collections.defaultdict(list)
                    for m in got: g2[m["season"]].append(m)
                    cur_src = max(g2) if g2 else cur          # kaynağa göre süren sezon tam değildir
                    for s in todo:
                        if s < cur_src and len(g2.get(s, [])) >= 50:
                            wrote += write_shard(lg, s, g2[s], "football-data", True); log[f"{lg}-{s}"] = len(g2[s])
            except Exception as e:
                log[lg] = f"hata: {e.__class__.__name__}"; net_ok = False
        # 2) ağ yoksa: season.json'daki bitmiş sezonlardan geçici dosya (veri kaybolmasın)
        for s in todo:
            if s in bys and len(bys[s]) >= 50 and not (jl(os.path.join(OUT, f"{lg}-{s}.json")) or {}).get("tam"):
                wrote += write_shard(lg, s, bys[s], "season.json", False)
    # özet (yalnız değiştiyse yazılır)
    idx = {}
    for f in sorted(os.listdir(OUT)) if os.path.isdir(OUT) else []:
        if f.endswith(".json") and f != "index.json":
            D = jl(os.path.join(OUT, f)) or {}; idx[f[:-5]] = [D.get("n", 0), bool(D.get("tam"))]
    ozet = {"toplam": sum(v[0] for v in idx.values()), "dosya": len(idx), "tam": sum(1 for v in idx.values() if v[1]), "parca": idx}
    old = jl(os.path.join(OUT, "index.json")) or {}
    if {k: old.get(k) for k in ozet} != ozet:
        os.makedirs(OUT, exist_ok=True)
        json.dump(dict(ozet, guncel=today.isoformat()), open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"Derin arşiv: {ozet['toplam']} maç, {ozet['dosya']} dosya ({ozet['tam']} tam); bu çalıştırmada {wrote} dosya yazıldı; ağ {'var' if net_ok else 'yok'}", flush=True)
    if log: print("İndirme:", json.dumps(log, ensure_ascii=False)[:1500], flush=True)

if __name__ == "__main__":
    try: main()
    except Exception as e:
        import traceback; traceback.print_exc(); print("derin arşiv atlandı:", e)
