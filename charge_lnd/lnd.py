import os
from os.path import expanduser
import codecs
import grpc
import sys
import re
import time
from types import SimpleNamespace

from .grpc_generated import lightning_pb2_grpc as lnrpc, lightning_pb2 as ln
from .grpc_generated import router_pb2_grpc as routerrpc, router_pb2 as router
from .grpc_generated import walletkit_pb2_grpc as walletkitrpc, walletkit_pb2 as walletkit

from .strategy import ChanParams, is_defined

MESSAGE_SIZE_MB = 50 * 1024 * 1024


def debug(message):
    sys.stderr.write(message + "\n")


class ChannelMetrics(SimpleNamespace):
    local_balance_settled: int = 0
    local_balance_unsettled: int = 0
    
    remote_balance_settled: int = 0
    remote_balance_unsettled: int = 0
    
    def local_balance_total(self):
        return self.local_balance_settled + self.local_balance_unsettled
    
    def remote_balance_total(self):
        return self.remote_balance_settled + self.remote_balance_unsettled


class PeerMetrics(SimpleNamespace):
    channels_active: int = 0
    channels_inactive: int = 0

    local_active_balance_settled: int = 0
    local_active_balance_unsettled: int = 0
    local_inactive_balance_settled: int = 0
    local_inactive_balance_unsettled: int = 0
    
    remote_active_balance_settled: int = 0
    remote_active_balance_unsettled: int = 0
    remote_inactive_balance_settled: int = 0
    remote_inactive_balance_unsettled: int = 0
    
    def local_active_balance_total(self):
        return self.local_active_balance_settled + self.local_active_balance_unsettled
    
    def remote_active_balance_total(self):
        return self.remote_active_balance_settled + self.remote_active_balance_unsettled
    
    def local_inactive_balance_total(self):
        return self.local_inactive_balance_settled + self.local_inactive_balance_unsettled
    
    def remote_inactive_balance_total(self):
        return self.remote_inactive_balance_settled + self.remote_inactive_balance_unsettled
    
    def active_balance_total(self):
        return self.local_active_balance_total() + self.remote_active_balance_total()
    
    def inactive_balance_total(self):
        return self.local_inactive_balance_total() + self.remote_inactive_balance_total()
    

def channel_metrics(channel):
    return ChannelMetrics(
        local_balance_settled=channel.local_balance,
        local_balance_unsettled=sum(h.amount for h in channel.pending_htlcs if not h.incoming),
        remote_balance_settled=channel.remote_balance,
        remote_balance_unsettled=sum(h.amount for h in channel.pending_htlcs if h.incoming)
    )

    
def peer_metrics(channels):
    pm = PeerMetrics()
    for channel in channels:
        cm = channel_metrics(channel)
        if channel.active:
            pm.local_active_balance_settled += cm.local_balance_settled
            pm.local_active_balance_unsettled += cm.local_balance_unsettled
            pm.remote_active_balance_settled += cm.remote_balance_settled
            pm.remote_active_balance_unsettled += cm.remote_balance_unsettled
            pm.channels_active += 1
        else:
            pm.local_inactive_balance_settled += cm.local_balance_settled
            pm.local_inactive_balance_unsettled += cm.local_balance_unsettled
            pm.remote_inactive_balance_settled += cm.remote_balance_settled
            pm.remote_inactive_balance_unsettled += cm.remote_balance_unsettled
            pm.channels_inactive += 1
    return pm


