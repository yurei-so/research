import { createHash, randomUUID } from "node:crypto";
import { constants } from "node:fs";
import { chmod, lstat, mkdir, open, readFile, rename, stat, unlink } from "node:fs/promises";
import { basename, dirname, resolve } from "node:path";

const CHOICES = new Set(["a", "b", "tie"]);
const DIMENSIONS = new Set(["clarity", "fidelity", "concision", "naturalness"]);

export class ReviewError extends Error {
  constructor(code, status = 400) {
    super(code);
    this.code = code;
    this.status = status;
  }
}

function canonical(value) {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value).replace(/[\u007f-\uffff]/g, (character) =>
      `\\u${character.charCodeAt(0).toString(16).padStart(4, "0")}`);
  }
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  return `{${Object.keys(value).sort().map((key) => `${canonical(key)}:${canonical(value[key])}`).join(",")}}`;
}

function digest(value) {
  return createHash("sha256").update(canonical(value)).digest("hex");
}

function unicodeDigest(value) {
  const stable = (item) => {
    if (item === null || typeof item !== "object") return JSON.stringify(item);
    if (Array.isArray(item)) return `[${item.map(stable).join(",")}]`;
    return `{${Object.keys(item).sort().map((name) => `${stable(name)}:${stable(item[name])}`).join(",")}}`;
  };
  return createHash("sha256").update(stable(value), "utf8").digest("hex");
}

function exactKeys(value, expected) {
  return value && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).length === expected.length
    && expected.every((key) => Object.hasOwn(value, key));
}

