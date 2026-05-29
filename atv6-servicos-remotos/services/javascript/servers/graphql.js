import http from "node:http";

import { buildSchema, graphqlSync } from "graphql";

import { GRAPHQL_PORT } from "../config.js";
import { DomainError, MusicStore, plainError } from "../domain/musicStore.js";
import { handleHttpError, readJson, sendJson } from "../httpUtils.js";

const store = new MusicStore();

const schema = buildSchema(`
  type User {
    id: ID!
    name: String!
    email: String!
  }

  type Song {
    id: ID!
    title: String!
    artist: String!
    album: String!
    durationSeconds: Int!
  }

  type Playlist {
    id: ID!
    userId: ID!
    name: String!
    songIds: [ID!]!
  }

  input UserInput {
    name: String!
    email: String!
  }

  input UserPatch {
    name: String
    email: String
  }

  input SongInput {
    title: String!
    artist: String!
    album: String!
    durationSeconds: Int!
  }

  input SongPatch {
    title: String
    artist: String
    album: String
    durationSeconds: Int
  }

  input PlaylistInput {
    userId: ID!
    name: String!
    songIds: [ID!]!
  }

  input PlaylistPatch {
    userId: ID
    name: String
    songIds: [ID!]
  }

  type MutationResult {
    ok: Boolean!
  }

  type Query {
    users: [User!]!
    user(id: ID!): User!
    songs: [Song!]!
    song(id: ID!): Song!
    playlists(userId: ID, songId: ID): [Playlist!]!
    playlist(id: ID!): Playlist!
    userPlaylists(userId: ID!): [Playlist!]!
    playlistSongs(playlistId: ID!): [Song!]!
    songPlaylists(songId: ID!): [Playlist!]!
  }

  type Mutation {
    reset: MutationResult!
    createUser(input: UserInput!): User!
    updateUser(id: ID!, input: UserPatch!): User!
    deleteUser(id: ID!): MutationResult!
    createSong(input: SongInput!): Song!
    updateSong(id: ID!, input: SongPatch!): Song!
    deleteSong(id: ID!): MutationResult!
    createPlaylist(input: PlaylistInput!): Playlist!
    updatePlaylist(id: ID!, input: PlaylistPatch!): Playlist!
    deletePlaylist(id: ID!): MutationResult!
  }
`);

function bindResolver(typeName, fieldName, resolver) {
  schema.getType(typeName).getFields()[fieldName].resolve = resolver;
}

bindResolver("Query", "users", () => store.listUsers());
bindResolver("Query", "user", (_source, args) => store.getUser(args.id));
bindResolver("Query", "songs", () => store.listSongs());
bindResolver("Query", "song", (_source, args) => store.getSong(args.id));
bindResolver("Query", "playlists", (_source, args) => store.listPlaylists(args));
bindResolver("Query", "playlist", (_source, args) => store.getPlaylist(args.id));
bindResolver("Query", "userPlaylists", (_source, args) => store.listUserPlaylists(args.userId));
bindResolver("Query", "playlistSongs", (_source, args) => store.listPlaylistSongs(args.playlistId));
bindResolver("Query", "songPlaylists", (_source, args) => store.listSongPlaylists(args.songId));

bindResolver("Mutation", "reset", () => store.reset());
bindResolver("Mutation", "createUser", (_source, args) => store.createUser(args.input));
bindResolver("Mutation", "updateUser", (_source, args) => store.updateUser(args.id, args.input));
bindResolver("Mutation", "deleteUser", (_source, args) => store.deleteUser(args.id));
bindResolver("Mutation", "createSong", (_source, args) => store.createSong(args.input));
bindResolver("Mutation", "updateSong", (_source, args) => store.updateSong(args.id, args.input));
bindResolver("Mutation", "deleteSong", (_source, args) => store.deleteSong(args.id));
bindResolver("Mutation", "createPlaylist", (_source, args) => store.createPlaylist(args.input));
bindResolver("Mutation", "updatePlaylist", (_source, args) => store.updatePlaylist(args.id, args.input));
bindResolver("Mutation", "deletePlaylist", (_source, args) => store.deletePlaylist(args.id));

function graphQlError(error) {
  const original = error.originalError || error;
  const formatted = {
    message: error.message || "Erro inesperado",
    extensions: {
      code: original.code || "INTERNAL_ERROR"
    }
  };

  if (error.locations) {
    formatted.locations = error.locations;
  }
  if (error.path) {
    formatted.path = error.path;
  }

  return formatted;
}

function executeGraphql(source, variables = {}) {
  if (typeof source !== "string" || source.trim() === "") {
    throw new DomainError(400, "INVALID_INPUT", "query e obrigatoria");
  }

  return graphqlSync({
    schema,
    source,
    variableValues: variables
  });
}

const server = http.createServer((request, response) => {
  const url = new URL(request.url, "http://localhost");

  Promise.resolve()
    .then(async () => {
      if (request.method === "GET" && url.pathname === "/health") {
        sendJson(response, 200, { ok: true, technology: "GraphQL JavaScript" });
        return;
      }

      if (request.method !== "POST" || url.pathname !== "/graphql") {
        sendJson(response, 404, plainError(new DomainError(404, "NOT_FOUND", "Rota nao encontrada")));
        return;
      }

      const payload = await readJson(request);
      try {
        const result = executeGraphql(payload.query, payload.variables || {});
        const content = { data: result.data };
        if (result.errors) {
          content.errors = result.errors.map(graphQlError);
        }
        sendJson(response, result.errors ? 400 : 200, content);
      } catch (error) {
        sendJson(response, 400, {
          data: null,
          errors: [graphQlError(error)]
        });
      }
    })
    .catch((error) => handleHttpError(response, error));
});

server.listen(GRAPHQL_PORT, "0.0.0.0", () => {
  console.log(`GraphQL JavaScript ouvindo em 0.0.0.0:${GRAPHQL_PORT}`);
});
