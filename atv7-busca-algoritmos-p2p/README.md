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
├── p2p
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── network.py
│   ├── output.py
│   └── visualization.py
├── README.md
├── examples
│   ├── complex.yaml
│   ├── complex_queries.json
│   ├── mesh.yaml
│   ├── queries.json
│   └── ring.json
└── Trabalho 7 – Implementação de Algoritmos de Busca em Sistemas P2P.pdf
```

Descrição dos principais arquivos:

- `p2p_search.py`: arquivo principal de execução. Nele fica o objeto `BUSCA`, que pode ser alterado diretamente para rodar uma busca sem montar comandos longos.
- `p2p/models.py`: constantes dos algoritmos, classes de erro e estruturas de dados, como `MessageEvent` e `SearchResult`.
- `p2p/config.py`: leitura de JSON, YAML simples e formato textual do enunciado.
- `p2p/network.py`: classe `P2PNetwork`, validação da rede, cache e algoritmos de busca.
- `p2p/output.py`: formatação dos resultados, rastros textuais, tabelas e estatísticas.
- `p2p/visualization.py`: geração dos arquivos HTML, CSS e JavaScript com o grafo e a animação da busca.
- `p2p/cli.py`: comandos de terminal, modo direto com argumentos, execução em lote e integração com o objeto `BUSCA`.
- `examples/ring.json`: exemplo de rede em anel com 6 nós.
- `examples/mesh.yaml`: exemplo de rede mais conectada em YAML.
- `examples/complex.yaml`: exemplo maior, com caches iniciais e topologia mais rica para demonstração.
- `examples/queries.json`: lista de buscas para execução em lote.
- `visualization.html`, `visualization.css` e `visualization.js`: arquivos gerados quando uma animação é criada.
- `results.csv`: arquivo gerado opcionalmente pelo comando `batch`.

## Como foi feito

O projeto foi implementado em Python puro, sem dependências externas, para facilitar a execução durante a apresentação.

O código foi separado em módulos para deixar cada parte mais fácil de entender e alterar. O arquivo `p2p_search.py` continua pequeno e focado na execução; a lógica principal fica dentro da pasta `p2p`.

A rede P2P é modelada pela classe `P2PNetwork`. Internamente, ela mantém:

- uma lista de nós no formato `n1`, `n2`, `n3` etc.;
- um mapa de recursos por nó;
- uma lista de adjacência para representar as conexões da rede;
- um mapa de localização dos recursos;
- caches locais usados pelas buscas informadas.

As buscas retornam um objeto `SearchResult`, que contém as métricas finais e uma lista de eventos de mensagem. Essa lista de eventos é usada pela visualização HTML para animar o caminho das requisições e respostas.

## Interpretação da rede

A implementação segue a interpretação discutida em aula:

- os nós representam sistemas ou computadores da rede;
- os vértices do grafo são os computadores;
- as arestas representam relações de vizinhança;
- as arestas não são direcionadas;
- a relação de vizinhança não é transitiva;
- cada nó tem um identificador único;
- cada nó conhece somente sua própria lista de vizinhos;
- cada nó mantém um conjunto de recursos locais;
- não há replicação de recursos, então um mesmo recurso não pode aparecer em mais de um nó.

Uma mensagem de busca carrega:

- `search_id`: identificador único da busca, usado para evitar ciclos;
- `node_id`: nó que iniciou a busca;
- `resource_id`: recurso procurado;
- `ttl`: quantidade restante de níveis de propagação.

O TTL é tratado como o número de níveis que a mensagem ainda pode avançar. A cada encaminhamento, o TTL é decrementado. Um nó só encaminha a busca se ainda houver nível disponível.

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
caches:
n2: r3=n3
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
  "caches": {
    "n2": {
      "r3": "n3"
    }
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
- se nenhum nó fica sem vizinhos em redes com mais de um nó;
- se não existem arestas de um nó para ele mesmo;
- se não há recursos replicados em mais de um nó;
- se caches iniciais apontam para nós e recursos existentes;
- se não há referências a nós desconhecidos;
- se os campos obrigatórios foram preenchidos corretamente.

Se alguma validação falhar, o programa encerra a execução e mostra uma mensagem explicando o problema.

O bloco `caches` é opcional. Ele representa conhecimentos prévios de alguns nós sobre onde um recurso está. No YAML simples, cada entrada usa o formato `recurso=nó`, como `n2: r3=n3`. No JSON, o mesmo cache pode ser escrito como `"n2": {"r3": "n3"}`. O cache só é usado quando a mensagem chega a um nó intermediário; o nó que inicia a busca não encerra a operação consultando o próprio cache antes de perguntar à rede.

## Algoritmos implementados

### Flooding

A busca por inundação envia a requisição para todos os vizinhos ao mesmo tempo, respeitando o limite de TTL. A simulação é feita em rodadas: na rodada 1 o nó inicial envia para seus vizinhos; na rodada 2 todos os nós alcançados na rodada anterior encaminham a mensagem simultaneamente; e assim por diante.

Como os envios de uma mesma rodada acontecem em paralelo, dois ramos podem enviar mensagens para o mesmo nó na mesma rodada. Essas mensagens contam no tráfego da rede, mesmo que o nó processe apenas a primeira por causa do `search_id`.

Mensagens que já foram disparadas na mesma rodada continuam aparecendo no rastro mesmo quando uma delas encontra o recurso. Depois que a resposta é enviada ao nó inicial, o algoritmo não inicia novas rodadas de propagação.

Quando o recurso é encontrado, o nó que possui o recurso envia uma resposta direta para o nó que iniciou a busca. Essa resposta direta representa a otimização discutida em aula: como a mensagem carrega o identificador do solicitante, o nó encontrado já sabe para quem avisar.

O `search_id` impede que um nó processe a mesma busca mais de uma vez e evita ciclos infinitos.

### Informed Flooding

Funciona como o `flooding`, mas os nós alcançados pela busca consultam seus caches locais antes de continuar propagando a mensagem. Quando a mensagem chega em um nó intermediário que tem cache para o recurso procurado, esse nó avisa diretamente o nó solicitante onde o recurso está. Em seguida, o solicitante cria uma conexão direta com o nó final, representada no rastro como uma mensagem `direct`.

O nó inicial não usa o próprio cache como resposta instantânea no começo da busca. Ele descobre a localização pelo processo de busca: ou chegando ao nó que possui o recurso, ou recebendo a informação de algum nó intermediário que já sabia onde o recurso estava.

Quando uma resposta já foi enviada ao nó inicial, o `informed_flooding` também não executa novas rodadas de propagação. As mensagens da rodada atual ainda aparecem, pois já foram disparadas em paralelo, mas a busca para antes de continuar para os próximos níveis.

Como a rede pode ser mutável, é possível ignorar o cache usando `--ignore-cache`.

### Random Walk

A busca por passeio aleatório escolhe apenas um vizinho por vez e encaminha a requisição para ele. Na prática, ela funciona como uma busca em profundidade aleatória: a cada nível, um vizinho ainda não visitado é escolhido para continuar a busca.

Esse algoritmo costuma gerar menos mensagens, mas pode não encontrar o recurso mesmo quando ele está relativamente perto, porque o caminho depende das escolhas aleatórias e do TTL.

### Informed Random Walk

Funciona como o `random_walk`, mas os nós visitados também consultam o cache local antes de sortear o próximo vizinho. Se um nó intermediário tiver cache para o recurso procurado, ele responde diretamente ao solicitante e a simulação cria a conexão direta até o nó final. Isso permite demonstrar a otimização em que um nó no caminho evita que a busca continue descendo desnecessariamente.

Assim como no `informed_flooding`, o cache pode ser ignorado com `--ignore-cache`.

## Contagem de mensagens

O total de mensagens contabiliza:

- cada envio de requisição entre dois nós;
- a resposta direta do nó que encontrou o recurso, ou do nó intermediário que conhecia o cache, para o nó que iniciou a busca;
- a conexão direta criada entre o solicitante e o nó final quando a localização veio de cache.

Por exemplo, se a busca percorre `n1 -> n2 -> n3` e o recurso está em `n3`, são contadas as mensagens de ida e uma resposta direta `n3 -> n1`. Se `n2` já souber em cache que o recurso está em `n3`, a busca conta a requisição `n1 -> n2`, a resposta `n2 -> n1` e a conexão direta `n1 -> n3`.

## Como executar

Use Python 3 no terminal dentro da pasta do projeto.

### Modo principal: editar o objeto `BUSCA`

O jeito mais simples de usar o projeto é editar o objeto `BUSCA` no começo do arquivo `p2p_search.py`.

Ele já vem assim:

```python
BUSCA = {
    "config": "examples/mesh.yaml",
    "node_id": "n1",
    "resource_id": "r5",
    "ttl": 5,
    "algo": "informed_flooding",
    "seed": None,
    "ignore_cache": False,
    "trace": True,
    "json": False,
    "visualize": "visualization.html",
}
```

Para testar outra busca, altere diretamente esses valores no código.

Depois execute apenas:

```powershell
python .\p2p_search.py
```

Campos do objeto:

- `config`: arquivo da rede que será carregado.
- `node_id`: nó que inicia a busca.
- `resource_id`: recurso procurado.
- `ttl`: quantidade máxima de níveis de propagação.
- `algo`: algoritmo usado na busca.
- `seed`: semente opcional para buscas com `random_walk`.
- `ignore_cache`: ignora caches locais quando for `True`.
- `trace`: imprime o rastro textual das mensagens quando for `True`.
- `json`: imprime a saída em JSON quando for `True`.
- `visualize`: caminho do HTML de visualização, ou `None` para não gerar.

Exemplo para usar passeio aleatório:

```python
BUSCA = {
    "config": "examples/ring.json",
    "node_id": "n1",
    "resource_id": "r4",
    "ttl": 4,
    "algo": "random_walk",
    "seed": 7,
    "ignore_cache": False,
    "trace": True,
    "json": False,
    "visualize": None,
}
```

Exemplo para gerar visualização:

```python
BUSCA = {
    "config": "examples/ring.json",
    "node_id": "n1",
    "resource_id": "r4",
    "ttl": 3,
    "algo": "flooding",
    "seed": None,
    "ignore_cache": False,
    "trace": True,
    "json": False,
    "visualize": "visualization.html",
}
```

### Modo por terminal, opcional

Se quiser, também é possível passar a busca pelo terminal:

```powershell
python .\p2p_search.py .\examples\ring.json n1 r4 --ttl 3 --algo flooding --trace
```

Esse modo é secundário. Para a apresentação, o modo recomendado é editar `BUSCA` e executar `python .\p2p_search.py`.

Exemplo com passeio aleatório pelo terminal:

```powershell
python .\p2p_search.py .\examples\ring.json n1 r4 --algo random_walk --ttl 4 --seed 7
```

Exemplo com visualização pelo terminal:

```powershell
python .\p2p_search.py .\examples\ring.json n1 r4 --visualize .\visualization.html
```

Quando a visualização é gerada, o programa cria três arquivos com o mesmo nome base: `visualization.html`, `visualization.css` e `visualization.js`.

### Comandos auxiliares

Além do modo simples, o programa mantém alguns comandos auxiliares.

#### `validate`

Valida apenas o arquivo de configuração da rede, sem executar busca.

```powershell
python .\p2p_search.py validate .\examples\ring.json
```

A saída também mostra `cache_entries`, que indica quantas entradas de cache foram carregadas do arquivo.

#### `compare`

Executa a mesma busca com os quatro algoritmos e imprime uma tabela comparativa com estatísticas.

```powershell
python .\p2p_search.py compare .\examples\ring.json --node n1 --resource r4 --ttl 3 --seed 7
```

#### `batch`

Executa várias buscas descritas em um arquivo JSON.

```powershell
python .\p2p_search.py batch .\examples\ring.json .\examples\queries.json --seed 7 --csv .\results.csv
```

#### `dot`

Gera uma representação da rede no formato Graphviz DOT.

```powershell
python .\p2p_search.py dot .\examples\ring.json
```

#### `search` e `visualize`

Os comandos antigos `search` e `visualize` ainda funcionam, mas o modo simples é o recomendado.

Exemplo equivalente ao modo simples:

```powershell
python .\p2p_search.py search .\examples\ring.json --node n1 --resource r4 --ttl 3 --algo flooding
```

```powershell
python .\p2p_search.py visualize .\examples\ring.json --node n1 --resource r4 --ttl 3 --algo flooding --output .\visualization.html
```

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

## Rastros e estatísticas

O simulador gera rastros textuais com `--trace`. Cada linha do rastro mostra:

- número do evento;
- `search_id`;
- `round`, que indica a rodada simultânea da mensagem;
- tipo da mensagem, como `request`, `reply` ou `direct`;
- nó de origem;
- nó de destino;
- recurso procurado;
- TTL restante.

Exemplo de rastro:

```text
trace:
  1. search_id=s1 round=1 request n1 -> n2 resource=r4 ttl=2
  2. search_id=s1 round=1 request n1 -> n6 resource=r4 ttl=2
  3. search_id=s1 round=2 request n2 -> n3 resource=r4 ttl=1
  4. search_id=s1 round=2 request n6 -> n5 resource=r4 ttl=1
  5. search_id=s1 round=3 request n3 -> n4 resource=r4 ttl=0
  6. search_id=s1 round=3 request n5 -> n4 resource=r4 ttl=0
  7. search_id=s1 round=3 reply n4 -> n1 resource=r4 ttl=-
