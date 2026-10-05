(() => {
  const C = window.CONFIG;
  const UI = {
    fr: { hint: "Place-toi au centre\net prends ta plus belle pose !",
          take: "Prendre une photo", title: "Ton 360°",
          printing: "Ton étiquette s’imprime. Colle-la dans ton passeport !",
          noprint: "Voilà comment le miroir te voit.",
          error: "La photo n’a pas pu être prise. Réessaie dans un instant.",
          again: "Recommencer" },
    en: { hint: "Stand in the middle\nand strike your best pose!",
          take: "Take a photo", title: "Your 360°",
          printing: "Your label is printing. Stick it in your passport!",
          noprint: "This is how the mirror sees you.",
          error: "The photo could not be taken. Try again in a moment.",
          again: "Start again" },
  };
  const $ = (s, el = document) => el.querySelector(s);
  const stage = $("#stage");
  let lang = "fr", busy = false, idleTimer, resultTimer;

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
  const PW = W - 2 * M, PH = H - 2 * M - C.LABEL_HEAD_MM;   // zone photo en mm
  const pageStyle = document.createElement("style");
  pageStyle.textContent = `@page { size: ${W}mm ${H}mm; margin: 0; }
    #label { width: ${W}mm; height: ${H}mm; padding: ${M}mm; }
    #label .l-head { height: ${C.LABEL_HEAD_MM}mm; }
    #label .l-photo { width: ${PW}mm; height: ${PH}mm; filter: ${C.LABEL_FILTER}; }`;
  document.head.appendChild(pageStyle);

  function show(id) {
    document.querySelectorAll(".screen").forEach(s => s.classList.toggle("active", s.id === id));
  }

  // --- Veille : retour à l'accueil ---
  function poke() {
    clearTimeout(idleTimer);
    if (!$("#welcome").classList.contains("active"))
      idleTimer = setTimeout(reset, C.IDLE_TIMEOUT_S * 1000);
  }
  addEventListener("pointerdown", poke, true);

  function reset() {
    clearTimeout(idleTimer); clearTimeout(resultTimer);
    busy = false; $("#shoot").classList.remove("counting");
    show("welcome");
  }

  // --- Accueil ---
  document.querySelectorAll(".lang").forEach(b => b.addEventListener("click", () => {
    lang = b.dataset.lang;
    document.documentElement.lang = lang;
    const t = UI[lang];
    $("#shoot .hint").textContent = t.hint;
    $("#shoot .take").textContent = t.take;
    show("shoot"); poke();
  }));
  $(".restart").addEventListener("click", reset);
  $(".again").addEventListener("click", reset);

  // --- Prise de vue ---
  $(".take").addEventListener("click", async () => {
    if (busy) return;
    busy = true;
    const shoot = $("#shoot"), cd = $("#shoot .countdown");
    shoot.classList.add("counting");
    for (let n = C.COUNTDOWN_S; n > 0; n--) {
      cd.textContent = n;
      await wait(1000);
      if (!busy) return;            // retour à l'accueil pendant le décompte
    }
    cd.textContent = "";
    shoot.classList.add("flashing");
    const shots = await grabAll();
    shoot.classList.remove("flashing", "counting");
    if (!busy) return;
    finish(shots);
  });

  const wait = ms => new Promise(r => setTimeout(r, ms));

  // Les 4 snapshots en parallèle ; null pour une caméra qui ne répond pas.
  function grabAll() {
    return Promise.all(Array.from({ length: C.CAMERA_COUNT }, (_, i) => grab(i + 1)
      .catch(err => {
        console.warn(`Caméra ${i + 1} :`, err.message);
        return C.DEMO ? demoImage(i + 1) : null;
      })));
  }

  async function grab(n) {
    const r = await fetch(`${C.SNAPSHOT_URL}${n}?t=${Date.now()}`, { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return createImageBitmap(await r.blob());
  }

  // Image de test (sans caméra) : dégradé de la charte + numéro.
  function demoImage(n) {
    const c = document.createElement("canvas"), x = c.getContext("2d");
    c.width = 1280; c.height = 720;
    const g = x.createLinearGradient(0, 0, 0, 720);
    g.addColorStop(0, "#98758b"); g.addColorStop(1, "#deb6b4");
    x.fillStyle = g; x.fillRect(0, 0, 1280, 720);
    x.fillStyle = "#231f40";
    x.beginPath(); x.arc(640, 300, 90, 0, 7); x.fill();          // silhouette
    x.fillRect(560, 400, 160, 320);
    x.fillStyle = "#fff"; x.font = "500 64px sans-serif"; x.textAlign = "center";
    x.fillText(`Caméra ${n}`, 640, 120);
    return c;
  }

  // --- Composition de l'image de l'étiquette ---
  const px = mm => Math.round(mm / 25.4 * C.LABEL_DPI);

  // Recadre img dans (dx, dy, dw, dh) autour du centre crop.x/y, avec crop.zoom.
  function drawCrop(ctx, img, crop, dx, dy, dw, dh) {
    const iw = img.width, ih = img.height, ar = dw / dh;
    let sw = iw, sh = iw / ar;
    if (sh > ih) { sh = ih; sw = ih * ar; }
    const z = Math.max(1, crop.zoom || 1);
    sw /= z; sh /= z;
    const sx = Math.min(Math.max(crop.x * iw - sw / 2, 0), iw - sw);
    const sy = Math.min(Math.max(crop.y * ih - sh / 2, 0), ih - sh);
    ctx.drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh);
  }

  function compose(shots) {
    const ok = shots.flatMap((s, i) => s ? [i] : []);
    if (!ok.length) return null;
    const c = document.createElement("canvas"), ctx = c.getContext("2d");
    c.width = px(PW); c.height = px(PH);
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, c.width, c.height);
    if (C.LAYOUT === "quad") {
      const gap = px(1), w = (c.width - gap) / 2, h = (c.height - gap) / 2;
      shots.forEach((s, i) => s && drawCrop(ctx, s, C.CROP[i], (i % 2) * (w + gap), Math.floor(i / 2) * (h + gap), w, h));
    } else {
      const i = ok[Math.floor(Math.random() * ok.length)];
      console.log("Caméra tirée :", i + 1);
      drawCrop(ctx, shots[i], C.CROP[i], 0, 0, c.width, c.height);
    }
    return c.toDataURL("image/jpeg", 0.92);
  }

  async function finish(shots) {
    const t = UI[lang], url = compose(shots);
    $("#result .title").textContent = t.title;
    $("#result .again").textContent = t.again;
    const photo = $("#result .photo"), lphoto = $(".l-photo");
    photo.hidden = !url;
    $("#result .printing").textContent = !url ? t.error : C.PRINT ? t.printing : t.noprint;
    if (url) {
      photo.src = lphoto.src = url;
      await Promise.all([photo.decode(), lphoto.decode()]).catch(() => {});
    }
    show("result");
    if (url && C.PRINT) setTimeout(() => window.print(), 400);
    clearTimeout(idleTimer);
    resultTimer = setTimeout(reset, C.RESULT_SCREEN_S * 1000);
  }
})();
