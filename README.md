# Own The Inbox reel engine

Renders vertical Reels (1080x1920) from HTML scenes with three.js, then stitches them with ffmpeg.

## Setup
npm install
pip install playwright --break-system-packages

## Render one scene
PORT=8801 FPS=30 CRF=21 python3 render.py s1.html v_s1.mp4 video 4.0
(args: scene file, output, mode, seconds)

## Render a full reel
bash runall.sh        # EN promo
bash runall_nl.sh     # NL promo
bash runall_why.sh    # why email
bash runall_owner.sh  # owner video
Then concat the scene videos with the matching *_list.txt:
ffmpeg -f concat -safe 0 -i list.txt -c copy out.mp4

## Files
- lib.js, ui.js: shared scene helpers
- s*, nl_s*, w*, e*.html: scenes per video
- render.py: frame capture to mp4
- sheet.py: contact sheet for quick review

## The machine (GitHub)
1. Add a folder `reels/<date>-<name>/` with `reel.json` (voice-over text, voice_id, scenes) and the scene HTML files.
   Scenes import `/lib.js` and use `/node_modules/...` in the importmap.
2. Push. The "Build reels" workflow makes the voice-over with ElevenLabs, renders, mixes, and uploads the mp4s.
3. Download from Actions -> latest run -> Artifacts -> reels.
Secret needed: ELEVENLABS_API_KEY. Local run: `python3 build_reel.py reels/<id>` (NO_VOICE=1 to skip voice).
