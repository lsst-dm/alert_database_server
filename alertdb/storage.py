"""
Implementations of backend storage systems for the alert database server.
"""

import abc
import os.path

import google.api_core.exceptions
import google.cloud.storage as gcs


class AlertDatabaseBackend(abc.ABC):
    """
    An abstract interface representing a storage backend for alerts and schemas.
    """

    @abc.abstractmethod
    def get_alert(self, alert_id: str) -> bytes:
        """
        Retrieve a single alert's payload, in compressed Confluent Wire Format.

        Confluent Wire Format is described here:
          https://docs.confluent.io/platform/current/schema-registry/serdes-develop/index.html#wire-format

        To summarize, it is a 5-byte header, followed by binary-encoded Avro data.

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
        """Retrieve a single alert schema JSON document in its JSON-serialized form.

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
        >>> alert_payload = backend.get_alert("alert-id")
        >>> alert_payload = gzip.decompress(alert_payload)
        >>> alert_
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


class GoogleObjectStorageBackend(AlertDatabaseBackend):
    """
    Retrieves alerts and schemas from a Google Cloud Storage bucket.

    The path for alert and schema objects follows the scheme in DMTN-183.
    """
    def __init__(self, gcp_project: str, bucket_name: str):
        self.object_store_client = gcs.Client(project=gcp_project)
        self.bucket = self.object_store_client.bucket(bucket_name)

    def get_alert(self, alert_id: str) -> bytes:
        try:
            blob = self.bucket.blob(f"/alert_archive/v1/alerts/{alert_id}.avro.gz")
            return blob.download_as_bytes()
        except google.api_core.exceptions.NotFound as not_found:
            raise NotFoundError("alert not found") from not_found

    def get_schema(self, schema_id: str) -> bytes:
        try:
            blob = self.bucket.blob(f"/alert_archive/v1/schemas/{schema_id}.json")
            return blob.download_as_bytes()
        except google.api_core.exceptions.NotFound as not_found:
            raise NotFoundError("alert not found") from not_found


class NotFoundError(Exception):
    """Error which represents a failure to find an alert or schema in a backend."""
