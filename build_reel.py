"""Build one Reel: per-scene ElevenLabs voice lines + rendered scenes + music -> out/<id>.mp4

Usage: python3 build_reel.py reels/<id>
Needs ELEVENLABS_API_KEY (skip voice with NO_VOICE=1).

reel.json:
  voice_id, model_id (optional), voice_settings (optional)
  music: "music/track.mp3" or "auto" (picks one from music/ by reel id), music_volume (default 0.12)
  scenes: [{file, seconds, say, say_at (seconds into the scene, default 0.25)}]
Each scene's line starts when the scene starts. If a line is longer than its scene,
the scene is rendered longer (it holds on its last frame) so voice and visuals stay together.
"""
import glob, hashlib, json, os, re, subprocess, sys, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
folder = sys.argv[1].rstrip("/")
rid = os.path.basename(folder)
cfg = json.load(open(os.path.join(ROOT, folder, "reel.json")))
work = os.path.join(ROOT, "build", rid)
out_dir = os.path.join(ROOT, "out")
os.makedirs(work, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
env = dict(os.environ, FPS=os.environ.get("FPS", "30"), CRF=os.environ.get("CRF", "21"))
scenes = cfg.get("scenes", [])
SARAH = "EXAVITQu4vr4xnSDxMaL"
JASON = "Xgbhok2GeC7jChQ5TJEl"  # Dutch, confident and direct (default)
LIAM = "TX3LPaxmHKxFdv7VOQHJ"


CACHE = os.path.join(ROOT, ".cache"); os.makedirs(CACHE, exist_ok=True)


def api(req, timeout=240):
    """Call ElevenLabs and show the real reason on errors (quota, bad key...)."""
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        if "quota" in body.lower() or "credits" in body.lower():
            sys.exit(f"ELEVENLABS OUT OF CREDITS: {body}")
        sys.exit(f"ElevenLabs error {e.code}: {body}")


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def tts(text, path, prev_text=None, next_text=None):
    if os.environ.get("FAKE_TTS"):  # local test: a beep as long as the text
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=f=440:d={len(text)/14:.2f}", path]); return
    body = {
        "text": text,
        "model_id": cfg.get("model_id", "eleven_multilingual_v2"),
        "voice_settings": cfg.get("voice_settings", {"stability": 0.5, "similarity_boost": 0.8, "style": 0.25, "use_speaker_boost": True}),
    }
    # keeps intonation consistent across the separate lines
    if prev_text: body["previous_text"] = prev_text
    if next_text: body["next_text"] = next_text
    if cfg.get("language_code"): body["language_code"] = cfg["language_code"]
    vid = cfg.get("voice_id", SARAH)
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128",
                                 data=json.dumps(body).encode(),
                                 headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"})
    with api(req, 180) as r, open(path, "wb") as f:
        f.write(r.read())


# Sound effects: ElevenLabs sound generation, one file per distinct prompt
DEFAULT_SFX = {
    "cut": "short fast cinematic whoosh transition, clean, no music",
    "hit": "deep cinematic boom impact with short tail, clean",
    "tick": "single soft elegant UI tick, crisp and minimal, premium interface sound",
    "click": "satisfying soft glassy digital click pop, premium app UI sound",
    "thud": "soft deep sub thump, elegant and short, no reverb",
    "shimmer": "fast bright cinematic light sweep whoosh with sparkle shimmer",
}
def sfx_file(prompt, secs):
    p = os.path.join(CACHE, "sfx_" + hashlib.md5(f"{prompt}|{secs}".encode()).hexdigest()[:12] + ".mp3")
    if os.path.exists(p): return p
    if os.environ.get("FAKE_TTS"):
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"anoisesrc=d={secs}:a=0.3", p]); return p
    req = urllib.request.Request("https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128",
                                 data=json.dumps({"text": prompt, "duration_seconds": secs, "prompt_influence": 0.6}).encode(),
                                 headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"})
    with api(req, 180) as r, open(p, "wb") as f:
        f.write(r.read())
    return p


def hit_events(hp, offset):
    out, last = [], -1.0
    if not (cfg.get("hit_sfx", True) and os.path.exists(hp)): return out
    for ht, decay in sorted((float(a), b) for a, b in json.load(open(hp)).items()):
        if ht - last < 0.08: continue
        last = ht
        kind = ("shimmer" if decay >= 25 else "tick" if decay >= 18 else "click" if decay >= 12 else "thud" if decay > 5 else "hit")
        secs = {"shimmer": 1.2, "hit": 1.5, "thud": 0.8}.get(kind, 0.5)
        vol = cfg.get("hit_volume", 0.35) * (1.25 if kind == "hit" else 1)
        out.append((offset + ht, sfx_file(DEFAULT_SFX[kind], secs), vol))
    return out


def hook_frames(hook, dur):
    """Cut the hook clip into JPG frames (headless Chromium can't reliably play video)."""
    d = os.path.join(work, "hook"); os.makedirs(d, exist_ok=True)
    fps = int(env["FPS"])
    run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", hook, "-t", f"{dur:.3f}", "-vf", f"fps={fps},scale=1080:1920",
         "-q:v", "3", os.path.join(d, "%04d.jpg")])
    n = len(glob.glob(os.path.join(d, "*.jpg")))
    return {"frames": "/" + os.path.relpath(d, ROOT) + "/", "fps": fps, "count": n}


