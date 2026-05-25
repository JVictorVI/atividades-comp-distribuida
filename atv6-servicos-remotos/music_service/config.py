import os


REST_PORT = int(os.getenv("REST_PORT", "3000"))
GRAPHQL_PORT = int(os.getenv("GRAPHQL_PORT", "3001"))
SOAP_PORT = int(os.getenv("SOAP_PORT", "3002"))
GRPC_PORT = int(os.getenv("GRPC_PORT", "50051"))
