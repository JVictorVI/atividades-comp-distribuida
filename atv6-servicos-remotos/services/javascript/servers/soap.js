import http from "node:http";

import { SOAP_PORT } from "../config.js";
import { MusicStore, plainError } from "../domain/musicStore.js";
import { readBody, sendJson, sendText } from "../httpUtils.js";

const NAMESPACE = "http://example.com/music-streaming";
const SOAP_NAMESPACE = "http://schemas.xmlsoap.org/soap/envelope/";
const SOAP_COMPLEXITY_PASSES = Number.parseInt(process.env.SOAP_COMPLEXITY_PASSES || "4", 10);
const OPERATIONS = [
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
  "ListSongPlaylists"
];
const FIELD_RULES = {
  Reset: [[], []],
  ListUsers: [[], []],
  ListSongs: [[], []],
  GetUser: [["id"], ["id"]],
  DeleteUser: [["id"], ["id"]],
  GetSong: [["id"], ["id"]],
  DeleteSong: [["id"], ["id"]],
  GetPlaylist: [["id"], ["id"]],
  DeletePlaylist: [["id"], ["id"]],
  ListUserPlaylists: [["userId"], ["userId"]],
  ListPlaylistSongs: [["playlistId"], ["playlistId"]],
  ListSongPlaylists: [["songId"], ["songId"]],
  CreateUser: [["name", "email"], ["name", "email"]],
  CreateSong: [["title", "artist", "album", "durationSeconds"], ["title", "artist", "album", "durationSeconds"]],
  CreatePlaylist: [["userId", "name", "songIds"], ["userId", "name", "songIds"]],
  UpdateUser: [["id"], ["id", "name", "email"]],
  UpdateSong: [["id"], ["id", "title", "artist", "album", "durationSeconds"]],
  UpdatePlaylist: [["id"], ["id", "userId", "name", "songIds"]],
  ListPlaylists: [[], ["userId", "songId"]]
};

const store = new MusicStore();

function escapeXml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function unescapeXml(value) {
  return String(value)
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", '"')
    .replaceAll("&apos;", "'")
    .replaceAll("&amp;", "&");
}

function localName(tag) {
  return tag.includes(":") ? tag.split(":").pop() : tag;
}

function tagPrefix(tag) {
  return tag.includes(":") ? tag.split(":", 1)[0] : "";
}

function namespaceDeclarations(xml) {
  const namespaces = new Map();
  const pattern = /\sxmlns(?::([A-Za-z_][\w.-]*))?="([^"]+)"/g;
  for (const match of xml.matchAll(pattern)) {
    namespaces.set(match[1] || "", match[2]);
  }
  return namespaces;
}

function namespaceUri(tag, namespaces) {
  return namespaces.get(tagPrefix(tag)) || "";
}

function canonicalizeXml(xml) {
  const tokens = [];
  const tagPattern = /<\s*(\/?)([A-Za-z_][\w:.-]*)([^>]*)>/g;
  for (let pass = 0; pass < SOAP_COMPLEXITY_PASSES; pass += 1) {
    for (const match of xml.matchAll(tagPattern)) {
      const [, closing, tag, rawAttributes] = match;
      const attrs = [...rawAttributes.matchAll(/([A-Za-z_][\w:.-]*)="([^"]*)"/g)]
        .map(([, key, value]) => `${localName(key)}=${value.trim()}`)
        .sort()
        .join("|");
      tokens.push(`${closing ? "/" : ""}${tagPrefix(tag)}:${localName(tag)}:${attrs}`);
    }
  }
  return tokens.join("\n");
}

function firstTag(source) {
  const match = source.match(/<([A-Za-z_][\w:.-]*)(?:\s[^>]*)?>([\s\S]*?)<\/\1>/);
  if (match) {
    return {
      rawName: match[1],
      name: localName(match[1]),
      inner: match[2]
    };
  }

  const selfClosingMatch = source.match(/<([A-Za-z_][\w:.-]*)(?:\s[^>]*)?\s\/>/);
  if (!selfClosingMatch) {
    return null;
  }

  return {
    rawName: selfClosingMatch[1],
    name: localName(selfClosingMatch[1]),
    inner: ""
  };
}

