import html
import itertools
import json
import os
import re
import time

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
                ("/playlists", "REST/listar-playlists"),
            ],
        )
        self.client.get(path, name=name)


GRAPHQL_QUERIES = {
    "users": ("query { users { id name email } }", "GraphQL/listar-usuarios"),
    "songs": ("query { songs { id title artist album durationSeconds } }", "GraphQL/listar-musicas"),
    "playlists": ("query { playlists { id userId name songIds } }", "GraphQL/listar-playlists"),
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
                GRAPHQL_QUERIES["playlists"],
            ],
        )
        self.graphql(query, name=name)


def soap_envelope(operation):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="http://example.com/music-streaming">
  <soapenv:Header/>
  <soapenv:Body>
    <tns:{operation}/>
  </soapenv:Body>
</soapenv:Envelope>"""


def parse_soap_payload(text):
    match = re.search(r"<payload[^>]*>([\s\S]*?)</payload>", text)
    if not match:
        return None

    return json.loads(html.unescape(match.group(1)))


class SoapApiUser(MusicHttpUser):
    host = SOAP_HOST

    def soap(self, operation, name):
        with self.client.post(
            "/soap",
            data=soap_envelope(operation),
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
        operation, name = next_item(
            self.catalog_counter,
            [
                ("ListUsers", "SOAP/listar-usuarios"),
                ("ListSongs", "SOAP/listar-musicas"),
                ("ListPlaylists", "SOAP/listar-playlists"),
            ],
        )
        self.soap(operation, name=name)


class GrpcMusicUser(User):
    def on_start(self):
        self.catalog_counter = itertools.count()
        self.channel = grpc.insecure_channel(GRPC_TARGET)
        self.methods = {
            "ListUsers": self.channel.unary_unary("/music.MusicStreaming/ListUsers"),
            "ListSongs": self.channel.unary_unary("/music.MusicStreaming/ListSongs"),
            "ListPlaylists": self.channel.unary_unary("/music.MusicStreaming/ListPlaylists"),
        }

    def on_stop(self):
        self.channel.close()

    def grpc_call(self, method, name):
        started = time.perf_counter()
        response = b""
        exception = None

        try:
            response = self.methods[method](b"", timeout=10)
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

    @tag("catalogo")
    @task
    def catalogo_leitura(self):
        method, name = next_item(
            self.catalog_counter,
            [
                ("ListUsers", "gRPC/listar-usuarios"),
                ("ListSongs", "gRPC/listar-musicas"),
                ("ListPlaylists", "gRPC/listar-playlists"),
            ],
        )
        self.grpc_call(method, name=name)
