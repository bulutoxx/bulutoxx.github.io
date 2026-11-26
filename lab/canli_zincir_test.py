import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import canli_zincir as z
r = lambda i, st: {"databaseId": i, "status": st}
assert z.karar([], "1")[0] is True
assert z.karar([r(1, "in_progress"), r(0, "completed")], "1")[0] is True        # kendi turu sayılmaz
assert z.karar([r(1, "in_progress"), r(2, "queued")], "1")[0] is False          # bekleyen var
assert z.karar([r(1, "in_progress"), r(2, "pending")], 1)[0] is False
assert z.karar([r(1, "in_progress"), r(2, "in_progress")], "1")[0] is False     # başka çalışan
assert z.karar([r(1, "in_progress")], "1", bayrak=False)[0] is False            # bayrak kapalı
# gh yoksa / hata verirse sessizce 0
os.environ["PATH"] = "/yok"
assert z.main() == 0
print("canli_zincir_test: 7/7 geçti")
