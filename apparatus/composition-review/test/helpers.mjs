import { createHash } from "node:crypto";
import { writeFile } from "node:fs/promises";

function canonical(value) {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value).replace(/[\u007f-\uffff]/g, (character) =>
      `\\u${character.charCodeAt(0).toString(16).padStart(4, "0")}`);
  }
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  return `{${Object.keys(value).sort().map((key) => `${canonical(key)}:${canonical(value[key])}`).join(",")}}`;
}

export function fixture(treatmentArm = "schema_revision") {
  const bundle = {
    format: "composition-pipeline.blinded-review", version: 1,
    campaign_digest: "campaign-digest",
    pairs: [
      { pair_id: "pair-one", case_id: "case-1", prompt_style: "concise", repetition: 0,
        task: "Improve this.", draft: "Rough.", candidate_a: "Alpha.", candidate_b: "Beta.",
        criteria: ["clarity"] },
      { pair_id: "pair-two", case_id: "case-2", prompt_style: "preserve", repetition: 0,
        task: "Fix this.", draft: "Wrong.", candidate_a: "Gamma.", candidate_b: "Delta.",
        criteria: ["clarity"] },
    ],
  };
  const key = {
    format: "composition-pipeline.blinded-review-key", version: 1,
    campaign_digest: bundle.campaign_digest,
    review_bundle_digest: createHash("sha256").update(canonical(bundle)).digest("hex"),
    pairs: [
      { pair_id: "pair-one", candidate_a_arm: "direct_rewrite", candidate_b_arm: treatmentArm },
      { pair_id: "pair-two", candidate_a_arm: treatmentArm, candidate_b_arm: "direct_rewrite" },
    ],
  };
  return { bundle, key };
}

export async function writeFixture(directory, treatmentArm) {
  const { bundle, key } = fixture(treatmentArm);
  const bundlePath = `${directory}/bundle.json`; const keyPath = `${directory}/key.json`;
  await Promise.all([
    writeFile(bundlePath, JSON.stringify(bundle)), writeFile(keyPath, JSON.stringify(key)),
  ]);
  return { bundlePath, keyPath, bundle, key };
}

export async function writeAudioFixture(directory) {
  const first = Buffer.from("RIFFaudio-one"); const second = Buffer.from("RIFFaudio-two");
  const assets = [
    { asset_id: "clip-one", file_name: "clip-one.wav",
      sha256: createHash("sha256").update(first).digest("hex"), media_type: "audio/wav" },
    { asset_id: "clip-two", file_name: "clip-two.wav",
      sha256: createHash("sha256").update(second).digest("hex"), media_type: "audio/wav" },
  ];
  const bundle = {
    format: "composition-pipeline.blinded-review", version: 2,
    campaign_digest: "audio-campaign", mode: "audio", calibration_asset: "clip-one", assets,
    pairs: [{ pair_id: "audio-pair", case_id: "case-a", prompt_style: "listener", repetition: 0,
      task: "Which delivery better matches the context?", draft: "The same words.",
      candidate_a_asset: "clip-one", candidate_b_asset: "clip-two", criteria: ["naturalness"] }],
  };
  const key = {
    format: "composition-pipeline.blinded-review-key", version: 2,
    campaign_digest: bundle.campaign_digest,
    review_bundle_digest: createHash("sha256").update(canonical(bundle)).digest("hex"),
    baseline_arm: "gold_ir", treatment_arm: "swapped_ir",
    pairs: [{ pair_id: "audio-pair", candidate_a_arm: "gold_ir", candidate_b_arm: "swapped_ir" }],
  };
  const bundlePath = `${directory}/audio-bundle.json`; const keyPath = `${directory}/audio-key.json`;
  await Promise.all([
    writeFile(bundlePath, JSON.stringify(bundle)), writeFile(keyPath, JSON.stringify(key)),
    writeFile(`${directory}/clip-one.wav`, first), writeFile(`${directory}/clip-two.wav`, second),
  ]);
  return { bundlePath, keyPath, bundle, key, first, second };
}
