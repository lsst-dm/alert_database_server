import pytest
from fastapi.testclient import TestClient

from alertdb.server import create_server
from alertdb.storage import FileBackend


@pytest.fixture
def file_backend(tmp_path):
    """Pytest fixture for a file-based backend"""
    yield FileBackend(str(tmp_path))


def test_server_healthcheck(file_backend):
    """Test that the server responds on the healthcheck endpoint."""
    server = create_server(file_backend)
    client = TestClient(server)
    response = client.get("/v1/health")
    assert response.status_code == 200
