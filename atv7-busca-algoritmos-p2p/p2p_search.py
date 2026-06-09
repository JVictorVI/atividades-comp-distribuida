"""Entrada principal do simulador de busca em redes P2P não estruturadas.

Altere o objeto BUSCA abaixo e execute `python .\\p2p_search.py` para rodar
uma busca sem precisar montar os parâmetros pelo terminal.
"""

from __future__ import annotations

from typing import Optional, Sequence

from p2p import (
    ALGORITHM_CHOICES,
    ALGORITHM_ORDER,
    ALGORITHMS,
    ConfigError,
    MessageEvent,
    P2PNetwork,
    SearchError,
    SearchResult,
    build_visualization_css,
    build_visualization_html,
    build_visualization_js,
    circular_layout,
    clean_token,
    escape_dot,
    format_result,
    format_trace,
    load_config,
    parse_edge_line,
    parse_list,
    parse_simple_yaml,
    print_statistics,
    print_table,
    summarize_results,
    topology_layout,
    write_visualization_files,
)
from p2p.cli import main as _run_cli


# Altere este objeto para montar a mensagem de busca que será executada quando
# você rodar apenas: python .\p2p_search.py
BUSCA = {
    "config": "examples/complex.yaml",
    "node_id": "n1",
    "resource_id": "r5",
    "ttl": 3,
    "algo": "flooding",
    "seed": None,
    "ignore_cache": False,
    "trace": True,
    "json": False,
    "visualize": "visualization.html",
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    return _run_cli(BUSCA, argv)


__all__ = [
    "ALGORITHM_CHOICES",
    "ALGORITHM_ORDER",
    "ALGORITHMS",
    "BUSCA",
    "ConfigError",
    "MessageEvent",
    "P2PNetwork",
    "SearchError",
    "SearchResult",
    "build_visualization_css",
    "build_visualization_html",
    "build_visualization_js",
    "circular_layout",
    "clean_token",
    "escape_dot",
    "format_result",
    "format_trace",
    "load_config",
    "main",
    "parse_edge_line",
    "parse_list",
    "parse_simple_yaml",
    "print_statistics",
    "print_table",
    "summarize_results",
    "topology_layout",
    "write_visualization_files",
]


if __name__ == "__main__":
    raise SystemExit(main())

