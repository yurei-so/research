// SPDX-License-Identifier: AGPL-3.0-only

const $ = (selector) => document.querySelector(selector);
const outcomeOrder = ["positive", "negative", "mixed", "inconclusive", "pending", "not-applicable"];
const escapeHtml = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");

function familyCard(family) {
  const outcomes = Object.entries(family.outcomes).map(([name, count]) => `<span data-outcome="${name}">${count} ${name}</span>`).join("");
  const successRate = family.labnote_count
    ? Math.round(((family.outcomes.positive ?? 0) / family.labnote_count) * 100)
    : 0;
  const noteLabel = family.labnote_count === 1 ? "labnote" : "labnotes";
  const action = family.has_graph ? "OPEN RESEARCH MAP →" : "FILTER TO THIS FAMILY ↓";
  const content = `<h3>${escapeHtml(family.title)}</h3><p>${family.labnote_count} published ${noteLabel}</p><div class="outcomes">${outcomes}</div><span class="inspect">${action}</span>`;
  const primary = family.has_graph
    ? `<a class="family-primary" href="projects/${family.id}/">${content}</a>`
    : `<button class="family-filter family-primary" data-family="${family.id}" type="button">${content}</button>`;
  return `<article class="family-card" data-family="${family.id}"><span class="success-rate" title="Positive published labnotes divided by all published labnotes" aria-label="${successRate} percent positive-result rate">${successRate}% SUCCESS</span>${primary}</article>`;
}

function noteCard(note) {
  return `<article class="feed-entry" data-family="${note.family}"><div class="entry-index"><span>${note.date}</span><b>${note.id}</b></div><div class="entry-main"><div class="entry-state"><span>${escapeHtml(note.status)}</span><span data-outcome="${note.outcome}">${escapeHtml(note.outcome)}</span></div><h3><a href="${note.href}">${escapeHtml(note.title)}</a></h3><p>${escapeHtml(note.question)}</p><div class="tags">${note.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div></div><a class="open-note" href="${note.href}" aria-label="Open ${note.id}">↗</a></article>`;
}

async function boot() {
  const embedded = $("#research-manifest-data")?.content.textContent;
  const catalog = embedded
    ? JSON.parse(embedded)
    : await fetch("research-manifest.json").then((response) => {
      if (!response.ok) throw new Error(`catalog unavailable (${response.status})`);
      return response.json();
    });
  $("#note-count").textContent = catalog.labnotes.length;
  $("#family-count").textContent = catalog.families.length;
  $("#revision").textContent = catalog.source_revision;
  $("#generated").textContent = `CATALOG ${catalog.generated_at.slice(0, 10)} / REV ${catalog.source_revision}`;
  $("#families").innerHTML = catalog.families.map(familyCard).join("");
  for (const outcome of outcomeOrder.filter((value) => catalog.labnotes.some((note) => note.outcome === value))) {
    $("#outcome").insertAdjacentHTML("beforeend", `<option value="${outcome}">${outcome}</option>`);
  }
  let family = "";
  const render = () => {
    const query = $("#search").value.trim().toLowerCase();
    const outcome = $("#outcome").value;
    const notes = catalog.labnotes.filter((note) => (!family || note.family === family) && (!outcome || note.outcome === outcome)
      && (!query || [note.id, note.title, note.question, note.family, ...note.tags].join(" ").toLowerCase().includes(query)));
    $("#feed").innerHTML = notes.length ? notes.map(noteCard).join("") : '<p class="empty">No published observations match this view.</p>';
    $("#result-count").textContent = `${notes.length} VISIBLE`;
    document.querySelectorAll(".family-card").forEach((card) => card.classList.toggle("selected", card.dataset.family === family));
  };
  $("#search").addEventListener("input", render);
  $("#outcome").addEventListener("change", render);
  $("#families").addEventListener("click", (event) => {
    const card = event.target.closest(".family-filter");
    if (!card) return;
    family = family === card.dataset.family ? "" : card.dataset.family;
    render();
    $(".archive").scrollIntoView({ block: "start" });
  });
  render();
}

boot().catch((error) => {
  $("#feed").innerHTML = `<p class="empty">Observation catalog unavailable. ${error.message}</p>`;
});
// SPDX-License-Identifier: AGPL-3.0-only
