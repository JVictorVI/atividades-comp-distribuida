"""Estrutura da rede P2P e algoritmos de busca."""

from __future__ import annotations

import random
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .config import clean_token, load_config, parse_list
from .models import ALGORITHMS, ConfigError, MessageEvent, SearchError, SearchResult, normalize_algorithm

class P2PNetwork:
    def __init__(self, config: Dict[str, Any]) -> None:
        # Campos obrigatórios
        self.num_nodes = self._required_int(config, "num_nodes")
        self.min_neighbors = self._required_int(config, "min_neighbors")
        self.max_neighbors = self._required_int(config, "max_neighbors")

        # Validações iniciais
        if self.num_nodes <= 0:
            raise ConfigError("num_nodes deve ser maior que zero")
        if self.min_neighbors < 0 or self.max_neighbors < 0:
            raise ConfigError("min_neighbors e max_neighbors não podem ser negativos")
        if self.min_neighbors > self.max_neighbors:
            raise ConfigError("min_neighbors não pode ser maior que max_neighbors")
        if self.max_neighbors > self.num_nodes - 1:
            raise ConfigError("max_neighbors não pode exceder num_nodes - 1")

        # Campos opcionais e normalizações
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

    # Normalização e validação de recursos, arestas e caches
    def _normalize_resources(self, raw_resources: Any) -> Dict[str, Set[str]]:
        if not isinstance(raw_resources, dict):
            raise ConfigError("resources deve ser um mapa nó -> lista de recursos")

        # Inicializa com conjuntos vazios para garantir que todos os nós tenham uma entrada
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
        algorithm = normalize_algorithm(algorithm)
        if algorithm not in ALGORITHMS:
            raise SearchError(f"Algoritmo inválido: {algorithm}")

        self._search_sequence += 1
        search_id = f"s{self._search_sequence}"
        cache_snapshot = self._snapshot_caches()
        if algorithm == "flooding":
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
        use_cache = not ignore_cache
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
        # Cada item é (nó atual, TTL restante, caminho até aqui)
        frontier: List[Tuple[str, int, List[str]]] = [(start, ttl, [start])]
        # Guarda a primeira resposta bem-sucedida para otimizar a resposta direta
        first_success: Optional[Tuple[str, str, Optional[str], List[str]]] = None
        reply_sent = False
        round_number = 0

        # O loop principal do flooding, processando cada "onda" de mensagens
        while frontier:
            round_number += 1
            # O próximo frontier é construído a partir do frontier atual, expandindo para os vizinhos dos nós atuais, respeitando o TTL e evitando ciclos. Durante essa expansão, verificamos se encontramos o recurso e registramos os eventos de mensagem. Se encontrarmos o recurso, preparamos a resposta direta e otimizamos as conexões se necessário.
            # O uso de um dicionário para o próximo frontier permite evitar duplicatas e garantir que cada nó seja processado apenas uma vez por rodada, mesmo que seja alcançado por múltiplos caminhos. Isso é importante para manter a eficiência do flooding e evitar explosões combinatórias de mensagens.
            next_frontier: Dict[str, Tuple[str, int, List[str]]] = {}
            reply_node: Optional[str] = None

            for current, remaining_ttl, path in frontier:
                if remaining_ttl <= 0:
                    continue
                # O processamento dos vizinhos é feito em ordem alfabética para garantir determinismo, o que é importante para testes e análises. Para cada vizinho, verificamos se ele já está no caminho atual para evitar ciclos, e se não estiver, preparamos a mensagem de busca para esse vizinho, registramos o evento e verificamos se encontramos o recurso. Se encontrarmos o recurso, preparamos a resposta direta e otimizamos as conexões se necessário. Se o TTL permitir, adicionamos o vizinho ao próximo frontier para ser processado na próxima rodada.
                for neighbor in sorted(self.adjacency[current]):
                    # Evita ciclos verificando se o vizinho já está no caminho atual. Isso é crucial para evitar que a busca fique presa em loops infinitos, especialmente em grafos com ciclos. Mesmo que um nó seja alcançado por múltiplos caminhos, ele só deve ser processado uma vez por rodada, e essa verificação ajuda a garantir isso.
                    if neighbor in path:
                        continue

                    next_ttl = remaining_ttl - 1
                    # O caminho para o vizinho é construído a partir do caminho atual, adicionando o vizinho ao final. Isso permite que, se encontrarmos o recurso no vizinho, possamos reconstruir o caminho completo desde o início até o detentor do recurso, o que é útil para análise e para otimizar as conexões futuras.
                    next_path = path + [neighbor]
                    # O vizinho é considerado envolvido na busca, mesmo que já tenha sido processado antes, pois ele participa do processo de busca e pode ser um ponto de contato importante para encontrar o recurso. Isso é importante para a análise do número de nós envolvidos na busca, especialmente em casos onde o recurso é encontrado por múltiplos caminhos ou quando o TTL é alto.
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

                    # Evita processar o mesmo vizinho múltiplas vezes na mesma rodada, mesmo que seja alcançado por múltiplos caminhos. Isso é importante para manter a eficiência do flooding e evitar explosões combinatórias de mensagens, especialmente em grafos densos ou com muitos ciclos. O vizinho ainda é considerado envolvido na busca, mas só será processado uma vez por rodada.
                    if neighbor in processed or neighbor in next_frontier:
                        continue

                    # Verifica se o recurso está no vizinho ou em seu cache (se permitido) e registra a primeira resposta bem-sucedida para otimizar a resposta direta. Se encontrarmos o recurso, preparamos a resposta direta e otimizamos as conexões se necessário. Se o TTL permitir, adicionamos o vizinho ao próximo frontier para ser processado na próxima rodada.
                    processed.add(neighbor)

                    # A busca é feita no vizinho, verificando se o recurso está disponível localmente ou via cache (se permitido). Se encontrado, preparamos a resposta direta e otimizamos as conexões se necessário. O uso do cache é controlado pelo algoritmo escolhido e pela flag ignore_cache, permitindo comparar o desempenho com e sem cache.
                    holder, found_via = self._lookup(neighbor, resource_id, use_cache)
                    found_resource = holder is not None
                    if found_resource:
                        if first_success is None:
                            first_success = (holder, neighbor, found_via, next_path)
                            reply_node = neighbor

                    # Se o recurso não for encontrado, mas o TTL permitir, adicionamos o vizinho ao próximo frontier para ser processado na próxima rodada. O uso de um dicionário para o próximo frontier permite evitar duplicatas e garantir que cada nó seja processado apenas uma vez por rodada, mesmo que seja alcançado por múltiplos caminhos. Isso é importante para manter a eficiência do flooding e evitar explosões combinatórias de mensagens.
                    if not found_resource and next_ttl > 0:
                        next_frontier[neighbor] = (neighbor, next_ttl, next_path)

            # Após processar todos os nós do frontier atual, verificamos se encontramos o recurso e preparamos a resposta direta se necessário. Se encontrarmos o recurso, preparamos a resposta direta e otimizamos as conexões se necessário. O uso do cache é controlado pelo algoritmo escolhido e pela flag ignore_cache, permitindo comparar o desempenho com e sem cache. O loop continua até que o recurso seja encontrado ou que não haja mais nós para processar.
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

        # Após o loop de flooding, verificamos se encontramos o recurso e preparamos a resposta direta se necessário. Se encontrarmos o recurso, preparamos a resposta direta e otimizamos as conexões se necessário. O uso do cache é controlado pelo algoritmo escolhido e pela flag ignore_cache, permitindo comparar o desempenho com e sem cache. Se não encontrarmos o recurso, retornamos um resultado de falha com os detalhes da busca.
        if first_success is not None:
            # Se o recurso foi encontrado, preparamos a resposta direta e otimizamos as conexões se necessário. O uso do cache é controlado pelo algoritmo escolhido e pela flag ignore_cache, permitindo comparar o desempenho com e sem cache. O caminho final inclui o caminho percorrido até o nó que respondeu, e se a resposta veio do cache, também inclui o detentor real do recurso para refletir a otimização de conexão direta.
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
        use_cache = not ignore_cache
        current = start
        path = [start]
        stack = [(start, ttl)]
        involved = {start}
        visited = {start}
        messages = 0
        remaining_ttl = ttl
        events: List[MessageEvent] = []

        while True:
            # Verifica se o recurso está no nó atual ou no cache (se permitido)
            holder, found_via = self._lookup(current, resource_id, use_cache and current != start)
            # Se encontrado, prepara a resposta e termina a busca
            if holder is not None:
                round_number = max(0, len(path) - 1)
                messages = self._add_direct_reply_if_needed(
                    events, search_id, round_number, start, current, resource_id, messages
                )
                # Se encontrado via cache, adiciona conexão direta e inclui o detentor real como envolvido
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
            # Seleciona aleatoriamente um vizinho não visitado para o próximo passo.
            # Se não houver, volta pelo caminho percorrido e tenta outra ramificação.
            neighbors = [neighbor for neighbor in sorted(self.adjacency[current]) if neighbor not in visited]

            previous = current
            next_event_ttl = remaining_ttl
            if neighbors and remaining_ttl > 0:
                # A escolha aleatória é feita entre os vizinhos não visitados para evitar ciclos desnecessários
                current = rng.choice(neighbors)
                visited.add(current)
                next_event_ttl = remaining_ttl - 1
                remaining_ttl -= 1
                stack.append((current, remaining_ttl))
            else:
                # Se chegou ao início sem poder avançar, todo o espaço permitido pelo TTL foi explorado
                if len(stack) == 1:
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
                stack.pop()
                current, remaining_ttl = stack[-1]
                next_event_ttl = remaining_ttl

            # Atualiza o caminho, os envolvidos e os eventos de mensagem
            path.append(current)
            # O nó atual é considerado envolvido mesmo que já tenha sido visitado antes, pois ele participa da busca
            involved.add(current)
            # Cada movimento conta como mensagem; apenas os avanços consomem TTL
            messages += 1
            # O número da rodada é baseado no comprimento do caminho, representando quantos saltos foram dados desde o início. Isso é útil para análise posterior dos eventos.
            round_number = len(path) - 1
            # Cada movimento é registrado como um evento de mensagem, incluindo o nó de origem, o nó de destino, o recurso buscado e o TTL restante. Isso permite uma análise detalhada do comportamento da busca.
            self._add_event(
                events,
                search_id,
                round_number,
                "request",
                previous,
                current,
                resource_id,
                next_event_ttl,
            )

    # Verifica se o recurso está disponível no nó ou em seu cache (se permitido) e retorna o detentor real e a origem da informação
    def _lookup(self, node: str, resource_id: str, use_cache: bool) -> Tuple[Optional[str], Optional[str]]:
        if resource_id in self.resources[node]:
            return node, "local"
        if use_cache and resource_id in self.caches[node]:
            return self.caches[node][resource_id], "cache"
        return None, None

    @staticmethod
    # Adiciona um evento de mensagem à lista de eventos, atribuindo um número de passo sequencial e incluindo detalhes como tipo, origem, destino, recurso e TTL restante. Isso é usado para registrar o histórico da busca para análise posterior.
    # Eventos são registrados para cada mensagem enviada, permitindo uma reconstrução detalhada do processo de busca, incluindo quais nós foram contatados, em que ordem, e como o recurso foi encontrado (se foi encontrado). O número da rodada é útil para entender a dinâmica temporal da busca, especialmente no caso do flooding onde múltiplas mensagens são enviadas em paralelo. O TTL registrado em cada evento ajuda a analisar a eficiência da busca e quantos saltos foram necessários para encontrar o recurso ou esgotar o TTL.
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

    # Adiciona um evento de resposta direta se o nó de início for diferente do nó que respondeu, e retorna o número atualizado de mensagens. Isso é usado para registrar a resposta direta do detentor do recurso ao nó inicial, otimizando a análise do processo de busca.
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

    # Adiciona um evento de conexão direta se o nó de início for diferente do detentor do recurso, e retorna o número atualizado de mensagens. Isso é usado para registrar a otimização onde o nó inicial estabelece uma conexão direta com o detentor do recurso após descobrir sua localização via cache, otimizando a análise do processo de busca.
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

    # Cria uma cópia profunda dos caches atuais para incluir no resultado da busca, permitindo uma análise do estado dos caches em cada nó no momento da busca. Isso é útil para entender como os caches influenciaram o processo de busca e para verificar se as informações nos caches estavam corretas.
    def _snapshot_caches(self) -> Dict[str, Dict[str, str]]:
        return {node: dict(entries) for node, entries in self.caches.items()}

    # Preenche os caches dos nós no caminho com a informação do detentor do recurso encontrado, e retorna um SearchResult indicando o sucesso da busca, incluindo detalhes como o algoritmo usado, o caminho percorrido, os eventos de mensagem e o estado dos caches. Isso é usado para registrar o resultado bem-sucedido da busca, incluindo as otimizações de cache aprendidas durante o processo.
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
    # Cria um SearchResult indicando o fracasso da busca, incluindo detalhes como o algoritmo usado, o caminho percorrido, os eventos de mensagem e o estado dos caches. Isso é usado para registrar o resultado de uma busca que não conseguiu encontrar o recurso dentro do TTL ou devido a outros fatores, permitindo uma análise detalhada do processo de busca mesmo em casos de falha.
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
    # Preenche os caches dos nós no caminho com a informação do detentor do recurso encontrado. Isso é usado para otimizar buscas futuras, permitindo que os nós aprendam a localização do recurso e possam responder mais rapidamente em buscas subsequentes.
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

