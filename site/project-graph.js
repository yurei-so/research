const $ = (selector) => document.querySelector(selector);

async function boot() {
  const response = await fetch("graph.json");
  if (!response.ok) throw new Error(`project graph unavailable (${response.status})`);
  const graph = await response.json();
  const byId = new Map(graph.notes.map((note) => [note.id, note]));
  let selected = graph.notes.at(-1)?.id;
  let tracing = false;

  const neighborhood = (root) => {
    const seen = new Set([root]);
    const walk = (direction) => {
      let frontier = new Set([root]);
      while (frontier.size) {
        const next = new Set();
        for (const relation of graph.relations) {
          const from = direction === "ancestors" ? relation.source : relation.target;
          const to = direction === "ancestors" ? relation.target : relation.source;
          if (frontier.has(from) && !seen.has(to)) { seen.add(to); next.add(to); }
        }
        frontier = next;
      }
    };
    for (const direction of ["ancestors", "descendants"]) {
      walk(direction);
    }
    return seen;
  };

  const renderInspector = () => {
    const note = byId.get(selected);
    if (!note) return;
    $("#inspect-id").textContent = note.id;
    $("#inspect-title").textContent = note.title;
    $("#inspect-date").textContent = note.date;
    $("#inspect-status").textContent = note.status;
    $("#inspect-outcome").textContent = note.outcome;
    $("#inspect-outcome").dataset.outcome = note.outcome;
    $("#inspect-summary").textContent = note.result_summary;
    $("#open-note").href = `../../${note.href}`;
    $("#view-source").href = note.source_url;
    const related = graph.relations.filter((relation) => relation.source === note.id || relation.target === note.id);
    $("#relation-list").replaceChildren(...related.map((relation) => {
      const item = document.createElement("div");
      item.className = "relation-item";
      const direction = relation.source === note.id ? "BUILDS ON" : "INFORMS";
      const other = byId.get(relation.source === note.id ? relation.target : relation.source);
      const label = document.createElement("b");
      label.textContent = `${direction} · ${relation.type.replaceAll("-", " ")}`;
      const title = document.createElement("span");
      title.textContent = `${other.id} — ${other.title}`;
      const rationale = document.createElement("p");
      rationale.textContent = relation.rationale;
      item.append(label, title, rationale);
      return item;
    }));
    document.querySelectorAll(".graph-node").forEach((node) => node.classList.toggle("selected", node.dataset.note === selected));
    const visible = tracing ? neighborhood(selected) : new Set(graph.notes.map((entry) => entry.id));
    document.querySelectorAll(".graph-node").forEach((node) => node.classList.toggle("unrelated", !visible.has(node.dataset.note)));
    document.querySelectorAll(".graph-edge").forEach((edge) => {
      edge.classList.toggle("unrelated", !visible.has(edge.dataset.source) || !visible.has(edge.dataset.target));
      edge.classList.toggle("related", edge.dataset.source === selected || edge.dataset.target === selected);
    });
  };

  document.querySelectorAll(".graph-node").forEach((node) => {
    node.addEventListener("click", (event) => { event.preventDefault(); selected = node.dataset.note; renderInspector(); });
    node.addEventListener("dblclick", () => location.assign(node.getAttribute("href")));
    node.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selected = node.dataset.note; renderInspector(); } });
  });
  document.querySelectorAll(".graph-edge").forEach((edge) => edge.addEventListener("click", () => {
    $("#edge-note").textContent = edge.dataset.rationale;
  }));
  $("#trace-lineage").addEventListener("click", () => { tracing = !tracing; $("#trace-lineage").setAttribute("aria-pressed", String(tracing)); renderInspector(); });
  $("#copy-link").addEventListener("click", async () => {
    const url = new URL(`../../${byId.get(selected).href}`, location.href).href;
    await navigator.clipboard.writeText(url);
    $("#copy-link").textContent = "COPIED";
  });
  renderInspector();
}

boot().catch((error) => { $("#edge-note").textContent = error.message; });
