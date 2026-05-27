import http2 from "node:http2";

import { GRPC_PORT } from "../config.js";
import { DomainError, MusicStore } from "../domain/musicStore.js";
import {
  decodeIdRequest,
  decodePlaylistFilter,
  decodePlaylistInput,
  decodeSongInput,
  decodeUpdatePlaylist,
  decodeUpdateSong,
  decodeUpdateUser,
  decodeUserInput,
  encodePlaylist,
  encodeSong,
  encodeUser,
  firstString,
  mutationResult,
  parseFields,
  playlistsResponse,
  songsResponse,
  usersResponse
} from "../protobuf.js";

const SERVICE_PREFIX = "/music.MusicStreaming/";
const store = new MusicStore();

function readStream(stream) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    stream.on("data", (chunk) => chunks.push(chunk));
    stream.on("end", () => resolve(Buffer.concat(chunks)));
    stream.on("error", reject);
  });
}

function parseGrpcMessage(body) {
  if (body.length === 0) {
    return Buffer.alloc(0);
  }
  if (body.length < 5) {
    throw new Error("Frame gRPC incompleto");
  }
  const compressed = body[0];
  if (compressed !== 0) {
    throw new Error("Compressao gRPC nao suportada");
  }
  const length = body.readUInt32BE(1);
  if (body.length < 5 + length) {
    throw new Error("Payload gRPC incompleto");
  }
  return body.subarray(5, 5 + length);
}

function frameGrpcMessage(payload) {
  const header = Buffer.alloc(5);
  header[0] = 0;
  header.writeUInt32BE(payload.length, 1);
  return Buffer.concat([header, payload]);
}

function grpcStatus(error) {
  if (error instanceof DomainError) {
    return error.status === 404 ? 5 : 3;
  }
  return 13;
}

function sendGrpc(stream, payload) {
  stream.respond(
    {
      ":status": 200,
      "content-type": "application/grpc+proto"
    },
    { waitForTrailers: true }
  );
  stream.on("wantTrailers", () => {
    stream.sendTrailers({
      "grpc-status": "0",
      "grpc-message": ""
    });
  });
  stream.end(frameGrpcMessage(payload));
}

function sendGrpcError(stream, error) {
  stream.respond({
    ":status": 200,
    "content-type": "application/grpc+proto",
    "grpc-status": String(grpcStatus(error)),
    "grpc-message": encodeURIComponent(error.message || "Erro inesperado")
  });
  stream.end();
}

function userPlaylistsRequest(request) {
  return firstString(parseFields(request), 1);
}

function playlistSongsRequest(request) {
  return firstString(parseFields(request), 1);
}

function songPlaylistsRequest(request) {
  return firstString(parseFields(request), 1);
}

const handlers = {
  Reset: () => mutationResult(store.reset()),
  ListUsers: () => usersResponse(store.listUsers()),
  GetUser: (request) => encodeUser(store.getUser(decodeIdRequest(request))),
  CreateUser: (request) => encodeUser(store.createUser(decodeUserInput(request))),
  UpdateUser: (request) => encodeUser(store.updateUser(...decodeUpdateUser(request))),
  DeleteUser: (request) => mutationResult(store.deleteUser(decodeIdRequest(request))),
  ListSongs: () => songsResponse(store.listSongs()),
  GetSong: (request) => encodeSong(store.getSong(decodeIdRequest(request))),
  CreateSong: (request) => encodeSong(store.createSong(decodeSongInput(request))),
  UpdateSong: (request) => encodeSong(store.updateSong(...decodeUpdateSong(request))),
  DeleteSong: (request) => mutationResult(store.deleteSong(decodeIdRequest(request))),
  ListPlaylists: (request) => playlistsResponse(store.listPlaylists(decodePlaylistFilter(request))),
  GetPlaylist: (request) => encodePlaylist(store.getPlaylist(decodeIdRequest(request))),
  CreatePlaylist: (request) => encodePlaylist(store.createPlaylist(decodePlaylistInput(request))),
  UpdatePlaylist: (request) => encodePlaylist(store.updatePlaylist(...decodeUpdatePlaylist(request))),
  DeletePlaylist: (request) => mutationResult(store.deletePlaylist(decodeIdRequest(request))),
  ListUserPlaylists: (request) => playlistsResponse(store.listUserPlaylists(userPlaylistsRequest(request))),
  ListPlaylistSongs: (request) => songsResponse(store.listPlaylistSongs(playlistSongsRequest(request))),
  ListSongPlaylists: (request) => playlistsResponse(store.listSongPlaylists(songPlaylistsRequest(request)))
};

const server = http2.createServer();

server.on("stream", (stream, headers) => {
  Promise.resolve()
    .then(async () => {
      const path = headers[":path"] || "";
      if (!path.startsWith(SERVICE_PREFIX)) {
        throw new DomainError(404, "NOT_FOUND", "Metodo gRPC desconhecido");
      }

      const method = path.slice(SERVICE_PREFIX.length);
      const handler = handlers[method];
      if (!handler) {
        throw new DomainError(404, "NOT_FOUND", `Metodo gRPC desconhecido: ${method}`);
      }

      const request = parseGrpcMessage(await readStream(stream));
      sendGrpc(stream, handler(request));
    })
    .catch((error) => sendGrpcError(stream, error));
});

server.listen(GRPC_PORT, "0.0.0.0", () => {
  console.log(`gRPC JavaScript ouvindo em 0.0.0.0:${GRPC_PORT}`);
});
