import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { assemblePublication } from "../scripts/assemble-pages.mjs";

const fixture = (root, label) => {
  fs.mkdirSync(root, { recursive: true });
  fs.writeFileSync(path.join(root, "index.html"), `<!doctype html><html><head><link rel="canonical" href="https://yurei-so.github.io/research/"><link rel="alternate" type="application/json" href="agent-overview-v1.json"></head><body>${label}<footer><span>REV abc123</span></footer></body></html>`);
  fs.writeFileSync(path.join(root, "research-manifest.json"), JSON.stringify({ label, url: "https://yurei-so.github.io/research/" }));
  fs.writeFileSync(path.join(root, "research-corpus-v1.json"), "{}");
  fs.writeFileSync(path.join(root, "agent-overview-v1.json"), "{}");
  fs.writeFileSync(path.join(root, "llms.txt"), "agent guide");
  fs.writeFileSync(path.join(root, "sitemap.xml"), "<urlset></urlset>");
  fs.mkdirSync(path.join(root, "projects", "demo"), { recursive: true });
  fs.writeFileSync(path.join(root, "projects", "demo", "index.json"), "{}");
  fs.writeFileSync(path.join(root, "projects", "demo", "graph.json"), "{}");
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
  const manifest = assemblePublication({ stable, beta, output, stableSha: "abc123", betaSha: "def456" });
  assert.equal(manifest.stable.source_revision, "abc123");
  assert.match(fs.readFileSync(path.join(output, "index.html"), "utf8"), />stable</);
  const betaHtml = fs.readFileSync(path.join(output, "beta", "index.html"), "utf8");
  assert.match(betaHtml, /noindex,nofollow/);
  assert.match(betaHtml, /https:\/\/yurei-so\.github\.io\/research\/beta\//);
  assert.match(betaHtml, /Beta changes presentation only/);
  assert.doesNotMatch(betaHtml, /rel="alternate"/);
  assert.equal(fs.readFileSync(path.join(output, "beta", "robots.txt"), "utf8"), "User-agent: *\nDisallow: /\n");
  for (const relative of ["research-manifest.json", "research-corpus-v1.json", "agent-overview-v1.json", "llms.txt", "sitemap.xml", "projects/demo/index.json", "projects/demo/graph.json"]) {
    assert.equal(fs.existsSync(path.join(output, "beta", relative)), false, `${relative} must not exist in beta`);
    assert.equal(fs.existsSync(path.join(output, relative)), true, `${relative} must remain available on stable`);
  }
  assert.ok(fs.existsSync(path.join(output, "publication-switch.css")));
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
