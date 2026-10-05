// Enregistrement des trajectoires et rendu de la « signature » : chaque membre trace un trait
// d'encre, épais quand le geste est lent, fin quand il est rapide (comme une plume).
(() => {
  // Membres qui signent et épaisseur relative de leur trait.
  const INK = { handR: 1, handL: 1, footL: 0.45, footR: 0.45, head: 0.35 };

  function create() { const tr = {}; for (const k in INK) tr[k] = []; return tr; }

  function add(tracks, body, t) {
    if (!body) return;
    for (const k in INK) {
      const p = body.joints[k];
      if (!p) continue;
      const a = tracks[k], last = a[a.length - 1];
      if (last && Math.hypot(p[0] - last[0], p[1] - last[1]) < 0.002) continue;  // immobile
      a.push([p[0], p[1], t]);
    }
  }

  // Moyenne glissante pour lisser le tremblement du capteur.
  function smooth(a, n = 2) {
    return a.map((p, i) => {
      let x = 0, y = 0, c = 0;
      for (let j = Math.max(0, i - n); j <= Math.min(a.length - 1, i + n); j++) { x += a[j][0]; y += a[j][1]; c++; }
      return [x / c, y / c, p[2]];
    });
  }

  function bounds(tracks) {
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const k in tracks) for (const [x, y] of tracks[k]) {
      x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y);
    }
    if (x0 > x1) return null;
    const m = 0.2;   // évite qu'un tout petit geste soit agrandi à l'extrême
    if (x1 - x0 < m) { const c = (x0 + x1) / 2; x0 = c - m / 2; x1 = c + m / 2; }
    if (y1 - y0 < m) { const c = (y0 + y1) / 2; y0 = c - m / 2; y1 = c + m / 2; }
    return { x0, y0, x1, y1 };
  }

  // Dessine les traces dans ctx. fit=true : recadre la signature dans le canvas (marge pad).
  function render(ctx, tracks, { color = "#000", width = 10, fit = true, pad = 0.08, clear = true } = {}) {
    const { width: W, height: H } = ctx.canvas;
    if (clear) ctx.clearRect(0, 0, W, H);
    let map = p => [p[0] * W, p[1] * H];
    if (fit) {
      const b = bounds(tracks);
      if (!b) return;
      const px = W * pad, py = H * pad;
      const k = Math.min((W - 2 * px) / (b.x1 - b.x0), (H - 2 * py) / (b.y1 - b.y0));
      const ox = (W - k * (b.x1 - b.x0)) / 2, oy = (H - k * (b.y1 - b.y0)) / 2;
      map = p => [ox + (p[0] - b.x0) * k, oy + (p[1] - b.y0) * k];
    }
    ctx.strokeStyle = ctx.fillStyle = color; ctx.lineCap = ctx.lineJoin = "round";
    for (const key in INK) {
      const a = smooth(tracks[key]).map(p => [...map(p), p[2]]);
      if (a.length < 3) continue;
      let prevW = null;
      for (let i = 1; i < a.length - 1; i++) {
        const [x0, y0] = mid(a[i - 1], a[i]), [x1, y1] = mid(a[i], a[i + 1]);
        const dt = Math.max(1, a[i + 1][2] - a[i - 1][2]);
        const speed = Math.hypot(a[i + 1][0] - a[i - 1][0], a[i + 1][1] - a[i - 1][1]) / Math.max(W, H) / dt * 1000;
        let w = width * INK[key] * Math.max(0.2, Math.min(1.6, 1.6 - speed * 2.5));
        w = prevW == null ? w : prevW * 0.7 + w * 0.3;  // variation progressive de l'épaisseur
        prevW = w;
        ctx.lineWidth = w;
        ctx.beginPath(); ctx.moveTo(x0, y0); ctx.quadraticCurveTo(a[i][0], a[i][1], x1, y1); ctx.stroke();
      }
    }
  }
  const mid = (p, q) => [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];

  // Longueur parcourue par les mains, en « largeurs d'image » (pour le texte de l'étiquette).
  function handTravel(tracks) {
    let d = 0;
    for (const k of ["handL", "handR"]) {
      const a = tracks[k];
      for (let i = 1; i < a.length; i++) d += Math.hypot(a[i][0] - a[i - 1][0], a[i][1] - a[i - 1][1]);
    }
    return d;
  }

  window.Signature = { create, add, render, handTravel };
})();
