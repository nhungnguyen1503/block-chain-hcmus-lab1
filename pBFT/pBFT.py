import signal
import grpc
from concurrent import futures
import time
import pbft_pb2
import pbft_pb2_grpc
import logging
import threading

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

# NUM_REPLICAS = 3  # Tổng số bản sao (Nodes)
# F = (NUM_REPLICAS - 1) // 3
# Tạo khóa RSA cho mỗi node (đơn giản hóa)
def generate_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=512)
    public_key = private_key.public_key()
    return private_key, public_key
# Define the Node class
class Node(pbft_pb2_grpc.PBFTServiceServicer):
    def __init__(self, node_id, peers, is_byzantine=False):
        self.node_id = node_id
        self.peers = peers  # List of peer addresses (strings)
        self.is_byzantine = is_byzantine
        self.logger = logging.getLogger(f"Node {self.node_id}")
        self.logger.setLevel(logging.INFO)
        
        # Logging setup
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s [Node %(node_id)d] %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.prepares_received = {}  # To track Prepare messages
        self.commits_received = {}   # To track Commit messages
        self.committed_blocks = set()  # To track committed blocks

        self.private_key, self.public_key = generate_keys()
        self.peer_keys = {} 

        # self.view_change_messages = {}  # Initialize the view_change_messages

        # self.current_view = 0
        # self.primary = 0  # Node đầu tiên là primary
        # self.view_change_timer = threading.Timer(5, self.start_view_change)  # 10 giây timeout
        # self.view_change_timer.start()

        self.F = (len(peers) - 1) // 3
    def exchange_keys(self):
    # Gửi khóa công khai của node này đến tất cả các peer
        for peer in self.peers:
            with grpc.insecure_channel(peer) as channel:
                stub = pbft_pb2_grpc.PBFTServiceStub(channel)
                public_key_pem = self.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                message = pbft_pb2.PublicKeyMessage(
                    sender_id=str(self.node_id),
                    public_key=public_key_pem
                )
                try:
                    stub.ExchangePublicKey(message)
                except grpc.RpcError as e:
                    self.log_info(f"Failed to send public key to Node {peer}: {e.details()}")

    def ExchangePublicKey(self, request, context):
        # Nhận khóa công khai từ một node khác và lưu trữ nó
        sender_id = request.sender_id
        public_key_pem = request.public_key
        public_key = serialization.load_pem_public_key(public_key_pem)
        self.peer_keys[sender_id] = public_key
        return pbft_pb2.Empty()
    
    def reset_timer(self):
        if self.view_change_timer.is_alive():
            self.view_change_timer.cancel()
        self.view_change_timer = threading.Timer(10, self.start_view_change)
        self.view_change_timer.start()

    def start_view_change(self):
        self.current_view += 1
        # Chọn primary mới, bỏ qua node Byzantine
        
        valid_peers = [peer for peer in self.peers if not self.is_peer_byzantine(peer)]
    
        if len(valid_peers) > 0:
            # Chọn primary từ các node hợp lệ
            self.primary = valid_peers[self.current_view % len(valid_peers)]
            self.log_info(f"Starting view change. New primary is Node {self.primary}")
        else:
            self.log_info("No valid peers to select as primary.")
        
        self.broadcast_view_change()
    def is_peer_byzantine(self, peer):
    # Kiểm tra nếu peer là Byzantine
        return self.is_byzantine if self.node_id == peer else False

    def broadcast_view_change(self):
        for peer in self.peers:
            with grpc.insecure_channel(peer) as channel:
                stub = pbft_pb2_grpc.PBFTServiceStub(channel)
                # Đảm bảo current_view là int và node_id là string
                message = pbft_pb2.ViewChangeMessage(view=int(self.current_view), node_id=str(self.node_id))
                try:
                    stub.ViewChange(message)
                    self.log_info(f"Sent VIEW-CHANGE to Node {peer}")
                except grpc.RpcError as e:
                    self.log_info(f"Failed to send VIEW-CHANGE to Node {peer}: {e.details()}")
    # def NewView(self, request, context):
    #     self.log_info(f"Received NEW-VIEW for view {request.view} from Node {request.node_id}")
        
    #     # Cập nhật view và primary mới
    #     self.current_view = request.view
    #     self.primary = self.current_view % len(self.peers)
    #     self.view_change_messages.clear()  # Xóa thông tin VIEW-CHANGE cũ
    #     self.log_info(f"Switched to new view {self.current_view} with primary Node {self.primary}")
    
    #     # Tiếp tục xử lý các yêu cầu chưa hoàn thành trong view trước
    #     self.process_pending_requests()
    #     return pbft_pb2.Empty()
    # def ViewChange(self, request, context):
    #     self.log_info(f"Received view change to view {request.view} from Node {request.node_id}")
        
    #     # Lưu trữ thông tin VIEW-CHANGE
    #     if request.view not in self.view_change_messages:
    #         self.view_change_messages[request.view] = set()
    #     self.view_change_messages[request.view].add(request.node_id)
        
    #     # Kiểm tra nếu đủ số lượng VIEW-CHANGE từ ít nhất 2f+1 bản sao
    #     if len(self.view_change_messages.get(request.view, set())) >= (2 * self.F + 1):
    #         self.log_info(f"Collected enough VIEW-CHANGE messages for view {request.view}")

    #         # Cập nhật view hiện tại và chọn primary mới
    #         self.current_view = request.view
    #         self.primary = self.current_view % len(self.peers)
    #         self.log_info(f"View changed to {self.current_view}. New primary is Node {self.primary}")
            
    #         # Nếu node này là primary trong view mới, gửi thông báo NEW-VIEW
    #         if self.primary == self.node_id:
    #             self.broadcast_new_view()

    #     return pbft_pb2.Empty()

    # def broadcast_new_view(self):
    #     self.log_info(f"Node {self.node_id} is new primary. Broadcasting NEW-VIEW message.")
    #     for peer in self.peers:
    #         with grpc.insecure_channel(peer) as channel:
    #             stub = pbft_pb2_grpc.PBFTServiceStub(channel)
    #             # Đảm bảo current_view là int và node_id là string
    #             new_view_message = pbft_pb2.NewViewMessage(view=self.current_view, node_id=str(self.node_id))
    #             try:
    #                 stub.NewView(new_view_message)
    #             except grpc.RpcError as e:
    #                 self.log_info(f"Failed to send NEW-VIEW to Node {peer}: {e.details()}")

    
    # def process_pending_requests(self):
    #     # Logic xử lý các yêu cầu chưa hoàn thành trong view cũ
    #     self.log_info(f"Processing pending requests in view {self.current_view}")

    def sign_block(self, block):
        message = block.blockhash.encode()
        signature = self.private_key.sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        return signature

    def verify_signature(self, block, signature, sender_id):
        if sender_id not in self.peer_keys:
            self.log_info(f"Public key for Node {sender_id} not found.")
            return False
        
        public_key = self.peer_keys[sender_id]
        try:
            public_key.verify(
                signature,
                block.blockhash.encode(),
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            self.log_info(f"Signature verification failed for Node {sender_id}: {e}")
            return False
        

    def stop_server(self, server):
        server.stop(0)
        self.log_info(f"Node {self.node_id} server stopped.")
        
    def log_info(self, message):
        self.logger.info(message, extra={'node_id': self.node_id})

    def PrePrepare(self, request, context):
        block = request.block
        signature = request.signature
        self.log_info(f"Received PrePrepare for block {block.blockheight} from Node {request.sender_id}")
        
        if not self.verify_signature(block, signature, request.sender_id):
            self.log_info(f"Invalid signature from Node {request.sender_id}")
            return pbft_pb2.Empty()

        # Validate block and broadcast Prepare
        if not self.is_byzantine:
            self.send_message("Prepare", block)
        
        return pbft_pb2.Empty()

    def Prepare(self, request, context):
        block = request.block
        self.log_info(f"Received Prepare for block {block.blockheight} from Node {request.sender_id}")
        
        # Track Prepare messages
        self.track_message(self.prepares_received, block.blockheight, request.sender_id)
        
        # Broadcast Commit if enough Prepare messages received
        if len(self.prepares_received.get(block.blockheight, set())) >= (2 * len(self.peers) // 3):
            self.send_message("Commit", block)
        return pbft_pb2.Empty()

    def Commit(self, request, context):
        block = request.block
        self.log_info(f"Received Commit for block {block.blockheight} from Node {request.sender_id}")
        
        # Track Commit messages
        self.track_message(self.commits_received, block.blockheight, request.sender_id)
        
        # Finalize block if enough Commit messages received
        if len(self.commits_received.get(block.blockheight, set())) >= (2 * len(self.peers) // 3):
            self.committed_blocks.add(block.blockheight)
            self.log_info(f"Block {block.blockheight} committed successfully!")
        return pbft_pb2.Empty()

    def track_message(self, message_store, block_height, sender_id):
        if block_height not in message_store:
            message_store[block_height] = set()
        message_store[block_height].add(sender_id)

    # Sending messages to peers
    def send_message(self, phase, block):
        for peer in self.peers:
            with grpc.insecure_channel(peer) as channel:
                stub = pbft_pb2_grpc.PBFTServiceStub(channel)
                message = pbft_pb2.PBFTMessage(
                    sender_id=str(self.node_id),
                    block=block,
                    phase=phase,
                    signature=self.sign_block(block) if not self.is_byzantine else b"fake_signature"
                )
                try:
                    getattr(stub, phase)(message)
                    self.log_info(f"Sent {phase} to {peer}")
                except grpc.RpcError as e:
                    self.log_info(f"RPC Error during {phase} to {peer}: {e.details()}")

def serve(node_id, port, peers, is_byzantine=False):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    node = Node(node_id, peers, is_byzantine)
    pbft_pb2_grpc.add_PBFTServiceServicer_to_server(node, server)
    server.add_insecure_port(f'[::]:{port}')
    
    server.start()
    node.log_info(f"Node {node_id} started on port {port}")

    node.exchange_keys()
    try:
        time.sleep(3)  # Give time for other nodes to start
        if node_id == 1:  # Leader node
            block = pbft_pb2.Block(previous_blockhash="0000", blockhash="blockhash_1", blockheight=1)
            node.send_message("PrePrepare", block)
        
        # Monitor shutdown event
        while not shutdown_event.is_set():
            time.sleep(1)  # Check periodically if shutdown is triggered

    
    finally:
        node.stop_server(server)
        


def handle_shutdown(signum, frame):
    print("\nShutting down all servers...")

if __name__ == "__main__":

    peers = ['localhost:50052', 'localhost:50053', 'localhost:50054']
    shutdown_event = threading.Event()
    threads = []


    try:
        for i, is_byzantine in zip([1, 2, 3, 4], [False, False, True, False]):
            t = threading.Thread(target=serve, args=(i, 50050 + i, peers, is_byzantine))
            threads.append(t)
            t.start()

        while not shutdown_event.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("**************************************")
        shutdown_event.set()

    for t in threads:
        t.join()

    
    print("----------------------------------")

    print("All servers have been shut down.")