function validateOperationArgs(operation, args) {
  const [required, allowed] = FIELD_RULES[operation];
  const received = new Set(Object.keys(args));
  const missing = required.filter((field) => !received.has(field));
  const unexpected = [...received].filter((field) => !allowed.includes(field));
  if (missing.length) {
    throw new Error(`Campos obrigatorios ausentes em ${operation}: ${missing.join(", ")}`);
  }
  if (unexpected.length) {
    throw new Error(`Campos nao permitidos em ${operation}: ${unexpected.join(", ")}`);
  }
}

function parseEnvelope(xml) {
  canonicalizeXml(xml);
  const namespaces = namespaceDeclarations(xml);
  const envelopeMatch = xml.match(/<([A-Za-z_][\w:.-]*)(?:\s[^>]*)?>/);
  if (!envelopeMatch || localName(envelopeMatch[1]) !== "Envelope" || namespaceUri(envelopeMatch[1], namespaces) !== SOAP_NAMESPACE) {
    throw new Error("Envelope SOAP invalido");
  }

  const bodyMatch = xml.match(/<([A-Za-z_][\w:.-]*:)?Body(?:\s[^>]*)?>([\s\S]*?)<\/([A-Za-z_][\w:.-]*:)?Body>/);
  if (!bodyMatch) {
    throw new Error("Envelope SOAP sem Body");
  }
  const body = bodyMatch[2];
  const operation = firstTag(body);
  if (!operation) {
    throw new Error("Envelope SOAP sem operacao");
  }
  if (!["", NAMESPACE].includes(namespaceUri(operation.rawName, namespaces))) {
    throw new Error("Namespace da operacao SOAP invalido");
  }
  if (!OPERATIONS.includes(operation.name)) {
    throw new Error(`Operacao SOAP desconhecida: ${operation.name}`);
  }

  const args = {};
  const fieldPattern = /<([A-Za-z_][\w:.-]*)(?:\s[^>]*)?>([\s\S]*?)<\/\1>/g;
  for (const match of operation.inner.matchAll(fieldPattern)) {
    const name = localName(match[1]);
    args[name] = unescapeXml(match[2].trim());
  }

  validateOperationArgs(operation.name, args);
  return { operation: operation.name, args };
}

function soapResponse(operation, success, payload) {
  const successText = success ? "true" : "false";
  const response = `<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="${SOAP_NAMESPACE}" xmlns:tns="${NAMESPACE}">
  <soap:Body>
    <tns:${operation}Response>
      <success>${successText}</success>
      <payload>${xmlPayload(payload)}</payload>
    </tns:${operation}Response>
  </soap:Body>
</soap:Envelope>`;
  validateSoapResponse(response);
  return response;
}

function validateSoapResponse(response) {
  canonicalizeXml(response);
  const namespaces = namespaceDeclarations(response);
  const envelopeMatch = response.match(/<([A-Za-z_][\w:.-]*)(?:\s[^>]*)?>/);
  if (!envelopeMatch || localName(envelopeMatch[1]) !== "Envelope" || namespaceUri(envelopeMatch[1], namespaces) !== SOAP_NAMESPACE) {
    throw new Error("Resposta SOAP invalida");
  }
  const bodyMatch = response.match(/<([A-Za-z_][\w:.-]*:)?Body(?:\s[^>]*)?>([\s\S]*?)<\/([A-Za-z_][\w:.-]*:)?Body>/);
  if (!bodyMatch) {
    throw new Error("Resposta SOAP sem Body");
  }
  if (!firstTag(bodyMatch[2])) {
    throw new Error("Resposta SOAP sem elemento de operacao");
  }
}

function xmlText(value) {
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (value === undefined || value === null) {
    return "";
  }
  return escapeXml(value);
}

function xmlElement(name, value) {
  if (Array.isArray(value)) {
    return `<${name}>${value.map((item) => xmlElement("item", item)).join("")}</${name}>`;
  }
  if (value && typeof value === "object") {
    const children = Object.entries(value)
      .map(([key, item]) => xmlElement(key, item))
      .join("");
    return `<${name}>${children}</${name}>`;
  }
  return `<${name}>${xmlText(value)}</${name}>`;
}

function xmlPayload(value) {
  if (Array.isArray(value)) {
    return value.map((item) => xmlElement("item", item)).join("");
  }
  if (value && typeof value === "object") {
    return Object.entries(value)
      .map(([key, item]) => xmlElement(key, item))
      .join("");
  }
  return xmlText(value);
}

