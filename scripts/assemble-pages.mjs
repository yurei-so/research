#!/usr/bin/env node
// SPDX-License-Identifier: AGPL-3.0-only

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const allowedExtensions = new Set([".css", ".html", ".js", ".json", ".png", ".txt", ".xml"]);
const allowedExtensionless = new Set([".nojekyll"]);
const stableBase = "https://yurei-so.github.io/research/";
const betaBase = `${stableBase}beta/`;

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
    fs.writeFileSync(file, content);
  }
  fs.writeFileSync(path.join(root, "robots.txt"), "User-agent: *\nDisallow: /\n");
  fs.writeFileSync(path.join(root, "BETA.txt"), "Yurei Research beta publication\nNot canonical. Not production.\n");
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
