"""Self-contained HTML5 Canvas animation of the UR20 palletizing cell.

Rendered with `streamlit.components.v1.html(build_animation_html(...), height=...)`.
No external CDN: plain HTML/CSS/JS. All displayed values come from Python.
"""

from __future__ import annotations

import json

ANIMATION_HEIGHT = 500


def build_animation_html(
    *,
    line_rate_bpm: float,
    bucket_weight_kg: float,
    gripper_weight_kg: float,
    has_handle: bool,
    side_selection: str,
    buckets_per_pallet: int,
    layers: int,
    benchmark_bpm: float,
    payload_total: float,
    valid: bool = True,
) -> str:
    params = {
        "rate": max(0.0, float(line_rate_bpm or 0)),
        "weight": float(bucket_weight_kg or 0),
        "gripper": float(gripper_weight_kg or 0),
        "handle": bool(has_handle),
        "side": side_selection if side_selection in ("Stânga", "Dreapta", "Dual") else "Dual",
        "perPallet": max(1, int(buckets_per_pallet or 1)),
        "layers": max(1, int(layers or 1)),
        "benchmark": float(benchmark_bpm or 7.4),
        "payload": float(payload_total or 0),
        "valid": bool(valid),
    }
    return _TEMPLATE.replace("__PARAMS__", json.dumps(params, ensure_ascii=False))


