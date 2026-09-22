#!/usr/bin/env node
import fs from "node:fs";
import { validateCandidate } from "./validator.mjs";

const [command, ...args] = process.argv.slice(2);
const value = (name) => { const index = args.indexOf(name); return index < 0 ? null : args[index + 1]; };
if (command !== "validate" || !value("--source") || !value("--candidate")) {
  console.error("usage: labnote-tldr validate --source LABNOTE.md --candidate CANDIDATE.json");
  process.exitCode = 2;
} else {
  const source = fs.readFileSync(value("--source"), "utf8");
  const candidate = JSON.parse(fs.readFileSync(value("--candidate"), "utf8"));
  const result = validateCandidate(source, candidate);
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  if (!result.valid) process.exitCode = 1;
}
