(() => {
  const C = window.CONFIG, DATA = window.CONTENT;
  const UI = {
    fr: { count: (i, n) => `Question ${i} / ${n}`, title: "Ton portrait",
          printing: "Ton étiquette s’imprime. Colle-la dans ton passeport !",
          noprint: "Note ton portrait dans ton passeport !",
          again: "Recommencer", label: "Le vrai test psychométrique" },
    en: { count: (i, n) => `Question ${i} / ${n}`, title: "Your portrait",
          printing: "Your label is printing. Stick it in your passport!",
          noprint: "Keep your portrait in mind!",
          again: "Start again", label: "The Real Psychometric Test" },
  };
  const $ = (s, el = document) => el.querySelector(s);
  const stage = $("#stage");
  let lang = "fr", step = 0, picks = [], busy = false, idleTimer, resultTimer;

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
    busy = false; show("welcome");
  }

  // --- Accueil ---
  document.querySelectorAll(".lang").forEach(b => b.addEventListener("click", () => {
    lang = b.dataset.lang; step = 0; picks = [];
    document.documentElement.lang = lang;
    renderQuestion(); show("question"); poke();
  }));
  $(".restart").addEventListener("click", reset);
  $(".again").addEventListener("click", reset);

  // --- Questions ---
  function renderQuestion() {
    const qs = DATA[lang].questions, q = qs[step];
    $("#question .count").textContent = UI[lang].count(step + 1, qs.length);
    $(".restart").setAttribute("aria-label", UI[lang].again);
    $("#question .dots").innerHTML = qs.map((_, i) => `<i class="${i <= step ? "on" : ""}"></i>`).join("");
    $("#question .q").textContent = q.q;
    const box = $("#question .answers");
    box.innerHTML = "";
    q.answers.forEach((a, i) => {
      const b = document.createElement("button");
      b.className = "answer";
      b.innerHTML = `<b>${"ABCD"[i]}</b><span></span>`;
      b.lastChild.textContent = a.label;
      b.addEventListener("click", () => choose(i, b));
      box.appendChild(b);
    });
    busy = false;
  }

  function choose(i, btn) {
    if (busy) return;
    busy = true; btn.classList.add("picked");
    picks[step] = i;
    setTimeout(() => {
      if (++step < DATA[lang].questions.length) renderQuestion();
      else finish();
    }, 350);
  }

  // --- Tirage : PICK_COUNT questions distinctes, gardées dans l'ordre du tableau ---
  function compose() {
    const d = DATA[lang], idx = d.questions.map((_, i) => i);
    for (let i = idx.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1)); [idx[i], idx[j]] = [idx[j], idx[i]];
    }
    const chosen = idx.slice(0, C.PICK_COUNT).sort((a, b) => a - b);
    return {
      sentences: chosen.map(q => d.questions[q].answers[picks[q]].result),
      artwork: d.artworks[Math.floor(Math.random() * d.artworks.length)],
      keys: chosen.map(q => `${q + 1}-${"abcd"[picks[q]]}`),
    };
  }

  function fillText(el, r) {
    el.textContent = r.sentences.join(" ") + " ";
    const s = document.createElement("span");
    s.className = "artwork"; s.textContent = r.artwork;
    el.appendChild(s);
  }

  // Réduit la police jusqu'à ce que le texte tienne dans son cadre.
  function shrinkToFit(text, box, startPx, minPx) {
    let px = startPx;
    text.style.fontSize = px + "px";
    while (px > minPx && text.scrollHeight > box.clientHeight) {
      px -= 0.25; text.style.fontSize = px + "px";
    }
  }

  function finish() {
    const r = compose(), t = UI[lang];
    console.log("Résultat", r.keys.join(", "));
    $("#result .title").textContent = t.title;
    $("#result .again").textContent = t.again;
    $("#result .printing").textContent = C.PRINT ? t.printing : t.noprint;
    fillText($("#result .text"), r);
    $(".l-title").textContent = t.label;
    fillText($(".l-text"), r);
    show("result");
    requestAnimationFrame(() => {
      shrinkToFit($("#result .text"), $("#result .textbox"), 26, 14);
      shrinkToFit($(".l-text"), $(".l-body"), 16, 6);   // 16px ≈ 12pt
      if (C.PRINT) setTimeout(() => window.print(), 400);
    });
    clearTimeout(idleTimer);
    resultTimer = setTimeout(reset, C.RESULT_SCREEN_S * 1000);
  }
})();
