# BIP 2026 « Miroir Miroir » · modules interactifs

Biennale de l'Image Possible, Liège (17.10–13.12.2026). Un dossier par module, chacun est une app web
statique FR/EN lancée en kiosk sur sa borne (écran tactile Elo 1024×768), qui imprime une étiquette 59×102 mm.

| Dossier | Module (FR / EN) | Borne |
|---|---|---|
| [`module1/`](module1/README.md) | Le vrai test psychométrique / The Real Psychometric Test : 8 questions, 4 résultats imprimés | Raspberry Pi 4 |
| [`module2/`](module2/README.md) | Des yeux derrière la tête / Eyes behind your head : photo par 4 caméras IP cachées (Tapo C110) | mini PC Linux |
| [`module3/`](module3/README.md) | Vide ton sac : faux scanner d'aéroport (webcam au-dessus du bac, ou capteur GPIO + Pi Camera), rayons X, étiquette AUTORISÉ / CLEAR | mini PC Linux ou Raspberry Pi |
| [`module4/`](module4/README.md) | Re-Kinect-Toi : Kinect v1 + squelette MediaPipe, 10 s de mouvements tracés en signature | mini PC Linux (Core i5) |

Commun aux 4 modules ([`kiosk/`](kiosk/README.md)) :
- **Autorun** au démarrage (Chromium en kiosk, relancé s'il se ferme), mise à jour par `./kiosk/linux/update.sh`.
- **Impression silencieuse** : `kiosk/print_server.py` imprime l'étiquette sans aperçu à l'écran (PDF + CUPS).
- **Imprimante** LW650XL PRO (TSPL) avec son pilote CUPS : [`kiosk/linux/tspl/`](kiosk/linux/tspl/README.md).
- **Bandeau « en panne »** sur l'accueil quand l'imprimante ou le matériel du module ne répond plus.
- Bouton **Terminé / Done** sur l'écran final, curseur masqué (`HIDE_CURSOR`), crédit Liège Hackerspace sur l'accueil.
