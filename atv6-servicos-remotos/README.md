# Trabalho 6 - Comparação de Tecnologias de Invocação de Serviços Remotos

Projeto com implementações em Python e JavaScript/Node.js para comparar SOAP, REST, GraphQL e gRPC usando o mesmo serviço de streaming de músicas. A comparação é feita com Locust, três cargas de usuários virtuais e gráficos gerados automaticamente a partir dos resultados.

Detalhes específicos da versão JavaScript ficam em `services/javascript/README.md`.

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

## Origem, Características, Vantagens e Desvantagens

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

## Como Foi Feito

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

Para subir, testar e manter os containers ligados ao final:

```powershell
.\scripts\run_python.ps1 -Api soap -KeepServices
.\scripts\run_javascript.ps1 -Api grpc -KeepServices
```

Rodar as duas implementações:

```powershell
.\scripts\run_all.ps1
```

Parâmetros úteis:

```powershell
.\scripts\run_all.ps1 -SpawnRate 50 -Duration 2m
```

Para manter os servidores ligados depois dos testes:

```powershell
.\scripts\run_all.ps1 -KeepServices
```

Para reutilizar imagens já construídas:

```powershell
.\scripts\run_all.ps1 -NoBuild
```

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

Controlar o `spawn-rate`:

```powershell
$env:LOCUST_SPAWN_RATE="50"
docker compose --profile python-scenarios run --rm locust-python
```

Controlar a duração de cada teste:

```powershell
$env:LOCUST_DURATION="2m"
docker compose --profile python-scenarios run --rm locust-python
```

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
- `listar-playlists-usuario`: lista os dados de todas as playlists de um determinado usuário.
- `listar-musicas-playlist`: lista os dados de todas as músicas de uma determinada playlist.
- `listar-playlists-musica`: lista os dados de todas as playlists que contêm uma determinada música.

O CRUD completo continua disponível nas APIs para uso manual, mas a bateria do Locust usa apenas essas consultas de leitura para forçar respostas maiores com a massa em memória.

O `locustfile.py` não define pausas artificiais entre tarefas. Os usuários virtuais executam chamadas continuamente durante o tempo do teste.

## Métricas

As principais métricas são:

- vazão em requisições por segundo;
- latência média;
- latência p95.

## Gráficos

Após executar a bateria, gere os gráficos:

```powershell
docker compose --profile python-charts run --rm charts-python
docker compose --profile js-charts run --rm charts-js
```

Se preferir executar o gerador diretamente no host, sem `LOCUST_RESULTS_DIR`, ele procura CSVs em `results/python` e `results/javascript` e gera os dois conjuntos:

```powershell
& .\services\python\.venv\Scripts\python.exe scripts/generate_charts.py
```

Quando `LOCUST_RESULTS_DIR` estiver definido, o script gera apenas para o diretório informado. Esse é o comportamento usado pelos serviços `charts-python` e `charts-js` no Docker Compose.

Todos os arquivos PNG são gravados diretamente em uma única pasta:

```text
results/charts/
```

Os nomes dos arquivos indicam a linguagem e a carga, por exemplo `python-locust-throughput-carga-leve-u50.png`, `javascript-locust-p95-latency-carga-alta-u500.png` e `comparativo-locust-throughput-carga-media-u250.png`.

São gerados quatro gráficos para cada carga. Dois gráficos agregam os cinco cenários de leitura e mostram a média por tecnologia:

- vazão média;
- latência p95 média.

Os outros dois gráficos mantêm a visão detalhada por cenário de leitura, como usuários, músicas, playlists do usuário, músicas da playlist e playlists que contêm uma música:

- vazão por tecnologia e cenário de leitura;
- latência p95 por tecnologia e cenário de leitura.

Quando os resultados das duas linguagens existem, também são gerados quatro gráficos comparativos por carga. Dois usam as mesmas médias e barras verticais agrupadas por tecnologia, comparando pares como `REST Python` x `REST JavaScript`. Os outros dois detalham os cenários de leitura.

Arquivos esperados:

