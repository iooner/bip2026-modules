(() => {
  const C = window.CONFIG, T = window.Tracker, S = window.Signature;
  const UI = {
    fr: { stepPlace: "Signature corporelle", placeTitle: "Place-toi sur la croix au sol",
          placeText: "Quand tu es en place, un décompte démarre : tu auras " + C.RECORD_S +
            " secondes pour bouger. Tes mains et tes pieds vont dessiner ta signature.",
          wait: "En attente de positionnement…", hold: "Position OK, ne bouge plus…", go: "Je suis prêt·e", replay: "Tes mouvements",
          ready: ["Prêt·e ?", "Bouge !"], move: "Bouge ! Danse, écarte les bras, saute…",
          resultTitle: "Ta signature corporelle", done: "Terminé", restart: "Recommencer", no: "N°",
          printing: "Ton étiquette s’imprime. Colle-la dans ton passeport !",
          noprint: "Voici ta signature !", label: "Signature corporelle" },
    en: { stepPlace: "Body signature", placeTitle: "Stand on the cross on the floor",
          placeText: "Once you are in place, a countdown starts: you will have " + C.RECORD_S +
            " seconds to move. Your hands and feet will draw your signature.",
          wait: "Waiting for you to get in position…", hold: "In position, hold still…", go: "I’m ready", replay: "Your moves",
          ready: ["Ready?", "Move!"], move: "Move! Dance, spread your arms, jump…",
          resultTitle: "Your body signature", done: "Done", restart: "Start again", no: "No.",
          printing: "Your label is printing. Stick it in your passport!",
          noprint: "Here is your signature!", label: "Body signature" },
  };
  const $ = (s, el = document) => el.querySelector(s);
  const stage = $("#stage");
  let lang = "fr", phase = "welcome", idleTimer, resultTimer, holdSince = 0, t0 = 0, tracks, replay = [], replayAt = 0;

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

  function show(id) {
    phase = id;
    document.querySelectorAll(".screen").forEach(s => s.classList.toggle("active", s.id === id));
  }

  // --- Veille ---
  function poke() {
    clearTimeout(idleTimer);
    if (phase !== "welcome") idleTimer = setTimeout(reset, C.IDLE_TIMEOUT_S * 1000);
  }
  addEventListener("pointerdown", poke, true);

  function reset() {
    clearTimeout(idleTimer); clearTimeout(resultTimer);
    show("welcome");
  }

  // --- Accueil ---
  document.querySelectorAll(".lang").forEach(b => b.addEventListener("click", () => {
    lang = b.dataset.lang;
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-t]").forEach(el => { el.textContent = UI[lang][el.dataset.t]; });
    $(".restart").setAttribute("aria-label", UI[lang].restart);
    console.log("Source du corps :", T.sourceName());
    holdSince = 0; show("place"); poke();
  }));
  $(".restart").addEventListener("click", reset);
  $(".done").addEventListener("click", reset);   // « Terminé » : retour au choix de langue
  $("#place .go").addEventListener("click", startCountdown);

  // --- Maintenance : réapprendre le décor vide (appui long 3 s sur le ✕ de l'accueil, ou touche CONFIG.LEARN_KEY) ---
  let learning = false;
  function learnBackground() {
    if (learning || phase !== "welcome") return;
    const box = $("#learn"), D = C.LEARN_DELAY_S;
    box.hidden = false;
    if (!T.learn(D)) { box.textContent = "Pont Kinect absent."; return setTimeout(() => { box.hidden = true; }, 2500); }
    learning = true;
    const end = performance.now() + (D + 3) * 1000;   // + 2 s d'apprentissage, 1 s de marge
    (function tick() {
      const left = (end - performance.now()) / 1000;
      if (left <= 0) { box.hidden = true; learning = false; return; }
      box.textContent = left > 3 ? `Sortez du champ de la Kinect… ${Math.ceil(left - 3)}` : "Apprentissage du décor vide…";
      setTimeout(tick, 200);
    })();
  }
  let pressTimer;
  const hidden = $("#welcome .xbox");
  hidden.addEventListener("pointerdown", () => { pressTimer = setTimeout(learnBackground, 3000); });
  for (const e of ["pointerup", "pointerleave", "pointercancel"]) hidden.addEventListener(e, () => clearTimeout(pressTimer));
  addEventListener("keydown", e => { if (e.key === C.LEARN_KEY) { e.preventDefault(); learnBackground(); } });

  // Le corps est-il centré sur la croix ?
  function onCross(body) {
    return body && Math.abs(body.center[0] - 0.5) < C.CROSS_TOLERANCE;
  }

  // --- Boucle principale ---
  const live = $("#place .live").getContext("2d");
  const draw = $("#record .draw").getContext("2d");
  const skel = $("#record .skel").getContext("2d");
  const replayCtx = $("#result .replay").getContext("2d");
  const OK = getComputedStyle(document.documentElement).getPropertyValue("--ok").trim() || "#5fe08a";
  function loop(now) {
    const body = T.get();
    if (phase === "place") {
      const ok = onCross(body);
      T.drawSkeleton(live, body, ok ? OK : "rgba(255,255,255,.5)", 7);
      $("#place .mirror").classList.toggle("ok", !!ok);
      if (ok && !holdSince) holdSince = now;
      if (!ok) holdSince = 0;
      const p = holdSince ? Math.min(1, (now - holdSince) / (C.READY_HOLD_S * 1000)) : 0;
      $("#place .hold i").style.width = p * 100 + "%";
      $("#place .status").textContent = $("#place .pos").textContent = ok ? UI[lang].hold : UI[lang].wait;
      if (p >= 1) startCountdown();
    } else if (phase === "record") {
      const el = (now - t0) / 1000;
      if (el < C.GET_READY_S) {
        const n = Math.ceil(C.GET_READY_S - el);
        $("#record .count").textContent = n;
        $("#record .hint").textContent = UI[lang].ready[0];
      } else if (el < C.GET_READY_S + C.RECORD_S) {
        const r = el - C.GET_READY_S;
        S.add(tracks, body, now);
        if (body) replay.push([r, body.joints]);               // pour rejouer le bonhomme sur l'écran final
        $("#record .count").textContent = Math.ceil(C.RECORD_S - r);
        $("#record .hint").textContent = r < 1.2 ? UI[lang].ready[1] : UI[lang].move;
        $("#record .bar i").style.width = (r / C.RECORD_S) * 100 + "%";
        S.render(draw, tracks, { color: "#fff", width: 14, fit: false });
      } else finish();
      // Pendant le 3, 2, 1 : bonhomme vert si la personne est toujours bien placée
      T.drawSkeleton(skel, body, el < C.GET_READY_S && onCross(body) ? OK : "#deb6b4", 3);
    } else if (phase === "result" && replay.length) {
      // Replay en boucle du bonhomme, à vitesse réelle, avec une courte pause entre deux passages
      const t = ((now - replayAt) / 1000) % (C.RECORD_S + 1);
      let i = replay.findIndex(f => f[0] >= t);
      if (i < 0) i = replay.length - 1;
      T.drawSkeleton(replayCtx, { joints: replay[i][1] }, "#deb6b4", 4);
    }
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);

  function startCountdown() {
    if (phase !== "place") return;
    tracks = S.create(); replay = []; t0 = performance.now();
    draw.clearRect(0, 0, 1024, 768);
    $("#record .bar i").style.width = "0";
    show("record"); poke();
  }

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

  // --- Résultat + étiquette ---
  function finish() {
    const t = UI[lang];
    const n = (parseInt(localStorage.getItem("bip2026-m4-count") || "0", 10) + 1);
    try { localStorage.setItem("bip2026-m4-count", n); } catch {}
    const d = new Date(), date = [d.getDate(), d.getMonth() + 1].map(v => String(v).padStart(2, "0")).join(".") + "." + d.getFullYear();
    const meta = `${t.no} ${String(n).padStart(4, "0")} · ${date}`;

    S.render($("#result .sig").getContext("2d"), tracks, { color: "#fff", width: 10 });
    $("#result .meta").textContent = meta;
    $("#result .printing").textContent = C.PRINT ? t.printing : t.noprint;

    // Signature de l'étiquette : canvas ~300 dpi (53 × 70 mm), encre noire
    const lc = document.createElement("canvas");
    lc.width = 626; lc.height = 830;
    S.render(lc.getContext("2d"), tracks, { color: "#000", width: 12, pad: 0.04 });
    $(".l-title").textContent = t.label;
    $(".l-meta").textContent = meta;
    const img = $(".l-sig");
    img.onload = () => { if (C.PRINT) setTimeout(printLabel, 300); };
    img.src = lc.toDataURL("image/png");

    replayAt = performance.now(); T.sessionEnd();
    show("result");
    clearTimeout(idleTimer);
    resultTimer = setTimeout(reset, C.RESULT_SCREEN_S * 1000);
  }
})();
