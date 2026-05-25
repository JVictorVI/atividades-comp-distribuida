# Trabalho 6 - Comparação de Tecnologias de Invocação de Serviços Remotos

Projeto em Python para comparar SOAP, REST, GraphQL e gRPC usando o mesmo serviço de streaming de músicas. A comparação é feita com Locust, três cargas de usuários virtuais e gráficos gerados automaticamente a partir dos resultados.

## Objetivo

O objetivo é comparar tecnologias de invocação remota em um mesmo domínio. Para manter a comparação justa, as quatro APIs usam a mesma regra de negócio e a mesma base de dados em memória.

O serviço gerencia:

- Usuários.
- Músicas.
- Playlists.

Operações cobertas:

- Criar, consultar, alterar e remover usuários.
- Criar, consultar, alterar e remover músicas.
- Criar, consultar, alterar e remover playlists.
- Listar playlists de um usuário.
- Listar músicas de uma playlist.
- Listar playlists que contêm uma música.

## Tecnologias Comparadas

REST:

- Implementado com FastAPI.
- Usa URLs, JSON e métodos HTTP.
- Porta local: `3000`.

GraphQL:

- Implementado com `graphql-core` e FastAPI.
- Usa schema tipado e permite consultar exatamente os campos desejados.
- Porta local: `3001`.

SOAP:

- Implementado em Python com FastAPI e XML.
- Expõe endpoint SOAP e WSDL básico.
- Porta local: `3002`.

gRPC:

- Implementado com `grpcio`.
- Usa o contrato `proto/music.proto`.
- O servidor usa handlers gRPC genéricos e serialização Protocol Buffers em Python.
- Porta local: `50051`.

## Origem, Características, Vantagens e Desvantagens

Todas as tecnologias abaixo foram exemplificadas em Python, que é a linguagem usada neste projeto.

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

channel = grpc.insecure_channel("localhost:50051")

try:
    list_songs = channel.unary_unary("/music.MusicStreaming/ListSongs")
    response_bytes = list_songs(b"", timeout=5)
    print(response_bytes)
finally:
    channel.close()
