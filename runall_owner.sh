cd "$(dirname "$0")"
export FPS=30 CRF=16
(PORT=8821 python3 render.py e4.html own_e4.mp4 video 15.0 >olog1 2>&1; PORT=8821 python3 render.py e3.html own_e3.mp4 video 10.0 >>olog1 2>&1; PORT=8821 python3 render.py e1.html own_e1.mp4 video 5.0 >>olog1 2>&1) &
(PORT=8822 python3 render.py e2.html own_e2.mp4 video 10.0 >olog2 2>&1; PORT=8822 python3 render.py e5.html own_e5.mp4 video 12.0 >>olog2 2>&1; PORT=8822 python3 render.py e6.html own_e6.mp4 video 8.0 >>olog2 2>&1) &
wait
printf "file 'own_e%d.mp4'\n" 1 2 3 4 5 6 > own_list.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i own_list.txt -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p -movflags +faststart owner_video.tmp.mp4 && mv owner_video.tmp.mp4 owner_video.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 owner_video.mp4
