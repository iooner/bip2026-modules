# Module 2 · Des yeux derrière la tête (Miroir Miroir, BIP 2026)

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
`server.py` en extrait une image avec **ffmpeg**. Une caméra vide ou injoignable
est ignorée. Les 4 caméras (IP 192.168.1.172, .9, .180, .131) sont déjà dans `cameras.json`.

**Identifiants : jamais dans git.** Créer à côté, sur la borne, `module2/cameras.secret.json` (ignoré par git) :
```json
{ "user": "compte_camera", "password": "…" }
```
Ils s'appliquent à toutes les caméras dont `user` est vide dans `cameras.json`.
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

### Capture instantanée
`server.py` garde une connexion RTSP ouverte par caméra et décode en continu ; au clic, chaque caméra rend la
première image clé qui suit (moins d'1 s, les 4 en même temps), au lieu de 3 à 4 s par connexion. Coupure
réseau ou caméra débranchée : reconnexion automatique. Réglages optionnels dans `cameras.json` :
- `"decode": "all"` (défaut, borne = mini PC) : toutes les images sont décodées, `live_fps` (4) gardées par
  seconde ; la photo est prise moins de 0,3 s après le clic. `"key"` : images clés seules, très peu de CPU
  (machine faible type Raspberry Pi), mais la photo attend l'image clé suivante.
- `"snap_wait_s": 2` : attente max d'une image prise après le clic, sinon la plus récente.
- `"live": false` : ancien mode, une connexion par photo. `timeout_s` : délai max de ce mode.

### Présence des caméras
`server.py` sait à tout moment quelles caméras envoient des images (`GET /cameras`, vérifié toutes les 5 s par
la page). Deux caméras absentes ou plus : bandeau « pause technique » sur l'accueil. Une seule : pas de bandeau
(le tirage l'ignore), son numéro est écrit en petit en bas à droite de l'accueil. Seuil : `CAMERAS_DOWN_OK`.

### Qualité d'image
Le serveur garde les images clés de `stream1` en JPEG qualité max. Si l'image reste moyenne, c'est la
source : app Tapo > ⚙ > **Qualité vidéo** sur la plus haute (2K/3MP), éclairage suffisant (sinon la caméra passe
en vision nocturne noir et blanc granuleuse : mode nuit sur « jour » ou « auto » selon la lumière), objectif propre.

## Recadrage : `config.js`
`CROP` : pour chaque caméra, le centre (`x`, `y` de 0 à 1) et le `zoom`, à régler sur place pour que la personne
soit au centre. `LAYOUT: "quad"` pour la grille de 4. `DEMO: true` remplace une caméra muette par une image
de test (mettre `false` en expo pour afficher un message d'erreur à la place).

## Lancer
- Borne (mini PC) : installer **Python 3** et **ffmpeg** (Windows : `winget install Python.Python.3.12 Gyan.FFmpeg` ;
  Linux : `sudo apt install python3 ffmpeg`), puis l'autorun `kiosk\windows\install.bat module2` ou
  `./kiosk/linux/install.sh module2`.
- Raspberry Pi : `./kiosk/linux/setup-pi.sh module2` (le kiosk démarre `server.py` tout seul, voir [`kiosk/`](../kiosk/README.md)).
- Test sur un poste : `python3 server.py` puis ouvrir http://127.0.0.1:8360/.
  En ouvrant `index.html` directement (sans serveur), le mode démo affiche 4 images de test.

## Polices
Déposer dans `fonts/` : HelveticaNeueLTStd-Roman.otf, -It.otf, -Md.otf, -MdIt.otf (sinon repli Helvetica/Arial).
