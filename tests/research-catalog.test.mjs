import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { collectCatalog, escapeHtml, extractResultSummary, parseLabnote, renderMarkdown, validateMetadata } from "../scripts/research-catalog-lib.mjs";
import { socialCardSvg } from "../scripts/social-card.mjs";
import { buildAttentionModel } from "../scripts/attention-map.mjs";

const metadata = { schema_version: 1, id: "test-001", title: "Test", date: "2026-09-08", status: "complete", outcome: "negative", question: "Did it work?", tags: ["negative-result"], lineage: [], publish: true };

test("repository catalog validates and exposes only allowlisted metadata", () => {
  const { records, manifest } = collectCatalog(path.resolve(import.meta.dirname, ".."));
  assert.ok(records.length >= 37);
  assert.ok(manifest.labnotes.some((note) => note.id === "prosody-001"));
  assert.ok(manifest.labnotes.some((note) => note.id === "voxel-guidance-001"));
  assert.equal(manifest.families.length, 5);
  assert.ok(manifest.families.every((family) => !Object.hasOwn(family, "status")));
  assert.deepEqual(Object.keys(manifest.labnotes[0]).sort(), ["date", "family", "href", "id", "lineage", "outcome", "question", "relations", "status", "tags", "timeline", "title"]);
  assert.ok(manifest.labnotes.every((note) => !JSON.stringify(note).includes("/home/")));
  const finalComposition = manifest.labnotes.find((note) => note.id === "composition-006");
  assert.deepEqual(finalComposition.timeline, { follows: ["composition-005"], continued_by: [] });
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
