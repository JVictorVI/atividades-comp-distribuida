# Trabalho 6 - Comparação de Tecnologias de Invocação de Serviços Remotos

Projeto com implementações em Python e JavaScript/Node.js para comparar SOAP, REST, GraphQL e gRPC usando o mesmo serviço de streaming de músicas. A comparação é feita com Locust, três cargas de usuários virtuais e gráficos gerados automaticamente a partir dos resultados.

Detalhes específicos da versão JavaScript ficam em `services/javascript/README.md`.

## Equipe

- João Victor da Silva Ferreira - 2314387
- Paulo Marconi Araújo Tomaz da Silva - 2310435

## Ambiente de execução

Os testes foram executados em uma máquina com as seguintes especificações:

| Componente          | Especificação       |
| ------------------- | ------------------- |
| Sistema operacional | Windows 11          |
| Processador         | Intel Core 5 210H   |
| Memória RAM         | 24 GB DDR5 5600 MHz |
| Armazenamento       | SSD de 1 TB         |

## Objetivo

O objetivo é comparar tecnologias de invocação remota em um mesmo domínio. Para manter a comparação justa, as quatro APIs de cada linguagem usam a mesma regra de negócio e a mesma base de dados em memória.

O serviço gerencia:

- Usuários.
- Músicas.
- Playlists.

A base inicial fica inteiramente em memória e já nasce com uma massa maior para os testes de carga:

| Entidade  | Quantidade inicial |
| --------- | -----------------: |
| Usuários  |                300 |
| Músicas   |                500 |
| Playlists |                400 |

Operações cobertas:

- Criar, consultar, alterar e remover usuários.
- Criar, consultar, alterar e remover músicas.
- Criar, consultar, alterar e remover playlists.
- Listar todas as playlists.
- Listar playlists de um usuário.
- Listar músicas de uma playlist.
- Listar playlists que contêm uma música.

## Tecnologias Comparadas

REST:

- Implementado com HTTP minimalista nas duas linguagens: `http.server` em Python e `node:http` em JavaScript.
- Usa URLs, JSON e métodos HTTP.
- Portas locais: `3000` em Python e `3100` em JavaScript.

GraphQL:

- Implementado com `graphql-core` e `http.server` na versão Python; na versão JavaScript, com a biblioteca `graphql` e `node:http`.
- Usa schema tipado e permite consultar exatamente os campos desejados.
- Endpoints locais: `http://localhost:3001/graphql` em Python e `http://localhost:3101/graphql` em JavaScript.

SOAP:

- Implementado com HTTP minimalista e XML nas duas linguagens: `http.server` em Python e `node:http` em JavaScript.
- Expõe endpoint SOAP, WSDL e validações adicionais de envelope, namespace, operação e campos.
- O custo extra de processamento XML pode ser ajustado com `SOAP_COMPLEXITY_PASSES`.
- Endpoints locais: `http://localhost:3002/soap` em Python e `http://localhost:3102/soap` em JavaScript.

gRPC:

- Implementado com `grpcio` em Python e com `@grpc/grpc-js` na versão JavaScript.
- Usa o contrato `proto/music.proto`.
- O Python usa código protobuf/gRPC gerado por `grpcio-tools`.
- O JavaScript usa `@grpc/proto-loader` para carregar o contrato `.proto` e delegar a serialização para a biblioteca gRPC.
- Portas locais: `50051` em Python e `55051` em JavaScript.

## Características de cada API

O projeto tem implementações em Python e JavaScript. Os exemplos conceituais abaixo usam Python por simplicidade, e a versão JavaScript fica organizada em `services/javascript/`.

### REST

REST, ou Representational State Transfer, foi formalizado por Roy Fielding em sua tese de doutorado em 2000. Ele não é um protocolo fechado, mas um estilo arquitetural para construção de sistemas distribuídos usando recursos, identificadores e operações padronizadas.

Características:

- Usa recursos identificados por URLs.
- Normalmente usa HTTP, JSON e métodos como `GET`, `POST`, `PUT`, `PATCH` e `DELETE`.
- É stateless, ou seja, cada requisição deve conter as informações necessárias para ser processada.
- É muito usado em APIs web e aplicações CRUD.

Vantagens:

- Simples de entender, testar e integrar.
- Compatível com navegadores, ferramentas HTTP e praticamente qualquer linguagem.
- Boa escolha para APIs públicas e serviços com operações bem definidas.

Desvantagens:

- Pode gerar excesso ou falta de dados em algumas consultas.
- Não possui contrato fortemente tipado por padrão.
- Pode exigir várias requisições para montar telas ou respostas mais relacionais.

