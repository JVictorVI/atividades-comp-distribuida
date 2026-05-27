import http from "node:http";

import { GRAPHQL_PORT } from "../config.js";
import { DomainError, MusicStore, plainError } from "../domain/musicStore.js";
import { handleHttpError, readJson, sendJson } from "../httpUtils.js";

const store = new MusicStore();

function compact(value) {
  if (!value || typeof value !== "object") {
    return {};
  }
  return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== undefined));
}

function normalizeQuery(query) {
  return String(query || "").replace(/\s+/g, " ").trim();
}

function hasField(query, fieldName) {
  const escaped = fieldName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(^|[\\s{])${escaped}\\s*(\\(|{|$)`).test(query);
}

function inlineArg(query, fieldName) {
  const match = query.match(new RegExp(`${fieldName}\\s*:\\s*"?([A-Za-z0-9_-]+)"?`));
  return match ? match[1] : undefined;
}

function executeGraphql(rawQuery, variables = {}) {
  const query = normalizeQuery(rawQuery);
  const data = {};

  if (!query) {
    throw new DomainError(400, "INVALID_INPUT", "query e obrigatoria");
  }

  if (query.includes("mutation")) {
    if (hasField(query, "reset")) {
      data.reset = store.reset();
    } else if (hasField(query, "createUser")) {
      data.createUser = store.createUser(variables.input || {});
    } else if (hasField(query, "updateUser")) {
      data.updateUser = store.updateUser(variables.id || inlineArg(query, "id"), variables.input || {});
    } else if (hasField(query, "deleteUser")) {
      data.deleteUser = store.deleteUser(variables.id || inlineArg(query, "id"));
    } else if (hasField(query, "createSong")) {
      data.createSong = store.createSong(variables.input || {});
    } else if (hasField(query, "updateSong")) {
      data.updateSong = store.updateSong(variables.id || inlineArg(query, "id"), variables.input || {});
    } else if (hasField(query, "deleteSong")) {
      data.deleteSong = store.deleteSong(variables.id || inlineArg(query, "id"));
    } else if (hasField(query, "createPlaylist")) {
      data.createPlaylist = store.createPlaylist(variables.input || {});
    } else if (hasField(query, "updatePlaylist")) {
      data.updatePlaylist = store.updatePlaylist(variables.id || inlineArg(query, "id"), variables.input || {});
    } else if (hasField(query, "deletePlaylist")) {
      data.deletePlaylist = store.deletePlaylist(variables.id || inlineArg(query, "id"));
    } else {
      throw new DomainError(400, "UNKNOWN_OPERATION", "Mutacao GraphQL desconhecida");
    }
    return data;
  }

  if (hasField(query, "users")) {
    data.users = store.listUsers();
  }
  if (hasField(query, "user")) {
    data.user = store.getUser(variables.id || inlineArg(query, "id"));
  }
  if (hasField(query, "songs")) {
    data.songs = store.listSongs();
  }
  if (hasField(query, "song")) {
    data.song = store.getSong(variables.id || inlineArg(query, "id"));
  }
  if (hasField(query, "playlists")) {
    data.playlists = store.listPlaylists(compact({
      userId: variables.userId || inlineArg(query, "userId"),
      songId: variables.songId || inlineArg(query, "songId")
    }));
  }
  if (hasField(query, "playlist")) {
    data.playlist = store.getPlaylist(variables.id || inlineArg(query, "id"));
  }
  if (hasField(query, "userPlaylists")) {
    data.userPlaylists = store.listUserPlaylists(variables.userId || inlineArg(query, "userId"));
  }
  if (hasField(query, "playlistSongs")) {
    data.playlistSongs = store.listPlaylistSongs(variables.playlistId || inlineArg(query, "playlistId"));
  }
  if (hasField(query, "songPlaylists")) {
    data.songPlaylists = store.listSongPlaylists(variables.songId || inlineArg(query, "songId"));
  }

  if (Object.keys(data).length === 0) {
    throw new DomainError(400, "UNKNOWN_OPERATION", "Consulta GraphQL desconhecida");
  }

  return data;
}

function graphQlError(error) {
  return {
    message: error.message || "Erro inesperado",
    extensions: {
      code: error.code || "INTERNAL_ERROR"
    }
  };
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
        sendJson(response, 200, {
          data: executeGraphql(payload.query, payload.variables || {})
        });
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
