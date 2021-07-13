# `alert_database_server` #

This is the implementation of the Rubin Observatory's alert database server. The
technical design of this system is described in
[DMTN-183](https://dmtn-183.lsst.io/).

## Installation ##

Clone, and install with `pip` (in a virtual environment, if you like):

```
git clone github.com/lsst-dm/alert_database_server
cd alert_database_server
pip install .
```

## Running the server ##

The server is installed by `pip` as a command named `alertdb`:
```
