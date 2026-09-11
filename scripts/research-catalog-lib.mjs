import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const statuses = new Set(["planned", "running", "awaiting-review", "complete", "aborted"]);
const outcomes = new Set(["positive", "negative", "mixed", "inconclusive", "pending", "not-applicable"]);
const relationTypes = new Set(["motivated-by", "reuses-data", "reuses-apparatus", "extends", "ablates", "replicates", "supports", "challenges", "supersedes"]);
const allowedKeys = new Set(["schema_version", "id", "title", "date", "status", "outcome", "question", "tags", "lineage", "relations", "publish"]);
const idPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*-\d{3}$/;
const tagPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

function fail(file, message) {
  throw new Error(`${file}: ${message}`);
}

function scalar(value, file) {
  const trimmed = value.trim();
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  if (/^-?\d+$/.test(trimmed)) return Number(trimmed);
  if (trimmed.startsWith('"') || trimmed.startsWith("[")) {
    try { return JSON.parse(trimmed); } catch { fail(file, "invalid JSON-style front matter value"); }
  }
  return trimmed;
}

export function parseLabnote(text, file = "labnote") {
  const match = text.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!match) fail(file, "missing YAML front matter");
  const metadata = {};
  for (const line of match[1].split("\n")) {
    if (!line.trim()) continue;
    const field = line.match(/^([a-z_]+):\s*(.*)$/);
    if (!field) fail(file, `unsupported front matter syntax: ${line}`);
    const [, key, value] = field;
    if (!allowedKeys.has(key)) fail(file, `unknown public metadata field ${key}`);
    if (Object.hasOwn(metadata, key)) fail(file, `duplicate field ${key}`);
    metadata[key] = scalar(value, file);
  }
  return { metadata, body: text.slice(match[0].length) };
}

function validateArray(value, field, file) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) fail(file, `${field} must be a string array`);
}

export function validateMetadata(metadata, file = "labnote") {
  for (const key of allowedKeys) if (key !== "relations" && !Object.hasOwn(metadata, key)) fail(file, `missing ${key}`);
  if (metadata.schema_version !== 1) fail(file, "unsupported schema_version");
  if (typeof metadata.id !== "string" || !idPattern.test(metadata.id)) fail(file, "invalid id");
  for (const key of ["title", "question"]) if (typeof metadata[key] !== "string" || !metadata[key].trim()) fail(file, `invalid ${key}`);
  if (metadata.title.length > 160 || metadata.question.length > 600) fail(file, "public text field is too long");
  if (typeof metadata.date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(metadata.date) || Number.isNaN(Date.parse(`${metadata.date}T00:00:00Z`))) fail(file, "invalid date");
  if (!statuses.has(metadata.status)) fail(file, "invalid status");
  if (!outcomes.has(metadata.outcome)) fail(file, "invalid outcome");
  if (typeof metadata.publish !== "boolean") fail(file, "publish must be boolean");
  validateArray(metadata.tags, "tags", file);
  validateArray(metadata.lineage, "lineage", file);
  if (metadata.tags.length > 24 || new Set(metadata.tags).size !== metadata.tags.length || metadata.tags.some((tag) => !tagPattern.test(tag))) fail(file, "invalid or duplicate tag");
  if (metadata.lineage.length > 24 || new Set(metadata.lineage).size !== metadata.lineage.length || metadata.lineage.some((id) => !idPattern.test(id))) fail(file, "invalid or duplicate lineage id");
  if (metadata.lineage.includes(metadata.id)) fail(file, "self lineage is not allowed");
  if (metadata.relations !== undefined) {
    if (!Array.isArray(metadata.relations) || metadata.relations.length > 24) fail(file, "relations must be an array of at most 24 objects");
    const seen = new Set();
    for (const relation of metadata.relations) {
      if (!relation || typeof relation !== "object" || Array.isArray(relation)) fail(file, "each relation must be an object");
      if (Object.keys(relation).some((key) => !new Set(["target", "type", "rationale"]).has(key))) fail(file, "unknown relation field");
      if (typeof relation.target !== "string" || !idPattern.test(relation.target) || relation.target === metadata.id) fail(file, "invalid relation target");
      if (!relationTypes.has(relation.type)) fail(file, `invalid relation type ${relation.type}`);
      if (typeof relation.rationale !== "string" || !relation.rationale.trim() || relation.rationale.length > 400) fail(file, "invalid relation rationale");
      const identity = `${relation.type}:${relation.target}`;
      if (seen.has(identity)) fail(file, `duplicate relation ${identity}`);
      seen.add(identity);
    }
  }
}

