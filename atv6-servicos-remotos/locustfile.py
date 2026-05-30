import html
import itertools
import os
import re
import sys
import time
from pathlib import Path

import grpc
from locust import HttpUser, User, tag, task

PYTHON_SERVICE_DIR = Path(__file__).resolve().parent / "services" / "python"
if PYTHON_SERVICE_DIR.exists():
    sys.path.insert(0, str(PYTHON_SERVICE_DIR))

from music_service.generated import music_pb2, music_pb2_grpc

try:
    from grpc.experimental import gevent as grpc_gevent

    grpc_gevent.init_gevent()
except Exception:
    pass


REST_HOST = os.getenv("REST_HOST", "http://localhost:3000")
GRAPHQL_HOST = os.getenv("GRAPHQL_HOST", "http://localhost:3001")
SOAP_HOST = os.getenv("SOAP_HOST", "http://localhost:3002")
GRPC_TARGET = os.getenv("GRPC_TARGET", "localhost:50051")
USER_ID = "u1"
SONG_ID = "s1"
PLAYLIST_ID = "p1"


def next_item(counter, items):
    return items[next(counter) % len(items)]


def check_json_response(response):
    if response.status_code >= 400:
        return None

    try:
        payload = response.json()
    except ValueError:
        return None

    if isinstance(payload, dict) and payload.get("errors"):
        return None

    return payload


class MusicHttpUser(HttpUser):
    abstract = True

    def on_start(self):
        self.catalog_counter = itertools.count()


class RestApiUser(MusicHttpUser):
    host = REST_HOST

    @tag("catalogo")
    @task
    def catalogo_leitura(self):
        path, name = next_item(
            self.catalog_counter,
            [
                ("/users", "REST/listar-usuarios"),
                ("/songs", "REST/listar-musicas"),
                (f"/users/{USER_ID}/playlists", "REST/listar-playlists-usuario"),
                (f"/playlists/{PLAYLIST_ID}/songs", "REST/listar-musicas-playlist"),
                (f"/songs/{SONG_ID}/playlists", "REST/listar-playlists-musica"),
            ],
        )
        self.client.get(path, name=name)


GRAPHQL_QUERIES = {
    "users": ("query { users { id name email } }", "GraphQL/listar-usuarios"),
    "songs": ("query { songs { id title artist album durationSeconds } }", "GraphQL/listar-musicas"),
    "user_playlists": (
        f'query {{ userPlaylists(userId: "{USER_ID}") {{ id userId name songIds }} }}',
        "GraphQL/listar-playlists-usuario",
    ),
    "playlist_songs": (
        f'query {{ playlistSongs(playlistId: "{PLAYLIST_ID}") {{ id title artist album durationSeconds }} }}',
        "GraphQL/listar-musicas-playlist",
    ),
    "song_playlists": (
        f'query {{ songPlaylists(songId: "{SONG_ID}") {{ id userId name songIds }} }}',
        "GraphQL/listar-playlists-musica",
    ),
}


class GraphqlApiUser(MusicHttpUser):
    host = GRAPHQL_HOST

    def graphql(self, query, name):
        with self.client.post(
            "/graphql",
            json={"query": query, "variables": {}},
            name=name,
            catch_response=True,
        ) as response:
            return check_json_response(response)

    @tag("catalogo")
    @task
    def catalogo_leitura(self):
        query, name = next_item(
            self.catalog_counter,
            [
                GRAPHQL_QUERIES["users"],
                GRAPHQL_QUERIES["songs"],
                GRAPHQL_QUERIES["user_playlists"],
                GRAPHQL_QUERIES["playlist_songs"],
                GRAPHQL_QUERIES["song_playlists"],
            ],
        )
        self.graphql(query, name=name)


def soap_fields(fields):
    return "".join(f"<{key}>{html.escape(str(value))}</{key}>" for key, value in (fields or {}).items())


def soap_envelope(operation, fields=None):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="http://example.com/music-streaming">
  <soapenv:Header/>
  <soapenv:Body>
    <tns:{operation}>{soap_fields(fields)}</tns:{operation}>
  </soapenv:Body>
</soapenv:Envelope>"""


def parse_soap_payload(text):
    match = re.search(r"<payload[^>]*>([\s\S]*?)</payload>", text)
    if not match:
        return None

    return match.group(1)


class SoapApiUser(MusicHttpUser):
    host = SOAP_HOST

    def soap(self, operation, name, fields=None):
        with self.client.post(
            "/soap",
            data=soap_envelope(operation, fields),
            headers={
                "content-type": "text/xml; charset=utf-8",
                "soapaction": f"urn:{operation}",
            },
            name=name,
            catch_response=True,
        ) as response:
            if response.status_code >= 400:
                return None

            parsed_payload = parse_soap_payload(response.text)
            if "<success>true</success>" not in response.text:
                return None

            return parsed_payload

    @tag("catalogo")
    @task
    def catalogo_leitura(self):
        operation, name, fields = next_item(
            self.catalog_counter,
            [
                ("ListUsers", "SOAP/listar-usuarios", None),
                ("ListSongs", "SOAP/listar-musicas", None),
                ("ListUserPlaylists", "SOAP/listar-playlists-usuario", {"userId": USER_ID}),
                ("ListPlaylistSongs", "SOAP/listar-musicas-playlist", {"playlistId": PLAYLIST_ID}),
                ("ListSongPlaylists", "SOAP/listar-playlists-musica", {"songId": SONG_ID}),
            ],
        )
        self.soap(operation, name=name, fields=fields)


class GrpcMusicUser(User):
    def on_start(self):
        self.catalog_counter = itertools.count()
        self.channel = grpc.insecure_channel(GRPC_TARGET)
        self.stub = music_pb2_grpc.MusicStreamingStub(self.channel)

    def on_stop(self):
        self.channel.close()

    def grpc_call(self, method, name, payload):
        started = time.perf_counter()
        response = None
        exception = None

        try:
            response = method(payload, timeout=10)
        except Exception as exc:
            exception = exc

        response_length = response.ByteSize() if response is not None else 0
        self.environment.events.request.fire(
            request_type="gRPC",
            name=name,
            response_time=(time.perf_counter() - started) * 1000,
            response_length=response_length,
            response=response,
            context={},
            exception=exception,
        )

    @tag("catalogo")
    @task
    def catalogo_leitura(self):
        method, name, payload = next_item(
            self.catalog_counter,
            [
                (self.stub.ListUsers, "gRPC/listar-usuarios", music_pb2.Empty()),
                (self.stub.ListSongs, "gRPC/listar-musicas", music_pb2.Empty()),
                (
                    self.stub.ListUserPlaylists,
                    "gRPC/listar-playlists-usuario",
                    music_pb2.UserPlaylistsRequest(userId=USER_ID),
                ),
                (
                    self.stub.ListPlaylistSongs,
                    "gRPC/listar-musicas-playlist",
                    music_pb2.PlaylistSongsRequest(playlistId=PLAYLIST_ID),
                ),
                (
                    self.stub.ListSongPlaylists,
                    "gRPC/listar-playlists-musica",
                    music_pb2.SongPlaylistsRequest(songId=SONG_ID),
                ),
            ],
        )
        self.grpc_call(method, name=name, payload=payload)
