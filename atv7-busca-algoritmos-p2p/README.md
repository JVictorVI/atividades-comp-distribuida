# Implementação de Algoritmos de Busca em Sistemas P2P

Projeto desenvolvido para a atividade de Computação Distribuída sobre algoritmos de busca em redes peer-to-peer (P2P) não estruturadas.

O programa lê uma rede P2P em YAML, valida a topologia e executa buscas por recursos usando duas estratégias, com cache opcional:

- `flooding`
- `random_walk`

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
  stress.yaml
  ring.yaml
  complex_queries.json
  queries.json
  stress_queries.json
  stress_results.json
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

### Random Walk

A busca por passeio aleatório escolhe apenas um vizinho por vez. Quando chega a um nó sem vizinhos ainda não visitados, ela faz backtracking pelo caminho já percorrido para tentar outra ramificação. Cada avanço ou retorno conta como mensagem, mas apenas avanços para vizinhos ainda não visitados consomem TTL.

No terminal, é possível informar `--seed` para repetir uma execução. Na interface, a seed é escolhida automaticamente por baixo dos panos. O botão `Novo exemplo random` sorteia outra execução para os algoritmos random.

### Uso de cache

Tanto `flooding` quanto `random_walk` podem consultar caches locais. Na interface, o botão `Usar cache` decide se a busca deve considerar essas informações. No terminal, o cache fica ativo por padrão e pode ser desativado com `--ignore-cache`.

Quando o cache está ativo, os nós intermediários também consultam seus caches locais. Se um nó souber onde está o recurso, ele avisa diretamente o nó inicial e a visualização mostra uma conexão direta até o nó que possui o recurso.

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
    "visualize": None,
}
```

Depois execute:

```powershell
python .\p2p_search.py
```

Isso executa apenas a busca no terminal. Os arquivos `visualization.html`, `visualization.css` e `visualization.js` ficam fixos e não são regenerados a cada execução.

Para regenerar a interface somente quando necessário, defina `"visualize": "visualization.html"` no objeto `BUSCA` ou use o comando `visualize`.

### Abrir a interface

Abra o arquivo `visualization.html` no navegador.

Na interface você pode:

- escolher um mesh pelo seletor com os YAMLs da pasta `examples`;
- editar `num_nodes`, `min_neighbors`, `max_neighbors`, recursos, arestas e caches;
- escolher o algoritmo;
- ligar ou desligar o uso de cache;
- escolher o nó inicial, o recurso e o TTL;
- executar uma nova busca;
- gerar outro exemplo para versões random;
- ver erros de validação diretamente na tela;
- acompanhar a animação das mensagens.

A própria interface também contém um tutorial resumido de uso.

Para que o seletor de redes detecte automaticamente novos arquivos `.yaml` criados em `examples/`, abra a interface por um servidor local:

```powershell
python -m http.server 8000
```

Depois acesse `http://localhost:8000/visualization.html`. Ao abrir a página ou clicar no seletor de redes, a interface tenta reler a pasta `examples/` e carregar todos os YAMLs disponíveis. Se o HTML for aberto diretamente como arquivo (`file://`), o navegador bloqueia a leitura da pasta por segurança e a interface usa a lista de redes embutida no `visualization.js`.

### Busca direta

```powershell
python .\p2p_search.py .\examples\mesh.yaml n1 r5 --ttl 4 --algo flooding --trace --visualize
```

### Comparar os dois algoritmos

```powershell
python .\p2p_search.py compare .\examples\complex.yaml --node n1 --resource r13 --ttl 4
```

### Execução em lote

O comando `batch` recebe uma rede em YAML e uma lista de buscas em JSON:

```powershell
python .\p2p_search.py batch .\examples\complex.yaml .\examples\complex_queries.json --seed 7 --csv results.csv
```

O arquivo JSON nesse caso contém consultas, não a estrutura da rede.

## Testes e métricas coletadas

Para coletar métricas em uma rede maior, foi criada a topologia `examples/stress.yaml`, com 20 nós, grau mínimo 2, grau máximo 5, caminhos alternativos e caches em nós intermediários.

As consultas de teste estão em `examples/stress_queries.json`. Elas variam:

