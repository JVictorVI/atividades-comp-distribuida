import http2 from "node:http2";

import { GRPC_PORT } from "./config.js";

function frameEmptyMessage() {
  return Buffer.alloc(5);
}

const client = http2.connect(`http://127.0.0.1:${GRPC_PORT}`);
const timeout = setTimeout(() => {
  client.destroy();
  process.exit(1);
}, 2000);

client.on("error", () => {
  clearTimeout(timeout);
  process.exit(1);
});

const request = client.request({
  ":method": "POST",
  ":path": "/music.MusicStreaming/ListUsers",
  "content-type": "application/grpc+proto",
  te: "trailers"
});

let responseLength = 0;
request.on("data", (chunk) => {
  responseLength += chunk.length;
});

request.on("end", () => {
  clearTimeout(timeout);
  client.close();
  process.exit(responseLength > 5 ? 0 : 1);
});

request.on("error", () => {
  clearTimeout(timeout);
  client.destroy();
  process.exit(1);
});

request.end(frameEmptyMessage());