Exemplo em Python:

```python
import requests

base_url = "http://localhost:3000"

response = requests.get(f"{base_url}/songs", timeout=5)
response.raise_for_status()

songs = response.json()
print(songs)
```

### GraphQL

GraphQL foi criado pelo Facebook em 2012 e disponibilizado publicamente em 2015. Ele surgiu para resolver problemas comuns em APIs REST usadas por aplicações móveis e web, principalmente o excesso de chamadas e o retorno de dados desnecessários.

Características:

- Usa um schema tipado.
- A API normalmente expõe um único endpoint.
- O cliente define quais campos deseja receber.
- Suporta consultas, mutações e composição de dados relacionados.

Vantagens:

- Reduz overfetching, quando a API retorna mais dados do que o necessário.
- Reduz underfetching, quando o cliente precisa fazer várias chamadas para montar uma resposta.
- Facilita a evolução da API por meio do schema.

Desvantagens:

- Possui maior complexidade de implementação.
- Consultas mal controladas podem ser custosas para o servidor.
- Cache HTTP tradicional tende a ser menos direto do que em REST.

Exemplo em Python:

```python
import requests

query = """
query {
  songs {
    id
    title
    artist
  }
}
"""

response = requests.post(
    "http://localhost:3001/graphql",
    json={"query": query},
    timeout=5,
)
response.raise_for_status()

payload = response.json()
print(payload["data"]["songs"])
```

### SOAP

SOAP, ou Simple Object Access Protocol, surgiu no fim da década de 1990 e foi padronizado pelo W3C. Ele foi muito usado em ambientes corporativos por oferecer uma forma mais formal de integração entre sistemas, baseada em XML e contratos.

Características:

- Usa mensagens XML estruturadas em envelopes SOAP.
- Pode ser descrito por WSDL.
- Costuma ser usado sobre HTTP, mas não depende exclusivamente dele.
- Tem forte presença em integrações corporativas e sistemas legados.

Vantagens:

- Possui contrato formal por WSDL.
- É adequado para cenários corporativos que exigem padronização rígida.
- Conta com padrões adicionais para segurança, transações e confiabilidade.

Desvantagens:

- É mais verboso por usar XML.
- Pode ser mais difícil de ler, testar e depurar manualmente.
- Em muitos cenários modernos, é mais pesado do que REST ou gRPC.

Exemplo em Python:

```python
import requests

envelope = """
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ListPlaylistSongs>
      <playlistId>p1</playlistId>
    </ListPlaylistSongs>
  </soap:Body>
</soap:Envelope>
"""

response = requests.post(
    "http://localhost:3002/soap",
    data=envelope.encode("utf-8"),
    headers={"Content-Type": "text/xml; charset=utf-8"},
    timeout=5,
)
response.raise_for_status()

print(response.text)
```

### gRPC

gRPC foi criado pelo Google e lançado publicamente em 2015, inspirado em uma tecnologia interna chamada Stubby. Ele usa HTTP/2 e Protocol Buffers para comunicação eficiente entre serviços.

Características:

- Usa arquivos `.proto` para definir serviços e mensagens.
- Usa Protocol Buffers como formato binário de serialização.
- Suporta chamadas unary, streaming do cliente, streaming do servidor e streaming bidirecional.
- É muito usado em comunicação entre microsserviços.

Vantagens:

- Alto desempenho e menor payload em comparação com formatos textuais.
- Contrato fortemente tipado pelo arquivo `.proto`.
- Bom suporte para geração de clientes em várias linguagens.

Desvantagens:

- É menos simples de testar diretamente pelo navegador.
- Exige ferramentas e clientes compatíveis com gRPC.
- Pode ser mais complexo para APIs públicas consumidas por clientes variados.

Exemplo em Python:

```python
import grpc

from music_service.generated import music_pb2, music_pb2_grpc

channel = grpc.insecure_channel("localhost:50051")

try:
    client = music_pb2_grpc.MusicStreamingStub(channel)
    response = client.ListSongs(music_pb2.Empty(), timeout=5)
    print(response.songs)
finally:
    channel.close()
```

No gRPC, o contrato em `proto/music.proto` é a fonte principal das mensagens e operações. A versão Python usa módulos gerados a partir desse contrato, enquanto a versão JavaScript carrega o mesmo arquivo `.proto` com a biblioteca oficial de gRPC para Node.js. Assim, a serialização Protocol Buffers fica sob responsabilidade das bibliotecas, não de código manual do projeto.