_TEMPLATE = r"""<!doctype html>
<html lang="ro"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { --bg:#0f172a; --panel:#111c33; --line:#26324d; --txt:#e2e8f0; --mut:#94a3b8;
          --ok:#22c55e; --warn:#f59e0b; --err:#ef4444; --acc:#38bdf8; }
  * { box-sizing:border-box; }
  html,body { margin:0; padding:0; background:transparent; font-family: system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; color:var(--txt); }
  .wrap { background:var(--bg); border:1px solid var(--line); border-radius:12px; padding:8px; max-width:760px; margin:0 auto; }
  .chips { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:6px; }
  .chip { background:var(--panel); border:1px solid var(--line); border-radius:999px; padding:3px 9px; font-size:12px; white-space:nowrap; }
  .chip b { color:#fff; }
  .banner { display:none; border-radius:8px; padding:5px 10px; font-size:13px; font-weight:700; margin-bottom:6px; text-align:center; }
  .banner.err { display:block; background:rgba(239,68,68,.18); border:1px solid var(--err); color:#fecaca; animation:blink 0.9s steps(2) infinite; }
  .banner.warn { display:block; background:rgba(245,158,11,.16); border:1px solid var(--warn); color:#fde68a; }
  .banner.info { display:block; background:rgba(148,163,184,.14); border:1px solid var(--mut); color:#e2e8f0; }
  @keyframes blink { 50% { opacity:.45; } }
  canvas { width:100%; height:auto; display:block; border-radius:8px; background:#0b1222; touch-action:manipulation; }
  .ctrls { display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin-top:6px; }
  button { font:inherit; font-size:13px; border-radius:8px; border:1px solid var(--line); background:var(--panel); color:var(--txt);
           padding:6px 10px; cursor:pointer; min-height:34px; }
  button:hover { border-color:var(--acc); }
  button.on { background:#0c4a6e; border-color:var(--acc); color:#fff; }
  .seg { display:inline-flex; gap:0; }
  .seg button { border-radius:0; }
  .seg button:first-child { border-radius:8px 0 0 8px; }
  .seg button:last-child { border-radius:0 8px 8px 0; }
  .lbl { font-size:12px; color:var(--mut); }
  .counter { margin-left:auto; font-size:12px; color:var(--mut); }
  .counter b { color:#fff; }
  @media (max-width:480px) { .chip { font-size:11px; padding:2px 7px; } button { font-size:12px; padding:5px 8px; } .counter { margin-left:0; width:100%; } }
</style></head>
<body>
<div class="wrap">
  <div class="chips" id="chips"></div>
  <div class="banner" id="banner"></div>
  <canvas id="cv" width="800" height="400" aria-label="Animație celulă de paletizare UR20"></canvas>
  <div class="ctrls">
    <button id="play" title="Pornește / oprește animația">⏸ Pauză</button>
    <span class="lbl">Previzualizare parte activă:</span>
    <span class="seg" id="sideSeg">
      <button data-side="Stânga">Stânga</button><button data-side="Dreapta">Dreapta</button><button data-side="Dual">Dual</button>
    </span>
    <span class="counter" id="counter"></span>
  </div>
</div>
<script>
(function(){
const P = __PARAMS__;
const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
const W = 800, H = 400;
const dpr = Math.min(window.devicePixelRatio || 1, 2);
cv.width = W*dpr; cv.height = H*dpr; ctx.setTransform(dpr,0,0,dpr,0,0);

const fmt = (v, d=1) => Number(v).toLocaleString('ro-RO', {minimumFractionDigits:d, maximumFractionDigits:d});
const overload = P.payload > 20.0;
const bottleneck = P.rate > 8.6;
const aboveBench = P.rate > P.benchmark;
const SPEED = 3; // visual time compression
const clamp = (v,a,b)=>Math.max(a,Math.min(b,v));
const arrivalInterval = P.rate > 0 ? clamp(60/P.rate/SPEED, 0.7, 9) : 1e9;
const robotCycle = clamp(60/P.benchmark/SPEED, 1.6, 6);
let side = P.side;
let playing = true;

// ---------- chips / banner ----------
document.getElementById('chips').innerHTML = [
  `Debit: <b>${fmt(P.rate,2)}</b> găleți/min`,
  `Găleată: <b>${fmt(P.weight)}</b> kg`,
  `Sarcină: <b style="color:${overload?'#fca5a5':'#fff'}">${fmt(P.payload)}</b> / 20 kg`,
  `Reper PURATOS: <b>${fmt(P.benchmark)}</b> găleți/min`,
  `Vision SICK: <b>${P.handle?'ACTIV':'STANDBY'}</b>`,
  `Simulare ×${SPEED}`
].map(t=>`<span class="chip">${t}</span>`).join('');
const banner = document.getElementById('banner');
if (!P.valid) { banner.className='banner info'; banner.textContent='DATE INVALIDE — corectați formularul pentru a porni simularea'; }
else if (overload) { banner.className='banner err'; banner.textContent=`SUPRASARCINĂ UR20 > 20 kg — sarcină totală ${fmt(P.payload)} kg · braț oprit în poziția de siguranță`; }
else if (bottleneck) { banner.className='banner warn'; banner.textContent=`ATENȚIE: DEBIT > 8,6 găleți/min (${fmt(P.rate,2)}) — se formează coadă pe transportor`; }
else if (aboveBench) { banner.className='banner warn'; banner.textContent=`Debit peste reperul testat de ${fmt(P.benchmark)} găleți/min pentru această greutate — coadă lentă pe transportor`; }

// ---------- geometry ----------
const BASE = {x:400, y:118};
const L1 = 182, L2 = 180;
const HOME = {x:400, y:236};
const PICK = {x:400, y:300};
const CONV = {x:368, w:64, top:280, bottom:H};
const CAM_Y = 374;
const PAL = {
  'Stânga': {x:88,  y:150, s:160},
  'Dreapta':{x:552, y:150, s:160},
};
const bucketR = clamp(9 + P.weight*0.55, 10, 22);
const perLayer = Math.max(1, Math.ceil(P.perPallet / P.layers));
const cols = Math.ceil(Math.sqrt(perLayer));
const rows = Math.ceil(perLayer / cols);

function newPallet(){ return {placed:0, state:'ready', timer:0}; }
const pallets = {'Stânga': newPallet(), 'Dreapta': newPallet()};
let activeBay = side === 'Dreapta' ? 'Dreapta' : 'Stânga';
let totalPlaced = 0, separators = 0, palletsDone = 0, upstreamQueue = 0;

function slotPos(bay, idx){
  const p = PAL[bay];
  const inLayer = idx % perLayer;
  const c = inLayer % cols, r = Math.floor(inLayer / cols);
  const cell = p.s / Math.max(cols, rows);
  const offX = (p.s - cell*cols)/2, offY = (p.s - cell*rows)/2;
  return {x: p.x + offX + cell*(c+0.5), y: p.y + offY + cell*(r+0.5), r: Math.min(cell*0.43, bucketR)};
}

// ---------- conveyor buckets ----------
let buckets = []; // {y, ang, scanned}
let spawnT = 0, beltOffset = 0, camFlash = 0, lastAngle = 0;
const gap = bucketR*2 + 8;

// ---------- robot state ----------
const R = {state:'home', t:0, from:{...HOME}, to:{...HOME}, pos:{...HOME}, carrying:null, target:null, bay:null, wait:0};
function ease(t){ return t<0.5 ? 2*t*t : 1-Math.pow(-2*t+2,2)/2; }
function moveTo(state, to, dur){ R.state=state; R.t=0; R.from={...R.pos}; R.to=to; R.dur=dur; }

function bayAvailable(b){ return pallets[b].state === 'ready'; }
function chooseBay(){
  if (side === 'Stânga') return bayAvailable('Stânga') ? 'Stânga' : null;
  if (side === 'Dreapta') return bayAvailable('Dreapta') ? 'Dreapta' : null;
  if (bayAvailable(activeBay)) return activeBay;
  const other = activeBay === 'Stânga' ? 'Dreapta' : 'Stânga';
  if (bayAvailable(other)) { activeBay = other; return other; }
  return null;
}

function step(dt){
  if (!P.valid) return;
  const halted = overload;
  // belt + spawn
  if (!halted) {
    beltOffset = (beltOffset + dt*45) % 24;
    spawnT += dt;
    while (spawnT >= arrivalInterval) {
      spawnT -= arrivalInterval;
      upstreamQueue++;
    }
    const last = buckets[buckets.length-1];
    if (upstreamQueue > 0 && (!last || last.y < H + bucketR - gap)) {
      upstreamQueue--;
      buckets.push({y: H + bucketR + 2, ang: (Math.random()*300+30)|0, scanned:false});
    }
  } else if (buckets.length < 4) {
    // show a stopped line: a few buckets parked on the conveyor
    if (buckets.length === 0) for (let i=0;i<4;i++) buckets.push({y: PICK.y + i*gap, ang:(Math.random()*300+30)|0, scanned:i===0});
  }
  // move conveyor buckets (stop at pick point / queue spacing)
  const speed = 70;
  for (let i=0;i<buckets.length;i++){
    const b = buckets[i];
    const limit = i===0 ? PICK.y : buckets[i-1].y + gap;
    if (!halted) b.y = Math.max(limit, b.y - speed*dt);
    if (!b.scanned && b.y <= CAM_Y) { b.scanned = true; camFlash = 0.5; lastAngle = b.ang; }
  }
  camFlash = Math.max(0, camFlash - dt);

  // pallet exchange / separator timers
  for (const bay of ['Stânga','Dreapta']) {
    const p = pallets[bay];
    if (p.state !== 'ready') {
      p.timer -= dt;
      if (p.timer <= 0) {
        if (p.state === 'exchange') { pallets[bay] = newPallet(); }
        else p.state = 'ready';
      }
    }
  }

  // robot
  if (halted) { R.pos = {...HOME}; R.state='home'; return; }
  R.t += dt;
  const k = R.dur ? clamp(R.t / R.dur, 0, 1) : 1;
  if (R.state !== 'home' && R.state !== 'wait') {
    const e = ease(k);
    R.pos = {x: R.from.x + (R.to.x-R.from.x)*e, y: R.from.y + (R.to.y-R.from.y)*e};
  }
  const c = robotCycle;
  switch (R.state) {
    case 'home': {
      const head = buckets[0];
      const bay = chooseBay();
      if (head && head.y <= PICK.y + 1 && head.scanned && bay) {
        R.bay = bay; R.target = slotPos(bay, pallets[bay].placed);
        moveTo('toPick', {...PICK}, c*0.22);
      }
      break; }
    case 'toPick': if (k>=1) { R.state='grip'; R.t=0; R.dur=c*0.08; } break;
    case 'grip': if (k>=1) { R.carrying = buckets.shift(); moveTo('toPlace', {x:R.target.x, y:R.target.y}, c*0.36); } break;
    case 'toPlace': if (k>=1) { R.state='release'; R.t=0; R.dur=c*0.08; } break;
    case 'release': if (k>=1) {
      const p = pallets[R.bay];
      p.placed++; totalPlaced++; R.carrying = null;
      if (p.placed >= P.perPallet) { p.state='exchange'; p.timer = 3.2; palletsDone++; if (side==='Dual') activeBay = R.bay==='Stânga'?'Dreapta':'Stânga'; }
      else if (p.placed % perLayer === 0) { p.state='separator'; p.timer = 1.4; separators++; }
      moveTo('toHome', {...HOME}, c*0.26);
    } break;
    case 'toHome': if (k>=1) { R.state='home'; } break;
  }
}

// ---------- drawing ----------
function rr(x,y,w,h,r){ ctx.beginPath(); ctx.moveTo(x+r,y); ctx.arcTo(x+w,y,x+w,y+h,r); ctx.arcTo(x+w,y+h,x,y+h,r); ctx.arcTo(x,y+h,x,y,r); ctx.arcTo(x,y,x+w,y,r); ctx.closePath(); }
function label(t,x,y,size=15,color='#cbd5e1',align='center',weight='600'){ ctx.font=`${weight} ${size}px system-ui,sans-serif`; ctx.fillStyle=color; ctx.textAlign=align; ctx.textBaseline='middle'; ctx.fillText(t,x,y); }

function drawBucket(x,y,r,ang,lifted){
  const s = lifted ? 1.12 : 1;
  ctx.save(); ctx.translate(x,y); ctx.scale(s,s);
  if (lifted) { ctx.fillStyle='rgba(0,0,0,.35)'; ctx.beginPath(); ctx.arc(4,5,r,0,Math.PI*2); ctx.fill(); }
  ctx.fillStyle = '#e5e7eb'; ctx.beginPath(); ctx.arc(0,0,r,0,Math.PI*2); ctx.fill();
  ctx.strokeStyle='#64748b'; ctx.lineWidth=2; ctx.stroke();
  ctx.fillStyle='#cbd5e1'; ctx.beginPath(); ctx.arc(0,0,r*0.72,0,Math.PI*2); ctx.fill();
  if (P.handle) {
    ctx.rotate(ang*Math.PI/180);
    ctx.strokeStyle='#f97316'; ctx.lineWidth=Math.max(2, r*0.18); ctx.lineCap='round';
    ctx.beginPath(); ctx.moveTo(-r*0.95,0); ctx.quadraticCurveTo(0,-r*0.55,r*0.95,0); ctx.stroke();
    ctx.rotate(-ang*Math.PI/180);
  }
  if (r >= 13) label(`${fmt(P.weight, P.weight%1?1:0)}kg`, 0, 0.5, Math.max(8, r*0.55), '#0f172a', 'center', '700');
  ctx.restore();
}

function drawScannerField(bay, active){
  const p = PAL[bay];
  ctx.save();
  ctx.fillStyle = active ? 'rgba(239,68,68,0.13)' : 'rgba(34,197,94,0.13)';
  ctx.strokeStyle = active ? 'rgba(239,68,68,0.75)' : 'rgba(34,197,94,0.75)';
  ctx.setLineDash([6,5]); ctx.lineWidth=1.5;
  rr(p.x-14, p.y-12, p.s+28, p.s+56, 12); ctx.fill(); ctx.stroke();
  ctx.restore();
  label(active ? 'ZONĂ ROBOT ACTIV' : 'ZONĂ OPERATOR (SIGUR)', p.x + p.s/2, p.y + p.s + 32, 12.5, active ? '#fca5a5' : '#86efac', 'center', '700');
}

function drawScanner(x,y,dir,color){
  ctx.save(); ctx.translate(x,y);
  const g = ctx.createRadialGradient(0,0,4,0,0,95);
  g.addColorStop(0, color.replace('A','0.35')); g.addColorStop(1, color.replace('A','0'));
  ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(0,0); ctx.arc(0,0,95,dir-0.75,dir+0.75); ctx.closePath(); ctx.fill();
  ctx.fillStyle='#facc15'; ctx.strokeStyle='#713f12'; ctx.lineWidth=2; rr(-9,-9,18,18,4); ctx.fill(); ctx.stroke();
  ctx.fillStyle='#111827'; ctx.beginPath(); ctx.arc(0,0,4,0,Math.PI*2); ctx.fill();
  ctx.restore();
}

function drawPallet(bay){
  const p = PAL[bay], st = pallets[bay];
  // euro pallet boards
  ctx.fillStyle = '#a16207'; rr(p.x, p.y, p.s, p.s, 4); ctx.fill();
  ctx.fillStyle = '#ca8a04';
  for (let i=0;i<5;i++) ctx.fillRect(p.x+4, p.y+4+i*(p.s-8)/5, p.s-8, (p.s-8)/5-6);
  const layer = Math.floor(st.placed / perLayer);
  if (layer > 0) { // previous layers + separator sheet
    ctx.fillStyle='rgba(226,232,240,0.30)'; rr(p.x+3,p.y+3,p.s-6,p.s-6,3); ctx.fill();
    for (let i=0;i<perLayer && i<P.perPallet;i++){ const s=slotPos(bay,i); ctx.fillStyle='rgba(148,163,184,0.35)'; ctx.beginPath(); ctx.arc(s.x,s.y,s.r,0,Math.PI*2); ctx.fill(); }
  }
  const startIdx = layer*perLayer;
  const inThis = st.placed - startIdx;
  if (!(st.state==='separator' && inThis===0)) {
    for (let i=0;i<inThis;i++){ const s=slotPos(bay,startIdx+i); drawBucket(s.x,s.y,s.r,90,false); }
  }
  label(`PALET ${bay.toUpperCase()}`, p.x + p.s/2, p.y - 24, 14, '#e2e8f0', 'center', '700');
  const layerShown = Math.min(P.layers, layer + (st.placed % perLayer ? 1 : 0)) || 1;
  label(`${st.placed}/${P.perPallet} · strat ${Math.min(layerShown,P.layers)}/${P.layers}`, p.x + p.s/2, p.y + p.s + 13, 12, '#cbd5e1');
  if (st.state === 'separator') {
    ctx.fillStyle='rgba(15,23,42,.72)'; rr(p.x+8,p.y+p.s/2-18,p.s-16,36,8); ctx.fill();
    label('SEPARATOR MANUAL', p.x+p.s/2, p.y+p.s/2, 13, '#fde68a', 'center', '700');
  } else if (st.state === 'exchange') {
    ctx.fillStyle='rgba(15,23,42,.78)'; rr(p.x+6,p.y+p.s/2-26,p.s-12,52,8); ctx.fill();
    label('PALET PLIN', p.x+p.s/2, p.y+p.s/2-9, 13, '#86efac', 'center', '800');
    label('schimb manual operator', p.x+p.s/2, p.y+p.s/2+10, 11.5, '#e2e8f0');
  }
}

function drawConveyor(){
  ctx.fillStyle='#1f2937'; ctx.fillRect(CONV.x-6, CONV.top, CONV.w+12, H-CONV.top);
  ctx.fillStyle='#334155'; ctx.fillRect(CONV.x, CONV.top, CONV.w, H-CONV.top);
  ctx.strokeStyle='#475569'; ctx.lineWidth=2;
  for (let y = CONV.top + ((24 - beltOffset) % 24); y < H; y += 24) { ctx.beginPath(); ctx.moveTo(CONV.x+3,y); ctx.lineTo(CONV.x+CONV.w-3,y); ctx.stroke(); }
  label('TRANSPORTOR', CONV.x - 14, 318, 11.5, '#94a3b8', 'right');
  label('ALIMENTARE ↑', CONV.x - 14, 333, 11.5, '#94a3b8', 'right');
}

function drawCamera(){
  const active = P.handle;
  const flash = active && camFlash > 0;
  ctx.fillStyle='#0f172a'; ctx.strokeStyle= active ? '#38bdf8' : '#64748b'; ctx.lineWidth=2;
  rr(CONV.x-20, CAM_Y-9, CONV.w+40, 18, 5); ctx.fill(); ctx.stroke();
  if (flash) {
    ctx.fillStyle = `rgba(34,197,94,${0.25 + camFlash})`;
    ctx.fillRect(CONV.x, CAM_Y-26, CONV.w, 52);
    ctx.strokeStyle='#22c55e'; ctx.lineWidth=3; ctx.beginPath(); ctx.moveTo(CONV.x, CAM_Y); ctx.lineTo(CONV.x+CONV.w, CAM_Y); ctx.stroke();
  }
  ctx.fillStyle = active ? (flash ? '#22c55e' : '#38bdf8') : '#64748b';
  ctx.beginPath(); ctx.arc(CONV.x+CONV.w+28, CAM_Y, 6, 0, Math.PI*2); ctx.fill();
  label('Cameră SICK 2D', CONV.x+CONV.w+40, CAM_Y-9, 12.5, active ? '#7dd3fc' : '#94a3b8', 'left', '700');
  const txt = !active ? 'STANDBY / BYPASS (fără mâner)' : (flash ? `mâner detectat · ${lastAngle}°` : 'activă — detecție orientare mâner');
  label(txt, CONV.x+CONV.w+40, CAM_Y+8, 11.5, flash ? '#86efac' : '#94a3b8', 'left', '500');
}

function drawArm(){
  const t = R.pos;
  let dx = t.x - BASE.x, dy = t.y - BASE.y;
  let d = Math.hypot(dx, dy);
  d = clamp(d, Math.abs(L1-L2)+2, L1+L2-2);
  const a = Math.atan2(dy, dx);
  const cosB = clamp((L1*L1 + d*d - L2*L2) / (2*L1*d), -1, 1);
  // two IK solutions: keep the elbow on the upper (back) side of the cell, away from the pallets
  const s1 = a + Math.acos(cosB), s2 = a - Math.acos(cosB);
  const y1 = Math.sin(s1), y2 = Math.sin(s2);
  const shoulder = (Math.abs(y1 - y2) < 1e-3) ? (Math.cos(s1) < Math.cos(s2) ? s1 : s2) : (y1 < y2 ? s1 : s2);
  const ex = BASE.x + L1*Math.cos(shoulder), ey = BASE.y + L1*Math.sin(shoulder);
  const wx = BASE.x + Math.cos(a)*d, wy = BASE.y + Math.sin(a)*d;
  // base
  ctx.fillStyle='#1e293b'; ctx.beginPath(); ctx.arc(BASE.x, BASE.y, 30, 0, Math.PI*2); ctx.fill();
  ctx.strokeStyle='#38bdf8'; ctx.lineWidth=3; ctx.stroke();
  // links (UR style: light grey with blue joint caps)
  ctx.lineCap='round';
  ctx.strokeStyle='#0f172a'; ctx.lineWidth=26; ctx.beginPath(); ctx.moveTo(BASE.x,BASE.y); ctx.lineTo(ex,ey); ctx.lineTo(wx,wy); ctx.stroke();
  ctx.strokeStyle= overload ? '#fca5a5' : '#e2e8f0'; ctx.lineWidth=20; ctx.beginPath(); ctx.moveTo(BASE.x,BASE.y); ctx.lineTo(ex,ey); ctx.stroke();
  ctx.lineWidth=16; ctx.beginPath(); ctx.moveTo(ex,ey); ctx.lineTo(wx,wy); ctx.stroke();
  for (const [x,y,r] of [[BASE.x,BASE.y,16],[ex,ey,13],[wx,wy,11]]) {
    ctx.fillStyle='#0ea5e9'; ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.fill();
    ctx.fillStyle='#0c4a6e'; ctx.beginPath(); ctx.arc(x,y,r*0.45,0,Math.PI*2); ctx.fill();
  }
  label('UR20', BASE.x + 46, BASE.y + 4, 13, '#7dd3fc', 'center', '800');
  // gripper + carried bucket
  if (R.carrying) drawBucket(wx, wy, bucketR, R.carrying.ang, true);
  const closed = R.carrying || R.state==='grip';
  ctx.save(); ctx.translate(wx, wy); ctx.rotate(a);
  ctx.fillStyle='#475569'; rr(-8,-14,16,28,4); ctx.fill();
  ctx.fillStyle='#94a3b8'; const off = closed ? 8 : 14;
  ctx.fillRect(-4, -off-4, 14, 5); ctx.fillRect(-4, off-1, 14, 5);
  ctx.restore();
}

function draw(){
  ctx.clearRect(0,0,W,H);
  ctx.fillStyle='#0b1222'; ctx.fillRect(0,0,W,H);
  // floor grid
  ctx.strokeStyle='rgba(148,163,184,0.06)'; ctx.lineWidth=1;
  for (let x=0;x<W;x+=40){ ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,H); ctx.stroke(); }
  for (let y=0;y<H;y+=40){ ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke(); }

  // which bay the robot uses now
  const robotBay = side === 'Dual' ? activeBay : side;
  for (const bay of ['Stânga','Dreapta']) {
    const active = !overload && P.valid && bay === robotBay && pallets[bay].state === 'ready';
    drawScannerField(bay, active);
  }
  // 3 safety scanners: left bay, right bay, center front
  const colL = robotBay==='Stânga' && !overload ? 'rgba(239,68,68,A)' : 'rgba(34,197,94,A)';
  const colR = robotBay==='Dreapta' && !overload ? 'rgba(239,68,68,A)' : 'rgba(34,197,94,A)';
  drawScanner(42, 120, 0.85, colL);
  drawScanner(758, 120, Math.PI-0.85, colR);
  drawScanner(400, 20, Math.PI/2, 'rgba(56,189,248,A)');
  label('Scaner 1', 42, 98, 11, '#fde047'); label('Scaner 2', 758, 98, 11, '#fde047'); label('Scaner 3', 418, 20, 11, '#fde047', 'left');

  drawPallet('Stânga'); drawPallet('Dreapta');
  drawConveyor();
  for (let i=buckets.length-1;i>=0;i--) drawBucket(CONV.x+CONV.w/2, buckets[i].y, bucketR, buckets[i].ang, false);
  drawCamera();
  drawArm();

  if (upstreamQueue > 0 && !overload) {
    ctx.fillStyle='rgba(245,158,11,.92)'; rr(CONV.x+CONV.w+12, 284, 150, 32, 8); ctx.fill();
    label(`Coadă amonte: ${upstreamQueue} găleți`, CONV.x+CONV.w+87, 300, 12.5, '#111827', 'center', '800');
  }
  if (overload) {
    ctx.fillStyle='rgba(127,29,29,.85)'; rr(250, 34, 300, 56, 10); ctx.fill();
    ctx.strokeStyle='#ef4444'; ctx.lineWidth=2; ctx.stroke();
    label('SUPRASARCINĂ UR20 > 20 kg', 400, 52, 16, '#fecaca', 'center', '800');
    label(`Sarcină totală ${fmt(P.payload)} kg — braț oprit (home)`, 400, 74, 12.5, '#fee2e2');
  }
  if (!P.valid) {
    ctx.fillStyle='rgba(15,23,42,.8)'; ctx.fillRect(0,0,W,H);
    label('Date invalide — simularea este oprită', 400, 200, 18, '#e2e8f0', 'center', '700');
  }
  if (!playing) {
    ctx.fillStyle='rgba(15,23,42,.55)'; rr(340,182,120,36,8); ctx.fill();
    label('⏸ PAUZĂ', 400, 200, 15, '#fff', 'center', '800');
  }
  document.getElementById('counter').innerHTML =
    `Plasate: <b>${totalPlaced}</b> · Paleți plini: <b>${palletsDone}</b> · Separatoare: <b>${separators}</b>`;
}

// ---------- controls ----------
const playBtn = document.getElementById('play');
playBtn.onclick = () => { playing = !playing; playBtn.textContent = playing ? '⏸ Pauză' : '▶ Pornește'; last = performance.now(); draw(); };
const segBtns = [...document.querySelectorAll('#sideSeg button')];
function refreshSeg(){ segBtns.forEach(b => b.classList.toggle('on', b.dataset.side === side)); }
segBtns.forEach(b => b.onclick = () => {
  side = b.dataset.side;
  if (side !== 'Dual') activeBay = side;
  refreshSeg(); draw();
});
refreshSeg();

let last = performance.now();
function loop(now){
  const dt = Math.min(0.05, (now - last)/1000); last = now;
  if (playing) step(dt);
  draw();
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
})();
</script>
</body></html>
"""
