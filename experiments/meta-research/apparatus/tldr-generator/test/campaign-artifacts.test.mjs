import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { validateCandidate } from "../src/validator.mjs";

const repository = path.resolve(import.meta.dirname, "../../../../..");
const experiment = path.join(repository, "experiments/meta-research/experiments/meta-research-001");
const artifacts = path.join(experiment, "artifacts");
const sources = new Map([
  ["composition-001", "experiments/composition-pipeline/docs/labnotes/001-prompted-constrained-editing-baseline.md"],
  ["prosody-018", "experiments/conversation-prosody-pipeline/docs/labnotes/labnote-018-conversation-conditioned-two-speaker-pilot.md"],
  ["composition-009", "experiments/composition-pipeline/docs/labnotes/009-readiness-gated-bounded-span-repair.md"],
  ["prosody-014", "experiments/conversation-prosody-pipeline/docs/labnotes/labnote-014-instruction-form-ablation.md"],
  ["prosody-017", "experiments/conversation-prosody-pipeline/docs/labnotes/labnote-017-multi-utterance-candidate-pool.md"],
  ["voxel-guidance-004", "experiments/voxel-guidance/docs/labnotes/voxel-guidance-004-machine-native-state-encoding.md"],
  ["composition-004", "experiments/composition-pipeline/docs/labnotes/004-changed-output-optional-editor-campaign.md"],
  ["prosody-011", "experiments/conversation-prosody-pipeline/docs/labnotes/labnote-011-reproducible-synthetic-rerun.md"],
]);
const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8"));

test("every frozen candidate retains a reproducible validator receipt", () => {
  const protocol = readJson(path.join(experiment, "frozen-protocol.json"));
  assert.deepEqual(protocol.frozen_corpus.map(({ id }) => id), [...sources.keys()]);
  for (const [id, relativeSource] of sources) {
    const source = fs.readFileSync(path.join(repository, relativeSource), "utf8");
    const candidate = readJson(path.join(artifacts, id, "candidate.json"));
    const stored = readJson(path.join(artifacts, id, "validator-result.json"));
    assert.deepEqual(validateCandidate(source, candidate, {
      maximumOrientationCharacters: protocol.maximum_orientation_characters,
    }), stored, `${id} validator receipt drifted`);
  }
});

test("shadow campaign stays blocked while human reviews are pending", () => {
  const status = readJson(path.join(artifacts, "campaign-status.json"));
  assert.equal(status.public_write_allowed, false);
  assert.equal(status.status, "awaiting-human-review");
  assert.equal(status.promotion_gate_evaluated, false);
  assert.equal(status.human_reviews_complete, 0);
  for (const id of sources.keys()) {
    const review = readJson(path.join(artifacts, id, "human-review.json"));
    assert.equal(review.status, "awaiting-human-review");
    assert.equal(review.reviewer, null);
    assert.equal(review.human_decision, null);
    assert.equal(review.reviewer_notes, null);
    assert.ok(Object.values(review.human_scores).every((score) => score === null));
  }
});
