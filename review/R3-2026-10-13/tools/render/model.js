// SmartVio R3 module + proposal variant + illustrative violin.
// Units: mm.  World: x = X-74 (cover length, drawing left->right),
// z = Y-24.5 (drawing Y downward), y = Z (up, 0 = violin mounting face).
import * as THREE from 'three';
import { Brush, Evaluator, SUBTRACTION, ADDITION } from 'three-bvh-csg';

const ev = new Evaluator();
ev.attributes = ['position', 'normal'];
ev.useGroups = false;

export const W = (X, Y, Z = 0) => new THREE.Vector3(X - 74, Z, Y - 24.5);

// ---------- materials ----------
export function makeMaterials(variant) {
  const M = {};
  M.cover = new THREE.MeshPhysicalMaterial({ color: variant === 'proposal' ? 0x121416 : 0x1a1d20, roughness: variant === 'proposal' ? 0.72 : 0.62, metalness: 0, clearcoat: variant === 'proposal' ? 0.12 : 0.0, clearcoatRoughness: 0.7, envMapIntensity: 0.7 });
  M.cup = M.cover.clone(); M.cup.color = new THREE.Color(0x24282c);
  M.steel = new THREE.MeshStandardMaterial({ color: 0xc9ccd0, metalness: 1, roughness: 0.32 });
  M.steelDark = new THREE.MeshStandardMaterial({ color: 0x2b2e31, metalness: 0.8, roughness: 0.45 });
  M.nickel = new THREE.MeshStandardMaterial({ color: 0xb9bdc1, metalness: 1, roughness: 0.3 });
  M.gold = new THREE.MeshStandardMaterial({ color: 0xb59d74, metalness: 1, roughness: 0.34 });
  M.black = new THREE.MeshStandardMaterial({ color: 0x0b0c0d, roughness: 0.85 });
  M.rubber = new THREE.MeshStandardMaterial({ color: 0x2a2e33, roughness: 0.8 });
  M.wheel = new THREE.MeshStandardMaterial({ color: 0x16181a, roughness: 0.55, metalness: 0.1 });
  M.ledOff = new THREE.MeshPhysicalMaterial({ color: 0xdfe8ee, roughness: 0.15, transmission: 0.0, transparent: true, opacity: 0.85 });
  M.ledOn = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0x7fd8ff, emissiveIntensity: 2.2, roughness: 0.3 });
  M.ledAmber = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffb347, emissiveIntensity: 2.2, roughness: 0.3 });
  M.pcb = new THREE.MeshStandardMaterial({ color: 0x1d6b4a, roughness: 0.45 });
  M.pcbDark = new THREE.MeshStandardMaterial({ color: 0x174d38, roughness: 0.5 });
  M.ic = new THREE.MeshStandardMaterial({ color: 0x1a1a1c, roughness: 0.6 });
  M.can = new THREE.MeshStandardMaterial({ color: 0xbfc3c7, metalness: 1, roughness: 0.3 });
  M.fpc = new THREE.MeshStandardMaterial({ color: 0xd98a2b, roughness: 0.4, metalness: 0.1 });
  M.kapton = new THREE.MeshStandardMaterial({ color: 0xd9a441, roughness: 0.35, transparent: true, opacity: 0.85 });
  M.pet = new THREE.MeshStandardMaterial({ color: 0x9fb7c4, roughness: 0.3, transparent: true, opacity: 0.7 });
  M.battery = new THREE.MeshStandardMaterial({ color: 0xc3c8cc, metalness: 0.7, roughness: 0.38 });
  M.batteryLabel = new THREE.MeshStandardMaterial({ color: 0x2f5d8a, roughness: 0.5 });
  M.jackBody = new THREE.MeshStandardMaterial({ color: 0x1b1c1e, roughness: 0.7 });
  M.wireRed = new THREE.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.5 });
  M.wireBlack = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.5 });
  M.wireWhite = new THREE.MeshStandardMaterial({ color: 0xe8e8e8, roughness: 0.5 });
  M.coax = new THREE.MeshStandardMaterial({ color: 0x3a3a3a, roughness: 0.5 });
  M.inductor = new THREE.MeshStandardMaterial({ color: 0x3a3c3f, roughness: 0.5, metalness: 0.3 });
  M.cap = new THREE.MeshStandardMaterial({ color: 0xb59a6a, roughness: 0.5 });
  M.speaker = new THREE.MeshStandardMaterial({ color: 0x121314, roughness: 0.6 });
  M.speakerCone = new THREE.MeshStandardMaterial({ color: 0x3b3b3d, roughness: 0.4 });
  return M;
}

