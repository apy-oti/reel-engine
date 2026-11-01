cd "$(dirname "$0")"
export FPS=30 CRF=21
(PORT=8801 python3 render.py s1.html v_s1.mp4 video 4.0 >log1 2>&1; PORT=8801 python3 render.py s3.html v_s3.mp4 video 6.0 >>log1 2>&1; PORT=8801 python3 render.py s5.html v_s5.mp4 video 4.0 >>log1 2>&1) &
(PORT=8802 python3 render.py s2.html v_s2.mp4 video 5.0 >log2 2>&1; PORT=8802 python3 render.py s4.html v_s4.mp4 video 7.0 >>log2 2>&1; PORT=8802 python3 render.py s6.html v_s6.mp4 video 4.0 >>log2 2>&1) &
wait
echo ALLDONE
