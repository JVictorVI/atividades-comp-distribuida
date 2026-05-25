from __future__ import annotations

from copy import deepcopy
from threading import RLock


class DomainError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code


INITIAL_DATA = {
    "users": [
        {"id": "u1", "name": "Ana Costa", "email": "ana@example.com"},
        {"id": "u2", "name": "Bruno Lima", "email": "bruno@example.com"},
        {"id": "u3", "name": "Carla Souza", "email": "carla@example.com"},
    ],
    "songs": [
        {
            "id": "s1",
            "title": "Azul Solar",
            "artist": "Marina Norte",
            "album": "Horizonte",
            "durationSeconds": 214,
        },
        {
            "id": "s2",
            "title": "Noite Curta",
            "artist": "Os Vetores",
            "album": "Cidade Acesa",
            "durationSeconds": 188,
        },
        {
            "id": "s3",
            "title": "Eco de Domingo",
            "artist": "Lia Ramos",
            "album": "Casa Aberta",
            "durationSeconds": 241,
        },
        {
            "id": "s4",
            "title": "Linha do Mar",
            "artist": "Davi Prado",
            "album": "Corrente",
            "durationSeconds": 203,
        },
        {
            "id": "s5",
            "title": "Baixo Contorno",
            "artist": "Trio Aurora",
            "album": "Depois das Seis",
            "durationSeconds": 267,
        },
    ],
    "playlists": [
        {"id": "p1", "userId": "u1", "name": "Manhã leve", "songIds": ["s1", "s3", "s4"]},
        {"id": "p2", "userId": "u1", "name": "Foco", "songIds": ["s2", "s5"]},
        {"id": "p3", "userId": "u2", "name": "Viagem", "songIds": ["s1", "s2", "s4"]},
    ],
}


def _clone(value):
    return deepcopy(value)


