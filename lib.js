import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';
export {THREE};

export const W = 1080, H = 1920;
export const CORAL = new THREE.Color(1, 0.36, 0.21), INK = '#d9d6cf', CORALHEX = '#ff5c36';
export const cl = x => Math.max(0, Math.min(1, x)), lerp = (a, b, t) => a + (b - a) * t;
export const eOut = t => 1 - Math.pow(1 - cl(t), 3), eIn = t => Math.pow(cl(t), 3);
export const eIO = t => { t = cl(t); return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2 };
export const eExpo = t => { t = cl(t); return t === 1 ? 1 : 1 - Math.pow(2, -10 * t) };
if (typeof window !== 'undefined') window.__HITS = window.__HITS || {};
// every animation hit (impulse) is recorded so the build can put a sound on it
export const impulse = (t, times, decay) => { const H = window.__HITS; for (const ti of times) { if (typeof ti === 'number' && isFinite(ti)) { const k = ti.toFixed(3); H[k] = Math.max(H[k] || 0, decay) } } let s = 0; for (const ti of times) if (t >= ti) s += Math.exp(-(t - ti) * decay); return s };
export function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296 } }

const FONTS = { IB: 'InterDisplay-Black.otf', IBD: 'InterDisplay-Bold.otf', ISB: 'InterDisplay-SemiBold.otf', IM: 'Inter-Medium.otf', MO: 'DejaVuSansMono.ttf' };

