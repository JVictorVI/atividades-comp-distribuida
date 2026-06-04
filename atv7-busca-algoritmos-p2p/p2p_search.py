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

COMMAND_NAMES = {"validate", "search", "compare", "batch", "dot", "visualize"}

# Altere este objeto para montar a mensagem de busca que será executada quando
# você rodar apenas: python .\p2p_search.py
BUSCA = {
    "config": "examples/complex.yaml",
    "node_id": "n2",
    "resource_id": "r13",
    "ttl": 5,
    "algo": "flooding",
    "seed": None,
    "ignore_cache": False,
    "trace": True,
    "json": False,
    "visualize": "visualization.html",
}


class ConfigError(ValueError):
    """Erro encontrado no arquivo de configuração da rede."""


class SearchError(ValueError):
    """Erro encontrado nos parâmetros de uma operação de busca."""


@dataclass
class MessageEvent:
    step: int
    search_id: str
    round: Optional[int]
    kind: str
    source: str
    target: str
    resource_id: str
    ttl: Optional[int]

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResult:
    search_id: str
    algorithm: str
    start_node: str
    resource_id: str
    ttl: int
    ignore_cache: bool
    found: bool
    holder: Optional[str]
    informed_by: Optional[str]
    found_via: Optional[str]
    messages: int
    nodes_involved: int
    path: List[str]
    events: List[MessageEvent] = field(default_factory=list)
    cache_snapshot: Dict[str, Dict[str, str]] = field(default_factory=dict)

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

    data: Dict[str, Any] = {"resources": {}, "edges": [], "caches": {}}
    section: Optional[str] = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        if line in {"resources:", "edges:", "caches:"}:
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

        if section == "caches":
            if ":" not in line:
                raise ConfigError(f"Linha {line_number}: cache inválido: {raw_line!r}")
            node, values = line.split(":", 1)
            data["caches"][node.strip()] = parse_list(values)
            continue

        if ":" not in line:
            raise ConfigError(f"Linha {line_number}: entrada inválida: {raw_line!r}")
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
        self.configured_caches = self._normalize_caches(config.get("caches", {}))
        self._validate()
        self._search_sequence = 0
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

    def _normalize_caches(self, raw_caches: Any) -> Dict[str, Dict[str, str]]:
        caches: Dict[str, Dict[str, str]] = {node: {} for node in self.nodes}
        if raw_caches in (None, ""):
            return caches
        if not isinstance(raw_caches, dict):
            raise ConfigError("caches deve ser um mapa nó -> recursos conhecidos")

        for node, raw_entries in raw_caches.items():
            node = clean_token(node)
            if node not in self.node_set:
                raise ConfigError(f"caches contém nó desconhecido: {node}")

            parsed_entries: List[Tuple[str, str]] = []
            if isinstance(raw_entries, dict):
                parsed_entries = [
                    (clean_token(resource), clean_token(holder))
                    for resource, holder in raw_entries.items()
                ]
            else:
                for entry in parse_list(raw_entries):
                    parsed_entries.append(self._parse_cache_entry(entry))

            for resource, holder in parsed_entries:
                if not resource:
                    raise ConfigError(f"Cache de {node} contém recurso vazio")
                if resource not in self.resource_locations:
                    raise ConfigError(f"Cache de {node} referencia recurso desconhecido: {resource}")
                if holder not in self.node_set:
                    raise ConfigError(f"Cache de {node} referencia nó desconhecido: {holder}")
                if holder not in self.resource_locations[resource]:
                    raise ConfigError(
                        f"Cache de {node} aponta {resource} para {holder}, "
                        "mas esse nó não possui o recurso"
                    )
                caches[node][resource] = holder

        return caches

    @staticmethod
    def _parse_cache_entry(entry: Any) -> Tuple[str, str]:
        text = clean_token(entry)
        for separator in ("->", "=", ":"):
            if separator in text:
                resource, holder = text.split(separator, 1)
                return clean_token(resource), clean_token(holder)
        raise ConfigError(f"Entrada de cache inválida: {entry!r}. Use recurso=nó")

    def _validate(self) -> None:
        nodes_without_resources = [node for node, values in self.resources.items() if not values]
        if nodes_without_resources:
            raise ConfigError("Nós sem recursos: " + ", ".join(nodes_without_resources))

        replicated_resources = [
            (resource, sorted(nodes))
            for resource, nodes in self.resource_locations.items()
            if len(nodes) > 1
        ]
        if replicated_resources:
            details = ", ".join(
                f"{resource} em {', '.join(nodes)}" for resource, nodes in replicated_resources
            )
            raise ConfigError("Recursos replicados não são permitidos: " + details)

        nodes_without_neighbors = [
            node for node, neighbors in self.adjacency.items() if not neighbors
        ]
        if self.num_nodes > 1 and nodes_without_neighbors:
            raise ConfigError("Nós sem vizinhos: " + ", ".join(nodes_without_neighbors))

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
        for node, entries in self.configured_caches.items():
            self.caches[node].update(entries)

    def search(
        self,
        node_id: str,
        resource_id: str,
        ttl: int,
        algorithm: str,
        seed: Optional[int] = None,
        ignore_cache: bool = False,
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

        self._search_sequence += 1
        search_id = f"s{self._search_sequence}"
        cache_snapshot = self._snapshot_caches()
        if algorithm in {"flooding", "informed_flooding"}:
            return self._flooding(
                node_id, resource_id, ttl, algorithm, search_id, ignore_cache, cache_snapshot
            )

        rng = random.Random(seed)
        return self._random_walk(
            node_id, resource_id, ttl, algorithm, rng, search_id, ignore_cache, cache_snapshot
        )

    def _flooding(
        self,
        start: str,
        resource_id: str,
        ttl: int,
        algorithm: str,
        search_id: str,
        ignore_cache: bool,
        cache_snapshot: Dict[str, Dict[str, str]],
    ) -> SearchResult:
        use_cache = algorithm == "informed_flooding" and not ignore_cache
        holder, found_via = self._lookup(start, resource_id, False)
        involved = {start}
        messages = 0
        events: List[MessageEvent] = []
        if holder is not None:
            return self._success(
                search_id,
                algorithm,
                start,
                resource_id,
                ttl,
                ignore_cache,
                holder,
                start,
                found_via,
                messages,
                involved,
                [start],
                events,
                cache_snapshot,
            )

        processed = {start}
        frontier: List[Tuple[str, int, List[str]]] = [(start, ttl, [start])]
        first_success: Optional[Tuple[str, str, Optional[str], List[str]]] = None
        reply_sent = False
        round_number = 0

        while frontier:
            round_number += 1
            next_frontier: Dict[str, Tuple[str, int, List[str]]] = {}
            reply_node: Optional[str] = None

            for current, remaining_ttl, path in frontier:
                if remaining_ttl <= 0:
                    continue

                for neighbor in sorted(self.adjacency[current]):
                    if neighbor in path:
                        continue

                    next_ttl = remaining_ttl - 1
                    next_path = path + [neighbor]
                    involved.add(neighbor)
                    messages += 1
                    self._add_event(
                        events,
                        search_id,
                        round_number,
                        "request",
                        current,
                        neighbor,
                        resource_id,
                        next_ttl,
                    )

                    if neighbor in processed or neighbor in next_frontier:
                        continue

                    processed.add(neighbor)
                    holder, found_via = self._lookup(neighbor, resource_id, use_cache)
                    if holder is not None:
                        if first_success is None:
                            first_success = (holder, neighbor, found_via, next_path)
                            reply_node = neighbor
                        continue

                    if next_ttl > 0:
                        next_frontier[neighbor] = (neighbor, next_ttl, next_path)

            if reply_node is not None and not reply_sent:
                cache_holder = first_success[0] if first_success is not None else reply_node
                found_via = first_success[2] if first_success is not None else None
                messages = self._add_direct_reply_if_needed(
                    events,
                    search_id,
                    round_number,
                    start,
                    reply_node,
                    resource_id,
                    messages,
                )
                if found_via == "cache":
                    involved.add(cache_holder)
                    messages = self._add_direct_connection_if_needed(
                        events,
                        search_id,
                        round_number,
                        start,
                        cache_holder,
                        resource_id,
                        messages,
                    )
                reply_sent = True

            frontier = list(next_frontier.values())

        if first_success is not None:
            holder, informed_by, found_via, path = first_success
            if found_via == "cache" and holder != informed_by:
                path = path + [holder]
            return self._success(
                search_id,
                algorithm,
                start,
                resource_id,
                ttl,
                ignore_cache,
                holder,
                informed_by,
                found_via,
                messages,
                involved,
                path,
                events,
                cache_snapshot,
            )

        return self._failure(
            search_id,
            algorithm,
            start,
            resource_id,
            ttl,
            ignore_cache,
            messages,
            involved,
            [start],
            events,
            cache_snapshot,
        )

    def _random_walk(
        self,
        start: str,
        resource_id: str,
        ttl: int,
        algorithm: str,
        rng: random.Random,
        search_id: str,
        ignore_cache: bool,
        cache_snapshot: Dict[str, Dict[str, str]],
    ) -> SearchResult:
        use_cache = algorithm == "informed_random_walk" and not ignore_cache
        current = start
        path = [start]
        involved = {start}
        visited = {start}
        messages = 0
        remaining_ttl = ttl
        events: List[MessageEvent] = []

        while True:
            holder, found_via = self._lookup(current, resource_id, use_cache and current != start)
            if holder is not None:
                round_number = max(0, len(path) - 1)
                messages = self._add_direct_reply_if_needed(
                    events, search_id, round_number, start, current, resource_id, messages
                )
                if found_via == "cache":
                    involved.add(holder)
                    messages = self._add_direct_connection_if_needed(
                        events, search_id, round_number, start, holder, resource_id, messages
                    )
                result_path = path + [holder] if found_via == "cache" and holder != current else path
                return self._success(
                    search_id,
                    algorithm,
                    start,
                    resource_id,
                    ttl,
                    ignore_cache,
                    holder,
                    current,
                    found_via,
                    messages,
                    involved,
                    result_path,
                    events,
                    cache_snapshot,
                )

            if remaining_ttl == 0:
                return self._failure(
                    search_id,
                    algorithm,
                    start,
                    resource_id,
                    ttl,
                    ignore_cache,
                    messages,
                    involved,
                    path,
                    events,
                    cache_snapshot,
                )

            neighbors = [neighbor for neighbor in sorted(self.adjacency[current]) if neighbor not in visited]
            if not neighbors:
                return self._failure(
                    search_id,
                    algorithm,
                    start,
                    resource_id,
                    ttl,
                    ignore_cache,
                    messages,
                    involved,
                    path,
                    events,
                    cache_snapshot,
                )

            previous = current
            current = rng.choice(neighbors)
            path.append(current)
            involved.add(current)
            visited.add(current)
            messages += 1
            round_number = len(path) - 1
            self._add_event(
                events,
                search_id,
                round_number,
                "request",
                previous,
                current,
                resource_id,
                remaining_ttl - 1,
            )
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
        search_id: str,
        round_number: Optional[int],
        kind: str,
        source: str,
        target: str,
        resource_id: str,
        ttl: Optional[int],
    ) -> None:
        events.append(
            MessageEvent(
                step=len(events) + 1,
                search_id=search_id,
                round=round_number,
                kind=kind,
                source=source,
                target=target,
                resource_id=resource_id,
                ttl=ttl,
            )
        )

    def _add_direct_reply_if_needed(
        self,
        events: List[MessageEvent],
        search_id: str,
        round_number: Optional[int],
        start: str,
        informed_by: str,
        resource_id: str,
        messages: int,
    ) -> int:
        if start == informed_by:
            return messages
        self._add_event(events, search_id, round_number, "reply", informed_by, start, resource_id, None)
        return messages + 1

    def _add_direct_connection_if_needed(
        self,
        events: List[MessageEvent],
        search_id: str,
        round_number: Optional[int],
        start: str,
        holder: str,
        resource_id: str,
        messages: int,
    ) -> int:
        if start == holder:
            return messages
        self._add_event(events, search_id, round_number, "direct", start, holder, resource_id, None)
        return messages + 1

    def _snapshot_caches(self) -> Dict[str, Dict[str, str]]:
        return {node: dict(entries) for node, entries in self.caches.items()}

    def _success(
        self,
        search_id: str,
        algorithm: str,
        start: str,
        resource_id: str,
        ttl: int,
        ignore_cache: bool,
        holder: str,
        informed_by: str,
        found_via: Optional[str],
        messages: int,
        involved: Set[str],
        path: List[str],
        events: List[MessageEvent],
        cache_snapshot: Dict[str, Dict[str, str]],
    ) -> SearchResult:
        self._learn([start], resource_id, holder)
        return SearchResult(
            search_id=search_id,
            algorithm=algorithm,
            start_node=start,
            resource_id=resource_id,
            ttl=ttl,
            ignore_cache=ignore_cache,
            found=True,
            holder=holder,
            informed_by=informed_by,
            found_via=found_via,
            messages=messages,
            nodes_involved=len(involved),
            path=path,
            events=events,
            cache_snapshot=cache_snapshot,
        )

    @staticmethod
    def _failure(
        search_id: str,
        algorithm: str,
        start: str,
        resource_id: str,
        ttl: int,
        ignore_cache: bool,
        messages: int,
        involved: Set[str],
        path: List[str],
        events: List[MessageEvent],
        cache_snapshot: Dict[str, Dict[str, str]],
    ) -> SearchResult:
        return SearchResult(
            search_id=search_id,
            algorithm=algorithm,
            start_node=start,
            resource_id=resource_id,
            ttl=ttl,
            ignore_cache=ignore_cache,
            found=False,
            holder=None,
            informed_by=None,
            found_via=None,
            messages=messages,
            nodes_involved=len(involved),
            path=path,
            events=events,
            cache_snapshot=cache_snapshot,
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
        f"search_id: {result.search_id}",
        f"status: {'ENCONTRADO' if result.found else 'NÃO ENCONTRADO'}",
        f"algorithm: {result.algorithm}",
        f"start_node: {result.start_node}",
        f"resource_id: {result.resource_id}",
        f"ttl: {result.ttl}",
        f"ignore_cache: {'sim' if result.ignore_cache else 'não'}",
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


def format_trace(result: SearchResult) -> str:
    if not result.events:
        return "trace: nenhuma mensagem trocada"

    lines = ["trace:"]
    for event in result.events:
        ttl = "-" if event.ttl is None else str(event.ttl)
        round_label = "-" if event.round is None else str(event.round)
        lines.append(
            "  "
            f"{event.step}. search_id={event.search_id} "
            f"round={round_label} "
            f"{event.kind} {event.source} -> {event.target} "
            f"resource={event.resource_id} ttl={ttl}"
        )
    return "\n".join(lines)


def print_table(results: Sequence[SearchResult]) -> None:
    rows = [
        [
            result.algorithm,
            "sim" if result.found else "não",
            result.holder or "-",
            str(result.messages),
            str(result.nodes_involved),
            " -> ".join(result.path),
        ]
        for result in results
    ]
    headers = ["algoritmo", "encontrado", "detentor", "mensagens", "nós", "caminho"]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows)) if rows else len(header)
        for index, header in enumerate(headers)
    ]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def summarize_results(results: Sequence[SearchResult]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[SearchResult]] = defaultdict(list)
    for result in results:
        grouped[result.algorithm].append(result)

    summary = []
    for algorithm in ALGORITHM_ORDER:
        items = grouped.get(algorithm, [])
        if not items:
            continue
        total = len(items)
        found = sum(1 for item in items if item.found)
        total_messages = sum(item.messages for item in items)
        total_nodes = sum(item.nodes_involved for item in items)
        summary.append(
            {
                "algorithm": algorithm,
                "runs": total,
                "found": found,
                "success_rate": found / total,
                "avg_messages": total_messages / total,
                "avg_nodes": total_nodes / total,
                "min_messages": min(item.messages for item in items),
                "max_messages": max(item.messages for item in items),
            }
        )
    return summary


