"""Componentes do simulador de busca em redes P2P."""

from .config import clean_token, load_config, parse_edge_line, parse_list, parse_simple_yaml
from .models import (
    ALGORITHM_CHOICES,
    ALGORITHM_ORDER,
    ALGORITHMS,
    ConfigError,
    MessageEvent,
    SearchError,
    SearchResult,
)
from .network import P2PNetwork, escape_dot
from .output import format_result, format_trace, print_statistics, print_table, summarize_results
from .visualization import (
    build_visualization_css,
    build_visualization_html,
    build_visualization_js,
    circular_layout,
    topology_layout,
    write_visualization_files,
)

__all__ = [
    "ALGORITHM_CHOICES",
    "ALGORITHM_ORDER",
    "ALGORITHMS",
    "ConfigError",
    "MessageEvent",
    "P2PNetwork",
    "SearchError",
    "SearchResult",
    "build_visualization_html",
    "build_visualization_css",
    "build_visualization_js",
    "circular_layout",
    "clean_token",
    "escape_dot",
    "format_result",
    "format_trace",
    "load_config",
    "parse_edge_line",
    "parse_list",
    "parse_simple_yaml",
    "print_statistics",
    "print_table",
    "summarize_results",
    "topology_layout",
    "write_visualization_files",
]

