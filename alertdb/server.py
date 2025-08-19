"""HTTP frontend server implementation."""

from fastapi import FastAPI, HTTPException, Response

from alertdb.storage import AlertDatabaseBackend, NotFoundError

# This Content-Type is described as the "preferred content type" for a
# Confluent Schema Registry here:
# https://docs.confluent.io/platform/current/schema-registry/develop/api.html#content-types
# We're not running a Confluent Schema Registry, and don't conform to the API
# of one, but we do serve schemas, so this seems possibly appropriate.

SCHEMA_CONTENT_TYPE = "application/vnd.schemaregistry.v1+json"

# There's no consensus on an Avro content type. application/avro+binary is
# sometimes used, but not very standard. If we did that, we'd want to specify
# the content-encoding as well, since contents are gzipped.
#
# application/octet-stream, which represents arbitrary bytes, is maybe overly
# general, but it's at least well-understood.
ALERT_CONTENT_TYPE = "application/octet-stream"


def create_server(backend: AlertDatabaseBackend) -> FastAPI:
    """
    Creates a new instance of an HTTP handler which fetches alerts and schemas
    from a backend.

    Parameters
    ----------
    backend : AlertDatabaseBackend
        The backend that stores alerts to be served.

    Returns
    -------
    FastAPI : A FastAPI application which routes HTTP requests to return
    schemas.
    """

    # FastAPI documentation suggests that the application be a global
    # singleton, with handlers defined as top-level functions, but this doesn't
    # seem to permit any way of passing in a persistent backend. So, this
    # little create_server closure exists to allow dependency injection.

    app = FastAPI()

    @app.get("/v1/health")
    def healthcheck():
        return Response(content=b"OK")

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
