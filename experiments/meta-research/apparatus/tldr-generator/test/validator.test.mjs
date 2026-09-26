import test from "node:test";
import assert from "node:assert/strict";
import { validateCandidate, validateCrayonCandidate, validateOrientationCandidate } from "../src/validator.mjs";

const source = "# Note\n\n## Result\nThe treatment did not improve accuracy.\n\n## Limitations\nOnly six trials were run.";
const candidate = {
  schema: "labnote-tldr/v1",
  orientation: "A six-trial test found no accuracy improvement.",
  finding: "The treatment did not improve accuracy.",
  limitations: ["Only six trials were run."],
  negative_evidence: ["No accuracy improvement was observed."],
  evidence_quotes: ["The treatment did not improve accuracy.", "Only six trials were run."],
  no_new_claims: true,
  generation: { provider: "fixture", model: "fixture", prompt_version: "meta-research-001/v1", generated_at: "2026-09-21T00:00:00Z" }
};

test("accepts a grounded shadow candidate and adds provenance", () => {
  const result = validateCandidate(source, candidate);
  assert.equal(result.valid, true);
  assert.equal(result.status, "ready-for-human-review");
  assert.match(result.provenance.source_hash, /^sha256:[0-9a-f]{64}$/);
});

test("does not misrepresent structural validation as factual review", () => {
  const result = validateCandidate(source, { ...candidate, finding: "An unreviewed paraphrase." });
  assert.equal(result.valid, true);
  assert.equal(result.status, "ready-for-human-review");
});

test("rejects invented quotations and missing claim acknowledgement", () => {
  const result = validateCandidate(source, { ...candidate, evidence_quotes: ["Invented evidence"], no_new_claims: false });
  assert.equal(result.valid, false);
  assert.ok(result.errors.some((error) => error.includes("unsupported evidence quote")));
  assert.ok(result.errors.includes("no_new_claims must be true"));
});

test("accepts exact source quotations across Markdown line wrapping", () => {
  const wrapped = source.replace("did not improve", "did not\nimprove");
  const result = validateCandidate(wrapped, candidate);
  assert.equal(result.valid, true);
});

const orientationCandidate = {
  schema: "labnote-orientation/v2",
  orientation: {
    question_or_cause: "The study asked whether the treatment improves accuracy.",
    effect: "Six trials found no improvement, so the treatment is not ready to adopt."
  },
  no_new_claims: true,
  generation: { provider: "fixture", model: "fixture", prompt_version: "meta-research-001/v2", generated_at: "2026-09-26T00:00:00Z" }
};

test("accepts exactly two compact orientation sentences", () => {
  const result = validateOrientationCandidate(source, orientationCandidate);
  assert.equal(result.valid, true);
  assert.equal(result.provenance.schema, "labnote-orientation/v2");
});

test("v2 does not require the model to extract citations", () => {
  const result = validateOrientationCandidate(source, orientationCandidate);
  assert.equal(result.valid, true);
  assert.equal(Object.hasOwn(orientationCandidate, "evidence_quotes"), false);
});

test("rejects a compressed paragraph in either orientation slot", () => {
  const result = validateOrientationCandidate(source, {
    ...orientationCandidate,
    orientation: {
      ...orientationCandidate.orientation,
      effect: "Six trials found no improvement. The sample was small. More work is needed."
    }
  });
  assert.equal(result.valid, false);
  assert.ok(result.errors.includes("orientation.effect must contain exactly one sentence"));
});

test("rejects an overlong two-sentence orientation", () => {
  const result = validateOrientationCandidate(source, orientationCandidate, { maximumOrientationCharacters: 60 });
  assert.equal(result.valid, false);
  assert.ok(result.errors.includes("rendered orientation exceeds 60 characters"));
});

test("v3 accepts conversational two-sentence language", () => {
  const result = validateCrayonCandidate(source, {
    ...orientationCandidate,
    schema: "labnote-orientation/v3",
    orientation: {
      question_or_cause: "We asked whether the treatment would improve accuracy.",
      effect: "It did not help in six trials, so we do not have a reason to use it yet."
    },
    generation: { ...orientationCandidate.generation, prompt_version: "meta-research-001/v3" }
  });
  assert.equal(result.valid, true);
  assert.deepEqual(result.warnings, []);
});

test("v3 warns on tiny-abstract language without pretending it is structurally invalid", () => {
  const result = validateCrayonCandidate(source, {
    ...orientationCandidate,
    schema: "labnote-orientation/v3",
    orientation: {
      question_or_cause: "We ran an ablation of the bounded-span intervention.",
      effect: "It was directionally correct but did not provide causal evidence."
    },
    generation: { ...orientationCandidate.generation, prompt_version: "meta-research-001/v3" }
  });
  assert.equal(result.valid, true);
  assert.ok(result.warnings.length >= 3);
});
