"""Geração da visualização HTML da rede e da animação da busca."""

from __future__ import annotations

import json
import math
from html import escape as html_escape
from pathlib import Path
from typing import Dict, Iterable, Sequence, Tuple

from .models import SearchResult
from .network import P2PNetwork


def circular_layout(nodes: Sequence[str], width: int = 960, height: int = 620) -> Dict[str, Dict[str, float]]:
    center_x = width / 2
    center_y = height / 2
    radius = min(width, height) * 0.38
    if len(nodes) == 1:
        return {nodes[0]: {"x": center_x, "y": center_y}}

    positions = {}
    for index, node in enumerate(nodes):
        angle = -math.pi / 2 + (2 * math.pi * index / len(nodes))
        positions[node] = {
            "x": round(center_x + radius * math.cos(angle), 2),
            "y": round(center_y + radius * math.sin(angle), 2),
        }
    return positions


def topology_layout(
    nodes: Sequence[str],
    edges: Iterable[Tuple[str, str]],
    width: int = 1080,
    height: int = 700,
) -> Dict[str, Dict[str, float]]:
    """Calcula um layout fixo usando apenas a topologia da rede."""

    ordered_nodes = list(nodes)
    positions = circular_layout(ordered_nodes, width, height)
    if len(ordered_nodes) <= 2:
        return positions

    padding = 90
    usable_width = max(1, width - 2 * padding)
    usable_height = max(1, height - 2 * padding)
    area = usable_width * usable_height
    ideal_distance = math.sqrt(area / len(ordered_nodes))
    edge_list = list(edges)
    temperature = min(width, height) * 0.12

    for iteration in range(180):
        displacement = {node: [0.0, 0.0] for node in ordered_nodes}

        for index, node_a in enumerate(ordered_nodes):
            for node_b in ordered_nodes[index + 1 :]:
                dx = positions[node_a]["x"] - positions[node_b]["x"]
                dy = positions[node_a]["y"] - positions[node_b]["y"]
                distance = max(math.hypot(dx, dy), 0.01)
                force = (ideal_distance * ideal_distance) / distance
                displacement[node_a][0] += (dx / distance) * force
                displacement[node_a][1] += (dy / distance) * force
                displacement[node_b][0] -= (dx / distance) * force
                displacement[node_b][1] -= (dy / distance) * force

        for node_a, node_b in edge_list:
            dx = positions[node_a]["x"] - positions[node_b]["x"]
            dy = positions[node_a]["y"] - positions[node_b]["y"]
            distance = max(math.hypot(dx, dy), 0.01)
            force = (distance * distance) / ideal_distance
            displacement[node_a][0] -= (dx / distance) * force
            displacement[node_a][1] -= (dy / distance) * force
            displacement[node_b][0] += (dx / distance) * force
            displacement[node_b][1] += (dy / distance) * force

        for node in ordered_nodes:
            dx, dy = displacement[node]
            distance = max(math.hypot(dx, dy), 0.01)
            step = min(distance, temperature)
            positions[node]["x"] = min(
                width - padding,
                max(padding, positions[node]["x"] + (dx / distance) * step),
            )
            positions[node]["y"] = min(
                height - padding,
                max(padding, positions[node]["y"] + (dy / distance) * step),
            )

        temperature *= 0.96
        if iteration > 40 and temperature < 0.5:
            break

    return {
        node: {"x": round(position["x"], 2), "y": round(position["y"], 2)}
        for node, position in positions.items()
    }




