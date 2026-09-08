const $ = (selector) => document.querySelector(selector);
const outcomeOrder = ["positive", "negative", "mixed", "inconclusive", "pending", "not-applicable"];
const escapeHtml = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");

function familyCard(family) {
  const outcomes = Object.entries(family.outcomes).map(([name, count]) => `<span data-outcome="${name}">${count} ${name}</span>`).join("");
  return `<button class="family-card" data-family="${family.id}" type="button"><span class="cell-state"><i></i>${escapeHtml(family.status)}</span><h3>${escapeHtml(family.title)}</h3><p>${family.labnote_count} published observations</p><div class="outcomes">${outcomes}</div><span class="inspect">ISOLATE CELL →</span></button>`;
}

function noteCard(note) {
  return `<article class="feed-entry" data-family="${note.family}"><div class="entry-index"><span>${note.date}</span><b>${note.id}</b></div><div class="entry-main"><div class="entry-state"><span>${escapeHtml(note.status)}</span><span data-outcome="${note.outcome}">${escapeHtml(note.outcome)}</span></div><h3><a href="${note.href}">${escapeHtml(note.title)}</a></h3><p>${escapeHtml(note.question)}</p><div class="tags">${note.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div></div><a class="open-note" href="${note.href}" aria-label="Open ${note.id}">↗</a></article>`;
}

async function boot() {
  const response = await fetch("research-manifest.json");
  if (!response.ok) throw new Error(`catalog unavailable (${response.status})`);
  const catalog = await response.json();
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
    const card = event.target.closest(".family-card");
    if (!card) return;
    family = family === card.dataset.family ? "" : card.dataset.family;
    render();
    $(".archive").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  render();
}

boot().catch((error) => {
  $("#feed").innerHTML = `<p class="empty">Observation catalog unavailable. ${error.message}</p>`;
});
