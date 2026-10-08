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
| `server.py` | petit serveur local (Python 3 + ffmpeg pour le RTSP) : sert l'app et relaie `/snap/1…4` vers les caméras |

Le navigateur ne peut pas lire directement une caméra IP (CORS, mot de passe) : `server.py` fait le relais
sur `http://127.0.0.1:8360/`. Il refuse de servir `cameras.json`.

## Caméras : `cameras.json`
Caméras retenues : **Tapo C110**. Elles n'ont pas d'URL snapshot HTTP, seulement un flux RTSP :
`server.py` en extrait une image avec **ffmpeg** (installé par `setup-pi.sh`). Une caméra vide ou injoignable
est ignorée. Par caméra :
```json
{ "url": "rtsp://192.168.1.101:554/stream1", "user": "compte_camera", "password": "…" }
```
`stream1` = pleine résolution, `stream2` = basse résolution. `user` / `password` = le **compte caméra** créé dans
l'app Tapo (pas le compte Tapo/TP-Link). Une URL `http://…` (caméra avec snapshot JPEG) marche aussi.
Prévoir une IP fixe par caméra (réservation DHCP dans la box/le routeur).

### Tester une caméra
1. App Tapo > caméra > ⚙ Paramètres > Paramètres avancés > **Compte de la caméra** : créer identifiant + mot de passe.
2. App Tapo > ⚙ > Infos sur l'appareil : noter l'**adresse IP**.
3. Sur un ordinateur du même réseau, VLC > Média > Ouvrir un flux réseau :
   `rtsp://identifiant:motdepasse@IP:554/stream1`. L'image doit s'afficher.
4. Avec ffmpeg : `ffmpeg -rtsp_transport tcp -i "rtsp://identifiant:motdepasse@IP:554/stream1" -frames:v 1 test.jpg`
5. Remplir `cameras.json`, lancer `python3 server.py`, ouvrir http://127.0.0.1:8360/snap/1 (image de la caméra 1),
   puis http://127.0.0.1:8360/ pour le parcours complet. Les erreurs s'affichent dans le terminal du serveur.

Une prise de vue RTSP prend 2 à 3 s (connexion au flux). `timeout_s` : délai max par caméra.

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
