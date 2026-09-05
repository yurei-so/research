const test = require("node:test");
const assert = require("node:assert/strict");
const { EndpointController, estimatePitch } = require("../src/prosody_demo/static/endpointing.js");

function feedSpeech(controller, pitches = [220, 215, 210, 200, 190, 180]) {
  pitches.forEach((pitchHz, index) => controller.addFrame({ nowMs: index * 100, rms: 0.1, pitchHz }));
}

test("baseline waits for its fixed silence window", () => {
  const controller = new EndpointController("baseline");
  feedSpeech(controller);
  assert.equal(controller.addFrame({ nowMs: 1300, rms: 0, pitchHz: null }), null);
  assert.equal(controller.addFrame({ nowMs: 1400, rms: 0, pitchHz: null }).reason, "fixed_silence");
});

test("prosody commits early on a falling pitch cue", () => {
  const controller = new EndpointController("prosody");
  feedSpeech(controller);
  const decision = controller.addFrame({ nowMs: 950, rms: 0, pitchHz: null });
  assert.equal(decision.reason, "measured_finality");
  assert.equal(decision.silenceMs, 450);
});

test("prosody uses conservative fallback without finality", () => {
  const controller = new EndpointController("prosody");
  feedSpeech(controller, [200, 200, 200, 200, 200, 200]);
  assert.equal(controller.addFrame({ nowMs: 950, rms: 0, pitchHz: null }), null);
  assert.equal(
    controller.addFrame({ nowMs: 1500, rms: 0, pitchHz: null }).reason,
    "prosody_fallback_silence",
  );
});

test("a short noise does not become a turn after silence", () => {
  const controller = new EndpointController("baseline");
  controller.addFrame({ nowMs: 0, rms: 0.1, pitchHz: null });
  controller.addFrame({ nowMs: 50, rms: 0.1, pitchHz: null });
  assert.equal(controller.addFrame({ nowMs: 2000, rms: 0, pitchHz: null }), null);
});

test("pitch estimator recognizes a voiced sine wave", () => {
  const sampleRate = 16000;
  const samples = new Float32Array(2048);
  for (let index = 0; index < samples.length; index += 1) {
    samples[index] = 0.2 * Math.sin(2 * Math.PI * 200 * index / sampleRate);
  }
  assert.ok(Math.abs(estimatePitch(samples, sampleRate) - 200) < 5);
});
