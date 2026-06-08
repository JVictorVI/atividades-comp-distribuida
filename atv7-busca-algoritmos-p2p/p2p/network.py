"""Estrutura da rede P2P e algoritmos de busca."""

from __future__ import annotations

import random
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .config import clean_token, load_config, parse_list
from .models import ALGORITHMS, ConfigError, MessageEvent, SearchError, SearchResult


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
                break

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

