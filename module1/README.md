# Module 1 · Le vrai test psychométrique (Miroir Miroir, BIP 2026)

App web statique, sans serveur ni dépendance : ouvrir `index.html`.

## Borne : Raspberry Pi 4
`./kiosk/linux/setup-pi.sh module1` (Chromium, CUPS, connexion automatique, autorun ; voir [`kiosk/`](../kiosk/README.md)).
L'étiquette part par le service d'impression silencieuse, sinon par `--kiosk-printing` (sans boîte de dialogue).
Imprimante hors service : bandeau « en panne » sur l'accueil.

## Réglages : `config.js`
Taille de l’étiquette (mm, 59×102), impression on/off, nombre de résultats tirés (4), retour à l'accueil sans
activité (`IDLE_TIMEOUT_S`, 60 s), durée de l'écran final (`RESULT_SCREEN_S`, 60 s : le temps de lire et que
l'étiquette sorte sur le Pi), curseur masqué (`HIDE_CURSOR`).

## Vue de réglage
Appui de 5 s sur le ✕ de l'accueil. « Redémarrer » et « Éteindre » arrêtent la borne proprement, par le service du
kiosk (`kiosk/print_server.py` : `systemctl reboot` / `poweroff`) : premier appui, le bouton passe à « Confirmer ? »,
second appui dans les 4 s pour valider. « Fermer » (ou Échap) pour sortir.

## Contenu
Source : `tools/BIP2026_testpersonnalite.xlsx`. Après modification du tableau :
`pip install openpyxl && python3 tools/build_content.py` (régénère `content.js`).
Corrections appliquées au tableau : EN 3c (traduit depuis le FR, la cellule contenait une phrase « œuvre »),
EN « Paula Murh » → Muhr, EN Q1 « firt » → first, FR « Dans Archives/ Présents » → « Dans la suite de l’exposition (****) ».

## Logique
8 questions × 4 réponses. À la fin : 4 questions tirées au hasard (distinctes), remises dans l'ordre du
tableau, avec la phrase résultat de la réponse choisie, puis une phrase « œuvre » (colonne E) au hasard.
Le texte est réduit automatiquement pour tenir sur l'étiquette. Bouton **Terminé / Done** : retour au choix de
la langue.

## Polices
Déposer dans `fonts/` : HelveticaNeueLTStd-Roman.otf, -It.otf, -Md.otf, -MdIt.otf (sinon repli Helvetica/Arial).
