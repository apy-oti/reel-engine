cd "$(dirname "$0")"
export FPS=30 CRF=16
(PORT=8811 python3 render.py w3.html why_s3.mp4 video 12.0 >wlog1 2>&1) &
(PORT=8812 python3 render.py w1.html why_s1.mp4 video 3.5 >wlog2 2>&1; PORT=8812 python3 render.py w2.html why_s2.mp4 video 8.5 >>wlog2 2>&1; PORT=8812 python3 render.py w4.html why_s4.mp4 video 6.0 >>wlog2 2>&1) &
wait
printf "file 'why_s%d.mp4'\n" 1 2 3 4 > why_list.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i why_list.txt -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p -movflags +faststart why_email.tmp.mp4 && mv why_email.tmp.mp4 why_email.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 why_email.mp4
