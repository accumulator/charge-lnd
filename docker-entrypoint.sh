#!/usr/bin/env sh

exec /usr/local/bin/charge-lnd --grpc "${GRPC_LOCATION}" --lnddir "${LND_DIR}" -c "${CONFIG_LOCATION}" "$@"
