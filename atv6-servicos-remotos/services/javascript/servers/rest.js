import http from "node:http";

import { REST_PORT } from "../config.js";
import { MusicStore } from "../domain/musicStore.js";
import {
  handleHttpError,
  methodNotAllowed,
  notFound,
  readJson,
  routeParts,
  sendJson
} from "../httpUtils.js";

const store = new MusicStore();

function runHandler(request, response, handler) {
  Promise.resolve()
    .then(handler)
    .catch((error) => handleHttpError(response, error));
}

const server = http.createServer((request, response) => {
  const { url, parts } = routeParts(request);
  const method = request.method || "GET";

  runHandler(request, response, async () => {
    if (method === "GET" && parts.length === 1 && parts[0] === "health") {
      sendJson(response, 200, { ok: true, technology: "REST JavaScript" });
      return;
    }

    if (method === "POST" && parts.length === 1 && parts[0] === "reset") {
      sendJson(response, 200, store.reset());
      return;
    }

    if (parts[0] === "users") {
      if (parts.length === 1) {
        if (method === "GET") {
          sendJson(response, 200, store.listUsers());
          return;
        }
        if (method === "POST") {
          sendJson(response, 201, store.createUser(await readJson(request)));
          return;
        }
        methodNotAllowed(response);
        return;
      }

      const userId = parts[1];
      if (parts.length === 3 && parts[2] === "playlists") {
        if (method === "GET") {
          sendJson(response, 200, store.listUserPlaylists(userId));
          return;
        }
        methodNotAllowed(response);
        return;
      }

      if (parts.length === 2) {
        if (method === "GET") {
          sendJson(response, 200, store.getUser(userId));
          return;
        }
        if (method === "PUT") {
          sendJson(response, 200, store.updateUser(userId, await readJson(request)));
          return;
        }
        if (method === "DELETE") {
          sendJson(response, 200, store.deleteUser(userId));
          return;
        }
        methodNotAllowed(response);
        return;
      }
    }

    if (parts[0] === "songs") {
      if (parts.length === 1) {
        if (method === "GET") {
          sendJson(response, 200, store.listSongs());
          return;
        }
        if (method === "POST") {
          sendJson(response, 201, store.createSong(await readJson(request)));
          return;
        }
        methodNotAllowed(response);
        return;
      }

      const songId = parts[1];
      if (parts.length === 3 && parts[2] === "playlists") {
        if (method === "GET") {
          sendJson(response, 200, store.listSongPlaylists(songId));
          return;
        }
        methodNotAllowed(response);
        return;
      }

      if (parts.length === 2) {
        if (method === "GET") {
          sendJson(response, 200, store.getSong(songId));
          return;
        }
        if (method === "PUT") {
          sendJson(response, 200, store.updateSong(songId, await readJson(request)));
          return;
        }
        if (method === "DELETE") {
          sendJson(response, 200, store.deleteSong(songId));
          return;
        }
        methodNotAllowed(response);
        return;
      }
    }

    if (parts[0] === "playlists") {
      if (parts.length === 1) {
        if (method === "GET") {
          sendJson(response, 200, store.listPlaylists({
            userId: url.searchParams.get("userId"),
            songId: url.searchParams.get("songId")
          }));
          return;
        }
        if (method === "POST") {
          sendJson(response, 201, store.createPlaylist(await readJson(request)));
          return;
        }
        methodNotAllowed(response);
        return;
      }

      const playlistId = parts[1];
      if (parts.length === 3 && parts[2] === "songs") {
        if (method === "GET") {
          sendJson(response, 200, store.listPlaylistSongs(playlistId));
          return;
        }
        methodNotAllowed(response);
        return;
      }

      if (parts.length === 2) {
        if (method === "GET") {
          sendJson(response, 200, store.getPlaylist(playlistId));
          return;
        }
        if (method === "PUT") {
          sendJson(response, 200, store.updatePlaylist(playlistId, await readJson(request)));
          return;
        }
        if (method === "DELETE") {
          sendJson(response, 200, store.deletePlaylist(playlistId));
          return;
        }
        methodNotAllowed(response);
        return;
      }
    }

    notFound(response);
  });
});

server.listen(REST_PORT, "0.0.0.0", () => {
  console.log(`REST JavaScript ouvindo em 0.0.0.0:${REST_PORT}`);
});
