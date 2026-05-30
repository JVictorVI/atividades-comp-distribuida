from music_service.config import REST_PORT
from music_service.domain.music_store import MusicStore
from music_service.http_utils import (
    MusicHttpHandler,
    create_http_server,
    handle_http_error,
    method_not_allowed,
    not_found,
    read_json,
    route_parts,
    run_http_server,
    send_json,
)


store = MusicStore()


class RestHandler(MusicHttpHandler):
    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_PUT(self):
        self.handle_request()

    def do_DELETE(self):
        self.handle_request()

    def handle_request(self):
        try:
            _url, parts, query = route_parts(self)
            method = self.command or "GET"

            if method == "GET" and parts == ["health"]:
                send_json(self, 200, {"ok": True, "technology": "REST Python"})
                return

            if method == "POST" and parts == ["reset"]:
                send_json(self, 200, store.reset())
                return

            if parts and parts[0] == "users":
                self.handle_users(method, parts)
                return

            if parts and parts[0] == "songs":
                self.handle_songs(method, parts)
                return

            if parts and parts[0] == "playlists":
                self.handle_playlists(method, parts, query)
                return

            not_found(self)
        except Exception as error:
            handle_http_error(self, error)

    def handle_users(self, method: str, parts: list[str]):
        if len(parts) == 1:
            if method == "GET":
                send_json(self, 200, store.list_users())
                return
            if method == "POST":
                send_json(self, 201, store.create_user(read_json(self)))
                return
            method_not_allowed(self)
            return

        user_id = parts[1]
        if len(parts) == 3 and parts[2] == "playlists":
            if method == "GET":
                send_json(self, 200, store.list_user_playlists(user_id))
                return
            method_not_allowed(self)
            return

        if len(parts) == 2:
            if method == "GET":
                send_json(self, 200, store.get_user(user_id))
                return
            if method == "PUT":
                send_json(self, 200, store.update_user(user_id, read_json(self)))
                return
            if method == "DELETE":
                send_json(self, 200, store.delete_user(user_id))
                return
            method_not_allowed(self)
            return

        not_found(self)

    def handle_songs(self, method: str, parts: list[str]):
        if len(parts) == 1:
            if method == "GET":
                send_json(self, 200, store.list_songs())
                return
            if method == "POST":
                send_json(self, 201, store.create_song(read_json(self)))
                return
            method_not_allowed(self)
            return

        song_id = parts[1]
        if len(parts) == 3 and parts[2] == "playlists":
            if method == "GET":
                send_json(self, 200, store.list_song_playlists(song_id))
                return
            method_not_allowed(self)
            return

        if len(parts) == 2:
            if method == "GET":
                send_json(self, 200, store.get_song(song_id))
                return
            if method == "PUT":
                send_json(self, 200, store.update_song(song_id, read_json(self)))
                return
            if method == "DELETE":
                send_json(self, 200, store.delete_song(song_id))
                return
            method_not_allowed(self)
            return

        not_found(self)

    def handle_playlists(self, method: str, parts: list[str], query: dict):
        if len(parts) == 1:
            if method == "GET":
                send_json(
                    self,
                    200,
                    store.list_playlists(
                        {
                            "userId": query.get("userId"),
                            "songId": query.get("songId"),
                        }
                    ),
                )
                return
            if method == "POST":
                send_json(self, 201, store.create_playlist(read_json(self)))
                return
            method_not_allowed(self)
            return

        playlist_id = parts[1]
        if len(parts) == 3 and parts[2] == "songs":
            if method == "GET":
                send_json(self, 200, store.list_playlist_songs(playlist_id))
                return
            method_not_allowed(self)
            return

        if len(parts) == 2:
            if method == "GET":
                send_json(self, 200, store.get_playlist(playlist_id))
                return
            if method == "PUT":
                send_json(self, 200, store.update_playlist(playlist_id, read_json(self)))
                return
            if method == "DELETE":
                send_json(self, 200, store.delete_playlist(playlist_id))
                return
            method_not_allowed(self)
            return

        not_found(self)


def create_server():
    return create_http_server(RestHandler, REST_PORT)


def main():
    run_http_server(RestHandler, REST_PORT, "REST Python")


if __name__ == "__main__":
    main()
