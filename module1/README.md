# Module 1 · Test de personnalité (Miroir Miroir, BIP 2026)

App web statique, sans serveur ni dépendance : ouvrir `index.html`.

## Borne (kiosk au démarrage)
```
chromium --kiosk --kiosk-printing --noerrdialogs --disable-pinch \
  --overscroll-history-navigation=0 file:///chemin/module1/index.html
```
`--kiosk-printing` imprime sans boîte de dialogue sur l'imprimante par défaut du système.

## Réglages : `config.js`
Taille de l’étiquette (mm, Dymo S0947420 59×102 sur LabelWriter 4XL/5XL), impression on/off, nombre de résultats tirés (4), veille, curseur.

## Contenu
Source : `tools/BIP2026_testpersonnalite.xlsx`. Après modification du tableau :
`pip install openpyxl && python3 tools/build_content.py` (régénère `content.js`).
Corrections appliquées au tableau : EN 3c (traduit depuis le FR, la cellule contenait une phrase « œuvre »),
EN « Paula Murh » → Muhr, EN Q1 « firt » → first, FR « Dans Archives/ Présents » → « Dans la suite de l’exposition (****) ».

## Logique
8 questions × 4 réponses. À la fin : 4 questions tirées au hasard (distinctes), remises dans l'ordre du
tableau, avec la phrase résultat de la réponse choisie, puis une phrase « œuvre » (colonne E) au hasard.
Le texte est réduit automatiquement pour tenir sur l'étiquette.

## Polices
Déposer dans `fonts/` : HelveticaNeueLTStd-Roman.otf, -It.otf, -Md.otf, -MdIt.otf (sinon repli Helvetica/Arial).
