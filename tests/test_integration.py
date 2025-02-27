import logging
import os
import unittest

import boto3
import botocore
import requests

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
        test_endpoint = os.environ.get("ALERTDB_TEST_ENDPOINT", None)
        if test_endpoint is None:
            raise unittest.SkipTest(
                "the $ALERTDB_TEST_ENDPOINT environment variable must be set"
            )
        packet_bucket_name = "alertdb-server-integration-test-bucket-packets"
        schema_bucket_name = "alertdb-server-integration-test-bucket-schemas"
        s3 = boto3.client("s3", endpoint_url=test_endpoint)

        logger.info("creating bucket %s", packet_bucket_name)
        # Need to update this, it doesn't work with boto3
        s3.create_bucket(Bucket=packet_bucket_name)

        def delete_packet_bucket():
            logger.info("deleting bucket %s", packet_bucket_name)
            s3.delete_bucket(Bucket=packet_bucket_name)

        cls.addClassCleanup(delete_packet_bucket)

        logger.info("creating bucket %s", schema_bucket_name)
        s3.create_bucket(Bucket=schema_bucket_name)

        def delete_schema_bucket():
            logger.info("deleting bucket %s", schema_bucket_name)
            s3.delete_bucket(Bucket=schema_bucket_name)

        cls.addClassCleanup(delete_schema_bucket)

        # Populate the test bucket with a few objects in the expected locations
        def delete_blob(key_id, bucket_name):
            # Callback to delete a blob during cleanup.
            logger.info("deleting blob %s", alert_id)
            s3.delete_objects(Bucket=bucket_name, Delete={"Objects": [{"Key": key_id}]})

        alerts = {
            "alert-id-1": b"payload-1",
            "alert-id-2": b"payload-2",
            "alert-id-3": b"payload-3",
        }
        for alert_id, alert_payload in alerts.items():
            alert_key = f"v1/alerts/{alert_id}.avro"
            s3.put_object(Body=alert_payload, Bucket=packet_bucket_name, Key=alert_key)
            logger.info("uploading alert %s", alert_id)
            cls.addClassCleanup(delete_blob, alert_key, packet_bucket_name)

        schemas = {
            "1": b"schema-payload-1",
            "2": b"schema-payload-2",
            "3": b"schema-payload-3",
        }
        for schema_id, schema_payload in schemas.items():
            schema_key = f"/v1/schemas/{schema_id}"
            s3.put_object(
                Body=schema_payload, Bucket=schema_bucket_name, Key=schema_key
            )
            logger.info("uploading blob %s", schema_id)
            cls.addClassCleanup(delete_blob, schema_key, schema_bucket_name)

        cls.endpoint_url = test_endpoint
        cls.packet_bucket_name = packet_bucket_name
        cls.schema_bucket_name = schema_bucket_name
        cls.stored_alerts = alerts
        cls.stored_schemas = schemas

    def setUp(self):
        """
        Run a local instance of the server.
        """
        backend = USDFObjectStorageBackend(
            self.endpoint_url, self.packet_bucket_name, self.schema_bucket_name
        )
        self.server = create_server(backend)
        self.s3 = boto3.client("s3", endpoint_url=self.endpoint_url)

    def test_get_existing_alerts(self):
        """Test that retrieving an alert over HTTP works as expected."""
        for alert_id, alert in self.stored_alerts.items():
            response = self._get_alert(alert_id)
            self.assertEqual(response["ResponseMetadata"]["HTTPStatusCode"], 200)
            self.assertEqual(response["Body"].read(), alert)

    def test_get_existing_schemas(self):
        """Test that retrieving a schema over HTTP works as expected."""
        for schema_id, schema in self.stored_schemas.items():
            response = self._get_schema(schema_id)
            self.assertEqual(response["ResponseMetadata"]["HTTPStatusCode"], 200)
            self.assertEqual(response["Body"].read(), schema)

    def test_get_missing_alert(self):
        """Test that retrieving an alert that does not exist gives a 404."""
        response = self._get_alert("bogus")
        self.assertEqual(response, "NoSuchKey")

    def test_get_missing_schema(self):
        """Test that retrieving a schema that does not exist gives a 404."""
        response = self._get_schema("bogus")
        self.assertEqual(response, "NoSuchKey")

    def test_healthcheck(self):
        """Test that the healthcheck endpoint returns 200."""
        response = self.s3.head_bucket(Bucket=self.schema_bucket_name)
        self.assertEqual(response["ResponseMetadata"]["HTTPStatusCode"], 200)
        response = self.s3.head_bucket(Bucket=self.packet_bucket_name)
        self.assertEqual(response["ResponseMetadata"]["HTTPStatusCode"], 200)

    def _get_alert(self, alert_id: str) -> requests.Response:
        alert_key = f"v1/alerts/{alert_id}.avro"
        alert_bucket = "alertdb-server-integration-test-bucket-packets"
        try:
            return self.s3.gOet_object(Bucket=alert_bucket, Key=alert_key)
        except botocore.exceptions.ClientError as err:
            return err.response["Error"]["Code"]

    def _get_schema(self, schema_id: str) -> requests.Response:
        schema_key = f"/v1/schemas/{schema_id}"
        schema_bucket_name = "alertdb-server-integration-test-bucket-schemas"
        try:
            return self.s3.get_object(Bucket=schema_bucket_name, Key=schema_key)
        except botocore.exceptions.ClientError as err:
            return err.response["Error"]["Code"]
