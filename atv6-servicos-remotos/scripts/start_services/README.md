# Scripts para subir APIs separadamente

Execute os comandos a partir da raiz do projeto.

## Python

```powershell
.\scripts\start_services\python_rest.ps1
.\scripts\start_services\python_graphql.ps1
.\scripts\start_services\python_soap.ps1
.\scripts\start_services\python_grpc.ps1
```

Endpoints:

- REST: `http://localhost:3000`
- GraphQL: `http://localhost:3001/graphql`
- SOAP: `http://localhost:3002/soap`
- gRPC: `localhost:50051`

## JavaScript

```powershell
.\scripts\start_services\javascript_rest.ps1
.\scripts\start_services\javascript_graphql.ps1
.\scripts\start_services\javascript_soap.ps1
.\scripts\start_services\javascript_grpc.ps1
```

Endpoints:

- REST: `http://localhost:3100`
- GraphQL: `http://localhost:3101/graphql`
- SOAP: `http://localhost:3102/soap`
- gRPC: `localhost:55051`

## Opções uteis

Para pular o build quando a imagem ja estiver atualizada:

```powershell
.\scripts\start_services\python_rest.ps1 -NoBuild
```

Para parar tudo:

```powershell
docker compose down
```
