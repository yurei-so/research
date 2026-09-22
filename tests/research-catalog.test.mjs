// SPDX-License-Identifier: AGPL-3.0-only

import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { buildAttentionModel, toInterchange, validateCorpus } from "@yurei-so/research-tools";
import { collectCatalog, escapeHtml, extractResultSummary, parseLabnote, renderMarkdown, validateMetadata } from "../scripts/research-catalog-lib.mjs";
import { familySocialCardSvg, socialCardSvg } from "../scripts/social-card.mjs";

const metadata = { schema_version: 1, id: "test-001", title: "Test", date: "2026-09-08", status: "complete", outcome: "negative", question: "Did it work?", tags: ["negative-result"], lineage: [], publish: true };

test("repository catalog validates and exposes only allowlisted metadata", () => {
  const { records, manifest } = collectCatalog(path.resolve(import.meta.dirname, ".."));
  assert.ok(records.length >= 37);
  assert.ok(manifest.labnotes.some((note) => note.id === "prosody-001"));
  assert.ok(manifest.labnotes.some((note) => note.id === "voxel-guidance-001"));
  assert.equal(manifest.families.length, 6);
  assert.equal(manifest.families.find((family) => family.id === "meta-research")?.title, "Meta Research");
  assert.ok(manifest.families.every((family) => !Object.hasOwn(family, "status")));
  assert.deepEqual(Object.keys(manifest.labnotes[0]).sort(), ["date", "family", "href", "id", "lineage", "outcome", "question", "relations", "status", "tags", "timeline", "title"]);
  assert.ok(manifest.labnotes.every((note) => !JSON.stringify(note).includes("/home/")));
  const finalComposition = manifest.labnotes.find((note) => note.id === "composition-006");
  assert.deepEqual(finalComposition.timeline, { follows: ["composition-005"], continued_by: ["composition-007"] });
  const firstComposition = manifest.labnotes.find((note) => note.id === "composition-001");
  assert.deepEqual(firstComposition.timeline, { follows: [], continued_by: ["composition-002"] });
  const namespaceAblation = manifest.labnotes.find((note) => note.id === "voxel-guidance-005");
  assert.equal(namespaceAblation.relations[0].type, "motivated-by");
  assert.equal(namespaceAblation.relations[0].target, "voxel-guidance-004");
  assert.ok(manifest.families.find((family) => family.id === "voxel-guidance").has_graph);
  assert.deepEqual(manifest.families.filter((family) => family.has_graph).map((family) => family.id),
    ["composition", "narrative-steering", "prosody", "voxel-guidance", "zenith"]);
});

test("every published labnote has enough metadata for a standalone discovery page", () => {
  const { manifest } = collectCatalog(path.resolve(import.meta.dirname, ".."));
  for (const note of manifest.labnotes) {
    assert.ok(note.title.length >= 8, `${note.id} needs a descriptive title`);
    assert.ok(note.question.length >= 24, `${note.id} needs a descriptive question`);
    assert.ok(note.tags.length >= 1, `${note.id} needs discovery terminology`);
    assert.match(note.href, new RegExp(`^labnotes/${note.id}/$`));
  }
});

test("publish false is excluded from the public projection", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "research-catalog-"));
  const dir = path.join(root, "experiments", "demo", "docs", "labnotes");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "demo.md"), `---\n${Object.entries({ ...metadata, publish: false }).map(([key, value]) => `${key}: ${JSON.stringify(value)}`).join("\n")}\n---\n# Private\nsecret payload`);
  const { records, manifest } = collectCatalog(root);
  assert.equal(records.length, 1);
  assert.equal(manifest.labnotes.length, 0);
  fs.rmSync(root, { recursive: true, force: true });
});

test("unknown metadata fields fail closed", () => {
  assert.throws(() => parseLabnote(`---\nid: test-001\nsecret_path: /tmp/private\n---\n`, "unsafe.md"), /unknown public metadata field/);
});

test("invalid metadata and unsafe lineage are rejected", () => {
  assert.throws(() => validateMetadata({ ...metadata, tags: ["fine", "Not Fine"] }), /invalid or duplicate tag/);
  assert.throws(() => validateMetadata({ ...metadata, lineage: ["test-001"] }), /self lineage/);
  assert.throws(() => validateMetadata({ ...metadata, relations: [{ target: "other-001", type: "imagines", rationale: "No." }] }), /invalid relation type/);
  assert.throws(() => validateMetadata({ ...metadata, relations: [{ target: "other-001", type: "extends", rationale: "" }] }), /invalid relation rationale/);
});

