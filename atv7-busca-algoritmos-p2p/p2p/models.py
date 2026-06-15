"""Modelos, erros e constantes compartilhadas do simulador P2P."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

# Constantes e tipos compartilhados entre os módulos do simulador.
ALGORITHM_ORDER = [
    "flooding",
    "random_walk",
]

ALGORITHMS = set(ALGORITHM_ORDER)

ALGORITHM_CHOICES = sorted(ALGORITHMS)

def normalize_algorithm(algorithm: str) -> str:
    return algorithm

class ConfigError(ValueError):
    """Erro encontrado no arquivo de configuração da rede."""


class SearchError(ValueError):
    """Erro encontrado nos parâmetros de uma operação de busca."""

# Modelos de dados usados para representar os resultados das buscas e 
# os eventos de mensagens trocadas entre os nós.
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

# Modelo principal para representar o resultado de uma busca, 
# incluindo detalhes como o caminho percorrido, os eventos de mensagens e 
# um snapshot do cache dos nós envolvidos.
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

