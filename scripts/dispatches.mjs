// SPDX-License-Identifier: AGPL-3.0-only

import fs from "node:fs";
import path from "node:path";
import { escapeHtml, renderMarkdown } from "./research-catalog-lib.mjs";

const allowedKeys = new Set(["schema_version", "id", "title", "date", "status", "lede", "tags", "related_labnotes", "publish"]);
const tagPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const idPattern = /^dispatch-\d{3}$/;
const siteUrl = "https://yurei-so.github.io/research/";
const repositoryUrl = "https://github.com/yurei-so/research";

function fail(file, message) { throw new Error(`${file}: ${message}`); }

function renderYoutubeEmbed(videoId, title) {
  // The Markdown extension accepts only an 11-character YouTube ID, and the
  // allow-listed no-cookie host is the only external frame source in Dispatch pages.
  const embedUrl = `https://www.youtube-nocookie.com/embed/${videoId}`;
  const watchUrl = `https://www.youtube.com/watch?v=${videoId}`;
  return `<figure class="dispatch-video"><div class="dispatch-video-frame"><iframe src="${embedUrl}" title="${escapeHtml(title)}" loading="lazy" referrerpolicy="no-referrer" allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div><figcaption>${escapeHtml(title)} · <a href="${watchUrl}">Watch on YouTube ↗</a></figcaption></figure>`;
}

function parseValue(value, file) {
  const trimmed = value.trim();
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  if (/^-?\d+$/.test(trimmed)) return Number(trimmed);
  if (trimmed.startsWith('"') || trimmed.startsWith("[")) {
    try { return JSON.parse(trimmed); } catch { fail(file, "invalid JSON-style front matter value"); }
  }
  return trimmed;
}

export function parseDispatch(text, file = "dispatch") {
  const match = text.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!match) fail(file, "missing YAML front matter");
  const metadata = {};
  for (const line of match[1].split("\n")) {
    if (!line.trim()) continue;
    const field = line.match(/^([a-z_]+):\s*(.*)$/);
    if (!field) fail(file, `unsupported front matter syntax: ${line}`);
    const [, key, value] = field;
    if (!allowedKeys.has(key)) fail(file, `unknown public metadata field ${key}`);
    if (Object.hasOwn(metadata, key)) fail(file, `duplicate field ${key}`);
    metadata[key] = parseValue(value, file);
  }
  const required = ["schema_version", "id", "title", "date", "status", "lede", "tags", "publish"];
  for (const key of required) if (!Object.hasOwn(metadata, key)) fail(file, `missing ${key}`);
  if (metadata.schema_version !== 1) fail(file, "unsupported schema_version");
  if (typeof metadata.id !== "string" || !idPattern.test(metadata.id)) fail(file, "invalid id; expected dispatch-NNN");
  if (typeof metadata.title !== "string" || !metadata.title.trim() || metadata.title.length > 160) fail(file, "invalid title");
  if (typeof metadata.lede !== "string" || !metadata.lede.trim() || metadata.lede.length > 360) fail(file, "invalid lede");
  if (typeof metadata.date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(metadata.date) || Number.isNaN(Date.parse(`${metadata.date}T00:00:00Z`))) fail(file, "invalid date");
  if (!["draft", "review", "published"].includes(metadata.status)) fail(file, "invalid status");
  if (typeof metadata.publish !== "boolean") fail(file, "publish must be boolean");
  if (metadata.publish && metadata.status !== "published") fail(file, "public dispatch must have status: published");
  if (!Array.isArray(metadata.tags) || metadata.tags.length > 24 || metadata.tags.some((tag) => typeof tag !== "string" || !tagPattern.test(tag)) || new Set(metadata.tags).size !== metadata.tags.length) fail(file, "invalid or duplicate tags");
  const related = metadata.related_labnotes ?? [];
  if (!Array.isArray(related) || related.length > 24 || related.some((id) => typeof id !== "string" || !/^[a-z0-9]+(?:-[a-z0-9]+)*-\d{3}$/.test(id)) || new Set(related).size !== related.length) fail(file, "invalid or duplicate related_labnotes");
  metadata.related_labnotes = related;
  return { metadata, body: text.slice(match[0].length) };
}

export function collectDispatches(root) {
  const directory = path.join(root, "dispatches");
  if (!fs.existsSync(directory)) return [];
  const files = fs.readdirSync(directory, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".md") && entry.name !== "README.md")
    .map((entry) => path.join(directory, entry.name)).sort();
  const records = files.map((file) => {
    const relative = path.relative(root, file).split(path.sep).join("/");
    return { ...parseDispatch(fs.readFileSync(file, "utf8"), relative), file, relative };
  });
  const seen = new Set();
  for (const record of records) {
    if (seen.has(record.metadata.id)) fail(record.relative, `duplicate id ${record.metadata.id}`);
    seen.add(record.metadata.id);
  }
  return records;
}

export function renderDispatchPage(record, sourceRevision) {
  const { metadata } = record;
  const canonicalUrl = new URL(`dispatches/${metadata.id}/`, siteUrl).href;
  const sourceUrl = `${repositoryUrl}/blob/main/${record.relative.split("/").map(encodeURIComponent).join("/")}`;
  const tags = metadata.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("");
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; frame-src https://www.youtube-nocookie.com; style-src 'self'; script-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'">
<meta name="description" content="${escapeHtml(metadata.lede)}"><meta property="og:type" content="article"><meta property="og:site_name" content="Yurei Research"><meta property="og:title" content="${escapeHtml(metadata.title)}"><meta property="og:description" content="${escapeHtml(metadata.lede)}"><meta property="og:url" content="${canonicalUrl}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="${escapeHtml(metadata.title)}"><meta name="twitter:description" content="${escapeHtml(metadata.lede)}">
<title>${escapeHtml(metadata.title)} | Yurei Research Dispatch</title><link rel="canonical" href="${canonicalUrl}"><link rel="icon" href="../../favicon.png" type="image/png"><link rel="stylesheet" href="../../assets/styles.css?v=${escapeHtml(sourceRevision)}"></head><body>
<header class="terminal-bar"><a class="wordmark" href="../../"><img src="../../favicon.png" alt="">YUREI RESEARCH</a><span>FIELD DISPATCH</span></header>
<main class="note-shell"><a class="back" href="../../#dispatches">← Return to dispatches</a><article class="dispatch-article" itemscope itemtype="https://schema.org/BlogPosting"><meta itemprop="url" content="${canonicalUrl}"><meta itemprop="author" content="Yurei Research"><header class="dispatch-header"><div class="eyebrow">AFTER-ACTION REPORT / ${escapeHtml(metadata.id)}</div><h1 itemprop="headline">${escapeHtml(metadata.title)}</h1><div class="note-vitals"><time itemprop="datePublished" datetime="${escapeHtml(metadata.date)}">${escapeHtml(metadata.date)}</time><span>${escapeHtml(metadata.status)}</span></div><p class="dispatch-lede" itemprop="description">${escapeHtml(metadata.lede)}</p><div class="tags">${tags}</div><p class="source-link"><a href="${sourceUrl}">View canonical Markdown ↗</a></p></header><div class="note-body dispatch-body" itemprop="articleBody">${renderMarkdown(record.body, { imagePrefix: "../../dispatches/", renderYoutubeEmbed })}</div></article></main>
<footer><span>YUREI RESEARCH · <a href="${repositoryUrl}">SOURCE</a> · <a href="https://github.com/yurei-so">GITHUB</a></span><span>REV ${escapeHtml(sourceRevision)}</span></footer></body></html>`;
}
