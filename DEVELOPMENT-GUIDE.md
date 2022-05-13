# Development guide

Opinionated guide for getting started developing on charge-lnd.

Requirements:
 - Linux (used for this guide)
 - LND node (for testing changes)

## Virtual environment

Libraries will need to be installed in order for charge-lnd to work. Create a virtual environment so the libraries can be installed.

First create the virtual environment.
```
python -m venv ./venv
```

Make sure your Python version is Python 3.

Enter the virtual environment.
```
source venv/bin/activate
```

Or use the `activate` which works for your terminal such as `activate.fish` for the fish terminal.


Install charge-lnd with requirements.
```
pip install -f requirements.txt .
```

Test to see if charge-lnd is basically working.

```
./venv/bin/charge-lnd --help
```

## Reinstall charge-lnd when source files change

Every time a source file is changed, the charge-lnd script will need to be installed again.

```
pip install .
```

For quicker development feedback, it is recommended to build/install the changes right away after source files changes. On Linux `entr` command can be used to watch for source file changes.


```
find charge_lnd -name '*.py' | entr -s 'pip install .'
```

Make sure your terminal is in the virtual environment or the pip command won't work.

## Test changes

There are currently no automated test for charge-lnd so manual testing is required. If you are testing against your own node, use `--dry-run` to avoid making unnecessary changes. A macaroon can also be created without the `offchain:write` permission. See [INSTALL.md](INSTALL.md) for details on creating a macaroon.

After getting your nodes tls certificate, creating your macaroon for charge-lnd and creating a test config file, a test command can be run against your own node.
```
./venv/bin/charge-lnd --tlscert tls.cert --macaroon charge-lnd.macaroon --grpc mynode.domain:10009 --dry-run -c charge-lnd.config
```
