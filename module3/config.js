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
  // SCAN_STYLE, rendu de la photo à l'écran :
  //   "neon"     contours lumineux roses sur bleu nuit (couleurs de l'expo)
  //   "radio"    radiographie : fond noir, objets blanc bleuté avec une lueur
  //   "aeroport" scanner à bagages : fond blanc, léger = orange, moyen = vert, dense = bleu
  //   "noir"     scanner à bagages sur fond noir
  //   "filtre"   ancien rendu, simple teinte de la photo
  // SCAN_EDGES (0…1) : force des contours.
  SCAN_STYLE: "neon",
  SCAN_EDGES: 0.7,
  SCAN_CONTRAST: 1.3,
  SCAN_BRIGHTNESS: 0,
  SCAN_INVERT: false,
  PRINT_CONTRAST: 1.6,
  PRINT_BRIGHTNESS: 0.05,

  // Étiquette Dymo S0947420 (LabelWriter 4XL/5XL) : 59 × 102 mm, portrait.
  LABEL_WIDTH_MM: 59,
  LABEL_HEIGHT_MM: 102,
  LABEL_MARGIN_MM: 3,

  LIVE_PREVIEW: true,     // écran des consignes : petite vue en direct de la caméra (helper en mode webcam)
  PRINT: true,            // imprime l'étiquette à chaque passage
  PRINT_START_S: 0.2,     // lance l'impression pendant le scan (secondes après son début) pour que l'étiquette
                          // sorte avec le verdict ; null = seulement après le verdict (environ 5 s plus tard)
  SOUND: true,            // bip de scanner + signal « autorisé »
  SCAN_S: 4,              // durée de l'animation de scan
  RESULT_SCREEN_S: 15,    // durée de l'écran « autorisé » avant retour à l'accueil
  IDLE_TIMEOUT_S: 60,     // retour à l'accueil si rien ne se passe
  HIDE_CURSOR: false,     // true sur la borne tactile
};
