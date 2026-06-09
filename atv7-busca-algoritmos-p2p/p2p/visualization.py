"""Geração da visualização HTML da rede e da animação da busca."""

from __future__ import annotations

import json
import math
from html import escape as html_escape
from pathlib import Path
from typing import Dict, Iterable, Sequence, Tuple

from .models import SearchResult
from .network import P2PNetwork


ASSET_DIR = Path(__file__).resolve().parent / "assets"


def _read_asset(filename: str) -> str:
    return (ASSET_DIR / filename).read_text(encoding="utf-8")


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
    algorithm_uses_cache = result.algorithm in {"informed_flooding", "informed_random_walk"}
    cache_snapshot = result.cache_snapshot or network.caches

    def cache_for(node: str) -> Dict[str, str]:
        return cache_snapshot.get(node, {})

    def cache_is_relevant(node: str) -> bool:
        cached_holder = cache_for(node).get(result.resource_id)
        return bool(node != result.start_node and cached_holder and cached_holder != node)

    has_relevant_cache = any(cache_is_relevant(node) for node in network.nodes)
    has_configured_cache = any(
        holder != node
        for node in network.nodes
        for holder in cache_for(node).values()
    )

    return {
        "layout": {"width": layout_width, "height": layout_height},
        "uses_cache": has_relevant_cache,
        "has_configured_cache": has_configured_cache,
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
                    algorithm_uses_cache
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


def build_visualization_html(
    network: P2PNetwork,
    result: SearchResult,
    css_href: str = "visualization.css",
    js_src: str = "visualization.js",
) -> str:
    title = html_escape(f"P2P Search - {result.algorithm}")
    css_href = html_escape(css_href)
    js_src = html_escape(js_src)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="{css_href}">
</head>
<body>
  <header>
    <h1 id="appTitle">Rede P2P - {html_escape(result.algorithm)}</h1>
  </header>

  <section class="query-panel" aria-label="Parâmetros da busca">
    <form class="query-form" id="searchForm">
      <label>Algoritmo
        <select id="algorithm" name="algorithm">
          <option value="flooding">Flooding</option>
          <option value="informed_flooding">Flooding informado</option>
          <option value="random_walk">Random walk</option>
          <option value="informed_random_walk">Random walk informado</option>
        </select>
      </label>
      <label>Nó inicial
        <select id="startNode" name="startNode"></select>
      </label>
      <label>Recurso
        <input id="resourceId" name="resourceId" list="resourceOptions" autocomplete="off">
        <datalist id="resourceOptions"></datalist>
      </label>
      <label>TTL
        <input id="ttl" name="ttl" type="number" min="0" step="1">
      </label>
      <label>Arquivo YAML/JSON
        <input id="configFile" name="configFile" type="file" accept=".yaml,.yml,.json">
      </label>
      <label class="check-field">
        <input id="ignoreCache" name="ignoreCache" type="checkbox">
        Ignorar cache
      </label>
      <div class="form-actions">
        <button type="submit" class="primary">Executar</button>
        <button type="button" id="randomExample">Novo exemplo random</button>
      </div>
    </form>
    <div class="editor-status" id="editorStatus" aria-live="polite"></div>
  </section>

  <main>
    <section class="graph-panel" aria-label="Visualização do grafo da rede P2P">
      <div class="status pending" id="statusLabel" data-final-status="ENCONTRADO" data-final-class="found">EXPLORANDO</div>
      <svg id="network" viewBox="0 0 1080 700" role="img" aria-label="Grafo da rede P2P e mensagens da busca"></svg>
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
      <section class="cache-panel hidden" id="cachePanel" aria-label="Caches dos nós">
        <h2>Caches dos nós</h2>
        <ul class="caches" id="caches"></ul>
      </section>
      <h2>Busca</h2>
      <dl id="searchStats"></dl>
      <h2>Legenda</h2>
      <ul class="legend">
        <li><span class="swatch" style="background: var(--start)"></span>nó inicial</li>
        <li><span class="swatch" style="background: var(--found)"></span>nó com recurso</li>
        <li id="cacheLegendItem" class="hidden"><span class="swatch" style="background: var(--cache)"></span>nó com cache do recurso</li>
        <li><span class="swatch" style="background: var(--request)"></span>requisição</li>
        <li><span class="swatch" style="background: var(--reply)"></span>resposta</li>
      </ul>
      <h2 class="section-gap">Recursos</h2>
      <ul class="resources" id="resources"></ul>
      <section class="mesh-editor" aria-label="Editor do mesh">
        <h2>Mesh</h2>
        <div class="editor-grid">
          <label>Recursos
            <textarea id="meshResources" spellcheck="false"></textarea>
          </label>
          <label>Arestas
            <textarea id="meshEdges" spellcheck="false"></textarea>
          </label>
          <label>Caches
            <textarea id="meshCaches" spellcheck="false"></textarea>
          </label>
          <div class="editor-actions">
            <button type="button" id="applyMesh">Aplicar mesh</button>
          </div>
        </div>
      </section>
    </aside>
  </main>
  <script src="{js_src}"></script>
</body>
</html>
"""


def build_visualization_css() -> str:
    return _read_asset("visualization_app.css")


def build_visualization_js(network: P2PNetwork, result: SearchResult) -> str:
    payload = build_visualization_payload(network, result)
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f"window.P2P_INITIAL_DATA = {data_json};\n" + _read_asset("visualization_app.js")


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
