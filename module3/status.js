// Bandeau « en panne », commun aux 4 modules (fichier identique dans chaque module).
// Quand quelque chose empêche le module de fonctionner (imprimante, capteur, caméra…), l'écran d'accueil est
// grisé et barré d'un bandeau qui invite à prévenir l'équipe ; le détail technique est écrit en petit.
// Le bandeau n'apparaît que sur l'accueil (on n'interrompt pas un visiteur) et disparaît dès que tout remarche.
//   KioskStatus.report("code", "détail")   signale un problème propre au module
//   KioskStatus.clear("code")              le lève
//   KioskStatus.warn("code", "détail")     souci mineur, sans bandeau : écrit en petit en bas de l'accueil
//   KioskStatus.unwarn("code")             l'efface
// L'état de l'impression vient du service du kiosk (kiosk/print_server.py, GET /status).
// Essai : ajouter ?panne=un+texte à l'adresse de la page.
(() => {
  const C = window.CONFIG || {};
  const URL_ = C.STATUS_URL === undefined ? "http://127.0.0.1:8361/status" : C.STATUS_URL;
  const local = new Map();          // problèmes signalés par le module
  const warns = new Map();          // soucis mineurs (pas de bandeau)
  let remote = [], seen = false, misses = 0, box, line;

  function build() {
    box = document.createElement("div");
    box.id = "outage"; box.hidden = true;
    box.innerHTML = `<div class="band"><p class="big">Oups, petite pause technique&nbsp;!</p>
      <p>Demande à une personne de l’expo de venir me dépanner, je reviens vite.</p>
      <p class="en">Oops, short technical break! Please ask a member of the exhibition team to come and fix me.</p></div>
      <p class="why"></p>`;
    document.body.appendChild(box);
    line = document.createElement("p");
    line.id = "kiosk-warn"; line.hidden = true;
    line.style.cssText = "position:fixed;right:12px;bottom:8px;margin:0;z-index:40;font:12px/1.3 monospace;" +
      "color:#231f40;background:rgba(255,255,255,.75);padding:3px 6px;pointer-events:none";
    document.body.appendChild(line);
  }

  function refresh() {
    if (!box) return;
    const all = [...local].map(([code, detail]) => ({ code, detail })).concat(remote);
    const home = document.querySelector("#welcome.active");
    box.hidden = !(all.length && home);
    box.querySelector(".why").textContent = all.map(p => `${p.code} : ${p.detail}`).join("  |  ");
    line.textContent = [...warns].map(([code, detail]) => `${code} : ${detail}`).join("  |  ");
    line.hidden = !(warns.size && home && box.hidden);
  }

  async function poll() {
    if (!URL_) return;
    try {
      const r = await fetch(URL_, { cache: "no-store" });
      const s = await r.json();
      seen = true; misses = 0; remote = s.problems || [];
    } catch {
      // Service absent depuis le début (Windows, essai sur un PC) : pas une panne. Disparu en route : si.
      remote = seen && ++misses >= 2 ? [{ code: "service", detail: "service d'impression du kiosk injoignable" }] : [];
    }
    refresh();
  }

  window.KioskStatus = {
    report(code, detail) { local.set(code, detail); refresh(); },
    clear(code) { if (local.delete(code)) refresh(); },
    warn(code, detail) { warns.set(code, detail); refresh(); },
    unwarn(code) { if (warns.delete(code)) refresh(); },
  };
  addEventListener("DOMContentLoaded", () => {
    build();
    const forced = new URLSearchParams(location.search).get("panne");
    if (forced) local.set("essai", forced);
    poll(); setInterval(poll, 2000);
    // L'écran actif change sans prévenir : on suit la classe « active » de l'accueil
    const home = document.querySelector("#welcome");
    if (home) new MutationObserver(refresh).observe(home, { attributes: true, attributeFilter: ["class"] });
    refresh();
  });
})();
