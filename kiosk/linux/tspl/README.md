# Imprimante d'étiquettes LW650XL PRO (TSPL) sous Linux

La LW650XL PRO (USB `2e3c:5757`, vendue comme compatible Dymo) parle TSPL et n'a pas de pilote Linux fiable.
Ce dossier contient un pilote CUPS minimal : `rastertotspl-bip` (filtre Python, sans dépendance) et `tspl-label.ppd`.

Réglé pour les étiquettes 59 × 102 mm, qui défilent **en paysage** dans la machine, en 300 dpi.
La page portrait envoyée par les modules est pivotée de 90°, tramée (Floyd-Steinberg) et éclaircie
(le thermique noircit beaucoup). Réglages en tête du filtre : `OFFSET_X`, `OFFSET_Y` (calage), `GAMMA`.

## Installation
```bash
sudo usermod -aG lpadmin,lp "$USER"
sudo install -o root -g root -m 755 rastertotspl-bip /usr/lib/cups/filter/
lpstat -v                      # repérer l'URI usb://… de l'imprimante
sudo lpadmin -p LW650XL-PRO -E -v 'usb://…' -P tspl-label.ppd -o printer-error-policy=retry-job
sudo lpadmin -d LW650XL-PRO    # imprimante par défaut (impression directe du kiosk)
```
Après une modification du filtre, relancer la commande `install`.

## Session GNOME en kiosk
`../gnome-no-overview/` : mini-extension GNOME Shell qui ouvre la session sur le bureau au lieu de la vue
« Activités » (sinon le kiosk n'est pas en plein écran au démarrage).
```bash
mkdir -p ~/.local/share/gnome-shell/extensions/no-overview@bip2026
cp ../gnome-no-overview/* ~/.local/share/gnome-shell/extensions/no-overview@bip2026/
gsettings set org.gnome.shell enabled-extensions "['no-overview@bip2026']"
```
Connexion automatique : `AutomaticLoginEnable = true` et `AutomaticLogin = <utilisateur>` dans `/etc/gdm3/daemon.conf`.
