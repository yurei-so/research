// SPDX-License-Identifier: AGPL-3.0-only

import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { collectDispatches, parseDispatch, renderDispatchPage } from "../scripts/dispatches.mjs";

const metadata = {
  schema_version: 1,
  id: "dispatch-001",
  title: "The controlled run",
  date: "2026-10-05",
  status: "draft",
  lede: "A bounded field report.",
  tags: ["field-test"],
  related_labnotes: [],
  publish: false,
};
const source = (overrides = {}, body = "## Observed\nThe test moved.") => `---\n${Object.entries({ ...metadata, ...overrides }).map(([key, value]) => `${key}: ${JSON.stringify(value)}`).join("\n")}\n---\n${body}`;

test("dispatch schema distinguishes drafts from published posts", () => {
  assert.equal(parseDispatch(source()).metadata.publish, false);
  assert.throws(() => parseDispatch(source({ publish: true }), "dispatch.md"), /status: published/);
  assert.throws(() => parseDispatch(source({ id: "labnote-001" }), "dispatch.md"), /expected dispatch-NNN/);
});

test("dispatch metadata fails closed and validates linked labnote IDs", () => {
  assert.throws(() => parseDispatch(source({ private_path: "/tmp/secret" }), "dispatch.md"), /unknown public metadata field/);
  assert.throws(() => parseDispatch(source({ related_labnotes: ["not-an-id"] }), "dispatch.md"), /invalid or duplicate related_labnotes/);
  assert.throws(() => parseDispatch(source({ tags: ["fine", "Not Fine"] }), "dispatch.md"), /invalid or duplicate tags/);
});

test("catalog reads ordinary Markdown dispatches without exposing draft as public", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "research-dispatches-"));
  const directory = path.join(root, "dispatches");
  fs.mkdirSync(directory);
  fs.writeFileSync(path.join(directory, "dispatch-001.md"), source());
  const records = collectDispatches(root);
  assert.equal(records.length, 1);
  assert.equal(records[0].metadata.publish, false);
  fs.writeFileSync(path.join(directory, "dispatch-002.md"), source({ id: "dispatch-001" }));
  assert.throws(() => collectDispatches(root), /duplicate id dispatch-001/);
  fs.rmSync(root, { recursive: true, force: true });
});

test("published Dispatch page is escaped, separately routed, and labelled as BlogPosting", () => {
  const record = { ...parseDispatch(source({ status: "published", publish: true, title: "Test <debrief>" }, "![Frame](assets/dispatch-001/frame.png)")), relative: "dispatches/dispatch-001-test.md" };
  const html = renderDispatchPage(record, "abc123");
  assert.match(html, /schema\.org\/BlogPosting/);
  assert.match(html, /Test &lt;debrief&gt;/);
  assert.match(html, /dispatches\/dispatch-001\//);
  assert.match(html, /View canonical Markdown/);
  assert.match(html, /assets\/styles\.css\?v=abc123/);
  assert.match(html, /src="\.\.\/\.\.\/dispatches\/assets\/dispatch-001\/frame\.png"/);
  assert.doesNotMatch(html, /<script/);
});

test("YouTube embeds use a strict ID, privacy-enhanced host, and narrow frame policy", () => {
  const body = '## Video\n\n:::youtube tR0AT65-AZs "VRageCage D1V3R8 — camera feed"';
  const record = { ...parseDispatch(source({ status: "published", publish: true }, body)), relative: "dispatches/dispatch-001-test.md" };
  const html = renderDispatchPage(record, "abc123");
  assert.match(html, /frame-src https:\/\/www\.youtube-nocookie\.com/);
  assert.match(html, /src="https:\/\/www\.youtube-nocookie\.com\/embed\/tR0AT65-AZs"/);
  assert.match(html, /loading="lazy" referrerpolicy="strict-origin-when-cross-origin"/);
  assert.match(html, /allow="picture-in-picture; web-share"/);
  assert.doesNotMatch(html, /accelerometer|encrypted-media|gyroscope/);
  assert.match(html, /Watch on YouTube/);

  const invalid = { ...parseDispatch(source({ status: "published", publish: true }, ':::youtube invalid "Not an embed"')), relative: "dispatches/dispatch-001-test.md" };
  assert.doesNotMatch(renderDispatchPage(invalid, "abc123"), /<iframe/);
});

test("published Dispatch 001 visibly links the relevant formal research records", () => {
  const root = path.resolve(import.meta.dirname, "..");
  const record = collectDispatches(root).find((item) => item.metadata.id === "dispatch-001");
  assert.deepEqual(record.metadata.related_labnotes, ["multiview-cameras-001", "voxel-guidance-006"]);
  const html = renderDispatchPage(record, "abc123");
  assert.match(html, /href="\.\.\/\.\.\/labnotes\/multiview-cameras-001\/"/);
  assert.match(html, /href="\.\.\/\.\.\/labnotes\/voxel-guidance-006\/"/);
});