// ---------- geometry helpers ----------
export function roundRectShape(w, h, r, cx = 0, cy = 0) {
  const s = new THREE.Shape();
  const x0 = cx - w / 2, y0 = cy - h / 2;
  r = Math.min(r, w / 2, h / 2);
  s.moveTo(x0 + r, y0);
  s.lineTo(x0 + w - r, y0); s.absarc(x0 + w - r, y0 + r, r, -Math.PI / 2, 0, false);
  s.lineTo(x0 + w, y0 + h - r); s.absarc(x0 + w - r, y0 + h - r, r, 0, Math.PI / 2, false);
  s.lineTo(x0 + r, y0 + h); s.absarc(x0 + r, y0 + h - r, r, Math.PI / 2, Math.PI, false);
  s.lineTo(x0, y0 + r); s.absarc(x0 + r, y0 + r, r, Math.PI, 1.5 * Math.PI, false);
  return s;
}
// Extrude a shape drawn in (X, -Y) drawing coordinates upward from z0 to z1.
// Shape coords: sx = X-74, sy = 24.5-Y.
export function slab(shape, z0, z1, bevel = 0, segs = 3) {
  const d = Math.max(0.01, z1 - z0 - 2 * bevel);
  const g = new THREE.ExtrudeGeometry(shape, { depth: d, bevelEnabled: bevel > 0, bevelThickness: bevel, bevelSize: bevel, bevelSegments: segs, curveSegments: 40 });
  g.rotateX(-Math.PI / 2);
  g.translate(0, z0 + bevel, 0);
  return g;
}
export function rrect(Xc, Yc, w, h, r, z0, z1, bevel = 0) {
  return slab(roundRectShape(w - 2 * bevel, h - 2 * bevel, Math.max(0.05, r - bevel), Xc - 74, 24.5 - Yc), z0, z1, bevel);
}
export function cyl(X, Y, d, z0, z1, seg = 64) {
  const g = new THREE.CylinderGeometry(d / 2, d / 2, z1 - z0, seg);
  g.translate(X - 74, (z0 + z1) / 2, Y - 24.5);
  return g;
}
export function box(X, Y, w, h, z0, z1) { // w along X, h along Y
  const g = new THREE.BoxGeometry(w, z1 - z0, h);
  g.translate(X - 74, (z0 + z1) / 2, Y - 24.5);
  return g;
}
function brush(g) { const b = new Brush(g); b.updateMatrixWorld(); return b; }
export function csgSub(baseGeom, cutters) {
  let acc = brush(baseGeom);
  for (const c of cutters) acc = ev.evaluate(acc, brush(c), SUBTRACTION);
  return acc.geometry;
}
export function csgAdd(geoms) {
  let acc = brush(geoms[0]);
  for (const g of geoms.slice(1)) acc = ev.evaluate(acc, brush(g), ADDITION);
  return acc.geometry;
}
export function mesh(g, m, cast = true, recv = true) { const o = new THREE.Mesh(g, m); o.castShadow = cast; o.receiveShadow = recv; return o; }
function dmesh(g, m) { const mm = m.clone(); mm.side = THREE.DoubleSide; mm.shadowSide = THREE.FrontSide; return mesh(g, mm); }

// knurled wheel (vertical axis)
function knurlShape(r, teeth, depth) {
  const s = new THREE.Shape();
  const N = teeth * 6;
  for (let i = 0; i <= N; i++) {
    const a = (i / N) * Math.PI * 2;
    const t = (i % 6) / 6;
    const rr = r - depth * (t < 0.5 ? 0 : 1) * Math.sin(Math.PI * (t - 0.5) * 2) ** 2;
    const x = rr * Math.cos(a), y = rr * Math.sin(a);
    if (i === 0) s.moveTo(x, y); else s.lineTo(x, y);
  }
  return s;
}

// ---------- data from R3 drawings (vector-extracted, mm) ----------
export const R3 = {
  L: 148, Wd: 49, Rc: 2, top: 3.80,
  screws: [[5.3, 5.3], [142.7, 5.3], [5.3, 43.7], [142.7, 43.7]],
  wheels: [[15, 10, 'VOL'], [35, 10, 'TONE'], [55, 10, 'FX']],
  leds: [[15, 21], [35, 21], [55, 21]],
  keys: [[10, 25, 'FX'], [23, 25, 'MODE'], [36, 25, 'MIX'], [49, 25, 'PWR'], [62, 25, 'BT']],
  jacks: [[46.5, 37, 'FX SEND'], [64.8, 37, 'LINE OUT'], [83.1, 37, 'AUX/RETURN'], [101.4, 37, 'PHONES']],
  usb: [98, 9.0],
  grille: { X0: 124.45, X1: 139.5, Y0: 14.95, Y1: 35.04, slotX0: 126.5, slotX1: 137.4, slots: [17.8, 19.8, 21.8, 23.8, 25.8, 27.8, 29.8, 31.8] },
  cup: { X0: 35.5, X1: 112.5, Y0: 2, Y1: 47, bottom: -21.05 },
};

