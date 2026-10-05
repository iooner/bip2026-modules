# Module 2 · 360° (Miroir Miroir, BIP 2026)

Écran tactile FR/EN. Page 2 : bouton « Prendre une photo ». Compte à rebours, puis les 4 caméras IP
cachées sont appelées en même temps ; l'étiquette (Dymo 59×102 mm) imprime **1 image tirée au hasard**
ou, en option, **les 4 recadrées en grille 2×2**.

## Fichiers
| Fichier | Rôle |
|---|---|
| `index.html`, `app.js`, `style.css` | l'app (même charte et scène 1024×768 que le module 1) |
| `config.js` | réglages : mise en page `random` / `quad`, recadrage par caméra, compte à rebours, étiquette, mode démo |
| `cameras.json` | adresses snapshot des 4 caméras + identifiants (**à remplir**) |
| `server.py` | petit serveur local (Python 3, sans dépendance) : sert l'app et relaie `/snap/1…4` vers les caméras |

Le navigateur ne peut pas lire directement une caméra IP (CORS, mot de passe) : `server.py` fait le relais
sur `http://127.0.0.1:8360/`. Il refuse de servir `cameras.json`.

## Caméras : `cameras.json`
Pour chaque caméra, l'URL HTTP qui renvoie une image JPEG fixe (« snapshot »), p. ex. selon la marque :
`http://192.168.1.101/cgi-bin/snapshot.cgi` (Dahua), `http://…/ISAPI/Streaming/channels/101/picture` (Hikvision),
`http://…/snapshot.jpg`. Authentification Basic ou Digest gérée (`user` / `password`). Vérifier d'abord dans
un navigateur que l'URL affiche bien une image. Une caméra vide ou injoignable est ignorée.

## Recadrage : `config.js`
`CROP` : pour chaque caméra, le centre (`x`, `y` de 0 à 1) et le `zoom`, à régler sur place pour que la personne
soit au centre. `LAYOUT: "quad"` pour la grille de 4. `DEMO: true` remplace une caméra muette par une image
de test (mettre `false` en expo pour afficher un message d'erreur à la place).

## Lancer
- Borne : `./kiosk/linux/setup-pi.sh module2` (le kiosk démarre `server.py` tout seul, voir [`kiosk/`](../kiosk/README.md)).
- Test sur un poste : `python3 server.py` puis ouvrir http://127.0.0.1:8360/.
  En ouvrant `index.html` directement (sans serveur), le mode démo affiche 4 images de test.

## Polices
Déposer dans `fonts/` : HelveticaNeueLTStd-Roman.otf, -It.otf, -Md.otf, -MdIt.otf (sinon repli Helvetica/Arial).
