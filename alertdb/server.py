from fastapi import FastAPI, HTTPException, Response

from alertdb.storage import AlertDatabaseBackend, NotFoundError


SCHEMA_CONTENT_TYPE = "application/vnd.schemaregistry.v1+json"
ALERT_CONTENT_TYPE = "application/octet-stream"


def create_server(backend: AlertDatabaseBackend):
    app = FastAPI()

    @app.get("/v1/schemas/{schema_id}")
    def get_schema(schema_id: str):
        try:
            schema_bytes = backend.get_schema(schema_id)
        except NotFoundError as nfe:
            raise HTTPException(status_code=404, detail="schema not found") from nfe

        return Response(content=schema_bytes, media_type=SCHEMA_CONTENT_TYPE)

    @app.get("/v1/alerts/{alert_id}")
    def get_alert(alert_id: str):
        try:
            alert_bytes = backend.get_alert(alert_id)
        except NotFoundError as nfe:
            raise HTTPException(status_code=404, detail="alert not found") from nfe

        return Response(content=alert_bytes, media_type=ALERT_CONTENT_TYPE)

    return app