def build_visualization_payload(network: P2PNetwork, result: SearchResult) -> Dict[str, object]:
    layout_width = 1080
    layout_height = 700
    positions = topology_layout(network.nodes, sorted(network.edges), layout_width, layout_height)
    resource_holders = sorted(network.resource_locations.get(result.resource_id, []))
    resource_holder = resource_holders[0] if resource_holders else None
    uses_cache = result.algorithm in {"informed_flooding", "informed_random_walk"}
    cache_snapshot = result.cache_snapshot or network.caches

    def cache_for(node: str) -> Dict[str, str]:
        return cache_snapshot.get(node, {})

    def cache_is_relevant(node: str) -> bool:
        cached_holder = cache_for(node).get(result.resource_id)
        return bool(uses_cache and node != result.start_node and cached_holder and cached_holder != node)

    payload = {
        "layout": {"width": layout_width, "height": layout_height},
        "uses_cache": uses_cache,
        "nodes": [
            {
                "id": node,
                "resources": sorted(network.resources[node]),
                "cache": [
                    {
                        "resource": resource,
                        "holder": holder,
                        "local": holder == node,
                        "searched": resource == result.resource_id,
                    }
                    for resource, holder in sorted(cache_for(node).items())
                ],
                "cache_relevant": cache_is_relevant(node),
                "cache_used": (
                    uses_cache
                    and result.found_via == "cache"
                    and result.informed_by == node
                ),
                "x": positions[node]["x"],
                "y": positions[node]["y"],
            }
            for node in network.nodes
        ],
        "edges": [{"source": node_a, "target": node_b} for node_a, node_b in sorted(network.edges)],
        "events": [event.as_dict() for event in result.events],
        "resource_holder": resource_holder,
        "result": result.as_dict(),
    }
    return payload

def build_visualization_html(
    network: P2PNetwork,
    result: SearchResult,
    css_href: str = "visualization.css",
    js_src: str = "visualization.js",
) -> str:
    payload = build_visualization_payload(network, result)
    resource_holder = payload["resource_holder"]
    uses_cache = bool(payload["uses_cache"])
    title = html_escape(f"P2P Search - {result.algorithm}")
    status_text = "ENCONTRADO" if result.found else "NÃO ENCONTRADO"
    status_class = "found" if result.found else "not-found"
    holder = resource_holder or result.holder or "-"
    found_via = result.found_via or "-"
    layout_width = payload["layout"]["width"]
    layout_height = payload["layout"]["height"]
    cache_panel_class = " " if uses_cache else " hidden"
    cache_legend = (
        '<li><span class="swatch" style="background: var(--cache)"></span>nó com cache do recurso</li>'
        if uses_cache
        else ""
    )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="{html_escape(css_href)}">
</head>
<body>
  <header>
    <h1>Rede P2P - {html_escape(result.algorithm)}</h1>
  </header>
  <main>
    <section class="graph-panel" aria-label="Visualização do grafo da rede P2P">
      <div class="status pending" id="statusLabel" data-final-status="{html_escape(status_text)}" data-final-class="{status_class}">EXPLORANDO</div>
      <svg id="network" viewBox="0 0 {layout_width} {layout_height}" role="img" aria-label="Grafo da rede P2P e mensagens da busca"></svg>
      <div class="controls">
        <button type="button" id="play">Reproduzir</button>
        <button type="button" id="step">Avançar</button>
        <button type="button" id="reset">Reiniciar</button>
        <span class="step-label" id="stepLabel">Quadro 0 / 0</span>
      </div>
    </section>
    <aside>
      <section class="message-panel" id="messagePanel" aria-label="Mensagens em tempo real">
        <h2>Mensagens</h2>
        <ul class="log" id="log"></ul>
      </section>
      <section class="cache-panel{cache_panel_class}" id="cachePanel" aria-label="Caches dos nós">
        <h2>Caches dos nós</h2>
        <ul class="caches" id="caches"></ul>
      </section>
      <h2>Busca</h2>
      <dl>
        <dt>Nó inicial</dt><dd>{html_escape(result.start_node)}</dd>
        <dt>Recurso</dt><dd>{html_escape(result.resource_id)}</dd>
        <dt>TTL</dt><dd>{result.ttl}</dd>
        <dt>Mensagens</dt><dd>{result.messages}</dd>
        <dt>Nós envolvidos</dt><dd>{result.nodes_involved}</dd>
        <dt>Nó com recurso</dt><dd>{html_escape(str(holder))}</dd>
        <dt>Encontrado via</dt><dd>{html_escape(found_via)}</dd>
        <dt>Caminho</dt><dd>{html_escape(" -> ".join(result.path))}</dd>
      </dl>
      <h2>Legenda</h2>
      <ul class="legend">
        <li><span class="swatch" style="background: var(--start)"></span>nó inicial</li>
        <li><span class="swatch" style="background: var(--found)"></span>nó com recurso</li>
        {cache_legend}
        <li><span class="swatch" style="background: var(--request)"></span>requisição</li>
        <li><span class="swatch" style="background: var(--reply)"></span>resposta</li>
      </ul>
      <h2 style="margin-top: 18px;">Recursos</h2>
      <ul class="resources" id="resources"></ul>
    </aside>
  </main>
  <script src="{html_escape(js_src)}"></script>
