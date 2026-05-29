export const REST_PORT = Number.parseInt(process.env.JS_REST_PORT || process.env.REST_PORT || "3100", 10);
export const GRAPHQL_PORT = Number.parseInt(process.env.JS_GRAPHQL_PORT || process.env.GRAPHQL_PORT || "3101", 10);
export const SOAP_PORT = Number.parseInt(process.env.JS_SOAP_PORT || process.env.SOAP_PORT || "3102", 10);
export const GRPC_PORT = Number.parseInt(process.env.JS_GRPC_PORT || process.env.GRPC_PORT || "55051", 10);
