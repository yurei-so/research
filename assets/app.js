// SPDX-License-Identifier: AGPL-3.0-only

const $ = (selector) => document.querySelector(selector);
const outcomeOrder = ["positive", "negative", "mixed", "inconclusive", "pending", "not-applicable"];
const escapeHtml = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");

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
    $("#labnotes").scrollIntoView({ block: "start" });
  });
  render();
}

boot().catch((error) => {
  $("#result-count").textContent = "Interactive filters unavailable.";
  console.error(error);
});
// SPDX-License-Identifier: AGPL-3.0-only
