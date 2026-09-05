#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = path.resolve(import.meta.dirname, "..");
const mode = process.argv[2] ?? "check";
if (!new Set(["apply", "check"]).has(mode)) {
  throw new Error("usage: node scripts/labnote-metadata.mjs [apply|check]");
}

const families = {
  "narrative-steering": {
    directory: "experiments/narrative-steering/docs/labnotes",
    pattern: /^narrative-steering-(\d{3})-.*\.md$/,
    dates: { "001": "2026-09-05" },
    statuses: { "001": "complete" },
    outcomes: { "001": "positive" },
    lineage: { "001": [] },
    baseTags: ["human-review", "model-comparison", "narrative-steering", "story-engine"],
  },
  prosody: {
    directory: "experiments/conversation-prosody-pipeline/docs/labnotes",
    pattern: /^labnote-(\d{3})-.*\.md$/,
    dates: {
      "001": "2026-06-27", "002": "2026-07-01", "003": "2026-07-01",
      "004": "2026-08-13", "005": "2026-08-13", "006": "2026-08-15",
      "007": "2026-08-15", "008": "2026-08-23", "009": "2026-08-23",
      "010": "2026-08-23", "011": "2026-08-23",
    },
    statuses: { "004": "awaiting-review", "008": "planned" },
    outcomes: {
      "001": "positive", "002": "negative", "003": "inconclusive",
      "004": "pending", "005": "negative", "006": "negative",
      "007": "inconclusive", "008": "pending", "009": "mixed",
      "010": "negative", "011": "inconclusive",
    },
    lineage: {
      "001": [], "002": ["prosody-001"], "003": ["prosody-002"],
      "004": ["prosody-003"], "005": ["prosody-004"],
      "006": ["prosody-005"], "007": ["prosody-006"],
      "008": ["prosody-004"], "009": ["prosody-008"],
      "010": ["prosody-009"], "011": ["prosody-003"],
    },
    baseTags: ["conversational-prosody"],
  },
  composition: {
    directory: "experiments/composition-pipeline/docs/labnotes",
    pattern: /^(\d{3})-.*\.md$/,
    dates: {
      "001": "2026-08-22", "002": "2026-08-22", "003": "2026-08-23",
      "004": "2026-08-23", "005": "2026-08-23", "006": "2026-08-23",
    },
    statuses: {},
    outcomes: {
      "001": "positive", "002": "inconclusive", "003": "negative",
      "004": "inconclusive", "005": "negative", "006": "mixed",
    },
    lineage: Object.fromEntries(Array.from({ length: 6 }, (_, index) => {
      const number = String(index + 1).padStart(3, "0");
      return [number, index === 0 ? [] : [`composition-${String(index).padStart(3, "0")}`]];
    })),
    baseTags: ["composition", "human-review"],
  },
  zenith: {
    directory: "experiments/zenith-vision/docs/labnotes",
    pattern: /^(\d{3})-.*\.md$/,
    dates: Object.fromEntries(Array.from({ length: 17 }, (_, index) => {
      const number = String(index + 1).padStart(3, "0");
      return [number, index < 11 ? "2026-08-24" : "2026-08-25"];
    })),
    statuses: {},
    outcomes: {
      "001": "negative", "002": "negative", "003": "negative",
      "004": "mixed", "005": "positive", "006": "positive",
      "007": "mixed", "008": "negative", "009": "negative",
      "010": "negative", "011": "positive", "012": "negative",
      "013": "mixed", "014": "positive", "015": "mixed",
      "016": "positive", "017": "negative",
    },
    lineage: Object.fromEntries(Array.from({ length: 17 }, (_, index) => {
      const number = String(index + 1).padStart(3, "0");
      return [number, index === 0 ? [] : [`zenith-${String(index).padStart(3, "0")}`]];
    })),
    baseTags: ["guild-wars-2", "computer-vision", "privacy"],
  },
};

const questionOverrides = {
  "prosody-008": "Can post-hoc focus control create audible, natural emphasis before spending human-review labor?",
  "prosody-009": "Can native Kokoro lexical stress produce natural audio and validate the intended focus mapping?",
  "prosody-010": "Does native lexical stress create reliable directional discourse prominence?",
};