def pick_hook():
    """Random hook from hooks/, never repeating until every hook was used once. Set "hook": false to skip,
    or "hook": "name" to force one."""
    if cfg.get("hook", True) is False: return None
    clips = sorted(glob.glob(os.path.join(ROOT, "hooks", "*.webm")))
    if not clips: return None
    if isinstance(cfg.get("hook"), str):
        m = [c for c in clips if cfg["hook"] in os.path.basename(c)]
        if m: return m[0]
    up = os.path.join(ROOT, "hooks", "used.json")
    used = json.load(open(up)) if os.path.exists(up) else {}
    if rid in used and os.path.exists(os.path.join(ROOT, "hooks", used[rid])):  # rebuild keeps its hook
        return os.path.join(ROOT, "hooks", used[rid])
    taken = set(used.values())
    free = [c for c in clips if os.path.basename(c) not in taken] or clips
    if len(free) == len(clips): used = {}  # new round
    import random
    c = random.Random(rid).choice(free)
    used[rid] = os.path.basename(c)
    json.dump(used, open(up, "w"), indent=1)
    return c


def tts_ts(text, prev_t=None, next_t=None):
    """TTS with character timings. Returns (mp3 path, starts, ends)."""
    import base64
    key = hashlib.md5(json.dumps([text, cfg.get("voice_id", LIAM), cfg.get("model_id"), cfg.get("voice_settings"), prev_t, next_t]).encode()).hexdigest()[:14]
    p = os.path.join(CACHE, f"line_{key}.mp3"); pj = p[:-4] + ".json"
    if os.path.exists(p) and os.path.exists(pj) and not os.environ.get("FAKE_TTS"):
        al = json.load(open(pj)); return p, al["s"], al["e"]
    if os.environ.get("FAKE_TTS"):
        p = os.path.join(work, f"line_{key}.mp3")
        cs = [i / 13 for i in range(len(text))]; ce = [c + 1 / 13 for c in cs]
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=f=200:d={len(text)/13:.2f}", p]); return p, cs, ce
    body = {"text": text, "model_id": cfg.get("model_id", "eleven_multilingual_v2"),
            "voice_settings": cfg.get("voice_settings", {"stability": 0.32, "similarity_boost": 0.8, "style": 0.6, "use_speaker_boost": True})}
    if prev_t: body["previous_text"] = prev_t
    if next_t: body["next_text"] = next_t
    if cfg.get("language_code"): body["language_code"] = cfg["language_code"]
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{cfg.get('voice_id', LIAM)}/with-timestamps?output_format=mp3_44100_128",
                                 data=json.dumps(body).encode(), headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"})
    with api(req) as r:
        res = json.loads(r.read())
    open(p, "wb").write(base64.b64decode(res["audio_base64"]))
    al = res["alignment"]
    json.dump({"s": al["character_start_times_seconds"], "e": al["character_end_times_seconds"]}, open(pj, "w"))
    return p, al["character_start_times_seconds"], al["character_end_times_seconds"]


