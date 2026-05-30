import grpc from "@grpc/grpc-js";
import protoLoader from "@grpc/proto-loader";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { GRPC_PORT } from "./config.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROTO_PATH = resolve(__dirname, "../../proto/music.proto");
const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: false,
  oneofs: true
});
const proto = grpc.loadPackageDefinition(packageDefinition).music;
const client = new proto.MusicStreaming(
  `127.0.0.1:${GRPC_PORT}`,
  grpc.credentials.createInsecure()
);

const timeout = setTimeout(() => {
  client.close();
  process.exit(1);
}, 2000);

client.ListUsers({}, (error, response) => {
  clearTimeout(timeout);
  client.close();
  if (error || !response || !Array.isArray(response.users) || response.users.length === 0) {
    process.exit(1);
  }
  process.exit(0);
});
