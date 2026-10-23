const state = { signs: [], index: 0, stream: null, busy: false, generation: 0, userId: "student_01" };
const $ = (id) => document.getElementById(id);
const video = $("camera-video");
const canvas = document.createElement("canvas");
const context = canvas.getContext("2d", { alpha: false });

function currentSign() { return state.signs[state.index]; }
function showMessage(text = "") { const el = $("page-message"); el.textContent = text; el.hidden = !text; }
function setFeedback(title, message, icon = "🌼", eyebrow = "YOU'RE DOING GREAT") {
  $("feedback-title").textContent = title; $("feedback-message").textContent = message;
  $("feedback-icon").textContent = icon; $("feedback-eyebrow").textContent = eyebrow;
  $("similarity-chip").hidden = true; $("score-note").hidden = true;
}
function renderSign() {
  const sign = currentSign(); if (!sign) return;
  state.generation += 1;
  $("capture-overlay").hidden = true;
  $("word-title").textContent = sign.word;
  $("hand-count").textContent = `✋ ${sign.hands} ${sign.hands === 1 ? "hand" : "hands"}`;
  $("progress-text").textContent = `Sign ${state.index + 1} of ${state.signs.length}`;
  $("progress-fill").style.width = `${((state.index + 1) / state.signs.length) * 100}%`;
  $("previous-button").disabled = state.index === 0;
  $("next-button").disabled = state.index === state.signs.length - 1;
  $("nav-hint").textContent = state.index === state.signs.length - 1 ? "You reached the last sign 🌿" : "Move at your own pace 🌿";
  $("reference-image").hidden = true; $("reference-video").hidden = true;
  $("reference-image").removeAttribute("src"); $("reference-video").pause(); $("reference-video").removeAttribute("src");
  $("replay-button").hidden = sign.media_type !== "video";
  if (sign.media_url) {
    $("media-placeholder").hidden = true;
    if (sign.media_type === "video") { $("reference-video").src = sign.media_url; $("reference-video").hidden = false; }
    else { $("reference-image").src = sign.media_url; $("reference-image").hidden = false; }
  } else { $("media-placeholder").hidden = false; $("media-placeholder").querySelector("p").textContent = "No reference demonstration is available yet."; }
  $("reference-caption").textContent = sign.media_type === "video" ? "Watch the SLSL demonstration. Use replay whenever you need." : "Look closely at the SLSL reference image.";
  $("analyze-button").disabled = !state.stream || !sign.media_url;
  setFeedback("Ready to try?", sign.media_url ? "Watch the example, then press Sign now when you're ready." : "This sign needs a reference demonstration before practice.");
  showMessage("");
}
async function loadLesson() {
  try {
    const response = await fetch("/api/lesson"); if (!response.ok) throw new Error((await response.json()).detail || "Could not load the lesson.");
    const data = await response.json(); state.signs = data.signs; state.userId = data.user_id || state.userId;
    if (!state.signs.length) throw new Error("No signs with reference material were found.");
    renderSign();
  } catch (error) { setFeedback("Let's try again", "The lesson could not load right now.", "🌱"); showMessage(error.message); }
}
async function startCamera() {
  showMessage("");
  if (!navigator.mediaDevices?.getUserMedia) { showMessage("Camera access needs a secure page (localhost is okay) and a supported browser."); return; }
  state.generation += 1;
  try {
    if (state.stream) state.stream.getTracks().forEach((track) => track.stop());
    state.stream = null; video.srcObject = null; video.hidden = true; $("camera-placeholder").hidden = false; $("analyze-button").disabled = true;
    state.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 960 }, height: { ideal: 720 } }, audio: false });
    video.srcObject = state.stream; video.hidden = false; $("camera-placeholder").hidden = true;
    $("camera-state").classList.add("is-live"); $("camera-state").innerHTML = "<i></i> Camera ready";
    $("camera-button").textContent = "↻ Retry camera"; $("analyze-button").disabled = !currentSign()?.media_url;
  } catch (error) {
    const reason = error.name === "NotAllowedError" ? "Camera permission is off. Allow camera access in your browser, then try again." : "We couldn't start the camera. Check that it is connected and not being used by another app.";
    showMessage(reason); setFeedback("Camera needs a hand", reason, "📷", "CAMERA HELP");
  }
}
function wait(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
async function captureSamples(generation) {
  const samples = []; const duration = 6000; const interval = 200; const started = performance.now();
  $("capture-overlay").hidden = false;
  while (performance.now() - started < duration && generation === state.generation) {
    const remaining = Math.max(0, Math.ceil((duration - (performance.now() - started)) / 1000));
    $("capture-label").textContent = "Signing…"; $("capture-countdown").textContent = String(remaining);
    if (video.videoWidth && video.videoHeight) {
      const scale = Math.min(1, 800 / video.videoWidth); canvas.width = Math.round(video.videoWidth * scale); canvas.height = Math.round(video.videoHeight * scale);
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      let sample = canvas.toDataURL("image/jpeg", 0.8).split(",")[1];
      if (sample.length > 340_000) {
        canvas.width = Math.round(canvas.width * 0.8); canvas.height = Math.round(canvas.height * 0.8);
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        sample = canvas.toDataURL("image/jpeg", 0.7).split(",")[1];
      }
      samples.push(sample);
    }
    await wait(interval);
  }
  $("capture-overlay").hidden = true;
  return generation === state.generation ? samples : null;
}
async function analyze() {
  if (!state.stream || state.busy) return;
  const sign = currentSign(); const signIndex = state.index; const generation = state.generation;
  state.busy = true; $("analyze-button").disabled = true; $("analyze-button").innerHTML = "<span>⏳</span> Analyzing";
  setFeedback("Keep signing!", "Hold your hands where the camera can see them.", "👀", "ANALYZING"); showMessage("");
  try {
    const frames = await captureSamples(generation);
    if (!frames || state.generation !== generation) return;
    $("capture-overlay").hidden = false;
    $("capture-label").textContent = "Checking your sign…";
    $("capture-countdown").textContent = "✦";
    const response = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ sign_id: sign.id, user_id: state.userId, frames }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "The sign could not be analyzed.");
    if (state.generation !== generation || state.index !== signIndex) return;
    if (data.status !== "COMPLETED") { setFeedback("Let's try once more", data.message, "🌱", "READY WHEN YOU ARE"); return; }
    const message = data.recommendation ? `${data.message} Practice idea: ${data.recommendation}.` : data.message;
    setFeedback("Nice work showing your sign!", message, data.ml_prediction === "NORMAL" ? "🌟" : "🦉", data.ml_available ? "SIGN ANALYZED" : "REFERENCE CHECK");
    $("similarity-value").textContent = `${Math.round(data.similarity_score)}%`;
    $("similarity-chip").hidden = false; $("score-note").hidden = false;
  } catch (error) {
    if (state.generation === generation) { setFeedback("Let's try again", error.message, "🌱", "ANALYSIS PAUSED"); showMessage("Check that the learning service is still running, then try again."); }
  } finally {
    $("capture-overlay").hidden = true;
    state.busy = false; $("analyze-button").innerHTML = "<span aria-hidden=\"true\">✋</span> Sign now";
    if (state.stream && currentSign()?.media_url) $("analyze-button").disabled = false;
  }
}
function moveTo(index) { if (index < 0 || index >= state.signs.length) return; state.index = index; renderSign(); }

$("camera-button").addEventListener("click", startCamera);
$("analyze-button").addEventListener("click", analyze);
$("previous-button").addEventListener("click", () => moveTo(state.index - 1));
$("next-button").addEventListener("click", () => moveTo(state.index + 1));
$("home-button").addEventListener("click", () => moveTo(0));
$("settings-button").addEventListener("click", () => { if (state.stream) { state.generation += 1; state.stream.getTracks().forEach((track) => track.stop()); state.stream = null; video.srcObject = null; video.hidden = true; $("camera-placeholder").hidden = false; $("camera-state").classList.remove("is-live"); $("camera-state").innerHTML = "<i></i> Camera off"; $("camera-button").textContent = "▶ Start camera"; $("analyze-button").disabled = true; setFeedback("Camera paused", "Start the camera again whenever you're ready.", "📷"); } else { startCamera(); } });
$("replay-button").addEventListener("click", () => { const media = $("reference-video"); media.currentTime = 0; media.play().catch(() => {}); });
window.addEventListener("beforeunload", () => state.stream?.getTracks().forEach((track) => track.stop()));
loadLesson();
