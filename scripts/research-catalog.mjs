#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { collectCatalog, escapeHtml, extractResultSummary, renderMarkdown } from "./research-catalog-lib.mjs";
import { writeSocialCard } from "./social-card.mjs";

const root = path.resolve(import.meta.dirname, "..");
const siteUrl = "https://yurei-so.github.io/research/";
const repositoryUrl = "https://github.com/yurei-so/research";
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
fs.mkdirSync(path.join(output, "assets", "social"), { recursive: true });
for (const name of ["styles.css", "app.js", "favicon.png"]) {
  const source = path.join(root, "site", name);
  const destination = name === "favicon.png" ? path.join(output, name) : path.join(output, "assets", name);
  fs.copyFileSync(source, destination);
}
const familyCard = (family) => `<button class="family-card" data-family="${escapeHtml(family.id)}" type="button"><h3>${escapeHtml(family.title)}</h3><p>${family.labnote_count} published labnotes</p><div class="outcomes">${Object.entries(family.outcomes).map(([name, count]) => `<span data-outcome="${name}">${count} ${name}</span>`).join("")}</div><span class="inspect">VIEW LABNOTES →</span></button>`;
const noteCard = (note) => `<article class="feed-entry" data-family="${escapeHtml(note.family)}"><div class="entry-index"><time datetime="${note.date}">${note.date}</time><b>${escapeHtml(note.id)}</b></div><div class="entry-main"><div class="entry-state"><span>${escapeHtml(note.status)}</span><span data-outcome="${note.outcome}">${escapeHtml(note.outcome)}</span></div><h3><a href="${escapeHtml(note.href)}">${escapeHtml(note.title)}</a></h3><p>${escapeHtml(note.question)}</p><div class="tags">${note.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div></div><a class="open-note" href="${escapeHtml(note.href)}" aria-label="Open ${escapeHtml(note.id)}">↗</a></article>`;
const indexTemplate = fs.readFileSync(path.join(root, "site", "index.html"), "utf8");
const indexPage = indexTemplate
  .replaceAll("{{NOTE_COUNT}}", String(manifest.labnotes.length))
  .replaceAll("{{FAMILY_COUNT}}", String(manifest.families.length))
  .replaceAll("{{REVISION}}", escapeHtml(manifest.source_revision))
  .replaceAll("{{GENERATED_AT}}", escapeHtml(manifest.generated_at.slice(0, 10)))
  .replace("{{FAMILY_CARDS}}", manifest.families.map(familyCard).join(""))
  .replace("{{LABNOTE_CARDS}}", manifest.labnotes.map(noteCard).join(""));
