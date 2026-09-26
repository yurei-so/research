import { createHash } from "node:crypto";

export const schema = "labnote-tldr/v1";
export const orientationSchema = "labnote-orientation/v2";
export const crayonSchema = "labnote-orientation/v3";
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

const sentenceCount = (value) => {
  if (typeof value !== "string" || !value.trim()) return 0;
  return [...new Intl.Segmenter("en", { granularity: "sentence" }).segment(value.trim())]
    .filter(({ segment }) => segment.trim()).length;
};

export function validateOrientationCandidate(source, candidate, options = {}) {
  const maximum = options.maximumOrientationCharacters ?? 320;
  const errors = [];
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) errors.push("candidate must be an object");
  if (candidate?.schema !== orientationSchema) errors.push(`schema must be ${orientationSchema}`);
  for (const field of ["orientation", "generation"]) {
    if (!Object.hasOwn(candidate ?? {}, field)) errors.push(`missing ${field}`);
  }
  if (!candidate?.orientation || typeof candidate.orientation !== "object" || Array.isArray(candidate.orientation)) {
    errors.push("orientation must be an object");
  } else {
    for (const field of ["question_or_cause", "effect"]) {
      const value = candidate.orientation[field];
      if (typeof value !== "string" || !value.trim()) errors.push(`orientation.${field} must be non-empty text`);
      else if (sentenceCount(value) !== 1) errors.push(`orientation.${field} must contain exactly one sentence`);
    }
    const rendered = `${candidate.orientation.question_or_cause ?? ""} ${candidate.orientation.effect ?? ""}`.trim();
    if (rendered.length > maximum) errors.push(`rendered orientation exceeds ${maximum} characters`);
  }
  if (!candidate?.generation || typeof candidate.generation !== "object" || Array.isArray(candidate.generation)) {
    errors.push("generation must be an object");
  } else {
    for (const field of ["provider", "model", "prompt_version", "generated_at"]) {
      if (typeof candidate.generation[field] !== "string" || !candidate.generation[field].trim()) errors.push(`generation.${field} must be non-empty text`);
    }
  }
  if (candidate?.no_new_claims !== true) errors.push("no_new_claims must be true");
  return {
    valid: errors.length === 0,
    status: errors.length === 0 ? "ready-for-human-review" : "rejected-before-review",
    errors,
    provenance: { source_hash: sourceHash(source), apparatus_version: "0.2.0", schema: orientationSchema }
  };
}

const crayonJargon = [
  "ablation", "bounded-span", "causal evidence", "directionally correct",
  "frozen holdout", "intervention", "preregistered gate", "transfer probe"
];
const wordCount = (value) => value.trim().split(/\s+/u).filter(Boolean).length;

export function validateCrayonCandidate(source, candidate, options = {}) {
  const normalized = candidate && typeof candidate === "object"
    ? { ...candidate, schema: orientationSchema }
    : candidate;
  const result = validateOrientationCandidate(source, normalized, options);
  result.errors = result.errors.filter((error) => !error.startsWith("schema must be "));
  if (candidate?.schema !== crayonSchema) result.errors.unshift(`schema must be ${crayonSchema}`);
  result.valid = result.errors.length === 0;
  result.status = result.valid ? "ready-for-human-review" : "rejected-before-review";
  result.provenance = { source_hash: sourceHash(source), apparatus_version: "0.3.0", schema: crayonSchema };
  const sentences = [candidate?.orientation?.question_or_cause, candidate?.orientation?.effect]
    .filter((value) => typeof value === "string");
  const rendered = sentences.join(" ");
  const warnings = [];
  sentences.forEach((sentence, index) => {
    if (wordCount(sentence) > 30) warnings.push(`sentence ${index + 1} exceeds 30 words`);
  });
  if (wordCount(rendered) > 55) warnings.push("orientation exceeds 55 words");
  for (const term of crayonJargon) {
    if (rendered.toLowerCase().includes(term)) warnings.push(`paper-language term may need translation: ${term}`);
  }
  if ((rendered.match(/\([^)]*\)/g) ?? []).length > 1) warnings.push("orientation uses more than one parenthetical");
  const acronyms = (rendered.match(/\b[A-Z]{2,}\b/g) ?? []).filter((value) => value !== "AI");
  if (acronyms.length > 0) warnings.push(`unexplained acronym may need translation: ${[...new Set(acronyms)].join(", ")}`);
  result.warnings = warnings;
  return result;
}
