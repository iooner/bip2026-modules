// Source du corps suivi : pont Kinect (WebSocket) en priorité, sinon simulation.
// Format commun d'un corps (coordonnées normalisées 0..1, image en miroir, y vers le bas) :
//   { center: [x, y], joints: { head: [x, y], handL: [x, y], handR, footL, footR, ... } }
(() => {
  const C = window.CONFIG;
  const BONES = [["head", "neck"], ["neck", "shoulderL"], ["neck", "shoulderR"], ["shoulderL", "elbowL"],
    ["elbowL", "handL"], ["shoulderR", "elbowR"], ["elbowR", "handR"], ["neck", "hip"], ["hip", "kneeL"],
    ["kneeL", "footL"], ["hip", "kneeR"], ["kneeR", "footR"]];

  const T = { body: null, source: "none", bridge: false, BONES };
  let bridgeAt = 0, simBody = null;

  // Corps courant : pont si une image récente, sinon simulation.
  T.get = () => {
    if (performance.now() - bridgeAt < 600) return T.body;
    T.bridge = false;
    return simBody;
  };
  T.sourceName = () => (performance.now() - bridgeAt < 600 ? "kinect" : C.SIMULATION);

  // --- Pont Kinect ---
  let sock = null;
  function connect() {
    let ws;
    try { ws = new WebSocket(C.BRIDGE_URL); } catch { return setTimeout(connect, 2000); }
    ws.onmessage = e => {
      try {
        const m = JSON.parse(e.data);
        T.body = (m.bodies && m.bodies[0]) || null;
        bridgeAt = performance.now(); T.bridge = true;
      } catch {}
    };
    ws.onopen = () => { sock = ws; };
    ws.onclose = () => { sock = null; setTimeout(connect, 2000); };
  }
  if (C.BRIDGE_URL) connect();
  // Demande au pont de réapprendre le décor vide dans `delay` secondes. Faux si le pont est absent.
  // Fin d'une session : le pont peut en garder la trace (option --keep-sessions, pour diagnostic).
  T.sessionEnd = () => { if (sock) sock.send(JSON.stringify({ cmd: "session" })); };
  T.learn = delay => { if (!sock) return false; sock.send(JSON.stringify({ cmd: "learn", delay })); return true; };

  // Silhouette par défaut, debout bras écartés.
  function pose(handL, handR, sway = 0) {
    const cx = 0.5 + sway;
    return {
      center: [cx, 0.55],
      joints: {
        head: [cx, 0.17], neck: [cx, 0.27], shoulderL: [cx - 0.07, 0.29], shoulderR: [cx + 0.07, 0.29],
        elbowL: [(cx - 0.07 + handL[0]) / 2, (0.29 + handL[1]) / 2 + 0.03],
        elbowR: [(cx + 0.07 + handR[0]) / 2, (0.29 + handR[1]) / 2 + 0.03],
        handL, handR, hip: [cx, 0.55], kneeL: [cx - 0.05, 0.73], kneeR: [cx + 0.05, 0.73],
        footL: [cx - 0.06, 0.92], footR: [cx + 0.06, 0.92],
      },
    };
  }

  // --- Simulation souris / doigt : main droite = pointeur, main gauche en miroir ---
  if (C.SIMULATION === "mouse") {
    let p = [0.75, 0.45];
    simBody = pose([0.25, 0.45], p);
    addEventListener("pointermove", e => {
      const r = document.getElementById("stage").getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      if (x < 0 || x > 1 || y < 0 || y > 1) return;
      simBody = pose([1 - x, y], [x, y]);
    });
  }

  // --- Simulation « danseur » : mouvements synthétiques ---
  if (C.SIMULATION === "demo") {
    const t0 = performance.now();
    (function tick() {
      const t = (performance.now() - t0) / 1000;
      simBody = pose(
        [0.3 + 0.15 * Math.sin(t * 1.3), 0.4 + 0.25 * Math.sin(t * 2.1 + 1)],
        [0.7 + 0.15 * Math.sin(t * 1.7 + 2), 0.4 + 0.25 * Math.cos(t * 1.1)],
        0.04 * Math.sin(t * 0.7));
      const j = simBody.joints;
      j.footL = [0.44 + 0.04 * Math.sin(t * 2.3), 0.92 - 0.04 * Math.max(0, Math.sin(t * 2.3))];
      j.footR = [0.56 + 0.04 * Math.cos(t * 1.9), 0.92 - 0.04 * Math.max(0, Math.cos(t * 1.9))];
      j.head = [simBody.center[0] + 0.02 * Math.sin(t * 3), 0.17 + 0.01 * Math.cos(t * 3)];
      requestAnimationFrame(tick);
    })();
  }

  // --- Simulation webcam : MediaPipe Pose dans le navigateur (téléchargé depuis internet) ---
  if (C.SIMULATION === "webcam") {
    const VER = "0.10.14", MAP = { head: 0, shoulderL: 11, shoulderR: 12, elbowL: 13, elbowR: 14,
      handL: 15, handR: 16, kneeL: 25, kneeR: 26, footL: 27, footR: 28 };
    (async () => {
      const v = await import(`https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${VER}/vision_bundle.mjs`);
      const files = await v.FilesetResolver.forVisionTasks(
        `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${VER}/wasm`);
      const lm = await v.PoseLandmarker.createFromOptions(files, {
        baseOptions: { modelAssetPath: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task" },
        runningMode: "VIDEO", numPoses: 1 });
      const video = document.createElement("video");
      video.srcObject = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      video.muted = true; await video.play();
      let last = -1;
      (function tick() {
        if (video.currentTime !== last) {
          last = video.currentTime;
          const r = lm.detectForVideo(video, performance.now());
          const L = r.landmarks && r.landmarks[0];
          if (!L) simBody = null;
          else {
            const pt = i => [1 - L[i].x, L[i].y], joints = {};   // 1 - x : effet miroir
            for (const k in MAP) joints[k] = pt(MAP[k]);
            const mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
            joints.neck = mid(joints.shoulderL, joints.shoulderR);
            joints.hip = mid(pt(23), pt(24));
            simBody = { center: joints.hip, joints };
          }
        }
        requestAnimationFrame(tick);
      })();
    })().catch(e => console.warn("Simulation webcam indisponible", e));
  }

  // Dessine le squelette (aperçu « miroir »).
  T.drawSkeleton = (ctx, body, color = "#fff", lw = 6) => {
    const { width: w, height: h } = ctx.canvas;
    ctx.clearRect(0, 0, w, h);
    if (!body) return;
    const j = { ...body.joints };
    // Kinect sans squelette (tête, mains, pieds, bassin) : cou déduit pour relier les mains.
    if (!j.neck && j.head && j.hip) j.neck = [j.head[0] * .75 + j.hip[0] * .25, j.head[1] * .75 + j.hip[1] * .25];
    for (const s of ["L", "R"]) {
      if (!j["shoulder" + s] && j.neck) j["shoulder" + s] = j.neck;
      if (!j["elbow" + s] && j["hand" + s]) j["elbow" + s] = j["shoulder" + s];
      if (!j["knee" + s] && j["foot" + s]) j["knee" + s] = j.hip;
    }
    ctx.strokeStyle = ctx.fillStyle = color; ctx.lineWidth = lw; ctx.lineCap = "round";
    ctx.beginPath();
    for (const [a, b] of BONES) if (j[a] && j[b]) {
      ctx.moveTo(j[a][0] * w, j[a][1] * h); ctx.lineTo(j[b][0] * w, j[b][1] * h);
    }
    ctx.stroke();
    if (j.head) { ctx.beginPath(); ctx.arc(j.head[0] * w, j.head[1] * h, lw * 3, 0, 7); ctx.fill(); }
    for (const k of ["handL", "handR", "footL", "footR"]) if (j[k]) {
      ctx.beginPath(); ctx.arc(j[k][0] * w, j[k][1] * h, lw * 1.4, 0, 7); ctx.fill();
    }
  };

  window.Tracker = T;
})();