def print_statistics(results: Sequence[SearchResult]) -> None:
    summary = summarize_results(results)
    if not summary:
        return

    rows = [
        [
            item["algorithm"],
            str(item["runs"]),
            str(item["found"]),
            f"{item['success_rate']:.2%}",
            f"{item['avg_messages']:.2f}",
            f"{item['avg_nodes']:.2f}",
            str(item["min_messages"]),
            str(item["max_messages"]),
        ]
        for item in summary
    ]
    headers = ["algoritmo", "execuções", "encontrados", "sucesso", "média_msg", "média_nós", "min_msg", "max_msg"]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    print("\nestatísticas")
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


def build_visualization_html(network: P2PNetwork, result: SearchResult) -> str:
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
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    title = html_escape(f"P2P Search - {result.algorithm}")
    status_text = "ENCONTRADO" if result.found else "NÃO ENCONTRADO"
    status_class = "found" if result.found else "not-found"
    holder = resource_holder or result.holder or "-"
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
      --cache: #b7791f;
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
    }}
    .status.pending {{
      border-color: #b9c4ce;
      background: rgba(247, 250, 252, 0.96);
    }}
    .status.found {{
      border-color: var(--found);
      background: #e8fff5;
      color: #0f7a54;
    }}
    .status.not-found {{
      border-color: #bd3131;
      background: #fff0f0;
      color: #9b1c1c;
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
      position: relative;
      overflow: hidden;
    }}
    svg {{
      display: block;
      width: 100%;
      height: min(76vh, 760px);
      min-height: 500px;
      background: #fbfcfd;
    }}
    .graph-edge {{
      stroke: var(--line);
      stroke-width: 2;
    }}
    .graph-edge.base {{
      stroke: #b7c4cf;
      stroke-width: 2;
    }}
    .graph-edge.event-edge {{
      stroke: #9ba8b4;
      stroke-dasharray: 6 5;
      opacity: 0;
    }}
    .graph-edge.event-edge.reply {{
      stroke: var(--reply);
      stroke-dasharray: 7 5;
    }}
    .graph-edge.event-edge.direct {{
      stroke: var(--cache);
      stroke-dasharray: 4 4;
    }}
    .graph-edge.active-request {{
      stroke: var(--request);
      stroke-width: 4;
      stroke-dasharray: none;
      opacity: 1;
    }}
    .graph-edge.active-reply {{
      stroke: var(--reply);
      stroke-width: 4;
      opacity: 1;
    }}
    .graph-edge.active-direct {{
      stroke: var(--cache);
      stroke-width: 4;
      opacity: 1;
    }}
    .node circle {{
      fill: var(--node);
      stroke: var(--node-border);
      stroke-width: 2.5;
    }}
    .node .cache-ring {{
      fill: none;
      stroke: var(--cache);
      stroke-width: 3;
      stroke-dasharray: 5 4;
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
    .node.cache-used .cache-ring {{
      stroke-width: 5;
      stroke-dasharray: none;
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
    .message.direct {{
      fill: var(--cache);
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
    button.active {{
      border-color: #456179;
      background: #e8eef5;
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
    .caches,
    .log {{
      margin: 0;
      padding: 0;
      list-style: none;
      font-size: 13px;
    }}
    .cache-panel {{
      margin: 0 0 18px;
      padding: 12px;
      background: #fff8df;
      border: 1px solid #ecd39a;
      border-radius: 8px;
    }}
    .cache-panel.hidden {{
      display: none;
    }}
    .cache-panel h2 {{
      color: #744c0f;
    }}
    .message-panel {{
      margin: -16px -16px 18px;
      padding: 14px 16px 16px;
      background: #fff8ed;
      border-bottom: 1px solid #efd7bd;
      box-shadow: inset 4px 0 0 #f0a85d;
    }}
    .message-panel.playing {{
      background: #fff3e3;
      box-shadow: inset 4px 0 0 var(--request);
    }}
    .message-panel h2 {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }}
    .message-panel h2::before {{
      content: "";
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--request);
    }}
    .message-panel .log {{
      max-height: 232px;
      overflow: auto;
    }}
    .legend li,
    .resources li,
    .caches li,
    .log li {{
      padding: 7px 0;
      border-top: 1px solid #edf0f3;
    }}
    .caches li {{
      border-top-color: #ecd39a;
      overflow-wrap: anywhere;
    }}
    .caches li.used {{
      color: #6f3f00;
      font-weight: 700;
    }}
    .message-panel .log li {{
      padding: 8px 10px;
      border-top-color: #f1dcc7;
      border-left: 3px solid transparent;
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
    .message-panel .log li.active {{
      background: #fff0df;
      border-left-color: var(--request);
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
      <section class="cache-panel{' ' if uses_cache else ' hidden'}" id="cachePanel" aria-label="Caches dos nós">
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
        <dt>Nó com recurso</dt><dd>{html_escape(holder)}</dd>
        <dt>Encontrado via</dt><dd>{html_escape(found_via)}</dd>
        <dt>Caminho</dt><dd>{html_escape(" -> ".join(result.path))}</dd>
      </dl>
      <h2>Legenda</h2>
      <ul class="legend">
        <li><span class="swatch" style="background: var(--start)"></span>nó inicial</li>
        <li><span class="swatch" style="background: var(--found)"></span>nó com recurso</li>
        {('<li><span class="swatch" style="background: var(--cache)"></span>nó com cache do recurso</li>' if uses_cache else '')}
        <li><span class="swatch" style="background: var(--request)"></span>requisição</li>
        <li><span class="swatch" style="background: var(--reply)"></span>resposta</li>
      </ul>
      <h2 style="margin-top: 18px;">Recursos</h2>
      <ul class="resources" id="resources"></ul>
    </aside>
  </main>
  <script>
    const data = {data_json};
    const svg = document.getElementById("network");
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

    function makeSvg(tag, attrs = {{}}) {{
      const el = document.createElementNS(ns, tag);
      for (const [key, value] of Object.entries(attrs)) {{
        el.setAttribute(key, value);
      }}
      return el;
    }}

    function eventPhase(event) {{
      if (event.kind === "reply") return 1;
      if (event.kind === "direct") return 2;
      return 0;
    }}

    function buildFrames(events) {{
      const frames = [];
      let current = null;
      for (const event of events) {{
        const round = event.round === null ? -1 : event.round;
        const phase = eventPhase(event);
        const key = `${{round}}:${{phase}}`;
        if (!current || current.key !== key) {{
          current = {{ key, round, phase, events: [] }};
          frames.push(current);
        }}
        current.events.push(event);
      }}
      return frames;
    }}

    function buildTopologyGraph() {{
      const eventEdges = data.events.map((event) => ({{
        source: event.source,
        target: event.target,
        eventStep: event.step,
        kind: event.kind,
      }}));

      return {{
        nodes: data.nodes,
        baseEdges: data.edges,
        eventEdges,
        width: data.layout.width,
        height: data.layout.height,
      }};
    }}

    function clearSvg() {{
      svg.innerHTML = "";
      visualNodes.clear();
      nodeElements.clear();
      edgeElements.clear();
      eventEndpoints.clear();
    }}

    function renderGraph() {{
      clearSvg();
      const graph = buildTopologyGraph();
      svg.setAttribute("viewBox", `0 0 ${{graph.width}} ${{graph.height}}`);
      const baseEdgeLayer = makeSvg("g");
      const eventEdgeLayer = makeSvg("g");
      const nodeLayer = makeSvg("g");
      svg.append(baseEdgeLayer, eventEdgeLayer, nodeLayer);

      const graphNodeById = new Map(graph.nodes.map((node) => [node.id, node]));

      for (const edge of graph.baseEdges) {{
        const source = graphNodeById.get(edge.source);
        const target = graphNodeById.get(edge.target);
        if (!source || !target) continue;
        const line = makeSvg("line", {{
          class: "graph-edge base",
          x1: source.x,
          y1: source.y,
          x2: target.x,
          y2: target.y,
        }});
        baseEdgeLayer.append(line);
      }}

      for (const edge of graph.eventEdges) {{
        const source = graphNodeById.get(edge.source);
        const target = graphNodeById.get(edge.target);
        if (!source || !target) continue;
        const id = `event-${{edge.eventStep}}`;
        const line = makeSvg("line", {{
          class: `graph-edge event-edge ${{edge.kind}}`,
          x1: source.x,
          y1: source.y,
          x2: target.x,
          y2: target.y,
        }});
        eventEdgeLayer.append(line);
        edgeElements.set(id, line);
        eventEndpoints.set(edge.eventStep, {{
          source: edge.source,
          target: edge.target,
          edgeId: id,
        }});
      }}

      for (const node of graph.nodes) {{
        const classes = ["node"];
        if (data.uses_cache && node.cache_relevant) classes.push("cache");
        if (data.uses_cache && node.cache_used) classes.push("cache-used");
        const group = makeSvg("g", {{ class: classes.join(" "), transform: `translate(${{node.x}}, ${{node.y}})` }});
        group.dataset.node = node.id;
        const title = makeSvg("title");
        const searchedCache = (node.cache || []).find((entry) => entry.resource === data.result.resource_id);
        const cacheText = searchedCache
          ? ` · cache: ${{searchedCache.resource}} -> ${{searchedCache.holder}}`
          : "";
        title.textContent = `${{node.id}}: ${{(resourceByNode.get(node.id) || []).join(", ")}}${{cacheText}}`;
        group.append(title);
        if (data.uses_cache && node.cache_relevant) {{
          group.append(makeSvg("circle", {{ class: "cache-ring", r: 31 }}));
        }}
        group.append(makeSvg("circle", {{ r: 24 }}));
        const label = makeSvg("text");
        label.textContent = node.id;
        group.append(label);
        nodeLayer.append(group);
        nodeElements.set(node.id, group);
        visualNodes.set(node.id, node);
      }}
    }}

    function renderCacheList() {{
      if (!data.uses_cache) return;
      const relevantNodes = data.nodes.filter((node) => node.cache_relevant);
      if (relevantNodes.length === 0) {{
        const item = document.createElement("li");
        item.textContent = "Nenhum cache para este recurso.";
        caches.append(item);
        return;
      }}

      for (const node of relevantNodes) {{
        const entry = node.cache.find((cacheEntry) => cacheEntry.resource === data.result.resource_id);
        if (!entry) continue;
        const item = document.createElement("li");
        if (node.cache_used) item.classList.add("used");
        const origin = entry.local ? "local" : "aprendido";
        const used = node.cache_used ? " · usado nesta busca" : "";
        item.textContent = `${{node.id}}: ${{entry.resource}} -> ${{entry.holder}} (${{origin}})${{used}}`;
        caches.append(item);
      }}
    }}

    function renderStaticLists() {{
      renderCacheList();
      for (const node of data.nodes) {{
        const item = document.createElement("li");
        item.textContent = `${{node.id}}: ${{node.resources.join(", ")}}`;
        resources.append(item);
      }}
    }}

    function formatLogMessage(event) {{
      const ttl = event.ttl === null ? "" : `, ttl=${{event.ttl}}`;
      const round = event.round === null ? "-" : event.round;
      const kindLabel = event.kind === "direct" ? "conexão direta" : event.kind;
      return `${{event.step}}. round=${{round}} ${{kindLabel}}: ${{event.source}} -> ${{event.target}}${{ttl}}`;
    }}

    function appendFrameLog(frame) {{
      for (const item of log.children) item.classList.remove("active");
      for (const event of frame.events) {{
        const item = document.createElement("li");
        item.dataset.step = event.step;
        item.textContent = formatLogMessage(event);
        item.classList.add("active");
        log.append(item);
      }}
      log.scrollTop = log.scrollHeight;
    }}

    function renderView() {{
      renderGraph();
      markBaseNodes();
    }}

    function render() {{
      renderStaticLists();
      reset();
    }}

    function clearActive() {{
      for (const edge of edgeElements.values()) {{
        edge.classList.remove("active-request", "active-reply", "active-direct");
      }}
      for (const node of nodeElements.values()) {{
        node.classList.remove("active");
      }}
    }}

    function hideFinalStatus() {{
      statusLabel.textContent = "EXPLORANDO";
      statusLabel.classList.remove("found", "not-found");
      statusLabel.classList.add("pending");
      if (frames.length === 0) {{
        revealFinalStatus();
      }}
    }}

    function revealFinalStatus() {{
      statusLabel.textContent = statusLabel.dataset.finalStatus;
      statusLabel.classList.remove("pending", "found", "not-found");
      statusLabel.classList.add(statusLabel.dataset.finalClass);
    }}

    function markBaseNodes() {{
      for (const node of nodeElements.values()) {{
        const nodeId = node.dataset.node;
        if (nodeId === data.result.start_node) {{
          node.classList.add("start", "involved");
        }}
        if (data.result.informed_by && nodeId === data.result.informed_by) {{
          node.classList.add("holder");
        }}
        if (data.result.holder && nodeId === data.result.holder) {{
          node.classList.add("holder");
        }}
        if (data.resource_holder && nodeId === data.resource_holder) {{
          node.classList.add("holder");
        }}
      }}
    }}

    function setStepLabel() {{
      if (frames.length === 0 || currentFrame < 0) {{
        stepLabel.textContent = `Quadro 0 / ${{frames.length}}`;
        return;
      }}
      const frame = frames[currentFrame];
      const round = frame.round < 0 ? "-" : frame.round;
      const phase = frame.phase === 1 ? "resposta" : frame.phase === 2 ? "conexão direta" : "requisições";
      stepLabel.textContent = `Quadro ${{currentFrame + 1}} / ${{frames.length}} · rodada ${{round}} · ${{phase}}`;
    }}

    function reset() {{
      stop();
      currentFrame = -1;
      clearActive();
      for (const node of nodeElements.values()) {{
        node.classList.remove("involved", "start", "holder");
      }}
      log.innerHTML = "";
      messagePanel.classList.remove("playing");
      svg.querySelectorAll(".message").forEach((message) => message.remove());
      renderView();
      hideFinalStatus();
      setStepLabel();
    }}

    function animateSingleEvent(event) {{
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
    }}

    function animateFrame(frame) {{
      clearActive();
      messagePanel.classList.add("playing");
      svg.querySelectorAll(".message").forEach((message) => message.remove());
      for (const event of frame.events) {{
        animateSingleEvent(event);
      }}
      appendFrameLog(frame);
      setStepLabel();
    }}

    function step() {{
      if (currentFrame + 1 >= frames.length) {{
        revealFinalStatus();
        stop();
        return;
      }}
      currentFrame += 1;
      animateFrame(frames[currentFrame]);
      if (currentFrame + 1 >= frames.length) {{
        revealFinalStatus();
        stop();
      }}
    }}

    function play() {{
      if (timer) {{
        stop();
        return;
      }}
      if (currentFrame + 1 >= frames.length) reset();
      playButton.textContent = "Pausar";
      step();
      if (currentFrame + 1 < frames.length) {{
        timer = setInterval(step, 820);
      }} else {{
        playButton.textContent = "Reproduzir";
      }}
    }}

    function stop() {{
      if (timer) {{
        clearInterval(timer);
        timer = null;
      }}
      playButton.textContent = "Reproduzir";
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
    search_parser.add_argument("--ignore-cache", action="store_true", help="ignora caches locais nesta busca")
    search_parser.add_argument("--trace", action="store_true", help="imprime o rastro textual das mensagens")
    search_parser.add_argument("--json", action="store_true", dest="json_output")

    compare_parser = subparsers.add_parser("compare", help="compara os quatro algoritmos para a mesma busca")
    compare_parser.add_argument("config", type=Path)
    compare_parser.add_argument("--node", "--node-id", dest="node_id", required=True)
    compare_parser.add_argument("--resource", "--resource-id", dest="resource_id", required=True)
    compare_parser.add_argument("--ttl", type=int, required=True)
    compare_parser.add_argument("--seed", type=int, default=None)
    compare_parser.add_argument("--ignore-cache", action="store_true", help="ignora caches locais nas buscas informadas")
    compare_parser.add_argument("--json", action="store_true", dest="json_output")

    batch_parser = subparsers.add_parser("batch", help="executa uma lista de buscas em JSON")
    batch_parser.add_argument("config", type=Path)
    batch_parser.add_argument("queries", type=Path)
    batch_parser.add_argument("--seed", type=int, default=None)
    batch_parser.add_argument("--csv", type=Path, default=None)
    batch_parser.add_argument("--ignore-cache", action="store_true", help="ignora caches locais em todas as buscas")
    batch_parser.add_argument("--trace", action="store_true", help="imprime rastros textuais de todas as buscas")
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
    visualize_parser.add_argument("--ignore-cache", action="store_true", help="ignora caches locais nesta busca")
    visualize_parser.add_argument("--output", type=Path, default=Path("visualization.html"))

    return parser


def build_direct_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Executa uma busca P2P diretamente. Exemplo: "
            "python p2p_search.py examples/ring.json n1 r4 --ttl 3 --algo flooding"
        )
    )
    parser.add_argument("config", type=Path, help="arquivo de configuração da rede")
    parser.add_argument("node_id_arg", nargs="?", help="nó que inicia a busca")
    parser.add_argument("resource_id_arg", nargs="?", help="recurso procurado")
    parser.add_argument("--node", "--node-id", dest="node_id", help="nó que inicia a busca")
    parser.add_argument("--resource", "--resource-id", dest="resource_id", help="recurso procurado")
    parser.add_argument("--ttl", type=int, default=3, help="níveis de propagação da busca (padrão: 3)")
    parser.add_argument("--algo", choices=ALGORITHM_CHOICES, default="flooding", help="algoritmo de busca")
    parser.add_argument("--seed", type=int, default=None, help="semente para random_walk")
    parser.add_argument("--ignore-cache", action="store_true", help="ignora caches locais nesta busca")
    parser.add_argument("--trace", action="store_true", help="imprime o rastro textual das mensagens")
    parser.add_argument("--json", action="store_true", dest="json_output", help="imprime o resultado em JSON")
    parser.add_argument(
        "--visualize",
        nargs="?",
        const="visualization.html",
        default=None,
        help="gera HTML da animação; opcionalmente informe o caminho do arquivo",
    )
    return parser


def should_use_direct_parser(argv: Sequence[str]) -> bool:
    if not argv:
        return True
    first = argv[0]
    if first in {"-h", "--help"}:
        return True
    return first not in COMMAND_NAMES


def resolve_direct_message(args: argparse.Namespace, parser: argparse.ArgumentParser) -> Tuple[str, str]:
    node_id = args.node_id or args.node_id_arg
    resource_id = args.resource_id or args.resource_id_arg
    if not node_id:
        parser.error("informe o nó inicial por posição ou com --node")
    if not resource_id:
        parser.error("informe o recurso por posição ou com --resource")
    return node_id, resource_id


def command_direct(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    node_id, resource_id = resolve_direct_message(args, parser)
    network = P2PNetwork.from_file(args.config)
    result = network.search(
        node_id,
        resource_id,
        args.ttl,
        args.algo,
        seed=args.seed,
        ignore_cache=args.ignore_cache,
    )

    if args.visualize:
        output = Path(args.visualize)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(build_visualization_html(network, result), encoding="utf-8")

    if args.json_output:
        payload = result.as_dict(include_events=args.trace)
        if args.visualize:
            payload["visualization"] = str(Path(args.visualize).resolve())
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_result(result))
        if args.trace:
            print()
            print(format_trace(result))
        if args.visualize:
            print(f"\nVisualização gravada em: {Path(args.visualize).resolve()}")
    return 0


def resolve_project_path(value: Any) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parent / path


def command_configured_search(search_message: Dict[str, Any]) -> int:
    config = resolve_project_path(search_message.get("config", "examples/ring.json"))
    node_id = search_message.get("node_id") or search_message.get("node")
    resource_id = search_message.get("resource_id") or search_message.get("resource")
    if not node_id:
        raise SearchError("BUSCA precisa informar node_id")
    if not resource_id:
        raise SearchError("BUSCA precisa informar resource_id")

    ttl = int(search_message.get("ttl", 3))
    algorithm = search_message.get("algo", "flooding")
    seed = search_message.get("seed")
    ignore_cache = bool(search_message.get("ignore_cache", False))
    trace = bool(search_message.get("trace", False))
    json_output = bool(search_message.get("json", False))
    visualize = search_message.get("visualize")

    network = P2PNetwork.from_file(config)
    result = network.search(
        str(node_id),
        str(resource_id),
        ttl,
        str(algorithm),
        seed=None if seed is None else int(seed),
        ignore_cache=ignore_cache,
    )

    visualization_path: Optional[Path] = None
    if visualize:
        visualization_path = resolve_project_path(visualize)
        visualization_path.parent.mkdir(parents=True, exist_ok=True)
        visualization_path.write_text(build_visualization_html(network, result), encoding="utf-8")

    if json_output:
        payload = result.as_dict(include_events=trace)
        if visualization_path is not None:
            payload["visualization"] = str(visualization_path.resolve())
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Executando busca configurada no objeto BUSCA\n")
        print(format_result(result))
        if trace:
            print()
            print(format_trace(result))
        if visualization_path is not None:
            print(f"\nVisualização gravada em: {visualization_path.resolve()}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    network = P2PNetwork.from_file(args.config)
    print("Configuração válida")
    print(f"nodes: {len(network.nodes)}")
    print(f"edges: {len(network.edges)}")
    print(f"resource_types: {len(network.resource_locations)}")
    return 0


def command_search(args: argparse.Namespace) -> int:
    network = P2PNetwork.from_file(args.config)
    result = network.search(
        args.node_id,
        args.resource_id,
        args.ttl,
        args.algo,
        seed=args.seed,
        ignore_cache=args.ignore_cache,
    )
    if args.json_output:
        print(json.dumps(result.as_dict(include_events=args.trace), ensure_ascii=False, indent=2))
    else:
        print(format_result(result))
        if args.trace:
            print()
            print(format_trace(result))
    return 0


def command_compare(args: argparse.Namespace) -> int:
    results = []
    for algorithm in ALGORITHM_ORDER:
        network = P2PNetwork.from_file(args.config)
        results.append(
            network.search(
                args.node_id,
                args.resource_id,
                args.ttl,
                algorithm,
                seed=args.seed,
                ignore_cache=args.ignore_cache,
            )
        )
    if args.json_output:
        print(
            json.dumps(
                {
                    "results": [result.as_dict() for result in results],
                    "statistics": summarize_results(results),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_table(results)
        print_statistics(results)
    return 0


def command_batch(args: argparse.Namespace) -> int:
    network = P2PNetwork.from_file(args.config)
    queries = load_queries(args.queries)
    results = []
    for index, query in enumerate(queries):
        seed = None if args.seed is None else args.seed + index
        query_ignore_cache = bool(args.ignore_cache or query.get("ignore_cache", False))
        result = network.search(
            query.get("node_id") or query.get("node"),
            query.get("resource_id") or query.get("resource"),
            int(query["ttl"]),
            query["algo"],
            seed=seed,
            ignore_cache=query_ignore_cache,
        )
        results.append(result)

    if args.csv:
        write_csv(args.csv, results)

    if args.json_output:
        print(
            json.dumps(
                {
                    "results": [result.as_dict(include_events=args.trace) for result in results],
                    "statistics": summarize_results(results),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_table(results)
        print_statistics(results)
        if args.trace:
            for result in results:
                print()
                print(f"{result.search_id} / {result.algorithm}")
                print(format_trace(result))
        if args.csv:
            print(f"\nCSV gravado em: {args.csv}")
    return 0


def command_dot(args: argparse.Namespace) -> int:
    network = P2PNetwork.from_file(args.config)
    print(network.to_dot())
    return 0


def command_visualize(args: argparse.Namespace) -> int:
    network = P2PNetwork.from_file(args.config)
    result = network.search(
        args.node_id,
        args.resource_id,
        args.ttl,
        args.algo,
        seed=args.seed,
        ignore_cache=args.ignore_cache,
    )
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
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        try:
            return command_configured_search(BUSCA)
        except (ConfigError, SearchError, KeyError, json.JSONDecodeError) as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1

    if should_use_direct_parser(argv):
        parser = build_direct_parser()
        args = parser.parse_args(argv)
        try:
            return command_direct(args, parser)
        except (ConfigError, SearchError, KeyError, json.JSONDecodeError) as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1

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
