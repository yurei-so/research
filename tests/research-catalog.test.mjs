import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { collectCatalog, escapeHtml, parseLabnote, renderMarkdown, validateMetadata } from "../scripts/research-catalog-lib.mjs";

const metadata = { schema_version: 1, id: "test-001", title: "Test", date: "2026-09-08", status: "complete", outcome: "negative", question: "Did it work?", tags: ["negative-result"], lineage: [], publish: true };

test("repository catalog validates and exposes only allowlisted metadata", () => {
  const { records, manifest } = collectCatalog(path.resolve(import.meta.dirname, ".."));
  assert.ok(records.length >= 37);
  assert.ok(manifest.labnotes.some((note) => note.id === "prosody-001"));
  assert.ok(manifest.labnotes.some((note) => note.id === "voxel-guidance-001"));
  assert.equal(manifest.families.length, 5);
  assert.ok(manifest.families.every((family) => !Object.hasOwn(family, "status")));
  assert.deepEqual(Object.keys(manifest.labnotes[0]).sort(), ["date", "family", "href", "id", "lineage", "outcome", "question", "relations", "status", "tags", "title"]);
  assert.ok(manifest.labnotes.every((note) => !JSON.stringify(note).includes("/home/")));
  const finalComposition = manifest.labnotes.find((note) => note.id === "composition-006");
  assert.deepEqual(finalComposition.relations, { follows: ["composition-005"], continued_by: [] });
  const firstComposition = manifest.labnotes.find((note) => note.id === "composition-001");
  assert.deepEqual(firstComposition.relations, { follows: [], continued_by: ["composition-002"] });
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
