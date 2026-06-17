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
  stress_queries.json
  stress_results.json
visualization.html
visualization.css
visualization.js
README.md
```

Principais arquivos:

- `p2p_search.py`: entrada principal. O objeto `BUSCA` pode ser alterado diretamente para executar uma busca sem montar comandos longos.
- `p2p/config.py`: leitura dos arquivos YAML de rede.
- `p2p/network.py`: validação da rede, cache e algoritmos de busca.
- `p2p/output.py`: formatação dos resultados, rastros textuais, tabelas e estatísticas.
- `p2p/visualization.py`: geração da interface HTML, CSS e JavaScript.
- `p2p/cli.py`: comandos de terminal, modo direto, comparação, lote e visualização.
- `examples/*.yaml`: redes P2P usadas como exemplos.
- `examples/stress_queries.json`: lista com as 60 consultas usadas nos testes e aceita pelo comando `batch`.
- `examples/stress_results.json`: resultados detalhados e métricas agregadas dos testes.
- `visualization.html`, `visualization.css` e `visualization.js`: interface pronta para abrir no navegador.

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

Quando um nó encontra o recurso, ele avisa diretamente o nó inicial e não encaminha mais a requisição para seus vizinhos. Os outros ramos da inundação continuam avançando pelos caminhos válidos até o TTL chegar a zero ou não haver novos nós para visitar.

Um conjunto de nós já processados evita ciclos e impede que o mesmo nó propague repetidamente a mesma busca. O `search_id` identifica a execução nos resultados e eventos do rastro.

### Random Walk

A busca por passeio aleatório escolhe apenas um vizinho por vez. Quando chega a um nó sem vizinhos ainda não visitados, ela faz backtracking pelo caminho já percorrido para tentar outra ramificação. Se o TTL zerar em um ramo e ainda houver vizinhos restantes em níveis anteriores, a busca volta pelo caminho e restaura o TTL restante daquele nível, sem ultrapassar a profundidade permitida pelo TTL original. Cada avanço ou retorno conta como mensagem, mas apenas avanços para vizinhos ainda não visitados consomem TTL. Por isso, o caminho completo registrado pode ter mais movimentos que o TTL, embora nenhum ramo ultrapasse a profundidade permitida.

No terminal, é possível informar `--seed` para repetir uma execução. Na interface, a seed é escolhida automaticamente por baixo dos panos. O botão `Novo exemplo random` sorteia outro percurso para o `random_walk`.

### Uso de cache

Tanto `flooding` quanto `random_walk` podem consultar os caches dos nós intermediários alcançados. Na interface, o botão `Usar cache` decide se a busca deve considerar essas informações. No terminal, o cache fica ativo por padrão e pode ser desativado com `--ignore-cache`.

Se um nó intermediário souber onde está o recurso, ele avisa diretamente o nó inicial e a visualização mostra uma conexão direta até o nó que possui o recurso. Após uma busca bem-sucedida, o nó inicial também registra a localização encontrada em seu cache, que poderá ser usada caso ele participe como intermediário de outra busca.

## Como executar

Use Python 3 no terminal dentro da pasta do projeto.

### Execução principal

O jeito mais simples é editar o objeto `BUSCA` no arquivo `p2p_search.py`:

```python
BUSCA = {
    "config": "examples/mesh.yaml",
    "node_id": "n1",
    "resource_id": "r5",
    "ttl": 6,
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
- gerar outro percurso para buscas `random_walk`;
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
python .\p2p_search.py batch .\examples\stress.yaml .\examples\stress_queries.json --seed 42 --csv results.csv
```

O arquivo JSON contém consultas, não a estrutura da rede. No comando `batch`, a mesma instância da rede é usada durante todo o lote; portanto, caches aprendidos por uma busca podem influenciar buscas posteriores.

## Testes e métricas coletadas

Para coletar métricas em uma rede maior, foi criada a topologia `examples/stress.yaml`, com 20 nós, grau mínimo 2, grau máximo 5, caminhos alternativos e caches em nós intermediários.

As consultas de teste estão em `examples/stress_queries.json`. Elas variam:

- algoritmo: `flooding` e `random_walk`;
- uso de cache: ligado e desligado com `ignore_cache`;
- TTL: valores baixos e altos;
- nó inicial;
- recurso procurado.

O arquivo possui 60 consultas, divididas em quatro cenários com 15 execuções cada: `flooding` e `random_walk`, ambos com cache ligado e desligado.

As métricas coletadas foram:

- sucesso da busca;
- quantidade de mensagens;
- quantidade de nós envolvidos;
- tamanho do caminho, contado pelo número de transições registradas;
- origem do resultado (`local` ou `cache`);
- quantidade de acertos via cache;
- taxa de sucesso por grupo.

Os resultados completos foram salvos em `examples/stress_results.json`. Para evitar contaminação entre execuções, cada teste foi coletado reinicializando a rede antes da busca; assim, caches aprendidos em uma execução não alteram as próximas. Essa coleta isolada difere do comportamento normal do comando `batch`, que reutiliza a rede durante o lote.

Para executar a lista de consultas em lote no terminal:

```powershell
python .\p2p_search.py batch .\examples\stress.yaml .\examples\stress_queries.json --seed 42
```

Esse comando é útil para uma execução operacional do lote, mas pode produzir resultados diferentes dos registrados em `stress_results.json` devido ao aprendizado de cache entre consultas.

Resumo dos resultados com `seed_base = 42`, 4 cenários e 15 execuções por cenário:

| Algoritmo   | Cache | Execuções | Encontrados | Sucesso | Média mensagens | Média nós | Média caminho | Hits cache |
| ----------- | ----: | --------: | ----------: | ------: | --------------: | --------: | ------------: | ---------: |
| flooding    |   não |        15 |           4 |  26.67% |           17.07 |     10.60 |          0.60 |          0 |
| flooding    |   sim |        15 |          15 | 100.00% |           17.87 |     11.13 |          2.20 |         12 |
| random_walk |   não |        15 |          14 |  93.33% |           18.40 |     11.67 |         17.47 |          0 |
| random_walk |   sim |        15 |          15 | 100.00% |           14.27 |      9.80 |         13.27 |          7 |

Resultados detalhados:

|   # | Algoritmo   | Cache | TTL | Nó inicial | Recurso | Encontrou | Mensagens | Nós envolvidos | Caminho                                                                                                                                                                                                                                  | Encontrado via |
| --: | ----------- | ----: | --: | ---------- | ------- | --------- | --------: | -------------: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
|   1 | flooding    |   sim |   2 | n11        | r4      | sim       |        15 |             13 | n11 -> n16 -> n4                                                                                                                                                                                                                         | cache          |
|   2 | flooding    |   sim |   2 | n2         | r19     | sim       |        18 |             13 | n2 -> n12 -> n13 -> n19                                                                                                                                                                                                                  | cache          |
|   3 | flooding    |   sim |   2 | n14        | r8      | sim       |        18 |             13 | n14 -> n13 -> n18 -> n8                                                                                                                                                                                                                  | cache          |
|   4 | flooding    |   sim |   1 | n15        | r10     | sim       |         6 |              6 | n15 -> n20 -> n10                                                                                                                                                                                                                        | cache          |
|   5 | flooding    |   sim |   2 | n6         | r12     | sim       |        16 |             12 | n6 -> n5 -> n12                                                                                                                                                                                                                          | cache          |
|   6 | flooding    |   sim |   1 | n4         | r2      | sim       |         6 |              6 | n4 -> n9 -> n2                                                                                                                                                                                                                           | cache          |
|   7 | flooding    |   sim |   3 | n1         | r14     | sim       |        43 |             20 | n1 -> n20 -> n15 -> n14                                                                                                                                                                                                                  | local          |
|   8 | flooding    |   sim |   6 | n18        | r3      | sim       |        61 |             20 | n18 -> n13 -> n3                                                                                                                                                                                                                         | local          |
|   9 | flooding    |   sim |   3 | n12        | r4      | sim       |        36 |             20 | n12 -> n11 -> n16 -> n4                                                                                                                                                                                                                  | cache          |
|  10 | flooding    |   sim |   2 | n20        | r10     | sim       |        19 |             14 | n20 -> n10                                                                                                                                                                                                                               | local          |
|  11 | flooding    |   sim |   1 | n6         | r18     | sim       |         6 |              6 | n6 -> n1 -> n18                                                                                                                                                                                                                          | cache          |
|  12 | flooding    |   sim |   1 | n8         | r20     | sim       |         6 |              6 | n8 -> n3 -> n20                                                                                                                                                                                                                          | cache          |
|  13 | flooding    |   sim |   1 | n2         | r15     | sim       |         6 |              6 | n2 -> n7 -> n15                                                                                                                                                                                                                          | cache          |
|  14 | flooding    |   sim |   1 | n12        | r6      | sim       |         6 |              6 | n12 -> n11 -> n6                                                                                                                                                                                                                         | cache          |
|  15 | flooding    |   sim |   1 | n12        | r19     | sim       |         6 |              6 | n12 -> n13 -> n19                                                                                                                                                                                                                        | cache          |
|  16 | flooding    |   não |   2 | n11        | r4      | não       |        17 |             13 | n11                                                                                                                                                                                                                                      | -              |
|  17 | flooding    |   não |   2 | n2         | r19     | não       |        16 |             12 | n2                                                                                                                                                                                                                                       | -              |
|  18 | flooding    |   não |   2 | n14        | r8      | não       |        16 |             12 | n14                                                                                                                                                                                                                                      | -              |
|  19 | flooding    |   não |   1 | n15        | r10     | não       |         4 |              5 | n15                                                                                                                                                                                                                                      | -              |
|  20 | flooding    |   não |   2 | n6         | r12     | não       |        17 |             13 | n6                                                                                                                                                                                                                                       | -              |
|  21 | flooding    |   não |   1 | n4         | r2      | não       |         4 |              5 | n4                                                                                                                                                                                                                                       | -              |
|  22 | flooding    |   não |   3 | n1         | r14     | sim       |        43 |             20 | n1 -> n20 -> n15 -> n14                                                                                                                                                                                                                  | local          |
|  23 | flooding    |   não |   6 | n18        | r3      | sim       |        61 |             20 | n18 -> n13 -> n3                                                                                                                                                                                                                         | local          |
|  24 | flooding    |   não |   3 | n12        | r4      | sim       |        39 |             20 | n12 -> n13 -> n14 -> n4                                                                                                                                                                                                                  | local          |
|  25 | flooding    |   não |   2 | n20        | r10     | sim       |        19 |             14 | n20 -> n10                                                                                                                                                                                                                               | local          |
|  26 | flooding    |   não |   1 | n6         | r18     | não       |         4 |              5 | n6                                                                                                                                                                                                                                       | -              |
|  27 | flooding    |   não |   1 | n8         | r20     | não       |         4 |              5 | n8                                                                                                                                                                                                                                       | -              |
|  28 | flooding    |   não |   1 | n2         | r15     | não       |         4 |              5 | n2                                                                                                                                                                                                                                       | -              |
|  29 | flooding    |   não |   1 | n12        | r6      | não       |         4 |              5 | n12                                                                                                                                                                                                                                      | -              |
|  30 | flooding    |   não |   1 | n12        | r19     | não       |         4 |              5 | n12                                                                                                                                                                                                                                      | -              |
|  31 | random_walk |   sim |   5 | n11        | r4      | sim       |         7 |              7 | n11 -> n1 -> n6 -> n7 -> n17 -> n16 -> n4                                                                                                                                                                                                | cache          |
|  32 | random_walk |   sim |   5 | n2         | r19     | sim       |         4 |              4 | n2 -> n3 -> n13 -> n19                                                                                                                                                                                                                   | cache          |
|  33 | random_walk |   sim |   5 | n14        | r8      | sim       |         4 |              4 | n14 -> n13 -> n18 -> n8                                                                                                                                                                                                                  | cache          |
|  34 | random_walk |   sim |   5 | n15        | r10     | sim       |        14 |             10 | n15 -> n5 -> n6 -> n16 -> n17 -> n12 -> n17 -> n7 -> n17 -> n18 -> n17 -> n16 -> n11 -> n10                                                                                                                                              | local          |
|  35 | random_walk |   sim |   5 | n6         | r12     | sim       |         3 |              3 | n6 -> n5 -> n12                                                                                                                                                                                                                          | cache          |
|  36 | random_walk |   sim |   5 | n4         | r2      | sim       |        17 |             12 | n4 -> n5 -> n15 -> n14 -> n13 -> n12 -> n13 -> n18 -> n13 -> n3 -> n13 -> n14 -> n19 -> n20 -> n19 -> n9 -> n2                                                                                                                           | cache          |
|  37 | random_walk |   sim |   3 | n1         | r14     | sim       |        36 |             20 | n1 -> n2 -> n12 -> n13 -> n12 -> n17 -> n12 -> n11 -> n12 -> n2 -> n3 -> n4 -> n3 -> n8 -> n3 -> n2 -> n7 -> n6 -> n7 -> n2 -> n1 -> n20 -> n10 -> n5 -> n10 -> n9 -> n10 -> n20 -> n16 -> n15 -> n16 -> n20 -> n19 -> n18 -> n19 -> n14 | local          |
|  38 | random_walk |   sim |   6 | n18        | r3      | sim       |        31 |             18 | n18 -> n17 -> n16 -> n20 -> n10 -> n11 -> n1 -> n11 -> n12 -> n11 -> n10 -> n5 -> n15 -> n5 -> n6 -> n5 -> n4 -> n5 -> n10 -> n9 -> n19 -> n9 -> n8 -> n9 -> n10 -> n20 -> n16 -> n17 -> n7 -> n2 -> n3                                  | local          |
|  39 | random_walk |   sim |   6 | n12        | r4      | sim       |        12 |              9 | n12 -> n17 -> n18 -> n8 -> n9 -> n19 -> n20 -> n19 -> n14 -> n19 -> n9 -> n4                                                                                                                                                             | local          |
|  40 | random_walk |   sim |   5 | n20        | r10     | sim       |        28 |             17 | n20 -> n19 -> n18 -> n17 -> n7 -> n8 -> n7 -> n6 -> n7 -> n2 -> n7 -> n17 -> n12 -> n11 -> n12 -> n13 -> n12 -> n17 -> n16 -> n15 -> n16 -> n17 -> n18 -> n19 -> n9 -> n4 -> n5 -> n10                                                   | local          |
|  41 | random_walk |   sim |   5 | n6         | r18     | sim       |        19 |             12 | n6 -> n16 -> n20 -> n15 -> n14 -> n13 -> n14 -> n4 -> n14 -> n19 -> n14 -> n15 -> n5 -> n10 -> n5 -> n15 -> n20 -> n1 -> n18                                                                                                             | cache          |
|  42 | random_walk |   sim |   5 | n8         | r20     | sim       |        11 |              9 | n8 -> n9 -> n19 -> n14 -> n13 -> n18 -> n13 -> n12 -> n13 -> n3 -> n20                                                                                                                                                                   | cache          |
|  43 | random_walk |   sim |   5 | n2         | r15     | sim       |         5 |              5 | n2 -> n3 -> n13 -> n14 -> n15                                                                                                                                                                                                            | local          |
|  44 | random_walk |   sim |   5 | n12        | r6      | sim       |        12 |              9 | n12 -> n13 -> n3 -> n8 -> n18 -> n19 -> n18 -> n17 -> n18 -> n8 -> n7 -> n6                                                                                                                                                              | local          |
|  45 | random_walk |   sim |   5 | n12        | r19     | sim       |        11 |              8 | n12 -> n11 -> n16 -> n20 -> n1 -> n2 -> n1 -> n6 -> n1 -> n20 -> n19                                                                                                                                                                     | local          |
|  46 | random_walk |   não |   5 | n11        | r4      | sim       |        22 |             14 | n11 -> n10 -> n9 -> n19 -> n20 -> n1 -> n20 -> n16 -> n20 -> n15 -> n20 -> n19 -> n18 -> n8 -> n18 -> n13 -> n18 -> n17 -> n18 -> n19 -> n14 -> n4                                                                                       | local          |
|  47 | random_walk |   não |   5 | n2         | r19     | sim       |        31 |             18 | n2 -> n7 -> n17 -> n16 -> n15 -> n5 -> n15 -> n14 -> n15 -> n20 -> n15 -> n16 -> n6 -> n1 -> n6 -> n16 -> n11 -> n10 -> n11 -> n12 -> n11 -> n16 -> n17 -> n18 -> n8 -> n3 -> n8 -> n9 -> n8 -> n18 -> n19                               | local          |
|  48 | random_walk |   não |   5 | n14        | r8      | sim       |         4 |              4 | n14 -> n13 -> n3 -> n8                                                                                                                                                                                                                   | local          |
|  49 | random_walk |   não |   5 | n15        | r10     | sim       |         4 |              4 | n15 -> n16 -> n11 -> n10                                                                                                                                                                                                                 | local          |
|  50 | random_walk |   não |   5 | n6         | r12     | sim       |        36 |             20 | n6 -> n1 -> n20 -> n15 -> n5 -> n10 -> n5 -> n4 -> n5 -> n15 -> n16 -> n17 -> n16 -> n11 -> n16 -> n15 -> n14 -> n19 -> n14 -> n13 -> n14 -> n15 -> n20 -> n1 -> n2 -> n7 -> n8 -> n3 -> n8 -> n18 -> n8 -> n9 -> n8 -> n7 -> n2 -> n12  | local          |
|  51 | random_walk |   não |   5 | n4         | r2      | sim       |        13 |              9 | n4 -> n9 -> n8 -> n7 -> n6 -> n5 -> n6 -> n16 -> n6 -> n1 -> n6 -> n7 -> n2                                                                                                                                                              | local          |
|  52 | random_walk |   não |   3 | n1         | r14     | não       |        24 |             13 | n1 -> n6 -> n7 -> n8 -> n7 -> n2 -> n7 -> n17 -> n7 -> n6 -> n16 -> n15 -> n16 -> n11 -> n16 -> n20 -> n16 -> n6 -> n5 -> n10 -> n5 -> n4 -> n5 -> n6 -> n1                                                                              | -              |
|  53 | random_walk |   não |   6 | n18        | r3      | sim       |         5 |              5 | n18 -> n17 -> n12 -> n13 -> n3                                                                                                                                                                                                           | local          |
|  54 | random_walk |   não |   6 | n12        | r4      | sim       |        30 |             18 | n12 -> n13 -> n18 -> n17 -> n16 -> n11 -> n1 -> n11 -> n10 -> n11 -> n16 -> n15 -> n14 -> n15 -> n20 -> n15 -> n5 -> n15 -> n16 -> n6 -> n7 -> n6 -> n16 -> n17 -> n18 -> n8 -> n9 -> n19 -> n9 -> n4                                    | local          |
|  55 | random_walk |   não |   5 | n20        | r10     | sim       |         6 |              6 | n20 -> n15 -> n16 -> n6 -> n5 -> n10                                                                                                                                                                                                     | local          |
|  56 | random_walk |   não |   5 | n6         | r18     | sim       |        32 |             18 | n6 -> n16 -> n20 -> n15 -> n14 -> n4 -> n14 -> n13 -> n14 -> n19 -> n14 -> n15 -> n5 -> n10 -> n5 -> n15 -> n20 -> n1 -> n11 -> n12 -> n11 -> n1 -> n2 -> n7 -> n2 -> n3 -> n2 -> n1 -> n20 -> n16 -> n17 -> n18                         | local          |
|  57 | random_walk |   não |   5 | n8         | r20     | sim       |        11 |              8 | n8 -> n7 -> n6 -> n1 -> n2 -> n3 -> n2 -> n12 -> n2 -> n1 -> n20                                                                                                                                                                         | local          |
|  58 | random_walk |   não |   5 | n2         | r15     | sim       |        16 |             11 | n2 -> n7 -> n6 -> n1 -> n11 -> n10 -> n11 -> n12 -> n11 -> n16 -> n11 -> n1 -> n20 -> n19 -> n20 -> n15                                                                                                                                  | local          |
|  59 | random_walk |   não |   5 | n12        | r6      | sim       |        26 |             16 | n12 -> n13 -> n18 -> n19 -> n14 -> n4 -> n14 -> n15 -> n14 -> n19 -> n9 -> n10 -> n9 -> n8 -> n9 -> n19 -> n20 -> n16 -> n20 -> n1 -> n20 -> n19 -> n18 -> n17 -> n7 -> n6                                                               | local          |
|  60 | random_walk |   não |   5 | n12        | r19     | sim       |        16 |             11 | n12 -> n13 -> n3 -> n4 -> n5 -> n10 -> n5 -> n15 -> n5 -> n6 -> n5 -> n4 -> n9 -> n8 -> n9 -> n19                                                                                                                                        | local          |

## Conclusão

Os 60 testes mostram que o cache tem impacto decisivo quando o TTL é baixo. No `flooding`, a taxa de sucesso passou de 26.67% sem cache para 100.00% com cache, porque os nós intermediários conseguiram informar diretamente a localização de recursos que não seriam alcançados dentro do limite de propagação.

O `random_walk` com backtracking apresentou alta capacidade de localização mesmo sem cache, alcançando 93.33% de sucesso. Com cache, chegou a 100.00% e também reduziu o custo médio: de 18.40 para 14.27 mensagens, de 11.67 para 9.80 nós envolvidos e de 17.47 para 13.27 movimentos no caminho.

Assim, o `flooding` oferece busca ampla e previsível, mas depende mais do TTL ou de informações em cache para alcançar recursos distantes. O `random_walk` com backtracking explora a rede de forma mais seletiva e, neste conjunto de testes, obteve o melhor equilíbrio entre taxa de sucesso e custo médio quando combinado com cache.

## Observações

- A rede usa arestas não direcionadas.
- A relação de vizinhança não é transitiva.
- Cada nó conhece seus recursos locais e seus vizinhos.
- Não há replicação de recursos: um mesmo recurso não pode aparecer em mais de um nó.
- O cache é opcional e pode ser ignorado com `--ignore-cache`.
- A interface mostra quais nós têm cache relevante para o recurso procurado quando isso existe.
