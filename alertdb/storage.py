"""
Implementations of backend storage systems for the alert database server.
"""

import abc
import logging
import os.path

import boto3

logger = logging.getLogger(__name__)


class AlertDatabaseBackend(abc.ABC):
    """
    An abstract interface representing a storage backend for alerts and
    schemas.
    """

    @abc.abstractmethod
    def get_alert(self, alert_id: str) -> bytes:
        """
        Retrieve a single alert's payload, in compressed Confluent Wire Format.

        Confluent Wire Format is described here:
          https://docs.confluent.io/platform/current/schema-registry/serdes-develop/index.html#wire-format

        To summarize, it is a 5-byte header, followed by binary-encoded Avro
        data.

        The first header byte is magic byte, with a value of 0.
        The next 4 bytes are a 4-byte schema ID, which is an unsigned 32-bit
        integer in big-endian order.

        Parameters
        ----------
        alert_id : str
            The ID of the alert to be retrieved.

        Returns
        -------
        bytes
            The alert contents in compressed Confluent Wire Format: serialized
            with Avro's binary encoding, prefixed with a magic byte and the
            schema ID, and then compressed with gzip.

        Raises
        ------
        NotFoundError
            If no alert can be found with that ID.

        Examples
        --------
        >>> import gzip
        >>> import struct
        >>> import io
        >>> raw_response = backend.get_alert("alert-id")
        >>> wire_format_payload = io.BytesIO(gzip.decompress(raw_response))
        >>> magic_byte = wire_format_payload.read(1)
        >>> schema_id = struct.unpack(">I", wire_format_payload.read(4))
        >>> alert_contents = wire_format_payload.read()
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_schema(self, schema_id: str) -> bytes:
        """
        Retrieve a single alert schema JSON document in its JSON-serialized
        form.

        Parameters
        ----------
        schema_id : str
            The ID of the schema to be retrieved.

        Returns
        -------
        bytes
            The schema document, encoded with JSON.

        Raises
        ------
        NotFoundError
            If no schema can be found with that ID.

        Examples
        --------
        >>> import gzip
        >>> import struct
        >>> import io
        >>> import json
        >>> import fastavro
        >>>
        >>> # Get an alert from the backend, and extract its schema ID
        >>> alert_payload = backend.get_alert("alert-id")
        >>> wire_format_payload = io.BytesIO(gzip.decompress(alert_payload))
        >>> magic_byte = wire_format_payload.read(1)
        >>> schema_id = struct.unpack(">I", wire_format_payload.read(4))
        >>>
        >>> # Download and use the schema
        >>> schema_bytes = backend.get_schema(schema_id)
        >>> schema = fastavro.parse(json.loads(schema_bytes))
        """
        raise NotImplementedError()


class FileBackend(AlertDatabaseBackend):
    """
    Retrieves alerts and schemas from a directory on disk.

    This is provided as an example, to ensure that it's clear how to implement
    an AlertDatabaseBackend subclass.
    """

    def __init__(self, root_dir: str):
        self.root_dir = root_dir

    def get_alert(self, alert_id: str) -> bytes:
        try:
            with open(os.path.join(self.root_dir, "alerts", alert_id), "rb") as f:
                return f.read()
        except FileNotFoundError as file_not_found:
            raise NotFoundError("alert not found") from file_not_found

    def get_schema(self, schema_id: str) -> bytes:
        try:
            with open(os.path.join(self.root_dir, "schemas", schema_id), "rb") as f:
                return f.read()
        except FileNotFoundError as file_not_found:
            raise NotFoundError("schema not found") from file_not_found


class USDFObjectStorageBackend(AlertDatabaseBackend):

    def __init__(
        self, endpoint_url: str, packet_bucket_name: str, schema_bucket_name: str
    ):
        self.object_store_client = boto3.client(
            "s3", endpoint_url=endpoint_url
        )  # Default way of getting a boto3 client that an talk to s3
        self.packet_bucket = packet_bucket_name
        self.schema_bucket = schema_bucket_name

    def get_alert(self, alert_id: str) -> bytes:
        logger.info("retrieving alert id=%s", alert_id)
        try:
            alert_key = f"/alert_archive/v1/alerts/{alert_id}.avro.gz"
            # boto3 terminology for objects, objects live in prefixes inside
            # of buckets
            blob = self.object_store_client.get_object(
                Bucket=self.packet_bucket, Key=alert_key
            )
            return blob["Body"].read()
        except self.object_store_client.exceptions.NoSuchKey as not_found:
            raise NotFoundError("alert not found") from not_found

    def get_schema(self, schema_id: str) -> bytes:
        logger.info("retrieving schema id=%s", schema_id)
        try:
            schema_key = f"/alert_archive/v1/schemas/{schema_id}.json"
            blob = self.object_store_client.get_object(
                Bucket=self.schema_bucket, Key=schema_key
            )
            return blob["Body"].read()
        except self.object_store_client.exceptions.NoSuchKey as not_found:
            raise NotFoundError("alert not found") from not_found


class NotFoundError(Exception):
    """
    Error which represents a failure to find an alert or schema in a backend.
    """
