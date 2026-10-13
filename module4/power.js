// Boutons « Redémarrer » / « Éteindre » de la vue de réglage (#debug [data-power]) : arrêt propre de la borne.
// Deux appuis : le premier arme le bouton (« Confirmer ? »), le second, dans les 4 s, confirme.
// La demande part au service du kiosk (kiosk/print_server.py : systemctl reboot / poweroff).
window.Power = (() => {
  const URL_ = "http://127.0.0.1:8361/power/";
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
    try {
      const r = await fetch(URL_ + b.dataset.power, { method: "POST" });
      msg.textContent = r.ok ? (b.dataset.power === "reboot" ? "Redémarrage en cours…" : "Extinction en cours…") : `Refusé (HTTP ${r.status})`;
    } catch (err) { msg.textContent = "Service du kiosk injoignable : arrêt impossible."; }
  });
  return { disarm };
})();
