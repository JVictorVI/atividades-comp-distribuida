# Implementação de Algoritmos de Busca em Sistemas P2P

Projeto desenvolvido para a atividade de Computação Distribuída sobre algoritmos de busca em redes peer-to-peer (P2P) não estruturadas.

O programa lê uma configuração de rede, valida a topologia e permite buscar recursos usando quatro estratégias:

- `flooding`
- `informed_flooding`
- `random_walk`
- `informed_random_walk`

Ao final de cada busca, o programa informa se o recurso foi encontrado, qual nó respondeu, o caminho percorrido, o número total de mensagens trocadas e o número total de nós envolvidos.

## Objetivo

O objetivo do projeto é simular como diferentes algoritmos localizam recursos em uma rede P2P sem servidor central e sem índice global. A rede é representada como um grafo não direcionado, em que cada nó possui recursos próprios e conhece apenas seus vizinhos.

Com isso, é possível comparar o custo de cada algoritmo em termos de mensagens trafegadas e nós envolvidos na busca.

## Estrutura do projeto

```text
.
├── p2p_search.py
├── README.md
├── examples
│   ├── mesh.yaml
│   ├── queries.json
│   └── ring.json
├── tests
│   └── test_p2p_search.py
└── Trabalho 7 – Implementação de Algoritmos de Busca em Sistemas P2P.pdf
```

Descrição dos principais arquivos:

- `p2p_search.py`: implementação principal do simulador, parser de configuração, validações, algoritmos de busca, comandos de terminal e geração da visualização HTML.
- `examples/ring.json`: exemplo de rede em anel com 6 nós.
- `examples/mesh.yaml`: exemplo de rede mais conectada em YAML.
- `examples/queries.json`: lista de buscas para execução em lote.
- `tests/test_p2p_search.py`: testes automatizados das validações, algoritmos, formatos de entrada e visualização.
- `visualization.html`: arquivo gerado pelo comando `visualize` quando uma animação é criada.
- `results.csv`: arquivo gerado opcionalmente pelo comando `batch`.

## Como foi feito

O projeto foi implementado em Python puro, sem dependências externas, para facilitar a execução durante a apresentação.

A rede P2P é modelada pela classe `P2PNetwork`. Internamente, ela mantém:

- uma lista de nós no formato `n1`, `n2`, `n3` etc.;
- um mapa de recursos por nó;
- uma lista de adjacência para representar as conexões da rede;
- um mapa de localização dos recursos;
- caches locais usados pelas buscas informadas.

As buscas retornam um objeto `SearchResult`, que contém as métricas finais e uma lista de eventos de mensagem. Essa lista de eventos é usada pela visualização HTML para animar o caminho das requisições e respostas.

## Formato do arquivo de configuração

O programa aceita o formato textual do enunciado, JSON ou YAML simples.

Exemplo no formato do enunciado:

```yaml
num_nodes: 3
min_neighbors: 1
max_neighbors: 2
resources:
n1: r1, doc-a
n2: r2, doc-b
n3: r3, doc-c
edges:
n1, n2
n2, n3
```

Exemplo equivalente em JSON:

```json
{
  "num_nodes": 3,
  "min_neighbors": 1,
  "max_neighbors": 2,
  "resources": {
    "n1": ["r1", "doc-a"],
    "n2": ["r2", "doc-b"],
    "n3": ["r3", "doc-c"]
  },
  "edges": [
    ["n1", "n2"],
    ["n2", "n3"]
  ]
}
```

## Validações realizadas

Após ler o arquivo de configuração, o programa verifica:

- se a rede está conectada, sem partições;
- se todos os nós respeitam os limites de `min_neighbors` e `max_neighbors`;
- se todos os nós possuem pelo menos um recurso;
- se não existem arestas de um nó para ele mesmo;
- se não há referências a nós desconhecidos;
- se os campos obrigatórios foram preenchidos corretamente.

Se alguma validação falhar, o programa encerra a execução e mostra uma mensagem explicando o problema.

## Algoritmos implementados

### Flooding

A busca por inundação envia a requisição para todos os vizinhos ainda não visitados, respeitando o limite de TTL. Ela tende a encontrar o recurso quando ele está dentro do alcance, mas pode gerar muitas mensagens.

### Informed Flooding

Funciona como o `flooding`, mas cada nó consulta seu cache local antes de continuar propagando a busca. Quando uma busca encontra um recurso, os nós no caminho de resposta aprendem a localização desse recurso.

### Random Walk

A busca por passeio aleatório escolhe apenas um vizinho por vez e encaminha a requisição para ele. Esse algoritmo costuma gerar menos mensagens, mas pode não encontrar o recurso mesmo quando ele está relativamente perto, porque o caminho depende das escolhas aleatórias.

### Informed Random Walk

Funciona como o `random_walk`, mas também consulta o cache local antes de sortear o próximo vizinho. Isso permite que buscas futuras sejam resolvidas mais rapidamente quando algum nó já aprendeu a localização do recurso.

## Contagem de mensagens

O total de mensagens contabiliza:

- cada envio de requisição entre dois nós;
- cada mensagem de resposta no caminho de volta quando o recurso é encontrado.

Por exemplo, se a busca percorre `n1 -> n2 -> n3`, são contadas as mensagens de ida e, em caso de sucesso, as mensagens de retorno até o nó inicial.

## Como executar

Use Python 3 no terminal dentro da pasta do projeto.

### `validate`

