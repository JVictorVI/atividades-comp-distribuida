# Serviço JavaScript

Esta pasta contém a implementação em Node.js do mesmo trabalho feito em Python. Ela usa os mesmos dados iniciais, as mesmas operações e os mesmos contratos de chamada:

- REST
- GraphQL
- SOAP
- gRPC

Assim como a versão Python, a base inicial fica em memória e é gerada com 300 usuários, 500 músicas e 400 playlists.

Os servidores REST, GraphQL e SOAP usam `node:http`. O servidor gRPC usa `node:http2` e serializa as mensagens conforme o contrato compartilhado `proto/music.proto`.

## Portas locais

Para poder rodar junto com a versão Python, a versão JavaScript usa portas diferentes por padrão:

| Tecnologia | Porta |
| ---------- | ----: |
| REST       | 3100  |
| GraphQL    | 3101  |
| SOAP       | 3102  |
| gRPC       | 51051 |

## Executar localmente

Abra quatro terminais a partir da pasta `services/javascript/`:

```powershell
npm run rest
npm run graphql
npm run soap
npm run grpc
```

Chamadas rápidas:

```powershell
Invoke-RestMethod http://localhost:3100/users
Invoke-RestMethod http://localhost:3101/graphql -Method Post -ContentType "application/json" -Body '{"query":"query { users { id name email } }"}'
Invoke-WebRequest -UseBasicParsing http://localhost:3102/soap
```

## Executar com Docker e Locust

Na raiz do projeto:

```powershell
.\scripts\run_javascript.ps1
```

Parâmetros úteis:

```powershell
.\scripts\run_javascript.ps1 -SpawnRate 50 -Duration 2m
.\scripts\run_javascript.ps1 -Api rest
.\scripts\run_javascript.ps1 -Api graphql
.\scripts\run_javascript.ps1 -Api soap
.\scripts\run_javascript.ps1 -Api grpc
.\scripts\run_javascript.ps1 -Api rest -StartOnly
.\scripts\run_javascript.ps1 -NoBuild
.\scripts\run_javascript.ps1 -KeepServices
```

Use `-StartOnly` quando quiser apenas subir a API escolhida e acessá-la depois, sem executar a bateria do Locust.

Também é possível rodar pelo Compose:

```powershell
docker compose build rest-js rest-python
docker compose up -d rest-js graphql-js soap-js grpc-js
docker compose --profile js-scenarios run --rm locust-js
docker compose --profile js-charts run --rm charts-js
docker compose stop rest-js graphql-js soap-js grpc-js
docker compose rm -f rest-js graphql-js soap-js grpc-js
```

## Estrutura

```text
services/javascript/
|-- Dockerfile
|-- README.md
|-- package.json
|-- config.js
|-- healthcheckGrpc.js
|-- httpUtils.js
|-- protobuf.js
|-- domain/
|   `-- musicStore.js
`-- servers/
    |-- rest.js
    |-- graphql.js
    |-- soap.js
    `-- grpcServer.js
```
