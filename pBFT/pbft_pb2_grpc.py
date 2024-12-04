# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

import pbft_pb2 as pbft__pb2

GRPC_GENERATED_VERSION = '1.68.0'
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in pbft_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class PBFTServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.PrePrepare = channel.unary_unary(
                '/pbft.PBFTService/PrePrepare',
                request_serializer=pbft__pb2.PBFTMessage.SerializeToString,
                response_deserializer=pbft__pb2.Empty.FromString,
                _registered_method=True)
        self.Prepare = channel.unary_unary(
                '/pbft.PBFTService/Prepare',
                request_serializer=pbft__pb2.PBFTMessage.SerializeToString,
                response_deserializer=pbft__pb2.Empty.FromString,
                _registered_method=True)
        self.Commit = channel.unary_unary(
                '/pbft.PBFTService/Commit',
                request_serializer=pbft__pb2.PBFTMessage.SerializeToString,
                response_deserializer=pbft__pb2.Empty.FromString,
                _registered_method=True)


class PBFTServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def PrePrepare(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Prepare(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Commit(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_PBFTServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'PrePrepare': grpc.unary_unary_rpc_method_handler(
                    servicer.PrePrepare,
                    request_deserializer=pbft__pb2.PBFTMessage.FromString,
                    response_serializer=pbft__pb2.Empty.SerializeToString,
            ),
            'Prepare': grpc.unary_unary_rpc_method_handler(
                    servicer.Prepare,
                    request_deserializer=pbft__pb2.PBFTMessage.FromString,
                    response_serializer=pbft__pb2.Empty.SerializeToString,
            ),
            'Commit': grpc.unary_unary_rpc_method_handler(
                    servicer.Commit,
                    request_deserializer=pbft__pb2.PBFTMessage.FromString,
                    response_serializer=pbft__pb2.Empty.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'pbft.PBFTService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('pbft.PBFTService', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class PBFTService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def PrePrepare(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/pbft.PBFTService/PrePrepare',
            pbft__pb2.PBFTMessage.SerializeToString,
            pbft__pb2.Empty.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def Prepare(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/pbft.PBFTService/Prepare',
            pbft__pb2.PBFTMessage.SerializeToString,
            pbft__pb2.Empty.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def Commit(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/pbft.PBFTService/Commit',
            pbft__pb2.PBFTMessage.SerializeToString,
            pbft__pb2.Empty.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)