function validateBundle(bundle, key) {
  const scalarMode = exactKeys(bundle, ["format", "version", "experiment_id", "protocol_digest", "source_digest", "items", "bundle_digest"])
    && bundle.format === "narrative-steering.review-bundle" && bundle.version === 1;
  if (scalarMode) {
    const unsigned = Object.fromEntries(Object.entries(bundle).filter(([name]) => name !== "bundle_digest"));
    if (bundle.bundle_digest !== unicodeDigest(unsigned) || !Array.isArray(bundle.items)
        || bundle.items.length < 1 || bundle.items.length > 500
        || !exactKeys(key, ["format", "version", "bundle_digest", "items"])
        || key.format !== "narrative-steering.reveal" || key.version !== 1
        || key.bundle_digest !== bundle.bundle_digest || !Array.isArray(key.items)) {
      throw new ReviewError("invalid_scalar_review_bundle");
    }
    const itemIds = new Set();
    for (const item of bundle.items) {
      if (!exactKeys(item, ["item_id", "case_id", "variant_id", "story_state", "instruction", "continuation", "dimensions", "anchors", "score_range", "confidence_range"])
          || typeof item.item_id !== "string" || itemIds.has(item.item_id)
          || typeof item.instruction !== "string" || typeof item.continuation !== "string"
          || !Array.isArray(item.dimensions) || item.dimensions.length < 1
          || new Set(item.dimensions).size !== item.dimensions.length
          || !item.dimensions.every((name) => typeof name === "string" && /^[a-z][a-z0-9_]{0,39}$/.test(name))
          || !exactKeys(item.anchors, item.dimensions)
          || !item.dimensions.every((name) => exactKeys(item.anchors[name], ["negative", "positive"])
            && typeof item.anchors[name].negative === "string" && typeof item.anchors[name].positive === "string")
          || !Array.isArray(item.score_range) || item.score_range.length !== 2
          || !item.score_range.every(Number.isInteger) || item.score_range[0] >= item.score_range[1]
          || !Array.isArray(item.confidence_range) || item.confidence_range.length !== 2
          || !item.confidence_range.every(Number.isInteger) || item.confidence_range[0] >= item.confidence_range[1]) {
        throw new ReviewError("invalid_scalar_review_item");
      }
      itemIds.add(item.item_id);
    }
    const revealIds = key.items.map((item) => item?.item_id);
    if (key.items.length !== itemIds.size || new Set(revealIds).size !== itemIds.size
        || revealIds.some((id) => !itemIds.has(id))
        || key.items.some((item) => !exactKeys(item, ["item_id", "model_id", "case_id", "variant_id", "sample_id"])
          || typeof item.model_id !== "string" || typeof item.case_id !== "string"
          || typeof item.variant_id !== "string" || !Number.isInteger(item.sample_id))) {
      throw new ReviewError("invalid_scalar_review_reveal");
    }
    return { bundleDigest: bundle.bundle_digest, bundle, reveal: null,
      baselineArm: null, treatmentArm: null, mode: "scalar", assets: new Map() };
  }
  const textMode = exactKeys(bundle, ["format", "version", "campaign_digest", "pairs"])
    && bundle.format === "composition-pipeline.blinded-review" && bundle.version === 1;
  const audioMode = exactKeys(bundle, ["format", "version", "campaign_digest", "mode", "calibration_asset", "assets", "pairs"])
    && bundle.format === "composition-pipeline.blinded-review" && bundle.version === 2
    && bundle.mode === "audio" && Array.isArray(bundle.assets);
  if ((!textMode && !audioMode) || !Array.isArray(bundle.pairs)
      || bundle.pairs.length < 1 || bundle.pairs.length > 500) {
    throw new ReviewError("invalid_review_bundle");
  }
  const keyFields = key?.version === 2
    ? ["format", "version", "campaign_digest", "review_bundle_digest", "baseline_arm", "treatment_arm", "pairs"]
    : ["format", "version", "campaign_digest", "review_bundle_digest", "pairs"];
  if (!exactKeys(key, keyFields)
      || key.format !== "composition-pipeline.blinded-review-key"
      || ![1, 2].includes(key.version) || key.version !== bundle.version
      || key.campaign_digest !== bundle.campaign_digest || key.review_bundle_digest !== digest(bundle)
      || !Array.isArray(key.pairs) || key.pairs.length !== bundle.pairs.length) {
    throw new ReviewError("invalid_review_key");
  }
  const assets = new Map();
  if (audioMode) {
    for (const asset of bundle.assets) {
      if (!exactKeys(asset, ["asset_id", "file_name", "sha256", "media_type"])
          || typeof asset.asset_id !== "string" || !/^[a-z0-9][a-z0-9_-]{0,79}$/.test(asset.asset_id)
          || assets.has(asset.asset_id) || typeof asset.file_name !== "string"
          || basename(asset.file_name) !== asset.file_name || !/^[a-zA-Z0-9][a-zA-Z0-9._-]{0,159}$/.test(asset.file_name)
          || !/^[a-f0-9]{64}$/.test(asset.sha256)
          || !["audio/wav", "audio/mpeg", "audio/ogg"].includes(asset.media_type)) {
        throw new ReviewError("invalid_review_asset");
      }
      assets.set(asset.asset_id, asset);
    }
    if (bundle.calibration_asset !== null && !assets.has(bundle.calibration_asset)) {
      throw new ReviewError("invalid_calibration_asset");
    }
  }
  const pairIds = new Set();
  for (const pair of bundle.pairs) {
    const expected = audioMode
      ? ["pair_id", "case_id", "prompt_style", "repetition", "task", "draft", "candidate_a_asset", "candidate_b_asset", "criteria"]
      : ["pair_id", "case_id", "prompt_style", "repetition", "task", "draft", "candidate_a", "candidate_b", "criteria"];
    if (!exactKeys(pair, expected)
        || typeof pair.pair_id !== "string" || pairIds.has(pair.pair_id)
        || typeof pair.task !== "string" || typeof pair.draft !== "string"
        || (audioMode
          ? !assets.has(pair.candidate_a_asset) || !assets.has(pair.candidate_b_asset)
            || pair.candidate_a_asset === pair.candidate_b_asset
          : typeof pair.candidate_a !== "string" || typeof pair.candidate_b !== "string")) {
      throw new ReviewError("invalid_review_pair");
    }
    pairIds.add(pair.pair_id);
  }
  const reveal = new Map();
  const arms = new Set();
  for (const item of key.pairs) {
    if (!exactKeys(item, ["pair_id", "candidate_a_arm", "candidate_b_arm"])
        || !pairIds.has(item.pair_id) || reveal.has(item.pair_id)
        || new Set([item.candidate_a_arm, item.candidate_b_arm]).size !== 2
        || ![item.candidate_a_arm, item.candidate_b_arm].every((arm) =>
          typeof arm === "string" && /^[a-z0-9][a-z0-9_]{0,79}$/.test(arm))) {
      throw new ReviewError("invalid_review_reveal");
    }
    arms.add(item.candidate_a_arm); arms.add(item.candidate_b_arm);
    reveal.set(item.pair_id, item);
  }
  if (reveal.size !== pairIds.size) throw new ReviewError("incomplete_review_reveal");
  const baselineArm = key.version === 2 ? key.baseline_arm : "direct_rewrite";
  const treatmentArm = key.version === 2 ? key.treatment_arm : [...arms].find((arm) => arm !== baselineArm);
  if (arms.size !== 2 || !arms.has(baselineArm) || !arms.has(treatmentArm)
      || baselineArm === treatmentArm) throw new ReviewError("invalid_review_arms");
  if ([...reveal.values()].some((item) =>
    new Set([item.candidate_a_arm, item.candidate_b_arm]).size !== 2
    || ![item.candidate_a_arm, item.candidate_b_arm].every((arm) => arms.has(arm)))) {
    throw new ReviewError("inconsistent_review_arms");
  }
  const bundleDigest = digest(bundle);
  const ranked = [...bundle.pairs].sort((left, right) => {
    const leftRank = digest(`${bundleDigest}:${left.pair_id}`);
    const rightRank = digest(`${bundleDigest}:${right.pair_id}`);
    return leftRank.localeCompare(rightRank);
  });
  const baselineOnA = new Set(
    ranked.slice(0, Math.ceil(ranked.length / 2)).map((pair) => pair.pair_id),
  );
  const presentedReveal = new Map();
  const presentedPairs = bundle.pairs.map((pair) => {
    const source = reveal.get(pair.pair_id);
    const targetA = baselineOnA.has(pair.pair_id) ? baselineArm : treatmentArm;
    if (source.candidate_a_arm === targetA) {
      presentedReveal.set(pair.pair_id, source);
      return { ...pair };
    }
    presentedReveal.set(pair.pair_id, {
      pair_id: pair.pair_id,
      candidate_a_arm: source.candidate_b_arm,
      candidate_b_arm: source.candidate_a_arm,
    });
    return audioMode
      ? { ...pair, candidate_a_asset: pair.candidate_b_asset, candidate_b_asset: pair.candidate_a_asset }
      : { ...pair, candidate_a: pair.candidate_b, candidate_b: pair.candidate_a };
  });
  return {
    bundleDigest,
    bundle: { ...bundle, pairs: presentedPairs },
    reveal: presentedReveal, baselineArm, treatmentArm, mode: audioMode ? "audio" : "text", assets,
  };
}

