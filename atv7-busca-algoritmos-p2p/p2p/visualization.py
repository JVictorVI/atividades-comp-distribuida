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
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def _read_asset(filename: str) -> str:
    return (ASSET_DIR / filename).read_text(encoding="utf-8")

def _looks_like_network_config(text: str) -> bool:
    return "resources" in text and "edges" in text

def list_visualization_configs() -> Sequence[Dict[str, str]]:
    examples_dir = PROJECT_ROOT / "examples"
    if not examples_dir.exists():
        return []

    configs = []
    for path in sorted(examples_dir.iterdir()):
        if path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        content = path.read_text(encoding="utf-8")
        if not _looks_like_network_config(content):
            continue
        configs.append(
            {
                "name": path.name,
                "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "content": content,
            }
        )
    return configs

# Gera uma representação textual do resultado de uma busca, incluindo detalhes como o caminho percorrido, os nós envolvidos e as mensagens trocadas.
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


def _node_sort_key(node: str) -> Tuple[int, int, str]:
    text = str(node)
    if text.lower().startswith("n") and text[1:].isdigit():
        return (0, int(text[1:]), text)
    return (1, 0, text)


def sequential_layers(
    nodes: Sequence[str],
    edges: Iterable[Tuple[str, str]],
    root: str = "n1",
) -> Sequence[Sequence[str]]:
    ordered_nodes = sorted(nodes, key=_node_sort_key)
    if not ordered_nodes:
        return []

    node_set = set(ordered_nodes)
    adjacency = {node: set() for node in ordered_nodes}
    for source, target in edges:
        if source not in node_set or target not in node_set:
            continue
        adjacency[source].add(target)
        adjacency[target].add(source)

    start = root if root in node_set else ordered_nodes[0]
    visited = {start}
    queue = [(start, 0)]
    layers = [[start]]

    while queue:
        node, depth = queue.pop(0)
        for neighbor in sorted(adjacency[node], key=_node_sort_key):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            next_depth = depth + 1
            while len(layers) <= next_depth:
                layers.append([])
            layers[next_depth].append(neighbor)
            queue.append((neighbor, next_depth))

    remaining = [node for node in ordered_nodes if node not in visited]
    if remaining:
        layers.append(remaining)

    return [sorted(layer, key=_node_sort_key) for layer in layers if layer]


def graph_layout_dimensions(
    nodes: Sequence[str],
    edges: Iterable[Tuple[str, str]],
) -> Tuple[int, int]:
    layers = sequential_layers(nodes, edges)
    layer_count = max(1, len(layers))
    widest_layer = max((len(layer) for layer in layers), default=1)
    width = max(760, 180 + widest_layer * 84)
    height = max(980, 180 + (layer_count - 1) * 170, round(width * 1.18))
    return width, height

# Calcula um layout fixo usando a topologia da rede em camadas verticais, a partir de n1.
def topology_layout(
    nodes: Sequence[str],
    edges: Iterable[Tuple[str, str]],
    width: int | None = None,
    height: int | None = None,
) -> Dict[str, Dict[str, float]]:
    """Calcula um layout fixo usando apenas a topologia da rede."""

    edge_list = list(edges)
    layers = sequential_layers(nodes, edge_list)
    if not layers:
        return {}

    if width is None or height is None:
        width, height = graph_layout_dimensions(nodes, edge_list)

    padding_x = 90
    padding_y = 90
    usable_width = max(1, width - 2 * padding_x)
    usable_height = max(1, height - 2 * padding_y)
    last_layer_index = max(1, len(layers) - 1)
    positions = {}

    for layer_index, layer in enumerate(layers):
        y = (
            height / 2
            if len(layers) == 1
            else padding_y + (usable_height * layer_index / last_layer_index)
        )
        gap = usable_width / (len(layer) + 1)
        for node_index, node in enumerate(layer):
            positions[node] = {
                "x": round(padding_x + gap * (node_index + 1), 2),
                "y": round(y, 2),
            }

    return positions

