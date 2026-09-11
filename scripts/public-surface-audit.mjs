#!/usr/bin/env node
// SPDX-License-Identifier: AGPL-3.0-only

import fs from "node:fs";
import path from "node:path";

const rules = [
  ["numbered internal note citation", /\bWhiteboard(?:\s+(?:ideas?\s+)?|\s*#)\d/i],
  ["private RFC1918 address", /\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b/],
  ["owner-specific home path", /\/home\/alu52\b/],
  ["private workstation hostname", /\bmpaiServer[-A-Za-z0-9.]*/i],
  ["internal execution UUID", /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i],
  ["private service or repository name", /\b(?:roostd|roost-sso|roost-console|agent[- ]runtime|chat[- ]runtime|agent[- ]companion|access[- ]server|personal[- ]access[- ]server|mpai(?:server)?|mamagpt|codecat|eden)\b/i],
  ["private actor identity", /\bactor:openai:[a-z0-9_-]+\b/i],
  ["Context Server operation name", /\b(?:request_actor_session|bind_sso_session|send_direct_context|list_direct_inbox|acknowledge_direct_context)\b/],
];
const excluded = new Set(["scripts/public-surface-audit.mjs"]);
const excludedDirectories = new Set([".git", ".gradle", ".pytest_cache", ".venv", "node_modules", "__pycache__"]);
const binary = /\.(?:bin|blend1?|gif|ico|jpe?g|jar|mp3|mp4|ogg|pdf|png|ttf|wav|webp|woff2?|zip)$/i;
const files = [];
const walk = (directory = ".") => {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name).replace(/^\.\//, "");
    if (entry.isDirectory()) {
      if (!excludedDirectories.has(entry.name)) walk(file);
    } else if (entry.isFile()) files.push(file);
  }
};
walk();
const findings = [];

for (const file of files) {
  if (excluded.has(file) || binary.test(file)) continue;
  const content = fs.readFileSync(file, "utf8");
  content.split("\n").forEach((line, index) => {
    for (const [label, pattern] of rules) if (pattern.test(line)) findings.push(`${file}:${index + 1}: ${label}`);
  });
}

if (findings.length) {
  console.error("Public-surface privacy policy failed:\n" + findings.join("\n"));
  process.exitCode = 1;
} else {
  console.log(`Public-surface privacy policy passed across ${files.length} repository files.`);
}