async function atomicWrite(path, value) {
  const directory = dirname(path);
  await mkdir(directory, { recursive: true, mode: 0o700 });
  const directoryInfo = await lstat(directory);
  if (!directoryInfo.isDirectory() || directoryInfo.isSymbolicLink()
      || (typeof process.getuid === "function" && directoryInfo.uid !== process.getuid())) {
    throw new ReviewError("unsafe_judgment_directory");
  }
  await chmod(directory, 0o700);
  const temporary = `${path}.${process.pid}.${randomUUID()}.tmp`;
  try {
    const handle = await open(temporary, constants.O_CREAT | constants.O_EXCL | constants.O_WRONLY, 0o600);
    try {
      await handle.writeFile(`${JSON.stringify(value, null, 2)}\n`);
      await handle.sync();
    } finally {
      await handle.close();
    }
    await rename(temporary, path);
    await chmod(path, 0o600);
  } finally {
    await unlink(temporary).catch(() => undefined);
  }
}

function validateSecondary(value) {
  if (value === undefined || value === null) return {};
  if (!value || typeof value !== "object" || Array.isArray(value) || Object.keys(value).some((key) => !DIMENSIONS.has(key))) {
    throw new ReviewError("invalid_secondary_scores");
  }
  const result = {};
  for (const [dimension, scores] of Object.entries(value)) {
    if (!exactKeys(scores, ["a", "b"]) || ![scores.a, scores.b].every((score) => Number.isInteger(score) && score >= 1 && score <= 5)) {
      throw new ReviewError("invalid_secondary_scores");
    }
    result[dimension] = { a: scores.a, b: scores.b };
  }
  return result;
}

