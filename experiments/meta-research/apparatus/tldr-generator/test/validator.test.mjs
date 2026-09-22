import test from "node:test";
import assert from "node:assert/strict";
import { validateCandidate } from "../src/validator.mjs";

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
