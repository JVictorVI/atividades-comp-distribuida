from graphql import build_schema, graphql_sync

from music_service.config import GRAPHQL_PORT
from music_service.domain.music_store import DomainError, MusicStore, plain_error
from music_service.http_utils import (
    MusicHttpHandler,
    create_http_server,
    handle_http_error,
    read_json,
    route_parts,
    run_http_server,
    send_json,
)


store = MusicStore()

SCHEMA = build_schema(
    """
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
    """
)


def bind_resolver(type_name, field_name, resolver):
    SCHEMA.type_map[type_name].fields[field_name].resolve = resolver


bind_resolver("Query", "users", lambda *_: store.list_users())
bind_resolver("Query", "user", lambda _obj, _info, id: store.get_user(id))
bind_resolver("Query", "songs", lambda *_: store.list_songs())
bind_resolver("Query", "song", lambda _obj, _info, id: store.get_song(id))
bind_resolver(
    "Query",
    "playlists",
    lambda _obj, _info, userId=None, songId=None: store.list_playlists(
        {"userId": userId, "songId": songId}
    ),
)
bind_resolver("Query", "playlist", lambda _obj, _info, id: store.get_playlist(id))
bind_resolver("Query", "userPlaylists", lambda _obj, _info, userId: store.list_user_playlists(userId))
bind_resolver("Query", "playlistSongs", lambda _obj, _info, playlistId: store.list_playlist_songs(playlistId))
bind_resolver("Query", "songPlaylists", lambda _obj, _info, songId: store.list_song_playlists(songId))

bind_resolver("Mutation", "reset", lambda *_: store.reset())
bind_resolver("Mutation", "createUser", lambda _obj, _info, input: store.create_user(input))
bind_resolver("Mutation", "updateUser", lambda _obj, _info, id, input: store.update_user(id, input))
bind_resolver("Mutation", "deleteUser", lambda _obj, _info, id: store.delete_user(id))
bind_resolver("Mutation", "createSong", lambda _obj, _info, input: store.create_song(input))
bind_resolver("Mutation", "updateSong", lambda _obj, _info, id, input: store.update_song(id, input))
bind_resolver("Mutation", "deleteSong", lambda _obj, _info, id: store.delete_song(id))
bind_resolver("Mutation", "createPlaylist", lambda _obj, _info, input: store.create_playlist(input))
bind_resolver("Mutation", "updatePlaylist", lambda _obj, _info, id, input: store.update_playlist(id, input))
bind_resolver("Mutation", "deletePlaylist", lambda _obj, _info, id: store.delete_playlist(id))


def graphql_error(error):
    original = getattr(error, "original_error", error)
    formatted = getattr(error, "formatted", {"message": str(error) or "Erro inesperado"})
    content = dict(formatted)
    extensions = dict(content.get("extensions") or {})
    extensions["code"] = getattr(original, "code", extensions.get("code", "INTERNAL_ERROR"))
    content["extensions"] = extensions
    return content


def invalid_query_error():
    return {
        "message": "query e obrigatoria",
        "extensions": {"code": "INVALID_INPUT"},
    }


def execute_graphql(source, variables=None):
    if not isinstance(source, str) or not source.strip():
        raise DomainError(400, "INVALID_INPUT", "query e obrigatoria")

    return graphql_sync(
        SCHEMA,
        source,
        variable_values=variables or {},
    )


class GraphqlHandler(MusicHttpHandler):
    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def handle_request(self):
        try:
            parsed, _parts, _query = route_parts(self)

            if self.command == "GET" and parsed.path == "/health":
                send_json(self, 200, {"ok": True, "technology": "GraphQL Python"})
                return

            if self.command != "POST" or parsed.path != "/graphql":
                send_json(
                    self,
                    404,
                    plain_error(DomainError(404, "NOT_FOUND", "Rota nao encontrada")),
                )
                return

            payload = read_json(self)
            try:
                result = execute_graphql(payload.get("query"), payload.get("variables") or {})
            except DomainError:
                send_json(self, 400, {"data": None, "errors": [invalid_query_error()]})
                return
            except Exception as error:
                send_json(self, 400, {"data": None, "errors": [graphql_error(error)]})
                return

            content = {"data": result.data}
            if result.errors:
                content["errors"] = [graphql_error(error) for error in result.errors]
            send_json(self, 400 if result.errors else 200, content)
        except Exception as error:
            handle_http_error(self, error)


def create_server():
    return create_http_server(GraphqlHandler, GRAPHQL_PORT)


def main():
    run_http_server(GraphqlHandler, GRAPHQL_PORT, "GraphQL Python")


if __name__ == "__main__":
    main()
