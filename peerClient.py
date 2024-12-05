import grpc
import peer_pb2
import peer_pb2_grpc

def send_message(target, sender, content):
    with grpc.insecure_channel(target) as channel:
        stub = peer_pb2_grpc.PeerStub(channel)
        message = peer_pb2.Message(sender=sender, content=content)
        response = stub.SendMessage(message)
        print(f"Response from {target}: {response.status}")

def get_peers(target):
    with grpc.insecure_channel(target) as channel:
        stub = peer_pb2_grpc.PeerStub(channel)
        peer_list = stub.GetPeers(peer_pb2.Empty())
        return [peer.address for peer in peer_list.peers]
