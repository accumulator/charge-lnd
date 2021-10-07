# Installation

This script needs a moderately recent LND (https://github.com/lightningnetwork/lnd) instance running.

You don't need to have full admin rights to use charge-lnd. The following access rights are used:
- `offchain:read`
- `offchain:write`
- `onchain:read`
- `info:read`

You should create a suitably limited macaroon by issuing:

```
$ lncli bakemacaroon offchain:read offchain:write onchain:read info:read --save_to=~/.lnd/data/chain/bitcoin/mainnet/charge-lnd.macaroon
```

By default charge-lnd connects to `localhost:10009`, using the macaroon file in `~/.lnd/data/chain/bitcoin/mainnet/charge-lnd.macaroon`. If `charge-lnd.macaroon` is not found, `admin.macaroon` will be tried.

If you need to change these defaults, please have a look at the optional arguments `--grpc` and `--lnddir`.

## Install from source

Python and PIP should be made available on the system before installing from source.
The project and its dependencies can be installed by running (don't forget the last dot):

```
$ pip install -r requirements.txt .
```

On some systems using Python 3, use pip3 instead:

```
$ pip3 install -r requirements.txt .
```

When running the install as `root`, `charge-lnd` will be installed to `/usr/local/bin`. Otherwise `charge-lnd` will be installed to `$HOME/.local/bin`.

## Install using docker image

If you don't want to install from source, you can use a pre-baked docker image.

charge-lnd is available from [Docker Hub](https://hub.docker.com/repository/docker/accumulator/charge-lnd), and can be installed by

```
$ docker pull accumulator/charge-lnd
```

When running charge-lnd using docker, you'll need to map the LND dir and the volume/path containing the policy config file(s) into the container and pass the endpoint of the LND instance. For example:

```
docker run --rm -v /path/to/my-charge-lnd-configs-folder:/app -v ~/.lnd:/home/charge/.lnd -e GRPC_LOCATION=YOUR.LND.IP.ADDRESS:10009 accumulator/charge-lnd
```


# Running charge-lnd periodically

charge-lnd runs only once, and exits after processing all channels. To keep your fees updated as conditions change, you'll need to make sure charge-lnd runs periodically.

Typically on unix systems, this is done using a service called `cron`.

There are a number of different Lightning Node solutions. There is no one-size-fits-all cron configuration to show here, so if you can't get it to work, check the following:

1. Which user do I run charge-lnd as? charge-lnd needs to be able to read its macaroon file, and it needs access to the TLS certificate (tls.cert). Make sure charge-lnd can access those files.
2. charge-lnd needs to be able to read its policy config file(s)
3. if LND and/or charge-lnd is running in docker, check that charge-lnd can reach LND over the network.
4. Check if you are running via system cron (runs as user root) or user cron (runs as that specific user). When running from system cron, you might need 'sudo' or 'runas' to run as the correct user.

General note: it is advised to not run charge-lnd too often (more frequently than once per hour), as this spams the lightning gossip and might even increase forwarding fail rate. If you do want to run it more frequently, please set a reasonable min_fee_ppm_delta (>5) to avoid applying minor fee changes.

## Raspiblitz

[Full Guide by The Count](https://nullcount.com/install-charge-lnd-routing-fees-on-autopilot/)

1. install charge-lnd as user 'bitcoin'
2. create a policy config file (/home/bitcoin/charge-lnd/charge.config)
3. create a cron entry to run charge-lnd once per hour

```
sudo su - bitcoin
crontab -e
```

at the end of the file, add this

```
0 * * * * /home/bitcoin/.local/bin/charge-lnd -c /home/bitcoin/charge-lnd/charge.config
```

.. and save the file.

Done!

## Umbrel
[Full Guide by entrepenewer](https://community.getumbrel.com/t/guide-installing-charge-lnd-in-a-docker-to-automate-your-fee-policies/2187)

1. login using SSH
2. install charge-lnd docker container
3. create folder ~/apps/charge-lnd to hold the policy config file(s)
4. create a policy config file
5. create a cron entry to run charge-lnd once per hour

```
crontab -e
```

at the end of the file, add this

```
0 * * * * docker run --rm --network=umbrel_main_network  -e GRPC_LOCATION=YOUR.LND.IP.ADDRESS:10009 -e LND_DIR=/data/.lnd -e CONFIG_LOCATION=/app/charge.config -v /home/umbrel/umbrel/lnd:/data/.lnd  -v /home/umbrel/umbrel/apps/charge-lnd:/app accumulator/charge-lnd:latest
```

.. and save the file.

Done!

[Full Guide by Plebnet - non docker](https://plebnet.wiki/wiki/Fees_And_Profitability#Installing_Charge-Lnd)
1. login using SSH
2. change directory to home ```cd ~```
3. get latest from git ```git clone https://github.com/accumulator/charge-lnd```
4. change directory to charge-lnd ```cd charge-lnd```
5. build with pip3 ```pip3 install -r requirements.txt .```
6. test installaion ```~/.local/bin/charge-lnd --help```
7. configure config file
8. do a dry run ```~/.local/bin/charge-lnd --lnddir ~/umbrel/lnd -c ~/charge-lnd/myconfig --dry-run```
9. create crontab entry

```
crontab -e
```

at the end of the file, add the following line
```
42 * * * * /home/umbrel/.local/bin/charge-lnd --lnddir /home/umbrel/umbrel/lnd -c /home/umbrel/charge-lnd/myconfig > /tmp/charge-lnd.log 2>&1; date >> /tmp/charge-lnd.log
```
save ```ctrl -x y``` exit ```enter```

Done!