</body>
</html>
"""


def build_visualization_css() -> str:
    return """:root {
  color-scheme: light;
  --bg: #f6f7f9;
  --panel: #ffffff;
  --ink: #1f2933;
  --muted: #627282;
  --line: #c9d2dc;
  --node: #ffffff;
  --node-border: #4f657a;
  --start: #1b74e4;
  --found: #0f9f6e;
  --request: #e1711d;
  --reply: #7c4dff;
  --cache: #b7791f;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  background: var(--bg);
  color: var(--ink);
  font-family: Segoe UI, Arial, sans-serif;
}
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 24px;
  border-bottom: 1px solid #d9e0e7;
  background: var(--panel);
}
h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0;
}
.status {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 4;
  min-width: 154px;
  padding: 10px 14px;
  border: 2px solid #aebdca;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 22px rgba(31, 41, 51, 0.14);
  text-align: center;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
  color: var(--muted);
}
.status.pending {
  border-color: #b9c4ce;
  background: rgba(247, 250, 252, 0.96);
}
.status.found {
  border-color: var(--found);
  background: #e8fff5;
  color: #0f7a54;
}
.status.not-found {
  border-color: #bd3131;
  background: #fff0f0;
  color: #9b1c1c;
}
main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  padding: 18px;
}
.graph-panel,
aside {
  background: var(--panel);
  border: 1px solid #d9e0e7;
  border-radius: 8px;
}
.graph-panel {
  position: relative;
  overflow: hidden;
}
svg {
  display: block;
  width: 100%;
  height: min(76vh, 760px);
  min-height: 500px;
  background: #fbfcfd;
}
.graph-edge {
  stroke: var(--line);
  stroke-width: 2;
}
.graph-edge.base {
  stroke: #b7c4cf;
  stroke-width: 2;
}
.graph-edge.event-edge {
  stroke: #9ba8b4;
  stroke-dasharray: 6 5;
  opacity: 0;
}
.graph-edge.event-edge.reply {
  stroke: var(--reply);
  stroke-dasharray: 7 5;
}
.graph-edge.event-edge.direct {
  stroke: var(--cache);
  stroke-dasharray: 4 4;
}
.graph-edge.active-request {
  stroke: var(--request);
  stroke-width: 4;
  stroke-dasharray: none;
  opacity: 1;
}
.graph-edge.active-reply {
  stroke: var(--reply);
  stroke-width: 4;
  opacity: 1;
}
.graph-edge.active-direct {
  stroke: var(--cache);
  stroke-width: 4;
  opacity: 1;
}
.node circle {
  fill: var(--node);
  stroke: var(--node-border);
  stroke-width: 2.5;
}
.node .cache-ring {
  fill: none;
  stroke: var(--cache);
  stroke-width: 2;
  stroke-dasharray: 3 7;
  opacity: 0.55;
}
.node text {
  font-size: 15px;
  font-weight: 700;
  text-anchor: middle;
  dominant-baseline: middle;
  fill: var(--ink);
  pointer-events: none;
}
.node.start circle {
  stroke: var(--start);
  stroke-width: 5;
}
.node.involved circle {
  fill: #edf6ff;
}
.node.active circle {
  fill: #fff4e8;
  stroke: var(--request);
  stroke-width: 5;
}
.node.holder circle {
  stroke: var(--found);
  stroke-width: 5;
}
.node.cache-accessed .cache-ring {
  stroke-width: 5;
  stroke-dasharray: none;
  opacity: 1;
}
.node.cache-accessed circle {
  fill: #fff8e7;
  stroke: var(--cache);
  stroke-width: 5;
}
.message {
  stroke: #ffffff;
  stroke-width: 2;
}
.message.request {
  fill: var(--request);
}
.message.reply {
  fill: var(--reply);
}
.message.direct {
  fill: var(--cache);
}
.controls {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-top: 1px solid #d9e0e7;
  background: var(--panel);
}
button {
  border: 1px solid #b7c2ce;
  background: #ffffff;
  color: var(--ink);
  border-radius: 6px;
  padding: 8px 12px;
  font-weight: 650;
  cursor: pointer;
}
button:hover {
  background: #edf2f7;
}
button.active {
  border-color: #456179;
  background: #e8eef5;
}
.step-label {
  color: var(--muted);
  font-size: 14px;
  margin-left: auto;
}
aside {
  padding: 16px;
  overflow: auto;
  max-height: calc(100vh - 112px);
}
h2 {
  margin: 0 0 10px;
  font-size: 16px;
  letter-spacing: 0;
}
dl {
  display: grid;
  grid-template-columns: 126px 1fr;
  gap: 8px 10px;
  margin: 0 0 18px;
  font-size: 14px;
}
dt {
  color: var(--muted);
}
dd {
  margin: 0;
  font-weight: 650;
  overflow-wrap: anywhere;
}
.legend,
.resources,
.caches,
.log {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 13px;
}
.cache-panel {
  margin: 0 0 18px;
  padding: 12px;
  background: #fff8df;
  border: 1px solid #ecd39a;
  border-radius: 8px;
}
.cache-panel.hidden {
  display: none;
}
.cache-panel h2 {
  color: #744c0f;
}
.message-panel {
  margin: -16px -16px 18px;
  padding: 14px 16px 16px;
  background: #fff8ed;
  border-bottom: 1px solid #efd7bd;
  box-shadow: inset 4px 0 0 #f0a85d;
}
.message-panel.playing {
  background: #fff3e3;
  box-shadow: inset 4px 0 0 var(--request);
}
.message-panel h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.message-panel h2::before {
  content: "";
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--request);
}
.message-panel .log {
  max-height: 232px;
  overflow: auto;
}
.legend li,
.resources li,
.caches li,
.log li {
  padding: 7px 0;
  border-top: 1px solid #edf0f3;
}
.caches li {
  border-top-color: #ecd39a;
  overflow-wrap: anywhere;
}
.caches li.used {
  color: #6f3f00;
  font-weight: 700;
}
.message-panel .log li {
  padding: 8px 10px;
  border-top-color: #f1dcc7;
  border-left: 3px solid transparent;
}
.swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 8px;
  vertical-align: middle;
}
.log li.active {
  color: var(--ink);
  font-weight: 700;
}
.message-panel .log li.active {
  background: #fff0df;
  border-left-color: var(--request);
}
@media (max-width: 880px) {
  header {
    align-items: flex-start;
    flex-direction: column;
  }
  main {
    grid-template-columns: 1fr;
  }
  aside {
    max-height: none;
  }
}
"""


def build_visualization_js(network: P2PNetwork, result: SearchResult) -> str:
    payload = build_visualization_payload(network, result)
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f"const data = {data_json};\n" + """const svg = document.getElementById("network");
const log = document.getElementById("log");
const resources = document.getElementById("resources");
const stepLabel = document.getElementById("stepLabel");
const playButton = document.getElementById("play");
const statusLabel = document.getElementById("statusLabel");
const messagePanel = document.getElementById("messagePanel");
const caches = document.getElementById("caches");
const ns = "http://www.w3.org/2000/svg";
const resourceByNode = new Map(data.nodes.map((node) => [node.id, node.resources]));
const visualNodes = new Map();
const nodeElements = new Map();
const edgeElements = new Map();
const eventEndpoints = new Map();
const frames = buildFrames(data.events);
let currentFrame = -1;
let timer = null;

