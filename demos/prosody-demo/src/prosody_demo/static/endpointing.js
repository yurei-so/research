(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.ProsodyEndpointing = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function mean(values) {
    return values.length ? values.reduce((total, value) => total + value, 0) / values.length : 0;
  }

  function median(values) {
    if (!values.length) return null;
    const sorted = [...values].sort((a, b) => a - b);
    const middle = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
  }

  function estimatePitch(samples, sampleRate) {
    let rms = 0;
    for (const sample of samples) rms += sample * sample;
    rms = Math.sqrt(rms / samples.length);
    if (rms < 0.01) return null;

    const minLag = Math.floor(sampleRate / 400);
    const maxLag = Math.min(Math.floor(sampleRate / 70), samples.length - 2);
    let bestLag = 0;
    let bestCorrelation = 0;
    for (let lag = minLag; lag <= maxLag; lag += 1) {
      let correlation = 0;
      let leftEnergy = 0;
      let rightEnergy = 0;
      for (let index = 0; index < samples.length - lag; index += 1) {
        const left = samples[index];
        const right = samples[index + lag];
        correlation += left * right;
        leftEnergy += left * left;
        rightEnergy += right * right;
      }
      const normalized = correlation / Math.sqrt(leftEnergy * rightEnergy || 1);
      if (normalized > bestCorrelation) {
        bestCorrelation = normalized;
        bestLag = lag;
      }
    }
    return bestCorrelation >= 0.6 && bestLag ? sampleRate / bestLag : null;
  }

  class EndpointController {
    constructor(mode, options = {}) {
      this.mode = mode;
      this.baselineSilenceMs = options.baselineSilenceMs ?? 900;
      this.prosodySilenceMs = options.prosodySilenceMs ?? 450;
      this.prosodyFallbackMs = options.prosodyFallbackMs ?? 1000;
      this.minimumSpeechMs = options.minimumSpeechMs ?? 350;
      this.minimumRms = options.minimumRms ?? 0.015;
      this.noiseFloor = options.initialNoiseFloor ?? 0.004;
      this.startedAt = null;
      this.lastVoicedAt = null;
      this.frames = [];
    }

    addFrame(frame) {
      const threshold = Math.max(this.minimumRms, this.noiseFloor * 3);
      const voiced = frame.rms >= threshold;
      if (!voiced && this.startedAt === null) {
        this.noiseFloor = this.noiseFloor * 0.92 + frame.rms * 0.08;
        return null;
      }
      if (voiced) {
        if (this.startedAt === null) this.startedAt = frame.nowMs;
        this.lastVoicedAt = frame.nowMs;
        this.frames.push(frame);
        if (this.frames.length > 120) this.frames.shift();
        return null;
      }
      if (
        this.lastVoicedAt === null
        || this.lastVoicedAt - this.startedAt < this.minimumSpeechMs
      ) {
        return null;
      }

      const silenceMs = frame.nowMs - this.lastVoicedAt;
      if (this.mode === "baseline" && silenceMs >= this.baselineSilenceMs) {
        return this._decision("fixed_silence", frame.nowMs, silenceMs);
      }
      if (this.mode !== "prosody") return null;
      if (silenceMs >= this.prosodyFallbackMs) {
        return this._decision("prosody_fallback_silence", frame.nowMs, silenceMs);
      }
      if (silenceMs >= this.prosodySilenceMs && this._hasFinalityCue()) {
        return this._decision("measured_finality", frame.nowMs, silenceMs);
      }
      return null;
    }

    _hasFinalityCue() {
      const recent = this.frames.slice(-10);
      if (recent.length < 6) return false;
      const midpoint = Math.floor(recent.length / 2);
      const earlierEnergy = mean(recent.slice(0, midpoint).map((frame) => frame.rms));
      const laterEnergy = mean(recent.slice(midpoint).map((frame) => frame.rms));
      const earlierPitch = median(recent.slice(0, midpoint).map((frame) => frame.pitchHz).filter(Boolean));
      const laterPitch = median(recent.slice(midpoint).map((frame) => frame.pitchHz).filter(Boolean));
      const energyFalling = earlierEnergy > 0 && laterEnergy <= earlierEnergy * 0.85;
      const pitchFalling = earlierPitch !== null && laterPitch !== null && laterPitch <= earlierPitch * 0.95;
      return energyFalling || pitchFalling;
    }

    _decision(reason, nowMs, silenceMs) {
      return {
        reason,
        mode: this.mode,
        speechMs: Math.round(this.lastVoicedAt - this.startedAt),
        silenceMs: Math.round(silenceMs),
        elapsedMs: Math.round(nowMs - this.startedAt),
      };
    }
  }

  return { EndpointController, estimatePitch };
});
