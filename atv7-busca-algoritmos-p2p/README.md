# Implementação de Algoritmos de Busca em Sistemas P2P

Projeto desenvolvido para a atividade de Computação Distribuída sobre algoritmos de busca em redes peer-to-peer (P2P) não estruturadas.

O programa lê uma rede P2P em YAML, valida a topologia e executa buscas por recursos usando quatro estratégias:

- `flooding`
- `informed_flooding`
- `random_walk`
- `informed_random_walk`

Ao final de cada busca, o programa informa se o recurso foi encontrado, qual nó respondeu, o caminho percorrido, o total de mensagens trocadas e o total de nós envolvidos.

## Objetivo

O objetivo é simular como diferentes algoritmos localizam recursos em uma rede P2P sem servidor central e sem índice global. A rede é representada como um grafo não direcionado: cada nó possui recursos próprios, conhece apenas seus vizinhos e pode manter informações em cache.

Com isso, é possível comparar o custo de cada algoritmo em mensagens trafegadas e nós envolvidos na busca.

## Estrutura do projeto

```text
p2p_search.py
p2p/
  __init__.py
  cli.py
  config.py
  models.py
  network.py
  output.py
  visualization.py
  assets/
    visualization_app.css
    visualization_app.js
examples/
  complex.yaml
  mesh.yaml
  ring.yaml
  complex_queries.json
  queries.json
README.md
Trabalho 7 – Implementação de Algoritmos de Busca em Sistemas P2P.pdf
```

Principais arquivos:

- `p2p_search.py`: entrada principal. O objeto `BUSCA` pode ser alterado diretamente para executar uma busca sem montar comandos longos.
- `p2p/config.py`: leitura dos arquivos YAML de rede.
- `p2p/network.py`: validação da rede, cache e algoritmos de busca.
- `p2p/output.py`: formatação dos resultados, rastros textuais, tabelas e estatísticas.
- `p2p/visualization.py`: geração da interface HTML, CSS e JavaScript.
- `p2p/cli.py`: comandos de terminal, modo direto, comparação, lote e visualização.
- `examples/*.yaml`: redes P2P usadas como exemplos.
- `examples/*_queries.json` e `examples/queries.json`: listas de buscas para o comando `batch`. Esses arquivos não descrevem a rede.

## Formato da rede

A estrutura da rede é lida somente em YAML (`.yaml` ou `.yml`). Arquivos JSON não são aceitos como configuração de rede.

Exemplo:

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
  - n1, n2
  - n2, n3
