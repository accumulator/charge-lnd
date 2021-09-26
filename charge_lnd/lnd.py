import base64
import os
from os.path import expanduser
import codecs
import grpc
import sys
import re

from .grpc_generated import rpc_pb2_grpc as lnrpc, rpc_pb2 as ln
from .grpc_generated import router_pb2_grpc as routerrpc, router_pb2 as router

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
        self.routerstub = routerrpc.RouterStub(grpc_channel)
        self.graph = None
        self.info = None
        self.channels = None
        self.node_info = {}
        self.chan_info = {}
        self.valid = True
        try:
            self.feereport = self.get_feereport()
        except grpc._channel._InactiveRpcError:
            self.valid = False

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

    def get_forward_history(self, out_chanid, start_time, end_time):
        out_chan_forwards = []
        index_offset = 0
        done = False
        while not done:
            forwards = self.stub.ForwardingHistory(ln.ForwardingHistoryRequest(start_time=start_time, end_time=end_time, index_offset=index_offset )) 
            if forwards.forwarding_events:
                for forward in forwards.forwarding_events:
                    if forward.chan_id_out == out_chanid:
                        out_chan_forwards.append(forward)
                index_offset = forwards.last_offset_index
            else:
                done = True

        return out_chan_forwards

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

    def min_version(self, major, minor, patch=0):
        p = re.compile("(\d+)\.(\d+)\.(\d+).*")
        m = p.match(self.get_info().version)
        if m is None:
            return False
        if major > int(m.group(1)):
            return False
        if minor > int(m.group(2)):
            return False
        if patch > int(m.group(3)):
            return False
        return True

    def update_chan_status(self, chanid, disable):
        chan_info = self.get_chan_info(chanid)
        if not chan_info:
            return None
        channel_point = ln.ChannelPoint(
            funding_txid_str=chan_info.chan_point.split(':')[0],
            output_index=int(chan_info.chan_point.split(':')[1])
        )
        my_policy = chan_info.node1_policy if chan_info.node1_pub == self.get_own_pubkey() else chan_info.node2_policy
        # ugly code, retries with 'AUTO' if channel turns out not to be active.
        # Alternative is to iterate or index the channel list, just to get active status
        try:
            action = 'DISABLE' if disable else 'ENABLE'
            self.routerstub.UpdateChanStatus(router.UpdateChanStatusRequest(
                chan_point=channel_point,
                action=action
                ))
        except:
            action = 'DISABLE' if disable else 'AUTO'
            self.routerstub.UpdateChanStatus(router.UpdateChanStatusRequest(
                chan_point=channel_point,
                action=action
                ))

    @staticmethod
    def hex_string_to_bytes(hex_string):
        decode_hex = codecs.getdecoder("hex_codec")
        return decode_hex(hex_string)[0]