const keywordTags = [
  [/(synthetic|kokoro)/i, "synthetic-audio"],
  [/(real-media|real audio)/i, "real-audio"],
  [/(specul|familiarity|subscription)/i, "speculative-execution"],
  [/(holdout|validation)/i, "holdout"],
  [/(review|listener)/i, "blinded-review"],
  [/(transfer|classifier|panel)/i, "panel-recognition"],
  [/(editing|editor|revision|repair)/i, "revision"],
  [/(deduplic|stochastic)/i, "deduplication"],
  [/(stress|focus|prominence)/i, "prosody-control"],
  [/(provenance|reproducible)/i, "provenance"],
];

function titleFrom(body) {
  const heading = body.match(/^#\s+(.+)$/m)?.[1];
  if (!heading) throw new Error("missing level-one title");
  return heading
    .replace(/^Lab note:\s*/i, "")
    .replace(/^Labnote\s+\d{3}:?\s*/i, "")
    .trim();
}

function questionFrom(body, id) {
  if (questionOverrides[id]) return questionOverrides[id];
  const heading = body.match(/^## (?:Question|Hypothesis)\s*$/m);
  if (!heading || heading.index === undefined) {
    throw new Error(`${id}: missing Question or Hypothesis section`);
  }
  const start = heading.index + heading[0].length;
  const remainder = body.slice(start).replace(/^\s+/, "");
  const nextHeading = remainder.search(/^##\s/m);
  const section = nextHeading === -1 ? remainder : remainder.slice(0, nextHeading);
  return section.replace(/\s+/g, " ").trim();
}

function frontMatter(metadata) {
  return [
    "---",
    "schema_version: 1",
    `id: ${metadata.id}`,
    `title: ${JSON.stringify(metadata.title)}`,
    `date: ${metadata.date}`,
    `status: ${metadata.status}`,
    `outcome: ${metadata.outcome}`,
    `question: ${JSON.stringify(metadata.question)}`,
    `tags: ${JSON.stringify(metadata.tags)}`,
    `lineage: ${JSON.stringify(metadata.lineage)}`,
    "publish: true",
    "---",
    "",
  ].join("\n");
}

const allowedStatuses = new Set(["planned", "running", "awaiting-review", "complete", "aborted"]);
const allowedOutcomes = new Set(["positive", "negative", "mixed", "inconclusive", "pending", "not-applicable"]);
const seenIds = new Set();
let count = 0;

for (const [familyName, family] of Object.entries(families)) {
  const directory = path.join(root, family.directory);
  for (const name of fs.readdirSync(directory).sort()) {
    const match = name.match(family.pattern);
    if (!match) continue;
    const number = match[1];
    const id = `${familyName}-${number}`;
    const file = path.join(directory, name);
    let body = fs.readFileSync(file, "utf8");
    const existing = body.match(/^---\n([\s\S]*?)\n---\n/);
    if (existing) body = body.slice(existing[0].length).replace(/^\n/, "");
    const title = titleFrom(body);
    const outcome = family.outcomes[number];
    const status = family.statuses[number] ?? "complete";
    const date = family.dates[number];
    const lineage = family.lineage[number];
    if (!date || !outcome || !lineage) throw new Error(`${id}: incomplete catalog entry`);
    if (!allowedStatuses.has(status)) throw new Error(`${id}: invalid status ${status}`);
    if (!allowedOutcomes.has(outcome)) throw new Error(`${id}: invalid outcome ${outcome}`);
    if (seenIds.has(id)) throw new Error(`${id}: duplicate id`);
    seenIds.add(id);
    const tags = new Set(family.baseTags);
    for (const [pattern, tag] of keywordTags) if (pattern.test(`${title}\n${body.slice(0, 1200)}`)) tags.add(tag);
    if (outcome !== "pending") tags.add(`${outcome}-result`);
    const metadata = {
      id, title, date, status, outcome,
      question: questionFrom(body, id),
      tags: [...tags].sort(),
      lineage,
    };
    const expected = frontMatter(metadata);
    if (mode === "apply") {
      fs.writeFileSync(file, `${expected}${body}`);
    } else if (!existing || existing[0] !== expected) {
      throw new Error(`${path.relative(root, file)}: metadata is absent or stale; run with apply`);
    }
    count += 1;
  }
}

if (count !== 35) throw new Error(`expected 35 labnotes, found ${count}`);
console.log(`${mode === "apply" ? "Applied" : "Validated"} metadata for ${count} labnotes.`);