class Lnd:
    def __init__(self, lnd_dir, server, tls_cert_path=None, macaroon_path=None):
        os.environ['GRPC_SSL_CIPHER_SUITES'] = 'HIGH+ECDSA'
        lnd_dir = expanduser(lnd_dir)
        combined_credentials = self.get_credentials(lnd_dir, tls_cert_path, macaroon_path)
        channel_options = [
            ('grpc.max_message_length', MESSAGE_SIZE_MB),
            ('grpc.max_receive_message_length', MESSAGE_SIZE_MB)
        ]
        grpc_channel = grpc.secure_channel(server, combined_credentials, channel_options)
        self.lnstub = lnrpc.LightningStub(grpc_channel)
        self.routerstub = routerrpc.RouterStub(grpc_channel)
        self.walletstub = walletkitrpc.WalletKitStub(grpc_channel)
        self.graph = None
        self.info = None
        self.version = None
        self.synced_to_chain = None
        self.channels = None
        self.node_info = {}
        self.chan_info = {}
        self.fwdhistory = {}
        self.valid = True
        self.dict_channels = None
        self.peer_channels = {}
        self.chan_metrics = {}
        self.peer_metrics = {}
        try:
            self.feereport = self.get_feereport()
        except grpc._channel._InactiveRpcError:
            self.valid = False

    @staticmethod
    def get_credentials(lnd_dir, tls_cert_path, macaroon_path):
        tls_certificate = open(tls_cert_path if tls_cert_path else lnd_dir + '/tls.cert', 'rb').read()
        ssl_credentials = grpc.ssl_channel_credentials(tls_certificate)
        if macaroon_path:
            macaroon = codecs.encode(open(macaroon_path, 'rb').read(), 'hex')
        else:
            try:
                macaroon = codecs.encode(open(lnd_dir + '/data/chain/bitcoin/mainnet/charge-lnd.macaroon', 'rb').read(), 'hex')
            except:
                macaroon = codecs.encode(open(lnd_dir + '/data/chain/bitcoin/mainnet/admin.macaroon', 'rb').read(), 'hex')
        auth_credentials = grpc.metadata_call_credentials(lambda _, callback: callback([('macaroon', macaroon)], None))
        combined_credentials = grpc.composite_channel_credentials(ssl_credentials, auth_credentials)
        return combined_credentials

    def get_info(self):
        if self.info is None:
            self.info = self.lnstub.GetInfo(ln.GetInfoRequest())
        return self.info

    def supports_inbound_fees(self):
        return self.min_version(0, 18)
    
    def get_synced_to_chain(self):
        # It can happen that lnd is not synced to the chain for a few seconds, typically 
        # after a new block has been found or after a restart of lnd. If lnd is still
        # not synced to the chain after 5 minutes, we set the parameter to false.        
        if self.synced_to_chain is None:
            self.synced_to_chain = False
            for _ in range(300):
                if self.lnstub.GetInfo(ln.GetInfoRequest()).synced_to_chain:
                    self.synced_to_chain = True
                    break
                time.sleep(1)
        return self.synced_to_chain

    def get_feereport(self):
        feereport = self.lnstub.FeeReport(ln.FeeReportRequest())
        feedict = {}
        for channel_fee in feereport.channel_fees:
            feedict[channel_fee.chan_id] = (channel_fee.base_fee_msat, channel_fee.fee_per_mil)
        return feedict

    # query the forwarding history for a channel covering the last # of seconds
    def get_forward_history(self, chanid, seconds):
        # cache all history to avoid stomping on lnd
        last_time = self.fwdhistory['last'] if 'last' in self.fwdhistory else int(time.time())

        start_time = int(time.time()) - seconds
        leeway = 5 # don't call lnd on each second boundary
        if start_time < last_time - leeway:
            # retrieve (remaining) for the queried period
            index_offset = 0
            done = False
            thishistory = {}
            while not done:
                forwards = self.lnstub.ForwardingHistory(ln.ForwardingHistoryRequest(
                    start_time=start_time, end_time=last_time, index_offset=index_offset))
                if forwards.forwarding_events:
                    for forward in forwards.forwarding_events:
                        if not forward.chan_id_out in thishistory:
                            thishistory[forward.chan_id_out] = { 'in': [], 'out': []}
                        if not forward.chan_id_in in thishistory:
                            thishistory[forward.chan_id_in] = { 'in': [], 'out': []}
                        # most recent last
                        thishistory[forward.chan_id_out]['out'].append(forward)
                        thishistory[forward.chan_id_in]['in'].append(forward)
                    index_offset = forwards.last_offset_index
                else:
                    done = True

            # add queried to existing cache and keep time order
            for i in thishistory.keys():
                if not i in self.fwdhistory:
                    self.fwdhistory[i] = { 'in': [], 'out': []}
                self.fwdhistory[i]['in'] = thishistory[i]['in'] + self.fwdhistory[i]['in']
                self.fwdhistory[i]['out'] = thishistory[i]['out'] + self.fwdhistory[i]['out']

            self.fwdhistory['last'] = start_time

        chan_data = self.fwdhistory[chanid] if chanid in self.fwdhistory else { 'in': [], 'out': []}
        result = { 'htlc_in': 0, 'htlc_out': 0, 'sat_in': 0, 'sat_out': 0, 'last_in': 0, 'last_out': 0}

        for fwd in reversed(chan_data['in']):
            if fwd.timestamp < start_time:
                break
            result['htlc_in'] = result['htlc_in'] + 1
            result['sat_in'] = result['sat_in'] + fwd.amt_in
            result['last_in'] = fwd.timestamp

        for fwd in reversed(chan_data['out']):
            if fwd.timestamp < start_time:
                break
            result['htlc_out'] = result['htlc_out'] + 1
            result['sat_out'] = result['sat_out'] + fwd.amt_out
            result['last_out'] = fwd.timestamp

        return result


    def get_node_info(self, nodepubkey):
        if not nodepubkey in self.node_info:
            self.node_info[nodepubkey] = self.lnstub.GetNodeInfo(ln.NodeInfoRequest(pub_key=nodepubkey))
        return self.node_info[nodepubkey]

    def get_chan_info(self, chanid):
        if not chanid in self.chan_info:
            try:
                self.chan_info[chanid] = self.lnstub.GetChanInfo(ln.ChanInfoRequest(chan_id=chanid))
            except:
                print("Failed to lookup {}".format(chanid),file=sys.stderr)
                return None
        return self.chan_info[chanid]

    def update_chan_policy(self, chanid, chp: ChanParams):
        chan_info = self.get_chan_info(chanid)
        if not chan_info:
            return None
        channel_point = ln.ChannelPoint(
            funding_txid_str=chan_info.chan_point.split(':')[0],
            output_index=int(chan_info.chan_point.split(':')[1])
        )
        my_policy = chan_info.node1_policy if chan_info.node1_pub == self.get_own_pubkey() else chan_info.node2_policy
        return self.lnstub.UpdateChannelPolicy(ln.PolicyUpdateRequest(
            chan_point=channel_point,
            base_fee_msat=(chp.base_fee_msat if is_defined(chp.base_fee_msat) else my_policy.fee_base_msat),
            fee_rate=chp.fee_ppm/1000000 if is_defined(chp.fee_ppm) else my_policy.fee_rate_milli_msat/1000000,
            min_htlc_msat=(chp.min_htlc_msat if is_defined(chp.min_htlc_msat) else my_policy.min_htlc),
            min_htlc_msat_specified=is_defined(chp.min_htlc_msat),
            max_htlc_msat=(chp.max_htlc_msat if is_defined(chp.max_htlc_msat) else my_policy.max_htlc_msat),
            time_lock_delta=(chp.time_lock_delta if is_defined(chp.time_lock_delta) else my_policy.time_lock_delta),
            inbound_fee=ln.InboundFee(
            base_fee_msat=(chp.inbound_base_fee_msat if is_defined(chp.inbound_base_fee_msat) else my_policy.inbound_fee_base_msat),
            fee_rate_ppm=(chp.inbound_fee_ppm if is_defined(chp.inbound_fee_ppm) else my_policy.inbound_fee_rate_milli_msat)
        )))

    def get_txns(self, start_height = None, end_height = None):
        return self.lnstub.GetTransactions(ln.GetTransactionsRequest(
            start_height=start_height,
            end_height=end_height
        ))

    def get_graph(self):
        if self.graph is None:
            self.graph = self.lnstub.DescribeGraph(ln.ChannelGraphRequest(include_unannounced=True))
        return self.graph

    def get_own_pubkey(self):
        return self.get_info().identity_pubkey

    def get_edges(self):
        return self.get_graph().edges

    def get_channels(self):
        if self.channels is None:
            request = ln.ListChannelsRequest()
            self.channels = self.lnstub.ListChannels(request).channels
        return self.channels
    
    def get_dict_channels(self):
        if self.dict_channels is None:
            channels = self.get_channels()
            self.dict_channels = {}
            for c in channels:
                self.dict_channels[c.chan_id] = c
        return self.dict_channels
    
    def get_chan_metrics(self, chanid):
        if not chanid in self.chan_metrics:
            self.chan_metrics[chanid] = channel_metrics(self.get_dict_channels()[chanid])
        return self.chan_metrics[chanid]
    
    # Get all channels shared with a node
    def get_peer_channels(self, peerid):
        if not peerid in self.peer_channels:
            channels = self.get_channels()
            self.peer_channels[peerid] = [c for c in channels if c.remote_pubkey == peerid]
        return self.peer_channels[peerid]
  
    def get_peer_metrics(self, peerid):
        if not peerid in self.peer_metrics:
            self.peer_metrics[peerid] = peer_metrics(self.get_peer_channels(peerid))
        return self.peer_metrics[peerid]

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
    
    # returns the onchain fee in sat per vbyte for a given confirmation target
    def get_fee_estimate(self, numblocks):
        # numblocks less than 2 are rejected by walletrpc
        return self.walletstub.EstimateFee(walletkit.EstimateFeeRequest(conf_target=max(numblocks,2))).sat_per_kw * 4 / 1000

    @staticmethod
    def hex_string_to_bytes(hex_string):
        decode_hex = codecs.getdecoder("hex_codec")
        return decode_hex(hex_string)[0]
