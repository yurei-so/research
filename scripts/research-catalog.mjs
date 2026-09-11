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
fs.copyFileSync(path.join(root, "site", "project-graph.js"), path.join(output, "assets", "project-graph.js"));
for (const record of records.filter((entry) => entry.metadata.publish)) {
  const note = manifest.labnotes.find((entry) => entry.id === record.metadata.id);
  note.result_summary = extractResultSummary(record.body, note.question);
}
const familyCard = (family) => {
  const graph = family.has_graph ? `<a class="graph-link" href="projects/${escapeHtml(family.id)}/">VIEW PROJECT MAP ↗</a>` : "";
  return `<article class="family-card" data-family="${escapeHtml(family.id)}"><button class="family-filter" data-family="${escapeHtml(family.id)}" type="button"><h3>${escapeHtml(family.title)}</h3><p>${family.labnote_count} published labnotes</p><div class="outcomes">${Object.entries(family.outcomes).map(([name, count]) => `<span data-outcome="${name}">${count} ${name}</span>`).join("")}</div><span class="inspect">VIEW LABNOTES →</span></button>${graph}</article>`;
};
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
const sitemapUrls = [{ loc: siteUrl, lastmod: manifest.labnotes[0]?.date }, ...manifest.families.filter((family) => family.has_graph).map((family) => ({ loc: `${siteUrl}projects/${family.id}/`, lastmod: manifest.labnotes.find((note) => note.id === family.latest_labnote_id)?.date })), ...manifest.labnotes.map((note) => ({ loc: `${siteUrl}${note.href}`, lastmod: note.date }))];
fs.writeFileSync(path.join(output, "sitemap.xml"), `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${sitemapUrls.map(({ loc, lastmod }) => `  <url><loc>${escapeHtml(loc)}</loc>${lastmod ? `<lastmod>${lastmod}</lastmod>` : ""}</url>`).join("\n")}\n</urlset>\n`);

