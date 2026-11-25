// SPDX-License-Identifier: AGPL-3.0-only
import { escapeHtml as html } from "./research-catalog-lib.mjs";

export const programs = [
  ["interactive-language", "Interactive Language and Communication", ["composition", "prosody", "narrative-steering"], "How can small systems improve communication without exceeding inference and human-review budgets?"],
  ["grounded-perception", "Grounded Perception and Behavior", ["voxel-guidance", "zenith"], "What compact representations retain useful task signals on unseen inputs?"],
  ["embodied-observation", "Embodied Observation and Control", ["multiview-cameras", "vehicle-navigation", "game-session-observation"], "What can bounded sensors and simulation receipts establish about observation and control?"],
  ["research-systems", "Research Systems and Provenance", ["meta-research"], "How can research apparatus make evidence easier to inspect while preserving its provenance?"],
];

const outcomes = ["positive", "mixed", "negative", "inconclusive", "pending", "not-applicable"];

export function outcomeMix(notes) {
  const counts = Object.fromEntries(outcomes.map((key) => [key, 0]));
  for (const { outcome } of notes) counts[outcome] += 1;
  const displayed = outcomes.filter((key, index) => index < 4 || counts[key]);
  return `<div class="outcome-mix"><svg viewBox="0 0 ${Math.max(1, notes.length)} 1" preserveAspectRatio="none" aria-hidden="true">${displayed.map((key, index) => `<rect data-outcome="${key}" x="${displayed.slice(0, index).reduce((sum, prior) => sum + (counts[prior] ?? 0), 0)}" width="${counts[key] ?? 0}" height="1"/>`).join("")}</svg><ul>${displayed.map((key) => `<li data-outcome="${key}">${counts[key] ?? 0} ${key}</li>`).join("")}</ul></div>`;
}

const chains = [
  ["Zenith · Generalization and failure", ["zenith-011", "zenith-017"]],
  ["Composition · Cost and mechanism rejection", ["composition-007", "composition-009"]],
  ["Voxel Guidance · Behavior, representation and perception", ["voxel-guidance-001", "voxel-guidance-006"]],
];

export const evidence = {
  "prosody-018": ["Pilot · Blinded · Single reviewer", "One listener compared two samples of one scene. The review does not isolate a causal effect of shared context."],
  "narrative-steering-001": ["Pilot · Blinded", "Model identity was blinded. The public pilot does not establish the seven-axis framework."],
  "voxel-guidance-002": ["Single participant · Restricted artifacts", "Raw streams and per-session predictions are absent from the public record."],
  "voxel-guidance-006": ["Synthetic only · Frozen evaluation", "Deterministic scenes and disjoint seeds were used to compare temporal and single-frame models."],
  "zenith-017": ["Fresh holdout · Live validation", "A fresh swamp holdout failed after stronger development results."],
  "game-session-observation-001": ["Restricted artifacts · Live observation", "The recording and server evidence were retained privately."],
  "multiview-cameras-006": ["Restricted artifacts · Live validation", "Full hashes and logs are omitted. Availability was inconsistent."],
};

