// Étape « Passport hack », commune aux 4 modules (fichier identique dans chaque module).
// Juste après le choix de langue, on demande au visiteur s'il a son « Passport hack » :
//   Oui → le module continue comme avant (rappel passé à Passport.ask) ;
//   Non → on l'invite à passer à l'accueil, puis retour au choix de langue par le bouton ou après NO_BACK_S secondes.
// Sans réponse, la question elle-même se referme après ASK_IDLE_S secondes (retour au choix de langue).
// Le volet « Miroir Miroir » du passeport (assets/passport-hack.png, tiré du PDF) flotte, incliné, à droite.
// L'écran se pose par-dessus l'accueil, dans la scène 1024×768 (#stage) : il suit sa mise à l'échelle.
//   Passport.ask(lang, next)   affiche la question dans la langue choisie ; next() si « Oui »
//   Passport.close()           referme l'écran (retour au choix de langue)
window.Passport = (() => {
  const NO_BACK_S = 10, ASK_IDLE_S = 30;
  const TEXT = {
    fr: { q: "Avez-vous votre<br>«&nbsp;Passport hack&nbsp;»&nbsp;?", yes: "Oui", no: "Non",
          info: "Pour participer, rendez-vous d’abord à l’accueil pour obtenir votre «&nbsp;Passport&nbsp;hack&nbsp;».",
          back: "Retour", auto: s => `Retour automatique dans ${s}&nbsp;s` },
    en: { q: "Do you have your<br>“Passport hack”?", yes: "Yes", no: "No",
          info: "To take part, please go to the reception desk first to get your “Passport&nbsp;hack”.",
          back: "Back", auto: s => `Back automatically in ${s}&nbsp;s` },
  };
  let box, next, timer, tick;

  function build() {
    box = document.createElement("section");
    box.id = "passport"; box.hidden = true;
    box.innerHTML = `<div class="pass"><img src="assets/passport-hack.png" alt="Passport hack"></div>
      <div class="ask"><h2 class="q"></h2><div class="btns"><button class="yes"></button><button class="no"></button></div></div>
      <div class="nope"><h2 class="info"></h2><button class="back"></button><p class="auto"></p></div>`;
    (document.querySelector("#stage") || document.body).appendChild(box);
    box.querySelector(".yes").addEventListener("click", () => { const f = next; close(); if (f) f(); });
    box.querySelector(".no").addEventListener("click", refuse);
    box.querySelector(".back").addEventListener("click", close);
  }

  function stop() { clearTimeout(timer); clearInterval(tick); }

  function ask(lang, then) {
    if (!box) build();
    stop();
    const t = TEXT[lang] || TEXT.fr;
    next = then;
    box.querySelector(".q").innerHTML = t.q;
    box.querySelector(".yes").textContent = t.yes;
    box.querySelector(".no").textContent = t.no;
    box.querySelector(".info").innerHTML = t.info;
    box.querySelector(".back").textContent = t.back;
    box.t = t;
    box.className = "ask"; box.hidden = false;
    timer = setTimeout(close, ASK_IDLE_S * 1000);
  }

  // « Non » : invitation à passer à l'accueil, compte à rebours avant le retour au choix de langue
  function refuse() {
    stop();
    let s = NO_BACK_S;
    const auto = box.querySelector(".auto"), draw = () => { auto.innerHTML = box.t.auto(s); };
    box.className = "nope"; draw();
    tick = setInterval(() => { if (--s <= 0) close(); else draw(); }, 1000);
  }

  function close() {
    stop(); next = null;
    if (box) box.hidden = true;
  }

  return { ask, close };
})();