// ---------- cover + exterior parts ----------
export function buildCover(M, variant = 'r3') {
  const P = variant === 'proposal';
  const g = new THREE.Group(); g.name = 'cover';
  const top = R3.top;
  const base = rrect(74, 24.5, R3.L, R3.Wd, R3.Rc, 0, top, 0.55);
  const cut = [];
  for (const [X, Y] of R3.screws) { cut.push(cyl(X, Y, 2.5, -1, 6, 40)); cut.push(cyl(X, Y, 4.5, 1.70, 6, 48)); }
  for (const [X, Y] of R3.wheels) cut.push(cyl(X, Y, 15.2, -1, 6, 96));
  if (!P) for (const [X, Y] of R3.leds) cut.push(cyl(X, Y, 2.1, -1, 6, 32));
  else for (const X of [15, 35, 55]) cut.push(rrect(X, 19.5, 12.0, 1.5, 0.75, -1, 6)); // segmented light-guide slots
  for (const [X, Y, n] of R3.keys) {
    cut.push(cyl(X, Y, 5.2, -1, 6, 48));
    const recD = (P && n === 'PWR') ? 8.4 : 7.2;
    cut.push(cyl(X, Y, recD, 3.30, 6, 64));
  }
  for (const [X, Y] of R3.jacks) { cut.push(cyl(X, Y, 12.0, 1.8, 6, 96)); cut.push(cyl(X, Y, 6.9, -1, 6, 64)); }
  cut.push(rrect(R3.usb[0], R3.usb[1], 12.0, 7.4, 1.5, 2.6, 6));
  cut.push(rrect(R3.usb[0], R3.usb[1], 10.2, 4.5, 2.2, -1, 6));
  const G = R3.grille;
  cut.push(rrect((G.X0 + G.X1) / 2, (G.Y0 + G.Y1) / 2, G.X1 - G.X0, G.Y1 - G.Y0, 1.8, top - 0.32, 6));
  cut.push(rrect((G.X0 + G.X1) / 2, (G.Y0 + G.Y1) / 2, 13.2, 18.3, 1.0, -1, 6));
  const coverGeom = csgSub(base, cut);
  g.add(dmesh(coverGeom, M.cover));

  // grille plate
  const gx = (G.X0 + G.X1) / 2, gy = (G.Y0 + G.Y1) / 2;
  let plate = rrect(gx, gy, G.X1 - G.X0 - 0.15, G.Y1 - G.Y0 - 0.15, 1.7, top - 0.32, top - 0.1);
  const sc = [];
  if (!P) {
    for (const y of G.slots) sc.push(rrect((G.slotX0 + G.slotX1) / 2, y, G.slotX1 - G.slotX0, 0.8, 0.4, top - 1, top + 1));
  } else {
    for (let iy = 0; iy < 11; iy++) for (let ix = 0; ix < 7; ix++) {
      const X = gx - 5.4 + ix * 1.8 + (iy % 2 ? 0.9 : 0), Y = gy - 8.0 + iy * 1.6;
      if (X > G.X1 - 1.6) continue;
      sc.push(cyl(X, Y, 0.9, top - 1, top + 1, 12));
    }
  }
  plate = csgSub(plate, sc);
  g.add(dmesh(plate, P ? M.steelDark : M.steel));
  // speaker beneath grille (visible through slots)
  g.add(mesh(rrect(gx, gy, 12.9, 17.9, 1.0, 0.6, top - 0.36), M.speaker));

  // screws (pan head, Phillips)
  for (const [X, Y] of R3.screws) {
    let h = cyl(X, Y, 4.1, 1.72, 3.05, 40);
    const dome = new THREE.SphereGeometry(2.05, 32, 12, 0, Math.PI * 2, 0, Math.PI / 2); dome.scale(1, 0.25, 1); dome.translate(X - 74, 3.05, Y - 24.5);
    h = csgAdd([h, dome]);
    h = csgSub(h, [box(X, Y, 2.4, 0.5, 2.7, 4), box(X, Y, 0.5, 2.4, 2.7, 4)]);
    g.add(dmesh(h, P ? M.steelDark : M.nickel));
  }
  // wheels
  for (const [X, Y, n] of R3.wheels) {
    if (!P) {
      const wg = slab(knurlShape(7.1, 60, 0.18), top - 1.4, top + 0.55, 0.12, 2); wg.translate(X - 74, 0, Y - 24.5);
      g.add(mesh(wg, M.wheel));
      const dot = cyl(X + 5.0, Y, 0.9, top + 0.5, top + 0.58, 16); g.add(mesh(dot, M.ledOff));
    } else {
      // raised knurled rim + concave dished centre for fingertip grip
      const rim = slab(knurlShape(7.1, 48, 0.32), top - 1.4, top + 1.45, 0.12, 2); rim.translate(X - 74, 0, Y - 24.5);
      const dish = csgSub(rim, [cyl(X, Y, 10.4, top + 0.9, top + 3, 64)]);
      g.add(dmesh(dish, M.wheel));
      g.add(mesh(cyl(X, Y, 10.4, top - 1.4, top + 0.9, 64), M.rubber));
      g.add(mesh(cyl(X, Y, 14.6, top - 0.2, top + 0.05, 96), M.gold, false));
      g.add(mesh(box(X + 3.6, Y, 2.2, 0.5, top + 0.9, top + 0.95), M.gold, false));
    }
  }
  // keys
  for (const [X, Y, n] of R3.keys) {
    const guard = P && n === 'PWR';
    const pts = [];
    const r = 3.0, h0 = 3.65, h1 = guard ? 3.62 : 4.15;
    pts.push(new THREE.Vector2(0, h0)); pts.push(new THREE.Vector2(r, h0));
    for (let i = 0; i <= 8; i++) { const a = i / 8 * Math.PI / 2; pts.push(new THREE.Vector2(r - 0.35 + 0.35 * Math.cos(a), h1 - 0.35 + 0.35 * Math.sin(a) - (guard ? 0 : 0.0))); }
    pts.push(new THREE.Vector2(0, h1 + (guard ? -0.12 : 0.05)));
    const kg = new THREE.LatheGeometry(pts, 64); kg.translate(X - 74, 0, Y - 24.5);
    g.add(mesh(kg, P ? M.rubber : M.rubber));
    g.add(mesh(cyl(X, Y, guard ? 8.3 : 7.1, 2.9, 3.31, 48), M.black, false));
    if (P && n === 'PWR') { const tr = new THREE.TorusGeometry(4.35, 0.22, 12, 96); tr.rotateX(Math.PI / 2); tr.translate(X - 74, top, Y - 24.5); g.add(mesh(tr, M.gold, false)); }
  }
  // LEDs / light bar
  if (!P) {
    R3.leds.forEach(([X, Y], i) => g.add(mesh(cyl(X, Y, 1.9, 0.5, top - 0.02, 24), i === 0 ? M.ledOn : M.ledOff, false)));
  } else {
    [15, 35, 55].forEach((X, i) => g.add(mesh(rrect(X, 19.5, 11.8, 1.3, 0.65, 0.5, top - 0.03), i < 2 ? M.ledOn : M.ledOff, false)));
  }
  // jacks: collar + bore
  for (const [X, Y] of R3.jacks) {
    let col = cyl(X, Y, 6.6, 1.0, top + 0.05, 64);
    col = csgSub(col, [cyl(X, Y, 3.6, -2, 6, 48)]);
    g.add(mesh(col, P ? M.gold : M.nickel));
    g.add(mesh(cyl(X, Y, 11.6, 0.0, 1.8, 64), M.jackBody));
    g.add(mesh(cyl(X, Y, 3.6, -8, 1.0, 32), M.black, false));
  }
  // USB-C receptacle
  {
    const [X, Y] = R3.usb;
    let shell = rrect(X, Y, 8.94, 3.26, 1.63, -5, 2.35);
    shell = csgSub(shell, [rrect(X, Y, 8.34, 2.66, 1.33, -4, 3)]);
    g.add(mesh(shell, M.nickel));
    g.add(mesh(rrect(X, Y, 6.7, 0.7, 0.2, -4, 1.9), M.black));
    g.add(mesh(rrect(X, Y, 8.6, 3.0, 1.5, -4.5, -3.8), M.black));
  }
  return g;
}

