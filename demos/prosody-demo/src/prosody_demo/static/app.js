const modelSelect = document.querySelector("#model");
const status = document.querySelector("#status");
const messagesNode = document.querySelector("#messages");
const composer = document.querySelector("#composer");
const prompt = document.querySelector("#prompt");
const send = document.querySelector("#send");
const record = document.querySelector("#record");
const autoSend = document.querySelector("#auto-send");
const timing = document.querySelector("#timing");
const prosodyOutput = document.querySelector("#prosody");
const comparisonBody = document.querySelector("#comparison-body");
const turnDelta = document.querySelector("#turn-delta");
const reset = document.querySelector("#reset");
let messages = [];
let latestProsody = null;
let transcribedText = null;
let sessionId = crypto.randomUUID();
let mediaRecorder = null;
let recordingStream = null;
let audioChunks = [];
let audioContext = null;
let analysisTimer = null;
let endpointController = null;
let endpointDecision = null;
let recordingStartedAt = null;
let pendingTurnTiming = null;
let previousTurn = null;
const latestByMode = { baseline: null, prosody: null };

function selectedMode() {
  return document.querySelector('input[name="mode"]:checked').value;
}

function renderMessage(message) {
  const article = document.createElement("article");
  article.className = `message ${message.role}`;
  const role = document.createElement("strong");
  role.textContent = message.role === "user" ? "You" : "Assistant";
  const content = document.createElement("p");
  content.textContent = message.content;
  article.append(role, content);
  messagesNode.append(article);
  article.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function loadModels() {
  try {
    const response = await fetch("/api/models");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not list models");
    modelSelect.replaceChildren();
    for (const model of data.models) {
      const option = document.createElement("option");
      option.value = model;
      option.textContent = model;
      modelSelect.append(option);
    }
    if (!data.models.length) throw new Error("Ollama has no installed models");
    status.textContent = `Ready · ${data.models.length} Ollama model${data.models.length === 1 ? "" : "s"}`;
  } catch (error) {
    modelSelect.innerHTML = "<option>No models available</option>";
    status.textContent = error.message;
    status.classList.add("error");
  }
}

function summarizeProsody(metadata) {
  const features = metadata.features || {};
  const relative = metadata.deltas?.relative || {};
  const parts = [
    `duration ${Math.round(features.duration_ms || 0)} ms`,
    `energy RMS ${(features.energy_rms || 0).toFixed(4)}`,
    `speech rate ${(features.speech_rate_wpm || 0).toFixed(1)} WPM`,
    `baseline turns ${metadata.baseline_sample_count || 0}`,
  ];
  if (relative.energy_rms != null) parts.push(`energy Δ ${(relative.energy_rms * 100).toFixed(1)}%`);
  if (relative.speech_rate_wpm != null) parts.push(`rate Δ ${(relative.speech_rate_wpm * 100).toFixed(1)}%`);
  const endpoint = endpointDecision
    ? `endpoint ${endpointDecision.reason} at ${endpointDecision.elapsedMs} ms (${endpointDecision.silenceMs} ms silence)\n`
    : "";
  return endpoint + parts.join(" · ");
}

function stopRecording(decision = null) {
  if (mediaRecorder?.state !== "recording") return;
  endpointDecision = decision || {
    reason: "manual_stop",
    mode: selectedMode(),
    elapsedMs: Math.round(performance.now() - recordingStartedAt),
    speechMs: null,
    silenceMs: null,
  };
  mediaRecorder.stop();
  record.disabled = true;
}

function startEndpointMonitor(stream) {
  audioContext = new AudioContext();
  const source = audioContext.createMediaStreamSource(stream);
  const analyser = audioContext.createAnalyser();
  analyser.fftSize = 2048;
  source.connect(analyser);
  const samples = new Float32Array(analyser.fftSize);
  endpointController = new ProsodyEndpointing.EndpointController(selectedMode());
  analysisTimer = setInterval(() => {
    analyser.getFloatTimeDomainData(samples);
    let squares = 0;
    for (const sample of samples) squares += sample * sample;
    const rms = Math.sqrt(squares / samples.length);
    const pitchHz = ProsodyEndpointing.estimatePitch(samples, audioContext.sampleRate);
    const decision = endpointController.addFrame({ nowMs: performance.now(), rms, pitchHz });
    if (decision) stopRecording(decision);
  }, 50);
}

async function transcribeRecording(blob) {
  status.textContent = "Transcribing locally…";
  const transcriptionStartedAt = performance.now();
  const response = await fetch(`/api/transcribe?session_id=${encodeURIComponent(sessionId)}`, {
    method: "POST",
    headers: { "Content-Type": blob.type || "audio/webm" },
    body: blob,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Transcription failed");
  pendingTurnTiming = {
    endpointWaitMs: endpointDecision?.silenceMs,
    transcriptionMs: performance.now() - transcriptionStartedAt,
  };
  prompt.value = data.transcript;
  transcribedText = data.transcript;
  latestProsody = data.prosody;
  prosodyOutput.textContent = summarizeProsody(data.prosody);
  status.textContent = "Transcript ready · review it, then send";
  if (autoSend.checked) {
    status.textContent = "Transcript ready · auto-sending…";
    composer.requestSubmit();
  }
  prompt.focus();
}

function milliseconds(value) {
  return value == null ? "—" : `${Math.round(value)} ms`;
}

function deltaCell(baseline, prosody) {
  if (baseline == null || prosody == null) return "<td>—</td>";
  const delta = prosody - baseline;
  const css = delta < 0 ? "faster" : delta > 0 ? "slower" : "";
  const sign = delta > 0 ? "+" : "";
  return `<td class="${css}">${sign}${Math.round(delta)} ms</td>`;
}

function renderComparison() {
  const baseline = latestByMode.baseline;
  const prosody = latestByMode.prosody;
  const rows = [
    ["Endpoint wait", "endpointWaitMs"],
    ["Transcription pipeline", "transcriptionMs"],
    ["Ollama round trip", "roundTripMs"],
    ["Post-speech total", "postSpeechMs"],
  ];
  comparisonBody.innerHTML = rows.map(([label, key]) => {
    const a = baseline?.[key];
    const b = prosody?.[key];
    return `<tr><th>${label}</th><td>${milliseconds(a)}</td><td>${milliseconds(b)}</td>${deltaCell(a, b)}</tr>`;
  }).join("");
}

prompt.addEventListener("input", () => {
  if (transcribedText !== null && prompt.value !== transcribedText) {
    latestProsody = null;
    transcribedText = null;
    prosodyOutput.textContent = "Transcript edited · measurements detached from this turn.";
  }
});

record.addEventListener("click", async () => {
  if (mediaRecorder?.state === "recording") {
    stopRecording();
    return;
  }
  try {
    recordingStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    endpointDecision = null;
    mediaRecorder = new MediaRecorder(recordingStream);
    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size) audioChunks.push(event.data);
    });
    mediaRecorder.addEventListener("stop", async () => {
      clearInterval(analysisTimer);
      analysisTimer = null;
      recordingStream.getTracks().forEach((track) => track.stop());
      await audioContext?.close();
      audioContext = null;
      record.textContent = "Start mic";
      record.classList.remove("active");
      try {
        await transcribeRecording(new Blob(audioChunks, { type: mediaRecorder.mimeType }));
      } catch (error) {
        status.textContent = error.message;
        status.classList.add("error");
      } finally {
        record.disabled = false;
      }
    });
    recordingStartedAt = performance.now();
    startEndpointMonitor(recordingStream);
    mediaRecorder.start();
    record.textContent = "Stop & transcribe";
    record.classList.add("active");
    status.textContent = "Recording…";
    status.classList.remove("error");
  } catch (error) {
    status.textContent = `Microphone unavailable: ${error.message}`;
    status.classList.add("error");
  }
});

composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  const content = prompt.value.trim();
  if (!content || !modelSelect.value) return;
  const userMessage = { role: "user", content };
  messages.push(userMessage);
  renderMessage(userMessage);
  prompt.value = "";
  send.disabled = true;
  status.textContent = "Ollama is thinking…";
  status.classList.remove("error");
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: modelSelect.value,
        mode: selectedMode(),
        messages,
        prosody: latestProsody,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Chat request failed");
    messages.push(data.message);
    const completedTurn = {
      mode: data.mode,
      recorded: pendingTurnTiming !== null,
      endpointWaitMs: pendingTurnTiming?.endpointWaitMs,
      transcriptionMs: pendingTurnTiming?.transcriptionMs,
      roundTripMs: data.timing.round_trip_ms,
    };
    completedTurn.postSpeechMs = completedTurn.recorded && completedTurn.endpointWaitMs != null
      ? completedTurn.endpointWaitMs
        + completedTurn.transcriptionMs
        + completedTurn.roundTripMs
      : null;
    if (previousTurn) {
      const delta = completedTurn.roundTripMs - previousTurn.roundTripMs;
      const sign = delta > 0 ? "+" : "";
      turnDelta.textContent = `Previous-turn Ollama round-trip Δ ${sign}${Math.round(delta)} ms`;
      turnDelta.className = delta < 0 ? "faster" : delta > 0 ? "slower" : "";
    }
    previousTurn = completedTurn;
    if (completedTurn.recorded) latestByMode[data.mode] = completedTurn;
    renderComparison();
    latestProsody = null;
    transcribedText = null;
    pendingTurnTiming = null;
    renderMessage(data.message);
    timing.textContent = `${data.mode} · round trip ${data.timing.round_trip_ms} ms · Ollama ${data.timing.ollama_total_ms} ms`;
    status.textContent = "Ready";
  } catch (error) {
    messages.pop();
    status.textContent = error.message;
    status.classList.add("error");
  } finally {
    send.disabled = false;
    prompt.focus();
  }
});

reset.addEventListener("click", async () => {
  await fetch("/api/session/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  messages = [];
  latestProsody = null;
  transcribedText = null;
  pendingTurnTiming = null;
  previousTurn = null;
  latestByMode.baseline = null;
  latestByMode.prosody = null;
  sessionId = crypto.randomUUID();
  messagesNode.replaceChildren();
  timing.textContent = "No completed turn yet.";
  prosodyOutput.textContent = "No recorded turn yet.";
  turnDelta.textContent = "Complete another turn to see a round-trip delta.";
  turnDelta.className = "";
  renderComparison();
  status.textContent = "New session ready";
  prompt.focus();
});

loadModels();
