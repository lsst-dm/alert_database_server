import argparse
import logging

import uvicorn

from alertdb.server import create_server
from alertdb.storage import FileBackend, USDFObjectStorageBackend

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        "alertdb",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Run an alert database HTTP server.",
    )
    parser.add_argument(
        "--listen-host",
        type=str,
        default="127.0.0.1",
        help="host address to listen on for requests",
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=5000,
        help="host port to listen on for requests",
    )
    parser.add_argument(
        "--backend",
        type=str,
        choices=("local-files", "google-cloud"),
        default="local-files",
        help="backend to use to source alerts",
    )
    parser.add_argument(
        "--local-file-root",
        type=str,
        default=None,
        help="when using the local-files backend, the root directory where alerts should be found",
    )
    parser.add_argument(
        "--gcp-project",
        type=str,
        default=None,
        help="when using the google-cloud backend, the name of the GCP project",
    )
    parser.add_argument(
        "--gcp-bucket-alerts",
        type=str,
        default="alert-packets",
        help="when using the google-cloud backend, the name of the boto3 bucket for alert packets",
    )
    parser.add_argument(
        "--gcp-bucket-schemas",
        type=str,
        default="alert-schemas",
        help="when using the google-cloud backend, the name of the boto3 bucket for alert schemas",
    )
    parser.add_argument("--verbose", action="store_true", help="log a bunch")
    parser.add_argument("--debug", action="store_true", help="log even more")

    args = parser.parse_args()

    if args.debug:
        uvicorn_log_level = "debug"
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose:
        uvicorn_log_level = "info"
        logging.basicConfig(level=logging.INFO)
    else:
        uvicorn_log_level = "info"
        logging.basicConfig(level=logging.WARNING)

    logger.info("initializing alert database server backend")

    # Configure the right backend
    if args.backend == "local-files":
        logger.info("using local-files backend")

        if args.local_file_root is None:
            parser.error("--backend=local-files requires --local-file-root be set")
        logger.info("root of file backend: %s", args.local_file_root)

        backend = FileBackend(args.local_file_root)

    elif args.backend == "google-cloud":
        logger.info("using google-cloud backend")

        if args.gcp_project is None:
            parser.error("--backend=google-cloud requires --gcp-project be set")
        logger.info("gcp_project: %s", args.gcp_project)

        if args.gcp_bucket_alerts is None or args.gcp_bucket_schemas is None:
            parser.error(
                "--backend=google-cloud requires --gcp-bucket-alerts and --gcp-bucket-schemas be set"
            )
        logger.info("gcp_bucket_alerts: %s", args.gcp_bucket_alerts)
        logger.info("gcp_bucket_schemas: %s", args.gcp_bucket_schemas)

        backend = USDFObjectStorageBackend(
            args.gcp_project, args.gcp_bucket_alerts, args.gcp_bucket_schemas
        )

    else:
        # Shouldn't be possible if argparse is using the choices parameter as
        # expected...
        raise AssertionError(
            "only valid --backend choices are local-files and google-cloud"
        )

    logger.info("backend initialized, creating server")
    server = create_server(backend)

    logger.info(
        "server initialized, running at %s:%s", args.listen_host, args.listen_port
    )
    uvicorn.run(
        server,
        host=args.listen_host,
        port=args.listen_port,
        log_level=uvicorn_log_level,
    )
