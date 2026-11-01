"""Build one Reel: ElevenLabs voice-over + rendered scenes -> out/<id>.mp4

Usage: python3 build_reel.py reels/<id>
Needs ELEVENLABS_API_KEY in the environment (skip voice with NO_VOICE=1).
"""
import json, os, subprocess, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
folder = sys.argv[1].rstrip("/")
rid = os.path.basename(folder)
cfg = json.load(open(os.path.join(ROOT, folder, "reel.json")))
work = os.path.join(ROOT, "build", rid)
out_dir = os.path.join(ROOT, "out")
os.makedirs(work, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
env = dict(os.environ, FPS=os.environ.get("FPS", "30"), CRF=os.environ.get("CRF", "21"))


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


# 1. Voice-over
voice = None
if cfg.get("voiceover") and not os.environ.get("NO_VOICE"):
    key = os.environ["ELEVENLABS_API_KEY"]
    vid = cfg.get("voice_id", "CwhRBWXzGAHq8TQ4Fs17")
    body = {
        "text": cfg["voiceover"],
        "model_id": cfg.get("model_id", "eleven_multilingual_v2"),
        "voice_settings": cfg.get("voice_settings", {"stability": 0.45, "similarity_boost": 0.8, "style": 0.3}),
    }
    if cfg.get("language_code"):
        body["language_code"] = cfg["language_code"]
    body = json.dumps(body).encode()
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128",
                                 data=body, headers={"xi-api-key": key, "Content-Type": "application/json"})
    voice = os.path.join(work, "voice.mp3")
    with urllib.request.urlopen(req, timeout=180) as r, open(voice, "wb") as f:
        f.write(r.read())
    print(f"voice-over: {duration(voice):.1f}s", flush=True)

# 2. Render scenes, two at a time
scenes = cfg["scenes"]
def render(i_s):
    i, s = i_s
    out = os.path.join(work, f"scene{i:02d}.mp4")
    page = f"{folder}/{s['file']}"
    run(["python3", os.path.join(ROOT, "render.py"), page, out, "video", str(s["seconds"])],
        env=dict(env, PORT=str(8800 + i)))
    return out
with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "2"))) as ex:
    parts = list(ex.map(render, enumerate(scenes)))

# 3. Stitch
lst = os.path.join(work, "list.txt")
open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
silent = os.path.join(work, "video.mp4")
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])

# 4. Add voice (and optional music) under the video
final = os.path.join(out_dir, f"{rid}.mp4")
vlen = duration(silent)
if voice:
    alen = duration(voice)
    if alen > vlen:
        print(f"WARNING: voice-over ({alen:.1f}s) is longer than the video ({vlen:.1f}s); it gets cut off", flush=True)
    delay = int(float(cfg.get("voice_delay", 0.3)) * 1000)
    music = cfg.get("music")
    if music:
        fc = (f"[1:a]adelay={delay}|{delay},apad[v];[2:a]volume={cfg.get('music_volume', 0.15)}[m];"
              f"[v][m]amix=inputs=2:duration=first:dropout_transition=0[a]")
        ins = ["-i", voice, "-stream_loop", "-1", "-i", os.path.join(ROOT, music)]
    else:
        fc = f"[1:a]adelay={delay}|{delay},apad[a]"
        ins = ["-i", voice]
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, *ins, "-filter_complex", fc,
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{vlen:.3f}",
         "-movflags", "+faststart", final])
else:
    os.replace(silent, final)
print("DONE", final, flush=True)