fs.writeFileSync(path.join(output, "index.html"), indexPage);
fs.writeFileSync(path.join(output, "research-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
fs.writeFileSync(path.join(output, ".nojekyll"), "");
fs.writeFileSync(path.join(output, "robots.txt"), `User-agent: *\nAllow: /research/\n\nSitemap: ${siteUrl}sitemap.xml\n`);
const sitemapUrls = [{ loc: siteUrl, lastmod: manifest.labnotes[0]?.date }, ...manifest.labnotes.map((note) => ({ loc: `${siteUrl}${note.href}`, lastmod: note.date }))];
fs.writeFileSync(path.join(output, "sitemap.xml"), `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${sitemapUrls.map(({ loc, lastmod }) => `  <url><loc>${escapeHtml(loc)}</loc>${lastmod ? `<lastmod>${lastmod}</lastmod>` : ""}</url>`).join("\n")}\n</urlset>\n`);

const socialCards = [];
for (const record of records.filter((entry) => entry.metadata.publish)) {
  const note = manifest.labnotes.find((entry) => entry.id === record.metadata.id);
  note.result_summary = extractResultSummary(record.body, note.question);
  const directory = path.join(output, "labnotes", note.id);
  fs.mkdirSync(directory, { recursive: true });
  const tags = note.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("");
  const title = escapeHtml(record.metadata.title);
  const question = escapeHtml(record.metadata.question);
  const canonicalUrl = `${siteUrl}${note.href}`;
  const socialImageUrl = `${siteUrl}assets/social/${note.id}.png`;
  const socialDescription = `${note.id.toUpperCase()} · ${note.family.toUpperCase()} · ${note.outcome.toUpperCase()} · ${note.status.toUpperCase()}`;
  socialCards.push(writeSocialCard(note, path.join(output, "assets", "social", `${note.id}.png`)));
  const sourceUrl = `${repositoryUrl}/blob/main/${record.relative.split("/").map(encodeURIComponent).join("/")}`;
  const relationCard = (id, current = false) => {
    const related = manifest.labnotes.find((entry) => entry.id === id);
    if (!related) throw new Error(`${note.id}: public relation target ${id} is missing`);
    const content = `<span class="lineage-id">${escapeHtml(related.id)}</span><strong>${escapeHtml(related.title)}</strong><span class="lineage-meta"><span data-outcome="${related.outcome}">${escapeHtml(related.outcome)}</span> · ${escapeHtml(related.date)}</span>`;
    return current ? `<div class="lineage-card current" aria-current="page">${content}</div>`
      : `<a class="lineage-card" href="../${escapeHtml(related.id)}/">${content}</a>`;
  };
  const follows = note.relations.follows.map((id) => relationCard(id)).join("");
  const continuedBy = note.relations.continued_by.map((id) => relationCard(id)).join("");
  const lineage = follows || continuedBy ? `<nav class="lineage" aria-label="Labnote lineage">
<div class="lineage-heading">Related labnotes</div><div class="lineage-track">
<div class="lineage-group"><span class="lineage-label">Follows</span><div class="lineage-cards">${follows || '<span class="lineage-empty">No earlier note</span>'}</div></div>
<span class="lineage-arrow" aria-hidden="true">→</span>
<div class="lineage-group current-group"><span class="lineage-label">Current</span><div class="lineage-cards">${relationCard(note.id, true)}</div></div>
<span class="lineage-arrow" aria-hidden="true">→</span>
<div class="lineage-group"><span class="lineage-label">Continued by</span><div class="lineage-cards">${continuedBy || '<span class="lineage-empty">No published follow-up</span>'}</div></div>
</div></nav>` : "";
  const page = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'">
<meta name="description" content="${escapeHtml(socialDescription)}">
<meta property="og:type" content="article"><meta property="og:site_name" content="Yurei Research"><meta property="og:title" content="${title}"><meta property="og:description" content="${escapeHtml(socialDescription)}"><meta property="og:url" content="${canonicalUrl}">
<meta property="og:image" content="${socialImageUrl}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Research card for ${escapeHtml(note.id)}: ${title}, outcome ${escapeHtml(note.outcome)}">
<meta property="article:published_time" content="${escapeHtml(note.date)}T00:00:00Z"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="${title}"><meta name="twitter:description" content="${escapeHtml(socialDescription)}"><meta name="twitter:image" content="${socialImageUrl}">
<title>${title} — ${escapeHtml(record.metadata.id)} | Yurei Research</title><link rel="canonical" href="${canonicalUrl}"><link rel="icon" href="../../favicon.png" type="image/png">
<link rel="stylesheet" href="../../assets/styles.css"></head><body>
<header class="terminal-bar"><a class="wordmark" href="../../"><img src="../../favicon.png" alt="">YUREI RESEARCH</a><span>RESEARCH LIBRARY</span></header>
<main class="note-shell"><a class="back" href="../../">← Return to research library</a>
<article class="labnote" itemscope itemtype="https://schema.org/TechArticle"><meta itemprop="url" content="${canonicalUrl}"><meta itemprop="author" content="Yurei Research"><header class="note-header"><div class="eyebrow">LABNOTE / ${escapeHtml(note.family)}</div><h1 itemprop="headline">${title}</h1>
<div class="note-vitals"><span>${note.id}</span><time itemprop="datePublished" datetime="${note.date}">${note.date}</time><span data-outcome="${note.outcome}">${note.outcome}</span><span>${note.status}</span></div>
<p class="question" itemprop="description">${question}</p><div class="tags">${tags}</div><p class="source-link"><a href="${sourceUrl}">View source record on GitHub ↗</a></p></header>
${lineage}
<div class="note-body">${renderMarkdown(record.body)}</div></article></main>
<footer><span>YUREI RESEARCH · <a href="${repositoryUrl}">SOURCE</a> · <a href="https://github.com/yurei-so">GITHUB</a></span><span>REV ${manifest.source_revision}</span></footer></body></html>`;
  fs.writeFileSync(path.join(directory, "index.html"), page);
}
await Promise.all(socialCards);
console.log(`Built public research library with ${manifest.labnotes.length} labnotes in dist/.`);
