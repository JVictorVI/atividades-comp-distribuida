import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from json import JSONDecodeError
from urllib.parse import parse_qs, unquote, urlparse

from music_service.domain.music_store import DomainError, plain_error


class MusicHttpHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format, *_args):
        return


class MusicHttpServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 2048


def create_http_server(handler_class, port: int, host: str = "0.0.0.0"):
    return MusicHttpServer((host, port), handler_class)


def run_http_server(handler_class, port: int, label: str):
    server = create_http_server(handler_class, port)
    print(f"{label} ouvindo em 0.0.0.0:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def read_body(handler) -> str:
    length = int(handler.headers.get("content-length") or 0)
    if length <= 0:
        return ""
    return handler.rfile.read(length).decode("utf-8")


def read_json(handler):
    text = read_body(handler)
    if not text.strip():
        return {}
    return json.loads(text)


def send_text(handler, status_code: int, text, content_type: str = "text/plain; charset=utf-8"):
    body = text if isinstance(text, bytes) else str(text).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("content-type", content_type)
    handler.send_header("content-length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def send_json(handler, status_code: int, payload):
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("content-type", "application/json; charset=utf-8")
    handler.send_header("content-length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def handle_http_error(handler, error: Exception):
    if isinstance(error, DomainError):
        send_json(handler, error.status, plain_error(error))
        return
    if isinstance(error, JSONDecodeError):
        send_json(handler, 400, plain_error(DomainError(400, "INVALID_JSON", "JSON invalido")))
        return
    send_json(handler, 500, plain_error(error))


def route_parts(handler):
    parsed = urlparse(handler.path)
    parts = [unquote(part) for part in parsed.path.split("/") if part]
    query = {
        key: values[0] if values else ""
        for key, values in parse_qs(parsed.query, keep_blank_values=True).items()
    }
    return parsed, parts, query


def method_not_allowed(handler):
    send_json(
        handler,
        405,
        {
            "error": {
                "code": "METHOD_NOT_ALLOWED",
                "message": "Metodo nao permitido",
            }
        },
    )


def not_found(handler):
    send_json(
        handler,
        404,
        {
            "error": {
                "code": "NOT_FOUND",
                "message": "Rota nao encontrada",
            }
        },
    )