function walk(directory) {
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...walk(target));
    else if (entry.isFile() && entry.name.endsWith(".md") && entry.name !== "README.md" && target.includes(`${path.sep}docs${path.sep}labnotes${path.sep}`)) files.push(target);
  }
  return files;
}

function familyFromId(id) { return id.replace(/-\d{3}$/, ""); }
function familyTitle(id) { return id.split("-").map((part) => part[0].toUpperCase() + part.slice(1)).join(" "); }

export function collectCatalog(root) {
  const records = walk(path.join(root, "experiments")).sort().map((file) => {
    const relative = path.relative(root, file).split(path.sep).join("/");
    const parsed = parseLabnote(fs.readFileSync(file, "utf8"), relative);
    validateMetadata(parsed.metadata, relative);
    return { ...parsed, file, relative };
  });
  const byId = new Map();
  for (const record of records) {
    if (byId.has(record.metadata.id)) fail(record.relative, `duplicate id ${record.metadata.id}`);
    byId.set(record.metadata.id, record);
  }
  for (const record of records) for (const parent of [...record.metadata.lineage, ...(record.metadata.relations ?? []).map((relation) => relation.target)]) {
    if (!byId.has(parent)) fail(record.relative, `unknown relation target ${parent}`);
    if (record.metadata.publish && !byId.get(parent).metadata.publish) fail(record.relative, `published note references unpublished relation target ${parent}`);
  }
  const published = records.filter((record) => record.metadata.publish);
  const labnotes = published.map(({ metadata }) => ({
    id: metadata.id,
    family: familyFromId(metadata.id),
    title: metadata.title,
    date: metadata.date,
    status: metadata.status,
    outcome: metadata.outcome,
    question: metadata.question,
    tags: [...metadata.tags],
    lineage: [...metadata.lineage],
    relations: [...(metadata.relations ?? []), ...metadata.lineage.filter((target) => !(metadata.relations ?? []).some((relation) => relation.target === target))
      .map((target) => ({ target, type: "follows", rationale: "Recorded as the preceding labnote in the original lineage metadata." }))],
    href: `labnotes/${metadata.id}/`,
  })).sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id));
  for (const note of labnotes) {
    note.timeline = {
      follows: [...note.lineage],
      continued_by: labnotes.filter((candidate) => candidate.lineage.includes(note.id)).map((candidate) => candidate.id)
        .sort((a, b) => a.localeCompare(b)),
    };
  }
  const families = [...new Set(labnotes.map((note) => note.family))].sort().map((id) => {
    const notes = labnotes.filter((note) => note.family === id);
    const latest = [...notes].sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id))[0];
    return { id, title: familyTitle(id), labnote_count: notes.length, latest_labnote_id: latest.id,
      has_graph: notes.some((note) => note.relations.length > 0),
      outcomes: Object.fromEntries([...outcomes].sort().map((outcome) => [outcome, notes.filter((note) => note.outcome === outcome).length]).filter(([, count]) => count)) };
  });
  let revision = "unknown";
  let generatedAt = new Date(0).toISOString();
  try {
    const options = { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] };
    revision = execFileSync("git", ["rev-parse", "--short=12", "HEAD"], options).trim();
    const epoch = Number(process.env.SOURCE_DATE_EPOCH ?? execFileSync("git", ["show", "-s", "--format=%ct", "HEAD"], options).trim());
    generatedAt = new Date(epoch * 1000).toISOString();
  } catch {}
  return { records, manifest: { schema_version: 1, generated_at: generatedAt, source_revision: revision, families, labnotes } };
}

