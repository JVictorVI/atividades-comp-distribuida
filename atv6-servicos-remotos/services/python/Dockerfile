FROM python:3.12-slim

WORKDIR /app

COPY services/python/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY services/python/music_service ./music_service
COPY proto ./proto
COPY scripts ./scripts
COPY locustfile.py ./locustfile.py

ENV REST_HOST=http://rest-python:3000
ENV GRAPHQL_HOST=http://graphql-python:3001
ENV SOAP_HOST=http://soap-python:3002
ENV GRPC_TARGET=grpc-python:50051
ENV LOCUST_RESULTS_DIR=/app/results
ENV LOCUST_DURATION=1m
ENV LOCUST_SPAWN_RATE=100

CMD ["python", "-m", "music_service.servers.rest"]
