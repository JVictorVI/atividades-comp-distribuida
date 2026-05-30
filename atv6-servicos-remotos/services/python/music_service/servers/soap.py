import os
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from music_service.config import SOAP_PORT
from music_service.domain.music_store import MusicStore, plain_error
from music_service.http_utils import (
    MusicHttpHandler,
    create_http_server,
    method_not_allowed,
    not_found,
    read_body,
    route_parts,
    run_http_server,
    send_json,
    send_text,
)


NAMESPACE = "http://example.com/music-streaming"
SOAP_NAMESPACE = "http://schemas.xmlsoap.org/soap/envelope/"
SOAP_COMPLEXITY_PASSES = int(os.getenv("SOAP_COMPLEXITY_PASSES", "4"))

OPERATIONS = [
    "Reset",
    "ListUsers",
    "GetUser",
    "CreateUser",
    "UpdateUser",
    "DeleteUser",
    "ListSongs",
    "GetSong",
    "CreateSong",
    "UpdateSong",
    "DeleteSong",
    "ListPlaylists",
    "GetPlaylist",
    "CreatePlaylist",
    "UpdatePlaylist",
    "DeletePlaylist",
    "ListUserPlaylists",
    "ListPlaylistSongs",
    "ListSongPlaylists",
]

FIELD_RULES = {
    "Reset": (set(), set()),
    "ListUsers": (set(), set()),
    "ListSongs": (set(), set()),
    "GetUser": ({"id"}, {"id"}),
    "DeleteUser": ({"id"}, {"id"}),
    "GetSong": ({"id"}, {"id"}),
    "DeleteSong": ({"id"}, {"id"}),
    "GetPlaylist": ({"id"}, {"id"}),
    "DeletePlaylist": ({"id"}, {"id"}),
    "ListUserPlaylists": ({"userId"}, {"userId"}),
    "ListPlaylistSongs": ({"playlistId"}, {"playlistId"}),
    "ListSongPlaylists": ({"songId"}, {"songId"}),
    "CreateUser": ({"name", "email"}, {"name", "email"}),
    "CreateSong": ({"title", "artist", "album", "durationSeconds"}, {"title", "artist", "album", "durationSeconds"}),
    "CreatePlaylist": ({"userId", "name", "songIds"}, {"userId", "name", "songIds"}),
    "UpdateUser": ({"id"}, {"id", "name", "email"}),
    "UpdateSong": ({"id"}, {"id", "title", "artist", "album", "durationSeconds"}),
    "UpdatePlaylist": ({"id"}, {"id", "userId", "name", "songIds"}),
    "ListPlaylists": (set(), {"userId", "songId"}),
}

store = MusicStore()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def namespace_uri(tag: str) -> str:
    return tag[1:].split("}", 1)[0] if tag.startswith("{") else ""


def operation_args(operation_element):
    return {
        local_name(child.tag): (child.text or "")
        for child in list(operation_element)
    }


def find_body(root):
    for element in root.iter():
        if local_name(element.tag) == "Body":
            return element
    return None


def canonicalize_xml_tree(root):
    tokens = []
    for _pass_index in range(SOAP_COMPLEXITY_PASSES):
        for element in root.iter():
            attrs = "|".join(
                f"{local_name(key)}={value.strip()}"
                for key, value in sorted(element.attrib.items())
            )
            text = " ".join((element.text or "").split())
            tokens.append(f"{namespace_uri(element.tag)}:{local_name(element.tag)}:{attrs}:{text}")
    return "\n".join(tokens)


def validate_operation_args(operation: str, args: dict):
    required, allowed = FIELD_RULES[operation]
    received = set(args)
    missing = sorted(required - received)
    unexpected = sorted(received - allowed)
    if missing:
        raise ValueError(f"Campos obrigatorios ausentes em {operation}: {', '.join(missing)}")
    if unexpected:
        raise ValueError(f"Campos nao permitidos em {operation}: {', '.join(unexpected)}")


def parse_soap_request(text: str):
    root = ElementTree.fromstring(text)
    canonicalize_xml_tree(root)

    if local_name(root.tag) != "Envelope" or namespace_uri(root.tag) != SOAP_NAMESPACE:
        raise ValueError("Envelope SOAP invalido")

    body = find_body(root)
    if body is None:
        raise ValueError("Envelope SOAP sem Body")

    operation_elements = [child for child in list(body) if isinstance(child.tag, str)]
    if len(operation_elements) != 1:
        raise ValueError("Envelope SOAP deve conter exatamente uma operacao")

    operation_element = operation_elements[0]
    if namespace_uri(operation_element.tag) not in ("", NAMESPACE):
        raise ValueError("Namespace da operacao SOAP invalido")

    operation = local_name(operation_element.tag)
    if operation not in OPERATIONS:
        raise ValueError(f"Operacao SOAP desconhecida: {operation}")

    args = operation_args(operation_element)
    validate_operation_args(operation, args)
    return operation, args


