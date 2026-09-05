import assert from "node:assert/strict";
import { mkdtemp, readFile, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { ReviewError, ReviewStore } from "../src/storage.mjs";
import { writeAudioFixture, writeFixture } from "./helpers.mjs";

test("review stays blinded, locks judgments, resumes, then reveals", async () => {
  const directory = await mkdtemp(join(tmpdir(), "composition-review-"));
  const { bundlePath, keyPath } = await writeFixture(directory);
  const statePath = join(directory, "state/judgments.json");
  let tick = 0;
  const now = () => new Date(1_800_000_000_000 + tick++ * 1000);
  const store = await ReviewStore.open({ bundlePath, keyPath, statePath, now });
  assert.equal(
    [...store.reveal.values()].filter((item) => item.candidate_a_arm === "direct_rewrite").length,
    1,
  );
  const first = store.session();
  assert.equal(first.progress.completed, 0);
  assert.equal(first.pair.pair_id, "pair-one");
  assert.equal(JSON.stringify(first).includes("direct_rewrite"), false);
  await assert.rejects(
    store.commit({ pair_id: "pair-two", choice: "a" }),
    (error) => error instanceof ReviewError && error.code === "pair_order_conflict",
  );
  await store.commit({ pair_id: "pair-one", choice: "b", secondary: { clarity: { a: 3, b: 5 } } });
  assert.throws(
    () => store.results(),
    (error) => error.code === "review_not_complete",
  );

  const resumed = await ReviewStore.open({ bundlePath, keyPath, statePath, now });
  assert.equal(resumed.session().pair.pair_id, "pair-two");
  await resumed.commit({ pair_id: "pair-two", choice: "a" });
  const results = resumed.results();
  assert.equal(results.preference.direct_rewrite + results.preference.schema_revision, 2);
  assert.equal(results.preference.tie, 0);
  assert.equal(
    results.secondary_means.clarity.direct_rewrite + results.secondary_means.clarity.schema_revision,
    8,
  );
  assert.equal((await stat(join(directory, "state"))).mode & 0o777, 0o700);
  assert.equal((await stat(statePath)).mode & 0o777, 0o600);
  const persisted = JSON.parse(await readFile(statePath, "utf8"));
  assert.ok(persisted.completed_at);
});

test("bundle changes cannot reuse judgments or reveal key", async () => {
  const directory = await mkdtemp(join(tmpdir(), "composition-review-"));
  const { bundlePath, keyPath, bundle } = await writeFixture(directory);
  const statePath = join(directory, "judgments.json");
  await ReviewStore.open({ bundlePath, keyPath, statePath });
  bundle.pairs[0].candidate_a = "Tampered";
  await writeFile(bundlePath, JSON.stringify(bundle));
  await assert.rejects(
    ReviewStore.open({ bundlePath, keyPath, statePath }),
    (error) => error.code === "invalid_review_key",
  );
});

test("review supports a bounded alternate treatment arm without pre-reveal disclosure", async () => {
  const directory = await mkdtemp(join(tmpdir(), "composition-review-"));
  const { bundlePath, keyPath } = await writeFixture(directory, "optional_editor");
  const store = await ReviewStore.open({
    bundlePath, keyPath, statePath: join(directory, "judgments.json"),
  });
  assert.equal(JSON.stringify(store.session()).includes("optional_editor"), false);
  await store.commit({ pair_id: "pair-one", choice: "a" });
  await store.commit({ pair_id: "pair-two", choice: "b" });
  const results = store.results();
  assert.equal(results.treatment_arm, "optional_editor");
  assert.equal(results.preference.direct_rewrite + results.preference.optional_editor, 2);
});

test("audio review verifies assets, stays blinded, and reveals generic arms", async () => {
  const directory = await mkdtemp(join(tmpdir(), "composition-review-audio-"));
  const { bundlePath, keyPath } = await writeAudioFixture(directory);
  const store = await ReviewStore.open({
    bundlePath, keyPath, assetRoot: directory, statePath: join(directory, "judgments.json"),
  });
  const session = store.session();
  assert.equal(session.mode, "audio");
  assert.equal(session.calibration_audio, "/v1/audio/clip-one");
  assert.equal(session.pair.audio_a.startsWith("/v1/audio/"), true);
  assert.equal(JSON.stringify(session).includes("gold_ir"), false);
  assert.equal(store.audioAsset("clip-one").mediaType, "audio/wav");
  await store.commit({ pair_id: "audio-pair", choice: "a", secondary: { naturalness: { a: 5, b: 3 } } });
  const results = store.results();
  assert.equal(results.baseline_arm, "gold_ir");
  assert.equal(results.treatment_arm, "swapped_ir");
  assert.equal(results.preference.gold_ir + results.preference.swapped_ir, 1);
});

test("audio review rejects tampered assets", async () => {
  const directory = await mkdtemp(join(tmpdir(), "composition-review-audio-"));
  const { bundlePath, keyPath } = await writeAudioFixture(directory);
  await writeFile(join(directory, "clip-one.wav"), "tampered");
  await assert.rejects(
    ReviewStore.open({ bundlePath, keyPath, assetRoot: directory,
      statePath: join(directory, "judgments.json") }),
    (error) => error.code === "review_asset_digest_mismatch",
  );
});