```text
results/charts/python-locust-throughput-carga-leve-u50.png
results/charts/python-locust-p95-latency-carga-leve-u50.png
results/charts/python-locust-throughput-por-cenario-carga-leve-u50.png
results/charts/python-locust-p95-latency-por-cenario-carga-leve-u50.png
results/charts/javascript-locust-throughput-carga-leve-u50.png
results/charts/javascript-locust-p95-latency-carga-leve-u50.png
results/charts/javascript-locust-throughput-por-cenario-carga-leve-u50.png
results/charts/javascript-locust-p95-latency-por-cenario-carga-leve-u50.png
results/charts/comparativo-locust-throughput-carga-leve-u50.png
results/charts/comparativo-locust-p95-latency-carga-leve-u50.png
results/charts/comparativo-locust-throughput-por-cenario-carga-leve-u50.png
results/charts/comparativo-locust-p95-latency-por-cenario-carga-leve-u50.png
```

Também são gerados:

```text
results/python/locust-summary.csv
results/python/locust-summary.json
results/javascript/locust-summary.csv
results/javascript/locust-summary.json
results/locust-combined-summary.csv
results/locust-combined-summary.json
```

## Execução Manual sem o Script Principal

O fluxo recomendado é usar os scripts principais. Ainda assim, se quiser executar as etapas manualmente com Docker Compose, use:

```powershell
docker compose build rest-python rest-js
docker compose up -d rest-python graphql-python soap-python grpc-python
docker compose --profile python-scenarios run --rm locust-python
docker compose --profile python-charts run --rm charts-python
docker compose up -d rest-js graphql-js soap-js grpc-js
docker compose --profile js-scenarios run --rm locust-js
docker compose --profile js-charts run --rm charts-js
docker compose --profile combined-charts run --rm charts-combined
docker compose down --remove-orphans
```

Também é possível preparar um ambiente Python local para desenvolvimento:

```powershell
Set-Location services\python
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

A execução local completa exige subir os quatro servidores manualmente em terminais separados:

```powershell
& .\.venv\Scripts\python.exe -m music_service.servers.rest
& .\.venv\Scripts\python.exe -m music_service.servers.graphql
& .\.venv\Scripts\python.exe -m music_service.servers.soap
& .\.venv\Scripts\python.exe -m music_service.servers.grpc_server
```

Depois, em outro terminal:

```powershell
& .\services\python\.venv\Scripts\python.exe scripts/run_locust_scenarios.py
& .\services\python\.venv\Scripts\python.exe scripts/generate_charts.py
```

## Exemplos Rápidos em Python

REST:

```python
import requests

response = requests.get("http://localhost:3000/users", timeout=5)
print(response.json())
```

GraphQL:

```python
import requests

query = "query { users { id name email } }"
response = requests.post("http://localhost:3001/graphql", json={"query": query}, timeout=5)
print(response.json())
```

SOAP:

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

response = requests.post("http://localhost:3002/soap", data=envelope, timeout=5)
print(response.text)
```

gRPC:

```python
import grpc

from music_service.generated import music_pb2, music_pb2_grpc

channel = grpc.insecure_channel("localhost:50051")

try:
    client = music_pb2_grpc.MusicStreamingStub(channel)
    print(client.ListUsers(music_pb2.Empty(), timeout=5).users)
finally:
    channel.close()
```

## Pontos para Análise

REST é simples, direto e adequado para APIs CRUD.

GraphQL é interessante quando o cliente precisa controlar quais campos buscar e compor consultas relacionais.

SOAP tem contrato formal e boa compatibilidade com cenários corporativos, mas é mais verboso.

gRPC é eficiente para comunicação entre serviços, mas exige clientes compatíveis com gRPC e Protocol Buffers.

## Observações

Os dados ficam em memória. Ao reiniciar um servidor ou chamar `reset`, a base volta ao estado inicial com 300 usuários, 500 músicas e 400 playlists.

Os testes de escrita criam usuários temporários e os removem em seguida.

Os resultados variam de acordo com máquina, Docker, sistema operacional, duração do teste e `spawn-rate`.
