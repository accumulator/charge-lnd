FROM python:3-slim

ENV GRPC_LOCATION=127.0.0.1:10009
ENV LND_DIR=~/.lnd
ENV CONFIG_LOCATION=/app/charge.config

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint
RUN chmod +x /usr/local/bin/docker-entrypoint

WORKDIR /app/

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

ENTRYPOINT ["/usr/local/bin/docker-entrypoint"]