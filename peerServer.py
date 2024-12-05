import grpc
from concurrent import futures
import peer_pb2
import peer_pb2_grpc

class PeerServer(peer_pb2_grpc.PeerServicer):
    def __init__(self, port):
        self.peers = []  # Danh sách các peers
        self.port = port

    def SendMessage(self, request, context):
        print(f"[{self.port}] Received message from {request.sender}: {request.content}")
        return peer_pb2.Response(status="Message received")

    def GetPeers(self, request, context):
        peer_list = peer_pb2.PeerList(peers=self.peers)
        return peer_list

    def add_peer(self, address):
        if address not in [peer.address for peer in self.peers]:
            self.peers.append(peer_pb2.PeerInfo(address=address))

def serve(port, peer_addresses):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    peer_server = PeerServer(port)
    
    # Kết nối với các peers đã biết
    for address in peer_addresses:
        peer_server.add_peer(address)
    
    peer_pb2_grpc.add_PeerServicer_to_server(peer_server, server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"[{port}] Server started")
    server.wait_for_termination()