export async function setup({ sceneNo, total = 6, tcOffset = 0, title = 'OWN THE INBOX - MOTION REEL 2026', bloom: bc = [0.8, 0.5, 0.9], bg = 0x050506 }) {
  for (const [n, f] of Object.entries(FONTS)) { const ff = new FontFace(n, `url(/${f})`); await ff.load(); document.fonts.add(ff) }
  const st = document.createElement('style');
  st.textContent = `html,body{margin:0;background:#000;width:1080px;height:1920px;overflow:hidden}canvas{display:block}
  #hud{position:fixed;inset:0;pointer-events:none;font:22px MO;color:#8a8a94;letter-spacing:2px}
  .c{position:absolute;width:38px;height:38px;border-color:#8a8a94;border-style:solid}
  #flash{position:fixed;inset:0;background:#fff;opacity:0}`;
  document.head.appendChild(st);
  document.body.insertAdjacentHTML('beforeend', `<div id="hud">
  <div class="c" style="left:60px;top:140px;border-width:3px 0 0 3px"></div><div class="c" style="right:60px;top:140px;border-width:3px 3px 0 0"></div>
  <div class="c" style="left:60px;bottom:140px;border-width:0 0 3px 3px"></div><div class="c" style="right:60px;bottom:140px;border-width:0 3px 3px 0"></div>
  <div style="position:absolute;left:70px;top:190px"><span style="color:#ff5c36">&#9679;</span> ${title}</div>
  <div style="position:absolute;right:70px;top:190px">SCENE 0${sceneNo} / 0${total}</div>
  <div style="position:absolute;left:70px;bottom:190px" id="lab"></div><div style="position:absolute;right:70px;bottom:190px" id="tc"></div></div><div id="flash"></div>`);

  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1); renderer.setSize(W, H); document.body.prepend(renderer.domElement);
  const uiC = document.createElement('canvas'); uiC.width = W; uiC.height = H; uiC.style.cssText = 'position:fixed;left:0;top:0;width:1080px;height:1920px;pointer-events:none'; renderer.domElement.after(uiC); const ui = uiC.getContext('2d');
  const scene = new THREE.Scene(); scene.background = new THREE.Color(bg);
  const cam = new THREE.PerspectiveCamera(50, W / H, 0.05, 500); scene.add(cam);
  const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(W, H, { samples: 4, type: THREE.HalfFloatType })); composer.addPass(new RenderPass(scene, cam));
  const bloom = new UnrealBloomPass(new THREE.Vector2(W, H), ...bc); composer.addPass(bloom);
  const fx = new ShaderPass({
    uniforms: { tDiffuse: { value: null }, uCA: { value: 0.004 }, uT: { value: 0 }, uG: { value: 0.006 }, uGl: { value: 0 } },
    vertexShader: `varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader: `uniform sampler2D tDiffuse;uniform float uCA,uT,uG,uGl;varying vec2 vUv;
    float h(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233))+uT*91.7)*43758.5453);}
    void main(){vec2 uv=vUv;float band=floor(uv.y*38.)+floor(uT*24.)*7.;float hb=fract(sin(band*91.3)*4375.5);if(hb>1.-uGl)uv.x+=(fract(sin(band*13.7)*917.)-.5)*.25*uGl;vec2 d=(uv-.5);vec2 o=d*uCA+vec2(uGl*.02,0.);float r=texture2D(tDiffuse,uv+o).r,g=texture2D(tDiffuse,uv).g,b=texture2D(tDiffuse,uv-o).b;
    vec3 c=vec3(r,g,b);float v=1.-dot(d*vec2(1.,.6),d*vec2(1.,.6))*1.1;c*=v;c+=(h(vUv*vec2(1080.,1920.))-.5)*uG;gl_FragColor=vec4(c,1.);}`
  });
  composer.addPass(fx); composer.addPass(new OutputPass());

  // glyph helpers
  const FS = 640, CAP = FS * 0.727, PAD = 40;
  const meas = document.createElement('canvas').getContext('2d');
  function glyphCanvas(str, color, font) {
    const c = document.createElement('canvas'); const x = c.getContext('2d'); x.font = `${FS}px ${font}`;
    c.width = Math.ceil(x.measureText(str).width) + PAD * 2; c.height = Math.ceil(CAP + PAD * 2);
    x.font = `${FS}px ${font}`; x.fillStyle = color; x.fillText(str, PAD, PAD + CAP); return c
  }
  // word: letters as planes. returns {letters,group,width}. x is center.
  function word(str, { color = INK, h = 1, x = 0, y = 0, z = 0, maxW = 6.3, split = true, parent = scene, font = 'IB', sample = 0 } = {}) {
    const group = new THREE.Group(); group.position.set(x, y, z); parent.add(group);
    meas.font = `${FS}px ${font}`; let k = h / CAP; const tot = meas.measureText(str).width * k; if (tot > maxW) k *= maxW / tot;
    const tw = meas.measureText(str).width * k; const parts = split ? [...str] : [str]; let cx = -tw / 2; const letters = [];
    for (const p of parts) {
      const adv = meas.measureText(p).width * k;
      if (p === ' ') { cx += adv; continue }
      const cv = glyphCanvas(p, color, font); const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
      const ww = cv.width * k, hh = cv.height * k;
      const m = new THREE.Mesh(new THREE.PlaneGeometry(ww, hh), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, opacity: 0 }));
      const rest = new THREE.Vector3(cx + ww / 2 - PAD * k, 0, 0); m.position.copy(rest); m.userData.rest = rest.clone();
      if (sample) {
        const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data; const pts = [];
        for (let py = 0; py < cv.height; py += sample) for (let px = 0; px < cv.width; px += sample)
          if (d[(py * cv.width + px) * 4 + 3] > 140) pts.push([x + rest.x + (px - cv.width / 2) * k, y + (cv.height / 2 - py) * k, color]);
        m.userData.pts = pts
      }
      cx += adv; group.add(m); letters.push(m)
    }
    return { group, letters, width: tw, k }
  }
  // texture plane from a 2D canvas draw fn
  function canvasPlane(wpx, hpx, worldW, draw, parent = scene) {
    const c = document.createElement('canvas'); c.width = wpx; c.height = hpx; const x = c.getContext('2d'); draw(x, c);
    const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(worldW, worldW * hpx / wpx), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false }));
    m.userData.ctx = x; m.userData.canvas = c; m.userData.tex = tex; m.userData.redraw = (fn) => { x.clearRect(0, 0, wpx, hpx); fn(x, c); tex.needsUpdate = true };
    parent.add(m); return m
  }
  function pointsMat(map) {
    return new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      uniforms: { uA: { value: 1 }, map: { value: map || null }, uUse: { value: map ? 1 : 0 } },
      vertexShader: `attribute float size;attribute vec3 color;varying vec3 vC;void main(){vC=color;vec4 mv=modelViewMatrix*vec4(position,1.);gl_PointSize=size*(300./-mv.z);gl_Position=projectionMatrix*mv;}`,
      fragmentShader: `uniform float uA,uUse;uniform sampler2D map;varying vec3 vC;void main(){float a;if(uUse>.5){a=texture2D(map,gl_PointCoord).a;}else{float d=length(gl_PointCoord-.5);a=smoothstep(.5,0.,d);}gl_FragColor=vec4(vC*a*uA,a*uA);}`
    })
  }
  function makePoints(n, parent = scene, map) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    g.setAttribute('size', new THREE.BufferAttribute(new Float32Array(n), 1));
    const p = new THREE.Points(g, pointsMat(map)); p.frustumCulled = false; parent.add(p); return p
  }
  const hudEl = document.getElementById('hud'), labEl = document.getElementById('lab'), tcEl = document.getElementById('tc'), flashEl = document.getElementById('flash');
  function hud(t, label, alpha = 1) {
    hudEl.style.opacity = alpha; labEl.textContent = label;
    const g = t + tcOffset, fr = Math.floor(g * 30) % 30;
    tcEl.textContent = `TC 00:00:${String(Math.floor(g)).padStart(2, '0')}:${String(fr).padStart(2, '0')}`
  }
  function flash(a, color = '#fff') { flashEl.style.opacity = a; flashEl.style.background = color }
  function render(t) { fx.uniforms.uT.value = t; composer.render(1 / 30) }
  return { THREE, scene, cam, renderer, composer, bloom, fx, word, canvasPlane, makePoints, hud, flash, render, glyphCanvas, ui }
}

// rounded rect helper for 2D canvas
export function rr(x, X, Y, w, h, r) { x.beginPath(); x.moveTo(X + r, Y); x.arcTo(X + w, Y, X + w, Y + h, r); x.arcTo(X + w, Y + h, X, Y + h, r); x.arcTo(X, Y + h, X, Y, r); x.arcTo(X, Y, X + w, Y, r); x.closePath() }
