import { DomainError, plainError } from "./domain/musicStore.js";

export function readBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    request.on("error", reject);
  });
}

export async function readJson(request) {
  const text = await readBody(request);
  if (!text.trim()) {
    return {};
  }
  return JSON.parse(text);
}

export function sendJson(response, statusCode, payload) {
  const body = JSON.stringify(payload);
  response.writeHead(statusCode, {
    "content-type": "application/json; charset=utf-8",
    "content-length": Buffer.byteLength(body)
  });
  response.end(body);
}

export function sendText(response, statusCode, text, contentType = "text/plain; charset=utf-8") {
  response.writeHead(statusCode, {
    "content-type": contentType,
    "content-length": Buffer.byteLength(text)
  });
  response.end(text);
}

export function handleHttpError(response, error) {
  if (error instanceof DomainError) {
    sendJson(response, error.status, plainError(error));
    return;
  }
  if (error instanceof SyntaxError) {
    sendJson(response, 400, plainError(new DomainError(400, "INVALID_JSON", "JSON invalido")));
    return;
  }
  sendJson(response, 500, plainError(error));
}

export function routeParts(request) {
  const url = new URL(request.url, "http://localhost");
  const parts = url.pathname.split("/").filter(Boolean);
  return { url, parts };
}

export function methodNotAllowed(response) {
  sendJson(response, 405, {
    error: {
      code: "METHOD_NOT_ALLOWED",
      message: "Metodo nao permitido"
    }
  });
}

export function notFound(response) {
  sendJson(response, 404, {
    error: {
      code: "NOT_FOUND",
      message: "Rota nao encontrada"
    }
  });
}
