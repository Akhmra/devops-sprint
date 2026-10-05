import time
import urllib.request


def timed(url):
    start = time.time()                      # засекли время до запроса
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, int((time.time() - start) * 1000)   # код и миллисекунды
    except Exception:
        return None, -1                      # не дошли — ошибку прячем в (None, -1)


print(timed("https://pypi.org"))
print(timed("https://nonexistent-host-xyz.local"))
