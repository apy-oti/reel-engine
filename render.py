import sys, os, threading, subprocess, time, functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
page_name, out = sys.argv[1], sys.argv[2]
FPS = int(os.environ.get("FPS","60"))
mode = sys.argv[3] if len(sys.argv) > 3 else "video"   # "video" or comma list of stills
DUR = float(sys.argv[4]) if len(sys.argv) > 4 else 4.0

class Q(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("PORT","8765"))), functools.partial(Q, directory=ROOT))
threading.Thread(target=srv.serve_forever, daemon=True).start()

with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
    pg.on("console", lambda m: print("console:", m.text) if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: print("pageerror:", e))
    pg.goto("http://127.0.0.1:" + os.environ.get("PORT","8765") + "/" + page_name)
    pg.wait_for_function("window.READY===true", timeout=60000)
    if mode != "video":
        for t in mode.split(","):
            pg.evaluate(f"window.renderAt({t})")
            pg.screenshot(path=f"{out}_{t}.jpg", type="jpeg", quality=92, timeout=180000)
        b.close(); sys.exit()
    tmp = out.replace(".mp4", ".tmp.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", os.environ.get("CRF","17"), "-pix_fmt", "yuv420p", "-r", str(FPS),
                           "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
    n = int(DUR * FPS); t0 = time.time()
    for i in range(n):
        pg.evaluate(f"window.renderAt({i / FPS})")
        ff.stdin.write(pg.screenshot(type="jpeg", quality=92, timeout=180000))
        if i % 30 == 0: print(i, round(time.time() - t0, 1), flush=True)
    ff.stdin.close()
    if ff.wait() == 0: os.replace(tmp, out)
    b.close()
