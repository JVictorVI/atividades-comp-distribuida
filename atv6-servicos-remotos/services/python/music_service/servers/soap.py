import json
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from fastapi import FastAPI, Request
from fastapi.responses import Response
import uvicorn

from music_service.config import SOAP_PORT
from music_service.domain.music_store import MusicStore, plain_error


NAMESPACE = "http://example.com/music-streaming"
SOAP_NAMESPACE = "http://schemas.xmlsoap.org/soap/envelope/"

store = MusicStore()
app = FastAPI(title="Music Streaming SOAP")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


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


def soap_response(operation: str, success: bool, payload) -> str:
    payload_json = escape(json.dumps(payload, ensure_ascii=False))
    success_text = "true" if success else "false"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="{SOAP_NAMESPACE}" xmlns:tns="{NAMESPACE}">
  <soap:Body>
    <tns:{operation}Response>
      <success>{success_text}</success>
      <payload>{payload_json}</payload>
    </tns:{operation}Response>
  </soap:Body>
</soap:Envelope>"""


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

    if operation not in operations:
        raise ValueError(f"Operação SOAP desconhecida: {operation}")
    return operations[operation]()


def wsdl() -> str:
    operations = [
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
    messages = "\n".join(
        f"""
    <message name="{name}Request"><part name="parameters" element="tns:{name}"/></message>
    <message name="{name}Response"><part name="parameters" element="tns:{name}Response"/></message>"""
        for name in operations
    )
    port_operations = "\n".join(
        f"""
      <operation name="{name}">
        <input message="tns:{name}Request"/>
        <output message="tns:{name}Response"/>
      </operation>"""
        for name in operations
    )
    binding_operations = "\n".join(
        f"""
      <operation name="{name}">
        <soap:operation soapAction="urn:{name}"/>
        <input><soap:body use="literal"/></input>
        <output><soap:body use="literal"/></output>
      </operation>"""
        for name in operations
    )
    elements = "\n".join(
        f"""
      <xsd:element name="{name}" type="tns:GenericRequestType"/>
      <xsd:element name="{name}Response" type="tns:JsonResponseType"/>"""
        for name in operations
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
      <xsd:complexType name="JsonResponseType">
        <xsd:sequence>
          <xsd:element name="success" type="xsd:boolean"/>
          <xsd:element name="payload" type="xsd:string"/>
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


@app.get("/health")
def health():
    return {"ok": True, "technology": "SOAP"}


@app.api_route("/soap", methods=["GET", "POST"])
async def soap_endpoint(request: Request):
    if request.method == "GET":
        return Response(content=wsdl(), media_type="text/xml")

    text = (await request.body()).decode("utf-8")
    try:
        root = ElementTree.fromstring(text)
        body = find_body(root)
        operation_element = list(body)[0] if body is not None and list(body) else None
        if operation_element is None:
            raise ValueError("Envelope SOAP sem operação")
        operation = local_name(operation_element.tag)
        result = execute(operation, operation_args(operation_element))
        response = soap_response(operation, True, result)
        return Response(content=response, media_type="text/xml")
    except Exception as error:
        operation = "Fault"
        response = soap_response(operation, False, plain_error(error))
        return Response(content=response, status_code=200, media_type="text/xml")


def main():
    uvicorn.run(app, host="0.0.0.0", port=SOAP_PORT)


if __name__ == "__main__":
    main()
