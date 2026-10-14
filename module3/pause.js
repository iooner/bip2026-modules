// Mode « pause vernissage », commun aux 4 modules (fichier identique dans chaque module).
// Un écran plein, dans la charte, recouvre la borne et invite à revenir à l'ouverture.
// Par défaut : en pause toute la journée du vernissage (DAY, heure locale de la borne), hors pause les autres jours.
// Le bouton [data-pause] de la vue de réglage force l'inverse pour la journée en cours : ce choix est gardé dans le
// navigateur (localStorage), survit à un rechargement ou à un redémarrage, et s'efface au changement de jour.
// L'écran est sous la vue de réglage : l'appui de 5 s sur le ✕ de l'accueil reste possible à travers lui.
//   Pause.on   vrai quand la borne est en pause (un module peut s'en servir pour ignorer ses capteurs)
window.Pause = (() => {
  const KEY = "bip2026-pause-vernissage", DAY = "2026-10-17";
  let on = false, box;
  const today = () => { const d = new Date(), p = n => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; };

  // Choix fait à la main aujourd'hui, sinon l'état par défaut du jour
  function load() {
    let saved = null;
    try { const s = JSON.parse(localStorage.getItem(KEY)); if (s && s.day === today()) saved = s.on; } catch {}
    const v = saved === null ? today() === DAY : saved;
    if (v !== on) { on = v; render(); }
  }

  function build() {
    box = document.createElement("div");
    box.id = "pause"; box.hidden = true;
    box.innerHTML = `<img src="assets/miroir-blanc.png" alt="Miroir Miroir">
      <p class="big">Pour obtenir votre «&nbsp;passeport hack&nbsp;», revenez dès le 18&nbsp;octobre.<br>À&nbsp;demain ou à très bientôt&nbsp;!</p>
      <p class="en">To get your “Passeport hack”, come back on 18&nbsp;October.<br>See you tomorrow, or very soon!</p>`;
    document.body.appendChild(box);
  }

  function render() {
    if (box) box.hidden = !on;
    document.querySelectorAll("[data-pause]").forEach(b => {
      b.textContent = on ? "Reprendre (fin du vernissage)" : "Pause vernissage";
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
  addEventListener("DOMContentLoaded", () => { build(); render(); setInterval(load, 30000); });   // suit le passage à minuit
  return { get on() { return on; }, set };
})();
