FROM node:24-slim

WORKDIR /app

COPY services/javascript ./services/javascript
COPY proto ./proto

RUN npm ci --omit=dev --prefix services/javascript

ENV JS_REST_PORT=3100
ENV JS_GRAPHQL_PORT=3101
ENV JS_SOAP_PORT=3102
ENV JS_GRPC_PORT=55051

CMD ["node", "services/javascript/servers/rest.js"]
