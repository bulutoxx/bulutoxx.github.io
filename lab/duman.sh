#!/usr/bin/env bash
# 💨 Duman testi: lab/qa.mjs'in hızlı modu (QA_MOD=hizli). Yayın kapısı ve yayın sonrası kontrol bunu kullanır.
#
#   bash lab/duman.sh kur                      # Playwright'ı (sürüm sabit) $QA_PW klasörüne kurar; depo ağacına node_modules koymaz
#   bash lab/duman.sh <site_klasoru> <cikti.json>   # klasörü yerelde (python3 -m http.server) sunup test eder
#   bash lab/duman.sh <https://adres/> <cikti.json> # yayındaki siteyi test eder
#
# QA_PW: Playwright kurulum klasörü (varsayılan $RUNNER_TEMP/pw ya da /tmp/oxx-pw). qa.mjs oraya kopyalanıp çalıştırılır,
# böylece "import playwright" o klasörün node_modules'unu bulur ve Pages'e yüklenen çalışma ağacı kirlenmez.
# Çıkış kodu: 0 = geçti, 1 = alarm, 2 = kullanım/kurulum hatası. Ücretsiz; issue/mail/bildirim açmaz.
set -euo pipefail
KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PW="${QA_PW:-${RUNNER_TEMP:-/tmp}/oxx-pw}"
PW_SURUM="${QA_PW_SURUM:-1.48.2}"

if [ "${1:-}" = "kur" ]; then
  mkdir -p "$PW"
  cd "$PW"
  [ -f package.json ] || npm init -y >/dev/null
  npm i --no-audit --no-fund "playwright@$PW_SURUM" >/dev/null
  npx playwright install --with-deps chromium >/dev/null
  echo "[duman] Playwright $PW_SURUM hazır: $PW"
  exit 0
fi

HEDEF="${1:-}"; CIKTI="${2:-}"
if [ -z "$HEDEF" ] || [ -z "$CIKTI" ]; then
  echo "kullanım: duman.sh kur | duman.sh <site_klasoru|https://adres/> <cikti.json>" >&2; exit 2
fi
case "$CIKTI" in /*) ;; *) CIKTI="$PWD/$CIKTI" ;; esac
mkdir -p "$(dirname "$CIKTI")"

if [ -d "$PW/node_modules/playwright" ]; then
  cp "$KOK/lab/qa.mjs" "$PW/qa.mjs"; BETIK="$PW/qa.mjs"
else
  BETIK="$KOK/lab/qa.mjs"           # lab/node_modules içinde kurulu Playwright (otonom ekip düzeni)
fi

SUNUCU=""
temizlik() { if [ -n "$SUNUCU" ]; then kill "$SUNUCU" 2>/dev/null || true; wait "$SUNUCU" 2>/dev/null || true; fi; }
trap temizlik EXIT

if [ -d "$HEDEF" ]; then
  PORT="${QA_PORT:-$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')}"
  python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$HEDEF" >/dev/null 2>&1 &
  SUNUCU=$!
  for _ in $(seq 1 60); do
    curl -fs -o /dev/null "http://127.0.0.1:$PORT/index.html" && break
    sleep 1
  done
  ADRES="http://127.0.0.1:$PORT/"
else
  ADRES="$HEDEF"
fi

echo "[duman] $ADRES → $CIKTI"
set +e
QA_URL="$ADRES" QA_MOD=hizli QA_CIKTI="$CIKTI" QA_EKRAN="${QA_EKRAN:-}" timeout "${QA_SURE:-600}" node "$BETIK" >"$CIKTI.log" 2>&1
RC=$?
set -e
python3 - "$CIKTI" <<'PY' || true
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as e:
    print(f"[duman] sonuç okunamadı: {e}"); sys.exit(0)
b = d.get("butce") or {}
print(f"[duman] alarm={d.get('alarm')} süre={d.get('sure_sn')} sn pageerror={d.get('pageerror')} taşma={d.get('tasma')} "
      f"index={b.get('index_kb')} KB ilk_veri={b.get('ilk_veri_kb')} KB en_uzun_görev={b.get('en_uzun_gorev_ms')} ms")
for h in (d.get("hatalar") or [])[:15]:
    print("  ✗", h)
PY
if [ "$RC" -ne 0 ] && [ ! -s "$CIKTI" ]; then tail -20 "$CIKTI.log" || true; fi
[ "$RC" -eq 0 ] && exit 0 || exit 1