## Metodologia

O domínio compartilhado fica em:

```text
services/python/music_service/domain/music_store.py
```

Na versão JavaScript, a regra equivalente fica em:

```text
services/javascript/domain/musicStore.js
```

Esses módulos contêm:

- dados iniciais;
- validações;
- regras de criação, alteração, remoção e consulta;
- relações entre usuários, músicas e playlists.

Os servidores apenas adaptam suas chamadas para esse mesmo domínio em cada linguagem. Assim, a diferença entre REST, GraphQL, SOAP e gRPC fica concentrada no mecanismo de invocação remota, não na regra de negócio.

Os dados iniciais são gerados de forma determinística no código das duas linguagens. Não há banco de dados nem arquivo externo; ao reiniciar ou chamar `reset`, cada serviço volta para a mesma massa em memória com centenas de registros.

## Equivalência das Implementações

As implementações em Python e JavaScript são equivalentes em comportamento para o escopo do trabalho. As duas linguagens expõem as mesmas entidades, as mesmas operações de CRUD e os mesmos cenários de leitura em REST, GraphQL, SOAP e gRPC.

Foram mantidos os mesmos dados iniciais, as mesmas regras de validação e as mesmas relações entre usuários, músicas e playlists. Dessa forma, os testes de carga comparam principalmente o mecanismo de comunicação remota, a serialização e o servidor usado em cada linguagem, não diferenças na regra de negócio.

A estrutura segue boas práticas para um projeto acadêmico de comparação: serviços separados por linguagem, execução independente por API, contratos consistentes, dados em memória reiniciáveis e scripts automatizados para testes e gráficos. As APIs HTTP usam servidores minimalistas nas duas linguagens para reduzir diferenças de framework. O SOAP inclui validações e reprocessamento de XML para representar melhor o custo típico desse modelo. O gRPC usa a toolchain de Protocol Buffers em vez de serialização manual.

## Estrutura

```text
.
|-- docker-compose.yml
|-- locustfile.py
|-- proto/
|   `-- music.proto
|-- services/
|   |-- python/
|   |   |-- Dockerfile
|   |   |-- requirements.txt
|   |   `-- music_service/
|   |       |-- generated/
|   |       |-- http_utils.py
|   |       `-- servers/
|   `-- javascript/
|       |-- Dockerfile
|       |-- package.json
|       |-- domain/
|       `-- servers/
|-- scripts/
|   |-- run_python.ps1
|   |-- run_javascript.ps1
|   |-- run_all.ps1
|   |-- start_services/
|   |-- run_locust_scenarios.py
|   `-- generate_charts.py
`-- results/
```

Arquivos importantes:

- `services/python/Dockerfile`: imagem Python usada pelos servidores Python, Locust e gráficos.
- `services/javascript/Dockerfile`: imagem Node.js usada pelos servidores JavaScript.
- `services/python/music_service/generated/`: módulos protobuf/gRPC gerados a partir de `proto/music.proto`.
- `services/python/music_service/http_utils.py`: utilitário HTTP minimalista usado por REST, GraphQL e SOAP em Python.
- `docker-compose.yml`: sobe as APIs das duas linguagens, Locust, bateria de testes e geração de gráficos.
- `locustfile.py`: define os usuários virtuais e cenários de carga.
- `scripts/run_python.ps1`: executa apenas a implementação Python.
- `scripts/run_javascript.ps1`: executa apenas a implementação JavaScript.
- `scripts/run_all.ps1`: executa Python e JavaScript no mesmo comando.
- `scripts/start_services/`: scripts para subir uma API isolada, sem executar Locust.
- `scripts/start_services/README.md`: guia de endpoints CRUD e exemplos de requisições para REST, GraphQL, SOAP e gRPC.
- `scripts/run_locust_scenarios.py`: executa a bateria com 50, 250 e 500 usuários.
- `scripts/generate_charts.py`: gera gráficos PNG, resumo agregado e comparativo Python x JavaScript. Quando executado sem `LOCUST_RESULTS_DIR`, detecta automaticamente `results/python` e `results/javascript`, se existirem.

## Execução com PowerShell

Cada script sobe as APIs em containers, espera os serviços ficarem saudáveis, executa a bateria headless do Locust, gera os gráficos e encerra os containers ao final.

Rodar apenas Python:

```powershell
.\scripts\run_python.ps1
```

Rodar apenas JavaScript:

```powershell
.\scripts\run_javascript.ps1
```

Rodar uma API específica de uma linguagem:

```powershell
.\scripts\run_python.ps1 -Api rest
.\scripts\run_python.ps1 -Api graphql
.\scripts\run_python.ps1 -Api soap
.\scripts\run_python.ps1 -Api grpc

