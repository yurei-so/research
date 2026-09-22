#!/usr/bin/env node
// SPDX-License-Identifier: AGPL-3.0-only

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { buildAttentionModel, toInterchange } from "@yurei-so/research-tools";
import { collectCatalog, escapeHtml, extractResultSummary, renderMarkdown } from "./research-catalog-lib.mjs";
import { writeFamilySocialCard, writeSocialCard } from "./social-card.mjs";

const root = path.resolve(import.meta.dirname, "..");
const siteUrl = "https://yurei-so.github.io/research/";
const repositoryUrl = "https://github.com/yurei-so/research";
const mode = process.argv[2] ?? "check";
if (!new Set(["check", "build"]).has(mode)) throw new Error("usage: node scripts/research-catalog.mjs [check|build]");

const { records, manifest } = collectCatalog(root);
const inlineJson = (value) => JSON.stringify(value).replaceAll("<", "\\u003c");
if (mode === "check") {
  console.log(`Validated ${records.length} labnotes; ${manifest.labnotes.length} eligible for publication.`);
  process.exit(0);
}

const output = path.join(root, "dist");
fs.rmSync(output, { recursive: true, force: true });
fs.mkdirSync(path.join(output, "assets"), { recursive: true });
fs.mkdirSync(path.join(output, "assets", "social"), { recursive: true });
for (const name of ["styles.css", "app.js", "labnote.js", "favicon.png"]) {
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
  const successRate = family.labnote_count
    ? Math.round(((family.outcomes.positive ?? 0) / family.labnote_count) * 100)
    : 0;
  const noteLabel = family.labnote_count === 1 ? "labnote" : "labnotes";
  const action = family.has_graph ? "OPEN RESEARCH MAP →" : "FILTER TO THIS FAMILY ↓";
  const content = `<h3>${escapeHtml(family.title)}</h3><p>${family.labnote_count} published ${noteLabel}</p><div class="outcomes">${Object.entries(family.outcomes).map(([name, count]) => `<span data-outcome="${name}">${count} ${name}</span>`).join("")}</div><span class="inspect">${action}</span>`;
  const primary = family.has_graph ? `<a class="family-primary" href="projects/${escapeHtml(family.id)}/">${content}</a>` : `<button class="family-filter family-primary" data-family="${escapeHtml(family.id)}" type="button">${content}</button>`;
  return `<article class="family-card" data-family="${escapeHtml(family.id)}"><span class="success-rate" title="Positive published labnotes divided by all published labnotes" aria-label="${successRate} percent positive-result rate">${successRate}% SUCCESS</span>${primary}</article>`;
};
const noteCard = (note) => `<article class="feed-entry" data-family="${escapeHtml(note.family)}"><div class="entry-index"><time datetime="${note.date}">${note.date}</time><b>${escapeHtml(note.id)}</b></div><div class="entry-main"><div class="entry-state"><span>${escapeHtml(note.status)}</span><span data-outcome="${note.outcome}">${escapeHtml(note.outcome)}</span></div><h3><a href="${escapeHtml(note.href)}">${escapeHtml(note.title)}</a></h3><p>${escapeHtml(note.question)}</p><div class="tags">${note.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div></div><a class="open-note" href="${escapeHtml(note.href)}" aria-label="Open ${escapeHtml(note.id)}">↗</a></article>`;
const indexTemplate = fs.readFileSync(path.join(root, "site", "index.html"), "utf8");
const indexPage = indexTemplate
  .replaceAll("{{NOTE_COUNT}}", String(manifest.labnotes.length))
  .replaceAll("{{FAMILY_COUNT}}", String(manifest.families.length))
  .replaceAll("{{REVISION}}", escapeHtml(manifest.source_revision))
  .replaceAll("{{GENERATED_AT}}", escapeHtml(manifest.generated_at.slice(0, 10)))
  .replace("{{RESEARCH_MANIFEST_JSON}}", inlineJson(manifest))
  .replace("{{FAMILY_CARDS}}", manifest.families.map(familyCard).join(""))
  .replace("{{LABNOTE_CARDS}}", manifest.labnotes.map(noteCard).join(""));
