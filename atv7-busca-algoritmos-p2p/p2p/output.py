"""Formatação textual e estatísticas das buscas."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Sequence

from .models import ALGORITHM_ORDER, SearchResult

# Altere o objeto BUSCA abaixo e execute `python .\\p2p_search.py` para rodar
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

 # Gera uma representação textual do trace de mensagens trocadas durante a busca.
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

# Gera uma tabela formatada com os resultados das buscas, mostrando os principais detalhes de cada execução.
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

# Agrupa os resultados por algoritmo e calcula estatísticas como taxa de sucesso, média de mensagens e nós envolvidos.
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

# Gera e imprime uma tabela de estatísticas resumidas para cada algoritmo testado, incluindo taxa de sucesso e média de mensagens trocadas.
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

