import grpc from "@grpc/grpc-js";
import protoLoader from "@grpc/proto-loader";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { GRPC_PORT } from "../config.js";
import { DomainError, MusicStore } from "../domain/musicStore.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROTO_PATH = resolve(__dirname, "../../../proto/music.proto");

const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: false,
  oneofs: true
});
const proto = grpc.loadPackageDefinition(packageDefinition).music;
const store = new MusicStore();

function grpcStatus(error) {
  if (error instanceof DomainError) {
    return error.status === 404 ? grpc.status.NOT_FOUND : grpc.status.INVALID_ARGUMENT;
  }
  return grpc.status.INTERNAL;
}

function callbackError(callback, error) {
  callback({
    code: grpcStatus(error),
    message: error.message || "Erro inesperado"
  });
}

function compact(data) {
  return Object.fromEntries(
    Object.entries(data).filter(([, value]) => {
      if (Array.isArray(value)) {
        return value.length > 0;
      }
      return value !== "" && value !== 0 && value !== null && value !== undefined;
    })
  );
}

function unary(handler) {
  return (call, callback) => {
    try {
      callback(null, handler(call.request || {}));
    } catch (error) {
      callbackError(callback, error);
    }
  };
}

function songInput(request) {
  return {
    title: request.title,
    artist: request.artist,
    album: request.album,
    durationSeconds: request.durationSeconds
  };
}

function playlistInput(request) {
  return {
    userId: request.userId,
    name: request.name,
    songIds: request.songIds || []
  };
}

const handlers = {
  Reset: unary(() => store.reset()),
  ListUsers: unary(() => ({ users: store.listUsers() })),
  GetUser: unary((request) => store.getUser(request.id)),
  CreateUser: unary((request) => store.createUser(request)),
  UpdateUser: unary((request) => store.updateUser(request.id, compact(request.user || {}))),
  DeleteUser: unary((request) => store.deleteUser(request.id)),
  ListSongs: unary(() => ({ songs: store.listSongs() })),
  GetSong: unary((request) => store.getSong(request.id)),
  CreateSong: unary((request) => store.createSong(songInput(request))),
  UpdateSong: unary((request) => store.updateSong(request.id, compact(request.song || {}))),
  DeleteSong: unary((request) => store.deleteSong(request.id)),
  ListPlaylists: unary((request) => ({
    playlists: store.listPlaylists(compact({ userId: request.userId, songId: request.songId }))
  })),
  GetPlaylist: unary((request) => store.getPlaylist(request.id)),
  CreatePlaylist: unary((request) => store.createPlaylist(playlistInput(request))),
  UpdatePlaylist: unary((request) => store.updatePlaylist(request.id, compact(request.playlist || {}))),
  DeletePlaylist: unary((request) => store.deletePlaylist(request.id)),
  ListUserPlaylists: unary((request) => ({ playlists: store.listUserPlaylists(request.userId) })),
  ListPlaylistSongs: unary((request) => ({ songs: store.listPlaylistSongs(request.playlistId) })),
  ListSongPlaylists: unary((request) => ({ playlists: store.listSongPlaylists(request.songId) }))
};

const server = new grpc.Server();
server.addService(proto.MusicStreaming.service, handlers);
server.bindAsync(`0.0.0.0:${GRPC_PORT}`, grpc.ServerCredentials.createInsecure(), (error, port) => {
  if (error) {
    console.error(error);
    process.exit(1);
  }
  console.log(`gRPC JavaScript ouvindo em 0.0.0.0:${port}`);
});