function makeSvg(tag, attrs = {}) {
  const el = document.createElementNS(ns, tag);
  for (const [key, value] of Object.entries(attrs)) {
    el.setAttribute(key, value);
  }
  return el;
}

function eventPhase(event) {
  if (event.kind === "reply") return 1;
  if (event.kind === "direct") return 2;
  return 0;
}

function buildFrames(events) {
  const frames = [];
  let current = null;
  for (const event of events) {
    const round = event.round === null ? -1 : event.round;
    const phase = eventPhase(event);
    const key = `${round}:${phase}`;
    if (!current || current.key !== key) {
      current = { key, round, phase, events: [] };
      frames.push(current);
    }
    current.events.push(event);
  }
  return frames;
}

function buildTopologyGraph() {
  const eventEdges = data.events.map((event) => ({
    source: event.source,
    target: event.target,
    eventStep: event.step,
    kind: event.kind,
  }));

  return {
    nodes: data.nodes,
    baseEdges: data.edges,
    eventEdges,
    width: data.layout.width,
    height: data.layout.height,
  };
}

function clearSvg() {
  svg.innerHTML = "";
  visualNodes.clear();
  nodeElements.clear();
  edgeElements.clear();
  eventEndpoints.clear();
}

function renderGraph() {
  clearSvg();
  const graph = buildTopologyGraph();
  svg.setAttribute("viewBox", `0 0 ${graph.width} ${graph.height}`);
  const baseEdgeLayer = makeSvg("g");
  const eventEdgeLayer = makeSvg("g");
  const nodeLayer = makeSvg("g");
  svg.append(baseEdgeLayer, eventEdgeLayer, nodeLayer);

  const graphNodeById = new Map(graph.nodes.map((node) => [node.id, node]));

  for (const edge of graph.baseEdges) {
    const source = graphNodeById.get(edge.source);
    const target = graphNodeById.get(edge.target);
    if (!source || !target) continue;
    const line = makeSvg("line", {
      class: "graph-edge base",
      x1: source.x,
      y1: source.y,
      x2: target.x,
      y2: target.y,
    });
    baseEdgeLayer.append(line);
  }

  for (const edge of graph.eventEdges) {
    const source = graphNodeById.get(edge.source);
    const target = graphNodeById.get(edge.target);
    if (!source || !target) continue;
    const id = `event-${edge.eventStep}`;
    const line = makeSvg("line", {
      class: `graph-edge event-edge ${edge.kind}`,
      x1: source.x,
      y1: source.y,
      x2: target.x,
      y2: target.y,
    });
    eventEdgeLayer.append(line);
    edgeElements.set(id, line);
    eventEndpoints.set(edge.eventStep, {
      source: edge.source,
      target: edge.target,
      edgeId: id,
    });
  }

  for (const node of graph.nodes) {
    const classes = ["node"];
    if (data.uses_cache && node.cache_relevant) classes.push("cache");
    const group = makeSvg("g", { class: classes.join(" "), transform: `translate(${node.x}, ${node.y})` });
    group.dataset.node = node.id;
    const title = makeSvg("title");
    const searchedCache = (node.cache || []).find((entry) => entry.resource === data.result.resource_id);
    const cacheText = searchedCache
      ? ` · cache: ${searchedCache.resource} -> ${searchedCache.holder}`
      : "";
    title.textContent = `${node.id}: ${(resourceByNode.get(node.id) || []).join(", ")}${cacheText}`;
    group.append(title);
    if (data.uses_cache && node.cache_relevant) {
      group.append(makeSvg("circle", { class: "cache-ring", r: 31 }));
    }
    group.append(makeSvg("circle", { r: 24 }));
    const label = makeSvg("text");
    label.textContent = node.id;
    group.append(label);
    nodeLayer.append(group);
    nodeElements.set(node.id, group);
    visualNodes.set(node.id, node);
  }
}

