// SPDX-License-Identifier: AGPL-3.0-only

const $ = (selector) => document.querySelector(selector);

const storedPageView = () => {
  try { return localStorage.getItem("yurei-family-page-view"); } catch { return null; }
};
const storedZoom = (view) => {
  try {
    const value = Number(JSON.parse(localStorage.getItem("yurei-family-map-zoom") ?? "{}")[view]);
    return Number.isFinite(value) && value >= .25 && value <= 1.4 ? value : null;
  } catch { return null; }
};
const saveZoom = (view, value) => {
  try {
    const saved = JSON.parse(localStorage.getItem("yurei-family-map-zoom") ?? "{}");
    saved[view] = value;
    localStorage.setItem("yurei-family-map-zoom", JSON.stringify(saved));
  } catch {}
};
const clearZoom = (view) => {
  try {
    const saved = JSON.parse(localStorage.getItem("yurei-family-map-zoom") ?? "{}");
    delete saved[view];
    localStorage.setItem("yurei-family-map-zoom", JSON.stringify(saved));
  } catch {}
};
const initialPageView = storedPageView() === "beta-fit" ? "beta-fit" : "standard";
document.body.dataset.pageView = initialPageView;

async function boot() {
  const embedded = $("#project-graph-data")?.textContent;
  const graph = embedded
    ? JSON.parse(embedded)
    : await fetch("graph.json").then((response) => {
      if (!response.ok) throw new Error(`project graph unavailable (${response.status})`);
      return response.json();
    });
  const byId = new Map(graph.notes.map((note) => [note.id, note]));
  const stage = $(".graph-stage");
  const maps = [...document.querySelectorAll(".project-map, .attention-map")];
  let activeView = "attention";
  const activeMap = () => maps.find((entry) => entry.dataset.mapView === activeView);
  const naturalWidth = Number(maps[0].dataset.naturalWidth);
  const naturalHeight = Number(maps[0].dataset.naturalHeight);
  let zoom = .82;
  let selected = graph.notes.at(-1)?.id;
  let tracing = false;
  let terrain = "cells";
  let userAdjustedZoom = false;

  const attentionMap = $(".attention-map");
  const attentionNodes = new Map([...attentionMap.querySelectorAll(".attention-node")]
    .map((node) => [node.dataset.note, node]));
  const contextLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
  contextLayer.classList.add("attention-context");
  contextLayer.setAttribute("aria-label", "Authored neighbor context");
  for (const relation of graph.relations) {
    const source = attentionNodes.get(relation.source);
    const target = attentionNodes.get(relation.target);
    if (!source || !target) continue;
    const edge = document.createElementNS("http://www.w3.org/2000/svg", "path");
    edge.classList.add("attention-context-edge");
    edge.dataset.source = relation.source;
    edge.dataset.target = relation.target;
    edge.setAttribute("d", `M ${target.dataset.centerX} ${target.dataset.centerY} L ${source.dataset.centerX} ${source.dataset.centerY}`);
    contextLayer.append(edge);
  }
  attentionMap.insertBefore(contextLayer, attentionMap.querySelector(".attention-node"));

  const renderAttentionDisclosure = () => {
    const stress = graph.attention.projection.normalized_stress.toFixed(3);
    const rendering = terrain === "cells"
      ? "Quantized cell density describes only this published Yurei corpus"
      : "Smooth heat and fog describe only this published Yurei corpus";
    $("#view-disclosure").textContent = `${graph.attention.representation.method} vectors projected with classical MDS · ${graph.notes.length} records · stress ${stress}. ${rendering}; geometry is approximate.`;
  };

  const setZoom = (next, { manual = false } = {}) => {
    if (manual) userAdjustedZoom = true;
    const map = activeMap();
    const oldBox = map.getBoundingClientRect();
    const oldWidth = oldBox.width || naturalWidth * zoom;
    const oldHeight = oldBox.height || naturalHeight * zoom;
    const focus = { x: (stage.scrollLeft + stage.clientWidth / 2) / oldWidth, y: (stage.scrollTop + stage.clientHeight / 2) / oldHeight };
    const minimumZoom = document.body.dataset.pageView === "beta-fit" ? .25 : .45;
    zoom = Math.max(minimumZoom, Math.min(1.4, next));
    if (manual) saveZoom(document.body.dataset.pageView, zoom);
    const newWidth = Math.round(naturalWidth * zoom);
    const newHeight = Math.round(naturalHeight * zoom);
    maps.forEach((entry) => {
      entry.style.width = `${newWidth}px`;
      entry.style.height = `${newHeight}px`;
    });
    $("#zoom-level").textContent = `${Math.round(zoom * 100)}%`;
    stage.scrollLeft = focus.x * newWidth - stage.clientWidth / 2;
    stage.scrollTop = focus.y * newHeight - stage.clientHeight / 2;
  };

  const runZoom = (event, action) => {
    event.preventDefault();
    try { action(); }
    catch (error) {
      $("#zoom-level").textContent = "ZOOM ERROR";
      $("#edge-note").textContent = `Zoom failed: ${error.message}`;
    }
  };
  const bindZoom = (selector, action) => {
    const button = $(selector);
    button.addEventListener("pointerup", (event) => runZoom(event, action));
    button.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") runZoom(event, action);
    });
  };
  bindZoom("#zoom-out", () => setZoom(zoom - .12, { manual: true }));
  bindZoom("#zoom-in", () => setZoom(zoom + .12, { manual: true }));
  bindZoom("#zoom-fit", () => {
    userAdjustedZoom = false;
    clearZoom(document.body.dataset.pageView);
    setZoom(fitZoom());
  });

  const focusSelected = ({ smooth = true } = {}) => {
    const node = activeMap()?.querySelector(`[data-note="${CSS.escape(selected)}"]`);
    if (!node) return;
    const scale = activeMap().clientWidth / naturalWidth;
    const x = Number(node.dataset.centerX) * scale;
    const y = Number(node.dataset.centerY) * scale;
    stage.scrollTo({ left: x - stage.clientWidth / 2, top: y - stage.clientHeight / 2, behavior: smooth ? "smooth" : "auto" });
  };

  const revealListSelection = () => {
    const rail = $(".family-notes");
    const item = rail?.querySelector(`.family-note[data-note="${CSS.escape(selected)}"]`);
    if (!rail || !item) return;
    const railBox = rail.getBoundingClientRect();
    const itemBox = item.getBoundingClientRect();
    if (itemBox.top >= railBox.top && itemBox.bottom <= railBox.bottom) return;
    rail.scrollTo({
      top: rail.scrollTop + itemBox.top - railBox.top - (rail.clientHeight - item.clientHeight) / 2,
      behavior: "smooth",
    });
  };

  const fitZoom = () => Math.min((stage.clientWidth - 28) / naturalWidth, (stage.clientHeight - 28) / naturalHeight);
  const readableZoom = () => Math.max(.68, fitZoom());
  const applyPageView = (view, { persist = true } = {}) => {
    const next = view === "beta-fit" ? "beta-fit" : "standard";
    document.body.dataset.pageView = next;
    document.querySelectorAll("[data-page-view]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.pageView === next));
    });
    const restoredZoom = storedZoom(next);
    userAdjustedZoom = restoredZoom !== null;
    if (persist) {
      try { localStorage.setItem("yurei-family-page-view", next); } catch {}
    }
    requestAnimationFrame(() => {
      setZoom(restoredZoom ?? (next === "beta-fit" && matchMedia("(min-width: 1000px)").matches ? fitZoom() : readableZoom()));
      focusSelected({ smooth: false });
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
    $("#inspect-question").textContent = note.question;
    $("#inspect-summary").textContent = note.result_summary;
    $("#open-note").href = `../../${note.href}`;
    $("#view-source").href = note.source_url;
    const related = graph.relations.filter((relation) => relation.source === note.id || relation.target === note.id);
    $("#relation-list").replaceChildren(...related.map((relation) => {
      const item = document.createElement("button");
      item.className = "relation-item";
      item.type = "button";
      const direction = relation.source === note.id ? "BUILDS ON" : "INFORMS";
      const other = byId.get(relation.source === note.id ? relation.target : relation.source);
      const label = document.createElement("b");
      label.textContent = `${direction} · ${relation.type.replaceAll("-", " ")}`;
      const title = document.createElement("span");
      title.textContent = `${other.id} — ${other.title}`;
      const rationale = document.createElement("p");
      rationale.textContent = relation.rationale;
      item.append(label, title, rationale);
      item.addEventListener("click", () => selectNote(other.id, { focus: true, reveal: true }));
      return item;
    }));
    document.querySelectorAll(".graph-node, .attention-node").forEach((node) => node.classList.toggle("selected", node.dataset.note === selected));
    document.querySelectorAll(".family-note").forEach((item) => {
      const isSelected = item.dataset.note === selected;
      item.classList.toggle("selected", isSelected);
      item.querySelector(".family-note-select")?.setAttribute("aria-pressed", String(isSelected));
    });
    const visible = tracing ? neighborhood(selected) : new Set(graph.notes.map((entry) => entry.id));
    document.querySelectorAll(".graph-node").forEach((node) => {
      node.classList.toggle("unrelated", !visible.has(node.dataset.note));
      node.classList.toggle("traced", tracing && visible.has(node.dataset.note));
    });
    document.querySelectorAll(".graph-edge").forEach((edge) => {
      edge.classList.toggle("unrelated", !visible.has(edge.dataset.source) || !visible.has(edge.dataset.target));
      edge.classList.toggle("related", edge.dataset.source === selected || edge.dataset.target === selected);
      edge.classList.toggle("traced", tracing && visible.has(edge.dataset.source) && visible.has(edge.dataset.target));
    });
    document.querySelectorAll(".attention-context-edge").forEach((edge) => {
      edge.classList.toggle("related", edge.dataset.source === selected || edge.dataset.target === selected);
    });
  };

  const selectNote = (id, { focus = false, reveal = false } = {}) => {
    if (!byId.has(id)) return;
    selected = id;
    renderInspector();
    if (focus) requestAnimationFrame(() => focusSelected());
    if (reveal) requestAnimationFrame(revealListSelection);
  };

  document.querySelectorAll(".graph-node, .attention-node").forEach((node) => {
    node.addEventListener("click", (event) => {
      event.preventDefault(); selectNote(node.dataset.note, { reveal: true });
    });
    node.addEventListener("dblclick", () => location.assign(node.getAttribute("href")));
    node.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectNote(node.dataset.note, { reveal: true }); } });
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
    $("#trace-lineage").textContent = "TRACE LINEAGE";
    $("#trace-lineage").disabled = activeView !== "provenance";
    $("#terrain-style").disabled = activeView !== "attention";
    if (activeView === "attention") {
      renderAttentionDisclosure();
      $("#edge-note").textContent = "Only the selected note’s authored relations are drawn. Semantic proximity creates no relationship edges.";
    } else {
      $("#view-disclosure").textContent = "Human-authored relationships only. Proximity is not used to create edges.";
      $("#edge-note").textContent = "Select an edge to read its authored rationale.";
    }
    renderInspector();
    requestAnimationFrame(() => {
      setZoom(zoom);
      focusSelected({ smooth: false });
    });
  }));
  document.querySelectorAll("[data-page-view]").forEach((button) => button.addEventListener("click", () => {
    applyPageView(button.dataset.pageView);
  }));
  addEventListener("resize", () => {
    if (userAdjustedZoom) return;
    requestAnimationFrame(() => setZoom(document.body.dataset.pageView === "beta-fit"
      && matchMedia("(min-width: 1000px)").matches ? fitZoom() : readableZoom()));
  });
  $("#trace-lineage").addEventListener("click", () => {
    tracing = !tracing;
    const button = $("#trace-lineage");
    button.setAttribute("aria-pressed", String(tracing));
    button.textContent = tracing ? "SHOW ALL" : "TRACE LINEAGE";
    renderInspector();
    if (tracing) {
      const count = neighborhood(selected).size;
      $("#edge-note").textContent = `Highlighted ${count} authored ancestor/current/descendant notes. Only explicit provenance edges are traced.`;
    } else {
      $("#edge-note").textContent = "Select an edge to read its authored rationale.";
    }
  });
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
  let suppressMapClick = false;
  stage.addEventListener("click", (event) => {
    if (!suppressMapClick) return;
    suppressMapClick = false;
    event.preventDefault();
    event.stopPropagation();
  }, true);
  stage.addEventListener("pointerdown", (event) => {
    if (event.pointerType === "touch" || event.button !== 0) return;
    suppressMapClick = false;
    stage.scrollTo({ left: stage.scrollLeft, top: stage.scrollTop, behavior: "auto" });
    pan = { x: event.clientX, y: event.clientY, left: stage.scrollLeft, top: stage.scrollTop, moved: false };
    stage.setPointerCapture(event.pointerId);
  });
  stage.addEventListener("pointermove", (event) => {
    if (!pan) return;
    if (!pan.moved && Math.hypot(event.clientX - pan.x, event.clientY - pan.y) < 5) return;
    pan.moved = true;
    suppressMapClick = true;
    stage.classList.add("panning");
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
  const noteFilter = $("#family-note-filter");
  const noteOutcome = $("#family-note-outcome");
  const filterFamilyNotes = () => {
    const query = noteFilter.value.trim().toLowerCase();
    const outcome = noteOutcome.value;
    let visibleCount = 0;
    document.querySelectorAll(".family-note").forEach((item) => {
      const shown = (!query || item.dataset.search.includes(query))
        && (!outcome || item.dataset.outcome === outcome);
      item.hidden = !shown;
      if (shown) visibleCount += 1;
    });
    $("#family-note-count").textContent = `${visibleCount} ${visibleCount === 1 ? "NOTE" : "NOTES"}`;
    $("#family-note-empty").hidden = visibleCount !== 0;
  };
  noteFilter.addEventListener("input", filterFamilyNotes);
  noteOutcome.addEventListener("change", filterFamilyNotes);
  document.querySelectorAll(".family-note-select").forEach((button) => button.addEventListener("click", () => {
    selectNote(button.closest(".family-note").dataset.note, { focus: true });
  }));
  renderInspector();
  renderAttentionDisclosure();
  applyPageView(initialPageView, { persist: false });
  $("#edge-note").textContent = "Only the selected note’s authored relations are drawn. Semantic proximity creates no relationship edges.";
}

boot().catch((error) => { $("#edge-note").textContent = error.message; });
// SPDX-License-Identifier: AGPL-3.0-only
