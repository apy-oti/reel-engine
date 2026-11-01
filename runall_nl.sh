cd "$(dirname "$0")"
export FPS=30 CRF=21
(PORT=8801 python3 render.py nl_s1.html nl_v_s1.mp4 video 4.0 >nllog1 2>&1; PORT=8801 python3 render.py nl_s3.html nl_v_s3.mp4 video 6.0 >>nllog1 2>&1; PORT=8801 python3 render.py nl_s5.html nl_v_s5.mp4 video 4.0 >>nllog1 2>&1) &
(PORT=8802 python3 render.py nl_s2.html nl_v_s2.mp4 video 5.0 >nllog2 2>&1; PORT=8802 python3 render.py nl_s4.html nl_v_s4.mp4 video 7.0 >>nllog2 2>&1; PORT=8802 python3 render.py nl_s6.html nl_v_s6.mp4 video 4.0 >>nllog2 2>&1) &
wait
echo ALLDONE
