#!/usr/bin/env sh

exec /app/charge-lnd.py --grpc "${GRPC_LOCATION}" --lnddir "${LND_DIR}" -c "${CONFIG_LOCATION}" "$@"