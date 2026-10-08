// Réglages du module 4. Modifier ici, puis recharger la page.
window.CONFIG = {
  // Étiquette Dymo S0947420 (LabelWriter 4XL/5XL) : 59 × 102 mm, portrait.
  LABEL_WIDTH_MM: 59,
  LABEL_HEIGHT_MM: 102,
  LABEL_MARGIN_MM: 3,
  PRINT: true,              // imprime l'étiquette à la fin

  // Pont Kinect (bridge/kinect_bridge.py) : squelette envoyé en WebSocket.
  BRIDGE_URL: "ws://localhost:8765",
  REQUIRE_KINECT: true,     // pont absent 15 s = bandeau « en panne » sur l'accueil (false pour travailler sans Kinect)
  // Si le pont ne répond pas : "mouse" (souris / doigt = main droite),
  // "demo" (danseur virtuel), "webcam" (détection de pose, internet requis), "none".
  SIMULATION: "mouse",

  READY_HOLD_S: 2,          // temps sur la croix avant le décompte
  CROSS_TOLERANCE: 0.18,    // écart horizontal toléré autour du centre (0..0,5)
  GET_READY_S: 3,           // 3, 2, 1…
  RECORD_S: 10,             // durée d'enregistrement des mouvements
  IDLE_TIMEOUT_S: 60,       // retour à l'accueil si personne
  RESULT_SCREEN_S: 30,      // durée de l'écran final
  LEARN_KEY: "F9",         // touche (clavier) qui réapprend le décor vide ; aussi : appui long 3 s sur le ✕ de l'accueil
  LEARN_DELAY_S: 5,         // temps pour sortir du champ avant l'apprentissage
  HIDE_CURSOR: true,        // true sur la borne
};
