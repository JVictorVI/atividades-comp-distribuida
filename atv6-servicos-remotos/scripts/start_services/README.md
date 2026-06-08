# Scripts para subir APIs separadamente

Execute os comandos a partir da raiz do projeto.

## Python

Para subir todas as APIs Python de uma vez:

```powershell
.\scripts\start_services\python_all.ps1
```

Ou suba uma API especifica:

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

Para subir todas as APIs JavaScript de uma vez:

```powershell
.\scripts\start_services\javascript_all.ps1
```

Ou suba uma API especifica:

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

## Modelos de dados

As quatro APIs usam os mesmos campos:

- Usuário: `id`, `name`, `email`
- Música: `id`, `title`, `artist`, `album`, `durationSeconds`
- Playlist: `id`, `userId`, `name`, `songIds`

IDs iniciais úteis para teste:

- Usuários: `u1`, `u2`, `u3`
- Músicas: `s1`, `s2`, `s3`, `s4`, `s5`
- Playlists: `p1`, `p2`, `p3`

## REST

Escolha a base conforme o serviço iniciado:

- Python: `http://localhost:3000`
- JavaScript: `http://localhost:3100`

Endpoints gerais:

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/health` | Verifica se o serviço está no ar. |
| `POST` | `/reset` | Reinicia os dados em memória para o estado inicial. |

CRUD de usuários:

| Método | Endpoint | Body JSON | Descrição |
| --- | --- | --- | --- |
| `GET` | `/users` | - | Lista usuários. |
| `GET` | `/users/{id}` | - | Busca um usuário por id. |
| `POST` | `/users` | `{"name":"João Silva","email":"joao@example.com"}` | Cria usuário. |
| `PUT` | `/users/{id}` | `{"name":"João Atualizado"}` | Atualiza um usuário. |
| `DELETE` | `/users/{id}` | - | Remove usuário e suas playlists. |
| `GET` | `/users/{id}/playlists` | - | Lista playlists de um usuário. |

CRUD de músicas:

| Método | Endpoint | Body JSON | Descrição |
| --- | --- | --- | --- |
| `GET` | `/songs` | - | Lista músicas. |
| `GET` | `/songs/{id}` | - | Busca uma música por id. |
| `POST` | `/songs` | `{"title":"Nova Faixa","artist":"Banda API","album":"Demo","durationSeconds":210}` | Cria música. |
| `PUT` | `/songs/{id}` | `{"durationSeconds":215}` | Atualiza uma música. |
| `DELETE` | `/songs/{id}` | - | Remove música e também remove seu id das playlists. |
| `GET` | `/songs/{id}/playlists` | - | Lista playlists que contêm a música. |

CRUD de playlists:

| Método | Endpoint | Body JSON | Descrição |
| --- | --- | --- | --- |
| `GET` | `/playlists` | - | Lista playlists. Aceita filtros opcionais `userId` e `songId`. |
| `GET` | `/playlists?userId=u1` | - | Lista playlists de um usuário. |
| `GET` | `/playlists?songId=s1` | - | Lista playlists que contêm uma música. |
| `GET` | `/playlists/{id}` | - | Busca uma playlist por id. |
| `POST` | `/playlists` | `{"userId":"u1","name":"Favoritas","songIds":["s1","s2"]}` | Cria playlist. |
| `PUT` | `/playlists/{id}` | `{"name":"Favoritas 2026","songIds":["s1","s3"]}` | Atualiza playlist. |
| `DELETE` | `/playlists/{id}` | - | Remove playlist. |
| `GET` | `/playlists/{id}/songs` | - | Lista músicas de uma playlist. |

Exemplos com `curl.exe`:

```powershell
# Listar usuários
curl.exe http://localhost:3000/users

# Criar usuário
curl.exe -X POST http://localhost:3000/users `
  -H "Content-Type: application/json" `
  -d '{"name":"João Silva","email":"joao@example.com"}'

# Atualizar música
curl.exe -X PUT http://localhost:3000/songs/s1 `
  -H "Content-Type: application/json" `
  -d '{"durationSeconds":220}'

# Criar playlist
curl.exe -X POST http://localhost:3000/playlists `
  -H "Content-Type: application/json" `
  -d '{"userId":"u1","name":"Favoritas","songIds":["s1","s2"]}'

# Remover playlist
curl.exe -X DELETE http://localhost:3000/playlists/p1
```

Para testar JavaScript, troque `3000` por `3100`.

## GraphQL

Escolha o endpoint conforme o serviço iniciado:

- Python: `http://localhost:3001/graphql`
- JavaScript: `http://localhost:3101/graphql`

Todas as requisições GraphQL usam `POST`, `Content-Type: application/json` e um corpo com `query` e, opcionalmente, `variables`.

Queries disponíveis:

