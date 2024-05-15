# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: router.proto
# Protobuf Python Version: 5.26.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from . import lightning_pb2 as lightning__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0crouter.proto\x12\trouterrpc\x1a\x0flightning.proto\"\xb7\x05\n\x12SendPaymentRequest\x12\x0c\n\x04\x64\x65st\x18\x01 \x01(\x0c\x12\x0b\n\x03\x61mt\x18\x02 \x01(\x03\x12\x14\n\x0cpayment_hash\x18\x03 \x01(\x0c\x12\x18\n\x10\x66inal_cltv_delta\x18\x04 \x01(\x05\x12\x17\n\x0fpayment_request\x18\x05 \x01(\t\x12\x17\n\x0ftimeout_seconds\x18\x06 \x01(\x05\x12\x15\n\rfee_limit_sat\x18\x07 \x01(\x03\x12\x1e\n\x10outgoing_chan_id\x18\x08 \x01(\x04\x42\x04\x18\x01\x30\x01\x12\x12\n\ncltv_limit\x18\t \x01(\x05\x12%\n\x0broute_hints\x18\n \x03(\x0b\x32\x10.lnrpc.RouteHint\x12Q\n\x13\x64\x65st_custom_records\x18\x0b \x03(\x0b\x32\x34.routerrpc.SendPaymentRequest.DestCustomRecordsEntry\x12\x10\n\x08\x61mt_msat\x18\x0c \x01(\x03\x12\x16\n\x0e\x66\x65\x65_limit_msat\x18\r \x01(\x03\x12\x17\n\x0flast_hop_pubkey\x18\x0e \x01(\x0c\x12\x1a\n\x12\x61llow_self_payment\x18\x0f \x01(\x08\x12(\n\rdest_features\x18\x10 \x03(\x0e\x32\x11.lnrpc.FeatureBit\x12\x11\n\tmax_parts\x18\x11 \x01(\r\x12\x1b\n\x13no_inflight_updates\x18\x12 \x01(\x08\x12\x19\n\x11outgoing_chan_ids\x18\x13 \x03(\x04\x12\x14\n\x0cpayment_addr\x18\x14 \x01(\x0c\x12\x1b\n\x13max_shard_size_msat\x18\x15 \x01(\x04\x12\x0b\n\x03\x61mp\x18\x16 \x01(\x08\x12\x11\n\ttime_pref\x18\x17 \x01(\x01\x1a\x38\n\x16\x44\x65stCustomRecordsEntry\x12\x0b\n\x03key\x18\x01 \x01(\x04\x12\r\n\x05value\x18\x02 \x01(\x0c:\x02\x38\x01\"H\n\x13TrackPaymentRequest\x12\x14\n\x0cpayment_hash\x18\x01 \x01(\x0c\x12\x1b\n\x13no_inflight_updates\x18\x02 \x01(\x08\"3\n\x14TrackPaymentsRequest\x12\x1b\n\x13no_inflight_updates\x18\x01 \x01(\x08\"Z\n\x0fRouteFeeRequest\x12\x0c\n\x04\x64\x65st\x18\x01 \x01(\x0c\x12\x0f\n\x07\x61mt_sat\x18\x02 \x01(\x03\x12\x17\n\x0fpayment_request\x18\x03 \x01(\t\x12\x0f\n\x07timeout\x18\x04 \x01(\r\"z\n\x10RouteFeeResponse\x12\x18\n\x10routing_fee_msat\x18\x01 \x01(\x03\x12\x17\n\x0ftime_lock_delay\x18\x02 \x01(\x03\x12\x33\n\x0e\x66\x61ilure_reason\x18\x05 \x01(\x0e\x32\x1b.lnrpc.PaymentFailureReason\"^\n\x12SendToRouteRequest\x12\x14\n\x0cpayment_hash\x18\x01 \x01(\x0c\x12\x1b\n\x05route\x18\x02 \x01(\x0b\x32\x0c.lnrpc.Route\x12\x15\n\rskip_temp_err\x18\x03 \x01(\x08\"H\n\x13SendToRouteResponse\x12\x10\n\x08preimage\x18\x01 \x01(\x0c\x12\x1f\n\x07\x66\x61ilure\x18\x02 \x01(\x0b\x32\x0e.lnrpc.Failure\"\x1c\n\x1aResetMissionControlRequest\"\x1d\n\x1bResetMissionControlResponse\"\x1c\n\x1aQueryMissionControlRequest\"J\n\x1bQueryMissionControlResponse\x12%\n\x05pairs\x18\x02 \x03(\x0b\x32\x16.routerrpc.PairHistoryJ\x04\x08\x01\x10\x02\"T\n\x1cXImportMissionControlRequest\x12%\n\x05pairs\x18\x01 \x03(\x0b\x32\x16.routerrpc.PairHistory\x12\r\n\x05\x66orce\x18\x02 \x01(\x08\"\x1f\n\x1dXImportMissionControlResponse\"o\n\x0bPairHistory\x12\x11\n\tnode_from\x18\x01 \x01(\x0c\x12\x0f\n\x07node_to\x18\x02 \x01(\x0c\x12$\n\x07history\x18\x07 \x01(\x0b\x32\x13.routerrpc.PairDataJ\x04\x08\x03\x10\x04J\x04\x08\x04\x10\x05J\x04\x08\x05\x10\x06J\x04\x08\x06\x10\x07\"\x99\x01\n\x08PairData\x12\x11\n\tfail_time\x18\x01 \x01(\x03\x12\x14\n\x0c\x66\x61il_amt_sat\x18\x02 \x01(\x03\x12\x15\n\rfail_amt_msat\x18\x04 \x01(\x03\x12\x14\n\x0csuccess_time\x18\x05 \x01(\x03\x12\x17\n\x0fsuccess_amt_sat\x18\x06 \x01(\x03\x12\x18\n\x10success_amt_msat\x18\x07 \x01(\x03J\x04\x08\x03\x10\x04\" \n\x1eGetMissionControlConfigRequest\"R\n\x1fGetMissionControlConfigResponse\x12/\n\x06\x63onfig\x18\x01 \x01(\x0b\x32\x1f.routerrpc.MissionControlConfig\"Q\n\x1eSetMissionControlConfigRequest\x12/\n\x06\x63onfig\x18\x01 \x01(\x0b\x32\x1f.routerrpc.MissionControlConfig\"!\n\x1fSetMissionControlConfigResponse\"\x93\x03\n\x14MissionControlConfig\x12\x1d\n\x11half_life_seconds\x18\x01 \x01(\x04\x42\x02\x18\x01\x12\x1b\n\x0fhop_probability\x18\x02 \x01(\x02\x42\x02\x18\x01\x12\x12\n\x06weight\x18\x03 \x01(\x02\x42\x02\x18\x01\x12\x1f\n\x17maximum_payment_results\x18\x04 \x01(\r\x12&\n\x1eminimum_failure_relax_interval\x18\x05 \x01(\x04\x12?\n\x05model\x18\x06 \x01(\x0e\x32\x30.routerrpc.MissionControlConfig.ProbabilityModel\x12/\n\x07\x61priori\x18\x07 \x01(\x0b\x32\x1c.routerrpc.AprioriParametersH\x00\x12/\n\x07\x62imodal\x18\x08 \x01(\x0b\x32\x1c.routerrpc.BimodalParametersH\x00\",\n\x10ProbabilityModel\x12\x0b\n\x07\x41PRIORI\x10\x00\x12\x0b\n\x07\x42IMODAL\x10\x01\x42\x11\n\x0f\x45stimatorConfig\"P\n\x11\x42imodalParameters\x12\x13\n\x0bnode_weight\x18\x01 \x01(\x01\x12\x12\n\nscale_msat\x18\x02 \x01(\x04\x12\x12\n\ndecay_time\x18\x03 \x01(\x04\"r\n\x11\x41prioriParameters\x12\x19\n\x11half_life_seconds\x18\x01 \x01(\x04\x12\x17\n\x0fhop_probability\x18\x02 \x01(\x01\x12\x0e\n\x06weight\x18\x03 \x01(\x01\x12\x19\n\x11\x63\x61pacity_fraction\x18\x04 \x01(\x01\"O\n\x17QueryProbabilityRequest\x12\x11\n\tfrom_node\x18\x01 \x01(\x0c\x12\x0f\n\x07to_node\x18\x02 \x01(\x0c\x12\x10\n\x08\x61mt_msat\x18\x03 \x01(\x03\"U\n\x18QueryProbabilityResponse\x12\x13\n\x0bprobability\x18\x01 \x01(\x01\x12$\n\x07history\x18\x02 \x01(\x0b\x32\x13.routerrpc.PairData\"\x88\x01\n\x11\x42uildRouteRequest\x12\x10\n\x08\x61mt_msat\x18\x01 \x01(\x03\x12\x18\n\x10\x66inal_cltv_delta\x18\x02 \x01(\x05\x12\x1c\n\x10outgoing_chan_id\x18\x03 \x01(\x04\x42\x02\x30\x01\x12\x13\n\x0bhop_pubkeys\x18\x04 \x03(\x0c\x12\x14\n\x0cpayment_addr\x18\x05 \x01(\x0c\"1\n\x12\x42uildRouteResponse\x12\x1b\n\x05route\x18\x01 \x01(\x0b\x32\x0c.lnrpc.Route\"\x1c\n\x1aSubscribeHtlcEventsRequest\"\xcb\x04\n\tHtlcEvent\x12\x1b\n\x13incoming_channel_id\x18\x01 \x01(\x04\x12\x1b\n\x13outgoing_channel_id\x18\x02 \x01(\x04\x12\x18\n\x10incoming_htlc_id\x18\x03 \x01(\x04\x12\x18\n\x10outgoing_htlc_id\x18\x04 \x01(\x04\x12\x14\n\x0ctimestamp_ns\x18\x05 \x01(\x04\x12\x32\n\nevent_type\x18\x06 \x01(\x0e\x32\x1e.routerrpc.HtlcEvent.EventType\x12\x30\n\rforward_event\x18\x07 \x01(\x0b\x32\x17.routerrpc.ForwardEventH\x00\x12\x39\n\x12\x66orward_fail_event\x18\x08 \x01(\x0b\x32\x1b.routerrpc.ForwardFailEventH\x00\x12.\n\x0csettle_event\x18\t \x01(\x0b\x32\x16.routerrpc.SettleEventH\x00\x12\x33\n\x0flink_fail_event\x18\n \x01(\x0b\x32\x18.routerrpc.LinkFailEventH\x00\x12\x36\n\x10subscribed_event\x18\x0b \x01(\x0b\x32\x1a.routerrpc.SubscribedEventH\x00\x12\x35\n\x10\x66inal_htlc_event\x18\x0c \x01(\x0b\x32\x19.routerrpc.FinalHtlcEventH\x00\"<\n\tEventType\x12\x0b\n\x07UNKNOWN\x10\x00\x12\x08\n\x04SEND\x10\x01\x12\x0b\n\x07RECEIVE\x10\x02\x12\x0b\n\x07\x46ORWARD\x10\x03\x42\x07\n\x05\x65vent\"v\n\x08HtlcInfo\x12\x19\n\x11incoming_timelock\x18\x01 \x01(\r\x12\x19\n\x11outgoing_timelock\x18\x02 \x01(\r\x12\x19\n\x11incoming_amt_msat\x18\x03 \x01(\x04\x12\x19\n\x11outgoing_amt_msat\x18\x04 \x01(\x04\"1\n\x0c\x46orwardEvent\x12!\n\x04info\x18\x01 \x01(\x0b\x32\x13.routerrpc.HtlcInfo\"\x12\n\x10\x46orwardFailEvent\"\x1f\n\x0bSettleEvent\x12\x10\n\x08preimage\x18\x01 \x01(\x0c\"3\n\x0e\x46inalHtlcEvent\x12\x0f\n\x07settled\x18\x01 \x01(\x08\x12\x10\n\x08offchain\x18\x02 \x01(\x08\"\x11\n\x0fSubscribedEvent\"\xae\x01\n\rLinkFailEvent\x12!\n\x04info\x18\x01 \x01(\x0b\x32\x13.routerrpc.HtlcInfo\x12\x30\n\x0cwire_failure\x18\x02 \x01(\x0e\x32\x1a.lnrpc.Failure.FailureCode\x12\x30\n\x0e\x66\x61ilure_detail\x18\x03 \x01(\x0e\x32\x18.routerrpc.FailureDetail\x12\x16\n\x0e\x66\x61ilure_string\x18\x04 \x01(\t\"r\n\rPaymentStatus\x12&\n\x05state\x18\x01 \x01(\x0e\x32\x17.routerrpc.PaymentState\x12\x10\n\x08preimage\x18\x02 \x01(\x0c\x12!\n\x05htlcs\x18\x04 \x03(\x0b\x32\x12.lnrpc.HTLCAttemptJ\x04\x08\x03\x10\x04\".\n\nCircuitKey\x12\x0f\n\x07\x63han_id\x18\x01 \x01(\x04\x12\x0f\n\x07htlc_id\x18\x02 \x01(\x04\"\xb1\x03\n\x1b\x46orwardHtlcInterceptRequest\x12\x33\n\x14incoming_circuit_key\x18\x01 \x01(\x0b\x32\x15.routerrpc.CircuitKey\x12\x1c\n\x14incoming_amount_msat\x18\x05 \x01(\x04\x12\x17\n\x0fincoming_expiry\x18\x06 \x01(\r\x12\x14\n\x0cpayment_hash\x18\x02 \x01(\x0c\x12\"\n\x1aoutgoing_requested_chan_id\x18\x07 \x01(\x04\x12\x1c\n\x14outgoing_amount_msat\x18\x03 \x01(\x04\x12\x17\n\x0foutgoing_expiry\x18\x04 \x01(\r\x12Q\n\x0e\x63ustom_records\x18\x08 \x03(\x0b\x32\x39.routerrpc.ForwardHtlcInterceptRequest.CustomRecordsEntry\x12\x12\n\nonion_blob\x18\t \x01(\x0c\x12\x18\n\x10\x61uto_fail_height\x18\n \x01(\x05\x1a\x34\n\x12\x43ustomRecordsEntry\x12\x0b\n\x03key\x18\x01 \x01(\x04\x12\r\n\x05value\x18\x02 \x01(\x0c:\x02\x38\x01\"\xe5\x01\n\x1c\x46orwardHtlcInterceptResponse\x12\x33\n\x14incoming_circuit_key\x18\x01 \x01(\x0b\x32\x15.routerrpc.CircuitKey\x12\x33\n\x06\x61\x63tion\x18\x02 \x01(\x0e\x32#.routerrpc.ResolveHoldForwardAction\x12\x10\n\x08preimage\x18\x03 \x01(\x0c\x12\x17\n\x0f\x66\x61ilure_message\x18\x04 \x01(\x0c\x12\x30\n\x0c\x66\x61ilure_code\x18\x05 \x01(\x0e\x32\x1a.lnrpc.Failure.FailureCode\"o\n\x17UpdateChanStatusRequest\x12\'\n\nchan_point\x18\x01 \x01(\x0b\x32\x13.lnrpc.ChannelPoint\x12+\n\x06\x61\x63tion\x18\x02 \x01(\x0e\x32\x1b.routerrpc.ChanStatusAction\"\x1a\n\x18UpdateChanStatusResponse*\x81\x04\n\rFailureDetail\x12\x0b\n\x07UNKNOWN\x10\x00\x12\r\n\tNO_DETAIL\x10\x01\x12\x10\n\x0cONION_DECODE\x10\x02\x12\x15\n\x11LINK_NOT_ELIGIBLE\x10\x03\x12\x14\n\x10ON_CHAIN_TIMEOUT\x10\x04\x12\x14\n\x10HTLC_EXCEEDS_MAX\x10\x05\x12\x18\n\x14INSUFFICIENT_BALANCE\x10\x06\x12\x16\n\x12INCOMPLETE_FORWARD\x10\x07\x12\x13\n\x0fHTLC_ADD_FAILED\x10\x08\x12\x15\n\x11\x46ORWARDS_DISABLED\x10\t\x12\x14\n\x10INVOICE_CANCELED\x10\n\x12\x15\n\x11INVOICE_UNDERPAID\x10\x0b\x12\x1b\n\x17INVOICE_EXPIRY_TOO_SOON\x10\x0c\x12\x14\n\x10INVOICE_NOT_OPEN\x10\r\x12\x17\n\x13MPP_INVOICE_TIMEOUT\x10\x0e\x12\x14\n\x10\x41\x44\x44RESS_MISMATCH\x10\x0f\x12\x16\n\x12SET_TOTAL_MISMATCH\x10\x10\x12\x15\n\x11SET_TOTAL_TOO_LOW\x10\x11\x12\x10\n\x0cSET_OVERPAID\x10\x12\x12\x13\n\x0fUNKNOWN_INVOICE\x10\x13\x12\x13\n\x0fINVALID_KEYSEND\x10\x14\x12\x13\n\x0fMPP_IN_PROGRESS\x10\x15\x12\x12\n\x0e\x43IRCULAR_ROUTE\x10\x16*\xae\x01\n\x0cPaymentState\x12\r\n\tIN_FLIGHT\x10\x00\x12\r\n\tSUCCEEDED\x10\x01\x12\x12\n\x0e\x46\x41ILED_TIMEOUT\x10\x02\x12\x13\n\x0f\x46\x41ILED_NO_ROUTE\x10\x03\x12\x10\n\x0c\x46\x41ILED_ERROR\x10\x04\x12$\n FAILED_INCORRECT_PAYMENT_DETAILS\x10\x05\x12\x1f\n\x1b\x46\x41ILED_INSUFFICIENT_BALANCE\x10\x06*<\n\x18ResolveHoldForwardAction\x12\n\n\x06SETTLE\x10\x00\x12\x08\n\x04\x46\x41IL\x10\x01\x12\n\n\x06RESUME\x10\x02*5\n\x10\x43hanStatusAction\x12\n\n\x06\x45NABLE\x10\x00\x12\x0b\n\x07\x44ISABLE\x10\x01\x12\x08\n\x04\x41UTO\x10\x02\x32\xb5\x0c\n\x06Router\x12@\n\rSendPaymentV2\x12\x1d.routerrpc.SendPaymentRequest\x1a\x0e.lnrpc.Payment0\x01\x12\x42\n\x0eTrackPaymentV2\x12\x1e.routerrpc.TrackPaymentRequest\x1a\x0e.lnrpc.Payment0\x01\x12\x42\n\rTrackPayments\x12\x1f.routerrpc.TrackPaymentsRequest\x1a\x0e.lnrpc.Payment0\x01\x12K\n\x10\x45stimateRouteFee\x12\x1a.routerrpc.RouteFeeRequest\x1a\x1b.routerrpc.RouteFeeResponse\x12Q\n\x0bSendToRoute\x12\x1d.routerrpc.SendToRouteRequest\x1a\x1e.routerrpc.SendToRouteResponse\"\x03\x88\x02\x01\x12\x42\n\rSendToRouteV2\x12\x1d.routerrpc.SendToRouteRequest\x1a\x12.lnrpc.HTLCAttempt\x12\x64\n\x13ResetMissionControl\x12%.routerrpc.ResetMissionControlRequest\x1a&.routerrpc.ResetMissionControlResponse\x12\x64\n\x13QueryMissionControl\x12%.routerrpc.QueryMissionControlRequest\x1a&.routerrpc.QueryMissionControlResponse\x12j\n\x15XImportMissionControl\x12\'.routerrpc.XImportMissionControlRequest\x1a(.routerrpc.XImportMissionControlResponse\x12p\n\x17GetMissionControlConfig\x12).routerrpc.GetMissionControlConfigRequest\x1a*.routerrpc.GetMissionControlConfigResponse\x12p\n\x17SetMissionControlConfig\x12).routerrpc.SetMissionControlConfigRequest\x1a*.routerrpc.SetMissionControlConfigResponse\x12[\n\x10QueryProbability\x12\".routerrpc.QueryProbabilityRequest\x1a#.routerrpc.QueryProbabilityResponse\x12I\n\nBuildRoute\x12\x1c.routerrpc.BuildRouteRequest\x1a\x1d.routerrpc.BuildRouteResponse\x12T\n\x13SubscribeHtlcEvents\x12%.routerrpc.SubscribeHtlcEventsRequest\x1a\x14.routerrpc.HtlcEvent0\x01\x12M\n\x0bSendPayment\x12\x1d.routerrpc.SendPaymentRequest\x1a\x18.routerrpc.PaymentStatus\"\x03\x88\x02\x01\x30\x01\x12O\n\x0cTrackPayment\x12\x1e.routerrpc.TrackPaymentRequest\x1a\x18.routerrpc.PaymentStatus\"\x03\x88\x02\x01\x30\x01\x12\x66\n\x0fHtlcInterceptor\x12\'.routerrpc.ForwardHtlcInterceptResponse\x1a&.routerrpc.ForwardHtlcInterceptRequest(\x01\x30\x01\x12[\n\x10UpdateChanStatus\x12\".routerrpc.UpdateChanStatusRequest\x1a#.routerrpc.UpdateChanStatusResponseB1Z/github.com/lightningnetwork/lnd/lnrpc/routerrpcb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'router_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'Z/github.com/lightningnetwork/lnd/lnrpc/routerrpc'
  _globals['_SENDPAYMENTREQUEST_DESTCUSTOMRECORDSENTRY']._loaded_options = None
  _globals['_SENDPAYMENTREQUEST_DESTCUSTOMRECORDSENTRY']._serialized_options = b'8\001'
  _globals['_SENDPAYMENTREQUEST'].fields_by_name['outgoing_chan_id']._loaded_options = None
  _globals['_SENDPAYMENTREQUEST'].fields_by_name['outgoing_chan_id']._serialized_options = b'\030\0010\001'
  _globals['_MISSIONCONTROLCONFIG'].fields_by_name['half_life_seconds']._loaded_options = None
  _globals['_MISSIONCONTROLCONFIG'].fields_by_name['half_life_seconds']._serialized_options = b'\030\001'
  _globals['_MISSIONCONTROLCONFIG'].fields_by_name['hop_probability']._loaded_options = None
  _globals['_MISSIONCONTROLCONFIG'].fields_by_name['hop_probability']._serialized_options = b'\030\001'
  _globals['_MISSIONCONTROLCONFIG'].fields_by_name['weight']._loaded_options = None
  _globals['_MISSIONCONTROLCONFIG'].fields_by_name['weight']._serialized_options = b'\030\001'
  _globals['_BUILDROUTEREQUEST'].fields_by_name['outgoing_chan_id']._loaded_options = None
  _globals['_BUILDROUTEREQUEST'].fields_by_name['outgoing_chan_id']._serialized_options = b'0\001'
  _globals['_FORWARDHTLCINTERCEPTREQUEST_CUSTOMRECORDSENTRY']._loaded_options = None
  _globals['_FORWARDHTLCINTERCEPTREQUEST_CUSTOMRECORDSENTRY']._serialized_options = b'8\001'
  _globals['_ROUTER'].methods_by_name['SendToRoute']._loaded_options = None
  _globals['_ROUTER'].methods_by_name['SendToRoute']._serialized_options = b'\210\002\001'
  _globals['_ROUTER'].methods_by_name['SendPayment']._loaded_options = None
  _globals['_ROUTER'].methods_by_name['SendPayment']._serialized_options = b'\210\002\001'
  _globals['_ROUTER'].methods_by_name['TrackPayment']._loaded_options = None
  _globals['_ROUTER'].methods_by_name['TrackPayment']._serialized_options = b'\210\002\001'
  _globals['_FAILUREDETAIL']._serialized_start=5075
  _globals['_FAILUREDETAIL']._serialized_end=5588
  _globals['_PAYMENTSTATE']._serialized_start=5591
  _globals['_PAYMENTSTATE']._serialized_end=5765
  _globals['_RESOLVEHOLDFORWARDACTION']._serialized_start=5767
  _globals['_RESOLVEHOLDFORWARDACTION']._serialized_end=5827
  _globals['_CHANSTATUSACTION']._serialized_start=5829
  _globals['_CHANSTATUSACTION']._serialized_end=5882
  _globals['_SENDPAYMENTREQUEST']._serialized_start=45
  _globals['_SENDPAYMENTREQUEST']._serialized_end=740
  _globals['_SENDPAYMENTREQUEST_DESTCUSTOMRECORDSENTRY']._serialized_start=684
  _globals['_SENDPAYMENTREQUEST_DESTCUSTOMRECORDSENTRY']._serialized_end=740
  _globals['_TRACKPAYMENTREQUEST']._serialized_start=742
  _globals['_TRACKPAYMENTREQUEST']._serialized_end=814
  _globals['_TRACKPAYMENTSREQUEST']._serialized_start=816
  _globals['_TRACKPAYMENTSREQUEST']._serialized_end=867
  _globals['_ROUTEFEEREQUEST']._serialized_start=869
  _globals['_ROUTEFEEREQUEST']._serialized_end=959
  _globals['_ROUTEFEERESPONSE']._serialized_start=961
  _globals['_ROUTEFEERESPONSE']._serialized_end=1083
  _globals['_SENDTOROUTEREQUEST']._serialized_start=1085
  _globals['_SENDTOROUTEREQUEST']._serialized_end=1179
  _globals['_SENDTOROUTERESPONSE']._serialized_start=1181
  _globals['_SENDTOROUTERESPONSE']._serialized_end=1253
  _globals['_RESETMISSIONCONTROLREQUEST']._serialized_start=1255
  _globals['_RESETMISSIONCONTROLREQUEST']._serialized_end=1283
  _globals['_RESETMISSIONCONTROLRESPONSE']._serialized_start=1285
  _globals['_RESETMISSIONCONTROLRESPONSE']._serialized_end=1314
  _globals['_QUERYMISSIONCONTROLREQUEST']._serialized_start=1316
  _globals['_QUERYMISSIONCONTROLREQUEST']._serialized_end=1344
  _globals['_QUERYMISSIONCONTROLRESPONSE']._serialized_start=1346
  _globals['_QUERYMISSIONCONTROLRESPONSE']._serialized_end=1420
  _globals['_XIMPORTMISSIONCONTROLREQUEST']._serialized_start=1422
  _globals['_XIMPORTMISSIONCONTROLREQUEST']._serialized_end=1506
  _globals['_XIMPORTMISSIONCONTROLRESPONSE']._serialized_start=1508
  _globals['_XIMPORTMISSIONCONTROLRESPONSE']._serialized_end=1539
  _globals['_PAIRHISTORY']._serialized_start=1541
  _globals['_PAIRHISTORY']._serialized_end=1652
  _globals['_PAIRDATA']._serialized_start=1655
  _globals['_PAIRDATA']._serialized_end=1808
  _globals['_GETMISSIONCONTROLCONFIGREQUEST']._serialized_start=1810
  _globals['_GETMISSIONCONTROLCONFIGREQUEST']._serialized_end=1842
  _globals['_GETMISSIONCONTROLCONFIGRESPONSE']._serialized_start=1844
  _globals['_GETMISSIONCONTROLCONFIGRESPONSE']._serialized_end=1926
  _globals['_SETMISSIONCONTROLCONFIGREQUEST']._serialized_start=1928
  _globals['_SETMISSIONCONTROLCONFIGREQUEST']._serialized_end=2009
  _globals['_SETMISSIONCONTROLCONFIGRESPONSE']._serialized_start=2011
  _globals['_SETMISSIONCONTROLCONFIGRESPONSE']._serialized_end=2044
  _globals['_MISSIONCONTROLCONFIG']._serialized_start=2047
  _globals['_MISSIONCONTROLCONFIG']._serialized_end=2450
  _globals['_MISSIONCONTROLCONFIG_PROBABILITYMODEL']._serialized_start=2387
  _globals['_MISSIONCONTROLCONFIG_PROBABILITYMODEL']._serialized_end=2431
  _globals['_BIMODALPARAMETERS']._serialized_start=2452
  _globals['_BIMODALPARAMETERS']._serialized_end=2532
  _globals['_APRIORIPARAMETERS']._serialized_start=2534
  _globals['_APRIORIPARAMETERS']._serialized_end=2648
  _globals['_QUERYPROBABILITYREQUEST']._serialized_start=2650
  _globals['_QUERYPROBABILITYREQUEST']._serialized_end=2729
  _globals['_QUERYPROBABILITYRESPONSE']._serialized_start=2731
  _globals['_QUERYPROBABILITYRESPONSE']._serialized_end=2816
  _globals['_BUILDROUTEREQUEST']._serialized_start=2819
  _globals['_BUILDROUTEREQUEST']._serialized_end=2955
  _globals['_BUILDROUTERESPONSE']._serialized_start=2957
  _globals['_BUILDROUTERESPONSE']._serialized_end=3006
  _globals['_SUBSCRIBEHTLCEVENTSREQUEST']._serialized_start=3008
  _globals['_SUBSCRIBEHTLCEVENTSREQUEST']._serialized_end=3036
  _globals['_HTLCEVENT']._serialized_start=3039
  _globals['_HTLCEVENT']._serialized_end=3626
  _globals['_HTLCEVENT_EVENTTYPE']._serialized_start=3557
  _globals['_HTLCEVENT_EVENTTYPE']._serialized_end=3617
  _globals['_HTLCINFO']._serialized_start=3628
  _globals['_HTLCINFO']._serialized_end=3746
  _globals['_FORWARDEVENT']._serialized_start=3748
  _globals['_FORWARDEVENT']._serialized_end=3797
  _globals['_FORWARDFAILEVENT']._serialized_start=3799
  _globals['_FORWARDFAILEVENT']._serialized_end=3817
  _globals['_SETTLEEVENT']._serialized_start=3819
  _globals['_SETTLEEVENT']._serialized_end=3850
  _globals['_FINALHTLCEVENT']._serialized_start=3852
  _globals['_FINALHTLCEVENT']._serialized_end=3903
  _globals['_SUBSCRIBEDEVENT']._serialized_start=3905
  _globals['_SUBSCRIBEDEVENT']._serialized_end=3922
  _globals['_LINKFAILEVENT']._serialized_start=3925
  _globals['_LINKFAILEVENT']._serialized_end=4099
  _globals['_PAYMENTSTATUS']._serialized_start=4101
  _globals['_PAYMENTSTATUS']._serialized_end=4215
  _globals['_CIRCUITKEY']._serialized_start=4217
  _globals['_CIRCUITKEY']._serialized_end=4263
  _globals['_FORWARDHTLCINTERCEPTREQUEST']._serialized_start=4266
  _globals['_FORWARDHTLCINTERCEPTREQUEST']._serialized_end=4699
  _globals['_FORWARDHTLCINTERCEPTREQUEST_CUSTOMRECORDSENTRY']._serialized_start=4647
  _globals['_FORWARDHTLCINTERCEPTREQUEST_CUSTOMRECORDSENTRY']._serialized_end=4699
  _globals['_FORWARDHTLCINTERCEPTRESPONSE']._serialized_start=4702
  _globals['_FORWARDHTLCINTERCEPTRESPONSE']._serialized_end=4931
  _globals['_UPDATECHANSTATUSREQUEST']._serialized_start=4933
  _globals['_UPDATECHANSTATUSREQUEST']._serialized_end=5044
  _globals['_UPDATECHANSTATUSRESPONSE']._serialized_start=5046
  _globals['_UPDATECHANSTATUSRESPONSE']._serialized_end=5072
  _globals['_ROUTER']._serialized_start=5885
  _globals['_ROUTER']._serialized_end=7474
# @@protoc_insertion_point(module_scope)
