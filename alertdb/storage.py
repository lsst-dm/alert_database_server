import abc
import os.path

import google.cloud.storage as gcs


class AlertDatabaseBackend(abc.ABC):
    @abc.abstractmethod
    def get_alert(self, alert_id: str) -> bytes:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_schema(self, schema_id: str) -> bytes:
        raise NotImplementedError()


class FileBackend(AlertDatabaseBackend):
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
    def __init__(self, gcp_project: str, bucket_name: str):
        self.object_store_client = gcs.Client(project=gcp_project)
        self.bucket = self.object_store_client.bucket(bucket_name)

    def get_alert(self, alert_id: str) -> bytes:
        blob = self.bucket.blob(f"/alert_archive/v1/alerts/{alert_id}.avro.gz")
        return blob.download_as_bytes()

    def get_schema(self, schema_id: str) -> bytes:
        blob = self.bucket.blob(f"/alert_archive/v1/schemas/{schema_id}.json")
        return blob.download_as_bytes()


class NotFoundError(Exception):
    pass
