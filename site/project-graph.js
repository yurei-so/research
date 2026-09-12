// SPDX-License-Identifier: AGPL-3.0-only

const $ = (selector) => document.querySelector(selector);

async function boot() {
  const response = await fetch("graph.json");
  if (!response.ok) throw new Error(`project graph unavailable (${response.status})`);
  const graph = await response.json();
  const byId = new Map(graph.notes.map((note) => [note.id, note]));
  const stage = $(".graph-stage");
  const maps = [...document.querySelectorAll(".project-map, .attention-map")];
  let activeView = "provenance";
  const activeMap = () => maps.find((entry) => entry.dataset.mapView === activeView);
  const naturalWidth = Number(maps[0].dataset.naturalWidth);
  const naturalHeight = Number(maps[0].dataset.naturalHeight);
  let zoom = .82;
  let selected = graph.notes.at(-1)?.id;
  let tracing = false;
  let terrain = "cells";

  const renderAttentionDisclosure = () => {
    const stress = graph.attention.projection.normalized_stress.toFixed(3);
    const rendering = terrain === "cells"
      ? "Quantized cell density describes only this published Yurei corpus"
      : "Smooth heat and fog describe only this published Yurei corpus";
    $("#view-disclosure").textContent = `${graph.attention.representation.method} vectors projected with classical MDS · ${graph.notes.length} records · stress ${stress}. ${rendering}; geometry is approximate.`;
  };

  const setZoom = (next) => {
    const map = activeMap();
    const oldWidth = map.getBoundingClientRect().width || naturalWidth * zoom;
    const focus = { x: (stage.scrollLeft + stage.clientWidth / 2) / oldWidth, y: (stage.scrollTop + stage.clientHeight / 2) / (oldWidth * naturalHeight / naturalWidth) };
    zoom = Math.max(.45, Math.min(1.4, next));
    maps.forEach((entry) => { entry.style.width = `${Math.round(naturalWidth * zoom)}px`; });
    $("#zoom-level").textContent = `${Math.round(zoom * 100)}%`;
    requestAnimationFrame(() => {
      stage.scrollLeft = focus.x * map.clientWidth - stage.clientWidth / 2;
      stage.scrollTop = focus.y * map.clientHeight - stage.clientHeight / 2;
    });
  };

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
    const related = activeView === "provenance"
      ? graph.relations.filter((relation) => relation.source === note.id || relation.target === note.id)
      : [];
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
    document.querySelectorAll(".graph-node, .attention-node").forEach((node) => node.classList.toggle("selected", node.dataset.note === selected));
    const visible = tracing ? neighborhood(selected) : new Set(graph.notes.map((entry) => entry.id));
    document.querySelectorAll(".graph-node").forEach((node) => node.classList.toggle("unrelated", !visible.has(node.dataset.note)));
    document.querySelectorAll(".graph-edge").forEach((edge) => {
      edge.classList.toggle("unrelated", !visible.has(edge.dataset.source) || !visible.has(edge.dataset.target));
      edge.classList.toggle("related", edge.dataset.source === selected || edge.dataset.target === selected);
    });
  };

  document.querySelectorAll(".graph-node, .attention-node").forEach((node) => {
    node.addEventListener("click", (event) => {
      event.preventDefault(); selected = node.dataset.note; renderInspector();
      if (matchMedia("(max-width: 720px)").matches) {
        requestAnimationFrame(() => $(".graph-inspector").scrollIntoView({ behavior: "smooth", block: "start" }));
      }
    });
    node.addEventListener("dblclick", () => location.assign(node.getAttribute("href")));
    node.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selected = node.dataset.note; renderInspector(); } });
  });
  document.querySelectorAll(".graph-edge").forEach((edge) => edge.addEventListener("click", () => {
    $("#edge-note").textContent = edge.dataset.rationale;
  }));
  document.querySelectorAll(".map-modes button[data-map-view]").forEach((button) => button.addEventListener("click", () => {
    activeView = button.dataset.mapView;
    maps.forEach((entry) => {
      entry.hidden = entry.dataset.mapView !== activeView;
      entry.style.display = entry.hidden ? "none" : "block";
    });
    document.querySelectorAll(".map-modes button[data-map-view]").forEach((entry) => entry.setAttribute("aria-pressed", String(entry === button)));
    tracing = false;
    $("#trace-lineage").setAttribute("aria-pressed", "false");
    $("#trace-lineage").disabled = activeView !== "provenance";
    $("#terrain-style").disabled = activeView !== "attention";
    if (activeView === "attention") {
      renderAttentionDisclosure();
      $("#edge-note").textContent = "Conceptual proximity is not provenance and creates no relationship edges.";
    } else {
      $("#view-disclosure").textContent = "Human-authored relationships only. Proximity is not used to create edges.";
      $("#edge-note").textContent = "Select an edge to read its authored rationale.";
    }
    renderInspector();
    requestAnimationFrame(() => setZoom(Math.min((stage.clientWidth - 28) / naturalWidth, (stage.clientHeight - 28) / naturalHeight)));
  }));
  $("#trace-lineage").addEventListener("click", () => { tracing = !tracing; $("#trace-lineage").setAttribute("aria-pressed", String(tracing)); renderInspector(); });
  $("#zoom-out").addEventListener("click", () => setZoom(zoom - .12));
  $("#zoom-in").addEventListener("click", () => setZoom(zoom + .12));
  $("#zoom-fit").addEventListener("click", () => setZoom(Math.min((stage.clientWidth - 28) / naturalWidth, (stage.clientHeight - 28) / naturalHeight)));
  $("#terrain-style").addEventListener("click", () => {
    terrain = terrain === "cells" ? "smooth" : "cells";
    const attentionMap = $(".attention-map");
    attentionMap.dataset.terrain = terrain;
    $("#terrain-style").textContent = terrain === "cells" ? "CELLS" : "SMOOTH";
    $("#terrain-style").setAttribute("aria-label", `Attention terrain: ${terrain}`);
    renderAttentionDisclosure();
  });
  $("#back-to-map").addEventListener("click", () => stage.scrollIntoView({ behavior: "smooth", block: "start" }));
  let pan = null;
  stage.addEventListener("pointerdown", (event) => {
    if (event.target.closest(".graph-node, .attention-node, .graph-edge")) return;
    pan = { x: event.clientX, y: event.clientY, left: stage.scrollLeft, top: stage.scrollTop };
    stage.setPointerCapture(event.pointerId);
    stage.classList.add("panning");
  });
  stage.addEventListener("pointermove", (event) => {
    if (!pan) return;
    stage.scrollLeft = pan.left - (event.clientX - pan.x);
    stage.scrollTop = pan.top - (event.clientY - pan.y);
  });
  const stopPanning = () => { pan = null; stage.classList.remove("panning"); };
  stage.addEventListener("pointerup", stopPanning);
  stage.addEventListener("pointercancel", stopPanning);
  $("#copy-link").addEventListener("click", async () => {
    const url = new URL(`../../${byId.get(selected).href}`, location.href).href;
    await navigator.clipboard.writeText(url);
    $("#copy-link").textContent = "COPIED";
  });
  renderInspector();
  requestAnimationFrame(() => {
    stage.scrollLeft = (stage.scrollWidth - stage.clientWidth) / 2;
    stage.scrollTop = (stage.scrollHeight - stage.clientHeight) / 2;
  });
}

boot().catch((error) => { $("#edge-note").textContent = error.message; });
// SPDX-License-Identifier: AGPL-3.0-only