test("markdown renderer escapes raw HTML and unsafe links", () => {
  const rendered = renderMarkdown("# Result\n<script>alert(1)</script>\n[bad](javascript:alert(1))\n[good](https://example.com)");
  assert.ok(!rendered.includes("<script>"));
  assert.ok(!rendered.includes('href="javascript:'));
  assert.ok(rendered.includes('href="https://example.com"'));
  assert.equal(escapeHtml('<img src=x onerror="bad">'), "&lt;img src=x onerror=&quot;bad&quot;&gt;");
});

test("markdown renderer preserves readable tables without trusting HTML", () => {
  const rendered = renderMarkdown("| Result | Count |\n| --- | ---: |\n| Negative | 4 |\n| <unsafe> | 1 |");
  assert.ok(rendered.includes("<table>"));
  assert.ok(rendered.includes("<th>Result</th>"));
  assert.ok(rendered.includes("&lt;unsafe&gt;"));
});

test("markdown headings expose stable copyable section links", () => {
  const rendered = renderMarkdown("## Result\nOne\n\n## Result\nTwo");
  assert.match(rendered, /<h3 id="result">Result<a class="heading-anchor" href="#result"/);
  assert.match(rendered, /<h3 id="result-2">Result<a class="heading-anchor" href="#result-2"/);
});

test("result summaries derive from canonical markdown and skip result tables", () => {
  const body = "## Results\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\nThe **namespace** supplied no [benefit](https://example.com).\n\n## Limits\nNope";
  assert.equal(extractResultSummary(body, "fallback"), "The namespace supplied no benefit.");
  assert.equal(extractResultSummary("## Method\nNothing", "Did it work?"), "Did it work?");
});

test("social card SVG contains research identity and escaped canonical metadata", () => {
  const svg = socialCardSvg({ id: "test-001", family: "test", title: "A <negative> result",
    date: "2026-09-10", status: "complete", outcome: "negative",
    question: "Did it work?", result_summary: "It did not work & that matters." });
  assert.ok(svg.includes("YUREI RESEARCH"));
  assert.ok(svg.includes("NEGATIVE"));
  assert.ok(svg.includes("A &lt;negative&gt; result"));
  assert.ok(!svg.includes("It did not work & that matters."));
});

test("social card wraps visually wide titles before the safe right edge", () => {
  const svg = socialCardSvg({ id: "test-002", family: "test", title: "Blinded current-task inference",
    date: "2026-09-10", status: "complete", outcome: "positive",
    question: "Did it work?", result_summary: "A compact result." });
  assert.ok(svg.includes("Blinded current-task"));
  assert.ok(svg.includes("inference</text>"));
});

test("family social card renders a pixel preview from real attention geometry", () => {
  const svg = familySocialCardSvg(
    { id: "test-family", title: "Test Family", outcomes: { positive: 2 }, labnote_count: 2 },
    [{ id: "test-001" }, { id: "test-002" }],
    { projection: { points: { "test-001": [0, 0], "test-002": [1, 1] } } },
  );
  assert.ok(svg.includes("RESEARCH FAMILY"));
  assert.ok(svg.includes("PIXEL PREVIEW"));
  assert.ok(svg.includes('width="13" height="13"'));
  assert.ok(svg.includes("2 published labnotes"));
});