```

Campos:

- `num_nodes`: quantidade de nós da rede. Os nós são criados como `n1`, `n2`, `n3` etc.
- `min_neighbors`: quantidade mínima de vizinhos que cada nó deve ter.
- `max_neighbors`: quantidade máxima de vizinhos que cada nó pode ter.
- `resources`: recursos existentes em cada nó. Nenhum nó pode ficar sem recurso.
- `caches`: bloco opcional com conhecimento prévio no formato `recurso=nó`.
- `edges`: arestas não direcionadas entre os nós.

## Validações

O projeto atende aos Requisitos II do enunciado. Ao carregar a rede, o programa valida:

- a rede não pode estar particionada;
- deve existir caminho entre quaisquer dois nós;
- todos os nós devem respeitar `min_neighbors` e `max_neighbors`;
- nenhum nó pode ficar sem recursos;
- não pode haver aresta de um nó para ele mesmo.

Além disso, a implementação também verifica:

- referências a nós desconhecidos em `resources`, `edges` e `caches`;
- recursos duplicados em mais de um nó;
- caches apontando para recursos inexistentes;
- caches apontando para nós que não possuem o recurso indicado;
- campos obrigatórios ausentes ou inválidos.

Essas validações são feitas tanto no backend Python quanto na interface, quando o usuário edita o mesh manualmente ou escolhe um YAML pelo seletor.

## Algoritmos

### Flooding

A busca por inundação envia a requisição para todos os vizinhos em paralelo, respeitando o TTL. A simulação ocorre em rodadas: na primeira rodada o nó inicial envia para seus vizinhos; nas próximas rodadas, os nós alcançados continuam propagando a requisição enquanto ainda houver TTL.

Quando um nó encontra o recurso, ele avisa diretamente o nó inicial. Mesmo assim, a propagação paralela não é interrompida imediatamente: as mensagens continuam avançando pelos ramos válidos até o TTL chegar a zero ou não haver novos nós para visitar.

O `search_id` evita ciclos, impedindo que um nó processe a mesma busca mais de uma vez.

### Informed Flooding

Funciona como o `flooding`, mas os nós intermediários também consultam seus caches locais. Se um nó intermediário souber onde está o recurso, ele avisa diretamente o nó inicial e a visualização mostra uma conexão direta até o nó que possui o recurso.

Assim como no `flooding`, encontrar o recurso não interrompe toda a propagação paralela antes do TTL acabar.

### Random Walk

A busca por passeio aleatório escolhe apenas um vizinho por vez. Ela gera menos mensagens que o flooding, mas pode não encontrar o recurso mesmo quando ele existe na rede, porque o caminho depende das escolhas aleatórias e do TTL.

No terminal, é possível informar `--seed` para repetir uma execução. Na interface, a seed é escolhida automaticamente por baixo dos panos. O botão `Novo exemplo random` sorteia outra execução para os algoritmos random.

### Informed Random Walk

Funciona como o `random_walk`, mas os nós visitados também consultam o cache local antes de sortear o próximo vizinho. Se um cache indicar onde está o recurso, o nó intermediário responde diretamente ao solicitante e a simulação mostra a conexão direta até o nó final.

## Como executar

Use Python 3 no terminal dentro da pasta do projeto.

### Execução principal

O jeito mais simples é editar o objeto `BUSCA` no arquivo `p2p_search.py`:

```python
BUSCA = {
    "config": "examples/complex.yaml",
    "node_id": "n1",
    "resource_id": "r5",
    "ttl": 3,
    "algo": "flooding",
    "seed": None,
    "ignore_cache": False,
    "trace": True,
    "visualize": "visualization.html",
}
```

Depois execute:

```powershell
python .\p2p_search.py
```

Isso executa a busca e gera `visualization.html`, `visualization.css` e `visualization.js`.

### Abrir a interface

Depois de executar o comando principal, abra o arquivo `visualization.html` no navegador.

Na interface você pode:

- escolher um mesh pelo seletor com os YAMLs da pasta `examples`;
- editar `num_nodes`, `min_neighbors`, `max_neighbors`, recursos, arestas e caches;
- escolher o algoritmo;
- escolher o nó inicial, o recurso e o TTL;
- executar uma nova busca;
- gerar outro exemplo para versões random;
- ver erros de validação diretamente na tela;
- acompanhar a animação das mensagens.

A própria interface também contém um tutorial resumido de uso.


### Busca direta

```powershell
python .\p2p_search.py .\examples\mesh.yaml n1 r5 --ttl 4 --algo flooding --trace --visualize
```

### Comparar os quatro algoritmos

```powershell
python .\p2p_search.py compare .\examples\complex.yaml --node n1 --resource r13 --ttl 4
```

### Execução em lote

O comando `batch` recebe uma rede em YAML e uma lista de buscas em JSON:

```powershell
python .\p2p_search.py batch .\examples\complex.yaml .\examples\complex_queries.json --seed 7 --csv results.csv
```

O arquivo JSON nesse caso contém consultas, não a estrutura da rede.

## Comandos disponíveis

- `search`: executa uma busca.
- `compare`: executa os quatro algoritmos para a mesma consulta.
- `batch`: executa várias buscas descritas em JSON.
- `visualize`: gera a interface HTML de visualização.

## Observações

- A rede usa arestas não direcionadas.
- A relação de vizinhança não é transitiva.
- Cada nó conhece seus recursos locais e seus vizinhos.
- Não há replicação de recursos: um mesmo recurso não pode aparecer em mais de um nó.
- O cache é opcional e pode ser ignorado com `--ignore-cache`.
- A interface mostra quais nós têm cache relevante para o recurso procurado quando isso existe.
