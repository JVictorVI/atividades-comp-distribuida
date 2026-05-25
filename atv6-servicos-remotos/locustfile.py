import html
import itertools
import json
import os
import re
import time
import uuid

import grpc
from locust import HttpUser, User, tag, task

try:
    from grpc.experimental import gevent as grpc_gevent

    grpc_gevent.init_gevent()
except Exception:
    pass


REST_HOST = os.getenv("REST_HOST", "http://localhost:3000")
GRAPHQL_HOST = os.getenv("GRAPHQL_HOST", "http://localhost:3001")
SOAP_HOST = os.getenv("SOAP_HOST", "http://localhost:3002")
GRPC_TARGET = os.getenv("GRPC_TARGET", "localhost:50051")


def unique_user(prefix):
    suffix = uuid.uuid4().hex[:12]
    return {
        "name": f"Carga {prefix} {suffix}",
        "email": f"load-{prefix.lower()}-{suffix}@example.com",
    }


def next_item(counter, items):
    return items[next(counter) % len(items)]


def check_json_response(response):
    if response.status_code >= 400:
        response.failure(f"HTTP {response.status_code}: {response.text[:200]}")
        return None

    try:
        payload = response.json()
    except ValueError as exc:
        response.failure(f"JSON invalido: {exc}")
        return None

    if isinstance(payload, dict) and payload.get("errors"):
        response.failure("; ".join(error.get("message", "GraphQL error") for error in payload["errors"]))
        return None

    return payload


class MusicHttpUser(HttpUser):
    abstract = True

    def on_start(self):
        self.catalog_counter = itertools.count()
        self.relation_counter = itertools.count()


class RestApiUser(MusicHttpUser):
    host = REST_HOST

    @tag("catalogo")
    @task(4)
    def catalogo_leitura(self):
        path = next_item(self.catalog_counter, ["/users", "/songs", "/playlists"])
        self.client.get(path, name="REST/catalogo-leitura")

    @tag("relacionamentos")
    @task(4)
    def relacionamentos_leitura(self):
        path = next_item(
            self.relation_counter,
            ["/users/u1/playlists", "/playlists/p1/songs", "/songs/s1/playlists"],
        )
        self.client.get(path, name="REST/relacionamentos-leitura")

    @tag("escrita")
    @task(1)
    def usuarios_escrita(self):
        with self.client.post(
            "/users",
            json=unique_user("REST"),
            name="REST/usuarios-escrita",
            catch_response=True,
        ) as response:
            created = check_json_response(response)

        user_id = created.get("id") if created else None
        if user_id:
            self.client.delete(f"/users/{user_id}", name="REST/usuarios-escrita")


GRAPHQL_QUERIES = {
    "users": "query { users { id name email } }",
    "songs": "query { songs { id title artist album durationSeconds } }",
    "playlists": "query { playlists { id userId name songIds } }",
    "user_playlists": """
        query($userId: ID!) {
          userPlaylists(userId: $userId) { id userId name songIds }
        }
    """,
    "playlist_songs": """
        query($playlistId: ID!) {
          playlistSongs(playlistId: $playlistId) { id title artist album durationSeconds }
        }
    """,
    "song_playlists": """
        query($songId: ID!) {
          songPlaylists(songId: $songId) { id userId name songIds }
        }
    """,
    "create_user": """
        mutation($input: UserInput!) {
          createUser(input: $input) { id name email }
        }
    """,
    "delete_user": """
        mutation($id: ID!) {
          deleteUser(id: $id) { ok }
        }
    """,
}


