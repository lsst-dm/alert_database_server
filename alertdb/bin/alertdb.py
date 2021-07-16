import uvicorn
import argparse

from alertdb.server import create_server
from alertdb.storage import FileBackend, GoogleObjectStorageBackend


def main():
    parser = argparse.ArgumentParser("alertdb")
    parser.add_argument(
        "--listen-host", type=str, default="127.0.0.1",
        help="host address to listen on for requests",
    )
    parser.add_argument(
        "--listen-port", type=int, default=5000,
        help="host port to listen on for requests",
    )
    parser.add_argument(
        "--backend", type=str, choices=("local-files", "google-cloud"), default="local-files",
        help="backend to use to source alerts",
    )
    parser.add_argument(
        "--local-file-root", type=str, default=None,
        help="when using the local-files backend, the root directory where alerts should be found",
    )
    parser.add_argument(
        "--gcp-project", type=str, default=None,
        help="when using the google-cloud backend, the name of the GCP project",
    )
    parser.add_argument(
        "--gcp-bucket", type=str, default=None,
        help="when using the google-cloud backend, the name of the Google Cloud Storage bucket",
    )
    args = parser.parse_args()

    # Configure the right backend
    if args.backend == "local-files":
        if args.local_file_root is None:
            parser.error("--backend=local-files requires --local-file-root be set")
        backend = FileBackend(args.local_file_root)
    elif args.backend == "google-cloud":
        if args.gcp_project is None:
            parser.error("--backend=google-cloud requires --gcp-project be set")
        if args.gcp_bucket is None:
            parser.error("--backend=google-cloud requires --gcp-bucket be set")
        backend = GoogleObjectStorageBackend(args.gcp_project, args.gcp_bucket)
    else:
        # Shouldn't be possible if argparse is using the choices parameter as expected...
        raise AssertionError("only valid --backend choices are local-files and google-cloud")

    server = create_server(backend)
    uvicorn.run(server, host=args.listen_host, port=args.listen_port, log_level="info")
