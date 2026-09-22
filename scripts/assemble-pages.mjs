#!/usr/bin/env node
// SPDX-License-Identifier: AGPL-3.0-only

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const allowedExtensions = new Set([".css", ".html", ".js", ".json", ".png", ".txt", ".xml"]);
const allowedExtensionless = new Set([".nojekyll"]);
const stableBase = "https://yurei-so.github.io/research/";
const betaBase = `${stableBase}beta/`;
const betaMachineFiles = new Set(["research-manifest.json", "research-corpus-v1.json", "agent-overview-v1.json", "llms.txt", "sitemap.xml"]);

function filesUnder(root) {
  const files = [];
  const walk = (directory) => {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const target = path.join(directory, entry.name);
      if (entry.isSymbolicLink()) throw new Error(`symbolic links are not publishable: ${target}`);
      if (entry.isDirectory()) walk(target);
      else if (entry.isFile()) files.push(target);
      else throw new Error(`unsupported publication entry: ${target}`);
    }
  };
  walk(root);
  return files;
}

function validateBuild(root, label) {
  if (!fs.statSync(root, { throwIfNoEntry: false })?.isDirectory()) throw new Error(`${label} build is missing: ${root}`);
  for (const required of ["index.html", "research-manifest.json", "robots.txt", ".nojekyll"]) {
    if (!fs.statSync(path.join(root, required), { throwIfNoEntry: false })?.isFile()) throw new Error(`${label} build is missing ${required}`);
  }
  for (const file of filesUnder(root)) {
    const name = path.basename(file);
    const extension = path.extname(name).toLowerCase();
    if (!allowedExtensions.has(extension) && !allowedExtensionless.has(name)) {
      throw new Error(`${label} build contains a non-public file type: ${path.relative(root, file)}`);
    }
  }
}

function copyTree(source, destination) {
  fs.cpSync(source, destination, { recursive: true, dereference: false, errorOnExist: false });
}

