import base64
import os
from os.path import expanduser
import codecs
import grpc
import sys

from grpc_generated import rpc_pb2_grpc as lnrpc, rpc_pb2 as ln

MESSAGE_SIZE_MB = 50 * 1024 * 1024


def debug(message):
    sys.stderr.write(message + "\n")


class Lnd:
    def __init__(self, lnd_dir, server):
        os.environ['GRPC_SSL_CIPHER_SUITES'] = 'HIGH+ECDSA'
        lnd_dir = expanduser(lnd_dir)
        combined_credentials = self.get_credentials(lnd_dir)
        channel_options = [
            ('grpc.max_message_length', MESSAGE_SIZE_MB),
            ('grpc.max_receive_message_length', MESSAGE_SIZE_MB)
        ]
        grpc_channel = grpc.secure_channel(server, combined_credentials, channel_options)
        self.stub = lnrpc.LightningStub(grpc_channel)
        self.graph = None
        self.info = None
        self.channels = None
        self.node_info = {}
        self.chan_info = {}
        self.feereport = self.get_feereport()

    @staticmethod
    def get_credentials(lnd_dir):
        tls_certificate = open(lnd_dir + '/tls.cert', 'rb').read()
        ssl_credentials = grpc.ssl_channel_credentials(tls_certificate)
        try:
            macaroon = codecs.encode(open(lnd_dir + '/data/chain/bitcoin/mainnet/charge-lnd.macaroon', 'rb').read(), 'hex')
        except:
            macaroon = codecs.encode(open(lnd_dir + '/data/chain/bitcoin/mainnet/admin.macaroon', 'rb').read(), 'hex')
        auth_credentials = grpc.metadata_call_credentials(lambda _, callback: callback([('macaroon', macaroon)], None))
        combined_credentials = grpc.composite_channel_credentials(ssl_credentials, auth_credentials)
        return combined_credentials

    def get_info(self):
        if self.info is None:
            self.info = self.stub.GetInfo(ln.GetInfoRequest())
        return self.info

    def get_feereport(self):
        feereport = self.stub.FeeReport(ln.FeeReportRequest())
        feedict = {}
        for channel_fee in feereport.channel_fees:
            feedict[channel_fee.chan_id] = (channel_fee.base_fee_msat, channel_fee.fee_per_mil)
        return feedict

    def get_node_info(self, nodepubkey):
        if not nodepubkey in self.node_info:
            self.node_info[nodepubkey] = self.stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=nodepubkey))
        return self.node_info[nodepubkey]

    def get_chan_info(self, chanid):
        if not chanid in self.chan_info:
            try:
                self.chan_info[chanid] = self.stub.GetChanInfo(ln.ChanInfoRequest(chan_id=chanid))
            except:
                print("Failed to lookup {}".format(chanid),file=sys.stderr)
                return None
        return self.chan_info[chanid]

    def update_chan_policy(self, chanid, base_fee_msat, fee_ppm, min_htlc_msat, max_htlc_msat, time_lock_delta):
        chan_info = self.get_chan_info(chanid)
        if not chan_info:
            return None
        channel_point = ln.ChannelPoint(
            funding_txid_str=chan_info.chan_point.split(':')[0],
            output_index=int(chan_info.chan_point.split(':')[1])
        )
        my_policy = chan_info.node1_policy if chan_info.node1_pub == self.get_own_pubkey() else chan_info.node2_policy
        print((min_htlc_msat if min_htlc_msat is not None else my_policy.min_htlc))
        print((max_htlc_msat if max_htlc_msat is not None else my_policy.max_htlc_msat))
        print((time_lock_delta if time_lock_delta is not None else my_policy.time_lock_delta))
        return self.stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(
            chan_point=channel_point,
            base_fee_msat=(base_fee_msat if base_fee_msat is not None else my_policy.fee_base_msat),
            fee_rate=fee_ppm/1000000 if fee_ppm is not None else my_policy.fee_rate_milli_msat/1000000,
            min_htlc_msat=(min_htlc_msat if min_htlc_msat is not None else my_policy.min_htlc),
            min_htlc_msat_specified=min_htlc_msat is not None,
            max_htlc_msat=(max_htlc_msat if max_htlc_msat is not None else my_policy.max_htlc_msat),
            time_lock_delta=(time_lock_delta if time_lock_delta is not None else my_policy.time_lock_delta)
        ))

    def get_txns(self, start_height = None, end_height = None):
        return self.stub.GetTransactions(ln.GetTransactionsRequest(
            start_height=start_height,
            end_height=end_height
        ))

    def get_graph(self):
        if self.graph is None:
            self.graph = self.stub.DescribeGraph(ln.ChannelGraphRequest(include_unannounced=True))
        return self.graph

    def get_own_pubkey(self):
        return self.get_info().identity_pubkey

    def get_edges(self):
        return self.get_graph().edges

    def get_channels(self):
        if self.channels is None:
            request = ln.ListChannelsRequest()
            self.channels = self.stub.ListChannels(request).channels
        return self.channels

    @staticmethod
    def hex_string_to_bytes(hex_string):
        decode_hex = codecs.getdecoder("hex_codec")
        return decode_hex(hex_string)[0]
