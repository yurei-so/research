import { createHash } from "node:crypto";

export const schema = "labnote-tldr/v1";
export const sourceHash = (source) => `sha256:${createHash("sha256").update(source).digest("hex")}`;
const normalizedText = (value) => value.replace(/\s+/g, " ").trim();

export function validateCandidate(source, candidate, options = {}) {
  const maximum = options.maximumOrientationCharacters ?? 420;
  const errors = [];
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) errors.push("candidate must be an object");
  if (candidate?.schema !== schema) errors.push(`schema must be ${schema}`);
  for (const field of ["orientation", "finding", "limitations", "negative_evidence", "evidence_quotes", "generation"]) {
    if (!Object.hasOwn(candidate ?? {}, field)) errors.push(`missing ${field}`);
  }
  if (typeof candidate?.orientation !== "string" || !candidate.orientation.trim()) errors.push("orientation must be non-empty text");
  else if (candidate.orientation.length > maximum) errors.push(`orientation exceeds ${maximum} characters`);
  if (typeof candidate?.finding !== "string" || !candidate.finding.trim()) errors.push("finding must be non-empty text");
  for (const field of ["limitations", "negative_evidence", "evidence_quotes"]) {
    if (!Array.isArray(candidate?.[field]) || candidate[field].some((value) => typeof value !== "string" || !value.trim())) errors.push(`${field} must be a text array`);
  }
  const normalizedSource = normalizedText(source);
  for (const quote of candidate?.evidence_quotes ?? []) if (!normalizedSource.includes(normalizedText(quote))) errors.push(`unsupported evidence quote: ${quote}`);
  if (!candidate?.generation || typeof candidate.generation !== "object" || Array.isArray(candidate.generation)) errors.push("generation must be an object");
  else for (const field of ["provider", "model", "prompt_version", "generated_at"]) {
    if (typeof candidate.generation[field] !== "string" || !candidate.generation[field].trim()) errors.push(`generation.${field} must be non-empty text`);
  }
  if (candidate?.no_new_claims !== true) errors.push("no_new_claims must be true");
  return {
    valid: errors.length === 0,
    status: errors.length === 0 ? "ready-for-human-review" : "rejected-before-review",
    errors,
    provenance: { source_hash: sourceHash(source), apparatus_version: "0.1.0", schema }
  };
}
