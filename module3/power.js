// Boutons « Redémarrer » / « Éteindre » de la vue de réglage (#debug [data-power]) : arrêt propre de la borne.
// Deux appuis : le premier arme le bouton (« Confirmer ? »), le second, dans les 4 s, confirme.
// La demande part au service du kiosk (kiosk/print_server.py, Linux), puis aux adresses suivantes de
// CONFIG.POWER_URLS si elle n'aboutit pas (module 4 sous Windows : pont Kinect).
window.Power = (() => {
  const URLS = (window.CONFIG || {}).POWER_URLS || ["http://127.0.0.1:8361/power/"];
  let armed = null, timer;
  const disarm = () => {
    clearTimeout(timer);
    if (armed) { armed.textContent = armed.dataset.label; armed.classList.remove("armed"); }
    armed = null;
  };
  document.addEventListener("click", async e => {
    const b = e.target.closest("[data-power]"), msg = document.querySelector("#debug .msg");
    if (!b || b !== armed) disarm();
    if (!b) return;
    if (!armed) {
      armed = b; b.dataset.label = b.textContent; b.textContent = "Confirmer ?"; b.classList.add("armed");
      timer = setTimeout(disarm, 4000);
      return;
    }
    disarm();
    msg.textContent = "…";
    let last = "Service du kiosk injoignable : arrêt impossible.";
    for (const url of URLS) {
      try {
        const r = await fetch(url + b.dataset.power, { method: "POST" });
        if (r.ok) { msg.textContent = b.dataset.power === "reboot" ? "Redémarrage en cours…" : "Extinction en cours…"; return; }
        last = `Refusé (HTTP ${r.status})`;
      } catch (err) { /* adresse suivante */ }
    }
    msg.textContent = last;
  });
  return { disarm };
})();