def cinematic():
    """Cinematic kinetic type: short excited lines, key words slam in as they are spoken, music in the gaps."""
    beats = cfg["beats"]
    texts = [b["say"].strip() for b in beats]
    hook = pick_hook()
    H = 0.0
    if hook:
        H = round(min(duration(hook), float(cfg.get("hook_max", 4.5))), 3)
    t = H + 0.15
    words, bt, ev = [], [], []
    for i, tx in enumerate(texts):
        p, cs, ce = tts_ts(tx, " ".join(texts[:i])[-300:] or None, " ".join(texts[i + 1:])[:300] or None)
        lead = float(beats[i].get("lead", 0.12))
        start = t
        ev.append((start + lead, p, 1.0))
        j = 0
        while j < len(tx):
            if tx[j] == " ": j += 1; continue
            k = j
            while k < len(tx) and tx[k] != " ": k += 1
            words.append({"w": tx[j:k], "s": round(start + lead + cs[min(j, len(cs)-1)], 3), "e": round(start + lead + ce[min(k-1, len(ce)-1)], 3), "beat": i})
            j = k
        t = start + lead + duration(p) + float(beats[i].get("gap", cfg.get("gap", 0.55)))
        bt.append({"start": round(start, 3), "end": round(t, 3)})
    cta = cfg.get("cta")
    end_start = round(t, 3)
    total = round(end_start + float(cta.get("seconds", 2.8)) if cta else t + 0.3, 3)
    tm = {"words": words, "beats": bt, "end_start": end_start, "duration": total}
    if hook:
        tm["hook"] = {"dur": H, "text": cfg.get("hook_text", texts[0]).rstrip("."), **hook_frames(hook, H)}
        print("hook:", os.path.basename(hook), H, flush=True)
    tpath = os.path.join(work, "timing.json"); json.dump(tm, open(tpath, "w"))
    rel_t = os.path.relpath(tpath, ROOT)
    jobs = int(os.environ.get("JOBS", "2")); n = max(1, min(jobs, int(total // 6) or 1)); seg = total / n
    def rpart(k):
        out = os.path.join(work, f"part{k:02d}.mp4")
        run(["python3", os.path.join(ROOT, "render.py"), f"cinematic.html?reel={folder}&timing={rel_t}", out, "video", f"{seg:.3f}"],
            env=dict(env, PORT=str(8870 + k), START=f"{k*seg:.4f}", HITS_ALL="1"))
        return out
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        parts = list(ex.map(rpart, range(n)))
    lst = os.path.join(work, "list.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    silent = os.path.join(work, "video.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])
    if hook:
        ha = hook[:-5] + ".mp3"
        if os.path.exists(ha): ev.append((0.0, ha, cfg.get("hook_volume", 0.55)))
    if cfg.get("sfx", True):
        sv = cfg.get("sfx_volume", 0.4)
        cuts = [b["start"] for b in bt[1:]] + ([end_start] if cta else []) + ([H] if hook else [])
        for c in cuts: ev.append((max(c - 0.2, 0), sfx_file(DEFAULT_SFX["cut"], 1.0), sv))
        ev += hit_events(os.path.join(work, "part00.hits.json"), 0.0)
    return silent, duration(silent), ev


def explainer():
    """Faceless explainer: one voice track with word timings, captions, UI visuals, end card."""
    import base64
    LEAD = 0.3
    beats = cfg["beats"]
    texts = [b["say"].strip() for b in beats]
    full = " ".join(texts)
    voice = os.path.join(work, "voice.mp3")
    if os.environ.get("FAKE_TTS"):
        cs = [i / 14 for i in range(len(full))]; ce = [c + 1 / 14 for c in cs]
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=f=330:d={len(full)/14:.2f}", voice])
    else:
        body = {"text": full, "model_id": cfg.get("model_id", "eleven_multilingual_v2"),
                "voice_settings": cfg.get("voice_settings", {"stability": 0.45, "similarity_boost": 0.8, "style": 0.3, "use_speaker_boost": True, "speed": 1.08})}
        if cfg.get("language_code"): body["language_code"] = cfg["language_code"]
        req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{cfg.get('voice_id', JASON)}/with-timestamps?output_format=mp3_44100_128",
                                     data=json.dumps(body).encode(),
                                     headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"})
        key = hashlib.md5(json.dumps([full, cfg.get("voice_id", JASON), cfg.get("model_id"), cfg.get("voice_settings")]).encode()).hexdigest()[:14]
        cj = os.path.join(CACHE, f"voice_{key}.json")
        if os.path.exists(cj):
            res = json.load(open(cj))
        else:
            with api(req) as r:
                res = json.loads(r.read())
            json.dump(res, open(cj, "w"))
        open(voice, "wb").write(base64.b64decode(res["audio_base64"]))
        al = res.get("normalized_alignment") or res["alignment"]
        if "".join(al["characters"]) != full: al = res["alignment"]
        cs, ce = al["character_start_times_seconds"], al["character_end_times_seconds"]
    # words with times
    words, i = [], 0
    while i < len(full):
        if full[i] == " ": i += 1; continue
        j = i
        while j < len(full) and full[j] != " ": j += 1
        words.append({"w": full[i:j], "s": round(cs[min(i, len(cs)-1)] + LEAD, 3), "e": round(ce[min(j-1, len(ce)-1)] + LEAD, 3)})
        i = j
    # beat starts (char offset of each beat)
    starts, off = [], 0
    for k, tx in enumerate(texts):
        starts.append({"start": 0.0 if k == 0 else round(max(cs[min(off, len(cs)-1)] + LEAD - 0.12, 0), 3)})
        off += len(tx) + 1
    voice_end = duration(voice) + LEAD
    cta = cfg.get("cta")
    end_start = round(voice_end + 0.35, 3)
    total = round(end_start + float(cta.get("seconds", 2.6)) if cta else voice_end + 0.8, 3)
    tm = {"words": words, "beats": starts, "voice_end": round(voice_end, 3), "end_start": end_start, "duration": total}
    hook = pick_hook()
    if hook:
        first = re.split(r"(?<=[.!?])\s", texts[0])[0]
        hd = round(min(duration(hook), float(cfg.get("hook_max", 4.5))), 3)
        tm["hook"] = {"dur": hd, "text": cfg.get("hook_text", first).rstrip("."), **hook_frames(hook, hd)}
        print("hook:", os.path.basename(hook), tm["hook"]["dur"], flush=True)
    tpath = os.path.join(work, "timing.json"); json.dump(tm, open(tpath, "w"))
    rel_t = os.path.relpath(tpath, ROOT)
    # render in parallel chunks
    jobs = int(os.environ.get("JOBS", "2")); n = max(1, min(jobs, int(total // 6) or 1)); seg = total / n
    def rpart(k):
        out = os.path.join(work, f"part{k:02d}.mp4")
        run(["python3", os.path.join(ROOT, "render.py"), f"explainer.html?reel={folder}&timing={rel_t}", out, "video", f"{seg:.3f}"],
            env=dict(env, PORT=str(8850 + k), START=f"{k*seg:.4f}", HITS_ALL="1"))
        return out
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        parts = list(ex.map(rpart, range(n)))
    lst = os.path.join(work, "list.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    silent = os.path.join(work, "video.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])
    ev = [(LEAD, voice, 1.0)]
    if hook:
        ha = hook[:-5] + ".mp3"
        if os.path.exists(ha): ev.append((0.0, ha, cfg.get("hook_volume", 0.55)))
        if cfg.get("sfx", True) and not os.environ.get("NO_VOICE"):
            ev.append((max(tm["hook"]["dur"] - 0.2, 0), sfx_file(DEFAULT_SFX["cut"], 1.0), cfg.get("sfx_volume", 0.45)))
    if not os.environ.get("NO_VOICE") and cfg.get("sfx", True):
        sv = cfg.get("sfx_volume", 0.45)
        for b in starts[1:]:
            ev.append((max(b["start"] - 0.2, 0), sfx_file(DEFAULT_SFX["cut"], 1.0), sv))
        if cta:
            ev.append((max(end_start - 0.2, 0), sfx_file(DEFAULT_SFX["cut"], 1.0), sv))
            ev.append((end_start + 0.05, sfx_file(DEFAULT_SFX["hit"], 1.5), sv))
        ev += hit_events(os.path.join(work, "part00.hits.json"), 0.0)
    return silent, duration(silent), ev


def scene_reel():
    # 1. Voice lines, one per scene
    use_voice = not os.environ.get("NO_VOICE")
    lines = [s.get("say", "").strip() for s in scenes]
    clips = [None] * len(scenes)
    if use_voice:
        for i, text in enumerate(lines):
            if not text: continue
            p = os.path.join(work, f"say{i:02d}.mp3")
            prev_t = " ".join(t for t in lines[:i] if t)[-300:] or None
            next_t = " ".join(t for t in lines[i + 1:] if t)[:300] or None
            tts(text, p, prev_t, next_t)
            clips[i] = p

    # 2. Final scene lengths: long enough for their line
    for i, s in enumerate(scenes):
        s["_at"] = float(s.get("say_at", 0.25))
        s["_len"] = float(s["seconds"])
        if clips[i]:
            need = s["_at"] + duration(clips[i]) + 0.35
            if need > s["_len"]:
                print(f"scene {i+1}: line needs {need:.1f}s, extending from {s['_len']:.1f}s", flush=True)
                s["_len"] = round(need, 2)

    # 3. Render scenes (a scene shown longer than designed holds its final frame)
    def render(i_s):
        i, s = i_s
        out = os.path.join(work, f"scene{i:02d}.mp4")
        run(["python3", os.path.join(ROOT, "render.py"), f"{folder}/{s['file']}", out, "video", str(s["seconds"])],
            env=dict(env, PORT=str(8800 + i)))
        extra = s["_len"] - float(s["seconds"])
        if extra > 0.01:
            held = out.replace(".mp4", ".hold.mp4")
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", out, "-vf", f"tpad=stop_mode=clone:stop_duration={extra:.3f}",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", env["CRF"], "-pix_fmt", "yuv420p", held])
            os.replace(held, out)
        return out
    with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "2"))) as ex:
        parts = list(ex.map(render, enumerate(scenes)))

    lst = os.path.join(work, "list.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    silent = os.path.join(work, "video.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])
    vlen = duration(silent)

    # events: (time in reel, file, volume)
    events = []
    t = 0.0
    for i, s in enumerate(scenes):
        if clips[i]:
            events.append((t + s["_at"], clips[i], 1.0))
        if use_voice and cfg.get("sfx", True):
            if i > 0:  # whoosh just before each cut lands
                events.append((max(t - 0.25, 0), sfx_file(cfg.get("sfx_cut", DEFAULT_SFX["cut"]), 1.0), cfg.get("sfx_volume", 0.5)))
            # sounds on the animation hits recorded while rendering (dots landing, words snapping in)
            events += hit_events(os.path.join(work, f"scene{i:02d}.hits.json"), t)
            for e in s.get("sfx", []):  # optional extra effects: {"t": 1.2, "prompt": "..."} or {"t":1.2,"type":"hit"}
                prompt = e.get("prompt") or DEFAULT_SFX[e.get("type", "hit")]
                events.append((t + float(e["t"]), sfx_file(prompt, float(e.get("seconds", 1.5))), e.get("volume", cfg.get("sfx_volume", 0.5))))
        t += s["_len"]
    if use_voice and cfg.get("sfx", True) and not any(s.get("sfx") for s in scenes[-1:]):
        events.append((t - scenes[-1]["_len"] + 0.1, sfx_file(DEFAULT_SFX["hit"], 1.5), cfg.get("sfx_volume", 0.5)))

    return silent, vlen, events


