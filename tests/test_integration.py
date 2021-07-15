import os
import sys
import unittest
import google.cloud.storage as gcs
import multiprocessing
import time
import uvicorn
import requests
import logging


from alertdb.server import create_server
from alertdb.storage import GoogleObjectStorageBackend


logger = logging.getLogger(__name__)
logger.level = logging.DEBUG


class ServerIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Create a test bucket, and populate it with three alerts and three schemas.

        The alerts and schemas don't have valid payloads.
        """
        gcp_project = os.environ.get("ALERTDB_TEST_GCP_PROJECT", None)
        if gcp_project is None:
            raise unittest.SkipTest("the $ALERTDB_TEST_GCP_PROJECT environment variable must be set")
        bucket_name = "alertdb_server_integration_test_bucket"
        client = gcs.Client(project=gcp_project)

        logger.info("creating bucket %s", bucket_name)
        bucket = client.create_bucket(bucket_name)

        def delete_bucket():
            logger.info("deleting bucket %s", bucket_name)
            bucket.delete()
        cls.addClassCleanup(delete_bucket)

        # Populate the test bucket with a few objects in the expected locations.
        def delete_blob(blob):
            # Callback to delete a blob during cleanup.
            logger.info("deleting blob %s", blob.name)
            blob.delete()

        alerts = {
            "alert-id-1": b"payload-1",
            "alert-id-2": b"payload-2",
            "alert-id-3": b"payload-3"
        }
        for alert_id, alert_payload in alerts.items():
            blob = bucket.blob(f"/alert_archive/v1/alerts/{alert_id}.avro.gz")
            logger.info("uploading blob %s", blob.name)
            # N.B. this method is poorly named; it accepts bytes:
            blob.upload_from_string(alert_payload)
            cls.addClassCleanup(delete_blob, blob)

        schemas = {
            "1": b"schema-payload-1",
            "2": b"schema-payload-2",
            "3": b"schema-payload-3"
        }
        for schema_id, schema_payload in schemas.items():
            blob = bucket.blob(f"/alert_archive/v1/schemas/{schema_id}.json")
            logger.info("uploading blob %s", blob.name)
            # N.B. this method is poorly named; it accepts bytes:
            blob.upload_from_string(schema_payload)
            cls.addClassCleanup(delete_blob, blob)

        cls.gcp_project = gcp_project
        cls.bucket_name = bucket_name
        cls.stored_alerts = alerts
        cls.stored_schemas = schemas

    def setUp(self):
        """
        Run a local instance of the server.
        """
        backend = GoogleObjectStorageBackend(self.gcp_project, self.bucket_name)
        self.server = create_server(backend)
        self.server_host = "127.0.0.1"
        self.server_port = 14541
        self.server_process = multiprocessing.Process(
            target=uvicorn.run,
            args=(self.server, ),
            kwargs={
                "host": self.server_host,
                "port": self.server_port,
            },
            daemon=True,
        )
        logger.info("launching server process")
        self.server_process.start()
        logger.info("server process pid: %s", self.server_process.pid)
        time.sleep(0.5)  # Time for the server to start up

    def tearDown(self):
        logger.info("terminating server")
        self.server_process.terminate()

    def test_get_existing_alerts(self):
        for alert_id, alert in self.stored_alerts.items():
            response = self._get_alert(alert_id)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, alert)

    def test_get_existing_schemas(self):
        for schema_id, schema in self.stored_schemas.items():
            response = self._get_schema(schema_id)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, schema)

    def test_get_missing_alert(self):
        response = self._get_alert("bogus")
        self.assertEqual(response.status_code, 404)

    def test_get_missing_schema(self):
        response = self._get_schema("bogus")
        self.assertEqual(response.status_code, 404)

    def _get_alert(self, alert_id: str) -> requests.Response:
        host = self.server_host
        port = self.server_port
        url = f"http://{host}:{port}/v1/alerts/{alert_id}"
        logger.info("fetching %s", url)
        return requests.get(url)

    def _get_schema(self, schema_id: str) -> requests.Response:
        host = self.server_host
        port = self.server_port
        url = f"http://{host}:{port}/v1/schemas/{schema_id}"
        logger.info("fetching %s", url)
        return requests.get(url)