.\scripts\run_javascript.ps1 -Api rest
.\scripts\run_javascript.ps1 -Api graphql
.\scripts\run_javascript.ps1 -Api soap
.\scripts\run_javascript.ps1 -Api grpc
```

Subir uma API e deixá-la disponível para acesso posterior, sem executar Locust:

```powershell
.\scripts\run_python.ps1 -Api rest -StartOnly
.\scripts\run_javascript.ps1 -Api graphql -StartOnly
```

Também é possível usar os scripts específicos de `scripts/start_services/` para subir apenas um serviço:

```powershell
.\scripts\start_services\python_rest.ps1
.\scripts\start_services\python_graphql.ps1
.\scripts\start_services\python_soap.ps1
.\scripts\start_services\python_grpc.ps1

.\scripts\start_services\javascript_rest.ps1
.\scripts\start_services\javascript_graphql.ps1
.\scripts\start_services\javascript_soap.ps1
.\scripts\start_services\javascript_grpc.ps1
```

O guia completo de endpoints CRUD e exemplos de requisição está em `scripts/start_services/README.md`.

## Bateria de Testes

Os testes usam três cargas:

| Cenário       | Usuários virtuais |
| ------------- | ----------------: |
| `carga-leve`  |                50 |
| `carga-media` |               250 |
| `carga-alta`  |               500 |

O `spawn-rate` é único para os três cenários. Nos scripts PowerShell, o padrão é `10` usuários por segundo; ao executar o serviço do Locust diretamente pelo Docker Compose sem definir variável de ambiente, o Compose usa `100`.

O script `run_all.ps1` já roda a bateria completa. Caso queira executar manualmente pelo Docker Compose:

```powershell
docker compose up -d rest-python graphql-python soap-python grpc-python
docker compose --profile python-scenarios run --rm locust-python
```

Para filtrar a bateria para uma tecnologia ao executar o runner diretamente, use `LOCUST_TECHNOLOGIES` com `rest`, `graphql`, `soap` ou `grpc`.

Os resultados são salvos em:

```text
results/python/
results/javascript/
```

Quando `-Api` é usado, os resultados ficam em subpastas por tecnologia, por exemplo `results/python/rest/` ou `results/javascript/graphql/`.

## Cenários do Locust

Cada tecnologia executa os mesmos cenários de leitura geral:

- `listar-usuarios`: lista os dados de todos os usuários do serviço.
- `listar-musicas`: lista os dados de todas as músicas mantidas pelo serviço.
- `listar-playlists`: lista os dados de todas as playlists mantidas pelo serviço.
- `listar-playlists-usuario`: lista os dados de todas as playlists de um determinado usuário.
- `listar-musicas-playlist`: lista os dados de todas as músicas de uma determinada playlist.
- `listar-playlists-musica`: lista os dados de todas as playlists que contêm uma determinada música.

O CRUD completo continua disponível nas APIs para uso manual, mas a bateria do Locust usa apenas essas consultas de leitura para forçar respostas maiores com a massa em memória. A massa também foi ajustada para que os cenários filtrados não sejam pequenos demais: o usuário `u1` possui 300 playlists, a playlist `p1` possui 300 músicas e a música `s1` aparece em 300 playlists.

O `locustfile.py` não define pausas artificiais entre tarefas. Os usuários virtuais executam chamadas continuamente durante o tempo do teste.

## Métricas

As principais métricas são:

- vazão em requisições por segundo;
- latência média;
- latência p95;
- tamanho médio da resposta.

## Gráficos

Todos os arquivos PNG são gravados diretamente em uma única pasta:

```text
results/charts/
```

Os nomes dos arquivos indicam a linguagem e a carga, por exemplo `python-locust-throughput-carga-leve-u50.png`, `javascript-locust-p95-latency-carga-alta-u500.png` e `comparativo-locust-throughput-carga-media-u250.png`.

São gerados quatro gráficos para cada carga. Dois gráficos agregam os seis cenários de leitura e mostram a média por tecnologia:

- vazão média;
- latência p95 média.

Os outros dois gráficos mantêm a visão detalhada por cenário de leitura, como usuários, músicas, playlists, playlists do usuário, músicas da playlist e playlists que contêm uma música:

- vazão por tecnologia e cenário de leitura;
- latência p95 por tecnologia e cenário de leitura.

Quando os resultados das duas linguagens existem, também são gerados quatro gráficos comparativos por carga. Dois usam as mesmas médias e barras verticais agrupadas por tecnologia, comparando pares como `REST Python` x `REST JavaScript`. Os outros dois detalham os cenários de leitura.

Como o tamanho da resposta depende do endpoint e da tecnologia, mas não do número de usuários virtuais, essa métrica é mostrada em um gráfico próprio, consolidado entre as cargas disponíveis:

- tamanho médio geral por endpoint e API.

## Análise e Discussão dos Resultados

A análise abaixo usa os gráficos comparativos gerados em `results/charts/`. Em todos os casos, a vazão está em requisições por segundo, então valores maiores são melhores; a latência usa p95 em milissegundos, então valores menores são melhores; e o tamanho médio da resposta está em KB por requisição. Os números de vazão e latência apresentados são a média dos seis cenários de leitura do Locust: listar usuários, listar músicas, listar playlists, listar playlists do usuário, listar músicas da playlist e listar playlists que contêm uma música.

### Tamanho médio por endpoint

O gráfico abaixo consolida as cargas de 50, 250 e 500 usuários e também consolida as duas linguagens, porque o volume retornado por cada endpoint não muda quando há mais usuários simultâneos. Ele serve para comparar quanto cada API retorna em cada cenário de leitura.

![Tamanho médio geral por endpoint e API](results/charts/locust-content-size-geral.png)

O resultado mostra que `listar-musicas`, `listar-playlists` e `listar-usuarios` tendem a retornar os maiores volumes porque entregam coleções completas da base em memória. Os cenários filtrados de playlist também foram aumentados para ficarem na casa das centenas: `listar-playlists-usuario` retorna 300 playlists do usuário `u1`, `listar-musicas-playlist` retorna 300 músicas da playlist `p1` e `listar-playlists-musica` retorna 300 playlists que contêm a música `s1`. Assim, eles passam a pesar de forma mais justa nas médias finais de latência e vazão.

As diferenças entre APIs vêm principalmente do formato de serialização. REST e GraphQL usam JSON textual, então carregam nomes de campos repetidos em cada objeto; GraphQL ainda envolve a resposta dentro de uma estrutura de resultado da consulta. SOAP tende a ser o maior porque adiciona envelope XML, namespaces e tags de abertura e fechamento, o que aumenta bastante o texto trafegado, principalmente nas respostas grandes. gRPC fica menor porque usa Protocol Buffers em formato binário, sem repetir nomes de campos textuais em cada item da lista. Por isso, mesmo quando o gRPC Python teve latência alta por custo de implementação e concorrência, o tamanho retornado por ele continua menor na comparação de payload.

### Carga leve: 50 usuários virtuais

![Comparativo de vazão com 50 usuários](results/charts/comparativo-locust-throughput-carga-leve-u50.png)

![Comparativo de latência p95 com 50 usuários](results/charts/comparativo-locust-p95-latency-carga-leve-u50.png)

| Tecnologia | Python req/s | JavaScript req/s | Python p95 | JavaScript p95 |
| ---------- | -----------: | ---------------: | ---------: | -------------: |
| REST       |       322,99 |           516,00 |      35 ms |          19 ms |
| GraphQL    |        67,17 |           366,59 |     232 ms |          32 ms |
| SOAP       |        53,82 |            66,02 |     384 ms |         222 ms |
| gRPC       |       305,57 |         1.020,42 |      40 ms |          13 ms |

Com 50 usuários, a diferença entre as tecnologias já aparece mesmo antes de o sistema entrar em saturação forte. No JavaScript, o gRPC foi o melhor resultado geral, com 1.020,42 req/s e p95 de 13 ms. Isso é coerente com o uso de HTTP/2, chamadas unary e Protocol Buffers, que reduzem payload textual e custo de parsing. O REST JavaScript também ficou forte, com 516,00 req/s e p95 de 19 ms, porque usa `node:http` diretamente e apenas serializa JSON, sem uma camada de framework pesada.

No Python, REST e gRPC ficaram próximos em vazão: 322,99 req/s no REST e 305,57 req/s no gRPC. O REST se beneficia de uma rota direta, JSON simples e pouca mediação entre HTTP e domínio. Já o gRPC Python usa `grpcio`, mas cada resposta passa pela construção explícita de objetos protobuf em Python, como listas de `User`, `Song` e `Playlist`; esse custo de alocação aparece mesmo com uma serialização binária eficiente.

O ponto mais chamativo da carga leve é o GraphQL Python: 67,17 req/s e p95 de 232 ms, contra 366,59 req/s e 32 ms no JavaScript. As duas versões usam execução síncrona de GraphQL, mas no Python a biblioteca `graphql-core` faz parsing, validação, execução do schema e resolução de campos em cima de objetos Python a cada requisição. Como esse trabalho é majoritariamente CPU-bound e ocorre dentro de threads do `ThreadingHTTPServer`, o GIL limita o ganho de paralelismo efetivo. No JavaScript, a biblioteca `graphql` roda sobre V8, e o servidor `node:http` mantém muitas conexões concorrentes com menos custo por conexão.

SOAP foi a tecnologia mais custosa nas duas linguagens. Mesmo em 50 usuários, o Python ficou em 53,82 req/s e 384 ms de p95; o JavaScript ficou em 66,02 req/s e 222 ms. Isso reflete a verbosidade do XML e o custo adicional implementado no projeto: o servidor valida envelope, namespace, operação, campos e ainda executa passagens de canonicalização configuradas por `SOAP_COMPLEXITY_PASSES`. A implementação JavaScript usa bastante manipulação de string e expressões regulares, que o V8 costuma otimizar bem; a versão Python usa `ElementTree` e cria árvores XML para requisição e resposta, o que aumenta o custo.

### Carga média: 250 usuários virtuais

![Comparativo de vazão com 250 usuários](results/charts/comparativo-locust-throughput-carga-media-u250.png)

![Comparativo de latência p95 com 250 usuários](results/charts/comparativo-locust-p95-latency-carga-media-u250.png)

| Tecnologia | Python req/s | JavaScript req/s | Python p95 | JavaScript p95 |
| ---------- | -----------: | ---------------: | ---------: | -------------: |
| REST       |       399,97 |           486,57 |      68 ms |          43 ms |
| GraphQL    |        66,80 |           357,28 |     858 ms |          80 ms |
| SOAP       |        50,48 |            65,64 |   1.560 ms |         762 ms |
| gRPC       |       310,57 |         1.028,82 |     202 ms |          58 ms |

Com 250 usuários, a diferença principal deixa de ser apenas vazão e passa a ser estabilidade sob concorrência. O JavaScript gRPC manteve praticamente o mesmo patamar de vazão, subindo para 1.028,82 req/s, com p95 de 58 ms. Isso indica que, nessa faixa, o servidor ainda não chegou ao mesmo gargalo visto nas versões Python. O REST JavaScript também permaneceu alto, com 486,57 req/s e 43 ms, enquanto o GraphQL JavaScript teve queda moderada para 357,28 req/s e p95 de 80 ms.

No Python, REST subiu para 399,97 req/s, mas já com p95 de 68 ms. Esse aumento em relação à carga leve pode ocorrer porque a carga maior mantém o servidor mais ocupado e reduz períodos ociosos, mas o ganho para aí: o teste passa a se aproximar do limite prático do servidor HTTP minimalista e da serialização JSON em Python.

GraphQL Python praticamente não aumentou a vazão: foi de 67,17 req/s para 66,80 req/s. A latência, porém, subiu de 232 ms para 858 ms. Esse é um sinal clássico de saturação: o servidor atinge sua capacidade de processamento por segundo, e as requisições excedentes passam a esperar mais tempo na fila. O mesmo padrão aparece no SOAP Python, que caiu para 50,48 req/s e teve p95 de 1.560 ms. Ou seja, aumentar usuários não gerou mais trabalho concluído por segundo; gerou espera.

O gRPC Python ficou em 310,57 req/s e p95 de 202 ms. Ele mantém boa vazão frente a GraphQL e SOAP, mas se distancia muito do JavaScript. Um fator específico da implementação é o uso de um pool de workers no servidor Python: quando muitos usuários concorrem, as chamadas que excedem a capacidade momentânea desse pool aguardam. Além disso, a conversão manual dos dicionários do domínio para mensagens protobuf cria muitos objetos por resposta, o que pressiona CPU, memória e coletor de lixo.

### Carga alta: 500 usuários virtuais

![Comparativo de vazão com 500 usuários](results/charts/comparativo-locust-throughput-carga-alta-u500.png)

![Comparativo de latência p95 com 500 usuários](results/charts/comparativo-locust-p95-latency-carga-alta-u500.png)

| Tecnologia | Python req/s | JavaScript req/s | Python p95 | JavaScript p95 |
| ---------- | -----------: | ---------------: | ---------: | -------------: |
| REST       |       402,28 |           479,13 |      70 ms |          46 ms |
| GraphQL    |        64,57 |           346,08 |   1.620 ms |          83 ms |
| SOAP       |        50,59 |            65,66 |   2.180 ms |         814 ms |
| gRPC       |       309,05 |         1.029,02 |     394 ms |         110 ms |

Com 500 usuários, os limites ficam bem nítidos. JavaScript gRPC continuou como melhor opção, com 1.029,02 req/s e p95 de 110 ms. Mesmo com aumento de latência em relação à carga média, ele sustentou a vazão. O REST JavaScript também se manteve estável, com 479,13 req/s e p95 de 46 ms. GraphQL JavaScript caiu pouco em vazão, para 346,08 req/s, e manteve p95 de 83 ms, valor muito menor que o GraphQL Python.

No Python, REST ficou praticamente no mesmo patamar da carga média: 402,28 req/s e p95 de 70 ms. Esse é um resultado importante, porque mostra que REST foi a opção Python mais equilibrada para esse conjunto de consultas: simples, previsível e com latência controlada. O gRPC Python manteve cerca de 309,05 req/s, mas a latência p95 subiu para 394 ms. A vazão estável com latência crescente sugere que a pilha consegue processar uma quantidade parecida de chamadas por segundo, mas com mais tempo de espera sob concorrência.

#### Por que REST superou gRPC no Python?

Embora gRPC normalmente seja associado a maior eficiência por usar HTTP/2 e Protocol Buffers, esse ganho não aparece automaticamente em qualquer implementação. Nesta versão Python, o REST percorre um caminho muito curto: a rota chama o domínio, recebe listas de dicionários e usa `json.dumps` para enviar a resposta. Como os dados já estão em estruturas nativas do Python, há pouca adaptação entre a regra de negócio e a resposta HTTP.

No gRPC Python, o caminho é mais trabalhoso. Depois que o domínio retorna os mesmos dicionários, o servidor precisa construir explicitamente mensagens protobuf para cada item retornado, como `User`, `Song` e `Playlist`. Em chamadas que retornam coleções grandes, como listagem de músicas e usuários, isso cria muitos objetos Python antes da serialização binária acontecer. Ou seja, mesmo que o payload final seja menor e mais eficiente na rede, existe um custo local de montagem das mensagens que pesa bastante neste cenário.

Outro fator é a concorrência. O servidor gRPC Python usa um pool de workers para executar chamadas simultâneas. Quando o número de usuários virtuais cresce, as chamadas que excedem a capacidade momentânea desse pool ficam aguardando, e a latência p95 aumenta mesmo quando a vazão permanece quase constante. Esse comportamento indica saturação: o sistema continua concluindo uma quantidade parecida de requisições por segundo, mas cada requisição passa mais tempo esperando sua vez.

Assim, o resultado não contradiz a vantagem teórica do gRPC. Ele mostra que, neste projeto, o REST Python teve uma implementação mais direta e barata para consultas em memória, enquanto o gRPC Python pagou mais custo de adaptação, alocação de objetos e concorrência. A própria versão JavaScript confirma essa leitura: nela, gRPC ficou muito acima do REST, porque a pilha `@grpc/grpc-js` e o runtime Node.js lidaram melhor com chamadas concorrentes e serialização nesse formato.

GraphQL Python chegou ao pior descolamento entre linguagens: 64,57 req/s e p95 de 1.620 ms, contra 346,08 req/s e 83 ms no JavaScript. Isso reforça que o custo não vem apenas do protocolo GraphQL em si, mas da combinação entre biblioteca, runtime, modelo de concorrência e volume de objetos processados por consulta. As consultas retornam coleções relativamente grandes da base em memória, e o GraphQL precisa percorrer o schema e resolver campos para cada item retornado. Em Python, esse trabalho envolve muitas chamadas pequenas e alocações; em JavaScript, a execução síncrona também existe, mas o V8 e o servidor HTTP do Node lidaram melhor com esse tipo de carga.

SOAP Python foi o caso mais pesado: 50,59 req/s e p95 de 2.180 ms. SOAP JavaScript também foi limitado, com 65,66 req/s e 814 ms, mas sofreu menos. A proximidade de vazão entre Python e JavaScript em SOAP mostra que o formato XML e as validações dominam o custo total, reduzindo o espaço para ganhos de runtime. Ainda assim, a latência Python cresceu mais porque cada requisição faz parsing e validação XML em estruturas de objetos, enquanto a versão JavaScript usa um caminho mais baseado em strings.

## Conclusão

Os resultados indicam três grupos de comportamento. O primeiro é o das APIs com baixo overhead de protocolo, especialmente REST e gRPC. REST foi muito competitivo por usar HTTP e JSON de forma direta; gRPC foi superior no JavaScript por combinar payload binário, contrato forte e uma implementação eficiente da pilha gRPC para Node.js. O segundo grupo é o GraphQL: ele oferece flexibilidade ao cliente, mas cobra esse benefício com parsing da query, validação do schema, execução do plano e resolução de campos. Esse custo ficou aceitável no JavaScript e muito alto no Python. O terceiro grupo é o SOAP, no qual XML, envelope, validação e payload textual dominaram o tempo de processamento.

As versões foram aproximadas em nível de implementação: as APIs REST, GraphQL e SOAP usam servidores HTTP minimalistas nas duas linguagens, sem frameworks web completos, e compartilham a mesma massa de dados em memória. Essa escolha ajuda a comparar o custo das tecnologias de invocação, mas também evidencia uma diferença importante entre os runtimes. No JavaScript, o `node:http` é naturalmente orientado a eventos e assíncrono, conseguindo manter muitas conexões abertas com baixa sobrecarga por requisição. No Python, o `ThreadingHTTPServer` cria um modelo baseado em múltiplas threads, que funciona bem para casos simples, mas sofre mais quando a requisição exige muito trabalho de CPU, alocação de objetos ou parsing pesado.

Essa diferença de concorrência aparece com força em GraphQL e SOAP. No GraphQL Python, cada chamada passa por parsing da consulta, validação do schema, execução síncrona e resolução dos campos retornados. Como essas etapas são principalmente CPU-bound, várias threads não significam paralelismo pleno por causa do GIL, e o aumento de usuários passa a gerar fila. Por isso a vazão do GraphQL Python fica praticamente parada entre 50, 250 e 500 usuários, enquanto a latência p95 sobe de 232 ms para 858 ms e depois 1.620 ms. No SOAP Python ocorre algo parecido: o parsing XML, a criação de árvores com `ElementTree`, a validação do envelope e as passagens de canonicalização tornam cada requisição mais pesada; a vazão fica perto de 50 req/s, enquanto o p95 cresce até 2.180 ms na carga alta.

No JavaScript, essas mesmas APIs também pagam custos de protocolo, mas o runtime absorve melhor a concorrência do teste. O Node.js mantém o gerenciamento de conexões e eventos em uma pilha otimizada, e o V8 tende a executar bem manipulação de JSON, strings e objetos de curta duração. Isso ajuda a explicar por que o GraphQL JavaScript sustentou 366,59 req/s em 50 usuários, 357,28 req/s em 250 e 346,08 req/s em 500, mantendo p95 abaixo de 83 ms na carga alta. Ainda assim, o SOAP JavaScript continuou limitado, porque XML e validações pesadas são caros em qualquer runtime; a diferença é que a degradação de latência foi menor do que no Python.

Também é importante notar que vazão e latência contam histórias complementares. Quando a vazão fica praticamente constante e a latência cresce muito, como ocorreu em GraphQL Python e SOAP Python, o sistema está saturado. Ele não consegue concluir muito mais requisições por segundo; em vez disso, acumula espera. Já JavaScript gRPC manteve vazão próxima de 1.020 req/s a 1.029 req/s nas três cargas, com aumento gradual de p95 de 13 ms para 58 ms e depois 110 ms, sinal de maior folga operacional.

Esses resultados não significam que JavaScript será sempre mais rápido nem que Python seja inadequado para serviços remotos. Eles mostram que, nesta implementação minimalista, com Locust gerando muitas chamadas curtas, respostas em memória e bastante serialização, o modelo de execução do Node.js foi mais favorável. Em uma aplicação real, frameworks assíncronos em Python, uso de múltiplos processos, cache de queries GraphQL, limitação de complexidade de consultas, serialização otimizada e ajustes no servidor poderiam mudar parte desse cenário.

Por fim, os números reforçam uma conclusão prática: se o objetivo principal for simplicidade e previsibilidade, REST apresentou bom equilíbrio nas duas linguagens. Se o objetivo for máxima vazão entre serviços, gRPC foi a melhor escolha, especialmente em JavaScript. GraphQL é útil quando o cliente precisa controlar a forma dos dados, mas precisa de cuidado com custo de execução, cache, complexidade de queries e otimização dos resolvers. SOAP manteve valor como modelo formal e compatível com integrações legadas, mas foi o mais caro para esse cenário de alto volume de chamadas.