export function observatory(manifest, siteUrl, repositoryUrl) {
  const { families, labnotes } = manifest;
  const byId = new Map(labnotes.map((note) => [note.id, note]));
  const noteLink = (note, base = "") => `<a href="${base}${html(note.href)}">${html(note.id)}</a>`;
  const readings = chains.map(([title, ids]) => `<li><strong>${html(title)}</strong><div>${ids.map((id) => byId.get(id)).filter(Boolean).map((note) => noteLink(note)).join(" · ")}</div></li>`).join("");
  const profiles = programs.map(([id, title, familyIds, question]) => ({
    id, title, question,
    families: families.filter((family) => familyIds.includes(family.id)),
    notes: labnotes.filter((note) => familyIds.includes(note.family)),
  }));
  const pages = new Map();
  const page = (route, title, content, base) => pages.set(route, `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'"><title>${html(title)} | Yūrei Research</title><link rel="canonical" href="${siteUrl}${route}"><link rel="stylesheet" href="${base}assets/styles.css?v=${html(manifest.source_revision)}"></head>
<body class="observatory"><header class="terminal-bar"><a class="wordmark" href="${base}">◇ YŪREI RESEARCH</a><span>STABLE</span></header><main class="note-shell editorial-page"><a class="back" href="${base}">← Research overview</a><h1>${html(title)}</h1>${content}</main></body></html>`);
  for (const { id, title, question, families: members, notes } of profiles) {
    const relations = notes.flatMap((note) => note.relations.map((relation) => [note, relation, byId.get(relation.target)]))
      .filter(([note, , target]) => target && note.family !== target.family);
    page(`programs/${id}/`, title, `<p class="eyebrow">Editorial research program</p><p>${html(question)}</p>
<h2>Experiment families</h2><ul>${members.map((family) => `<li><a href="../../projects/${html(family.id)}/">${html(family.title)}</a> · ${family.labnote_count} labnotes</li>`).join("")}</ul>
<h2>Outcome mix</h2>${outcomeMix(notes)}
<h2>Authored cross-family relationships</h2>${relations.length ? `<ul>${relations.map(([note, relation, target]) => `<li>${noteLink(note, "../../")} ${html(relation.type)} ${noteLink(target, "../../")}</li>`).join("")}</ul>` : "<p>No published cross-family relationships originate in this program.</p>"}`, "../../");
  }
  const exemplars = ["prosody-018", "zenith-017", "composition-009", "voxel-guidance-006"].map((id) => byId.get(id)).filter(Boolean);
  page("reviewers/", "For reviewers", `<p>How much useful interactive intelligence can small, resource-conscious systems deliver under explicit evidence, cost and authority constraints?</p>
<h2>Research programs</h2><ul>${profiles.map(({ id, title }) => `<li><a href="../programs/${id}/">${html(title)}</a></li>`).join("")}</ul>
<h2>Representative findings</h2><ul>${exemplars.map((note) => `<li>${noteLink(note, "../")} · <span data-outcome="${html(note.outcome)}">${html(note.outcome)}</span><p>${html(note.result_summary)}</p></li>`).join("")}</ul>
<h2>Methods and limitations</h2><p>We freeze protocols where documented, preserve failed results and distinguish synthetic tests from live and human-driven observations. Small samples, single reviewers and restricted artifacts limit external replication and generalization.</p>
<h2>Infrastructure</h2><p>Simulation, instrumented observation and review tools support bounded experiments. <a href="${repositoryUrl}/tree/main/apparatus">Browse published apparatus</a>.</p>
<h2>Prospective research</h2><p>Compare stateless, fixed-summary and retrieval-backed memory across frozen, repeated tasks. Longer-running and multi-agent effects remain open research questions.</p>`, "../");
  page("maps/", "Research maps", `<p>Family maps show corpus-relative attention. Only the selected record’s authored lineage represents provenance. Open the labnote for the underlying evidence.</p>
<ul>${families.filter((family) => family.has_graph).map((family) => `<li><a href="../projects/${html(family.id)}/">${html(family.title)}</a></li>`).join("")}</ul>`, "../");
  page("inventory/", "Publication inventory", `<p>${labnotes.length} labnotes in the current public corpus. <a href="${repositoryUrl}/blob/main/docs/experiment-inventory.md">Historical migration inventory</a></p>
${families.map((family) => `<section><h2><a href="../projects/${html(family.id)}/">${html(family.title)}</a></h2><ul>${labnotes.filter((note) => note.family === family.id).map((note) => `<li>${noteLink(note, "../")} · ${html(note.title)} · <span data-outcome="${html(note.outcome)}">${html(note.outcome)}</span></li>`).join("")}</ul></section>`).join("")}`, "../");
  return {
    pages,
    programCount: profiles.length,
    cards: profiles.map(({ id, title, question, notes }) => `<a class="program-card" href="programs/${id}/"><h3>${html(title)}</h3><p>${html(question)}</p><span>${notes.length} ${notes.length === 1 ? "labnote" : "labnotes"}</span></a>`).join(""),
    latest: labnotes.slice(0, 3).map((note) => `<li><a href="${html(note.href)}">${html(note.title)}</a><span data-outcome="${html(note.outcome)}">${html(note.outcome)}</span></li>`).join(""),
    readings,
  };
}
