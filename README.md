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

## Explainer reels (faceless, captions)
`"type": "explainer"` in reel.json. One voice track with word timings (ElevenLabs with-timestamps), bold synced captions,
browser-window visuals per beat, glowing step labels, cursor clicks, CTA end card. Visual kinds:
big (kinetic text, lines split by |), inbox, flow, email, stat, image (file in the reel folder), html (raw).
Options per visual: url (address bar), h (window height), top, zoom [[progress, scale, x, y], ...], cursor {x, y, click}.
See reels/2026-11-explainer-3-flows/reel.json.

## Hooks
Every explainer starts with a random hook clip from `hooks/` (never repeats until all were used; tracked in hooks/used.json).
Add hooks: `python3 tools/add_hooks.py clip1.mp4 compilation.mp4` (long videos are split at scene changes), then commit.
Per reel: "hook_text" (big line on the hook), "hook": false (no hook) or "hook": "tree-smash" (force one).

## Cinematic reels (gold kinetic type)
`"type": "cinematic"`. Short excited lines (one TTS call per beat, with pauses), key words slam in when spoken.
Beat styles: title (small serif + big gold), flash (paper screen, black type), echo (stacked outlines), streak (light sweep + sparks),
chrome (3D metal), diagram (items lit by a gold line), prompt (typing box + button), number.
Fields: say, style, small, big (lines split by |), items [{icon,label}], prompt, highlight, tool, button, hud, gap.
Default voice Liam (energetic male). See reels/2026-11-cinematic-3-flows/reel.json.
