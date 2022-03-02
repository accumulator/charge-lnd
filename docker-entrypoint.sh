#!/usr/bin/env sh

TLS_CERT_PATH=${TLS_CERT_PATH:-$LND_DIR/tls.cert}
if [ -z "$MACAROON_PATH" ]
then
  exec /usr/local/bin/charge-lnd \
    --grpc "${GRPC_LOCATION}" \
    --lnddir "${LND_DIR}" \
    --tlscertpath "${TLS_CERT_PATH}"
    -c "${CONFIG_LOCATION}" \
    "$@"
else
  exec /usr/local/bin/charge-lnd \
    --grpc "${GRPC_LOCATION}" \
    --lnddir "${LND_DIR}" \
    --tlscertpath "${TLS_CERT_PATH}"
    --macaroonpath "${MACAROON_PATH}"
    -c "${CONFIG_LOCATION}" \
    "$@"
fi
  
