import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { assemblePublication } from "../scripts/assemble-pages.mjs";

const fixture = (root, label) => {
  fs.mkdirSync(root, { recursive: true });
  fs.writeFileSync(path.join(root, "index.html"), `<!doctype html><html><head><link rel="canonical" href="https://yurei-so.github.io/research/"></head><body>${label}</body></html>`);
  fs.writeFileSync(path.join(root, "research-manifest.json"), JSON.stringify({ label, url: "https://yurei-so.github.io/research/" }));
  fs.writeFileSync(path.join(root, "robots.txt"), "User-agent: *\nAllow: /research/\n");
  fs.writeFileSync(path.join(root, ".nojekyll"), "");
};

test("assembles allowlisted stable and non-canonical beta publication trees", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "research-pages-"));
  const stable = path.join(temporary, "stable");
  const beta = path.join(temporary, "beta");
  const output = path.join(temporary, "publication");
  fixture(stable, "stable");
  fixture(beta, "beta");
  const manifest = assemblePublication({ stable, beta, output, stableSha: "stable123", betaSha: "beta456" });
  assert.equal(manifest.stable.source_revision, "stable123");
  assert.match(fs.readFileSync(path.join(output, "index.html"), "utf8"), />stable</);
  const betaHtml = fs.readFileSync(path.join(output, "beta", "index.html"), "utf8");
  assert.match(betaHtml, /noindex,nofollow/);
  assert.match(betaHtml, /https:\/\/yurei-so\.github\.io\/research\/beta\//);
  assert.equal(fs.readFileSync(path.join(output, "beta", "robots.txt"), "utf8"), "User-agent: *\nDisallow: /\n");
  assert.ok(fs.existsSync(path.join(output, "deployment-manifest.json")));
});

test("rejects unexpected source-like files from a build", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "research-pages-reject-"));
  const stable = path.join(temporary, "stable");
  const beta = path.join(temporary, "beta");
  fixture(stable, "stable");
  fixture(beta, "beta");
  fs.writeFileSync(path.join(beta, "secret.env"), "nope");
  assert.throws(() => assemblePublication({ stable, beta, output: path.join(temporary, "out"), stableSha: "a", betaSha: "b" }), /non-public file type/);
});