Valida o arquivo de configuração da rede antes de executar qualquer busca. Esse comando verifica se a rede está conectada, se todos os nós respeitam os limites de vizinhos, se todos possuem recursos e se não existem arestas inválidas.

Use esse comando quando quiser confirmar que a topologia criada está correta.

```powershell
python .\p2p_search.py validate .\examples\ring.json
```

Saída esperada:

```text
Configuração válida
nodes: 6
edges: 6
resource_types: 12
```

### `search`

Executa uma única operação de busca em uma rede validada. Esse comando recebe o nó inicial, o recurso procurado, o TTL e o algoritmo que será utilizado.

Use esse comando para demonstrar uma busca específica e observar o caminho percorrido, o resultado, o total de mensagens e o total de nós envolvidos.

```powershell
python .\p2p_search.py search .\examples\ring.json --node n1 --resource r4 --ttl 3 --algo flooding
```

Parâmetros principais:

- `--node`: nó que inicia a busca.
- `--resource`: recurso que será procurado.
- `--ttl`: quantidade máxima de saltos permitida.
- `--algo`: algoritmo usado na busca.
- `--seed`: semente opcional para tornar o `random_walk` reprodutível.
- `--json`: imprime o resultado em JSON.

### `compare`

Executa a mesma busca usando os quatro algoritmos implementados. O objetivo é facilitar a comparação entre `flooding`, `informed_flooding`, `random_walk` e `informed_random_walk`.

Use esse comando para gerar uma tabela comparativa com resultado, nó detentor do recurso, mensagens, nós envolvidos e caminho percorrido.

```powershell
python .\p2p_search.py compare .\examples\ring.json --node n1 --resource r4 --ttl 3 --seed 7
```

Observação: no `compare`, cada algoritmo é executado em uma rede recém-carregada. Isso evita que o cache aprendido por um algoritmo interfira no resultado de outro.

### `batch`

Executa uma lista de buscas definida em um arquivo JSON. As buscas são processadas na ordem em que aparecem no arquivo.

Use esse comando para rodar vários cenários de teste de uma vez, preservar o cache entre as buscas e gerar resultados para tabelas ou gráficos.

```powershell
python .\p2p_search.py batch .\examples\ring.json .\examples\queries.json --seed 7 --csv .\results.csv
```

Parâmetros principais:

- primeiro argumento: arquivo de configuração da rede.
- segundo argumento: arquivo JSON com as buscas.
- `--csv`: caminho do arquivo CSV que será gerado.
- `--json`: imprime todos os resultados em JSON.
- `--seed`: semente base usada nas buscas aleatórias.

### `dot`

Gera uma representação da rede no formato Graphviz DOT. Esse formato pode ser usado por ferramentas externas, como Graphviz, para renderizar uma imagem do grafo.

Use esse comando quando quiser visualizar apenas a topologia da rede, sem executar uma busca.

```powershell
python .\p2p_search.py dot .\examples\ring.json
```

### `visualize`

Executa uma busca e gera uma página HTML com a representação gráfica da rede e a animação das mensagens trocadas. O arquivo gerado é autocontido, ou seja, não depende de bibliotecas externas.

Use esse comando para demonstrar a busca de forma visual durante a apresentação.

```powershell
python .\p2p_search.py visualize .\examples\ring.json --node n1 --resource r4 --ttl 3 --algo flooding --output .\visualization.html
```

Na página gerada, os controles fazem o seguinte:

- `Play`: reproduz a animação automaticamente.
- `Step`: avança uma mensagem por vez.
- `Reset`: volta a animação para o início.

Depois, abra `visualization.html` no navegador para ver a rede, os nós envolvidos, as mensagens e as métricas finais.

## Execução em lote

O comando `batch` recebe um arquivo JSON com várias consultas e executa uma após a outra.

Exemplo:

```json
[
  {
    "node_id": "n1",
    "resource_id": "r4",
    "ttl": 3,
    "algo": "flooding"
  },
  {
    "node_id": "n1",
    "resource_id": "r4",
    "ttl": 3,
    "algo": "informed_flooding"
  }
]
```

Nesse modo, o cache é preservado entre as buscas. Isso é útil para demonstrar o ganho das buscas informadas depois que uma busca anterior já preencheu parte dos caches.

## Visualização gráfica

O comando `visualize` gera um arquivo HTML autocontido. Ele não depende de bibliotecas externas e pode ser aberto diretamente no navegador.

A visualização mostra:

- os nós e as arestas da rede;
- o nó inicial;
- o nó que respondeu à busca;
- as mensagens de requisição e resposta;
- a lista de recursos por nó;
- as métricas finais da busca.

## Testes

Execute os testes com:

```powershell
python -m unittest discover -s tests
```

Os testes cobrem:

- leitura de JSON;
- leitura do formato textual do enunciado;
- leitura de YAML simples;
- validação de rede particionada;
- validação de limites de vizinhos;
- validação de nós sem recursos;
- validação de arestas para o próprio nó;
- comportamento dos algoritmos de busca;
- uso de cache nas buscas informadas;
- geração da visualização HTML.

## Observações

- O identificador dos nós segue o padrão `n1`, `n2`, `n3` até `num_nodes`.
- O TTL representa o número máximo de saltos que uma requisição pode realizar.
- O `random_walk` aceita `--seed` para tornar os testes e demonstrações reprodutíveis.
- O projeto ignora arquivos gerados, como `results.csv`, `visualization.html`, `visualization.htm` e `__pycache__`.
