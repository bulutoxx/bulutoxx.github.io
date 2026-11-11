#!/usr/bin/env bash
# Playwright (sürüm sabit) + Chromium kurulumu — YH-64.
#   bash lab/pw_kur.sh <klasör>     # <klasör>/node_modules/playwright + ~/.cache/ms-playwright/chromium-*
# Sıra önemli: önce tarayıcı (Playwright CDN, apt gerektirmez; 2 deneme), sonra sistem bağımlılıkları en iyi çaba
# (apt, zaman sınırlı). 2026-11-11 otonom ekip turunda runner'ın apt aynası DNS'i çözülemedi; eski tek komut
# `install --with-deps` bağımlılıkta düşüp tarayıcıyı hiç indirmedi (607 sn, kalite + sohbet koçu çalışmadı).
# ubuntu-latest imajında Chromium'un kütüphaneleri hazır; apt yalnız ek yazı tiplerini getirir.
# Çıkış: 0 = tarayıcı hazır (bağımlılık adımı düşse bile), 1 = paket ya da tarayıcı kurulamadı. Ücretsiz.
set -uo pipefail
HEDEF="${1:?kullanım: pw_kur.sh <klasör>}"
PW_SURUM="${QA_PW_SURUM:-1.48.2}"
BEKLE="${PW_KUR_BEKLE:-20}"
mkdir -p "$HEDEF" && cd "$HEDEF" || exit 1
[ -f package.json ] || npm init -y >/dev/null || exit 1

tekrar() {  # tekrar <ad> <komut...>: 2 deneme
  local i
  for i in 1 2; do
    "$@" && return 0
    echo "[pw_kur] $1 … denemesi $i başarısız" >&2
    [ "$i" = 2 ] || sleep "$BEKLE"
  done
  return 1
}

tekrar npm i --no-audit --no-fund "playwright@$PW_SURUM" >/dev/null || exit 1
tekrar npx playwright install chromium >/dev/null || exit 1
if timeout "${PW_DEPS_SN:-240}" npx playwright install-deps chromium >/dev/null 2>&1; then
  echo "[pw_kur] Playwright $PW_SURUM + Chromium + sistem bağımlılıkları hazır: $HEDEF"
else
  echo "::warning::[pw_kur] sistem bağımlılıkları kurulamadı (apt); tarayıcı kurulu, devam ediliyor"
fi
exit 0
