// Réglages du module 2 (360°). Modifier ici, puis recharger la page.
// Les adresses des caméras sont dans cameras.json (lu par server.py, pas par le navigateur).
window.CONFIG = {
  // Étiquette Dymo S0947420 (LabelWriter 4XL/5XL) : 59 × 102 mm, portrait.
  LABEL_WIDTH_MM: 59,
  LABEL_HEIGHT_MM: 102,
  LABEL_MARGIN_MM: 3,
  LABEL_HEAD_MM: 15,      // hauteur réservée à l'en-tête (logo + titre)
  LABEL_DPI: 300,         // résolution de l'image envoyée à l'imprimante
  LABEL_FILTER: "grayscale(1) contrast(1.15)", // rendu sur l'étiquette (imprimante noir et blanc)

  // "random" : 1 caméra tirée au hasard. "quad" : les 4 recadrées en grille 2×2.
  LAYOUT: "random",
  CAMERA_COUNT: 4,
  SNAPSHOT_URL: "snap/",  // servi par server.py : snap/1 … snap/4
  CAMERAS_URL: "cameras", // présence des caméras (server.py) ; "" pour ne pas vérifier
  CAMERA_CHECK_S: 5,      // fréquence de la vérification
  CAMERAS_DOWN_OK: 1,     // caméras absentes tolérées sans bandeau (au-delà : « pause technique »)
  // Recadrage par caméra : l'image est toujours coupée au format de la zone photo de l'étiquette,
  // centrée sur (x, y de 0 à 1). zoom 1 = bande centrale pleine hauteur (848×1296 px sur C110).
  // À régler sur place pour que la personne soit au centre.
  CROP: [
    { x: 0.5, y: 0.5, zoom: 1 },
    { x: 0.5, y: 0.5, zoom: 1 },
    { x: 0.5, y: 0.5, zoom: 1 },
    { x: 0.5, y: 0.5, zoom: 1 },
  ],
  DEMO: false,            // caméra injoignable : image de test au lieu d'une erreur (false en expo)

  SHOT_DELAY_MS: 1500,    // attente entre la fin du décompte et la capture : augmenter si la photo est prise trop tôt, 0 si trop tard
  COUNTDOWN_S: 3,         // compte à rebours avant la prise de vue
  PRINT: true,            // lance l'impression
  IDLE_TIMEOUT_S: 60,     // retour à l'accueil si personne ne touche l'écran
  RESULT_SCREEN_S: 30,    // durée de l'écran final avant retour à l'accueil
  HIDE_CURSOR: true,      // true sur la borne tactile
};
