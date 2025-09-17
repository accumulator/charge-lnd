FROM python:3.13-slim

ENV GRPC_LOCATION=127.0.0.1:10009
ENV LND_DIR=~/.lnd
ENV CONFIG_LOCATION=/app/charge.config

ARG USER_ID=1000
ARG GROUP_ID=1000
ENV USER_ID=$USER_ID
ENV GROUP_ID=$GROUP_ID

RUN addgroup --gid $GROUP_ID charge
RUN adduser --home /home/charge --uid $USER_ID --gid $GROUP_ID --disabled-login charge

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint
RUN chmod +x /usr/local/bin/docker-entrypoint

WORKDIR /home/charge/src
COPY . .

RUN pip install -r requirements.txt .
RUN chown -R charge:charge /home/charge/src

WORKDIR /app
USER charge

ENTRYPOINT ["/usr/local/bin/docker-entrypoint"]