function renderCacheList() {
  if (!data.uses_cache) return;
  const relevantNodes = data.nodes.filter((node) => node.cache_relevant);
  if (relevantNodes.length === 0) {
    const item = document.createElement("li");
    item.textContent = "Nenhum cache para este recurso.";
    caches.append(item);
    return;
  }

  for (const node of relevantNodes) {
    const entry = node.cache.find((cacheEntry) => cacheEntry.resource === data.result.resource_id);
    if (!entry) continue;
    const item = document.createElement("li");
    item.dataset.node = node.id;
    const origin = entry.local ? "local" : "aprendido";
    const label = `${node.id}: ${entry.resource} -> ${entry.holder} (${origin})`;
    item.textContent = label;
    if (node.cache_used) item.dataset.usedLabel = `${label} · usado nesta busca`;
    caches.append(item);
  }
}

function renderStaticLists() {
  renderCacheList();
  for (const node of data.nodes) {
    const item = document.createElement("li");
    item.textContent = `${node.id}: ${node.resources.join(", ")}`;
    resources.append(item);
  }
}

function formatLogMessage(event) {
  const ttl = event.ttl === null ? "" : `, ttl=${event.ttl}`;
  const round = event.round === null ? "-" : event.round;
  const kindLabel = event.kind === "direct" ? "conexão direta" : event.kind;
  return `${event.step}. round=${round} ${kindLabel}: ${event.source} -> ${event.target}${ttl}`;
}

