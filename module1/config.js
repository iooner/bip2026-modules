// Réglages du module 1. Modifier ici, puis recharger la page.
window.CONFIG = {
  // Étiquette Dymo S0947420 (LabelWriter 4XL/5XL) : 59 × 102 mm, portrait.
  LABEL_WIDTH_MM: 59,
  LABEL_HEIGHT_MM: 102,
  LABEL_MARGIN_MM: 3,

  PRINT: true,            // lance l'impression à la fin du test
  PICK_COUNT: 4,          // nombre de résultats tirés parmi les 8 réponses
  IDLE_TIMEOUT_S: 60,     // retour à l'accueil si personne ne touche l'écran
  RESULT_SCREEN_S: 30,    // durée de l'écran final avant retour à l'accueil
  HIDE_CURSOR: false,     // true sur la borne tactile
};
