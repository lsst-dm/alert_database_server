import logging
import os
import unittest

import boto3
import requests
from fastapi.testclient import TestClient

from alertdb.server import create_server
from alertdb.storage import USDFObjectStorageBackend

logger = logging.getLogger(__name__)
logger.level = logging.DEBUG


class ServerIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Create a test bucket, and populate it with three alerts and three
        schemas.

        The alerts and schemas don't have valid payloads.
        """
        gcp_project = os.environ.get("ALERTDB_TEST_GCP_PROJECT", None)
        if gcp_project is None:
            raise unittest.SkipTest(
                "the $ALERTDB_TEST_GCP_PROJECT environment variable must be set"
            )
        packet_bucket_name = "alertdb_server_integration_test_bucket_packets"
        schema_bucket_name = "alertdb_server_integration_test_bucket_schemas"
        client = boto3.client("s3", endpoint_url=gcp_project)

        logger.info("creating bucket %s", packet_bucket_name)
        packet_bucket = client.create_bucket(packet_bucket_name)

        def delete_packet_bucket():
            logger.info("deleting bucket %s", packet_bucket_name)
            packet_bucket.delete()

        cls.addClassCleanup(delete_packet_bucket)

        logger.info("creating bucket %s", schema_bucket_name)
        schema_bucket = client.create_bucket(schema_bucket_name)

        def delete_schema_bucket():
            logger.info("deleting bucket %s", schema_bucket_name)
            schema_bucket.delete()

        cls.addClassCleanup(delete_schema_bucket)

        # Populate the test bucket with a few objects in the expected locations
        def delete_blob(blob):
            # Callback to delete a blob during cleanup.
            logger.info("deleting blob %s", blob.name)
            blob.delete()

        alerts = {
            "alert-id-1": b"payload-1",
            "alert-id-2": b"payload-2",
            "alert-id-3": b"payload-3",
        }
        for alert_id, alert_payload in alerts.items():
            blob = packet_bucket.blob(f"/alert_archive/v1/alerts/{alert_id}.avro.gz")
            logger.info("uploading blob %s", blob.name)
            # N.B. this method is poorly named; it accepts bytes:
            blob.upload_from_string(alert_payload)
            cls.addClassCleanup(delete_blob, blob)

        schemas = {
            "1": b"schema-payload-1",
            "2": b"schema-payload-2",
            "3": b"schema-payload-3",
        }
        for schema_id, schema_payload in schemas.items():
            blob = schema_bucket.blob(f"/alert_archive/v1/schemas/{schema_id}.json")
            logger.info("uploading blob %s", blob.name)
            # N.B. this method is poorly named; it accepts bytes:
            blob.upload_from_string(schema_payload)
            cls.addClassCleanup(delete_blob, blob)

        cls.gcp_project = gcp_project
        cls.packet_bucket_name = packet_bucket_name
        cls.schema_bucket_name = schema_bucket_name
        cls.stored_alerts = alerts
        cls.stored_schemas = schemas

    def setUp(self):
        """
        Run a local instance of the server.
        """
        backend = USDFObjectStorageBackend(
            self.gcp_project, self.packet_bucket_name, self.schema_bucket_name
        )
        self.server = create_server(backend)
        self.client = TestClient(self.server)

    def test_get_existing_alerts(self):
        """Test that retrieving an alert over HTTP works as expected."""
        for alert_id, alert in self.stored_alerts.items():
            response = self._get_alert(alert_id)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, alert)

    def test_get_existing_schemas(self):
        """Test that retrieving a schema over HTTP works as expected."""
        for schema_id, schema in self.stored_schemas.items():
            response = self._get_schema(schema_id)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, schema)

    def test_get_missing_alert(self):
        """Test that retrieving an alert that does not exist gives a 404."""
        response = self._get_alert("bogus")
        self.assertEqual(response.status_code, 404)

    def test_get_missing_schema(self):
        """Test that retrieving a schema that does not exist gives a 404."""
        response = self._get_schema("bogus")
        self.assertEqual(response.status_code, 404)

    def test_healthcheck(self):
        """Test that the healthcheck endpoint returns 200."""
        response = self.client.get("/v1/health")
        self.assertEqual(response.status_code, 200)

    def _get_alert(self, alert_id: str) -> requests.Response:
        return self.client.get(f"/v1/alerts/{alert_id}")

    def _get_schema(self, schema_id: str) -> requests.Response:
        return self.client.get(f"/v1/schemas/{schema_id}")