function appendFrameLog(frame) {
  for (const item of log.children) item.classList.remove("active");
  for (const event of frame.events) {
    const item = document.createElement("li");
    item.dataset.step = event.step;
    item.textContent = formatLogMessage(event);
    item.classList.add("active");
    log.append(item);
  }
  log.scrollTop = log.scrollHeight;
}

function renderView() {
  renderGraph();
  markBaseNodes();
}

function render() {
  renderStaticLists();
  reset();
}

function clearActive() {
  for (const edge of edgeElements.values()) {
    edge.classList.remove("active-request", "active-reply", "active-direct");
  }
  for (const node of nodeElements.values()) {
    node.classList.remove("active");
  }
}

function hideFinalStatus() {
  statusLabel.textContent = "EXPLORANDO";
  statusLabel.classList.remove("found", "not-found");
  statusLabel.classList.add("pending");
  if (frames.length === 0) {
    revealFinalStatus();
  }
}

function revealFinalStatus() {
  statusLabel.textContent = statusLabel.dataset.finalStatus;
  statusLabel.classList.remove("pending", "found", "not-found");
  statusLabel.classList.add(statusLabel.dataset.finalClass);
}

function markBaseNodes() {
  for (const node of nodeElements.values()) {
    const nodeId = node.dataset.node;
    if (nodeId === data.result.start_node) {
      node.classList.add("start", "involved");
    }
    if (data.result.holder && nodeId === data.result.holder) {
      node.classList.add("holder");
    }
    if (data.resource_holder && nodeId === data.resource_holder) {
      node.classList.add("holder");
    }
  }
}

function markCacheAccessed(nodeId) {
  if (!data.uses_cache) return;
  const node = nodeElements.get(nodeId);
  if (!node) return;
  const nodeData = data.nodes.find((item) => item.id === nodeId);
  if (!nodeData || !nodeData.cache_used) return;
  node.classList.add("cache-accessed");
  const cacheItem = caches.querySelector(`[data-node="${nodeId}"]`);
  if (cacheItem) {
    cacheItem.classList.add("used");
    cacheItem.textContent = cacheItem.dataset.usedLabel || cacheItem.textContent;
  }
}

function setStepLabel() {
  if (frames.length === 0 || currentFrame < 0) {
    stepLabel.textContent = `Quadro 0 / ${frames.length}`;
    return;
  }
  const frame = frames[currentFrame];
  const round = frame.round < 0 ? "-" : frame.round;
  const phase = frame.phase === 1 ? "resposta" : frame.phase === 2 ? "conexão direta" : "requisições";
  stepLabel.textContent = `Quadro ${currentFrame + 1} / ${frames.length} · rodada ${round} · ${phase}`;
}

