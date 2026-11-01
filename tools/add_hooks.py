"""Add hook clips to the library: python3 tools/add_hooks.py video1.mp4 [video2.mp4 ...]

Long videos (a compilation of hooks) are split at every scene change.
Each hook is saved as hooks/<name>.webm (1080x1920, VP9, no sound) + hooks/<name>.mp3 (its sound).
Pieces shorter than 0.8s are skipped, longer than 5s are cut to 5s.
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "hooks")
os.makedirs(OUT, exist_ok=True)


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True, check=True).stdout.strip())


def slug(s):
    s = re.sub(r"^[0-9a-f]{8}-", "", os.path.splitext(os.path.basename(s))[0])
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "hook"


def cuts(p, total):
    if total <= 6: return [(0.0, total)]
    r = subprocess.run(["ffmpeg", "-nostdin", "-i", p, "-vf", "select='gt(scene,0.35)',showinfo", "-f", "null", "-"],
                       capture_output=True, text=True)
    ts = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    pts = [0.0] + [t for t in ts if t > 0.3] + [total]
    return [(a, b) for a, b in zip(pts, pts[1:]) if b - a >= 0.8]


n = 0
for src in sys.argv[1:]:
    total = dur(src)
    for k, (a, b) in enumerate(cuts(src, total)):
        b = min(b, a + 5.0)
        name = slug(src) + (f"-{k+1:03d}" if total > 6 else "")
        base = os.path.join(OUT, name)
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30"
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src, "-an",
                        "-vf", vf, "-c:v", "libvpx-vp9", "-crf", "36", "-b:v", "0", "-row-mt", "1", "-deadline", "good", "-cpu-used", "4",
                        base + ".webm"], check=True)
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src, "-vn",
                        "-c:a", "libmp3lame", "-q:a", "4", base + ".mp3"], check=False)
        n += 1
        print("added", name, f"{b-a:.1f}s")
print(n, "hooks added")
