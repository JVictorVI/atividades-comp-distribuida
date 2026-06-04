"""Leitura e parsing dos arquivos de configura??o da rede."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import ConfigError


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