# Gera o payload de dados necessário para a visualização, incluindo a topologia da rede, os eventos da busca e o estado dos caches dos nós.
def build_visualization_payload(network: P2PNetwork, result: SearchResult) -> Dict[str, object]:
    edge_list = sorted(network.edges)
    layout_width, layout_height = graph_layout_dimensions(network.nodes, edge_list)
    positions = topology_layout(network.nodes, edge_list, layout_width, layout_height)
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
        "config": {
            "num_nodes": network.num_nodes,
            "min_neighbors": network.min_neighbors,
            "max_neighbors": network.max_neighbors,
        },
        "uses_cache": algorithm_uses_cache and has_relevant_cache,
        "has_configured_cache": algorithm_uses_cache and has_configured_cache,
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
                "cache_relevant": algorithm_uses_cache and cache_is_relevant(node),
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

# Gera o conteúdo HTML para a visualização, incorporando os links para os arquivos CSS e JS necessários e estruturando a página com seções para a visualização do grafo, os logs de mensagens e os detalhes da busca.
def build_visualization_html(
    network: P2PNetwork,
    result: SearchResult,
    css_href: str = "visualization.css",
    js_src: str = "visualization.js",
) -> str:
    title = html_escape(f"Rede P2P")
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
    <h1 id="appTitle">Rede P2P</h1>
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
        <input id="startNode" name="startNode" list="nodeOptions" autocomplete="off">
        <datalist id="nodeOptions"></datalist>
      </label>
      <label>Recurso
        <input id="resourceId" name="resourceId" list="resourceOptions" autocomplete="off">
        <datalist id="resourceOptions"></datalist>
      </label>
      <label>TTL
        <input id="ttl" name="ttl" type="number" min="0" step="1">
      </label>
      <label>Rede
        <select id="configSelect" name="configSelect"></select>
      </label>
      <label class="check-field">
        <input id="ignoreCache" name="ignoreCache" type="checkbox">
        Ignorar cache
      </label>
      <div class="form-actions">
        <button type="submit" class="primary">Aplicar e iniciar</button>
      </div>
    </form>
    <div class="error-panel hidden" id="errorPanel" role="alert"></div>
    <div class="editor-status" id="editorStatus" aria-live="polite"></div>
  </section>

  <main>
    <section class="graph-panel" aria-label="Visualização do grafo da rede P2P">
      <div class="status pending" id="statusLabel" data-final-status="ENCONTRADO" data-final-class="found">EXPLORANDO</div>
      <svg id="network" viewBox="0 0 760 980" role="img" aria-label="Grafo da rede P2P e mensagens da busca"></svg>
      <div class="controls">
        <button type="button" id="play">Reproduzir animação completa</button>
        <button type="button" id="step">Avançar rodada</button>
        <button type="button" id="reset">Reiniciar animação</button>
        <button type="button" id="randomExample">Novo exemplo random</button>
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
      <section class="tutorial-panel" aria-label="Tutorial de uso">
        <h2>Tutorial</h2>
        <ol>
          <li>Escolha um um arquivo de topologia no seletor superior ou edite os campos da topologia manualmente.</li>
          <li>Escolha o algoritmo, o nó inicial, o recurso procurado e o TTL.</li>
          <li>Clique em Executar para recalcular a busca.</li>
          <li>Use os botões da barra inferior para controlar a animação.</li>
          <li>Em random walk, use Novo exemplo random para sortear outra execução.</li>
        </ol>
      </section>
      <section class="mesh-editor" aria-label="Editor da rede">
        <h2>Topologia da Rede</h2>
        <div class="editor-grid">
          <div class="mesh-numbers">
            <label>Nós
              <input id="meshNumNodes" type="number" min="1" step="1">
            </label>
            <label>Mín. vizinhos
              <input id="meshMinNeighbors" type="number" min="0" step="1">
            </label>
            <label>Máx. vizinhos
              <input id="meshMaxNeighbors" type="number" min="0" step="1">
            </label>
          </div>
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
            <button type="button" id="applyMesh">Aplicar alterações</button>
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
    configs_json = json.dumps(list_visualization_configs(), ensure_ascii=False).replace("</", "<\\/")
    return (
        f"window.P2P_INITIAL_DATA = {data_json};\n"
        f"window.P2P_CONFIG_FILES = {configs_json};\n"
        + _read_asset("visualization_app.js")
    )


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
