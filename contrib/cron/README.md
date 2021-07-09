# Running charge-lnd periodically using cron

There are a number of different Lightning Node solutions. There is no one-size-fits-all cron configuration to show here, so if you can't get it to work, check the following:

1. Which user do I run charge-lnd as? charge-lnd needs to be able to read its macaroon file, and it needs access to the TLS certificate (tls.cert). Make sure charge-lnd can access those files.
2. charge-lnd needs to be able to read its policy config file(s)
3. if LND and/or charge-lnd is running in docker, check that charge-lnd can reach LND over the network.
4. Check if you are running via system cron (runs as user root) or user cron (runs as that specific user). When running from system cron, you might need 'sudo' or 'runas' to run as the correct user.

General note: it is advised to not run charge-lnd too often (more frequently than once per hour), as this spams the lightning gossip and might even increase forwarding fail rate. If you do want to run it more frequently, please set a reasonable min_fee_ppm_delta (>5) to avoid applying minor fee changes.

## Raspiblitz

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