```

Em uma implementação gRPC tradicional, o cliente Python também poderia ser gerado automaticamente a partir do arquivo `proto/music.proto`. Neste projeto, o servidor e o cliente de carga usam handlers genéricos para manter a implementação concentrada em Python e evitar etapas adicionais de geração de código.

## Como Foi Feito

O domínio compartilhado fica em:

```text
music_service/domain/music_store.py
```

Esse módulo contém:

- dados iniciais;
- validações;
- regras de criação, alteração, remoção e consulta;
- relações entre usuários, músicas e playlists.

Os quatro servidores apenas adaptam suas chamadas para esse mesmo domínio. Assim, a diferença entre REST, GraphQL, SOAP e gRPC fica concentrada no mecanismo de invocação remota, não na regra de negócio.

## Estrutura

```text
.
├── docker-compose.yml
├── Dockerfile
├── locustfile.py
├── requirements.txt
├── music_service/
│   ├── config.py
│   ├── domain/
│   │   └── music_store.py
│   └── servers/
│       ├── rest.py
│       ├── graphql.py
│       ├── soap.py
│       └── grpc_server.py
├── proto/
│   └── music.proto
├── scripts/
│   ├── generate_charts.py
│   ├── run_locust_scenarios.py
│   └── run_all.ps1
└── results/
```

Arquivos importantes:

- `Dockerfile`: imagem Python usada pelos servidores, Locust e gráficos.
- `docker-compose.yml`: sobe as APIs, Locust, bateria de testes e geração de gráficos.
- `locustfile.py`: define os usuários virtuais e cenários de carga.
- `scripts/run_all.ps1`: executa o fluxo completo com Docker Compose.
- `scripts/run_locust_scenarios.py`: executa a bateria com 50, 250 e 500 usuários.
- `scripts/generate_charts.py`: gera gráficos SVG e resumo agregado.

## Execução Completa com PowerShell

O script sobe as quatro APIs em containers, espera os serviços ficarem saudáveis, executa a bateria headless do Locust, gera os gráficos e encerra os containers ao final.

Execute:

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
| `carga-baixa` |                50 |
| `carga-media` |               250 |
| `carga-alta`  |               500 |

O `spawn-rate` é único para os três cenários. O padrão é `100` usuários por segundo.

O script `run_all.ps1` já roda a bateria completa. Caso queira executar manualmente pelo Docker Compose:

```powershell
docker compose up -d rest graphql soap grpc
docker compose --profile scenarios up --build --abort-on-container-exit --exit-code-from locust-scenarios locust-scenarios
```

Controlar o `spawn-rate`:

```powershell
$env:LOCUST_SPAWN_RATE="50"
docker compose --profile scenarios up --build --abort-on-container-exit --exit-code-from locust-scenarios locust-scenarios
```

Controlar a duração de cada teste:

```powershell
$env:LOCUST_DURATION="2m"
docker compose --profile scenarios up --build --abort-on-container-exit --exit-code-from locust-scenarios locust-scenarios
```

Os resultados são salvos em:

```text
results/
```

## Cenários do Locust

Cada tecnologia executa os mesmos cenários:

- `catalogo-leitura`: lista usuários, músicas e playlists.
- `relacionamentos-leitura`: consulta playlists por usuário, músicas por playlist e playlists por música.
- `usuarios-escrita`: cria e remove usuários temporários.

O `locustfile.py` não define pausas artificiais entre tarefas. Os usuários virtuais executam chamadas continuamente durante o tempo do teste.

## Métricas

As principais métricas são:

- vazão em requisições por segundo;
- latência média;
- latência p95;
- quantidade de falhas;
- taxa de erros.

A taxa de erros é calculada assim:

```text
failureCount / requestCount * 100
```

## Gráficos

Após executar a bateria, gere os gráficos:

```powershell
docker compose --profile charts run --build --rm charts
```

São gerados três gráficos para cada carga, dentro de `results/charts/`:

- vazão;
- latência p95;
- taxa de erros.

Arquivos esperados:

```text
results/charts/locust-throughput-carga-baixa-u50.svg
results/charts/locust-p95-latency-carga-baixa-u50.svg
results/charts/locust-error-rate-carga-baixa-u50.svg
results/charts/locust-throughput-carga-media-u250.svg
results/charts/locust-p95-latency-carga-media-u250.svg
results/charts/locust-error-rate-carga-media-u250.svg
results/charts/locust-throughput-carga-alta-u500.svg
results/charts/locust-p95-latency-carga-alta-u500.svg
results/charts/locust-error-rate-carga-alta-u500.svg
```

Também são gerados:

```text
results/locust-summary.csv
results/locust-summary.json
```

## Execução Manual sem o Script Principal

O fluxo recomendado é usar `scripts/run_all.ps1`. Ainda assim, se quiser executar as etapas manualmente com Docker Compose, use:

```powershell
docker compose build
docker compose up -d rest graphql soap grpc
docker compose --profile scenarios run --rm locust-scenarios
docker compose --profile charts run --rm charts
docker compose down --remove-orphans
```

Também é possível preparar um ambiente Python local para desenvolvimento:

```powershell
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
& .\.venv\Scripts\python.exe scripts/run_locust_scenarios.py
& .\.venv\Scripts\python.exe scripts/generate_charts.py
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

channel = grpc.insecure_channel("localhost:50051")
list_users = channel.unary_unary("/music.MusicStreaming/ListUsers")

try:
    print(list_users(b"", timeout=5))
finally:
    channel.close()
```

## Pontos para Análise

REST é simples, direto e adequado para APIs CRUD.

GraphQL é interessante quando o cliente precisa controlar quais campos buscar e compor consultas relacionais.

SOAP tem contrato formal e boa compatibilidade com cenários corporativos, mas é mais verboso.

gRPC é eficiente para comunicação entre serviços, mas exige clientes compatíveis com gRPC e Protocol Buffers.

## Observações

Os dados ficam em memória. Ao reiniciar um servidor, a base volta ao estado inicial.

Os testes de escrita criam usuários temporários e os removem em seguida.

Os resultados variam de acordo com máquina, Docker, sistema operacional, duração do teste e `spawn-rate`.