export function escapeHtml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function plainMarkdown(value) {
  return value
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[`*_~]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function extractResultSummary(markdown, fallback = "") {
  const heading = markdown.match(/^##\s+(?:results?|findings?)\s*$/im);
  if (!heading) return plainMarkdown(fallback);
  const remaining = markdown.slice((heading.index ?? 0) + heading[0].length);
  const section = remaining.split(/^##\s+/m, 1)[0];
  const lines = section.replace(/\r/g, "").split("\n");
  let paragraph = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      if (paragraph.length) break;
      continue;
    }
    if (trimmed.startsWith("|") || /^#{1,6}\s/.test(trimmed) || /^[-*]\s/.test(trimmed)) {
      if (paragraph.length) break;
      continue;
    }
    paragraph.push(trimmed);
  }
  const summary = plainMarkdown(paragraph.join(" ")) || plainMarkdown(fallback);
  return summary.length <= 280 ? summary : `${summary.slice(0, 277).trimEnd()}…`;
}

function inline(text) {
  let value = escapeHtml(text);
  value = value.replace(/`([^`]+)`/g, "<code>$1</code>");
  value = value.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  value = value.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, href) => {
    if (/^(?:https?:\/\/|\.\.\/|\.\/|#)/.test(href) && !/["'<>]/.test(href)) return `<a href="${href}">${label}</a>`;
    return `${label} <code>${escapeHtml(href)}</code>`;
  });
  return value;
}

export function renderMarkdown(markdown) {
  const lines = markdown.replace(/\r/g, "").split("\n");
  const html = [];
  let paragraph = [];
  let list = null;
  let code = null;
  const flushParagraph = () => { if (paragraph.length) { html.push(`<p>${inline(paragraph.join(" "))}</p>`); paragraph = []; } };
  const flushList = () => { if (list) { html.push(`</${list}>`); list = null; } };
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (code !== null) {
      if (line.startsWith("```")) { html.push(`<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`); code = null; }
      else code.push(line);
      continue;
    }
    if (line.startsWith("```")) { flushParagraph(); flushList(); code = []; continue; }
    if (line.trim().startsWith("|") && line.trim().endsWith("|")
        && /^\s*\|(?:\s*:?-+:?\s*\|)+\s*$/.test(lines[index + 1] ?? "")) {
      flushParagraph(); flushList();
      const cells = (row) => row.trim().slice(1, -1).split("|").map((cell) => cell.trim());
      const headers = cells(line);
      index += 2;
      const rows = [];
      while (index < lines.length && lines[index].trim().startsWith("|") && lines[index].trim().endsWith("|")) {
        rows.push(cells(lines[index])); index += 1;
      }
      index -= 1;
      html.push(`<div class="table-wrap"><table><thead><tr>${headers.map((cell) => `<th>${inline(cell)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${inline(cell)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
      continue;
    }
    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) { flushParagraph(); flushList(); const level = Math.min(heading[1].length + 1, 5); html.push(`<h${level}>${inline(heading[2])}</h${level}>`); continue; }
    const item = line.match(/^\s*([-*]|\d+\.)\s+(.+)$/);
    if (item) { flushParagraph(); const type = item[1].endsWith(".") ? "ol" : "ul"; if (list !== type) { flushList(); list = type; html.push(`<${type}>`); } html.push(`<li>${inline(item[2])}</li>`); continue; }
    if (line.startsWith("> ")) { flushParagraph(); flushList(); html.push(`<blockquote>${inline(line.slice(2))}</blockquote>`); continue; }
    if (!line.trim()) { flushParagraph(); flushList(); continue; }
    if (/^[-| :]+$/.test(line.trim())) continue;
    paragraph.push(line.trim());
  }
  flushParagraph(); flushList();
  if (code !== null) html.push(`<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`);
  return html.join("\n");
}
