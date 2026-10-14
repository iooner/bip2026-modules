// Mode « pause vernissage », commun aux 4 modules (fichier identique dans chaque module).
// Un écran plein, dans la charte, recouvre la borne : le jour du vernissage, il invite à revenir à l'ouverture ;
// les autres jours (pause manuelle), il dit simplement que le module est en pause.
// Par défaut : en pause toute la journée du vernissage (DAY, heure locale de la borne), hors pause les autres jours.
// Le bouton [data-pause] de la vue de réglage force l'inverse pour la journée en cours : ce choix est gardé dans le
// navigateur (localStorage), survit à un rechargement ou à un redémarrage, et s'efface au changement de jour.
// L'écran est sous la vue de réglage : l'appui de 5 s sur le ✕ de l'accueil reste possible à travers lui (un rappel
// discret du ✕ est affiché à sa place).
//   Pause.on   vrai quand la borne est en pause (un module peut s'en servir pour ignorer ses capteurs)
window.Pause = (() => {
  const KEY = "bip2026-pause-vernissage", DAY = "2026-10-17";
  let on = false, box, shown;
  const today = () => { const d = new Date(), p = n => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; };

  // Choix fait à la main aujourd'hui, sinon l'état par défaut du jour
  function load() {
    let saved = null;
    try { const s = JSON.parse(localStorage.getItem(KEY)); if (s && s.day === today()) saved = s.on; } catch {}
    const v = saved === null ? today() === DAY : saved;
    if (v !== on || today() !== shown) { on = v; shown = today(); render(); }
  }

  // Texte du jour du vernissage, et texte d'une pause manuelle les autres jours
  const TEXT = {
    vernissage: ["Pour obtenir votre “Passport hack”, revenez dès le 18&nbsp;octobre.<br>À&nbsp;demain ou à très bientôt&nbsp;!",
                 "To get your “Passport hack”, come back on 18&nbsp;October.<br>See you tomorrow, or very soon!"],
    autre:      ["Ce module est actuellement en pause.<br>Désolé pour la gêne occasionnée.",
                 "This module is currently paused.<br>Sorry for the inconvenience."],
  };

  function build() {
    box = document.createElement("div");
    box.id = "pause"; box.hidden = true;
    box.innerHTML = `<div class="logo"><img src="assets/miroir-blanc.png" alt="Miroir Miroir"><i class="g1"></i><i class="g2"></i></div><span class="x" aria-hidden="true">✕</span>
      <p class="big"></p><p class="en"></p>`;
    document.body.appendChild(box);
  }

  // Le ✕ de l'accueil est sous l'écran de pause : on en montre un rappel discret à la même place
  function placeX() {
    const x = box && box.querySelector(".x"), b = document.querySelector("#welcome .xbox");
    if (!x) return;
    const r = b && b.getBoundingClientRect(), ok = r && r.width > 0;
    x.hidden = !ok;
    if (ok) Object.assign(x.style, { left: r.left + "px", top: r.top + "px", width: r.width + "px", height: r.height + "px",
                                     fontSize: r.height * .55 + "px" });
  }

  function render() {
    const day = today() === DAY;
    if (box) {
      box.hidden = !on;
      [box.querySelector(".big").innerHTML, box.querySelector(".en").innerHTML] = TEXT[day ? "vernissage" : "autre"];
    }
    if (on) placeX();
    document.querySelectorAll("[data-pause]").forEach(b => {
      b.textContent = on ? (day ? "Reprendre (fin du vernissage)" : "Reprendre") : (day ? "Pause vernissage" : "Mettre en pause");
      b.classList.toggle("on", on);
    });
  }

  function set(v) {
    on = !!v;
    try { localStorage.setItem(KEY, JSON.stringify({ day: today(), on })); } catch {}
    render();
  }

  document.addEventListener("click", e => { if (e.target.closest("[data-pause]")) set(!on); });
  load();
  addEventListener("DOMContentLoaded", () => { build(); render(); setInterval(load, 30000); });
  addEventListener("resize", () => on && placeX());   // suit le passage à minuit
  return { get on() { return on; }, set };
})();