export class ReviewStore {
  static async open({ bundlePath, keyPath, statePath, assetRoot, now = () => new Date() }) {
    const [bundleInfo, keyInfo] = await Promise.all([stat(bundlePath), stat(keyPath)]);
    if (!bundleInfo.isFile() || !keyInfo.isFile()) throw new ReviewError("review_sources_must_be_files");
    const [bundle, key] = await Promise.all([
      readFile(bundlePath, "utf8").then(JSON.parse),
      readFile(keyPath, "utf8").then(JSON.parse),
    ]);
    const validation = validateBundle(bundle, key);
    const audioAssets = new Map();
    if (validation.mode === "audio") {
      if (typeof assetRoot !== "string" || !assetRoot.startsWith("/")) {
        throw new ReviewError("absolute_audio_asset_root_required");
      }
      const root = resolve(assetRoot);
      for (const [assetId, asset] of validation.assets) {
        const path = resolve(root, asset.file_name);
        if (!path.startsWith(`${root}/`)) throw new ReviewError("unsafe_review_asset_path");
        const info = await lstat(path);
        if (!info.isFile() || info.isSymbolicLink()) throw new ReviewError("unsafe_review_asset");
        const content = await readFile(path);
        if (createHash("sha256").update(content).digest("hex") !== asset.sha256) {
          throw new ReviewError("review_asset_digest_mismatch");
        }
        audioAssets.set(assetId, { path, mediaType: asset.media_type, size: info.size });
      }
    }
    const absoluteState = resolve(statePath);
    let state;
    try {
      state = JSON.parse(await readFile(absoluteState, "utf8"));
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
      const timestamp = now().toISOString();
      state = validation.mode === "scalar" ? {
        format: "narrative-steering.judgments", version: 1,
        bundle_digest: validation.bundleDigest, judgments: [],
        started_at: timestamp, updated_at: timestamp, completed_at: null,
      } : {
        format: "composition-review.judgments", version: 1,
        bundle_digest: validation.bundleDigest, judgments: {},
        started_at: timestamp, updated_at: timestamp, completed_at: null,
      };
      await atomicWrite(absoluteState, state);
    }
    const expectedStateFormat = validation.mode === "scalar" ? "narrative-steering.judgments" : "composition-review.judgments";
    if (!exactKeys(state, ["format", "version", "bundle_digest", "judgments", "started_at", "updated_at", "completed_at"])
        || state.format !== expectedStateFormat || state.version !== 1
        || state.bundle_digest !== validation.bundleDigest || !state.judgments || typeof state.judgments !== "object"
        || (validation.mode === "scalar" && !Array.isArray(state.judgments))
        || (validation.mode !== "scalar" && Array.isArray(state.judgments))) {
      throw new ReviewError("judgment_state_mismatch");
    }
    if (validation.mode === "scalar") {
      const knownItems = new Map(bundle.items.map((item) => [item.item_id, item]));
      const seen = new Set();
      for (const judgment of state.judgments) {
        const item = knownItems.get(judgment?.item_id);
        if (!item || seen.has(judgment.item_id)
            || !exactKeys(judgment, ["item_id", "scores", "confidence", "committed_at"])
            || !exactKeys(judgment.scores, item.dimensions)
            || !Object.values(judgment.scores).every((score) => Number.isInteger(score)
              && score >= item.score_range[0] && score <= item.score_range[1])
            || !Number.isInteger(judgment.confidence)
            || judgment.confidence < item.confidence_range[0] || judgment.confidence > item.confidence_range[1]) {
          throw new ReviewError("invalid_judgment_state");
        }
        seen.add(judgment.item_id);
      }
      return new ReviewStore({ bundle: validation.bundle, reveal: null,
        baselineArm: null, treatmentArm: null, mode: validation.mode,
        audioAssets, state, statePath: absoluteState, now });
    }
    const knownIds = new Set(bundle.pairs.map((pair) => pair.pair_id));
    for (const [pairId, judgment] of Object.entries(state.judgments)) {
      if (!knownIds.has(pairId)
          || !exactKeys(judgment, ["choice", "secondary", "committed_at"])
          || !CHOICES.has(judgment.choice) || typeof judgment.committed_at !== "string") {
        throw new ReviewError("invalid_judgment_state");
      }
      validateSecondary(judgment.secondary);
    }
    return new ReviewStore({
      bundle: validation.bundle, reveal: validation.reveal,
      baselineArm: validation.baselineArm, treatmentArm: validation.treatmentArm,
      mode: validation.mode, audioAssets, state, statePath: absoluteState, now,
    });
  }

