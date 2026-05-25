FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY music_service ./music_service
COPY proto ./proto
COPY scripts ./scripts
COPY locustfile.py ./locustfile.py

ENV REST_HOST=http://rest:3000
ENV GRAPHQL_HOST=http://graphql:3001
ENV SOAP_HOST=http://soap:3002
ENV GRPC_TARGET=grpc:50051
ENV LOCUST_RESULTS_DIR=/app/results
ENV LOCUST_DURATION=1m
ENV LOCUST_SPAWN_RATE=100

CMD ["python", "-m", "music_service.servers.rest"]
