import asyncio
import aiorpcx

class Electrum:
    host = None
    port = None
    ssl = False
    # cache
    estimates = {}

    @staticmethod
    def set_server(server):
        if server is not None:
            split = server.split(':')
            Electrum.host = split[0]
            Electrum.port = int(split[1])
            if len(split) > 2:
                Electrum.ssl = split[2] == 's'

    @staticmethod
    async def _request_fee_estimate(numblocks):
        async with aiorpcx.connect_rs(Electrum.host, Electrum.port, ssl=Electrum.ssl) as session:
            result = await session.send_request('blockchain.estimatefee', [numblocks])
            # convert from btc/kbyte
            sat_per_byte = int(result * (100_000_000/1000))
            Electrum.estimates[numblocks] = sat_per_byte

    @staticmethod
    def get_fee_estimate(numblocks):
        if not numblocks in Electrum.estimates:
            asyncio.get_event_loop().run_until_complete(Electrum._request_fee_estimate(numblocks))
        if not numblocks in Electrum.estimates:
            return 0
        return Electrum.estimates[numblocks]