  constructor({ bundle, reveal, baselineArm, treatmentArm, mode, audioAssets, state, statePath, now }) {
    this.bundle = bundle;
    this.reveal = reveal;
    this.baselineArm = baselineArm;
    this.treatmentArm = treatmentArm;
    this.mode = mode;
    this.audioAssets = audioAssets;
    this.state = state;
    this.statePath = statePath;
    this.now = now;
  }

  session() {
    if (this.mode === "scalar") {
      const completedIds = new Set(this.state.judgments.map((item) => item.item_id));
      const item = this.bundle.items.find((candidate) => !completedIds.has(candidate.item_id));
      return {
        format: "composition-review.session", version: 2, mode: "scalar",
        progress: { completed: completedIds.size, total: this.bundle.items.length },
        complete: !item,
        item: !item ? null : {
          item_id: item.item_id, case_id: item.case_id, variant_id: item.variant_id,
          story_state: item.story_state, instruction: item.instruction,
          continuation: item.continuation, dimensions: item.dimensions, anchors: item.anchors,
          score_range: item.score_range, confidence_range: item.confidence_range,
        },
      };
    }
    const completed = Object.keys(this.state.judgments).length;
    const pair = this.bundle.pairs.find((item) => !Object.hasOwn(this.state.judgments, item.pair_id));
    const pairView = !pair ? null : this.mode === "audio" ? {
      pair_id: pair.pair_id, task: pair.task, draft: pair.draft, criteria: pair.criteria,
      audio_a: `/v1/audio/${encodeURIComponent(pair.candidate_a_asset)}`,
      audio_b: `/v1/audio/${encodeURIComponent(pair.candidate_b_asset)}`,
    } : {
      pair_id: pair.pair_id, task: pair.task, draft: pair.draft, criteria: pair.criteria,
      response_a: pair.candidate_a, response_b: pair.candidate_b,
    };
    return {
      format: "composition-review.session", version: 1,
      mode: this.mode,
      calibration_audio: this.mode === "audio" && this.bundle.calibration_asset
        ? `/v1/audio/${encodeURIComponent(this.bundle.calibration_asset)}` : null,
      progress: { completed, total: this.bundle.pairs.length },
      complete: !pair,
      pair: pairView,
    };
  }

  audioAsset(assetId) {
    if (this.mode !== "audio" || !this.audioAssets.has(assetId)) {
      throw new ReviewError("audio_asset_not_found", 404);
    }
    return this.audioAssets.get(assetId);
  }