function execute(operation, args) {
  const operations = {
    Reset: () => store.reset(),
    ListUsers: () => store.listUsers(),
    GetUser: () => store.getUser(args.id),
    CreateUser: () => store.createUser(args),
    UpdateUser: () => store.updateUser(args.id, args),
    DeleteUser: () => store.deleteUser(args.id),
    ListSongs: () => store.listSongs(),
    GetSong: () => store.getSong(args.id),
    CreateSong: () => store.createSong(args),
    UpdateSong: () => store.updateSong(args.id, args),
    DeleteSong: () => store.deleteSong(args.id),
    ListPlaylists: () => store.listPlaylists(args),
    GetPlaylist: () => store.getPlaylist(args.id),
    CreatePlaylist: () => store.createPlaylist(args),
    UpdatePlaylist: () => store.updatePlaylist(args.id, args),
    DeletePlaylist: () => store.deletePlaylist(args.id),
    ListUserPlaylists: () => store.listUserPlaylists(args.userId),
    ListPlaylistSongs: () => store.listPlaylistSongs(args.playlistId),
    ListSongPlaylists: () => store.listSongPlaylists(args.songId)
  };

  return operations[operation]();
}

function wsdl() {
  const messages = OPERATIONS.map(
    (name) => `
    <message name="${name}Request"><part name="parameters" element="tns:${name}"/></message>
    <message name="${name}Response"><part name="parameters" element="tns:${name}Response"/></message>`
  ).join("\n");
  const portOperations = OPERATIONS.map(
    (name) => `
      <operation name="${name}">
        <input message="tns:${name}Request"/>
        <output message="tns:${name}Response"/>
      </operation>`
  ).join("\n");
  const bindingOperations = OPERATIONS.map(
    (name) => `
      <operation name="${name}">
        <soap:operation soapAction="urn:${name}"/>
        <input><soap:body use="literal"/></input>
        <output><soap:body use="literal"/></output>
      </operation>`
  ).join("\n");
  const elements = OPERATIONS.map(
    (name) => `
      <xsd:element name="${name}" type="tns:GenericRequestType"/>
      <xsd:element name="${name}Response" type="tns:SoapResponseType"/>`
  ).join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<definitions name="MusicStreamingService"
  targetNamespace="${NAMESPACE}"
  xmlns="http://schemas.xmlsoap.org/wsdl/"
  xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
  xmlns:tns="${NAMESPACE}"
  xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <types>
    <xsd:schema targetNamespace="${NAMESPACE}">
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
      ${elements}
    </xsd:schema>
  </types>
  ${messages}
  <portType name="MusicStreamingPortType">${portOperations}</portType>
  <binding name="MusicStreamingBinding" type="tns:MusicStreamingPortType">
    <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
    ${bindingOperations}
  </binding>
  <service name="MusicStreamingService">
    <port name="MusicStreamingPort" binding="tns:MusicStreamingBinding">
      <soap:address location="http://localhost:${SOAP_PORT}/soap"/>
    </port>
  </service>
</definitions>`;
}

const server = http.createServer((request, response) => {
  const url = new URL(request.url, "http://localhost");

  Promise.resolve()
    .then(async () => {
      if (request.method === "GET" && url.pathname === "/health") {
        sendJson(response, 200, { ok: true, technology: "SOAP JavaScript" });
        return;
      }

      if (url.pathname !== "/soap") {
        sendJson(response, 404, plainError(new Error("Rota nao encontrada")));
        return;
      }

      if (request.method === "GET") {
        sendText(response, 200, wsdl(), "text/xml; charset=utf-8");
        return;
      }

      if (request.method !== "POST") {
        sendJson(response, 405, plainError(new Error("Metodo nao permitido")));
        return;
      }

      try {
        const { operation, args } = parseEnvelope(await readBody(request));
        sendText(response, 200, soapResponse(operation, true, execute(operation, args)), "text/xml; charset=utf-8");
      } catch (error) {
        sendText(response, 200, soapResponse("Fault", false, plainError(error)), "text/xml; charset=utf-8");
      }
    })
    .catch((error) => {
      sendText(response, 200, soapResponse("Fault", false, plainError(error)), "text/xml; charset=utf-8");
    });
});

server.listen(SOAP_PORT, "0.0.0.0", () => {
  console.log(`SOAP JavaScript ouvindo em 0.0.0.0:${SOAP_PORT}`);
});
