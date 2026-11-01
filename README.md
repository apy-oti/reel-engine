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
