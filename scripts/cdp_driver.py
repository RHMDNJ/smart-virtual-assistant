"""
cdp_driver.py
Driver Chrome minimal lewat Chrome DevTools Protocol.

Dipakai untuk menjalankan dan menguji aplikasi di browser sungguhan tanpa
menambah dependency berat seperti Playwright (yang mengunduh browser sendiri).
Chrome yang sudah terpasang di mesin dipakai apa adanya.

headless=True merender di luar layar (untuk pengujian otomatis),
headless=False membuka jendela yang bisa ditonton.
"""
import json, os, subprocess, sys, time, urllib.request
from websockets.sync.client import connect

PORT = 9222
PROFILE = "/tmp/chrome-sva-profile"   # profil terpisah, tidak mengganggu Chrome harian
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def launch(url, headless=True):
    """headless=False membuka jendela Chrome sungguhan agar prosesnya terlihat."""
    argv = [CHROME, f"--remote-debugging-port={PORT}",
            f"--user-data-dir={PROFILE}", "--no-first-run", "--no-default-browser-check",
            "--window-size=1180,900", "--window-position=80,60"]
    if headless:
        argv.insert(1, "--headless=new")
    argv.append(url)
    subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not headless:
        subprocess.run(["osascript", "-e",
                        'tell application "Google Chrome" to activate'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
            page = [t for t in tabs if t["type"] == "page"]
            if page:
                return page[0]["webSocketDebuggerUrl"]
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("Chrome tidak siap")


class Session:
    def __init__(self, ws_url):
        self.ws = connect(ws_url, max_size=100 * 1024 * 1024)
        self.n = 0

    def send(self, method, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv(timeout=180))
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def js(self, expr):
        r = self.send("Runtime.evaluate", expression=expr,
                      returnByValue=True, awaitPromise=True)
        if r.get("exceptionDetails"):
            d = r["exceptionDetails"]
            pesan = (d.get("exception") or {}).get("description") or d.get("text")
            raise RuntimeError(f"JS error: {pesan}")
        return r.get("result", {}).get("value")

    def shot(self, path):
        r = self.send("Page.captureScreenshot", format="png")
        import base64
        open(path, "wb").write(base64.b64decode(r["data"]))
        print(f"  screenshot -> {path}")
