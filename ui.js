import { cl, lerp, eOut, eIn, eIO, eExpo, CORALHEX, rr } from './lib.js';
export const WHITE = '#f3f1eb', GREY = '#9a98a2', DIM = '#5d5c66', CORAL = CORALHEX;
export function font(x, size, f = 'IBD', ls = 0) { x.font = `${size}px ${f}`; x.letterSpacing = ls + 'px' }
export function fit(x, lines, f, maxW, maxS, ls = -1.5) {
  let s = maxS; for (; s > 20; s -= 2) { font(x, s, f, ls); if (lines.every(l => x.measureText(l).width <= maxW)) break } return s
}
// per-letter rise-in, lift-out
export function letters(x, str, X, Y, o) {
  const { size = 100, f = 'IBD', color = WHITE, align = 'left', t, t0, t1 = 1e9, stagger = 0.018, dur = 0.6, rise = 34, ls = -1.5, alpha = 1, glow = 0 } = o;
  font(x, size, f, ls); const w = x.measureText(str).width; const sx = align === 'center' ? X - w / 2 : align === 'right' ? X - w : X;
  const fp = eIn((t - t1) / 0.4); if (fp >= 1 || t < t0) return w; x.textAlign = 'left'; x.fillStyle = color;
  if (glow) { x.shadowColor = color; x.shadowBlur = glow }
  for (let i = 0; i < str.length; i++) {
    const ch = str[i]; if (ch === ' ') continue; const p = eExpo((t - t0 - i * stagger) / dur); if (p <= 0) continue;
    const px = sx + x.measureText(str.slice(0, i + 1)).width - x.measureText(ch).width;
    x.globalAlpha = alpha * cl(p * 1.6) * (1 - fp); x.fillText(ch, px, Y + (1 - p) * rise - fp * 26)
  }
  x.globalAlpha = 1; x.shadowBlur = 0; return w
}
export function mono(x, str, X, Y, { size = 26, color = GREY, align = 'left', alpha = 1, ls = 4 } = {}) {
  font(x, size, 'MO', ls); x.textAlign = align; x.fillStyle = color; x.globalAlpha = alpha; x.fillText(str, X, Y); x.globalAlpha = 1; x.textAlign = 'left'
}
export function panel(x, X, Y, w, h, { r = 32, fill = 'rgba(255,255,255,0.045)', stroke = 'rgba(255,255,255,0.10)', alpha = 1, lw = 2 } = {}) {
  x.globalAlpha = alpha; x.fillStyle = fill; rr(x, X, Y, w, h, r); x.fill(); if (stroke) { x.strokeStyle = stroke; x.lineWidth = lw; rr(x, X, Y, w, h, r); x.stroke() } x.globalAlpha = 1
}
export function envelope(x, cx, cy, s, color = '#fff', lw = 7) {
  x.strokeStyle = color; x.lineWidth = lw; x.lineJoin = 'round'; x.lineCap = 'round';
  rr(x, cx - s, cy - s * 0.72, s * 2, s * 1.44, s * 0.18); x.stroke();
  x.beginPath(); x.moveTo(cx - s * 0.86, cy - s * 0.56); x.lineTo(cx, cy + s * 0.08); x.lineTo(cx + s * 0.86, cy - s * 0.56); x.stroke()
}
export function chrome(x, g, total = 60) {
  const X0 = 70, X1 = 1010, Y = 1752; x.fillStyle = 'rgba(255,255,255,0.10)'; x.fillRect(X0, Y, X1 - X0, 3);
  x.fillStyle = CORALHEX; x.fillRect(X0, Y, (X1 - X0) * cl(g / total), 3)
}
export { cl, lerp, eOut, eIn, eIO, eExpo, rr };
