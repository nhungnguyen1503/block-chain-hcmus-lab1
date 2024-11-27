import grpc
from concurrent import futures
import time
import p2p_pb2
import p2p_pb2_grpc
from block import Block
import json

# Lớp PeerService để nhận và xử lý tin nhắn
class PeerService(p2p_pb2_grpc.PeerServiceServicer):
    def __init__(self, peer_id, total_peers, is_byzantine=False):
        self.peer_id = peer_id
        self.total_peers = total_peers  # Tổng số peer (dựa trên len(peer_list))
        self.is_byzantine = is_byzantine
        self.blockchain = []
        self.prepare_messages = {}
        self.commit_messages = {}

    def SendMessage(self, request, context):
        print(f"[{self.peer_id}] Received message from {request.sender}: {request.content}")
        return p2p_pb2.Response(status="Message received")
    
    # Giai đoạn Pre-prepare
    def handle_pre_prepare(self, message):
        block = Block(message["previous_hash"], message["blockheight"])
        print(f"[Peer {self.peer_id}] Validating block: {block.blockhash}")
        self.broadcast_prepare(block)

    # Giai đoạn Prepare
    def handle_prepare(self, message):
        blockhash = message["blockhash"]
        self.prepare_messages[blockhash] = self.prepare_messages.get(blockhash, 0) + 1
        print(f"[Peer {self.peer_id}] Received Prepare for block: {blockhash}")
        if self.prepare_messages[blockhash] >= (self.total_peers - 1) // 3 + 1:
            self.broadcast_commit(blockhash)

    # Giai đoạn Commit
    def handle_commit(self, message):
        blockhash = message["blockhash"]
        self.commit_messages[blockhash] = self.commit_messages.get(blockhash, 0) + 1
        if self.commit_messages[blockhash] >= (self.total_peers - 1) // 3 + 1:
            self.commit_block(message)

    def broadcast_prepare(self, block):
        if self.is_byzantine:
            print(f"[Peer {self.peer_id}] Byzantine behavior! Sending invalid blockhash")
            block.blockhash = "INVALID_HASH"
        message = {"type": "prepare", "blockhash": block.blockhash}
        self.broadcast_message(message)

    def broadcast_commit(self, blockhash):
        message = {"type": "commit", "blockhash": blockhash}
        self.broadcast_message(message)

    def commit_block(self, message):
        block = Block(message["previous_hash"], message["blockheight"])
        self.blockchain.append(block)
        print(f"[Peer {self.peer_id}] Block committed: {block.blockhash}")

    def broadcast_message(self, message):
        # Broadcast to all peers
        pass  # Sẽ được cài đặt khi tích hợp

# Hàm chạy server gRPC
def run_server(peer_id, port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    p2p_pb2_grpc.add_PeerServiceServicer_to_server(PeerService(peer_id), server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"[{peer_id}] Server started at port {port}")
    return server

# Hàm gửi tin nhắn đến peer khác
def send_message(target_host, target_port, sender_name, content):
    channel = grpc.insecure_channel(f"{target_host}:{target_port}")
    stub = p2p_pb2_grpc.PeerServiceStub(channel)
    message = p2p_pb2.Message(sender=sender_name, content=content)
    response = stub.SendMessage(message)
    print(f"[{sender_name}] Received response: {response.status}")

# Chạy peer
def run_peer(peer_id, port, peer_list, is_byzantine=False):
    # server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    # p2p_pb2_grpc.add_PeerServiceServicer_to_server(
    #     PeerService(peer_id, len(peer_list), is_byzantine), server
    # )
    # server.add_insecure_port(f'[::]:{port}')
    # server.start()
    # print(f"[Peer {peer_id}] Server running at port {port}")

    # try:
    #     while True:
    #         time.sleep(10)
    # except KeyboardInterrupt:
    #     print(f"[Peer {peer_id}] Shutting down...")
    #     server.stop(0)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    p2p_pb2_grpc.add_PeerServiceServicer_to_server(
        PeerService(peer_id, len(peer_list), is_byzantine), server
    )
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"[Peer {peer_id}] Server running at port {port}")

    # Peer 1 sẽ gửi block
    if peer_id == 1:  # Chỉ Peer 1 là Primary
        block = Block("GENESIS_HASH", 1)  # Tạo block mới với previous_hash là "GENESIS_HASH"
        message = {"type": "pre-prepare", **block.to_dict()}  # Tạo message chứa thông tin block
        print(f"[Peer 1] Sending pre-prepare for block: {block.blockhash}")

        # Gửi block đến tất cả các peer khác
        for target_id, target_port in peer_list:
            try:
                channel = grpc.insecure_channel(f"localhost:{target_port}")
                stub = p2p_pb2_grpc.PeerServiceStub(channel)
                request = p2p_pb2.Message(
                    sender=f"Peer {peer_id}",
                    content=json.dumps(message)
                )
                stub.SendMessage(request)
                print(f"[Peer 1] Block sent to Peer {target_id}: {block.blockhash}")
            except Exception as e:
                print(f"[Peer {peer_id}] Error sending to Peer {target_id}: {e}")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print(f"[Peer {peer_id}] Shutting down...")
        server.stop(0)