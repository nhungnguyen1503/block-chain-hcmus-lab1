import grpc
from concurrent import futures
import time
import p2p_pb2
import p2p_pb2_grpc

# Lớp PeerService để nhận và xử lý tin nhắn
class PeerService(p2p_pb2_grpc.PeerServiceServicer):
    def __init__(self, peer_name):
        self.peer_name = peer_name

    def SendMessage(self, request, context):
        print(f"[{self.peer_name}] Received message from {request.sender}: {request.content}")
        return p2p_pb2.Response(status="Message received")

# Hàm chạy server gRPC
def run_server(peer_name, port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    p2p_pb2_grpc.add_PeerServiceServicer_to_server(PeerService(peer_name), server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"[{peer_name}] Server started at port {port}")
    return server

# Hàm gửi tin nhắn đến peer khác
def send_message(target_host, target_port, sender_name, content):
    channel = grpc.insecure_channel(f"{target_host}:{target_port}")
    stub = p2p_pb2_grpc.PeerServiceStub(channel)
    message = p2p_pb2.Message(sender=sender_name, content=content)
    response = stub.SendMessage(message)
    print(f"[{sender_name}] Received response: {response.status}")

# Chạy peer
def run_peer(peer_name, port, peers):
    server = run_server(peer_name, port)

    try:
        time.sleep(1)  # Đợi server khởi động
        for peer in peers:
            target_host, target_port = peer
            send_message(target_host, target_port, peer_name, f"Hello from {peer_name}")
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print(f"[{peer_name}] Shutting down...")
        server.stop(0)