| Query | Descrição |
| --- | --- |
| `users` | Lista usuários. |
| `user(id: ID!)` | Busca usuário por id. |
| `songs` | Lista músicas. |
| `song(id: ID!)` | Busca música por id. |
| `playlists(userId: ID, songId: ID)` | Lista playlists, com filtros opcionais. |
| `playlist(id: ID!)` | Busca playlist por id. |
| `userPlaylists(userId: ID!)` | Lista playlists de um usuário. |
| `playlistSongs(playlistId: ID!)` | Lista músicas de uma playlist. |
| `songPlaylists(songId: ID!)` | Lista playlists que contêm uma música. |

Mutations disponíveis:

| Mutation | Descrição |
| --- | --- |
| `reset` | Reinicia os dados em memória. |
| `createUser(input: UserInput!)` | Cria usuário. |
| `updateUser(id: ID!, input: UserPatch!)` | Atualiza usuário. |
| `deleteUser(id: ID!)` | Remove usuário. |
| `createSong(input: SongInput!)` | Cria música. |
| `updateSong(id: ID!, input: SongPatch!)` | Atualiza música. |
| `deleteSong(id: ID!)` | Remove música. |
| `createPlaylist(input: PlaylistInput!)` | Cria playlist. |
| `updatePlaylist(id: ID!, input: PlaylistPatch!)` | Atualiza playlist. |
| `deletePlaylist(id: ID!)` | Remove playlist. |

Exemplos com `curl.exe`:

```powershell
# Listar usuários
curl.exe -X POST http://localhost:3001/graphql `
  -H "Content-Type: application/json" `
  -d '{"query":"query { users { id name email } }"}'

# Buscar música por id
curl.exe -X POST http://localhost:3001/graphql `
  -H "Content-Type: application/json" `
  -d '{"query":"query ($id: ID!) { song(id: $id) { id title artist album durationSeconds } }","variables":{"id":"s1"}}'

# Criar usuário
curl.exe -X POST http://localhost:3001/graphql `
  -H "Content-Type: application/json" `
  -d '{"query":"mutation ($input: UserInput!) { createUser(input: $input) { id name email } }","variables":{"input":{"name":"João Silva","email":"joao@example.com"}}}'

# Atualizar playlist
curl.exe -X POST http://localhost:3001/graphql `
  -H "Content-Type: application/json" `
  -d '{"query":"mutation ($id: ID!, $input: PlaylistPatch!) { updatePlaylist(id: $id, input: $input) { id name songIds } }","variables":{"id":"p1","input":{"name":"Favoritas 2026","songIds":["s1","s3"]}}}'

# Remover música
curl.exe -X POST http://localhost:3001/graphql `
  -H "Content-Type: application/json" `
  -d '{"query":"mutation ($id: ID!) { deleteSong(id: $id) { ok } }","variables":{"id":"s1"}}'
```

Para testar JavaScript, troque `3001` por `3101`.

## SOAP

Escolha o endpoint conforme o serviço iniciado:

- Python: `http://localhost:3002/soap`
- JavaScript: `http://localhost:3102/soap`

O WSDL fica disponível via `GET /soap`. As operações usam `POST /soap` com envelope SOAP XML.

Operações disponíveis:

| Operação | Campos |
| --- | --- |
| `Reset` | Nenhum. |
| `ListUsers` | Nenhum. |
| `GetUser` | `id` |
| `CreateUser` | `name`, `email` |
| `UpdateUser` | `id`, campos opcionais `name`, `email` |
| `DeleteUser` | `id` |
| `ListSongs` | Nenhum. |
| `GetSong` | `id` |
| `CreateSong` | `title`, `artist`, `album`, `durationSeconds` |
| `UpdateSong` | `id`, campos opcionais `title`, `artist`, `album`, `durationSeconds` |
| `DeleteSong` | `id` |
| `ListPlaylists` | Campos opcionais `userId`, `songId` |
| `GetPlaylist` | `id` |
| `CreatePlaylist` | `userId`, `name`, `songIds` |
| `UpdatePlaylist` | `id`, campos opcionais `userId`, `name`, `songIds` |
| `DeletePlaylist` | `id` |
| `ListUserPlaylists` | `userId` |
| `ListPlaylistSongs` | `playlistId` |
| `ListSongPlaylists` | `songId` |

Use `songIds` como texto separado por vírgulas em SOAP, por exemplo `s1,s2,s3`.

Exemplos com `Invoke-WebRequest`, exibindo o XML retornado em `$response.Content`:

