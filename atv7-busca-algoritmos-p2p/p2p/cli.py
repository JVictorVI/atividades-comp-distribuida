"""Interface de linha de comando enxuta do simulador P2P."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .models import ALGORITHM_CHOICES, ALGORITHM_ORDER, ConfigError, SearchError, SearchResult
from .network import P2PNetwork
from .output import format_result, format_trace, print_statistics, print_table
from .visualization import write_visualization_files


COMMAND_NAMES = {"search", "compare", "batch", "visualize"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulador de busca em redes P2P nao estruturadas")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="executa uma busca")
    search_parser.add_argument("config", type=Path)
    search_parser.add_argument("--node", "--node-id", dest="node_id", required=True)
    search_parser.add_argument("--resource", "--resource-id", dest="resource_id", required=True)
    search_parser.add_argument("--ttl", type=int, required=True)
    search_parser.add_argument("--algo", choices=ALGORITHM_CHOICES, required=True)
    search_parser.add_argument("--seed", type=int, default=None)
    search_parser.add_argument("--ignore-cache", action="store_true", help="ignora caches locais nesta busca")
    search_parser.add_argument("--trace", action="store_true", help="imprime o rastro textual das mensagens")

    compare_parser = subparsers.add_parser("compare", help="compara os dois algoritmos para a mesma busca")
    compare_parser.add_argument("config", type=Path)
    compare_parser.add_argument("--node", "--node-id", dest="node_id", required=True)
    compare_parser.add_argument("--resource", "--resource-id", dest="resource_id", required=True)
    compare_parser.add_argument("--ttl", type=int, required=True)
    compare_parser.add_argument("--seed", type=int, default=None)
    compare_parser.add_argument("--ignore-cache", action="store_true", help="ignora caches locais nas buscas informadas")

    batch_parser = subparsers.add_parser("batch", help="executa uma lista de buscas em JSON")
    batch_parser.add_argument("config", type=Path)
    batch_parser.add_argument("queries", type=Path)
    batch_parser.add_argument("--seed", type=int, default=None)
    batch_parser.add_argument("--csv", type=Path, default=None)
    batch_parser.add_argument("--ignore-cache", action="store_true", help="ignora caches locais em todas as buscas")
    batch_parser.add_argument("--trace", action="store_true", help="imprime rastros textuais de todas as buscas")

    visualize_parser = subparsers.add_parser("visualize", help="gera HTML com grafo e animacao da busca")
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
            "python p2p_search.py examples/ring.yaml n1 r4 --ttl 3 --algo flooding"
        )
    )
    parser.add_argument("config", type=Path, help="arquivo de configuracao da rede")
    parser.add_argument("node_id_arg", nargs="?", help="no que inicia a busca")
    parser.add_argument("resource_id_arg", nargs="?", help="recurso procurado")
    parser.add_argument("--node", "--node-id", dest="node_id", help="no que inicia a busca")
    parser.add_argument("--resource", "--resource-id", dest="resource_id", help="recurso procurado")
    parser.add_argument("--ttl", type=int, default=3, help="niveis de propagacao da busca")
    parser.add_argument("--algo", choices=ALGORITHM_CHOICES, default="flooding", help="algoritmo de busca")
    parser.add_argument("--seed", type=int, default=None, help="semente para random_walk")
    parser.add_argument("--ignore-cache", action="store_true", help="ignora caches locais nesta busca")
    parser.add_argument("--trace", action="store_true", help="imprime o rastro textual das mensagens")
    parser.add_argument(
        "--visualize",
        nargs="?",
        const="visualization.html",
        default=None,
        help="gera HTML da animacao; opcionalmente informe o caminho do arquivo",
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
        parser.error("informe o no inicial por posicao ou com --node")
    if not resource_id:
        parser.error("informe o recurso por posicao ou com --resource")
    return node_id, resource_id


def print_visualization_paths(paths: Dict[str, Path]) -> None:
    print(f"\nVisualizacao gravada em: {paths['html'].resolve()}")
    print(f"CSS gravado em: {paths['css'].resolve()}")
    print(f"JS gravado em: {paths['js'].resolve()}")


def print_search_result(result: SearchResult, trace: bool = False) -> None:
    print(format_result(result))
    if trace:
        print()
        print(format_trace(result))


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

    visualization_paths: Optional[Dict[str, Path]] = None
    if args.visualize:
        visualization_paths = write_visualization_files(Path(args.visualize), network, result)

    print_search_result(result, args.trace)
    if visualization_paths is not None:
        print_visualization_paths(visualization_paths)
    return 0


def resolve_project_path(value: Any) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parent.parent / path


def command_configured_search(search_message: Dict[str, Any]) -> int:
    config = resolve_project_path(search_message.get("config", "examples/ring.yaml"))
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

    visualization_paths: Optional[Dict[str, Path]] = None
    if visualize:
        visualization_paths = write_visualization_files(resolve_project_path(visualize), network, result)

    print("Executando busca configurada no objeto BUSCA\n")
    print_search_result(result, trace)
    if visualization_paths is not None:
        print_visualization_paths(visualization_paths)
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
    print_search_result(result, args.trace)
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
    visualization_paths = write_visualization_files(args.output, network, result)
    print_search_result(result)
    print_visualization_paths(visualization_paths)
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


def main(search_message: Optional[Dict[str, Any]] = None, argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        try:
            if search_message is None:
                raise SearchError("BUSCA nao foi informada")
            return command_configured_search(search_message)
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
        "search": command_search,
        "compare": command_compare,
        "batch": command_batch,
        "visualize": command_visualize,
    }
    try:
        return commands[args.command](args)
    except (ConfigError, SearchError, KeyError, json.JSONDecodeError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
