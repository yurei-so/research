const $ = (selector) => document.querySelector(selector);
const review = $("#review");
const complete = $("#complete");
const errorPanel = $("#error");
const dimensions = ["clarity", "fidelity", "concision", "naturalness"];
let current = null;
let busy = false;
let reviewMode = "text";
let activeDimensions = dimensions;

function showError(message) {
  review.classList.add("hidden"); complete.classList.add("hidden");
  errorPanel.classList.remove("hidden");
  $("#errorMessage").textContent = message;
}

async function request(path, options) {
  const response = await fetch(path, {
    ...options,
    headers: { "content-type": "application/json", ...(options?.headers ?? {}) },
  });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error ?? "request_failed");
  return value;
}

function scoreSelect(dimension, candidate) {
  const select = document.createElement("select");
  select.dataset.dimension = dimension; select.dataset.candidate = candidate;
  select.setAttribute("aria-label", `${dimension} score for response ${candidate.toUpperCase()}`);
  for (const [value, label] of [["", `${candidate.toUpperCase()} —`], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"], ["5", "5"]]) {
    const option = document.createElement("option"); option.value = value; option.textContent = label; select.append(option);
  }
  return select;
}

function resetScores(criteria = dimensions) {
  activeDimensions = criteria.filter((item) => dimensions.includes(item));
  const grid = $("#scoreGrid"); grid.replaceChildren();
  for (const dimension of activeDimensions) {
    const row = document.createElement("div"); row.className = "score-row";
    const label = document.createElement("label"); label.textContent = dimension;
    row.append(label, scoreSelect(dimension, "a"), scoreSelect(dimension, "b")); grid.append(row);
  }
  $("#details").open = false;
}

function secondaryScores() {
  const result = {};
  for (const dimension of activeDimensions) {
    const a = $(`select[data-dimension="${dimension}"][data-candidate="a"]`).value;
    const b = $(`select[data-dimension="${dimension}"][data-candidate="b"]`).value;
    if (a || b) {
      if (!a || !b) throw new Error(`Score both responses for ${dimension}, or leave both blank.`);
      result[dimension] = { a: Number(a), b: Number(b) };
    }
  }
  return result;
}

function renderSession(session) {
  current = session.pair;
  reviewMode = session.mode ?? "text";
  const { completed: done, total } = session.progress;
  $("#progressLabel").textContent = `${Math.min(done + (session.complete ? 0 : 1), total)} / ${total}`;
  $("#progressBar").style.width = `${total ? done / total * 100 : 0}%`;
  if (session.complete) { void renderResults(); return; }
  if (reviewMode === "audio" && sessionStorage.getItem("composition_audio_ready") !== "yes") {
    review.classList.add("hidden"); complete.classList.add("hidden");
    const gate = $("#audioGate"); gate.classList.remove("hidden");
    const calibration = $("#calibrationAudio");
    calibration.classList.toggle("hidden", !session.calibration_audio);
    if (session.calibration_audio) calibration.src = session.calibration_audio;
    return;
  }
  $("#audioGate").classList.add("hidden");
  errorPanel.classList.add("hidden"); complete.classList.add("hidden"); review.classList.remove("hidden");
  $("#task").textContent = current.task;
  $("#draft").textContent = current.draft;
  $("#textResponses").classList.toggle("hidden", reviewMode === "audio");
  $("#audioResponses").classList.toggle("hidden", reviewMode !== "audio");
  if (reviewMode === "audio") {
    $("#audioA").src = current.audio_a; $("#audioB").src = current.audio_b;
  } else {
    $("#responseA").textContent = current.response_a;
    $("#responseB").textContent = current.response_b;
  }
  resetScores(current.criteria);
  window.scrollTo({ top: 0, behavior: done ? "smooth" : "auto" });
}

async function choose(choice) {
  if (busy || !current) return;
  let secondary;
  try { secondary = secondaryScores(); } catch (error) { showError(error.message); return; }
  busy = true; review.classList.add("busy");
  try {
    const session = await request("/api/judgments", {
      method: "POST", body: JSON.stringify({ pair_id: current.pair_id, choice, secondary }),
    });
    renderSession(session);
  } catch (error) {
    showError(`Could not save this judgment: ${error.message}`);
  } finally {
    busy = false; review.classList.remove("busy");
  }
}

async function renderResults() {
  try {
    const results = await request("/api/results");
    const baseline = results.baseline_arm ?? "direct_rewrite";
    const treatment = results.treatment_arm;
    const baselineLabel = baseline.split("_").map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
    const direct = results.preference[baseline];
    const treatmentWins = results.preference[treatment];
    if (typeof treatment !== "string" || !Number.isInteger(direct) || !Number.isInteger(treatmentWins)
        || !Number.isInteger(results.preference.tie)) {
      throw new Error("invalid_result_summary");
    }
    const treatmentLabel = treatment.split("_").map((word) =>
      word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
    review.classList.add("hidden"); errorPanel.classList.add("hidden"); complete.classList.remove("hidden");
    $("#progressLabel").textContent = `${results.pairs.length} / ${results.pairs.length}`;
    $("#progressBar").style.width = "100%";
    const cards = $("#resultCards"); cards.replaceChildren();
    for (const [label, value] of [[baselineLabel, direct], [treatmentLabel, treatmentWins], ["Ties", results.preference.tie]]) {
      const card = document.createElement("div"); card.className = "result-card";
      const strong = document.createElement("strong"); strong.textContent = value;
      const span = document.createElement("span"); span.textContent = label;
      card.append(strong, span); cards.append(card);
    }
    $("#resultNote").textContent = direct === treatmentWins
      ? "The preference result is even. Review the secondary scores before drawing a conclusion."
      : `${direct > treatmentWins ? baselineLabel : treatmentLabel} received more primary preferences. Treat this small reviewed corpus as directional evidence.`;
  } catch (error) { showError(`Could not reveal completed results: ${error.message}`); }
}

async function load() {
  try { renderSession(await request("/api/session")); }
  catch (error) { showError(`Could not load the private review session: ${error.message}`); }
}

document.querySelectorAll("[data-choice]").forEach((button) => button.addEventListener("click", () => void choose(button.dataset.choice)));
document.addEventListener("keydown", (event) => {
  if (event.metaKey || event.ctrlKey || event.altKey || event.target.matches("select, input, textarea, summary")) return;
  const choice = { a: "a", b: "b", t: "tie" }[event.key.toLowerCase()];
  if (choice) { event.preventDefault(); void choose(choice); }
});
$("#contextToggle").addEventListener("click", () => {
  const body = $("#contextBody"); const hidden = body.classList.toggle("hidden");
  $("#contextToggle").textContent = hidden ? "Show context" : "Hide context";
});
$("#retry").addEventListener("click", () => { errorPanel.classList.add("hidden"); void load(); });
$("#beginAudioReview").addEventListener("click", () => {
  if (!$("#audioReadyCheck").checked) return;
  sessionStorage.setItem("composition_audio_ready", "yes"); void load();
});
void load();