- algoritmo: `flooding` e `random_walk`;
- uso de cache: ligado e desligado com `ignore_cache`;
- TTL: valores baixos e altos;
- nó inicial;
- recurso procurado.

As métricas coletadas foram:

- sucesso da busca;
- quantidade de mensagens;
- quantidade de nós envolvidos;
- tamanho do caminho;
- origem do resultado (`local` ou `cache`);
- quantidade de acertos via cache;
- taxa de sucesso por grupo.

Os resultados completos foram salvos em `examples/stress_results.json`. Para evitar contaminação entre execuções, cada teste do JSON foi coletado reinicializando a rede antes da busca; assim, caches aprendidos em uma execução não alteram as próximas.

Para executar a mesma lista de consultas no terminal:

```powershell
python .\p2p_search.py batch .\examples\stress.yaml .\examples\stress_queries.json --seed 42
```

Resumo dos resultados com `seed_base = 42`, 4 cenários e 10 execuções por cenário:

| Algoritmo | Cache | Execuções | Encontrados | Sucesso | Média mensagens | Média nós | Média caminho | Hits cache |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| flooding | não | 10 | 4 | 40.00% | 24.20 | 13.40 | 0.90 | 0 |
| flooding | sim | 10 | 10 | 100.00% | 25.50 | 14.00 | 2.30 | 7 |
| random_walk | não | 10 | 1 | 10.00% | 5.00 | 5.90 | 4.90 | 0 |
| random_walk | sim | 10 | 4 | 40.00% | 5.10 | 5.70 | 4.70 | 2 |

Resultados detalhados:

