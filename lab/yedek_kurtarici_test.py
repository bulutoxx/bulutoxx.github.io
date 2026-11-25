import os, sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yedek_kurtarici as y
S = datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc)
r = lambda ts, st="completed": {"createdAt": ts, "status": st}
assert y.karar([], S)[0] is True
assert y.karar([r("2026-11-25T09:30:00Z")], S)[0] is False           # 30 dk
assert y.karar([r("2026-11-25T09:10:00Z")], S)[0] is True            # 50 dk
assert y.karar([r("2026-11-25T02:20:00Z"), r("2026-11-25T09:50:00Z")], S)[0] is False
assert y.karar([r("2026-11-25T02:20:00Z"), r("2026-11-25T09:59:00Z", "queued")], S)[0] is False
assert y.karar([r("2026-11-25T02:20:00Z", "in_progress")], S)[0] is False
# gh yoksa / hata verirse sessizce 0
os.environ["PATH"] = "/yok"
assert y.main() == 0
print("yedek_kurtarici_test: 7/7 geçti")