export function buildCup(M) {
  const C = R3.cup;
  let cup = rrect((C.X0 + C.X1) / 2, (C.Y0 + C.Y1) / 2, C.X1 - C.X0, C.Y1 - C.Y0, 2.0, C.bottom, -0.02, 0.6);
  const clips = [];
  for (const X of [55, 93]) for (const Y of [C.Y0, C.Y1]) clips.push(box(X, Y, 8, 1.2, -9, -4.5));
  cup = csgSub(cup, clips);
  const g = new THREE.Group(); g.name = 'cup';
  g.add(dmesh(cup, M.cup));
  return g;
}

// ---------- internal parts (for exploded view) ----------
function chip(parent, M, X, Y, w, h, z0, t, mat = M.ic) { parent.add(mesh(box(X, Y, w, h, z0, z0 + t), mat)); }

export function buildInternals(M) {
  const parts = {};
  // cover (control) board 0.4 mm, Z 0.1..0.5
  {
    const g = new THREE.Group(); g.name = 'coverBoard';
    let b = rrect(74, 24.5, 148, 46, 1.0, 0.1, 0.5);
    const cut = [];
    for (const [X, Y] of R3.screws) cut.push(cyl(X, Y, 5.2, -1, 2, 32));
    for (const [X] of R3.jacks) cut.push(rrect(X, 35.5, 11.6, 12.6, 0.5, -1, 2));
    cut.push(rrect(127.1, 40.5, 27, 10.3, 0.5, -1, 2)); // antenna window
    cut.push(rrect(98.6, 7.0, 11.3, 7.1, 0.5, -1, 2));  // USB opening
    b = csgSub(b, cut);
    g.add(dmesh(b, M.pcb));
    for (const [X, Y] of R3.wheels) { chip(g, M, X, Y, 10, 10, 0.5, 1.0, M.can); }
    for (const [X, Y] of R3.keys) { chip(g, M, X, Y, 5.2, 5.2, 0.5, 1.0, M.ic); g.add(mesh(cyl(X, Y, 1.6, 1.5, 1.6, 16), M.can)); }
    for (const [X, Y] of R3.leds) chip(g, M, X, Y, 1.6, 0.8, 0.5, 0.6, M.ledOn);
    // speaker 18x13x2.5 (long axis along Y)
    g.add(mesh(rrect(132, 25, 13, 18, 1.2, 0.5, 3.0), M.speaker));
    g.add(mesh(rrect(132, 25, 9.5, 14.5, 3.0, 2.95, 3.05), M.speakerCone));
    // FPC antenna in window
    g.add(mesh(rrect(127.1, 40.5, 25, 9, 0.5, 0.0, 0.12), M.fpc));
    parts.coverBoard = g;
  }
  // wheels (RK10J discs) & keycaps follow cover; audio board with jacks
  {
    const g = new THREE.Group(); g.name = 'audioBoard';
    g.add(mesh(rrect(73.8, 37, 73.0, 13.4, 0.6, -10.65, -9.65), M.pcb));
    for (const [X, Y] of R3.jacks) {
      g.add(mesh(box(X, Y, 10.6, 10.6, -9.65, 0.9), M.jackBody));
      let col = cyl(X, Y, 6.6, 0.9, 3.85, 48); col = csgSub(col, [cyl(X, Y, 3.6, -1, 5, 32)]);
      g.add(mesh(col, M.nickel));
      for (const dx of [-3.5, 3.5]) g.add(mesh(box(X + dx, Y + 5.6, 1.2, 0.6, -11.05, -6), M.nickel));
    }
    parts.audioBoard = g;
  }
  // USB board + sensor board (tray hanging from cover)
  {
    const g = new THREE.Group(); g.name = 'usbBoard';
    g.add(mesh(rrect(98.6, 15.5, 22, 21, 0.8, -6.0, -5.0), M.pcbDark));
    let shell = rrect(98, 9, 8.94, 3.26, 1.63, -5.0, 2.35); shell = csgSub(shell, [rrect(98, 9, 8.3, 2.6, 1.3, -4, 3)]);
    g.add(mesh(shell, M.nickel));
    chip(g, M, 98, 15, 3.0, 2.0, -6.9, 0.9); chip(g, M, 93, 18, 1.6, 1.6, -6.6, 0.6); chip(g, M, 103, 18, 3, 3, -6.9, 0.9);
    g.add(mesh(rrect(91, 23.5, 14, 7.5, 0.4, -3.2, -2.4), M.pcb));
    chip(g, M, 92, 23.5, 2, 2, -2.4, 0.75);
    parts.usbBoard = g;
  }
  // main board 0.8 mm at Z -12.55..-11.75 ; BOM coords offset (37.2, 3.5)
  {
    const g = new THREE.Group(); g.name = 'mainBoard';
    const ox = 37.2, oy = 3.5, zt = -11.75;
    let b = rrect(74, 24.5, 73.6, 42, 1.0, -12.55, zt);
    g.add(mesh(b, M.pcb));
    const P = (x, y) => [ox + x, oy + y];
    const F = (x, y, w, h, t, mat) => { const [X, Y] = P(x, y); chip(g, M, X, Y, w, h, zt, t, mat); };
    F(32.7, 13.1, 14, 14, 1.4); // STM32H743 LQFP100
    for (let i = 0; i < 25; i++) for (const s of [-1, 1]) { const [X, Y] = P(32.7 - 6 + i * 0.5, 13.1 + s * 7.5); chip(g, M, X, Y, 0.22, 1.0, zt, 0.15, M.can); const [X2, Y2] = P(32.7 + s * 7.5, 13.1 - 6 + i * 0.5); chip(g, M, X2, Y2, 1.0, 0.22, zt, 0.15, M.can); }
    { const [X, Y] = P(49.3, 11.8); chip(g, M, X, Y, 13.2, 16.6, zt, 0.8, M.pcbDark); chip(g, M, X, Y - 1.5, 12.2, 11.5, zt + 0.8, 1.6, M.can); g.add(mesh(cyl(X - 4.5, Y + 6.5, 2.0, zt + 0.8, zt + 2.0, 24), M.can)); }
    F(12, 7.8, 7.8, 6.4, 1.1); F(12, 17.8, 6.5, 4.4, 1.1); F(19.3, 21.3, 3, 3, 0.8); F(60.3, 6.8, 3, 3, 0.8);
    F(61.3, 14.8, 2.5, 3, 0.9); F(65.8, 14.8, 4, 4, 2.1, M.inductor); F(60.3, 22.8, 3, 3, 0.8); F(66.3, 6.8, 2, 2, 0.75);
    F(19.95, 6.65, 5, 4.4, 1.1); F(19.95, 15.95, 5, 4.4, 1.1); F(19.8, 11.3, 3.2, 2.5, 0.8, M.can); F(68.3, 22.8, 2.9, 1.6, 0.9); F(11.25, 23.25, 3, 3, 1.0);
    for (const [x, y] of [[4.9, 24.05], [32.3, 24.05], [39.3, 24.05], [64.15, 23.8], [47.6, 24.05]]) F(x, y, 4.45, 2.65, 2.0);
    // passives scatter (deterministic)
    let s = 7; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
    for (let i = 0; i < 90; i++) { const x = 3 + rnd() * 68, y = 2 + rnd() * 38; if (x > 24 && x < 41 && y > 5 && y < 21) continue; if (x > 42 && x < 56.5 && y > 3 && y < 21) continue; F(x, y, 1.6, 0.8, 0.5, rnd() > 0.5 ? M.cap : M.ic); }
    // battery JST on B side
    { const [X, Y] = P(67.1, 21.1); chip(g, M, X, Y, 4.5, 8.5, -12.55 - 1.0, 1.0, M.wireWhite); }
    // coax to antenna
    { const [X, Y] = P(44.8, 18.3); const c = new THREE.CatmullRomCurve3([W(X, Y, zt + 2.0), W(X + 10, Y + 12, -6), W(112, 40, -3), W(118, 41, 0.2)]); g.add(mesh(new THREE.TubeGeometry(c, 60, 0.4, 10), M.coax)); }
    parts.mainBoard = g;
  }
  // insulation + battery 52 x 34.5 x 5.4
  {
    const g = new THREE.Group(); g.name = 'battery';
    g.add(mesh(rrect(66, 24.5, 54, 36.5, 1.0, -13.8, -13.7), M.pet));
    let bat = rrect(66, 24.5, 52, 34.5, 2.0, -20.2, -14.8, 0.6);
    g.add(mesh(bat, M.battery));
    g.add(mesh(rrect(64, 24.5, 30, 20, 1.0, -14.81, -14.78), M.batteryLabel));
    g.add(mesh(rrect(66 + 27.5, 24.5, 3, 12, 0.5, -17.8, -17.2), M.kapton));
    const wires = [[M.wireRed, -2.5], [M.wireBlack, 0], [M.wireWhite, 2.5]];
    for (const [m, dy] of wires) { const c = new THREE.CatmullRomCurve3([W(93, 24.5 + dy, -17.5), W(98, 24.5 + dy, -17), W(102, 26 + dy, -14.5), W(104.3, 24.6 + dy, -13.6)]); g.add(mesh(new THREE.TubeGeometry(c, 30, 0.45, 8), m)); }
    g.add(mesh(rrect(66, 24.5, 54, 36.5, 1.0, -20.3, -20.2), M.pet));
    parts.battery = g;
  }
  return parts;
}