def xml_text(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return escape(str(value))


def xml_element(name: str, value) -> str:
    if isinstance(value, dict):
        children = "".join(xml_element(key, item) for key, item in value.items())
        return f"<{name}>{children}</{name}>"
    if isinstance(value, list):
        children = "".join(xml_element("item", item) for item in value)
        return f"<{name}>{children}</{name}>"
    return f"<{name}>{xml_text(value)}</{name}>"


def xml_payload(value) -> str:
    if isinstance(value, list):
        return "".join(xml_element("item", item) for item in value)
    if isinstance(value, dict):
        return "".join(xml_element(key, item) for key, item in value.items())
    return xml_text(value)


def soap_response(operation: str, success: bool, payload) -> str:
    success_text = "true" if success else "false"
    response = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="{SOAP_NAMESPACE}" xmlns:tns="{NAMESPACE}">
  <soap:Body>
    <tns:{operation}Response>
      <success>{success_text}</success>
      <payload>{xml_payload(payload)}</payload>
    </tns:{operation}Response>
  </soap:Body>
</soap:Envelope>"""
    validate_soap_response(response)
    return response


def validate_soap_response(response: str):
    root = ElementTree.fromstring(response)
    canonicalize_xml_tree(root)
    if local_name(root.tag) != "Envelope" or namespace_uri(root.tag) != SOAP_NAMESPACE:
        raise ValueError("Resposta SOAP invalida")
    body = find_body(root)
    if body is None:
        raise ValueError("Resposta SOAP sem Body")
    response_elements = [child for child in list(body) if isinstance(child.tag, str)]
    if len(response_elements) != 1:
        raise ValueError("Resposta SOAP deve conter exatamente um elemento")


def execute(operation: str, args: dict):
    operations = {
        "Reset": lambda: store.reset(),
        "ListUsers": lambda: store.list_users(),
        "GetUser": lambda: store.get_user(args.get("id")),
        "CreateUser": lambda: store.create_user(args),
        "UpdateUser": lambda: store.update_user(args.get("id"), args),
        "DeleteUser": lambda: store.delete_user(args.get("id")),
        "ListSongs": lambda: store.list_songs(),
        "GetSong": lambda: store.get_song(args.get("id")),
        "CreateSong": lambda: store.create_song(args),
        "UpdateSong": lambda: store.update_song(args.get("id"), args),
        "DeleteSong": lambda: store.delete_song(args.get("id")),
        "ListPlaylists": lambda: store.list_playlists(args),
        "GetPlaylist": lambda: store.get_playlist(args.get("id")),
        "CreatePlaylist": lambda: store.create_playlist(args),
        "UpdatePlaylist": lambda: store.update_playlist(args.get("id"), args),
        "DeletePlaylist": lambda: store.delete_playlist(args.get("id")),
        "ListUserPlaylists": lambda: store.list_user_playlists(args.get("userId")),
        "ListPlaylistSongs": lambda: store.list_playlist_songs(args.get("playlistId")),
        "ListSongPlaylists": lambda: store.list_song_playlists(args.get("songId")),
    }

    return operations[operation]()


def wsdl() -> str:
    messages = "\n".join(
        f"""
    <message name="{name}Request"><part name="parameters" element="tns:{name}"/></message>
    <message name="{name}Response"><part name="parameters" element="tns:{name}Response"/></message>"""
        for name in OPERATIONS
    )
    port_operations = "\n".join(
        f"""
      <operation name="{name}">
        <input message="tns:{name}Request"/>
        <output message="tns:{name}Response"/>
      </operation>"""
        for name in OPERATIONS
    )
    binding_operations = "\n".join(
        f"""
      <operation name="{name}">
        <soap:operation soapAction="urn:{name}"/>
        <input><soap:body use="literal"/></input>
        <output><soap:body use="literal"/></output>
      </operation>"""
        for name in OPERATIONS
    )
    elements = "\n".join(
        f"""
      <xsd:element name="{name}" type="tns:GenericRequestType"/>
      <xsd:element name="{name}Response" type="tns:SoapResponseType"/>"""
        for name in OPERATIONS
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions name="MusicStreamingService"
  targetNamespace="{NAMESPACE}"
  xmlns="http://schemas.xmlsoap.org/wsdl/"
  xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
  xmlns:tns="{NAMESPACE}"
  xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <types>
    <xsd:schema targetNamespace="{NAMESPACE}">
      <xsd:complexType name="GenericRequestType">
        <xsd:sequence>
          <xsd:any minOccurs="0" maxOccurs="unbounded" processContents="lax"/>
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="SoapResponseType">
        <xsd:sequence>
          <xsd:element name="success" type="xsd:boolean"/>
          <xsd:element name="payload" type="tns:GenericRequestType"/>
        </xsd:sequence>
      </xsd:complexType>
      {elements}
    </xsd:schema>
  </types>
  {messages}
  <portType name="MusicStreamingPortType">{port_operations}</portType>
  <binding name="MusicStreamingBinding" type="tns:MusicStreamingPortType">
    <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
    {binding_operations}
  </binding>
  <service name="MusicStreamingService">
    <port name="MusicStreamingPort" binding="tns:MusicStreamingBinding">
      <soap:address location="http://localhost:{SOAP_PORT}/soap"/>
    </port>
  </service>
</definitions>"""


class SoapHandler(MusicHttpHandler):
    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_PUT(self):
        self.handle_request()

    def do_DELETE(self):
        self.handle_request()

    def handle_request(self):
        _parsed, parts, _query = route_parts(self)

        if self.command == "GET" and parts == ["health"]:
            send_json(self, 200, {"ok": True, "technology": "SOAP Python"})
            return

        if parts != ["soap"]:
            not_found(self)
            return

        if self.command == "GET":
            send_text(self, 200, wsdl(), "text/xml; charset=utf-8")
            return

        if self.command != "POST":
            method_not_allowed(self)
            return

        try:
            operation, args = parse_soap_request(read_body(self))
            result = execute(operation, args)
            send_text(self, 200, soap_response(operation, True, result), "text/xml; charset=utf-8")
        except Exception as error:
            send_text(
                self,
                200,
                soap_response("Fault", False, plain_error(error)),
                "text/xml; charset=utf-8",
            )


def main():
    run_http_server(SoapHandler, SOAP_PORT, "SOAP Python")


def create_server():
    return create_http_server(SoapHandler, SOAP_PORT)


if __name__ == "__main__":
    main()
