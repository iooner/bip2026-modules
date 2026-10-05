(() => {
  const C = window.CONFIG, T = window.Tracker, S = window.Signature;
  const UI = {
    fr: { stepPlace: "Signature corporelle", placeTitle: "Place-toi sur la croix au sol",
          placeText: "Quand tu es en place, un décompte démarre : tu auras " + C.RECORD_S +
            " secondes pour bouger. Tes mains, tes pieds et ta tête vont dessiner ta signature.",
          wait: "On te cherche…", hold: "Ne bouge plus…", go: "Je suis prêt·e",
          ready: ["Prêt·e ?", "Bouge !"], move: "Bouge ! Danse, écarte les bras, saute…",
          resultTitle: "Ta signature corporelle", again: "Recommencer", restart: "Recommencer", no: "N°",
          printing: "Ton étiquette s’imprime. Colle-la dans ton passeport !",
          noprint: "Voici ta signature !", label: "Signature corporelle",
          line: d => `Tes mains ont parcouru ${d} m.` },
    en: { stepPlace: "Body signature", placeTitle: "Stand on the cross on the floor",
          placeText: "Once you are in place, a countdown starts: you will have " + C.RECORD_S +
            " seconds to move. Your hands, feet and head will draw your signature.",
          wait: "Looking for you…", hold: "Hold still…", go: "I’m ready",
          ready: ["Ready?", "Move!"], move: "Move! Dance, spread your arms, jump…",
          resultTitle: "Your body signature", again: "Start again", restart: "Start again", no: "No.",
          printing: "Your label is printing. Stick it in your passport!",
          noprint: "Here is your signature!", label: "Body signature",
          line: d => `Your hands travelled ${d} m.` },
  };
  const $ = (s, el = document) => el.querySelector(s);
  const stage = $("#stage");
  let lang = "fr", phase = "welcome", idleTimer, resultTimer, holdSince = 0, t0 = 0, tracks;

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
  document.querySelectorAll(".restart, .again").forEach(b => b.addEventListener("click", reset));
  $("#place .go").addEventListener("click", startCountdown);

  // Le corps est-il centré sur la croix ?
  function onCross(body) {
    return body && Math.abs(body.center[0] - 0.5) < C.CROSS_TOLERANCE;
  }

  // --- Boucle principale ---
  const live = $("#place .live").getContext("2d");
  const draw = $("#record .draw").getContext("2d");
  const skel = $("#record .skel").getContext("2d");
  function loop(now) {
    const body = T.get();
    if (phase === "place") {
      const ok = onCross(body);
      T.drawSkeleton(live, body, ok ? "#fff" : "rgba(255,255,255,.5)", 7);
      if (ok && !holdSince) holdSince = now;
      if (!ok) holdSince = 0;
      const p = holdSince ? Math.min(1, (now - holdSince) / (C.READY_HOLD_S * 1000)) : 0;
      $("#place .hold i").style.width = p * 100 + "%";
      $("#place .status").textContent = ok ? UI[lang].hold : UI[lang].wait;
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
        $("#record .count").textContent = Math.ceil(C.RECORD_S - r);
        $("#record .hint").textContent = r < 1.2 ? UI[lang].ready[1] : UI[lang].move;
        $("#record .bar i").style.width = (r / C.RECORD_S) * 100 + "%";
        S.render(draw, tracks, { color: "#fff", width: 14, fit: false });
      } else finish();
      T.drawSkeleton(skel, body, "#deb6b4", 3);
    }
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);

  function startCountdown() {
    if (phase !== "place") return;
    tracks = S.create(); t0 = performance.now();
    draw.clearRect(0, 0, 1024, 768);
    $("#record .bar i").style.width = "0";
    show("record"); poke();
  }

  // --- Résultat + étiquette ---
  function finish() {
    const t = UI[lang];
    const n = (parseInt(localStorage.getItem("bip2026-m4-count") || "0", 10) + 1);
    try { localStorage.setItem("bip2026-m4-count", n); } catch {}
    const d = new Date(), date = [d.getDate(), d.getMonth() + 1].map(v => String(v).padStart(2, "0")).join(".") + "." + d.getFullYear();
    // Champ horizontal Kinect v1 ≈ 2,7 m à 2,5 m de distance
    const meters = (S.handTravel(tracks) * 2.7).toFixed(1).replace(".", lang === "fr" ? "," : ".");
    const meta = `${t.no} ${String(n).padStart(4, "0")} · ${date}`;

    S.render($("#result .sig").getContext("2d"), tracks, { color: "#fff", width: 10 });
    $("#result .meta").textContent = t.line(meters) + "  " + meta;
    $("#result .printing").textContent = C.PRINT ? t.printing : t.noprint;

    // Signature de l'étiquette : canvas ~300 dpi (53 × 70 mm), encre noire
    const lc = document.createElement("canvas");
    lc.width = 626; lc.height = 830;
    S.render(lc.getContext("2d"), tracks, { color: "#000", width: 12, pad: 0.04 });
    $(".l-title").textContent = t.label;
    $(".l-line").textContent = t.line(meters);
    $(".l-meta").textContent = meta;
    const img = $(".l-sig");
    img.onload = () => { if (C.PRINT) setTimeout(() => window.print(), 300); };
    img.src = lc.toDataURL("image/png");

    show("result");
    clearTimeout(idleTimer);
    resultTimer = setTimeout(reset, C.RESULT_SCREEN_S * 1000);
  }
})();
