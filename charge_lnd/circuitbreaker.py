import grpc
import operator
import sys

from .grpc_generated import circuitbreaker_pb2_grpc as cbrpc, circuitbreaker_pb2 as cb
from typing import Optional
from types import SimpleNamespace

MESSAGE_SIZE_MB = 50 * 1024 * 1024


def debug(message):
    sys.stderr.write(message + "\n")

# Aggregation function for two circuitbreaker modes, choosing
# the most conservative one.
def add_cb_modes(x, y):
    # MODE_BLOCK > MODE_FAIL > MODE_QUEUE > MODE_QUEUE_PEER_INITIATED
    prio={3: 0, 0: 1, 1: 2, 2: 3}

    if prio[x] < prio[y]:
        return x
    return y

# Aggregation of two numbers with 0 is equal to infinity.
def add_with_infty(x, y):
    if x == 0 or y == 0:
        return 0
    return x + y

# Aggregation of two operands with an arbitragy operator,
# where both operands can be none.
def add_with_none(x, y, op):
    if x is None:
        s = y
    elif y is None:
        s = x
    else:
        s = op(x,y)
    return s

class CircuitbreakerParams(SimpleNamespace):
    max_hourly_rate: Optional[int] = None
    max_pending: Optional[int] = None
    mode: Optional[int] = None
    clear_limit: Optional[bool] = None

    # In the case that we have several channels open for a peer,
    # we would like to aggregate the limit conservatively.
    def __add__(self, add):
        sum = CircuitbreakerParams()
        sum.max_hourly_rate = add_with_none(self.max_hourly_rate, add.max_hourly_rate, add_with_infty)
        sum.max_pending = add_with_none(self.max_pending, add.max_pending, add_with_infty)
        sum.mode = add_with_none(self.mode, add.mode, add_cb_modes)
        sum.clear_limit = add_with_none(self.clear_limit, add.clear_limit, operator.or_)

        return sum

class Circuitbreaker:
    def __init__(self, server):
        channel_options = [
            ('grpc.max_message_length', MESSAGE_SIZE_MB),
            ('grpc.max_receive_message_length', MESSAGE_SIZE_MB)
        ]
        grpc_channel = grpc.insecure_channel(server, channel_options)
        self.stub = cbrpc.ServiceStub(grpc_channel)
        self.info = None
        self.valid = True
        # dict of existing limits
        self.dict_limits = None
        # dict of circuitbreaker params per peer
        self.peer_params = {}

        try:
            _ = self.get_info()
        except grpc._channel._InactiveRpcError:
            self.valid = False

    def get_info(self):
        if not self.info:
            self.info = self.stub.GetInfo(cb.GetInfoRequest())
        return self.info

    def list_limits(self):
        return self.stub.ListLimits(cb.ListLimitsRequest())

    # Returns the current limit. limit can be either a pubkey
    # of a peer or 'default' for the default limit. We are returning
    # None if no peer limit is set.
    def get_limit(self, limitid):
        if self.dict_limits is None:
            self.dict_limits = {}
            list_limits = self.list_limits()
            for l in list_limits.limits:
                if l.HasField("limit"):
                    self.dict_limits[l.node] = l.limit
                else:
                    self.dict_limits[l.node] = None
            self.dict_limits["default"] = list_limits.default_limit

        return self.dict_limits.get(limitid)

    # Updating the internal circuitbreaker limits for a peer but not
    # sending updates to the backend.
    def apply_params(self, params, peerid):
        if peerid not in self.peer_params:
            self.peer_params[peerid] = CircuitbreakerParams()
        
        self.peer_params[peerid] += params

    # Returns the necessary limit deletes and updates to make backend
    # consistent with the current params.
    def get_limit_updates(self):
        clear_limits = []
        update_limits = {}
        for k, v in self.peer_params.items():
            if not any([
                v.max_hourly_rate is not None,
                v.max_pending is not None,
                v.mode is not None
            ]):
                if v.clear_limit is not None and v.clear_limit:
                    clear_limits.append(k)
                continue

            limit_ref = self.get_limit("default")
            limit = cb.Limit(
                max_hourly_rate=limit_ref.max_hourly_rate if v.max_hourly_rate is None else v.max_hourly_rate,
                max_pending=limit_ref.max_pending if v.max_pending is None else v.max_pending,
                mode=limit_ref.mode if v.mode is None else v.mode
            )
            update_limits[k] = limit

        return clear_limits, update_limits

    def update_limits(self, limits):
        return self.stub.UpdateLimits(cb.UpdateLimitsRequest(limits=limits))

    def clear_limits(self, nodes):
        return self.stub.ClearLimits(cb.ClearLimitsRequest(nodes=nodes))