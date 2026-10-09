(() => {
  const C = window.CONFIG;
  const SIM = C.SIMULATE || /[?&]sim=1/.test(location.search);
  const SAMPLES = ["assets/sample-1.svg", "assets/sample-2.svg", "assets/sample-3.svg"];
  const UI = {
    fr: { kicker: "Contrôle de sûreté", title: "Vide ton sac !",
          steps: ["Vide tes poches ou ton sac dans le bac.",
                  "Glisse le bac dans le scanner.",
                  "Attends le verdict à l’écran.",
                  "Récupère tes affaires et remets le bac au début du scanner."],
          waiting: "Le scanner attend ton bac…",
          wait: { partial: "Bac mal placé.\nGlisse-le en entier sous la caméra.", moving: "Lâche le bac, ne le touche plus…",
                  hold: "Bac en place, ne bouge plus…", done: "Ce bac est déjà scanné.\nAu suivant !" },
          simulate: "Simuler un passage",
          scanning: "Analyse en cours…", stamp: "AUTORISÉ", clear: "Bonne visite !", xray: 'RAYONS <i class="xmark">✕</i>', restart: "Recommencer", home: "Retour à l’accueil", locale: "fr-BE",
          printing: "Colle ton étiquette dans ton passeport. N’oublie pas de récupérer tes affaires et de remettre le bac au début du scanner !",
          noprint: "N’oublie pas de récupérer tes affaires et de remettre le bac au début du scanner !",
          label: "Vide ton sac", info: ["Passager", "Date", "Heure", "Porte"],
          agent: ["Agent", "Sarah Sûre"] },
    en: { kicker: "Security check", title: "Empty your bag!",
          steps: ["Empty your pockets or your bag into the tray.",
                  "Slide the tray into the scanner.",
                  "Wait for the verdict on screen.",
                  "Collect your belongings and put the tray back at the start of the scanner."],
          waiting: "The scanner is waiting for your tray…",
          wait: { partial: "Tray not fully in view.\nSlide it all the way in.", moving: "Let go of the tray…",
                  hold: "Tray in place, hold still…", done: "This tray has already been scanned.\nNext one!" },
          simulate: "Simulate a pass",
          scanning: "Scanning…", stamp: "CLEAR", clear: "Enjoy the exhibition!", xray: '<i class="xmark">✕</i>-RAY', restart: "Start again", home: "Back to start", locale: "en-GB",
          printing: "Stick your label in your passport. Don’t forget to collect your belongings and put the tray back at the start of the scanner!",
          noprint: "Don’t forget to collect your belongings and put the tray back at the start of the scanner!",
          label: "Empty your bag", info: ["Passenger", "Date", "Time", "Gate"],
          agent: ["Agent", "Justin Case"] },
  };
  const $ = (s, el = document) => el.querySelector(s);
  const stage = $("#stage");
  let lang = "fr", state = "welcome", idleTimer, resultTimer, photoTimer, scanId = 0;

  // --- Mise à l'échelle de la scène 1024×768 ---
  function fit() {
    const k = Math.min(innerWidth / 1024, innerHeight / 768);
    stage.style.transform = `scale(${k}) translate(-50%, -50%)`;
  }
  addEventListener("resize", fit); fit();
  if (C.HIDE_CURSOR) document.body.classList.add("nocursor");
  addEventListener("contextmenu", e => e.preventDefault());

  // --- Étiquette : format de page selon CONFIG ---
  const W = C.LABEL_WIDTH_MM, H = C.LABEL_HEIGHT_MM, M = C.LABEL_MARGIN_MM;
  const pageStyle = document.createElement("style");
  pageStyle.textContent = `@page { size: ${W}mm ${H}mm; margin: 0; }
    #label { width: ${W}mm; height: ${H}mm; padding: ${M}mm; }`;
  document.head.appendChild(pageStyle);

  // Impression silencieuse : l'étiquette est envoyée au service local du kiosk (kiosk/print_server.py), qui
  // l'imprime sans rien afficher. Service absent (Windows, essai sur un PC) : impression du navigateur.
  async function printLabel() {
    try {
      const el = document.querySelector("#label"), copy = el.cloneNode(true), from = el.querySelectorAll("canvas, img");
      copy.querySelectorAll("canvas, img").forEach((n, i) => {       // un canvas copié est vide : on le fige en image
        let c = from[i];
        if (c.tagName !== "CANVAS") {
          if (!c.src.startsWith("blob:")) return;
          const im = c; c = document.createElement("canvas"); c.width = im.naturalWidth; c.height = im.naturalHeight;
          c.getContext("2d").drawImage(im, 0, 0);
        }
        const img = document.createElement("img");
        img.className = n.className; img.id = n.id; img.style.cssText = n.style.cssText; img.src = c.toDataURL("image/png");
        n.replaceWith(img);
      });
      const html = `<!doctype html><html><head><meta charset="utf-8"><base href="${location.href}">` +
        `<link rel="stylesheet" href="style.css"><style>${pageStyle.textContent}</style></head><body>${copy.outerHTML}</body></html>`;
      const r = await fetch("http://127.0.0.1:8361/print", { method: "POST", body: html });
      if (!r.ok) throw new Error(await r.text());
    } catch (e) { window.print(); }
  }

  // --- Réglage des filtres (contraste / luminosité / négatif) ---
  function tone(filter, contrast, brightness, invert) {
    const s = invert ? -contrast : contrast;
    const b = 0.5 - s / 2 + brightness;
    document.querySelectorAll(`#${filter} .tone > *`).forEach(f => {
      f.setAttribute("slope", s); f.setAttribute("intercept", b);
    });
  }
  tone("f-xray", C.SCAN_CONTRAST ?? 1.3, C.SCAN_BRIGHTNESS ?? 0, C.SCAN_INVERT ?? false);
  tone("f-print", C.PRINT_CONTRAST ?? 1.6, C.PRINT_BRIGHTNESS ?? 0.05, C.SCAN_INVERT ?? false);

  // Vue en direct de la caméra sur l'écran des consignes (helper en mode webcam) : le visiteur voit
  // son bac se placer, cadre vert quand il est bien dans le champ. Flux coupé hors de cet écran.
  const live = $("#steps .live");
  live.onerror = () => { live.hidden = true; };       // helper sans webcam (Pi) ou injoignable
  function setLive(on) {
    if (SIM || C.LIVE_PREVIEW === false) return;
    live.hidden = !on;
    if (on) live.src = C.HELPER_URL + "/live.mjpg?" + Date.now(); else live.removeAttribute("src");
  }

  // Vue de réglage (helper en mode webcam) : appui de 5 s sur le ✕ de l'accueil, comme au module 4.
  // Grande image en direct avec l'état du suivi du bac ; un appui dessus la ferme.
  const debug = $("#debug"), hiddenBtn = $("#welcome .xbox");
  let pressTimer;
  const setDebug = on => {
    debug.hidden = !on;
    if (on) debug.src = C.HELPER_URL + "/live.mjpg?debug&" + Date.now(); else debug.removeAttribute("src");
  };
  hiddenBtn.addEventListener("pointerdown", () => { pressTimer = setTimeout(() => SIM || setDebug(true), 5000); });
  for (const e of ["pointerup", "pointerleave", "pointercancel"]) hiddenBtn.addEventListener(e, () => clearTimeout(pressTimer));
  debug.addEventListener("pointerdown", () => setDebug(false));
  debug.onerror = () => setDebug(false);

  function show(id) {
    state = id;
    setLive(id === "steps");
    document.querySelectorAll(".screen").forEach(s => s.classList.toggle("active", s.id === id));
    clearTimeout(idleTimer);
    if (id !== "welcome") idleTimer = setTimeout(reset, C.IDLE_TIMEOUT_S * 1000);
  }

  function reset() {
    clearTimeout(resultTimer); clearTimeout(photoTimer);
    scanId++; lang = "fr"; document.documentElement.lang = lang;
    $("#scan").className = "screen";
    show("welcome");
  }

  // --- Accueil et consignes ---
  // Pictogrammes des consignes, un par étape : vider dans le bac, glisser dans le scanner, verdict à l'écran,
  // reprendre ses affaires et rapporter le bac.
  const ICONS = [
    '<path d="M10 40h44l-6 14H16z"/><path d="M32 6v24M23 21l9 9 9-9"/>',
    '<path d="M26 54V12h32v42M20 54h42M26 30h32M37 16l10 10M47 16l-10 10"/><path d="M2 43h20M15 36l7 7-7 7"/>',
    '<rect x="8" y="10" width="48" height="34"/><path d="M24 54h16M32 44v10M22 27l7 7 13-14"/>',
    '<path d="M10 40h44l-6 14H16z"/><path d="M46 30V21a9 9 0 0 0-9-9H18M25 5l-7 7 7 7"/>',
  ];

  // Écran des consignes : ce que le scanner attend (état du suivi du bac envoyé par le helper en mode webcam)
  let waitCode = "absent";
  function renderWait() {
    $("#steps .waiting span").textContent = UI[lang].wait[waitCode] || UI[lang].waiting;
    $("#steps .waiting").dataset.code = waitCode;
  }

  function renderSteps() {
    const t = UI[lang];
    $("#steps .kicker").textContent = t.kicker;
    $("#steps .title").textContent = t.title;
    $("#steps .list").innerHTML = t.steps.map((s, i) =>
      `<li><svg class="ico" viewBox="0 0 64 64">${ICONS[i] || ""}</svg><b>${i + 1}</b><span>${s}</span></li>`).join("");
    renderWait();
    const sim = $("#steps .simulate");
    sim.textContent = t.simulate; sim.hidden = !SIM;
    $("#steps .restart").setAttribute("aria-label", t.restart);
  }
  document.querySelectorAll(".lang").forEach(b => b.addEventListener("click", () => {
    lang = b.dataset.lang; document.documentElement.lang = lang;
    renderSteps(); show("steps");
  }));
  $(".restart").addEventListener("click", reset);
  $("#scan .home").addEventListener("click", reset);    // écran « autorisé » : retour immédiat à l'accueil
  $("#steps .simulate").addEventListener("click", () => manualTrigger());
  addEventListener("keydown", e => {
    if (e.code === "Space" || e.key === "s") { e.preventDefault(); manualTrigger(); }
    if (e.key === "Escape") reset();
  });

  // --- Déclenchement : GPIO (via le helper) ou simulation ---
  function manualTrigger() {
    if (SIM) { onTrigger(); setTimeout(() => onPhoto(SAMPLES[Math.floor(Math.random() * SAMPLES.length)]), 600); }
    else fetch(C.HELPER_URL + "/trigger", { method: "POST" }).catch(() => {});
  }

  if (!SIM) {
    const es = new EventSource(C.HELPER_URL + "/events");
    let downTimer = 0;
    es.addEventListener("open", () => { $("#offline").hidden = true; clearTimeout(downTimer); downTimer = 0; KioskStatus.clear("scanner"); });
    es.addEventListener("error", () => {
      $("#offline").hidden = false;
      // Toujours absent après 15 s : bandeau « en panne » sur l'accueil
      downTimer = downTimer || setTimeout(() => KioskStatus.report("scanner", "helper du scanner injoignable (" + C.HELPER_URL + ") : capteur et caméra hors service"), 15000);
    });
    es.addEventListener("state", e => { waitCode = JSON.parse(e.data).code; renderWait(); });
    es.addEventListener("trigger", onTrigger);
    es.addEventListener("photo", e => onPhoto(C.HELPER_URL + JSON.parse(e.data).url));
    es.addEventListener("failed", e => { console.warn("Capture :", e.data); onPhoto(null); });
  }

  // Le bac est entré : on passe à l'écran de scan et on attend la photo.
  function onTrigger() {
    if (state === "scan") return;           // un passage à la fois
    const t = UI[lang], id = ++scanId;
    const n = nextCount(), now = new Date();
    const info = [String(n).padStart(4, "0"),
                  now.toLocaleDateString(t.locale, { day: "2-digit", month: "2-digit", year: "numeric" }),
                  now.toLocaleTimeString(t.locale, { hour: "2-digit", minute: "2-digit" }), "✕"];
    const dl = t.info.map((k, i) => `<dt>${k}</dt><dd>${info[i]}</dd>`).join("") +
      `<dt>${t.agent[0]}</dt><dd class="agent">${t.agent[1]}</dd>`;   // l'agent de sûreté (jeu de mots, sans l'expliquer)
    $("#scan .kicker").textContent = t.kicker;
    $("#scan .info").innerHTML = dl;
    $("#scan .meta").textContent = `#${info[0]} · ${info[1]} ${info[2]}`;
    $("#scan .status span").textContent = t.scanning;
    $("#scan .stamp b").textContent = t.stamp;
    $("#scan .stamp span").textContent = t.clear;
    $("#scan .tag").innerHTML = t.xray;     // le X est le ✕ encadré de l'expo (clin d'œil)
    $(".l-stamp b").textContent = "✓ " + t.stamp;
    $("#scan .printing").textContent = "";
    $("#scan .home").textContent = t.home;
    $(".l-title").textContent = t.label;
    $(".l-kicker").textContent = t.kicker;
    $(".l-stamp span").textContent = t.clear;
    $(".l-info").innerHTML = dl;
    barcode($(".l-code"), n);
    const cv = $("#xray"); cv.getContext("2d").clearRect(0, 0, cv.width, cv.height);
    $("#scan").className = "screen waiting";
    show("scan");
    clearTimeout(idleTimer);
    beep(880, 0.08);
    // Pas de photo reçue : on scanne une image d'exemple plutôt que de bloquer le visiteur.
    clearTimeout(photoTimer);
    photoTimer = setTimeout(() => id === scanId && onPhoto(null), 8000);
  }

  function onPhoto(src) {
    if (state !== "scan" || !$("#scan").classList.contains("waiting")) return;
    clearTimeout(photoTimer);
    const id = scanId, img = new Image();
    if (src && /^https?:/.test(src)) img.crossOrigin = "anonymous";
    img.onload = () => id === scanId && runScan(img);
    img.onerror = () => { if (src) { console.warn("Image illisible :", src); img.src = SAMPLES[0]; } };
    img.src = src || SAMPLES[0];
  }

  // Dessine la photo recadrée/tournée dans un canvas, avec un filtre SVG.
  function render(img, canvas, filter, lines) {
    const ctx = canvas.getContext("2d"), cw = canvas.width, ch = canvas.height;
    const c = C.CROP || {}, iw = img.naturalWidth || img.width, ih = img.naturalHeight || img.height;
    const sx = iw * (c.left || 0), sy = ih * (c.top || 0);
    const sw = iw * (1 - (c.left || 0) - (c.right || 0)), sh = ih * (1 - (c.top || 0) - (c.bottom || 0));
    const rot = ((C.ROTATE || 0) % 360 + 360) % 360, side = rot === 90 || rot === 270;
    const dw = side ? ch : cw, dh = side ? cw : ch;
    const k = Math.max(dw / sw, dh / sh);    // remplit le cadre (object-fit: cover)
    const draw = f => {
      ctx.save();
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, cw, ch);
      ctx.translate(cw / 2, ch / 2);
      ctx.rotate(rot * Math.PI / 180);
      if (C.MIRROR) ctx.scale(-1, 1);
      ctx.filter = f ? `url(#${f})` : "none";
      ctx.drawImage(img, sx, sy, sw, sh, -sw * k / 2, -sh * k / 2, sw * k, sh * k);
      ctx.restore();
    };
    // Écran : rendu « rayons X » calculé pixel par pixel ; à défaut (SCAN_STYLE: "filtre",
    // ou image d'exemple illisible par le canvas), simple filtre de couleur.
    const style = C.SCAN_STYLE ?? "neon", rx = filter === "f-xray" && style !== "filtre";
    draw(rx ? null : filter);
    if (rx && !xray(canvas, style)) draw(filter);
    if (lines) {                              // fines lignes de balayage
      ctx.fillStyle = lines;
      for (let y = 0; y < ch; y += 4) ctx.fillRect(0, y, cw, 1);
    }
  }

  // Rendus « rayons X » calculés pixel par pixel (SCAN_STYLE). Le fond du bac sert de référence « vide » ;
  // plus un objet est sombre, plus il est « dense ». Chaque style : palette selon la densité + contours.
  const ramp = (pal, v, out) => {
    const n = pal.length - 1, f = Math.min(1, Math.max(0, v)) * n, a = Math.min(n - 1, f | 0), u = f - a;
    for (let c = 0; c < 3; c++) out[c] = pal[a][c] + (pal[a + 1][c] - pal[a][c]) * u;
  };
  const SCANNER = [[20, 18, 51], [46, 94, 173], [79, 163, 107], [227, 153, 69], [247, 237, 214], [255, 255, 250]];
  const STYLES = {
    // scanner d'aéroport : fond blanc, léger = orange, moyen = vert, dense = bleu
    aeroport: (d, e, g, o) => { ramp(SCANNER, 1 - d, o); const k = 1 - e; o[0] *= k; o[1] *= k; o[2] *= k; },
    // radiographie : fond noir, objets blanc bleuté avec une lueur
    radio: (d, e, g, o) => {
      ramp([[4, 6, 14], [20, 45, 80], [90, 150, 190], [215, 235, 245], [255, 255, 255]], d * 1.1 + .25 * g, o);
      o[0] += e * 130; o[1] += e * 130; o[2] += e * 130;
    },
    // scanner sur fond noir
    noir: (d, e, g, o) => {
      ramp([[6, 6, 16], [230, 150, 60], [240, 190, 70], [80, 180, 110], [60, 120, 230], [150, 200, 255]], d, o);
      const k = 1 - e * .7; o[0] *= k; o[1] *= k; o[2] *= k;
    },
    // contours lumineux roses sur bleu nuit (couleurs de l'expo)
    neon: (d, e, g, o) => {
      o[0] = 35 + d * 60 + e * 350 + g * 196; o[1] = 31 + d * 50 + e * 286 + g * 150; o[2] = 61 + d * 90 + e * 283 + g * 179;
    },
  };
  // Flou rapide : 3 passes de moyenne glissante, horizontale puis verticale
  function blur(src, w, h, r) {
    const a = Float32Array.from(src), b = new Float32Array(w * h), k = 2 * r + 1;
    const pass = (from, to, lines, len, line, step) => {
      for (let j = 0; j < lines; j++) {
        const o = j * line, at = i => from[o + Math.min(len - 1, Math.max(0, i)) * step];
        let acc = 0;
        for (let i = -r; i <= r; i++) acc += at(i);
        for (let i = 0; i < len; i++) { to[o + i * step] = acc / k; acc += at(i + r + 1) - at(i - r); }
      }
    };
    for (let n = 0; n < 3; n++) { pass(a, b, h, w, w, 1); pass(b, a, w, h, 1, w); }
    return a;
  }
  function xray(canvas, style) {
    const ctx = canvas.getContext("2d"), w = canvas.width, h = canvas.height;
    let im;
    try { im = ctx.getImageData(0, 0, w, h); } catch (e) { return false; }   // image d'une autre origine
    const p = im.data, n = w * h, L = new Float32Array(n), hist = new Uint32Array(256);
    for (let i = 0; i < n; i++) {
      L[i] = p[4 * i] * .299 + p[4 * i + 1] * .587 + p[4 * i + 2] * .114;
      hist[L[i] | 0]++;
    }
    // Fond du bac : la luminosité dépassée par seulement 15 % de l'image ; c'est le « vide »
    let bg = 255;
    for (let acc = 0; bg > 60 && (acc += hist[bg]) < n * .15; bg--);
    const contrast = C.SCAN_CONTRAST ?? 1.3, bright = C.SCAN_BRIGHTNESS ?? 0, inv = C.SCAN_INVERT ?? false;
    const edges = C.SCAN_EDGES ?? .7, D = new Float32Array(n), E = new Float32Array(n);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = y * w + x;
      const t = Math.min(1, Math.max(0, (Math.min(1, L[i] / bg / .92) - .5) * contrast + .5 + bright));
      D[i] = inv ? t : 1 - t;                                    // densité : 0 = vide, 1 = opaque
      if (x > 0 && y > 0 && x < w - 1 && y < h - 1) {            // contour (Sobel)
        const gx = L[i - w + 1] + 2 * L[i + 1] + L[i + w + 1] - L[i - w - 1] - 2 * L[i - 1] - L[i + w - 1];
        const gy = L[i + w - 1] + 2 * L[i + w] + L[i + w + 1] - L[i - w - 1] - 2 * L[i - w] - L[i - w + 1];
        E[i] = Math.min(1, Math.hypot(gx, gy) / 220) * edges;
      }
    }
    // Lueur : flou de la densité (radio) ou des contours (néon)
    const G = style === "radio" ? blur(D, w, h, 6) : style === "neon" ? blur(E, w, h, 3) : null;
    const paint = STYLES[style] || STYLES.neon, o = [0, 0, 0];
    for (let i = 0; i < n; i++) {
      paint(D[i], E[i], G ? G[i] : 0, o);
      p[4 * i] = o[0]; p[4 * i + 1] = o[1]; p[4 * i + 2] = o[2];   // tableau borné : dépassements écrêtés à 255
    }
    ctx.putImageData(im, 0, 0);
    return true;
  }

  function runScan(img) {
    const id = scanId, t = UI[lang];
    render(img, $("#xray"), "f-xray", "rgba(255,255,255,.07)");
    render(img, $(".l-img"), "f-print", "rgba(255,255,255,.35)");
    const scan = $("#scan");
    scan.style.setProperty("--scan-s", C.SCAN_S + "s");
    scan.className = "screen active scanning";
    hum(C.SCAN_S);
    // L'étiquette met plusieurs secondes à sortir (mise en page puis impression) : on la lance pendant le
    // balayage (PRINT_START_S après son début) pour qu'elle arrive avec le verdict. null = après le verdict.
    const early = C.PRINT_START_S ?? null;
    if (C.PRINT && early !== null) setTimeout(() => id === scanId && printLabel(), early * 1000);
    setTimeout(() => {
      if (id !== scanId) return;
      scan.className = "screen active cleared";
      $("#scan .status span").textContent = t.stamp;
      $("#scan .printing").textContent = C.PRINT ? t.printing : t.noprint;
      chime();
      if (C.PRINT && early === null) setTimeout(printLabel, 600);
      resultTimer = setTimeout(reset, C.RESULT_SCREEN_S * 1000);
    }, C.SCAN_S * 1000);
  }

  // --- Numéro de passage (conservé sur la borne) ---
  function nextCount() {
    let n = 0;
    try { n = +localStorage.getItem("bip3-count") || 0; localStorage.setItem("bip3-count", ++n); }
    catch { n = Math.floor(Math.random() * 9000) + 1; }
    return n;
  }

  // Faux code-barres façon carte d'embarquement, propre à chaque passage.
  function barcode(canvas, seed) {
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#000";
    let x = 0, s = seed * 9301 + 49297;
    const rnd = () => (s = (s * 9301 + 49297) % 233280) / 233280;
    while (x < canvas.width) {
      const w = 2 + Math.floor(rnd() * 3) * 2;
      ctx.fillRect(x, 0, w, canvas.height);
      x += w + 2 + Math.floor(rnd() * 3) * 2;
    }
  }

  // --- Sons (Web Audio, sans fichier) ---
  let audio;
  function ac() {
    if (!C.SOUND) return null;
    try { audio = audio || new AudioContext(); audio.resume(); return audio; } catch { return null; }
  }
  function beep(freq, dur, when = 0, type = "square", vol = 0.06) {
    const a = ac(); if (!a) return;
    const o = a.createOscillator(), g = a.createGain(), t0 = a.currentTime + when;
    o.type = type; o.frequency.value = freq;
    g.gain.setValueAtTime(vol, t0); g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    o.connect(g).connect(a.destination); o.start(t0); o.stop(t0 + dur + 0.02);
  }
  function hum(s) {
    const a = ac(); if (!a) return;
    const o = a.createOscillator(), g = a.createGain(), t0 = a.currentTime;
    o.type = "sawtooth"; o.frequency.value = 70;
    g.gain.setValueAtTime(0, t0); g.gain.linearRampToValueAtTime(0.03, t0 + 0.3);
    g.gain.setValueAtTime(0.03, t0 + s - 0.3); g.gain.linearRampToValueAtTime(0, t0 + s);
    o.connect(g).connect(a.destination); o.start(t0); o.stop(t0 + s + 0.05);
  }
  function chime() { beep(988, 0.18, 0, "sine", 0.15); beep(1319, 0.4, 0.16, "sine", 0.15); }
})();