if cfg.get("type") == "explainer":
    silent, vlen, events = explainer()
elif cfg.get("type") == "cinematic":
    silent, vlen, events = cinematic()
else:
    silent, vlen, events = scene_reel()

# 4. Audio: each line placed at its scene start, music underneath with fade in/out
music = cfg.get("music")
if music == "auto":
    tracks = sorted(glob.glob(os.path.join(ROOT, "music", "*.mp3")))
    music = tracks[int(hashlib.md5(rid.encode()).hexdigest(), 16) % len(tracks)] if tracks else None
elif music:
    music = os.path.join(ROOT, music)

inputs, filters, mix = [], [], []
k = 0
for at, f, vol in events:
    k += 1; ms = int(at * 1000)
    inputs += ["-i", f]
    filters.append(f"[{k}:a]aformat=channel_layouts=stereo,adelay={ms}|{ms},volume={vol}[a{k}]")
    mix.append(f"[a{k}]")
if music:
    k += 1
    inputs += ["-stream_loop", "-1", "-i", music]
    vol = cfg.get("music_volume", 0.12)
    filters.append(f"[{k}:a]aformat=channel_layouts=stereo,atrim=0:{vlen:.3f},volume={vol},afade=t=in:d=0.8,afade=t=out:st={max(vlen-1.5,0):.3f}:d=1.5[m]")
    mix.append("[m]")

final = os.path.join(out_dir, f"{rid}.mp4")
if mix:
    filters.append(f"{''.join(mix)}amix=inputs={len(mix)}:duration=longest:dropout_transition=0:normalize=0,"
                   f"alimiter=limit=0.95,apad[a]")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, *inputs, "-filter_complex", ";".join(filters),
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{vlen:.3f}",
         "-movflags", "+faststart", final])
else:
    os.replace(silent, final)

# keep files small enough for Instagram and Metricool
if os.path.getsize(final) > 60 * 1024 * 1024:
    small = final.replace(".mp4", ".small.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", final, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
         "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", small])
    os.replace(small, final)
    print(f"compressed to {os.path.getsize(final)/1e6:.0f} MB", flush=True)
print(f"DONE {final} ({vlen:.1f}s)", flush=True)
