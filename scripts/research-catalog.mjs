#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { collectCatalog, escapeHtml, renderMarkdown } from "./research-catalog-lib.mjs";

const root = path.resolve(import.meta.dirname, "..");
const mode = process.argv[2] ?? "check";
if (!new Set(["check", "build"]).has(mode)) throw new Error("usage: node scripts/research-catalog.mjs [check|build]");

const { records, manifest } = collectCatalog(root);
if (mode === "check") {
  console.log(`Validated ${records.length} labnotes; ${manifest.labnotes.length} eligible for publication.`);
  process.exit(0);
}

const output = path.join(root, "dist");
fs.rmSync(output, { recursive: true, force: true });
fs.mkdirSync(path.join(output, "assets"), { recursive: true });
for (const name of ["index.html", "styles.css", "app.js", "favicon.png"]) {
  const source = path.join(root, "site", name);
  const destination = ["index.html", "favicon.png"].includes(name) ? path.join(output, name) : path.join(output, "assets", name);
  fs.copyFileSync(source, destination);
}
fs.writeFileSync(path.join(output, "research-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
fs.writeFileSync(path.join(output, ".nojekyll"), "");

for (const record of records.filter((entry) => entry.metadata.publish)) {
  const note = manifest.labnotes.find((entry) => entry.id === record.metadata.id);
  const directory = path.join(output, "labnotes", note.id);
  fs.mkdirSync(directory, { recursive: true });
  const tags = note.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("");
  const title = escapeHtml(record.metadata.title);
  const question = escapeHtml(record.metadata.question);
  const page = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'">
<meta name="description" content="${question}"><title>${escapeHtml(record.metadata.id)} — Yurei Research</title><link rel="icon" href="../../favicon.png" type="image/png">
<link rel="stylesheet" href="../../assets/styles.css"></head><body>
<header class="terminal-bar"><a class="wordmark" href="../../"><img src="../../favicon.png" alt="">YUREI RESEARCH</a><span>RESEARCH LIBRARY</span></header>
<main class="note-shell"><a class="back" href="../../">← Return to research library</a>
<article class="labnote"><header class="note-header"><div class="eyebrow">LABNOTE / ${escapeHtml(note.family)}</div><h1>${title}</h1>
<div class="note-vitals"><span>${note.id}</span><span>${note.date}</span><span data-outcome="${note.outcome}">${note.outcome}</span><span>${note.status}</span></div>
<p class="question">${question}</p><div class="tags">${tags}</div></header>
<div class="note-body">${renderMarkdown(record.body)}</div></article></main>
<footer><span>YUREI RESEARCH</span><span>REV ${manifest.source_revision}</span></footer></body></html>`;
  fs.writeFileSync(path.join(directory, "index.html"), page);
}
console.log(`Built public research library with ${manifest.labnotes.length} labnotes in dist/.`);
