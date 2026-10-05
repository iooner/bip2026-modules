(() => {
  const C = window.CONFIG;
  const SIM = C.SIMULATE || /[?&]sim=1/.test(location.search);
  const SAMPLES = ["assets/sample-1.svg", "assets/sample-2.svg", "assets/sample-3.svg"];
  const UI = {
    fr: { kicker: "Contrôle de sûreté", title: "Vide ton sac !",
          steps: ["Vide tes poches ou ton sac dans le bac.",
                  "Glisse le bac dans le scanner.",
                  "Attends le verdict à l’écran."],
          waiting: "Le scanner attend ton bac…", simulate: "Simuler un passage",
          scanning: "Analyse en cours…", clear: "Autorisé · Bonne visite !",
          printing: "Ton étiquette s’imprime : colle-la dans ton passeport. N’oublie pas tes affaires !",
          noprint: "N’oublie pas tes affaires !",
          label: "Vide ton sac", info: ["Passager", "Date", "Heure", "Porte"] },
    en: { kicker: "Security check", title: "Empty your bag!",
          steps: ["Empty your pockets or your bag into the tray.",
                  "Slide the tray into the scanner.",
                  "Wait for the verdict on screen."],
          waiting: "The scanner is waiting for your tray…", simulate: "Simulate a pass",
          scanning: "Scanning…", clear: "Cleared · Enjoy the show!",
          printing: "Your label is printing: stick it in your passport. Don’t forget your belongings!",
          noprint: "Don’t forget your belongings!",
          label: "Empty your bag", info: ["Passenger", "Date", "Time", "Gate"] },
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

  function show(id) {
    state = id;
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
  function renderSteps() {
    const t = UI[lang];
    $("#steps .kicker").textContent = t.kicker;
    $("#steps .title").textContent = t.title;
    $("#steps .list").innerHTML = t.steps.map((s, i) => `<li><b>${i + 1}</b><span>${s}</span></li>`).join("");
    $("#steps .waiting span").textContent = t.waiting;
    const sim = $("#steps .simulate");
    sim.textContent = t.simulate; sim.hidden = !SIM;
  }
  document.querySelectorAll(".lang").forEach(b => b.addEventListener("click", () => {
    lang = b.dataset.lang; document.documentElement.lang = lang;
    renderSteps(); show("steps");
  }));
  $(".restart").addEventListener("click", reset);
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
    es.addEventListener("open", () => { $("#offline").hidden = true; });
    es.addEventListener("error", () => { $("#offline").hidden = false; });
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
                  now.toLocaleDateString("fr-BE", { day: "2-digit", month: "2-digit", year: "numeric" }),
                  now.toLocaleTimeString("fr-BE", { hour: "2-digit", minute: "2-digit" }), "✕"];
    const dl = t.info.map((k, i) => `<dt>${k}</dt><dd>${info[i]}</dd>`).join("");
    $("#scan .kicker").textContent = t.kicker;
    $("#scan .info").innerHTML = dl;
    $("#scan .meta").textContent = `#${info[0]} · ${info[1]} ${info[2]}`;
    $("#scan .status span").textContent = t.scanning;
    $("#scan .stamp span").textContent = t.clear;
    $("#scan .printing").textContent = "";
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
    ctx.save();
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, cw, ch);
    ctx.translate(cw / 2, ch / 2);
    ctx.rotate(rot * Math.PI / 180);
    if (C.MIRROR) ctx.scale(-1, 1);
    ctx.filter = `url(#${filter})`;
    ctx.drawImage(img, sx, sy, sw, sh, -sw * k / 2, -sh * k / 2, sw * k, sh * k);
    ctx.restore();
    if (lines) {                              // fines lignes de balayage
      ctx.fillStyle = lines;
      for (let y = 0; y < ch; y += 4) ctx.fillRect(0, y, cw, 1);
    }
  }

  function runScan(img) {
    const id = scanId, t = UI[lang];
    render(img, $("#xray"), "f-xray", "rgba(255,255,255,.07)");
    render(img, $(".l-img"), "f-print", "rgba(255,255,255,.35)");
    const scan = $("#scan");
    scan.style.setProperty("--scan-s", C.SCAN_S + "s");
    scan.className = "screen active scanning";
    hum(C.SCAN_S);
    setTimeout(() => {
      if (id !== scanId) return;
      scan.className = "screen active cleared";
      $("#scan .status span").textContent = "CLEAR";
      $("#scan .printing").textContent = C.PRINT ? t.printing : t.noprint;
      chime();
      if (C.PRINT) setTimeout(() => window.print(), 600);
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
