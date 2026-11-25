#!/usr/bin/env node
// SPDX-License-Identifier: AGPL-3.0-only

import { isDeepStrictEqual } from "node:util";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const allowedExtensions = new Set([".css", ".html", ".js", ".json", ".mp4", ".png", ".txt", ".xml"]);
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
    if (extension === ".mp4") {
      const relative = path.relative(root, file).split(path.sep).join("/");
      if (!/^labnotes\/([a-z0-9]+(?:-[a-z0-9]+)*-\d{3})\/assets\/\1\/[A-Za-z0-9][A-Za-z0-9._-]*\.mp4$/i.test(relative)) {
        throw new Error(`${label} build contains a video outside an explicit labnote asset route: ${relative}`);
      }
      if (fs.statSync(file).size > 25 * 1024 * 1024) throw new Error(`${label} build contains an MP4 larger than 25 MiB: ${relative}`);
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

function relativePageUrl(fromFile, targetFile) {
  const relative = path.relative(path.dirname(fromFile), targetFile).split(path.sep).join("/");
  if (!relative.endsWith("index.html")) return relative;
  const directory = relative.slice(0, -"index.html".length);
  return directory || "./";
}

// Approve alternates by canonical family ID after presentation and evidence review.
const approvedBetaFamilies = new Set([]);

function eligibleFamilyRoutes(output, approvedFamilies) {
  const routes = new Set();
  for (const family of approvedFamilies) {
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(family)) throw new Error(`Invalid beta family ID: ${family}`);
    const relative = `projects/${family}/index.html`;
    const stable = path.join(output, relative);
    const beta = path.join(output, "beta", relative);
    if (!fs.existsSync(stable) || !fs.existsSync(beta)) continue;
    const readEvidence = (file) => {
      const embedded = fs.readFileSync(file, "utf8").match(/<template id="project-graph-data">([\s\S]*?)<\/template>/);
      if (!embedded) return null;
      const { family: identity, notes, relations } = JSON.parse(embedded[1]);
      return identity?.id === family && Array.isArray(notes) && notes.length && Array.isArray(relations)
        ? { identity, notes, relations } : null;
    };
    const evidence = readEvidence(stable);
    if (evidence && isDeepStrictEqual(evidence, readEvidence(beta))) routes.add(relative);
  }
  return routes;
}

function stableAlias(file, stableFile) {
  const href = escapeHtml(relativePageUrl(file, stableFile));
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><meta http-equiv="refresh" content="0; url=${href}"><title>Yūrei Research · Stable</title></head><body><p><a href="${href}">Continue to the stable publication</a></p></body></html>`;
}

function channelSwitch({ channel, stableUrl, betaUrl }) {
  const stable = channel === "stable" ? '<span aria-current="page">STABLE</span>'
    : `<a href="${escapeHtml(stableUrl)}">STABLE</a>`;
  const beta = channel === "beta" ? '<span aria-current="page">BETA VIEW</span>'
    : betaUrl ? `<a href="${escapeHtml(betaUrl)}">BETA VIEW</a>` : "";
  return `<nav class="publication-channel-switch" aria-label="Publication channel">${stable}${beta}</nav>`;
}

function revisionControl({ channel, revision, stableUrl, betaUrl, manifestUrl }) {
  const disclosure = betaUrl ? "<p>Beta changes presentation only. The stable labnotes remain the canonical record.</p>" : "";
  return `<details class="publication-revision"><summary>REV ${escapeHtml(revision.slice(0, 12))}</summary><div class="publication-revision-menu">${channelSwitch({ channel, stableUrl, betaUrl })}${disclosure}<a href="${escapeHtml(manifestUrl)}">VIEW DEPLOYMENT MANIFEST</a></div></details>`;
}

function addRevisionControls(output, channel, revision, eligibleRoutes) {
  const root = channel === "stable" ? output : path.join(output, "beta");
  const betaRoot = path.join(output, "beta") + path.sep;
  for (const file of filesUnder(root).filter((entry) => path.extname(entry).toLowerCase() === ".html"
    && (channel !== "stable" || !entry.startsWith(betaRoot)))) {
    const relative = path.relative(root, file);
    const stableFile = path.join(output, relative);
    const betaFile = path.join(output, "beta", relative);
    const eligible = eligibleRoutes.has(relative.split(path.sep).join("/"));
    if (channel === "beta" && !eligible) {
      fs.writeFileSync(file, stableAlias(file, fs.existsSync(stableFile) ? stableFile : path.join(output, "index.html")));
      continue;
    }
    const options = { channel, revision,
      stableUrl: fs.existsSync(stableFile) ? relativePageUrl(file, stableFile) : null,
      betaUrl: eligible ? relativePageUrl(file, betaFile) : null,
      manifestUrl: path.relative(path.dirname(file), path.join(output, "deployment-manifest.json")).split(path.sep).join("/") };
    const control = revisionControl(options);
    const publicationSwitch = channelSwitch(options);
    const switchStyles = path.relative(path.dirname(file), path.join(output, "publication-switch.css")).split(path.sep).join("/");
    let content = fs.readFileSync(file, "utf8");
    content = content.replace(/<header class="terminal-bar">([\s\S]*?)<\/header>/i, (header) => {
      if (header.includes("publication-channel-switch")) return header;
      return header.replace(/<span(?: class="stable-label")?>[^<]*<\/span>\s*<\/header>$/i, `${publicationSwitch}</header>`);
    });
    content = content.replace(/<span id="generated">(CATALOG [^<]+?) \/ REV [0-9a-f]+<\/span>/i, `<span>$1 / ${control}</span><span id="generated" hidden></span>`);
    content = content.replace(/<span>REV [0-9a-f]+<\/span>/gi, `<span>${control}</span>`);
    content = content.replace(/<head>/i, `<head><link rel="stylesheet" href="${escapeHtml(switchStyles)}">`);
    fs.writeFileSync(file, content);
  }
}

export function assemblePublication({ stable, beta, output, stableSha, betaSha, approvedFamilies = approvedBetaFamilies }) {
  validateBuild(stable, "stable");
  validateBuild(beta, "beta");
  fs.rmSync(output, { recursive: true, force: true });
  fs.mkdirSync(output, { recursive: true });
  copyTree(stable, output);
  copyTree(beta, path.join(output, "beta"));
  markBeta(path.join(output, "beta"));
  const eligibleRoutes = eligibleFamilyRoutes(output, approvedFamilies);
  const manifest = {
    schema: "yurei-pages-publication/v1",
    stable: { source_branch: "main", source_revision: stableSha, path: "/" },
    previews: [{ channel: "beta", source_branch: "beta", source_revision: betaSha, path: "/beta/", canonical: false }],
  };
  fs.writeFileSync(path.join(output, "deployment-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  fs.copyFileSync(path.resolve(import.meta.dirname, "..", "site", "publication-switch.css"), path.join(output, "publication-switch.css"));
  addRevisionControls(output, "stable", stableSha, eligibleRoutes);
  addRevisionControls(output, "beta", betaSha, eligibleRoutes);
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