| # | Algoritmo | Cache | TTL | Nó inicial | Recurso | Encontrou | Mensagens | Nós envolvidos | Caminho | Encontrado via |
|---:|---|---:|---:|---|---|---|---:|---:|---|---|
| 1 | flooding | sim | 2 | n11 | r4 | sim | 19 | 14 | n11 -> n16 -> n4 | cache |
| 2 | flooding | sim | 2 | n2 | r19 | sim | 18 | 13 | n2 -> n12 -> n13 -> n19 | cache |
| 3 | flooding | sim | 2 | n14 | r8 | sim | 18 | 13 | n14 -> n13 -> n18 -> n8 | cache |
| 4 | flooding | sim | 1 | n15 | r10 | sim | 6 | 6 | n15 -> n20 -> n10 | cache |
| 5 | flooding | sim | 2 | n6 | r12 | sim | 19 | 14 | n6 -> n5 -> n12 | cache |
| 6 | flooding | sim | 1 | n4 | r2 | sim | 6 | 6 | n4 -> n9 -> n2 | cache |
| 7 | flooding | sim | 3 | n1 | r14 | sim | 43 | 20 | n1 -> n20 -> n15 -> n14 | local |
| 8 | flooding | sim | 6 | n18 | r3 | sim | 64 | 20 | n18 -> n13 -> n3 | local |
| 9 | flooding | sim | 3 | n12 | r4 | sim | 40 | 20 | n12 -> n11 -> n16 -> n4 | cache |
| 10 | flooding | sim | 2 | n20 | r10 | sim | 22 | 14 | n20 -> n10 | local |
| 11 | flooding | não | 2 | n11 | r4 | não | 17 | 13 | n11 | - |
| 12 | flooding | não | 2 | n2 | r19 | não | 16 | 12 | n2 | - |
| 13 | flooding | não | 2 | n14 | r8 | não | 16 | 12 | n14 | - |
| 14 | flooding | não | 1 | n15 | r10 | não | 4 | 5 | n15 | - |
| 15 | flooding | não | 2 | n6 | r12 | não | 17 | 13 | n6 | - |
| 16 | flooding | não | 1 | n4 | r2 | não | 4 | 5 | n4 | - |
| 17 | flooding | não | 3 | n1 | r14 | sim | 43 | 20 | n1 -> n20 -> n15 -> n14 | local |
| 18 | flooding | não | 6 | n18 | r3 | sim | 64 | 20 | n18 -> n13 -> n3 | local |
| 19 | flooding | não | 3 | n12 | r4 | sim | 39 | 20 | n12 -> n13 -> n14 -> n4 | local |
| 20 | flooding | não | 2 | n20 | r10 | sim | 22 | 14 | n20 -> n10 | local |
| 21 | random_walk | sim | 5 | n11 | r4 | sim | 6 | 6 | n11 -> n10 -> n20 -> n15 -> n16 -> n4 | cache |
| 22 | random_walk | sim | 5 | n2 | r19 | não | 5 | 6 | n2 -> n7 -> n6 -> n16 -> n17 -> n18 | - |
| 23 | random_walk | sim | 5 | n14 | r8 | sim | 4 | 4 | n14 -> n4 -> n3 -> n8 | local |
| 24 | random_walk | sim | 5 | n15 | r10 | não | 5 | 6 | n15 -> n5 -> n4 -> n3 -> n8 -> n18 | - |
| 25 | random_walk | sim | 5 | n6 | r12 | não | 5 | 6 | n6 -> n1 -> n2 -> n3 -> n13 -> n14 | - |
| 26 | random_walk | sim | 5 | n4 | r2 | sim | 7 | 7 | n4 -> n14 -> n13 -> n18 -> n19 -> n9 -> n2 | cache |
| 27 | random_walk | sim | 3 | n1 | r14 | não | 3 | 4 | n1 -> n6 -> n7 -> n8 | - |
| 28 | random_walk | sim | 6 | n18 | r3 | não | 6 | 7 | n18 -> n13 -> n12 -> n11 -> n1 -> n6 -> n5 | - |
| 29 | random_walk | sim | 6 | n12 | r4 | sim | 5 | 5 | n12 -> n11 -> n10 -> n9 -> n4 | local |
| 30 | random_walk | sim | 5 | n20 | r10 | não | 5 | 6 | n20 -> n15 -> n5 -> n6 -> n1 -> n2 | - |
| 31 | random_walk | não | 5 | n11 | r4 | não | 5 | 6 | n11 -> n1 -> n6 -> n7 -> n17 -> n16 | - |
| 32 | random_walk | não | 5 | n2 | r19 | sim | 5 | 5 | n2 -> n3 -> n13 -> n18 -> n19 | local |
| 33 | random_walk | não | 5 | n14 | r8 | não | 5 | 6 | n14 -> n13 -> n18 -> n17 -> n16 -> n15 | - |
| 34 | random_walk | não | 5 | n15 | r10 | não | 5 | 6 | n15 -> n5 -> n6 -> n16 -> n17 -> n12 | - |
| 35 | random_walk | não | 5 | n6 | r12 | não | 5 | 6 | n6 -> n5 -> n15 -> n16 -> n11 -> n10 | - |
| 36 | random_walk | não | 5 | n4 | r2 | não | 5 | 6 | n4 -> n5 -> n15 -> n14 -> n13 -> n12 | - |
| 37 | random_walk | não | 3 | n1 | r14 | não | 3 | 4 | n1 -> n2 -> n12 -> n13 | - |
| 38 | random_walk | não | 6 | n18 | r3 | não | 6 | 7 | n18 -> n17 -> n16 -> n20 -> n10 -> n11 -> n1 | - |
| 39 | random_walk | não | 6 | n12 | r4 | não | 6 | 7 | n12 -> n17 -> n18 -> n8 -> n9 -> n19 -> n20 | - |
| 40 | random_walk | não | 5 | n20 | r10 | não | 5 | 6 | n20 -> n19 -> n18 -> n17 -> n7 -> n8 | - |

Nos testes, cada cenário teve exatamente 10 execuções. O cache aumentou a taxa de sucesso dos dois algoritmos: no `flooding`, de 40.00% para 100.00%; no `random_walk`, de 10.00% para 40.00%. O `flooding` alcançou mais recursos, mas com custo médio de mensagens bem maior que o `random_walk`.

## Comandos disponíveis

- `search`: executa uma busca.
- `compare`: executa os dois algoritmos para a mesma consulta.
- `batch`: executa várias buscas descritas em JSON.
- `visualize`: gera a interface HTML de visualização.

## Observações

- A rede usa arestas não direcionadas.
- A relação de vizinhança não é transitiva.
- Cada nó conhece seus recursos locais e seus vizinhos.
- Não há replicação de recursos: um mesmo recurso não pode aparecer em mais de um nó.
- O cache é opcional e pode ser ignorado com `--ignore-cache`.
- A interface mostra quais nós têm cache relevante para o recurso procurado quando isso existe.
