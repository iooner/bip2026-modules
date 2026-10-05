// Réglages du module 3. Modifier ici, puis recharger la page.
window.CONFIG = {
  // Simulation (sans Pi, sans caméra) : image d'exemple, déclenchement par la touche Espace
  // ou le bouton à l'écran. Aussi activable par l'URL : index.html?sim=1
  SIMULATE: false,

  // Petit serveur local sur le Pi (helper/helper.py) : bouton GPIO + Pi Camera.
  HELPER_URL: "http://127.0.0.1:8765",

  // Cadrage de la photo (fractions de l'image : 0 = rien rogné), rotation 0/90/180/270, miroir.
  CROP: { left: 0, top: 0, right: 0, bottom: 0 },
  ROTATE: 0,
  MIRROR: false,

  // Rendu « rayons X » : contraste, luminosité (-0.5…0.5), négatif. Écran puis étiquette (noir et blanc).
  SCAN_CONTRAST: 1.3,
  SCAN_BRIGHTNESS: 0,
  SCAN_INVERT: false,
  PRINT_CONTRAST: 1.6,
  PRINT_BRIGHTNESS: 0.05,

  // Étiquette Dymo S0947420 (LabelWriter 4XL/5XL) : 59 × 102 mm, portrait.
  LABEL_WIDTH_MM: 59,
  LABEL_HEIGHT_MM: 102,
  LABEL_MARGIN_MM: 3,

  PRINT: true,            // imprime l'étiquette à chaque passage
  SOUND: true,            // bip de scanner + signal « autorisé »
  SCAN_S: 4,              // durée de l'animation de scan
  RESULT_SCREEN_S: 15,    // durée de l'écran « autorisé » avant retour à l'accueil
  IDLE_TIMEOUT_S: 60,     // retour à l'accueil si rien ne se passe
  HIDE_CURSOR: false,     // true sur la borne tactile
};
