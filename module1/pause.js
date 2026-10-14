// Mode « pause vernissage », commun aux 4 modules (fichier identique dans chaque module).
// Activé depuis la vue de réglage (bouton [data-pause] dans #debug .bar) : un écran plein, dans la charte,
// recouvre la borne et invite à revenir à l'ouverture. L'état est gardé dans le navigateur (localStorage) :
// il survit à un rechargement ou à un redémarrage, et se lève depuis le même bouton.
// L'écran est sous la vue de réglage : l'appui de 5 s sur le ✕ de l'accueil reste possible à travers lui.
//   Pause.on   vrai quand la borne est en pause (un module peut s'en servir pour ignorer ses capteurs)
window.Pause = (() => {
  const KEY = "bip2026-pause-vernissage";
  let on = false, box;
  try { on = localStorage.getItem(KEY) === "1"; } catch {}

  function build() {
    box = document.createElement("div");
    box.id = "pause"; box.hidden = true;
    box.innerHTML = `<img src="assets/miroir-blanc.png" alt="Miroir Miroir">
      <p class="big">Pour obtenir votre «&nbsp;passeport hack&nbsp;», revenez dès le 18&nbsp;octobre. À&nbsp;demain ou à très bientôt&nbsp;!</p>
      <p class="en">To get your “Passeport hack”, come back on 18&nbsp;October. See you tomorrow, or very soon!</p>`;
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
    try { v ? localStorage.setItem(KEY, "1") : localStorage.removeItem(KEY); } catch {}
    render();
  }

  document.addEventListener("click", e => { if (e.target.closest("[data-pause]")) set(!on); });
  addEventListener("DOMContentLoaded", () => { build(); render(); });
  return { get on() { return on; }, set };
})();