class GraphqlApiUser(MusicHttpUser):
    host = GRAPHQL_HOST

    def graphql(self, query, variables=None, name="GraphQL"):
        with self.client.post(
            "/graphql",
            json={"query": query, "variables": variables or {}},
            name=name,
            catch_response=True,
        ) as response:
            return check_json_response(response)

    @tag("catalogo")
    @task(4)
    def catalogo_leitura(self):
        query = next_item(
            self.catalog_counter,
            [GRAPHQL_QUERIES["users"], GRAPHQL_QUERIES["songs"], GRAPHQL_QUERIES["playlists"]],
        )
        self.graphql(query, name="GraphQL/catalogo-leitura")

    @tag("relacionamentos")
    @task(4)
    def relacionamentos_leitura(self):
        query, variables = next_item(
            self.relation_counter,
            [
                (GRAPHQL_QUERIES["user_playlists"], {"userId": "u1"}),
                (GRAPHQL_QUERIES["playlist_songs"], {"playlistId": "p1"}),
                (GRAPHQL_QUERIES["song_playlists"], {"songId": "s1"}),
            ],
        )
        self.graphql(query, variables, name="GraphQL/relacionamentos-leitura")

    @tag("escrita")
    @task(1)
    def usuarios_escrita(self):
        created_payload = self.graphql(
            GRAPHQL_QUERIES["create_user"],
            {"input": unique_user("GraphQL")},
            name="GraphQL/usuarios-escrita",
        )
        user_id = created_payload.get("data", {}).get("createUser", {}).get("id") if created_payload else None
        if user_id:
            self.graphql(
                GRAPHQL_QUERIES["delete_user"],
                {"id": user_id},
                name="GraphQL/usuarios-escrita",
            )


def escape_xml(value):
    return html.escape(str(value), quote=True)


def soap_fields(payload):
    return "".join(
        f"<{key}>{escape_xml(','.join(value) if isinstance(value, list) else value)}</{key}>"
        for key, value in payload.items()
        if value is not None
    )


def soap_envelope(operation, payload=None):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="http://example.com/music-streaming">
  <soapenv:Header/>
  <soapenv:Body>
    <tns:{operation}>
      {soap_fields(payload or {})}
    </tns:{operation}>
  </soapenv:Body>