fs.writeFileSync(path.join(output, "index.html"), indexPage);
fs.writeFileSync(path.join(output, "research-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
fs.writeFileSync(path.join(output, "research-corpus-v1.json"), `${JSON.stringify(toInterchange(manifest), null, 2)}\n`);
const absoluteUrl = (relative = "") => new URL(relative, siteUrl).href;
const compactText = (value, limit = 280) => value.length <= limit ? value : `${value.slice(0, limit - 1).trimEnd()}…`;
const writeBoundedJson = (file, value, maxBytes) => {
  const serialized = `${JSON.stringify(value, null, 2)}\n`;
  const bytes = Buffer.byteLength(serialized);
  if (bytes > maxBytes) throw new Error(`${path.relative(root, file)} exceeds its ${maxBytes}-byte agent-view budget (${bytes} bytes)`);
  fs.writeFileSync(file, serialized);
};
const agentDisclaimers = {
  evidence: "This overview routes readers to published labnotes; it is not itself evidence.",
  relations: "Relations are human-authored provenance statements, not automatic proof of causality or support.",
  similarity: "Similarity geometry is omitted here. Its projection is navigational, corpus-relative, lossy, and not evidence of causality.",
  generated_summaries: "Derived AI summaries are absent unless explicitly labeled with provenance and review status.",
};
const familyOverview = (family) => {
  const notes = manifest.labnotes.filter((note) => note.family === family.id);
  const chronological = [...notes].sort((a, b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id));
  const latest = chronological.at(-1);
  const latestNegative = [...chronological].reverse().find((note) => note.outcome === "negative");
  const entryPoints = [...new Map([latest, latestNegative, chronological[0]].filter(Boolean).map((note) => [note.id, note])).values()]
    .map((note) => ({ id: note.id, title: note.title, date: note.date, status: note.status, outcome: note.outcome,
      question: compactText(note.question), finding: compactText(note.result_summary), evidence_url: absoluteUrl(note.href) }));
  const entryIds = new Set(entryPoints.map((note) => note.id));
  const relations = notes.flatMap((note) => note.relations.map((relation) => ({ from: note.id, to: relation.target, type: relation.type })))
    .filter((relation) => entryIds.has(relation.from) || entryIds.has(relation.to)).slice(0, 8);
  return {
    schema: "research-family-overview/v1",
    generated_at: manifest.generated_at,
    source_revision: manifest.source_revision,
    family: { id: family.id, title: family.title, labnote_count: family.labnote_count, outcomes: family.outcomes, latest_labnote_id: family.latest_labnote_id },
    orientation: {
      purpose: `Compact orientation to the published ${family.title} record. Follow evidence_url before making substantive claims.`,
      entry_point_policy: "Latest work, latest negative result, and earliest published record; duplicates are removed.",
      entry_points: entryPoints,
    },
    authored_relations_near_entry_points: relations,
    disclaimers: agentDisclaimers,
    links: { human: absoluteUrl(`projects/${family.id}/`), complete_corpus: absoluteUrl("research-corpus-v1.json"),
      heavy_geometry: family.has_graph ? absoluteUrl(`projects/${family.id}/graph.json`) : null,
      source: `${repositoryUrl}/tree/main/experiments` },
  };
};
const agentFamilies = manifest.families.map((family) => ({ id: family.id, title: family.title, labnote_count: family.labnote_count,
  outcomes: family.outcomes, latest_labnote_id: family.latest_labnote_id, overview_url: absoluteUrl(`projects/${family.id}/index.json`),
  human_url: absoluteUrl(`projects/${family.id}/`) }));
const agentOverview = { schema: "research-agent-overview/v1", generated_at: manifest.generated_at, source_revision: manifest.source_revision,
  purpose: "Token-bounded orientation and routing for the public Yurei Research record.", disclaimers: agentDisclaimers,
  families: agentFamilies, links: { human: siteUrl, complete_corpus: absoluteUrl("research-corpus-v1.json"), source: repositoryUrl } };
writeBoundedJson(path.join(output, "agent-overview-v1.json"), agentOverview, 8192);
const llms = [`# Yurei Research`, ``, `Public experimental records. Start with the compact overview; retrieve full evidence only as needed.`, ``,
  `## Interpretation contract`, ``, `- Overviews route to evidence; they are not evidence.`,
  `- Authored relations do not automatically establish causality or support.`,
  `- Similarity projections are corpus-relative, lossy navigation aids.`,
  `- AI summaries must declare provenance and review status; none are currently included.`, ``, `## Entry points`, ``,
  `- [Compact corpus overview](${absoluteUrl("agent-overview-v1.json")})`,
  `- [Complete public corpus](${absoluteUrl("research-corpus-v1.json")})`,
  ...agentFamilies.map((family) => `- [${family.title}](${family.overview_url}) — ${family.labnote_count} published ${family.labnote_count === 1 ? "labnote" : "labnotes"}`), ``,
  `Canonical source: ${repositoryUrl}`, ``].join("\n");
if (Buffer.byteLength(llms) > 4096) throw new Error("llms.txt exceeds its 4096-byte agent-view budget");
fs.writeFileSync(path.join(output, "llms.txt"), llms);
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
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'">
<meta name="description" content="${escapeHtml(socialDescription)}">
<meta property="og:type" content="article"><meta property="og:site_name" content="Yurei Research"><meta property="og:title" content="${title}"><meta property="og:description" content="${escapeHtml(socialDescription)}"><meta property="og:url" content="${canonicalUrl}">
<meta property="og:image" content="${socialImageUrl}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Research card for ${escapeHtml(note.id)}: ${title}, outcome ${escapeHtml(note.outcome)}">
<meta property="article:published_time" content="${escapeHtml(note.date)}T00:00:00Z"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="${title}"><meta name="twitter:description" content="${escapeHtml(socialDescription)}"><meta name="twitter:image" content="${socialImageUrl}">
<title>${title} — ${escapeHtml(record.metadata.id)} | Yurei Research</title><link rel="canonical" href="${canonicalUrl}"><link rel="icon" href="../../favicon.png" type="image/png">
<link rel="stylesheet" href="../../assets/styles.css?v=${escapeHtml(manifest.source_revision)}"></head><body>
<header class="terminal-bar"><a class="wordmark" href="../../"><img src="../../favicon.png" alt="">YUREI RESEARCH</a><span>RESEARCH LIBRARY</span></header>
<main class="note-shell"><a class="back" href="../../">← Return to research library</a>
<article class="labnote" itemscope itemtype="https://schema.org/TechArticle"><meta itemprop="url" content="${canonicalUrl}"><meta itemprop="author" content="Yurei Research"><header class="note-header"><div class="eyebrow"><a class="family-backlink" href="../../projects/${escapeHtml(note.family)}/" aria-label="Open the ${escapeHtml(note.family)} family detailed view">LABNOTE / ${escapeHtml(note.family)} <span aria-hidden="true">↗</span></a></div><h1 itemprop="headline">${title}</h1>
<div class="note-vitals"><span>${note.id}</span><time itemprop="datePublished" datetime="${note.date}">${note.date}</time><span data-outcome="${note.outcome}">${note.outcome}</span><span>${note.status}</span></div>
<p class="question" itemprop="description">${question}</p><div class="tags">${tags}</div><p class="source-link"><a href="${sourceUrl}">View source record on GitHub ↗</a></p></header>
${lineage}
<div class="note-body">${renderMarkdown(record.body)}</div></article></main>
<footer><span>YUREI RESEARCH · <a href="${repositoryUrl}">SOURCE</a> · <a href="https://github.com/yurei-so">GITHUB</a></span><span>REV ${manifest.source_revision}</span></footer><script type="module" src="../../assets/labnote.js?v=${escapeHtml(manifest.source_revision)}"></script></body></html>`;
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
const pixelAttentionTerrain = (notes, positions, width, height) => {
  const cell = 24;
  const radius = 170;
  const samples = [];
  for (let y = 0; y < height; y += cell) {
    for (let x = 0; x < width; x += cell) {
      const centerX = x + cell / 2;
      const centerY = y + cell / 2;
      const heat = notes.reduce((sum, note) => {
        const point = positions.get(note.id);
        const distance = (centerX - point.x) ** 2 + (centerY - point.y) ** 2;
        return sum + Math.exp(-distance / (2 * radius ** 2));
      }, 0);
      samples.push({ x, y, heat });
    }
  }
  const peak = Math.max(...samples.map((sample) => sample.heat), 1e-9);
  const cells = samples.flatMap(({ x, y, heat }) => {
    const relative = heat / peak;
    const level = relative < .06 ? 0 : Math.max(1, Math.ceil(relative * 6));
    return level ? [`<rect class="attention-cell level-${level}" x="${x}" y="${y}" width="${cell - 2}" height="${cell - 2}"/>`] : [];
  });
  return cells.join("");
};
const recordById = new Map(records.map((record) => [record.metadata.id, record]));
for (const family of manifest.families) {
  const graphDirectory = path.join(output, "projects", family.id);
  fs.mkdirSync(graphDirectory, { recursive: true });
  writeBoundedJson(path.join(graphDirectory, "index.json"), familyOverview(family), 4096);
  if (!family.has_graph) continue;
  const notes = manifest.labnotes.filter((note) => note.family === family.id).sort((a, b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id));
  const noteIds = new Set(notes.map((note) => note.id));
  const graphNotes = notes.map((note) => ({ ...note, source_url: `${repositoryUrl}/blob/main/${recordById.get(note.id).relative.split("/").map(encodeURIComponent).join("/")}` }));
  const relations = notes.flatMap((note) => note.relations.filter((relation) => noteIds.has(relation.target)).map((relation) => ({ source: note.id, ...relation })));
  const graphWidth = notes.length > 7 ? 1500 : 1200;
  const graphHeight = notes.length > 7 ? 1200 : 900;
  const center = { x: graphWidth / 2, y: graphHeight / 2 };
  const positions = new Map(notes.map((note, index) => {
    if (index === 0) return [note.id, { cx: center.x, cy: center.y, x: center.x - 110, y: center.y - 59 }];
    const firstRingCapacity = 6;
    const ring = index <= firstRingCapacity ? 0 : 1;
    const positionInRing = ring === 0 ? index - 1 : index - firstRingCapacity - 1;
    const population = ring === 0 ? Math.min(firstRingCapacity, notes.length - 1) : notes.length - firstRingCapacity - 1;
    const radius = ring === 0 ? 265 : 505;
    const angle = -Math.PI / 2 + ring * .24 + positionInRing / population * Math.PI * 2;
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
  const attention = buildAttentionModel(manifest.labnotes, notes);
  const rawAttentionPoints = notes.map((note) => attention.projection.points[note.id]);
  const extent = (axis) => [Math.min(...rawAttentionPoints.map((point) => point[axis])), Math.max(...rawAttentionPoints.map((point) => point[axis]))];
  const [minX, maxX] = extent(0);
  const [minY, maxY] = extent(1);
  const attentionPositions = new Map(notes.map((note) => {
    const point = attention.projection.points[note.id];
    const x = maxX === minX ? graphWidth / 2 : 170 + (point[0] - minX) / (maxX - minX) * (graphWidth - 340);
    const y = maxY === minY ? graphHeight / 2 : 150 + (point[1] - minY) / (maxY - minY) * (graphHeight - 300);
    return [note.id, { x, y }];
  }));
  const attentionHeat = notes.map((note) => {
    const point = attentionPositions.get(note.id);
    return `<circle cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="190"/>`;
  }).join("");
  const attentionCells = pixelAttentionTerrain(notes, attentionPositions, graphWidth, graphHeight);
  const attentionNodes = notes.map((note) => {
    const point = attentionPositions.get(note.id);
    return `<a class="attention-node" data-note="${escapeHtml(note.id)}" data-center-x="${point.x.toFixed(1)}" data-center-y="${point.y.toFixed(1)}" href="../../${escapeHtml(note.href)}"><circle class="attention-hit" cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="22"/><circle class="attention-point" cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="8" fill="${outcomeColors[note.outcome]}"/><text x="${(point.x + 15).toFixed(1)}" y="${(point.y - 13).toFixed(1)}">${escapeHtml(note.id.toUpperCase())}</text><title>${escapeHtml(note.title)}</title></a>`;
  }).join("");
  const familySocialImageUrl = `${siteUrl}assets/social/family-${family.id}.png`;
  socialCards.push(writeFamilySocialCard(family, notes, attention,
    path.join(output, "assets", "social", `family-${family.id}.png`)));
  const graphData = { family: { id: family.id, title: family.title }, notes: graphNotes, relations, attention };
  fs.writeFileSync(path.join(graphDirectory, "graph.json"), `${JSON.stringify(graphData, null, 2)}\n`);
  const familyNoteList = [...notes].sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id)).map((note) =>
    `<li class="family-note" data-note="${escapeHtml(note.id)}" data-search="${escapeHtml(`${note.id} ${note.title} ${note.question} ${note.tags.join(" ")}`.toLowerCase())}" data-outcome="${escapeHtml(note.outcome)}"><button class="family-note-select" type="button" aria-pressed="false"><span class="family-note-id">${escapeHtml(note.id)}</span><span class="family-note-meta"><time datetime="${escapeHtml(note.date)}">${escapeHtml(note.date)}</time> · <span data-outcome="${escapeHtml(note.outcome)}">${escapeHtml(note.outcome)}</span></span><strong>${escapeHtml(note.title)}</strong><span class="family-note-question">${escapeHtml(note.question)}</span></button><a class="family-note-open" href="../../${escapeHtml(note.href)}">OPEN LABNOTE ↗</a></li>`).join("");
  const familyOutcomes = [...new Set(notes.map((note) => note.outcome))].sort().map((outcome) =>
    `<option value="${escapeHtml(outcome)}">${escapeHtml(outcome.toUpperCase())}</option>`).join("");
  const familyNoteSection = `<section class="family-notes" aria-labelledby="family-notes-title"><div class="family-notes-heading"><div><span class="eyebrow">PUBLISHED RECORD</span><h2 id="family-notes-title">Labnotes</h2></div><span id="family-note-count">${notes.length} NOTES</span></div><div class="family-note-controls"><label>FILTER NOTES<input id="family-note-filter" type="search" placeholder="ID, title, question, or tag" autocomplete="off"></label><label>OUTCOME<select id="family-note-outcome"><option value="">ALL OUTCOMES</option>${familyOutcomes}</select></label></div><ol class="family-note-list">${familyNoteList}</ol><p id="family-note-empty" class="empty" hidden>No matching labnotes.</p></section>`;
  const graphPage = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'"><meta name="description" content="Detailed provenance and research-attention views for ${escapeHtml(family.title)}."><meta property="og:type" content="website"><meta property="og:site_name" content="Yurei Research"><meta property="og:title" content="${escapeHtml(family.title)} detailed view"><meta property="og:description" content="Authored provenance and corpus-relative research attention in Yurei Research."><meta property="og:url" content="${siteUrl}projects/${escapeHtml(family.id)}/"><meta property="og:image" content="${familySocialImageUrl}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Pixel attention-map preview for the ${escapeHtml(family.title)} research family"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="${escapeHtml(family.title)} detailed view"><meta name="twitter:description" content="${family.labnote_count} published labnotes in Yurei Research"><meta name="twitter:image" content="${familySocialImageUrl}"><title>${escapeHtml(family.title)} detailed view | Yurei Research</title><link rel="canonical" href="${siteUrl}projects/${escapeHtml(family.id)}/"><link rel="icon" href="../../favicon.png" type="image/png"><link rel="stylesheet" href="../../assets/styles.css"></head><body class="project-page"><header class="terminal-bar"><a class="wordmark" href="../../"><img src="../../favicon.png" alt="">YUREI RESEARCH</a><div class="page-view-switch" aria-label="Page view"><button type="button" data-page-view="standard" aria-pressed="true">STANDARD</button><button type="button" data-page-view="beta-fit" aria-pressed="false">BETA FIT</button></div><span>RESEARCH FAMILY</span></header><main class="project-shell"><a class="back" href="../../">← Return to research library</a><header class="project-header"><div class="project-identity"><div class="eyebrow">PROJECT / ${escapeHtml(family.id)}</div><h1>${escapeHtml(family.title)}</h1></div><p>Two strictly separate views of the published record: authored provenance and corpus-relative research attention.</p></header><div class="map-modes" aria-label="Detailed visualization"><button type="button" data-map-view="attention" aria-pressed="true">ATTENTION HEATMAP</button><button type="button" data-map-view="provenance" aria-pressed="false">PROVENANCE WEB</button><p id="view-disclosure">Human-authored relationships only. Proximity is not used to create edges.</p></div><div class="graph-layout"><div class="graph-panel"><div class="graph-toolbar" aria-label="Map controls"><button id="zoom-out" type="button" aria-label="Zoom out">−</button><span id="zoom-level">82%</span><button id="zoom-in" type="button" aria-label="Zoom in">+</button><button id="zoom-fit" type="button">FIT</button><button id="terrain-style" type="button">CELLS</button><span>DRAG SCROLLBARS OR PAN WITH TOUCH</span></div><div class="graph-stage" aria-label="${escapeHtml(family.title)} detailed visualization"><svg class="project-map" data-map-view="provenance" data-natural-width="${graphWidth}" data-natural-height="${graphHeight}" style="width:${Math.round(graphWidth * .82)}px" viewBox="0 0 ${graphWidth} ${graphHeight}" role="group" hidden><defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#596278"/></marker></defs>${edges}${nodes}</svg><svg class="attention-map" data-map-view="attention" data-terrain="cells" data-natural-width="${graphWidth}" data-natural-height="${graphHeight}" style="width:${Math.round(graphWidth * .82)}px" viewBox="0 0 ${graphWidth} ${graphHeight}" role="group" aria-label="Projected research attention map"><defs><radialGradient id="attention-heat"><stop offset="0" stop-color="#a98aff" stop-opacity=".55"/><stop offset=".45" stop-color="#6650a8" stop-opacity=".22"/><stop offset="1" stop-color="#27223a" stop-opacity="0"/></radialGradient><filter id="fog-blur"><feGaussianBlur stdDeviation="65"/></filter><mask id="fog-mask"><rect width="100%" height="100%" fill="white"/><g filter="url(#fog-blur)" fill="black">${attentionHeat}</g></mask></defs><rect width="100%" height="100%" fill="#0b0d14"/><g class="attention-smooth"><g class="attention-heat" fill="url(#attention-heat)">${attentionHeat}</g><rect class="attention-fog" width="100%" height="100%" fill="#03040a" mask="url(#fog-mask)"/></g><g class="attention-cells">${attentionCells}</g>${attentionNodes}</svg></div></div><aside class="graph-inspector" aria-live="polite"><span class="eyebrow" id="inspect-id">SELECT A LABNOTE</span><h2 id="inspect-title">Project record</h2><div class="inspector-vitals"><span id="inspect-date"></span><span id="inspect-status"></span><span id="inspect-outcome"></span></div><p class="inspector-summary" id="inspect-summary">Select once to inspect. Double-click a node to open its full labnote.</p><div class="relation-list" id="relation-list"></div><div class="inspector-actions"><button id="back-to-map" type="button">↑ BACK TO MAP</button><a id="open-note" href="../../">OPEN LABNOTE</a><a id="view-source" href="${repositoryUrl}">VIEW SOURCE</a><button id="trace-lineage" type="button" aria-pressed="false">TRACE LINEAGE</button><button id="copy-link" type="button">COPY LINK</button></div><p class="edge-note" id="edge-note">Select an edge to read its authored rationale.</p></aside></div></main><footer><span>YUREI RESEARCH · <a href="${repositoryUrl}">SOURCE</a></span><span>REV ${escapeHtml(manifest.source_revision)}</span></footer><script type="module" src="../../assets/project-graph.js"></script></body></html>`;
  fs.writeFileSync(path.join(graphDirectory, "index.html"), graphPage
    .replace('<div class="graph-layout">', `<div class="graph-layout">${familyNoteSection}`)
    .replace('<p class="inspector-summary" id="inspect-summary">Select once to inspect. Double-click a node to open its full labnote.</p>', '<div class="inspector-reading"><span class="inspector-label">QUESTION</span><p class="inspector-question" id="inspect-question">Select a labnote to read its research question.</p><span class="inspector-label">RESULT</span><p class="inspector-summary" id="inspect-summary">Its published result will appear here.</p></div>')
    .replace('aria-label="Page view"', 'aria-label="Page layout"')
    .replace('>STANDARD</button>', '>SCROLL</button>')
    .replace('>BETA FIT</button>', '>FIT TO SCREEN</button>')
    .replace("</head>", `<link rel="alternate" type="application/json" href="index.json" title="Compact agent overview"></head>`)
    .replace('<script type="module" src="../../assets/project-graph.js">', `<script id="project-graph-data" type="application/json">${inlineJson(graphData)}</script><script type="module" src="../../assets/project-graph.js">`)
    .replace("../../assets/styles.css", `../../assets/styles.css?v=${escapeHtml(manifest.source_revision)}`)
    .replace("../../assets/project-graph.js", `../../assets/project-graph.js?v=${escapeHtml(manifest.source_revision)}`));
}
await Promise.all(socialCards);
console.log(`Built public research library with ${manifest.labnotes.length} labnotes in dist/.`);
// SPDX-License-Identifier: AGPL-3.0-only