```

Os comandos `compare` e `batch` também imprimem estatísticas agregadas por algoritmo:

- `runs`: quantidade de execuções;
- `found`: quantidade de buscas bem-sucedidas;
- `success`: taxa de sucesso;
- `avg_msg`: média de mensagens;
- `avg_nodes`: média de nós envolvidos;
- `min_msg`: menor quantidade de mensagens;
- `max_msg`: maior quantidade de mensagens.

## Visualização do grafo

O comando `visualize` gera três arquivos: um HTML, um CSS e um JavaScript. Eles não dependem de bibliotecas externas; basta abrir o arquivo `.html` no navegador, mantendo o `.css` e o `.js` na mesma pasta.

A visualização mostra:

- todos os nós da rede em um layout calculado a partir da topologia do arquivo;
- todas as relações de vizinhança configuradas como arestas do grafo;
- o nó inicial;
- o nó que possui o recurso procurado, mesmo quando a busca não encontra esse nó;
- as mensagens reais de requisição e resposta animadas sobre o grafo;
- as mensagens simultâneas da mesma rodada se movendo em paralelo;
- a lista de recursos por nó;
- as métricas finais da busca.

O SVG é montado pela estrutura geral da rede, usando somente os nós e as arestas do arquivo de configuração. O resultado da busca não define a forma do grafo; ele apenas destaca o nó inicial, o nó que possui o recurso e as mensagens durante a animação. Assim, mesmo no `random_walk`, os nós que não participaram da busca continuam aparecendo normalmente.

Na animação, o botão `Avançar` passa um quadro por vez, `Reproduzir` executa automaticamente e `Reiniciar` volta para o início. Um quadro pode conter várias mensagens quando elas pertencem à mesma rodada do `flooding`. Por exemplo, se `n1` envia para `n2` e `n6` na rodada 1, as duas mensagens aparecem ao mesmo tempo.

O painel `Mensagens` fica no topo da lateral da visualização. Ele começa vazio e adiciona as mensagens conforme a animação avança, destacando a mensagem ou o conjunto de mensagens do quadro atual.

O selo de status fica no canto superior direito do grafo. Ele começa como `EXPLORANDO` e só muda para `ENCONTRADO` ou `NÃO ENCONTRADO` quando a animação chega ao último quadro.

Nas buscas `informed_flooding` e `informed_random_walk`, a visualização também mostra o painel `Caches dos nós`. Ele lista quais nós intermediários têm cache para o recurso procurado e destaca quando uma entrada de cache foi usada pela busca. No grafo, esses nós recebem um anel em cor de cache, e a conexão direta criada até o nó final aparece como uma mensagem própria.

## Verificação manual

O arquivo de testes automatizados foi removido da entrega. Para conferir o funcionamento do projeto, use os comandos principais:

```powershell
python .\p2p_search.py validate .\examples\mesh.yaml
python .\p2p_search.py .\examples\mesh.yaml n1 r5 --ttl 5 --algo informed_flooding --trace --visualize .\visualization.html
python .\p2p_search.py .\examples\complex.yaml n2 r13 --ttl 5 --algo informed_flooding --trace --visualize .\visualization.html
```

Essas execuções validam a rede, executam buscas com cache intermediário, mostram o rastro textual e geram a visualização em HTML, CSS e JavaScript.

## Observações

- O identificador dos nós segue o padrão `n1`, `n2`, `n3` até `num_nodes`.
- O TTL representa o número máximo de saltos que uma requisição pode realizar.
- O `random_walk` aceita `--seed` para tornar os testes e demonstrações reprodutíveis.
- Recursos não são replicados: cada `resource_id` pertence a um único nó.
- As buscas informadas usam cache por padrão, mas podem ser executadas com `--ignore-cache`.
- O projeto ignora arquivos gerados, como `results.csv`, `visualization.html`, `visualization.htm`, `visualization.css`, `visualization.js` e `__pycache__`.