</soapenv:Envelope>"""


def parse_soap_payload(text):
    match = re.search(r"<payload[^>]*>([\s\S]*?)</payload>", text)
    if not match:
        return None

    return json.loads(html.unescape(match.group(1)))


class SoapApiUser(MusicHttpUser):
    host = SOAP_HOST

    def soap(self, operation, payload=None, name="SOAP"):
        with self.client.post(
            "/soap",
            data=soap_envelope(operation, payload),
            headers={
                "content-type": "text/xml; charset=utf-8",
                "soapaction": f"urn:{operation}",
            },
            name=name,
            catch_response=True,
        ) as response:
            if response.status_code >= 400:
                response.failure(f"HTTP {response.status_code}: {response.text[:200]}")
                return None

            parsed_payload = parse_soap_payload(response.text)
            if "<success>true</success>" not in response.text:
                response.failure(parsed_payload.get("error", {}).get("message", "SOAP error") if parsed_payload else "SOAP error")
                return None

            return parsed_payload

    @tag("catalogo")
    @task(4)
    def catalogo_leitura(self):
        operation = next_item(self.catalog_counter, ["ListUsers", "ListSongs", "ListPlaylists"])
        self.soap(operation, name="SOAP/catalogo-leitura")

    @tag("relacionamentos")
    @task(4)
    def relacionamentos_leitura(self):
        operation, payload = next_item(
            self.relation_counter,
            [
                ("ListUserPlaylists", {"userId": "u1"}),
                ("ListPlaylistSongs", {"playlistId": "p1"}),
                ("ListSongPlaylists", {"songId": "s1"}),
            ],
        )
        self.soap(operation, payload, name="SOAP/relacionamentos-leitura")

    @tag("escrita")
    @task(1)
    def usuarios_escrita(self):
        created = self.soap("CreateUser", unique_user("SOAP"), name="SOAP/usuarios-escrita")
        user_id = created.get("id") if created else None
        if user_id:
            self.soap("DeleteUser", {"id": user_id}, name="SOAP/usuarios-escrita")


def encode_varint(value):
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            encoded.append(byte | 0x80)
        else:
            encoded.append(byte)
            return bytes(encoded)


def decode_varint(buffer, position):
    shift = 0
    result = 0
    while True:
        byte = buffer[position]
        position += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, position
        shift += 7


def pb_string(field_number, value):
    data = str(value).encode("utf-8")
    return encode_varint((field_number << 3) | 2) + encode_varint(len(data)) + data


def pb_user_input(user):
    return pb_string(1, user["name"]) + pb_string(2, user["email"])


def pb_id_request(value):
    return pb_string(1, value)


def read_string_field(buffer, wanted_field):
    position = 0
    while position < len(buffer):
        tag_value, position = decode_varint(buffer, position)
        field_number = tag_value >> 3
        wire_type = tag_value & 0x07

        if wire_type == 2:
            length, position = decode_varint(buffer, position)
            value = buffer[position : position + length]
            position += length
            if field_number == wanted_field:
                return value.decode("utf-8")
        elif wire_type == 0:
            _, position = decode_varint(buffer, position)
        else:
            return None

    return None


class GrpcMusicUser(User):
    def on_start(self):
        self.catalog_counter = itertools.count()
        self.relation_counter = itertools.count()
        self.channel = grpc.insecure_channel(GRPC_TARGET)
        self.methods = {
            "ListUsers": self.channel.unary_unary("/music.MusicStreaming/ListUsers"),
            "ListSongs": self.channel.unary_unary("/music.MusicStreaming/ListSongs"),
            "ListPlaylists": self.channel.unary_unary("/music.MusicStreaming/ListPlaylists"),
            "ListUserPlaylists": self.channel.unary_unary("/music.MusicStreaming/ListUserPlaylists"),
            "ListPlaylistSongs": self.channel.unary_unary("/music.MusicStreaming/ListPlaylistSongs"),
            "ListSongPlaylists": self.channel.unary_unary("/music.MusicStreaming/ListSongPlaylists"),
            "CreateUser": self.channel.unary_unary("/music.MusicStreaming/CreateUser"),
            "DeleteUser": self.channel.unary_unary("/music.MusicStreaming/DeleteUser"),
        }

    def on_stop(self):
        self.channel.close()

    def grpc_call(self, method, request, name):
        started = time.perf_counter()
        response = b""
        exception = None

        try:
            response = self.methods[method](request, timeout=10)
        except Exception as exc:
            exception = exc

        self.environment.events.request.fire(
            request_type="gRPC",
            name=name,
            response_time=(time.perf_counter() - started) * 1000,
            response_length=len(response or b""),
            response=response,
            context={},
            exception=exception,
        )

        return None if exception else response

    @tag("catalogo")
    @task(4)
    def catalogo_leitura(self):
        method = next_item(self.catalog_counter, ["ListUsers", "ListSongs", "ListPlaylists"])
        self.grpc_call(method, b"", "gRPC/catalogo-leitura")

    @tag("relacionamentos")
    @task(4)
    def relacionamentos_leitura(self):
        method, payload = next_item(
            self.relation_counter,
            [
                ("ListUserPlaylists", pb_string(1, "u1")),
                ("ListPlaylistSongs", pb_string(1, "p1")),
                ("ListSongPlaylists", pb_string(1, "s1")),
            ],
        )
        self.grpc_call(method, payload, "gRPC/relacionamentos-leitura")

    @tag("escrita")
    @task(1)
    def usuarios_escrita(self):
        created = self.grpc_call("CreateUser", pb_user_input(unique_user("gRPC")), "gRPC/usuarios-escrita")
        user_id = read_string_field(created, 1) if created else None
        if user_id:
            self.grpc_call("DeleteUser", pb_id_request(user_id), "gRPC/usuarios-escrita")