// ---------- labels (proposal: laser-etched legends) ----------
export function legendTexture(variant) {
  const S = 20; // px per mm
  const cv = document.createElement('canvas'); cv.width = 148 * S; cv.height = 49 * S;
  const c = cv.getContext('2d');
  c.clearRect(0, 0, cv.width, cv.height);
  c.fillStyle = 'rgba(214,218,222,0.92)'; c.strokeStyle = 'rgba(214,218,222,0.92)';
  c.textAlign = 'center'; c.textBaseline = 'middle';
  const font = (px, w = 600) => `${w} ${px * S}px "DejaVu Sans", "WenQuanYi Zen Hei", sans-serif`;
  const T = (t, X, Y, px = 1.55, w = 600) => { c.font = font(px, w); c.fillText(t, X * S, Y * S); };
  T('VOL', 25.0, 10, 1.25); T('TONE', 45.0, 10, 1.2); T('FX', 65.0, 10, 1.25);
  T('FX', 10, 30.2); T('MODE', 23, 30.2); T('MIX', 36, 30.2); T('BT', 62, 30.2);
  // power icon
  { const X = 49, Y = 30.3; c.lineWidth = 0.28 * S; c.beginPath(); c.arc(X * S, Y * S, 0.95 * S, -Math.PI / 2 + 0.6, Math.PI * 1.5 - 0.6); c.stroke(); c.beginPath(); c.moveTo(X * S, (Y - 1.25) * S); c.lineTo(X * S, (Y - 0.1) * S); c.stroke(); }
  T('SEND', 46.5, 45.6, 1.35); T('LINE OUT', 64.8, 45.6, 1.35); T('RETURN', 83.1, 45.6, 1.35); T('PHONES', 101.4, 45.6, 1.35);
  T('5V', 98, 14.4, 1.25);
  c.font = font(2.0, 700); c.textAlign = 'left'; c.fillText('SmartVio', 113.5 * S, 3.4 * S);
  // tactile dot hint next to PWR
  return cv;
}