def _require_string(value, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DomainError(400, "INVALID_INPUT", f"{field_name} é obrigatório")
    return value.strip()


def _optional_string(value, field_name: str):
    if value is None:
        return None
    return _require_string(value, field_name)


def _require_positive_number(value, field_name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise DomainError(400, "INVALID_INPUT", f"{field_name} deve ser positivo") from None

    if number <= 0:
        raise DomainError(400, "INVALID_INPUT", f"{field_name} deve ser positivo")
    return number


def _normalize_song_ids(song_ids) -> list[str]:
    if song_ids is None:
        return []
    if isinstance(song_ids, str):
        return [song_id.strip() for song_id in song_ids.split(",") if song_id.strip()]
    if not isinstance(song_ids, list):
        raise DomainError(400, "INVALID_INPUT", "songIds deve ser lista ou texto separado por vírgulas")
    return [_require_string(song_id, "songId") for song_id in song_ids]


class MusicStore:
    def __init__(self):
        self._lock = RLock()
        self.reset()

    def reset(self):
        with self._lock:
            self.users = {item["id"]: _clone(item) for item in INITIAL_DATA["users"]}
            self.songs = {item["id"]: _clone(item) for item in INITIAL_DATA["songs"]}
            self.playlists = {item["id"]: _clone(item) for item in INITIAL_DATA["playlists"]}
            self.counters = {
                "user": len(self.users) + 1,
                "song": len(self.songs) + 1,
                "playlist": len(self.playlists) + 1,
            }
            return {"ok": True}

    def _next_id(self, kind: str) -> str:
        prefixes = {"user": "u", "song": "s", "playlist": "p"}
        item_id = f"{prefixes[kind]}{self.counters[kind]}"
        self.counters[kind] += 1
        return item_id

    @staticmethod
    def _list_values(items):
        return [_clone(item) for item in items.values()]

    @staticmethod
    def _assert_exists(items, item_id: str, item_type: str):
        if item_id not in items:
            raise DomainError(404, "NOT_FOUND", f"{item_type} {item_id} não encontrado")

    def list_users(self):
        with self._lock:
            return self._list_values(self.users)

    def get_user(self, user_id: str):
        with self._lock:
            self._assert_exists(self.users, user_id, "Usuário")
            return _clone(self.users[user_id])

    def create_user(self, data):
        with self._lock:
            user = {
                "id": self._next_id("user"),
                "name": _require_string((data or {}).get("name"), "name"),
                "email": _require_string((data or {}).get("email"), "email"),
            }
            self.users[user["id"]] = user
            return _clone(user)

    def update_user(self, user_id: str, data):
        with self._lock:
            self._assert_exists(self.users, user_id, "Usuário")
            current = self.users[user_id]
            updated = {
                **current,
                "name": _optional_string((data or {}).get("name"), "name") or current["name"],
                "email": _optional_string((data or {}).get("email"), "email") or current["email"],
            }
            self.users[user_id] = updated
            return _clone(updated)

    def delete_user(self, user_id: str):
        with self._lock:
            self._assert_exists(self.users, user_id, "Usuário")
            del self.users[user_id]
            self.playlists = {
                playlist_id: playlist
                for playlist_id, playlist in self.playlists.items()
                if playlist["userId"] != user_id
            }
            return {"ok": True}

    def list_songs(self):
        with self._lock:
            return self._list_values(self.songs)

    def get_song(self, song_id: str):
        with self._lock:
            self._assert_exists(self.songs, song_id, "Música")
            return _clone(self.songs[song_id])

    def create_song(self, data):
        with self._lock:
            song = {
                "id": self._next_id("song"),
                "title": _require_string((data or {}).get("title"), "title"),
                "artist": _require_string((data or {}).get("artist"), "artist"),
                "album": _require_string((data or {}).get("album"), "album"),
                "durationSeconds": _require_positive_number((data or {}).get("durationSeconds"), "durationSeconds"),
            }
            self.songs[song["id"]] = song
            return _clone(song)

    def update_song(self, song_id: str, data):
        with self._lock:
            self._assert_exists(self.songs, song_id, "Música")
            current = self.songs[song_id]
            duration = (data or {}).get("durationSeconds")
            updated = {
                **current,
                "title": _optional_string((data or {}).get("title"), "title") or current["title"],
                "artist": _optional_string((data or {}).get("artist"), "artist") or current["artist"],
                "album": _optional_string((data or {}).get("album"), "album") or current["album"],
                "durationSeconds": current["durationSeconds"]
                if duration is None
                else _require_positive_number(duration, "durationSeconds"),
            }
            self.songs[song_id] = updated
            return _clone(updated)

    def delete_song(self, song_id: str):
        with self._lock:
            self._assert_exists(self.songs, song_id, "Música")
            del self.songs[song_id]
            for playlist in self.playlists.values():
                playlist["songIds"] = [current_id for current_id in playlist["songIds"] if current_id != song_id]
            return {"ok": True}

    def list_playlists(self, filters=None):
        with self._lock:
            filters = filters or {}
            user_id = filters.get("userId") or None
            song_id = filters.get("songId") or None

            if user_id:
                self._assert_exists(self.users, user_id, "Usuário")
            if song_id:
                self._assert_exists(self.songs, song_id, "Música")

            playlists = self._list_values(self.playlists)
            return [
                playlist
                for playlist in playlists
                if (not user_id or playlist["userId"] == user_id)
                and (not song_id or song_id in playlist["songIds"])
            ]

    def get_playlist(self, playlist_id: str):
        with self._lock:
            self._assert_exists(self.playlists, playlist_id, "Playlist")
            return _clone(self.playlists[playlist_id])

    def create_playlist(self, data):
        with self._lock:
            data = data or {}
            user_id = _require_string(data.get("userId"), "userId")
            song_ids = _normalize_song_ids(data.get("songIds"))
            self._assert_exists(self.users, user_id, "Usuário")
            for song_id in song_ids:
                self._assert_exists(self.songs, song_id, "Música")

            playlist = {
                "id": self._next_id("playlist"),
                "userId": user_id,
                "name": _require_string(data.get("name"), "name"),
                "songIds": song_ids,
            }
            self.playlists[playlist["id"]] = playlist
            return _clone(playlist)

    def update_playlist(self, playlist_id: str, data):
        with self._lock:
            data = data or {}
            self._assert_exists(self.playlists, playlist_id, "Playlist")
            current = self.playlists[playlist_id]
            user_id = _optional_string(data.get("userId"), "userId") or current["userId"]
            song_ids = current["songIds"] if data.get("songIds") is None else _normalize_song_ids(data.get("songIds"))

            self._assert_exists(self.users, user_id, "Usuário")
            for song_id in song_ids:
                self._assert_exists(self.songs, song_id, "Música")

            updated = {
                **current,
                "userId": user_id,
                "name": _optional_string(data.get("name"), "name") or current["name"],
                "songIds": song_ids,
            }
            self.playlists[playlist_id] = updated
            return _clone(updated)

    def delete_playlist(self, playlist_id: str):
        with self._lock:
            self._assert_exists(self.playlists, playlist_id, "Playlist")
            del self.playlists[playlist_id]
            return {"ok": True}

    def list_user_playlists(self, user_id: str):
        with self._lock:
            self._assert_exists(self.users, user_id, "Usuário")
            return [playlist for playlist in self._list_values(self.playlists) if playlist["userId"] == user_id]

    def list_playlist_songs(self, playlist_id: str):
        with self._lock:
            self._assert_exists(self.playlists, playlist_id, "Playlist")
            return [
                _clone(self.songs[song_id])
                for song_id in self.playlists[playlist_id]["songIds"]
                if song_id in self.songs
            ]

    def list_song_playlists(self, song_id: str):
        with self._lock:
            self._assert_exists(self.songs, song_id, "Música")
            return [
                playlist
                for playlist in self._list_values(self.playlists)
                if song_id in playlist["songIds"]
            ]


def plain_error(error: Exception):
    return {
        "error": {
            "code": getattr(error, "code", "INTERNAL_ERROR"),
            "message": str(error) or "Erro inesperado",
        }
    }