  async commit(payload) {
    if (this.mode === "scalar") {
      const current = this.session().item;
      if (!current) throw new ReviewError("review_complete", 409);
      if (payload.item_id !== current.item_id) throw new ReviewError("item_order_conflict", 409);
      if (!exactKeys(payload, ["item_id", "scores", "confidence"])
          || !exactKeys(payload.scores, current.dimensions)
          || !Object.values(payload.scores).every((score) => Number.isInteger(score)
            && score >= current.score_range[0] && score <= current.score_range[1])
          || !Number.isInteger(payload.confidence)
          || payload.confidence < current.confidence_range[0]
          || payload.confidence > current.confidence_range[1]) {
        throw new ReviewError("invalid_scalar_judgment");
      }
      const timestamp = this.now().toISOString();
      this.state.judgments.push({ ...payload, committed_at: timestamp });
      this.state.updated_at = timestamp;
      if (this.state.judgments.length === this.bundle.items.length) this.state.completed_at = timestamp;
      await atomicWrite(this.statePath, this.state);
      return this.session();
    }
    const { pair_id: pairId, choice, secondary } = payload;
    if (typeof pairId !== "string" || !CHOICES.has(choice)) throw new ReviewError("invalid_judgment");
    const current = this.session().pair;
    if (!current) throw new ReviewError("review_complete", 409);
    if (current.pair_id !== pairId) throw new ReviewError("pair_order_conflict", 409);
    if (Object.hasOwn(this.state.judgments, pairId)) throw new ReviewError("judgment_locked", 409);
    const timestamp = this.now().toISOString();
    this.state.judgments[pairId] = {
      choice, secondary: validateSecondary(secondary), committed_at: timestamp,
    };
    this.state.updated_at = timestamp;
    if (Object.keys(this.state.judgments).length === this.bundle.pairs.length) {
      this.state.completed_at = timestamp;
    }
    await atomicWrite(this.statePath, this.state);
    return this.session();
  }

  results() {
    if (this.mode === "scalar") {
      if (!this.state.completed_at || this.state.judgments.length !== this.bundle.items.length) {
        throw new ReviewError("review_not_complete", 409);
      }
      return { format: "composition-review.scalar-complete", version: 1,
        bundle_digest: this.state.bundle_digest, completed_at: this.state.completed_at,
        judgment_count: this.state.judgments.length };
    }
    if (!this.state.completed_at || Object.keys(this.state.judgments).length !== this.bundle.pairs.length) {
      throw new ReviewError("review_not_complete", 409);
    }
    const preference = { [this.baselineArm]: 0, [this.treatmentArm]: 0, tie: 0 };
    const dimensions = {};
    const pairs = [];
    for (const pair of this.bundle.pairs) {
      const judgment = this.state.judgments[pair.pair_id];
      const reveal = this.reveal.get(pair.pair_id);
      const winningArm = judgment.choice === "tie" ? "tie"
        : judgment.choice === "a" ? reveal.candidate_a_arm : reveal.candidate_b_arm;
      preference[winningArm] += 1;
      for (const [dimension, scores] of Object.entries(judgment.secondary)) {
        const bucket = dimensions[dimension] ?? { [this.baselineArm]: [], [this.treatmentArm]: [] };
        bucket[reveal.candidate_a_arm].push(scores.a);
        bucket[reveal.candidate_b_arm].push(scores.b);
        dimensions[dimension] = bucket;
      }
      pairs.push({
        pair_id: pair.pair_id, choice: judgment.choice, winning_arm: winningArm,
        candidate_a_arm: reveal.candidate_a_arm, candidate_b_arm: reveal.candidate_b_arm,
      });
    }
    const secondaryMeans = Object.fromEntries(Object.entries(dimensions).map(([dimension, arms]) => [
      dimension,
      Object.fromEntries(Object.entries(arms).map(([arm, values]) => [
        arm, values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null,
      ])),
    ]));
    return {
      format: "composition-review.results", version: 1,
      bundle_digest: this.state.bundle_digest, completed_at: this.state.completed_at,
      baseline_arm: this.baselineArm, treatment_arm: this.treatmentArm,
      preference, secondary_means: secondaryMeans, pairs,
    };
  }
}