export function buildLegend(M) {
  const cv = legendTexture();
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  const mat = new THREE.MeshStandardMaterial({ map: tex, transparent: true, roughness: 0.7, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 });
  const g = new THREE.PlaneGeometry(148, 49); g.rotateX(-Math.PI / 2); g.translate(0, R3.top + 0.004, 0);
  const m = new THREE.Mesh(g, mat); m.renderOrder = 5; return m;
}

// ---------- module assembly ----------
export function buildModule(M, variant = 'r3', opts = {}) {
  const g = new THREE.Group();
  g.add(buildCover(M, variant));
  if (variant === 'proposal') g.add(buildLegend(M));
  if (opts.cup !== false) g.add(buildCup(M));
  return g;
}

// ---------- illustrative skeleton electric violin ----------
// Violin coordinates: u = distance from tail metal datum toward head (mm).
// Body top (string side) faces +y_v; back faces -y_v.  Built in its own frame then placed.
function outlineHalf() {
  // half violin outline (u, w) from tail (u=0) to neck heel (u=356), w = half-width
  return [[0, 0], [2, 40], [12, 72], [32, 95], [60, 103], [95, 100], [125, 88], [145, 66], [165, 57], [190, 56], [212, 62], [228, 76], [250, 82], [275, 84], [305, 78], [330, 62], [348, 38], [356, 0]];
}
export function buildViolin(M) {
  const V = new THREE.Group(); V.name = 'violin';
  const wood = new THREE.MeshPhysicalMaterial({ color: 0x3f1a09, roughness: 0.4, clearcoat: 0.5, clearcoatRoughness: 0.3, envMapIntensity: 0.6 });
  const woodDark = new THREE.MeshPhysicalMaterial({ color: 0x2c140a, roughness: 0.4, clearcoat: 0.5, envMapIntensity: 0.6 });
  const ebony = new THREE.MeshStandardMaterial({ color: 0x0f0d0c, roughness: 0.35 });
  const maple = new THREE.MeshStandardMaterial({ color: 0xd9b98a, roughness: 0.6 });
  const string = new THREE.MeshStandardMaterial({ color: 0xc8c8c8, metalness: 1, roughness: 0.25 });
  // central column body (solid), u from -2..356, width profile, thickness 32 (y from -16..16)
  const prof = [[-2, 27], [40, 31], [90, 31], [130, 30], [180, 29.5], [235, 30], [290, 29], [330, 26], [356, 21]];
  const sh = new THREE.Shape();
  prof.forEach(([u, w], i) => (i ? sh.lineTo(u, w) : sh.moveTo(u, w)));
  [...prof].reverse().forEach(([u, w]) => sh.lineTo(u, -w));
  sh.closePath();
  const col = new THREE.ExtrudeGeometry(sh, { depth: 26, bevelEnabled: true, bevelThickness: 3, bevelSize: 3, bevelSegments: 6, curveSegments: 24 });
  col.translate(0, 0, -13); // z_v = thickness axis -16..16
  V.add(mesh(col, wood));
  // outline frame tube (maple-tinted dark wood), slightly forward (string side)
  const half = outlineHalf();
  const ptsR = half.map(([u, w]) => new THREE.Vector3(u, w, 4));
  const ptsL = half.slice().reverse().map(([u, w]) => new THREE.Vector3(u, -w, 4));
  const loop = new THREE.CatmullRomCurve3([...ptsR, ...ptsL.slice(1, -1)], true, 'centripetal');
  V.add(mesh(new THREE.TubeGeometry(loop, 400, 5.0, 16, true), woodDark));
  // neck + fingerboard + scroll
  const neck = new THREE.BoxGeometry(130, 26, 22); neck.translate(356 + 65, 0, 3); V.add(mesh(neck, wood));
  const fbShape = new THREE.Shape(); fbShape.moveTo(250, -21); fbShape.lineTo(356 + 130, -12); fbShape.lineTo(356 + 130, 12); fbShape.lineTo(250, 21); fbShape.closePath();
  const fb = new THREE.ExtrudeGeometry(fbShape, { depth: 6, bevelEnabled: true, bevelThickness: 1, bevelSize: 1, bevelSegments: 3 }); fb.translate(0, 0, 17); V.add(mesh(fb, ebony));
  const pegbox = new THREE.BoxGeometry(75, 22, 26); pegbox.translate(356 + 130 + 37, 0, 4); V.add(mesh(pegbox, wood));
  const spiralPts = []; for (let i = 0; i <= 160; i++) { const t = i / 160 * Math.PI * 3.2; const r = 21 * Math.exp(-0.17 * t); spiralPts.push(new THREE.Vector3(356 + 130 + 75 + 18 + r * Math.sin(t), 0, 6 + r * Math.cos(t) - 4)); }
  for (const dy of [-6, 6]) { const sc = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(spiralPts), 200, 4.5, 12); sc.translate(0, dy * 0.9, 0); V.add(mesh(sc, wood)); }
  for (let i = 0; i < 4; i++) { const u = 356 + 145 + i * 15; const side = i % 2 ? 1 : -1; const p = new THREE.CylinderGeometry(3.2, 2.5, 40, 16); p.translate(u, side * 26, 4); V.add(mesh(p, ebony)); const hd = new THREE.SphereGeometry(7, 16, 12); hd.scale(1.3, 0.35, 1); hd.translate(u, side * 46, 4); V.add(mesh(hd, ebony)); }
  // tailpiece, bridge, chinrest, end button
  const tp = new THREE.Shape(); tp.moveTo(8, -9); tp.quadraticCurveTo(60, -22, 112, -19); tp.lineTo(112, 19); tp.quadraticCurveTo(60, 22, 8, 9); tp.closePath();
  const tpg = new THREE.ExtrudeGeometry(tp, { depth: 4, bevelEnabled: true, bevelThickness: 1.5, bevelSize: 1.5, bevelSegments: 3 }); tpg.translate(0, 0, 18); V.add(mesh(tpg, ebony));
  const br = new THREE.BoxGeometry(2.5, 42, 32); br.translate(165, 0, 31); V.add(mesh(br, maple));
  const eb = new THREE.CylinderGeometry(4, 5, 10, 24); eb.rotateZ(Math.PI / 2); eb.translate(-5, 0, 0); V.add(mesh(eb, ebony));
  // strings from tailpiece to nut
  for (let i = 0; i < 4; i++) { const y = -8.5 + i * 5.7; const a = new THREE.Vector3(110, y * 1.4, 24); const b = new THREE.Vector3(165, y * 1.25, 47); const c = new THREE.Vector3(486, y * 0.68, 25); const curve = new THREE.CatmullRomCurve3([a, b, c], false, 'chordal', 0); V.add(mesh(new THREE.TubeGeometry(new THREE.LineCurve3(a, b), 2, 0.45, 8), string, false)); V.add(mesh(new THREE.TubeGeometry(new THREE.LineCurve3(b, c), 2, 0.4 - i * 0.04, 8), string, false)); }
  return V;
}