const socialCards = [];
for (const record of records.filter((entry) => entry.metadata.publish)) {
  const note = manifest.labnotes.find((entry) => entry.id === record.metadata.id);
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
  const follows = note.timeline.follows.map((id) => relationCard(id)).join("");
  const continuedBy = note.timeline.continued_by.map((id) => relationCard(id)).join("");
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

const outcomeColors = { positive: "#84d6a0", negative: "#de8d9a", mixed: "#d9bd78", inconclusive: "#70d7da", pending: "#858d9d", "not-applicable": "#858d9d" };
// Graph arrows run from earlier evidence to the later note, so labels use the
// inverse voice of the relation stored on that later note.
const relationLabels = { "motivated-by": "MOTIVATES", "reuses-data": "DATA REUSED BY", "reuses-apparatus": "APPARATUS REUSED BY", extends: "EXTENDED BY", ablates: "ABLATED BY", replicates: "REPLICATED BY", supports: "SUPPORTED BY", challenges: "CHALLENGED BY", supersedes: "SUPERSEDED BY", follows: "FOLLOWED BY" };
const wrapNodeTitle = (title) => {
  const words = title.split(/\s+/);
  const lines = [""];
  for (const word of words) {
    const current = lines.at(-1);
    if (!current || `${current} ${word}`.length <= 25) lines[lines.length - 1] = current ? `${current} ${word}` : word;
    else if (lines.length < 3) lines.push(word);
    else { lines[2] = `${lines[2].slice(0, 21).trimEnd()}…`; break; }
  }
  return lines;
};
const recordById = new Map(records.map((record) => [record.metadata.id, record]));
for (const family of manifest.families.filter((entry) => entry.has_graph)) {
  const notes = manifest.labnotes.filter((note) => note.family === family.id).sort((a, b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id));
  const noteIds = new Set(notes.map((note) => note.id));
  const graphNotes = notes.map((note) => ({ ...note, source_url: `${repositoryUrl}/blob/main/${recordById.get(note.id).relative.split("/").map(encodeURIComponent).join("/")}` }));
  const relations = notes.flatMap((note) => note.relations.filter((relation) => noteIds.has(relation.target)).map((relation) => ({ source: note.id, ...relation })));
  const graphWidth = 1400;
  const graphHeight = 950;
  const center = { x: graphWidth / 2, y: graphHeight / 2 };
  const positions = new Map(notes.map((note, index) => {
    if (index === 0) return [note.id, { cx: center.x, cy: center.y, x: center.x - 110, y: center.y - 59 }];
    const radius = 150 + index * 68;
    const angle = -Math.PI / 2 + (index - 1) * 1.72;
    const cx = center.x + Math.cos(angle) * radius;
    const cy = center.y + Math.sin(angle) * radius;
    return [note.id, { cx, cy, x: cx - 110, y: cy - 59 }];
  }));
  const edges = relations.map((relation) => {
    const from = positions.get(relation.target);
    const to = positions.get(relation.source);
    const dx = to.cx - from.cx;
    const dy = to.cy - from.cy;
    const length = Math.hypot(dx, dy) || 1;
    const start = { x: from.cx + dx / length * 112, y: from.cy + dy / length * 65 };
    const end = { x: to.cx - dx / length * 112, y: to.cy - dy / length * 65 };
    const bend = relations.indexOf(relation) % 2 ? 34 : -34;
    const control = { x: (start.x + end.x) / 2 - dy / length * bend, y: (start.y + end.y) / 2 + dx / length * bend };
    const label = { x: .25 * start.x + .5 * control.x + .25 * end.x, y: .25 * start.y + .5 * control.y + .25 * end.y - 12 };
    return `<g class="graph-edge" data-source="${escapeHtml(relation.source)}" data-target="${escapeHtml(relation.target)}" data-rationale="${escapeHtml(relation.rationale)}" tabindex="0"><title>${escapeHtml(relationLabels[relation.type])}: ${escapeHtml(relation.rationale)}</title><path d="M ${start.x.toFixed(1)} ${start.y.toFixed(1)} Q ${control.x.toFixed(1)} ${control.y.toFixed(1)} ${end.x.toFixed(1)} ${end.y.toFixed(1)}"/><text x="${label.x.toFixed(1)}" y="${label.y.toFixed(1)}" text-anchor="middle">${escapeHtml(relationLabels[relation.type])}</text></g>`;
  }).join("");
  const nodes = notes.map((note) => {
    const position = positions.get(note.id);
    const titleLines = wrapNodeTitle(note.title);
    return `<a class="graph-node" data-note="${escapeHtml(note.id)}" data-center-x="${position.cx.toFixed(1)}" data-center-y="${position.cy.toFixed(1)}" href="../../${escapeHtml(note.href)}"><g transform="translate(${position.x.toFixed(1)} ${position.y.toFixed(1)})"><rect width="220" height="118" rx="2"/><text class="node-id" x="15" y="23">${escapeHtml(note.id.toUpperCase())}</text><circle cx="198" cy="19" r="4.5" fill="${outcomeColors[note.outcome]}"/>${titleLines.slice(0, 2).map((line, index) => `<text class="node-title" x="15" y="${52 + index * 21}">${escapeHtml(line)}</text>`).join("")}<text class="node-date" x="15" y="103">${escapeHtml(note.date)} · ${escapeHtml(note.outcome.toUpperCase())}</text></g></a>`;
  }).join("");
  const graphDirectory = path.join(output, "projects", family.id);
  fs.mkdirSync(graphDirectory, { recursive: true });
  fs.writeFileSync(path.join(graphDirectory, "graph.json"), `${JSON.stringify({ family: { id: family.id, title: family.title }, notes: graphNotes, relations }, null, 2)}\n`);
  const graphPage = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'"><meta name="description" content="Explicit labnote relationships and experimental lineage for ${escapeHtml(family.title)}."><meta property="og:type" content="website"><meta property="og:title" content="${escapeHtml(family.title)} project map"><meta property="og:description" content="Authored labnote relationships and experimental lineage in Yurei Research."><meta property="og:url" content="${siteUrl}projects/${escapeHtml(family.id)}/"><title>${escapeHtml(family.title)} project map | Yurei Research</title><link rel="canonical" href="${siteUrl}projects/${escapeHtml(family.id)}/"><link rel="icon" href="../../favicon.png" type="image/png"><link rel="stylesheet" href="../../assets/styles.css"></head><body><header class="terminal-bar"><a class="wordmark" href="../../"><img src="../../favicon.png" alt="">YUREI RESEARCH</a><span>PROJECT MAP</span></header><main class="project-shell"><a class="back" href="../../">← Return to research library</a><header class="project-header"><div class="eyebrow">PROJECT / ${escapeHtml(family.id)}</div><h1>${escapeHtml(family.title)}</h1><p>Authored relationships between published labnotes. Select a note to inspect why it exists and what it informed.</p></header><div class="graph-layout"><div class="graph-panel"><div class="graph-toolbar" aria-label="Graph zoom controls"><button id="zoom-out" type="button">−</button><span id="zoom-level">82%</span><button id="zoom-in" type="button">+</button><button id="zoom-fit" type="button">FIT</button><span>DRAG SCROLLBARS OR PAN WITH TOUCH</span></div><div class="graph-stage" aria-label="${escapeHtml(family.title)} labnote relationship graph"><svg class="project-map" data-natural-width="${graphWidth}" data-natural-height="${graphHeight}" style="width:${Math.round(graphWidth * .82)}px" viewBox="0 0 ${graphWidth} ${graphHeight}" role="group"><defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#596278"/></marker></defs>${edges}${nodes}</svg></div></div><aside class="graph-inspector" aria-live="polite"><span class="eyebrow" id="inspect-id">SELECT A LABNOTE</span><h2 id="inspect-title">Project lineage</h2><div class="inspector-vitals"><span id="inspect-date"></span><span id="inspect-status"></span><span id="inspect-outcome"></span></div><p class="inspector-summary" id="inspect-summary">Select once to inspect. Double-click a node to open its full labnote.</p><div class="relation-list" id="relation-list"></div><div class="inspector-actions"><a id="open-note" href="../../">OPEN LABNOTE</a><a id="view-source" href="${repositoryUrl}">VIEW SOURCE</a><button id="trace-lineage" type="button" aria-pressed="false">TRACE LINEAGE</button><button id="copy-link" type="button">COPY LINK</button></div><p class="edge-note" id="edge-note">Select an edge to read its authored rationale.</p></aside></div></main><footer><span>YUREI RESEARCH · <a href="${repositoryUrl}">SOURCE</a></span><span>REV ${escapeHtml(manifest.source_revision)}</span></footer><script type="module" src="../../assets/project-graph.js"></script></body></html>`;
  fs.writeFileSync(path.join(graphDirectory, "index.html"), graphPage);
}
await Promise.all(socialCards);
console.log(`Built public research library with ${manifest.labnotes.length} labnotes in dist/.`);
