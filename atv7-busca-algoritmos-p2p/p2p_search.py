"""Simulador de busca em redes P2P não estruturadas.

O módulo implementa validação de topologia, busca por inundação, passeio
aleatório e as variações informadas com cache local por nó.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from html import escape as html_escape
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Set, Tuple


ALGORITHM_ORDER = [
    "flooding",
    "informed_flooding",
    "random_walk",
    "informed_random_walk",
]

ALGORITHMS = set(ALGORITHM_ORDER)

ALGORITHM_CHOICES = sorted(ALGORITHMS)


class ConfigError(ValueError):
    """Erro encontrado no arquivo de configuração da rede."""


class SearchError(ValueError):
    """Erro encontrado nos parâmetros de uma operação de busca."""


@dataclass
class MessageEvent:
    step: int
    kind: str
    source: str
    target: str
    resource_id: str
    ttl: Optional[int]

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResult:
    algorithm: str
    start_node: str
    resource_id: str
    ttl: int
    found: bool
    holder: Optional[str]
    informed_by: Optional[str]
    found_via: Optional[str]
    messages: int
    nodes_involved: int
    path: List[str]
    events: List[MessageEvent] = field(default_factory=list)

    def as_dict(self, include_events: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        data["path"] = " -> ".join(self.path)
        if include_events:
            data["events"] = [event.as_dict() for event in self.events]
        else:
            data.pop("events", None)
        return data


def load_config(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if path.suffix.lower() == ".json" or stripped.startswith("{"):
        return json.loads(text)
    return parse_simple_yaml(text)


def parse_simple_yaml(text: str) -> Dict[str, Any]:
    """Parser pequeno para o formato YAML simples usado no enunciado.

    Suporta escalares no topo, um bloco `resources` com `nó: r1, r2` e um
    bloco `edges` com linhas `n1, n2`, `- n1, n2` ou `- [n1, n2]`.
    """

    data: Dict[str, Any] = {"resources": {}, "edges": []}
    section: Optional[str] = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        if line in {"resources:", "edges:"}:
            section = line[:-1]
            continue

        if section == "resources":
            if ":" not in line:
                raise ConfigError(f"Linha {line_number}: recurso inválido: {raw_line!r}")
            node, values = line.split(":", 1)
            data["resources"][node.strip()] = parse_list(values)
            continue

        if section == "edges":
            data["edges"].append(parse_edge_line(line, line_number))
            continue

        if ":" not in line:
            raise ConfigError(f"Linha {line_number}: entrada invalida: {raw_line!r}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in {"num_nodes", "min_neighbors", "max_neighbors"}:
            try:
                data[key] = int(value)
            except ValueError as exc:
                raise ConfigError(f"Linha {line_number}: {key} deve ser inteiro") from exc
        else:
            data[key] = value

    return data


def parse_list(value: Any) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        return [clean_token(item) for item in value if clean_token(item)]
    value = str(value).strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [token for token in (clean_token(part) for part in value.split(",")) if token]


def parse_edge_line(line: str, line_number: int) -> Tuple[str, str]:
    if line.startswith("-"):
        line = line[1:].strip()
    parts = parse_list(line)
    if len(parts) != 2:
        raise ConfigError(f"Linha {line_number}: aresta deve ter exatamente dois nós")
    return parts[0], parts[1]


def clean_token(value: Any) -> str:
    return str(value).strip().strip("\"'")


class P2PNetwork:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.num_nodes = self._required_int(config, "num_nodes")
        self.min_neighbors = self._required_int(config, "min_neighbors")
        self.max_neighbors = self._required_int(config, "max_neighbors")

        if self.num_nodes <= 0:
            raise ConfigError("num_nodes deve ser maior que zero")
        if self.min_neighbors < 0 or self.max_neighbors < 0:
            raise ConfigError("min_neighbors e max_neighbors não podem ser negativos")
        if self.min_neighbors > self.max_neighbors:
            raise ConfigError("min_neighbors não pode ser maior que max_neighbors")
        if self.max_neighbors > self.num_nodes - 1:
            raise ConfigError("max_neighbors não pode exceder num_nodes - 1")

        self.nodes = [f"n{i}" for i in range(1, self.num_nodes + 1)]
        self.node_set = set(self.nodes)
        self.resources = self._normalize_resources(config.get("resources", {}))
        self.adjacency, self.edges = self._normalize_edges(config.get("edges", []))
        self.resource_locations = self._build_resource_locations()
        self._validate()
        self.reset_caches()

    @classmethod
    def from_file(cls, path: Path) -> "P2PNetwork":
        return cls(load_config(path))

    @staticmethod
    def _required_int(config: Dict[str, Any], key: str) -> int:
        if key not in config:
            raise ConfigError(f"Campo obrigatório ausente: {key}")
        try:
            return int(config[key])
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"{key} deve ser inteiro") from exc

    def _normalize_resources(self, raw_resources: Any) -> Dict[str, Set[str]]:
        if not isinstance(raw_resources, dict):
            raise ConfigError("resources deve ser um mapa nó -> lista de recursos")

        resources: Dict[str, Set[str]] = {node: set() for node in self.nodes}
        for node, raw_values in raw_resources.items():
            node = clean_token(node)
            if node not in self.node_set:
                raise ConfigError(f"resources contém nó desconhecido: {node}")
            parsed = set(parse_list(raw_values))
            if not parsed:
                raise ConfigError(f"Nó {node} está sem recursos")
            resources[node] = parsed
        return resources

    def _normalize_edges(self, raw_edges: Any) -> Tuple[Dict[str, Set[str]], Set[Tuple[str, str]]]:
        if not isinstance(raw_edges, list):
            raise ConfigError("edges deve ser uma lista")

        adjacency: Dict[str, Set[str]] = {node: set() for node in self.nodes}
        edges: Set[Tuple[str, str]] = set()

        for raw_edge in raw_edges:
            node_a, node_b = self._parse_edge(raw_edge)
            if node_a not in self.node_set or node_b not in self.node_set:
                raise ConfigError(f"Aresta contém nó desconhecido: {node_a}, {node_b}")
            if node_a == node_b:
                raise ConfigError(f"Aresta de um nó para ele mesmo não é permitida: {node_a}")

            edge = tuple(sorted((node_a, node_b)))
            if edge in edges:
                continue
            edges.add(edge)
            adjacency[node_a].add(node_b)
            adjacency[node_b].add(node_a)

        return adjacency, edges

    @staticmethod
    def _parse_edge(raw_edge: Any) -> Tuple[str, str]:
        if isinstance(raw_edge, dict):
            node_a = raw_edge.get("from") or raw_edge.get("source") or raw_edge.get("a")
            node_b = raw_edge.get("to") or raw_edge.get("target") or raw_edge.get("b")
            if not node_a or not node_b:
                raise ConfigError("Aresta em objeto deve conter from/to")
            return clean_token(node_a), clean_token(node_b)

        if isinstance(raw_edge, str):
            parts = parse_list(raw_edge)
        elif isinstance(raw_edge, (list, tuple)):
            parts = [clean_token(part) for part in raw_edge]
        else:
            raise ConfigError(f"Aresta inválida: {raw_edge!r}")

        if len(parts) != 2:
            raise ConfigError(f"Aresta deve ter exatamente dois nós: {raw_edge!r}")
        return parts[0], parts[1]

    def _build_resource_locations(self) -> Dict[str, Set[str]]:
        locations: Dict[str, Set[str]] = defaultdict(set)
        for node, resources in self.resources.items():
            for resource in resources:
                locations[resource].add(node)
        return dict(locations)

    def _validate(self) -> None:
        nodes_without_resources = [node for node, values in self.resources.items() if not values]
        if nodes_without_resources:
            raise ConfigError("Nós sem recursos: " + ", ".join(nodes_without_resources))

        invalid_degrees = [
            (node, len(neighbors))
            for node, neighbors in self.adjacency.items()
            if len(neighbors) < self.min_neighbors or len(neighbors) > self.max_neighbors
        ]
        if invalid_degrees:
            details = ", ".join(f"{node}={degree}" for node, degree in invalid_degrees)
            raise ConfigError(
                "Quantidade de vizinhos fora dos limites "
                f"[{self.min_neighbors}, {self.max_neighbors}]: {details}"
            )

        if not self._is_connected():
            raise ConfigError("A rede está particionada")

    def _is_connected(self) -> bool:
        visited = {self.nodes[0]}
        queue: Deque[str] = deque([self.nodes[0]])
        while queue:
            node = queue.popleft()
            for neighbor in self.adjacency[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return len(visited) == len(self.nodes)

    def reset_caches(self) -> None:
        self.caches: Dict[str, Dict[str, str]] = {
            node: {resource: node for resource in resources}
            for node, resources in self.resources.items()
        }

    def search(
        self,
        node_id: str,
        resource_id: str,
        ttl: int,
        algorithm: str,
        seed: Optional[int] = None,
    ) -> SearchResult:
        node_id = clean_token(node_id)
        resource_id = clean_token(resource_id)
        if node_id not in self.node_set:
            raise SearchError(f"Nó inicial desconhecido: {node_id}")
        if not resource_id:
            raise SearchError("resource_id não pode ser vazio")
        if ttl < 0:
            raise SearchError("ttl não pode ser negativo")
        if algorithm not in ALGORITHMS:
            raise SearchError(f"Algoritmo inválido: {algorithm}")

        if algorithm in {"flooding", "informed_flooding"}:
            return self._flooding(node_id, resource_id, ttl, algorithm)

        rng = random.Random(seed)
        return self._random_walk(node_id, resource_id, ttl, algorithm, rng)

    def _flooding(
        self, start: str, resource_id: str, ttl: int, algorithm: str
    ) -> SearchResult:
        use_cache = algorithm == "informed_flooding"
        queue: Deque[Tuple[str, int, List[str]]] = deque([(start, ttl, [start])])
        seen = {start}
        involved = {start}
        messages = 0
        events: List[MessageEvent] = []

        while queue:
            current, remaining_ttl, path = queue.popleft()
            holder, found_via = self._lookup(current, resource_id, use_cache)
            if holder is not None:
                return self._success(
                    algorithm,
                    start,
                    resource_id,
                    ttl,
                    holder,
                    current,
                    found_via,
                    messages,
                    involved,
                    path,
                    events,
                )

            if remaining_ttl == 0:
                continue

            for neighbor in sorted(self.adjacency[current]):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                involved.add(neighbor)
                messages += 1
                self._add_event(events, "request", current, neighbor, resource_id, remaining_ttl - 1)
                queue.append((neighbor, remaining_ttl - 1, path + [neighbor]))

        return self._failure(algorithm, start, resource_id, ttl, messages, involved, [start], events)

    def _random_walk(
        self,
        start: str,
        resource_id: str,
        ttl: int,
        algorithm: str,
        rng: random.Random,
    ) -> SearchResult:
        use_cache = algorithm == "informed_random_walk"
        current = start
        path = [start]
        involved = {start}
        messages = 0
        remaining_ttl = ttl
        events: List[MessageEvent] = []

        while True:
            holder, found_via = self._lookup(current, resource_id, use_cache)
            if holder is not None:
                return self._success(
                    algorithm,
                    start,
                    resource_id,
                    ttl,
                    holder,
                    current,
                    found_via,
                    messages,
                    involved,
                    path,
                    events,
                )

            if remaining_ttl == 0:
                return self._failure(algorithm, start, resource_id, ttl, messages, involved, path, events)

            neighbors = sorted(self.adjacency[current])
            if not neighbors:
                return self._failure(algorithm, start, resource_id, ttl, messages, involved, path, events)

            previous = current
            current = rng.choice(neighbors)
            path.append(current)
            involved.add(current)
            messages += 1
            self._add_event(events, "request", previous, current, resource_id, remaining_ttl - 1)
            remaining_ttl -= 1

    def _lookup(self, node: str, resource_id: str, use_cache: bool) -> Tuple[Optional[str], Optional[str]]:
        if resource_id in self.resources[node]:
            return node, "local"
        if use_cache and resource_id in self.caches[node]:
            return self.caches[node][resource_id], "cache"
        return None, None

    @staticmethod
    def _add_event(
        events: List[MessageEvent],
        kind: str,
        source: str,
        target: str,
        resource_id: str,
        ttl: Optional[int],
    ) -> None:
        events.append(
            MessageEvent(
                step=len(events) + 1,
                kind=kind,
                source=source,
                target=target,
                resource_id=resource_id,
                ttl=ttl,
            )
        )

    def _success(
        self,
        algorithm: str,
        start: str,
        resource_id: str,
        ttl: int,
        holder: str,
        informed_by: str,
        found_via: Optional[str],
        query_messages: int,
        involved: Set[str],
        path: List[str],
        events: List[MessageEvent],
    ) -> SearchResult:
        for source, target in zip(reversed(path[1:]), reversed(path[:-1])):
            self._add_event(events, "reply", source, target, resource_id, None)
        reply_messages = max(0, len(path) - 1)
        self._learn(path, resource_id, holder)
        return SearchResult(
            algorithm=algorithm,
            start_node=start,
            resource_id=resource_id,
            ttl=ttl,
            found=True,
            holder=holder,
            informed_by=informed_by,
            found_via=found_via,
            messages=query_messages + reply_messages,
            nodes_involved=len(involved),
            path=path,
            events=events,
        )

    @staticmethod
    def _failure(
        algorithm: str,
        start: str,
        resource_id: str,
        ttl: int,
        messages: int,
        involved: Set[str],
        path: List[str],
        events: List[MessageEvent],
    ) -> SearchResult:
        return SearchResult(
            algorithm=algorithm,
            start_node=start,
            resource_id=resource_id,
            ttl=ttl,
            found=False,
            holder=None,
            informed_by=None,
            found_via=None,
            messages=messages,
            nodes_involved=len(involved),
            path=path,
            events=events,
        )

    def _learn(self, path: Iterable[str], resource_id: str, holder: str) -> None:
        for node in path:
            self.caches[node][resource_id] = holder

    def to_dot(self) -> str:
        lines = ["graph p2p {"]
        for node in self.nodes:
            resources = ", ".join(sorted(self.resources[node]))
            label = escape_dot(f"{node}\\n{resources}")
            lines.append(f'  "{escape_dot(node)}" [label="{label}"];')
        for node_a, node_b in sorted(self.edges):
            lines.append(f'  "{escape_dot(node_a)}" -- "{escape_dot(node_b)}";')
        lines.append("}")
        return "\n".join(lines)


def escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def format_result(result: SearchResult) -> str:
    lines = [
        f"status: {'FOUND' if result.found else 'NOT_FOUND'}",
        f"algorithm: {result.algorithm}",
        f"start_node: {result.start_node}",
        f"resource_id: {result.resource_id}",
        f"ttl: {result.ttl}",
        f"messages: {result.messages}",
        f"nodes_involved: {result.nodes_involved}",
        f"path: {' -> '.join(result.path)}",
    ]
    if result.found:
        lines.extend(
            [
                f"holder: {result.holder}",
                f"informed_by: {result.informed_by}",
                f"found_via: {result.found_via}",
            ]
        )
    return "\n".join(lines)


def print_table(results: Sequence[SearchResult]) -> None:
    rows = [
        [
            result.algorithm,
            "yes" if result.found else "no",
            result.holder or "-",
            str(result.messages),
            str(result.nodes_involved),
            " -> ".join(result.path),
        ]
        for result in results
    ]
    headers = ["algorithm", "found", "holder", "messages", "nodes", "path"]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows)) if rows else len(header)
        for index, header in enumerate(headers)
    ]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


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


def build_visualization_html(network: P2PNetwork, result: SearchResult) -> str:
    positions = circular_layout(network.nodes)
    payload = {
        "nodes": [
            {
                "id": node,
                "resources": sorted(network.resources[node]),
                "x": positions[node]["x"],
                "y": positions[node]["y"],
            }
            for node in network.nodes
        ],
        "edges": [{"source": node_a, "target": node_b} for node_a, node_b in sorted(network.edges)],
        "events": [event.as_dict() for event in result.events],
        "result": result.as_dict(),
    }
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    title = html_escape(f"P2P Search - {result.algorithm}")
    status = "FOUND" if result.found else "NOT FOUND"
    holder = result.holder or "-"
    found_via = result.found_via or "-"

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
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
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
      font-family: Segoe UI, Arial, sans-serif;
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 24px;
      border-bottom: 1px solid #d9e0e7;
      background: var(--panel);
    }}
    h1 {{
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .status {{
      font-weight: 700;
      color: {("#0f7a54" if result.found else "#9b1c1c")};
    }}
    main {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 320px;
      gap: 18px;
      padding: 18px;
    }}
    .graph-panel,
    aside {{
      background: var(--panel);
      border: 1px solid #d9e0e7;
      border-radius: 8px;
    }}
    .graph-panel {{
      overflow: hidden;
    }}
    svg {{
      display: block;
      width: 100%;
      height: min(72vh, 680px);
      min-height: 460px;
      background: #fbfcfd;
    }}
    .edge {{
      stroke: var(--line);
      stroke-width: 2;
    }}
    .edge.active-request {{
      stroke: var(--request);
      stroke-width: 4;
    }}
    .edge.active-reply {{
      stroke: var(--reply);
      stroke-width: 4;
    }}
    .node circle {{
      fill: var(--node);
      stroke: var(--node-border);
      stroke-width: 2.5;
    }}
    .node text {{
      font-size: 15px;
      font-weight: 700;
      text-anchor: middle;
      dominant-baseline: middle;
      fill: var(--ink);
      pointer-events: none;
    }}
    .node.start circle {{
      stroke: var(--start);
      stroke-width: 5;
    }}
    .node.involved circle {{
      fill: #edf6ff;
    }}
    .node.active circle {{
      fill: #fff4e8;
      stroke: var(--request);
      stroke-width: 5;
    }}
    .node.holder circle {{
      stroke: var(--found);
      stroke-width: 5;
    }}
    .message {{
      stroke: #ffffff;
      stroke-width: 2;
    }}
    .message.request {{
      fill: var(--request);
    }}
    .message.reply {{
      fill: var(--reply);
    }}
    .controls {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px;
      border-top: 1px solid #d9e0e7;
      background: var(--panel);
    }}
    button {{
      border: 1px solid #b7c2ce;
      background: #ffffff;
      color: var(--ink);
      border-radius: 6px;
      padding: 8px 12px;
      font-weight: 650;
      cursor: pointer;
    }}
    button:hover {{
      background: #edf2f7;
    }}
    .step-label {{
      color: var(--muted);
      font-size: 14px;
      margin-left: auto;
    }}
    aside {{
      padding: 16px;
      overflow: auto;
      max-height: calc(100vh - 112px);
    }}
    h2 {{
      margin: 0 0 10px;
      font-size: 16px;
      letter-spacing: 0;
    }}
    dl {{
      display: grid;
      grid-template-columns: 126px 1fr;
      gap: 8px 10px;
      margin: 0 0 18px;
      font-size: 14px;
    }}
    dt {{
      color: var(--muted);
    }}
    dd {{
      margin: 0;
      font-weight: 650;
      overflow-wrap: anywhere;
    }}
    .legend,
    .resources,
    .log {{
      margin: 0;
      padding: 0;
      list-style: none;
      font-size: 13px;
    }}
    .legend li,
    .resources li,
    .log li {{
      padding: 7px 0;
      border-top: 1px solid #edf0f3;
    }}
    .swatch {{
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      margin-right: 8px;
      vertical-align: middle;
    }}
    .log li.active {{
      color: var(--ink);
      font-weight: 700;
    }}
    @media (max-width: 880px) {{
      header {{
        align-items: flex-start;
        flex-direction: column;
      }}
      main {{
        grid-template-columns: 1fr;
      }}
      aside {{
        max-height: none;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Rede P2P - {html_escape(result.algorithm)}</h1>
    <div class="status">{status}</div>
  </header>
  <main>
    <section class="graph-panel" aria-label="Representação gráfica da rede P2P">
      <svg id="network" viewBox="0 0 960 620" role="img" aria-label="Topologia da rede P2P"></svg>
      <div class="controls">
        <button type="button" id="play">Play</button>
        <button type="button" id="step">Step</button>
        <button type="button" id="reset">Reset</button>
        <span class="step-label" id="stepLabel">Step 0 / {len(result.events)}</span>
      </div>
    </section>
    <aside>
      <h2>Busca</h2>
      <dl>
        <dt>Nó inicial</dt><dd>{html_escape(result.start_node)}</dd>
        <dt>Recurso</dt><dd>{html_escape(result.resource_id)}</dd>
        <dt>TTL</dt><dd>{result.ttl}</dd>
        <dt>Mensagens</dt><dd>{result.messages}</dd>
        <dt>Nós envolvidos</dt><dd>{result.nodes_involved}</dd>
        <dt>Detentor</dt><dd>{html_escape(holder)}</dd>
        <dt>Encontrado via</dt><dd>{html_escape(found_via)}</dd>
        <dt>Caminho</dt><dd>{html_escape(" -> ".join(result.path))}</dd>
      </dl>
      <h2>Legenda</h2>
      <ul class="legend">
        <li><span class="swatch" style="background: var(--start)"></span>nó inicial</li>
        <li><span class="swatch" style="background: var(--found)"></span>nó com resposta</li>
        <li><span class="swatch" style="background: var(--request)"></span>requisição</li>
        <li><span class="swatch" style="background: var(--reply)"></span>resposta</li>
      </ul>
      <h2 style="margin-top: 18px;">Recursos</h2>
      <ul class="resources" id="resources"></ul>
      <h2 style="margin-top: 18px;">Mensagens</h2>
      <ul class="log" id="log"></ul>
    </aside>
  </main>
  <script>
    const data = {data_json};
    const svg = document.getElementById("network");
    const log = document.getElementById("log");
    const resources = document.getElementById("resources");
    const stepLabel = document.getElementById("stepLabel");
    const playButton = document.getElementById("play");
    const ns = "http://www.w3.org/2000/svg";
    const nodeById = new Map(data.nodes.map((node) => [node.id, node]));
    const nodeElements = new Map();
    const edgeElements = new Map();
    let currentStep = -1;
    let timer = null;

    function makeSvg(tag, attrs = {{}}) {{
      const el = document.createElementNS(ns, tag);
      for (const [key, value] of Object.entries(attrs)) {{
        el.setAttribute(key, value);
      }}
      return el;
    }}

    function edgeKey(a, b) {{
      return [a, b].sort().join("--");
    }}

    function render() {{
      const edgeLayer = makeSvg("g");
      const messageLayer = makeSvg("g");
      const nodeLayer = makeSvg("g");
      svg.append(edgeLayer, messageLayer, nodeLayer);

      for (const edge of data.edges) {{
        const source = nodeById.get(edge.source);
        const target = nodeById.get(edge.target);
        const line = makeSvg("line", {{
          class: "edge",
          x1: source.x,
          y1: source.y,
          x2: target.x,
          y2: target.y,
        }});
        edgeLayer.append(line);
        edgeElements.set(edgeKey(edge.source, edge.target), line);
      }}

      for (const node of data.nodes) {{
        const group = makeSvg("g", {{ class: "node", transform: `translate(${{node.x}}, ${{node.y}})` }});
        group.dataset.node = node.id;
        const title = makeSvg("title");
        title.textContent = `${{node.id}}: ${{node.resources.join(", ")}}`;
        group.append(title);
        group.append(makeSvg("circle", {{ r: 28 }}));
        const label = makeSvg("text");
        label.textContent = node.id;
        group.append(label);
        nodeLayer.append(group);
        nodeElements.set(node.id, group);
      }}

      for (const node of data.nodes) {{
        const item = document.createElement("li");
        item.textContent = `${{node.id}}: ${{node.resources.join(", ")}}`;
        resources.append(item);
      }}

      for (const event of data.events) {{
        const item = document.createElement("li");
        const ttl = event.ttl === null ? "" : `, ttl=${{event.ttl}}`;
        item.textContent = `${{event.step}}. ${{event.kind}}: ${{event.source}} -> ${{event.target}}${{ttl}}`;
        log.append(item);
      }}

      reset();
    }}

    function clearActive() {{
      for (const edge of edgeElements.values()) {{
        edge.classList.remove("active-request", "active-reply");
      }}
      for (const node of nodeElements.values()) {{
        node.classList.remove("active");
      }}
    }}

    function markBaseNodes() {{
      const start = nodeElements.get(data.result.start_node);
      if (start) start.classList.add("start", "involved");
      if (data.result.informed_by) {{
        const informedBy = nodeElements.get(data.result.informed_by);
        if (informedBy) informedBy.classList.add("holder");
      }}
      if (data.result.holder) {{
        const holder = nodeElements.get(data.result.holder);
        if (holder) holder.classList.add("holder");
      }}
    }}

    function setStepLabel() {{
      stepLabel.textContent = `Step ${{Math.max(0, currentStep + 1)}} / ${{data.events.length}}`;
    }}

    function reset() {{
      stop();
      currentStep = -1;
      clearActive();
      for (const node of nodeElements.values()) {{
        node.classList.remove("involved", "start", "holder");
      }}
      for (const item of log.children) {{
        item.classList.remove("active");
      }}
      svg.querySelectorAll(".message").forEach((message) => message.remove());
      markBaseNodes();
      setStepLabel();
    }}

    function animateEvent(event) {{
      clearActive();
      const source = nodeById.get(event.source);
      const target = nodeById.get(event.target);
      const edge = edgeElements.get(edgeKey(event.source, event.target));
      const sourceNode = nodeElements.get(event.source);
      const targetNode = nodeElements.get(event.target);
      if (edge) edge.classList.add(event.kind === "reply" ? "active-reply" : "active-request");
      if (sourceNode) sourceNode.classList.add("active", "involved");
      if (targetNode) targetNode.classList.add("active", "involved");

      const message = makeSvg("circle", {{
        class: `message ${{event.kind}}`,
        r: 7,
        cx: source.x,
        cy: source.y,
      }});
      const moveX = makeSvg("animate", {{
        attributeName: "cx",
        from: source.x,
        to: target.x,
        dur: "0.52s",
        fill: "freeze",
      }});
      const moveY = makeSvg("animate", {{
        attributeName: "cy",
        from: source.y,
        to: target.y,
        dur: "0.52s",
        fill: "freeze",
      }});
      message.append(moveX, moveY);
      svg.append(message);
      moveX.beginElement();
      moveY.beginElement();
      setTimeout(() => message.remove(), 680);

      for (const item of log.children) item.classList.remove("active");
      if (log.children[event.step - 1]) log.children[event.step - 1].classList.add("active");
      setStepLabel();
    }}

    function step() {{
      if (currentStep + 1 >= data.events.length) {{
        stop();
        return;
      }}
      currentStep += 1;
      animateEvent(data.events[currentStep]);
    }}

    function play() {{
      if (timer) {{
        stop();
        return;
      }}
      if (currentStep + 1 >= data.events.length) reset();
      playButton.textContent = "Pause";
      step();
      timer = setInterval(step, 820);
    }}

    function stop() {{
      if (timer) {{
        clearInterval(timer);
        timer = null;
      }}
      playButton.textContent = "Play";
    }}

    document.getElementById("play").addEventListener("click", play);
    document.getElementById("step").addEventListener("click", step);
    document.getElementById("reset").addEventListener("click", reset);
    render();
  </script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulador de busca em redes P2P não estruturadas")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="valida o arquivo de configuração")
    validate_parser.add_argument("config", type=Path)

    search_parser = subparsers.add_parser("search", help="executa uma busca")
    search_parser.add_argument("config", type=Path)
    search_parser.add_argument("--node", "--node-id", dest="node_id", required=True)
    search_parser.add_argument("--resource", "--resource-id", dest="resource_id", required=True)
    search_parser.add_argument("--ttl", type=int, required=True)
    search_parser.add_argument("--algo", choices=ALGORITHM_CHOICES, required=True)
    search_parser.add_argument("--seed", type=int, default=None)
    search_parser.add_argument("--json", action="store_true", dest="json_output")

    compare_parser = subparsers.add_parser("compare", help="compara os quatro algoritmos para a mesma busca")
    compare_parser.add_argument("config", type=Path)
    compare_parser.add_argument("--node", "--node-id", dest="node_id", required=True)
    compare_parser.add_argument("--resource", "--resource-id", dest="resource_id", required=True)
    compare_parser.add_argument("--ttl", type=int, required=True)
    compare_parser.add_argument("--seed", type=int, default=None)
    compare_parser.add_argument("--json", action="store_true", dest="json_output")

    batch_parser = subparsers.add_parser("batch", help="executa uma lista de buscas em JSON")
    batch_parser.add_argument("config", type=Path)
    batch_parser.add_argument("queries", type=Path)
    batch_parser.add_argument("--seed", type=int, default=None)
    batch_parser.add_argument("--csv", type=Path, default=None)
    batch_parser.add_argument("--json", action="store_true", dest="json_output")

    dot_parser = subparsers.add_parser("dot", help="imprime a rede em formato Graphviz DOT")
    dot_parser.add_argument("config", type=Path)

    visualize_parser = subparsers.add_parser("visualize", help="gera HTML com grafo e animação da busca")
    visualize_parser.add_argument("config", type=Path)
    visualize_parser.add_argument("--node", "--node-id", dest="node_id", required=True)
    visualize_parser.add_argument("--resource", "--resource-id", dest="resource_id", required=True)
    visualize_parser.add_argument("--ttl", type=int, required=True)
    visualize_parser.add_argument("--algo", choices=ALGORITHM_CHOICES, required=True)
    visualize_parser.add_argument("--seed", type=int, default=None)
    visualize_parser.add_argument("--output", type=Path, default=Path("visualization.html"))

    return parser


def command_validate(args: argparse.Namespace) -> int:
    network = P2PNetwork.from_file(args.config)
    print("Configuração válida")
    print(f"nodes: {len(network.nodes)}")
    print(f"edges: {len(network.edges)}")
    print(f"resource_types: {len(network.resource_locations)}")
    return 0


def command_search(args: argparse.Namespace) -> int:
    network = P2PNetwork.from_file(args.config)
    result = network.search(args.node_id, args.resource_id, args.ttl, args.algo, seed=args.seed)
    if args.json_output:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(format_result(result))
    return 0


def command_compare(args: argparse.Namespace) -> int:
    results = []
    for algorithm in ALGORITHM_ORDER:
        network = P2PNetwork.from_file(args.config)
        results.append(network.search(args.node_id, args.resource_id, args.ttl, algorithm, seed=args.seed))
    if args.json_output:
        print(json.dumps([result.as_dict() for result in results], ensure_ascii=False, indent=2))
    else:
        print_table(results)
    return 0


def command_batch(args: argparse.Namespace) -> int:
    network = P2PNetwork.from_file(args.config)
    queries = load_queries(args.queries)
    results = []
    for index, query in enumerate(queries):
        seed = None if args.seed is None else args.seed + index
        result = network.search(
            query.get("node_id") or query.get("node"),
            query.get("resource_id") or query.get("resource"),
            int(query["ttl"]),
            query["algo"],
            seed=seed,
        )
        results.append(result)

    if args.csv:
        write_csv(args.csv, results)

    if args.json_output:
        print(json.dumps([result.as_dict() for result in results], ensure_ascii=False, indent=2))
    else:
        print_table(results)
        if args.csv:
            print(f"\nCSV gravado em: {args.csv}")
    return 0


def command_dot(args: argparse.Namespace) -> int:
    network = P2PNetwork.from_file(args.config)
    print(network.to_dot())
    return 0


def command_visualize(args: argparse.Namespace) -> int:
    network = P2PNetwork.from_file(args.config)
    result = network.search(args.node_id, args.resource_id, args.ttl, args.algo, seed=args.seed)
    html = build_visualization_html(network, result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(format_result(result))
    print(f"\nVisualização gravada em: {args.output.resolve()}")
    return 0


def load_queries(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    queries = data.get("queries", data) if isinstance(data, dict) else data
    if not isinstance(queries, list):
        raise ConfigError("Arquivo de consultas deve conter uma lista JSON")
    for index, query in enumerate(queries, start=1):
        if not isinstance(query, dict):
            raise ConfigError(f"Consulta {index} deve ser um objeto")
        missing = [key for key in ("ttl", "algo") if key not in query]
        if not (query.get("node_id") or query.get("node")):
            missing.append("node_id")
        if not (query.get("resource_id") or query.get("resource")):
            missing.append("resource_id")
        if missing:
            raise ConfigError(f"Consulta {index} sem campos: {', '.join(missing)}")
    return queries


def write_csv(path: Path, results: Sequence[SearchResult]) -> None:
    fieldnames = list(results[0].as_dict().keys()) if results else []
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result.as_dict())


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    commands = {
        "validate": command_validate,
        "search": command_search,
        "compare": command_compare,
        "batch": command_batch,
        "dot": command_dot,
        "visualize": command_visualize,
    }
    try:
        return commands[args.command](args)
    except (ConfigError, SearchError, KeyError, json.JSONDecodeError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
