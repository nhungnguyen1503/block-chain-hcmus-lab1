# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: pbft.proto
# Protobuf Python Version: 5.28.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    28,
    1,
    '',
    'pbft.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\npbft.proto\x12\x04pbft\"K\n\x05\x42lock\x12\x1a\n\x12previous_blockhash\x18\x01 \x01(\t\x12\x11\n\tblockhash\x18\x02 \x01(\t\x12\x13\n\x0b\x62lockheight\x18\x03 \x01(\x05\"^\n\x0bPBFTMessage\x12\x11\n\tsender_id\x18\x01 \x01(\t\x12\x1a\n\x05\x62lock\x18\x02 \x01(\x0b\x32\x0b.pbft.Block\x12\r\n\x05phase\x18\x03 \x01(\t\x12\x11\n\tsignature\x18\x04 \x01(\x0c\"9\n\x10PublicKeyMessage\x12\x11\n\tsender_id\x18\x01 \x01(\t\x12\x12\n\npublic_key\x18\x02 \x01(\x0c\"\x07\n\x05\x45mpty\"2\n\x11ViewChangeMessage\x12\x0c\n\x04view\x18\x01 \x01(\x05\x12\x0f\n\x07node_id\x18\x02 \x01(\t\"/\n\x0eNewViewMessage\x12\x0c\n\x04view\x18\x01 \x01(\x05\x12\x0f\n\x07node_id\x18\x02 \x01(\t2\xac\x02\n\x0bPBFTService\x12,\n\nPrePrepare\x12\x11.pbft.PBFTMessage\x1a\x0b.pbft.Empty\x12)\n\x07Prepare\x12\x11.pbft.PBFTMessage\x1a\x0b.pbft.Empty\x12(\n\x06\x43ommit\x12\x11.pbft.PBFTMessage\x1a\x0b.pbft.Empty\x12\x32\n\nViewChange\x12\x17.pbft.ViewChangeMessage\x1a\x0b.pbft.Empty\x12,\n\x07NewView\x12\x14.pbft.NewViewMessage\x1a\x0b.pbft.Empty\x12\x38\n\x11\x45xchangePublicKey\x12\x16.pbft.PublicKeyMessage\x1a\x0b.pbft.Emptyb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'pbft_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_BLOCK']._serialized_start=20
  _globals['_BLOCK']._serialized_end=95
  _globals['_PBFTMESSAGE']._serialized_start=97
  _globals['_PBFTMESSAGE']._serialized_end=191
  _globals['_PUBLICKEYMESSAGE']._serialized_start=193
  _globals['_PUBLICKEYMESSAGE']._serialized_end=250
  _globals['_EMPTY']._serialized_start=252
  _globals['_EMPTY']._serialized_end=259
  _globals['_VIEWCHANGEMESSAGE']._serialized_start=261
  _globals['_VIEWCHANGEMESSAGE']._serialized_end=311
  _globals['_NEWVIEWMESSAGE']._serialized_start=313
  _globals['_NEWVIEWMESSAGE']._serialized_end=360
  _globals['_PBFTSERVICE']._serialized_start=363
  _globals['_PBFTSERVICE']._serialized_end=663
# @@protoc_insertion_point(module_scope)