function markBeta(root) {
  for (const file of filesUnder(root)) {
    const extension = path.extname(file).toLowerCase();
    if (![".html", ".json", ".txt", ".xml"].includes(extension)) continue;
    let content = fs.readFileSync(file, "utf8").replaceAll(stableBase, betaBase);
    if (extension === ".html" && !/name=["']robots["']/i.test(content)) {
      content = content.replace(/<head>/i, '<head><meta name="robots" content="noindex,nofollow">');
    }
    if (extension === ".html") {
      content = content.replace(/<link\s+rel=["']alternate["'][^>]*>/gi, "");
    }
    fs.writeFileSync(file, content);
  }
  for (const file of filesUnder(root)) {
    const relative = path.relative(root, file).split(path.sep).join("/");
    if (betaMachineFiles.has(relative) || (/^projects\/[^/]+\/(?:index|graph)\.json$/).test(relative)) fs.rmSync(file);
  }
  fs.writeFileSync(path.join(root, "robots.txt"), "User-agent: *\nDisallow: /\n");
  fs.writeFileSync(path.join(root, "BETA.txt"), "Yurei Research visual beta\nNot canonical. Not production. Labnote content, research tools, and machine-readable research interfaces remain stable-only.\n");
}

const escapeHtml = (value) => String(value).replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");

function publicationRoute(relative) {
  const normalized = relative.split(path.sep).join("/");
  return normalized === "index.html" ? "" : normalized.replace(/index\.html$/, "");
}

function revisionControl({ channel, revision, stableUrl, betaUrl, summaryHtml }) {
  const stable = channel === "stable" ? `<span aria-current="page">STABLE · ${escapeHtml(revision.slice(0, 12))}</span>`
    : stableUrl ? `<a href="${escapeHtml(stableUrl)}">STABLE</a>` : '<span class="unavailable">STABLE · ROUTE UNAVAILABLE</span>';
  const beta = channel === "beta" ? `<span aria-current="page">BETA · ${escapeHtml(revision.slice(0, 12))}</span>`
    : betaUrl ? `<a href="${escapeHtml(betaUrl)}">BETA</a>` : '<span class="unavailable">BETA · ROUTE UNAVAILABLE</span>';
  const summary = summaryHtml ?? `REV ${escapeHtml(revision.slice(0, 12))}`;
  return `<details class="publication-revision"><summary>${summary}</summary><div class="publication-revision-menu"><strong>PUBLICATION VIEW</strong>${stable}${beta}<p>Beta changes presentation only. It does not revise labnote content or research tools, and exposes no beta machine-readable research interface.</p><a href="${stableBase}deployment-manifest.json">VIEW DEPLOYMENT MANIFEST</a></div></details>`;
}

function addRevisionControls(output, channel, revision) {
  const root = channel === "stable" ? output : path.join(output, "beta");
  const betaRoot = path.join(output, "beta") + path.sep;
  for (const file of filesUnder(root).filter((entry) => path.extname(entry).toLowerCase() === ".html"
    && (channel !== "stable" || !entry.startsWith(betaRoot)))) {
    const relative = path.relative(root, file);
    const route = publicationRoute(relative);
    const stableFile = path.join(output, relative);
    const betaFile = path.join(output, "beta", relative);
    const options = { channel, revision,
      stableUrl: fs.existsSync(stableFile) ? `${stableBase}${route}` : null,
      betaUrl: fs.existsSync(betaFile) ? `${betaBase}${route}` : null };
    const control = revisionControl(options);
    const heroControl = revisionControl({ ...options, summaryHtml: `<b id="revision">${escapeHtml(revision.slice(0, 12))}</b> REVISION` });
    let content = fs.readFileSync(file, "utf8");
    content = content.replace(/<b id="revision">[^<]+<\/b> REVISION/, heroControl);
    content = content.replace(/<span id="generated">(CATALOG [^<]+?) \/ REV [0-9a-f]+<\/span>/i, `<span>$1 / ${control}</span><span id="generated" hidden></span>`);
    content = content.replace(/<span>REV [0-9a-f]+<\/span>/gi, `<span>${control}</span>`);
    content = content.replace(/<head>/i, `<head><link rel="stylesheet" href="${stableBase}publication-switch.css">`);
    fs.writeFileSync(file, content);
  }
}

export function assemblePublication({ stable, beta, output, stableSha, betaSha }) {
  validateBuild(stable, "stable");
  validateBuild(beta, "beta");
  fs.rmSync(output, { recursive: true, force: true });
  fs.mkdirSync(output, { recursive: true });
  copyTree(stable, output);
  copyTree(beta, path.join(output, "beta"));
  markBeta(path.join(output, "beta"));
  const manifest = {
    schema: "yurei-pages-publication/v1",
    stable: { source_branch: "main", source_revision: stableSha, path: "/" },
    previews: [{ channel: "beta", source_branch: "beta", source_revision: betaSha, path: "/beta/", canonical: false }],
  };
  fs.writeFileSync(path.join(output, "deployment-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  fs.copyFileSync(path.resolve(import.meta.dirname, "..", "site", "publication-switch.css"), path.join(output, "publication-switch.css"));
  addRevisionControls(output, "stable", stableSha);
  addRevisionControls(output, "beta", betaSha);
  validateBuild(output, "assembled publication");
  return manifest;
}

const value = (args, name) => {
  const index = args.indexOf(name);
  return index < 0 ? null : args[index + 1];
};

if (path.resolve(process.argv[1] ?? "") === path.resolve(import.meta.filename)) {
  const args = process.argv.slice(2);
  const options = Object.fromEntries([
    ["stable", value(args, "--stable")],
    ["beta", value(args, "--beta")],
    ["output", value(args, "--output")],
    ["stableSha", value(args, "--stable-sha")],
    ["betaSha", value(args, "--beta-sha")],
  ]);
  if (Object.values(options).some((entry) => !entry)) {
    throw new Error("usage: assemble-pages --stable DIR --beta DIR --output DIR --stable-sha SHA --beta-sha SHA");
  }
  const manifest = assemblePublication(options);
  console.log(`Assembled stable ${manifest.stable.source_revision} and beta ${manifest.previews[0].source_revision}.`);
}