function reset() {
  stop();
  currentFrame = -1;
  clearActive();
  for (const node of nodeElements.values()) {
    node.classList.remove("involved", "start", "holder", "cache-accessed");
  }
  log.innerHTML = "";
  messagePanel.classList.remove("playing");
  svg.querySelectorAll(".message").forEach((message) => message.remove());
  renderView();
  hideFinalStatus();
  setStepLabel();
}

function animateSingleEvent(event) {
  const endpoint = eventEndpoints.get(event.step);
  if (!endpoint) return;
  const source = visualNodes.get(endpoint.source);
  const target = visualNodes.get(endpoint.target);
  if (!source || !target) return;
  const edge = edgeElements.get(endpoint.edgeId);
  const sourceNode = nodeElements.get(endpoint.source);
  const targetNode = nodeElements.get(endpoint.target);
  const activeClass = event.kind === "reply" ? "active-reply" : event.kind === "direct" ? "active-direct" : "active-request";
  if (edge) edge.classList.add(activeClass);
  if (sourceNode) sourceNode.classList.add("active", "involved");
  if (targetNode) targetNode.classList.add("active", "involved");
  const touchedNodes = [sourceNode, targetNode];
  for (const node of touchedNodes) {
    if (node) markCacheAccessed(node.dataset.node);
  }

  const message = makeSvg("circle", {
    class: `message ${event.kind}`,
    r: 7,
    cx: source.x,
    cy: source.y,
  });
  const moveX = makeSvg("animate", {
    attributeName: "cx",
    from: source.x,
    to: target.x,
    dur: "0.52s",
    fill: "freeze",
  });
  const moveY = makeSvg("animate", {
    attributeName: "cy",
    from: source.y,
    to: target.y,
    dur: "0.52s",
    fill: "freeze",
  });
  message.append(moveX, moveY);
  svg.append(message);
  moveX.beginElement();
  moveY.beginElement();
  setTimeout(() => message.remove(), 680);
}

function animateFrame(frame) {
  clearActive();
  messagePanel.classList.add("playing");
  svg.querySelectorAll(".message").forEach((message) => message.remove());
  for (const event of frame.events) {
    animateSingleEvent(event);
  }
  appendFrameLog(frame);
  setStepLabel();
}

function step() {
  if (currentFrame + 1 >= frames.length) {
    revealFinalStatus();
    stop();
    return;
  }
  currentFrame += 1;
  animateFrame(frames[currentFrame]);
  if (currentFrame + 1 >= frames.length) {
    revealFinalStatus();
    stop();
  }
}

function play() {
  if (timer) {
    stop();
    return;
  }
  if (currentFrame + 1 >= frames.length) reset();
  playButton.textContent = "Pausar";
  step();
  if (currentFrame + 1 < frames.length) {
    timer = setInterval(step, 820);
  } else {
    playButton.textContent = "Reproduzir";
  }
}

function stop() {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
  playButton.textContent = "Reproduzir";
}

document.getElementById("play").addEventListener("click", play);
document.getElementById("step").addEventListener("click", step);
document.getElementById("reset").addEventListener("click", reset);
render();
"""


def visualization_asset_paths(output: Path) -> Dict[str, Path]:
    return {
        "html": output,
        "css": output.with_suffix(".css"),
        "js": output.with_suffix(".js"),
    }


def write_visualization_files(output: Path, network: P2PNetwork, result: SearchResult) -> Dict[str, Path]:
    paths = visualization_asset_paths(output)
    paths["html"].parent.mkdir(parents=True, exist_ok=True)
    paths["html"].write_text(
        build_visualization_html(network, result, paths["css"].name, paths["js"].name),
        encoding="utf-8",
    )
    paths["css"].write_text(build_visualization_css(), encoding="utf-8")
    paths["js"].write_text(build_visualization_js(network, result), encoding="utf-8")
    return paths
