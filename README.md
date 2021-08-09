# `alert_database_server` #

This is the implementation of the Rubin Observatory's alert database server. The
technical design of this system is described in
[DMTN-183](https://dmtn-183.lsst.io/).

## Installation ##

Clone, and install with `pip` (in a virtual environment, if you like):

```
git clone github.com/lsst-dm/alert_database_server
cd alert_database_server
pip install -r requirements.txt
pip install .
```

## Running the server ##

The server is installed by `pip` as a command named `alertdb`:
```
% alertdb -h
usage: alertdb [-h] [--listen-host LISTEN_HOST] [--listen-port LISTEN_PORT]
               [--backend {local-files,google-cloud}]
               [--local-file-root LOCAL_FILE_ROOT] [--gcp-project GCP_PROJECT]
               [--gcp-bucket GCP_BUCKET]

Run an alert database HTTP server.

optional arguments:
  -h, --help            show this help message and exit
  --listen-host LISTEN_HOST
                        host address to listen on for requests (default:
                        127.0.0.1)
  --listen-port LISTEN_PORT
                        host port to listen on for requests (default: 5000)
  --backend {local-files,google-cloud}
                        backend to use to source alerts (default: local-files)
  --local-file-root LOCAL_FILE_ROOT
                        when using the local-files backend, the root directory
                        where alerts should be found (default: None)
  --gcp-project GCP_PROJECT
                        when using the google-cloud backend, the name of the
                        GCP project (default: None)
  --gcp-bucket GCP_BUCKET
                        when using the google-cloud backend, the name of the
                        Google Cloud Storage bucket (default: None)
```

## Development Setup

Clone as above, and then make a virtual environment and use
[pip-tools](https://github.com/jazzband/pip-tools) to synchronize your
environment. This is a one-time setup:

```
# Optional, but recommended: use a virtualenv
python3 -m virtualenv virtualenv
source virtualenv/bin/activate

# Install dependencies
pip install pip-tools
pip-sync requirements.txt dev-requirements.txt

# Install package
pip install --editable .

# Install precommit hooks
pre-commit install
```

### Running lint and mypy ###
Linters and mypy checks should run automatically when you go to commit. To run
them on-demand, you can use:

```
pre-commit run
```

That will only run on the files that you changed; to run on all files, use

```
pre-commit run --all-files
```

### Running tests ##

The only test is an integration test against the Interim Data Facility on Google
Cloud.

You'll need an activated Google Cloud SDK to use it (like with `gcloud auth
application-default login`).

Then, specify a GCP project to run against via an `$ALERTDB_TEST_GCP_PROJECT`
environment variable, and run the tests:

```
% export ALERTDB_TEST_GCP_PROJECT=alert-stream
% pytest
============================= test session starts ==============================
platform linux -- Python 3.8.10, pytest-6.2.4, py-1.10.0, pluggy-0.13.1
rootdir: /home/swnelson/code/rubin/alert_database_server
collected 4 items

tests/test_integration.py ....                                           [100%]

============================== 4 passed in 10.88s ==============================
```

The test needs permissions to create buckets and blobs in your project.