```powershell
# Consultar WSDL
$response = Invoke-WebRequest -Uri http://localhost:3002/soap -Method Get
$response.Content

# Listar usuários
$body = @'
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="http://example.com/music-streaming">
  <soap:Body>
    <tns:ListUsers />
  </soap:Body>
</soap:Envelope>
'@

$response = Invoke-WebRequest -Uri http://localhost:3002/soap -Method Post -ContentType "text/xml; charset=utf-8" -Body $body
$response.Content

# Criar usuário
$body = @'
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="http://example.com/music-streaming">
  <soap:Body>
    <tns:CreateUser>
      <name>João Silva</name>
      <email>joao@example.com</email>
    </tns:CreateUser>
  </soap:Body>
</soap:Envelope>
'@

$response = Invoke-WebRequest -Uri http://localhost:3002/soap -Method Post -ContentType "text/xml; charset=utf-8" -Body $body
$response.Content

# Atualizar playlist
$body = @'
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="http://example.com/music-streaming">
  <soap:Body>
    <tns:UpdatePlaylist>
      <id>p1</id>
      <name>Favoritas 2026</name>
      <songIds>s1,s3</songIds>
    </tns:UpdatePlaylist>
  </soap:Body>
</soap:Envelope>
'@

$response = Invoke-WebRequest -Uri http://localhost:3002/soap -Method Post -ContentType "text/xml; charset=utf-8" -Body $body
$response.Content

# Remover música
$body = @'
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="http://example.com/music-streaming">
  <soap:Body>
    <tns:DeleteSong>
      <id>s1</id>
    </tns:DeleteSong>
  </soap:Body>
</soap:Envelope>
'@

$response = Invoke-WebRequest -Uri http://localhost:3002/soap -Method Post -ContentType "text/xml; charset=utf-8" -Body $body
$response.Content
```

Para testar JavaScript, troque `3002` por `3102`.

## gRPC

Escolha o endereço conforme o serviço iniciado:

- Python: `localhost:50051`
- JavaScript: `localhost:55051`

O contrato está em `proto/music.proto`, no serviço `music.MusicStreaming`. Como o servidor não expõe reflection, informe o arquivo `.proto` ao usar `grpcurl`.

Métodos disponíveis:

| Método gRPC | Request | Descrição |
| --- | --- | --- |
| `Reset` | `{}` | Reinicia os dados em memória. |
| `ListUsers` | `{}` | Lista usuários. |
| `GetUser` | `{"id":"u1"}` | Busca usuário por id. |
| `CreateUser` | `{"name":"João Silva","email":"joao@example.com"}` | Cria usuário. |
| `UpdateUser` | `{"id":"u1","user":{"name":"João Atualizado"}}` | Atualiza usuário. |
| `DeleteUser` | `{"id":"u1"}` | Remove usuário. |
| `ListSongs` | `{}` | Lista músicas. |
| `GetSong` | `{"id":"s1"}` | Busca música por id. |
| `CreateSong` | `{"title":"Nova Faixa","artist":"Banda API","album":"Demo","durationSeconds":210}` | Cria música. |
| `UpdateSong` | `{"id":"s1","song":{"durationSeconds":220}}` | Atualiza música. |
| `DeleteSong` | `{"id":"s1"}` | Remove música. |
| `ListPlaylists` | `{}` ou `{"userId":"u1"}` ou `{"songId":"s1"}` | Lista playlists, com filtros opcionais. |
| `GetPlaylist` | `{"id":"p1"}` | Busca playlist por id. |
| `CreatePlaylist` | `{"userId":"u1","name":"Favoritas","songIds":["s1","s2"]}` | Cria playlist. |
| `UpdatePlaylist` | `{"id":"p1","playlist":{"name":"Favoritas 2026","songIds":["s1","s3"]}}` | Atualiza playlist. |
| `DeletePlaylist` | `{"id":"p1"}` | Remove playlist. |
| `ListUserPlaylists` | `{"userId":"u1"}` | Lista playlists de um usuário. |
| `ListPlaylistSongs` | `{"playlistId":"p1"}` | Lista músicas de uma playlist. |
| `ListSongPlaylists` | `{"songId":"s1"}` | Lista playlists que contêm uma música. |

Exemplos com `grpcurl`:

```powershell
# Listar usuários
grpcurl -plaintext -proto proto/music.proto -d '{}' localhost:50051 music.MusicStreaming/ListUsers

# Buscar música por id
grpcurl -plaintext -proto proto/music.proto -d '{"id":"s1"}' localhost:50051 music.MusicStreaming/GetSong

# Criar usuário
grpcurl -plaintext -proto proto/music.proto `
  -d '{"name":"João Silva","email":"joao@example.com"}' `
  localhost:50051 music.MusicStreaming/CreateUser

# Atualizar playlist
grpcurl -plaintext -proto proto/music.proto `
  -d '{"id":"p1","playlist":{"name":"Favoritas 2026","songIds":["s1","s3"]}}' `
  localhost:50051 music.MusicStreaming/UpdatePlaylist

# Remover música
grpcurl -plaintext -proto proto/music.proto -d '{"id":"s1"}' localhost:50051 music.MusicStreaming/DeleteSong
```

Para testar JavaScript, troque `50051` por `55051`.

## Opções úteis

Para pular o build quando a imagem já estiver atualizada:

```powershell
.\scripts\start_services\python_all.ps1 -NoBuild
.\scripts\start_services\javascript_all.ps1 -NoBuild
```

Para parar tudo:

```powershell
docker compose down
```