test("detailed map retains both terrains and dedicated mobile navigation", () => {
  const catalog = fs.readFileSync(path.resolve("scripts/research-catalog.mjs"), "utf8");
  const client = fs.readFileSync(path.resolve("site/project-graph.js"), "utf8");
  const styles = fs.readFileSync(path.resolve("site/styles.css"), "utf8");
  assert.match(catalog, /class=\"attention-cells\"/);
  assert.match(catalog, /class=\"attention-smooth\"/);
  assert.match(client, /terrain === \"cells\" \? \"smooth\" : \"cells\"/);
  assert.match(client, /attention-context-edge/);
  assert.match(client, /Authored neighbor context/);
  assert.match(client, /back-to-map/);
  assert.match(client, /Highlighted \$\{count\} authored ancestor\/current\/descendant notes/);
  assert.match(client, /family-note-filter/);
  assert.match(catalog, /class="family-note-list"/);
  assert.match(catalog, /ID, title, question, or tag/);
  assert.match(styles, /\.graph-edge\.traced path/);
  assert.match(styles, /\.family-note-list/);
  assert.match(styles, /height: min\(52svh, 500px\)/);
  assert.match(styles, /#back-to-map \{ display: inline-flex; \}/);
});

test("family view defaults to the attention map with a synchronized note rail", () => {
  const catalog = fs.readFileSync(path.resolve("scripts/research-catalog.mjs"), "utf8");
  const client = fs.readFileSync(path.resolve("site/project-graph.js"), "utf8");
  const styles = fs.readFileSync(path.resolve("site/styles.css"), "utf8");
  assert.match(catalog, /data-map-view="attention" aria-pressed="true"/);
  assert.match(catalog, /class="project-map"[^>]+hidden/);
  assert.match(catalog, /class="family-note-select"/);
  assert.match(catalog, /replace\('<div class="graph-layout">'/);
  assert.match(client, /let activeView = "attention"/);
  assert.match(client, /focusSelected/);
  assert.match(client, /naturalHeight \* zoom/);
  assert.match(client, /stage\.scrollLeft = focus\.x \* newWidth/);
  assert.doesNotMatch(client, /requestAnimationFrame\(\(\) => \{\n\s+setZoom\(document\.body\.dataset\.pageView/);
  assert.match(client, /if \(manual\) userAdjustedZoom = true/);
  assert.match(client, /yurei-family-map-zoom/);
  assert.match(client, /saveZoom\(document\.body\.dataset\.pageView, zoom\)/);
  assert.match(client, /restoredZoom \?\?/);
  assert.match(client, /if \(userAdjustedZoom\) return/);
  assert.match(client, /bindZoom\("#zoom-in"/);
  assert.match(client, /addEventListener\("pointerup"/);
  assert.match(client, /ZOOM ERROR/);
  assert.match(client, /revealListSelection/);
  assert.match(client, /selectNote\(node\.dataset\.note, \{ reveal: true \}\)/);
  assert.match(client, /item\.addEventListener\("click", \(\) => selectNote\(other\.id, \{ focus: true, reveal: true \}\)\)/);
  assert.match(client, /Math\.max\(matchMedia\("\(max-width: 720px\)"\)\.matches \? \.58 : \.68, fitZoom\(\)\)/);
  assert.match(client, /selectNote\(button\.closest\("\.family-note"\)\.dataset\.note, \{ focus: true \}\)/);
  assert.match(styles, /grid-template-columns: 19rem minmax\(0, 1fr\) 21rem/);
  assert.match(styles, /\.attention-context-edge \{[^}]+opacity: 0/s);
  assert.match(styles, /\.attention-context-edge\.related \{ opacity: \.72/);
  assert.match(styles, /\.relation-item:hover/);
  assert.match(catalog, /id="inspect-question"/);
  assert.match(client, /\$\("#inspect-question"\)\.textContent = note\.question/);
});

test("labnote headers link back to their family detailed view", () => {
  const catalog = fs.readFileSync(path.resolve("scripts/research-catalog.mjs"), "utf8");
  assert.match(catalog, /class="family-backlink"/);
  assert.match(catalog, /href="\.\.\/\.\.\/projects\/\$\{escapeHtml\(note\.family\)\}\/"/);
});

test("generated pages revision their styles and scripts to avoid mixed deployments", () => {
  const catalog = fs.readFileSync(path.resolve("scripts/research-catalog.mjs"), "utf8");
  const index = fs.readFileSync(path.resolve("site/index.html"), "utf8");
  assert.match(index, /styles\.css\?v=\{\{REVISION\}\}/);
  assert.match(index, /app\.js\?v=\{\{REVISION\}\}/);
  assert.match(catalog, /styles\.css\?v=\$\{escapeHtml\(manifest\.source_revision\)\}/);
  assert.match(catalog, /project-graph\.js\?v=\$\{escapeHtml\(manifest\.source_revision\)\}/);
  assert.match(catalog, /labnote\.js\?v=\$\{escapeHtml\(manifest\.source_revision\)\}/);
});

test("detailed family pages expose a persistent fit-to-screen view with working zoom", () => {
  const catalog = fs.readFileSync(path.resolve("scripts/research-catalog.mjs"), "utf8");
  const client = fs.readFileSync(path.resolve("site/project-graph.js"), "utf8");
  const styles = fs.readFileSync(path.resolve("site/styles.css"), "utf8");
  assert.match(catalog, /data-page-view="standard"/);
  assert.match(catalog, /data-page-view="beta-fit"/);
  assert.match(catalog, /class="map-layout-switch"/);
  assert.match(catalog, />FIT SCREEN<\/button>/);
  assert.match(client, /yurei-family-page-view/);
  assert.doesNotMatch(client, /fitLocked/);
  assert.match(client, /setZoom\(zoom\)/);
  assert.match(styles, /data-page-view="beta-fit".*?overflow: hidden/s);
  assert.match(styles, /data-page-view="beta-fit".*?\.family-notes \{[^}]*overflow-y: auto/s);
  assert.match(styles, /data-page-view="beta-fit".*?\.graph-stage \{[^}]*overflow: hidden/s);
  assert.match(styles, /\.family-notes \{[^}]*max-height: none;[^}]*overflow: visible;[^}]*order: 3/s);
  assert.match(styles, /\.graph-inspector \{[^}]*order: 2/s);
});

test("family cards derive success readouts from published positive outcomes", () => {
  const catalog = fs.readFileSync(path.resolve("scripts/research-catalog.mjs"), "utf8");
  const client = fs.readFileSync(path.resolve("site/app.js"), "utf8");
  assert.match(catalog, /family\.outcomes\.positive \?\? 0/);
  assert.match(catalog, /class="success-rate"/);
  assert.match(catalog, /Positive published labnotes divided by all published labnotes/);
  assert.match(client, /family\.outcomes\.positive \?\? 0/);
  assert.match(client, /class="success-rate"/);
  assert.match(catalog, /class="family-primary" href="projects\//);
  assert.match(client, /OPEN RESEARCH MAP/);
  assert.match(client, /FILTER TO THIS FAMILY/);
  assert.match(catalog, /FILTER TO THIS FAMILY/);
  assert.match(client, /family\.labnote_count === 1 \? "labnote" : "labnotes"/);
  assert.match(catalog, /family\.labnote_count === 1 \? "labnote" : "labnotes"/);
});

test("attention model preserves vectors and distances separately from its 2D projection", () => {
  const notes = [
    { id: "map-001", title: "Audio timing", question: "Can speech timing improve conversational response?", tags: ["audio", "timing"] },
    { id: "map-002", title: "Audio stress", question: "Can speech stress improve conversational response?", tags: ["audio", "stress"] },
    { id: "map-003", title: "Visual panel", question: "Can vision recognize a game panel?", tags: ["vision", "panel"] },
  ];
  const model = buildAttentionModel(notes, notes);
  assert.equal(model.representation.method, "tf-idf");
  assert.equal(model.pairwise_distances.length, 3);
  assert.ok(model.pairwise_distances[0][1] < model.pairwise_distances[0][2]);
  assert.equal(Object.keys(model.projection.points).length, 3);
  assert.match(model.warning, /not evidence of causality/);
});

test("attention projection does not invent a degenerate second axis", () => {
  const notes = [
    { id: "map-001", title: "First", question: "Does alpha work?", tags: ["alpha"] },
    { id: "map-002", title: "Second", question: "Does beta work?", tags: ["beta"] },
  ];
  const model = buildAttentionModel(notes, notes);
  assert.equal(model.projection.normalized_stress, 0);
  assert.deepEqual(Object.values(model.projection.points).map((point) => point[1]), [0, 0]);
});

test("public catalog exports the research-tools interchange boundary", () => {
  const { manifest } = collectCatalog(path.resolve(import.meta.dirname, ".."));
  const interchange = toInterchange(manifest);
  assert.equal(validateCorpus(interchange), interchange);
  assert.equal(interchange.schema, "research-corpus/v1");
  assert.equal(interchange.labnotes.length, manifest.labnotes.length);
});

test("agent discovery is compact, evidence-routed, and explicit about interpretation limits", () => {
  const catalog = fs.readFileSync(path.resolve("scripts/research-catalog.mjs"), "utf8");
  const index = fs.readFileSync(path.resolve("site/index.html"), "utf8");
  const publication = fs.readFileSync(path.resolve("docs/publication.md"), "utf8");
  assert.match(index, /rel="alternate" type="application\/json" href="agent-overview-v1\.json"/);
  assert.match(index, /rel="alternate" type="text\/plain" href="llms\.txt"/);
  assert.match(catalog, /schema: "research-agent-overview\/v1"/);
  assert.match(catalog, /schema: "research-family-overview\/v1"/);
  assert.match(catalog, /Latest work, latest negative result, and earliest published record/);
  assert.match(catalog, /not itself evidence/);
  assert.match(catalog, /Similarity geometry is omitted here/);
  assert.match(catalog, /writeBoundedJson\(path\.join\(graphDirectory, "index\.json"\), familyOverview\(family\), 4096\)/);
  assert.match(publication, /limited to 4096 bytes/);
});

test("licensing policy keeps software and research content separate", () => {
  const policy = fs.readFileSync(path.resolve("LICENSE.md"), "utf8");
  assert.match(policy, /AGPL-3\.0-only — research software/);
  assert.match(policy, /MIT — general apparatus and reusable infrastructure/);
  assert.match(policy, /Research content is separate/);
  assert.match(policy, /does not automatically license files\s+under `docs\/` or `artifacts\/`/);
  assert.match(fs.readFileSync(path.resolve("LICENSES/AGPL-3.0-only.txt"), "utf8"), /GNU AFFERO GENERAL PUBLIC LICENSE/);
});
// SPDX-License-Identifier: AGPL-3.0-only
