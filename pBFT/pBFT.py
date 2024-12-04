import grpc
from concurrent import futures
import time
import pbft_pb2
import pbft_pb2_grpc
import logging
import threading

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
    def stop_server(self, server):
        server.stop(0)
        self.log_info(f"Node {self.node_id} server stopped.")
    def log_info(self, message):
        self.logger.info(message, extra={'node_id': self.node_id})

    def PrePrepare(self, request, context):
        block = request.block
        self.log_info(f"Received PrePrepare for block {block.blockheight} from Node {request.sender_id}")
        
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
                    phase=phase
                )
                getattr(stub, phase)(message)
                self.log_info(f"Sent {phase} to {peer}")

def serve(node_id, port, peers, is_byzantine=False):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    node = Node(node_id, peers, is_byzantine)
    pbft_pb2_grpc.add_PBFTServiceServicer_to_server(node, server)
    server.add_insecure_port(f'[::]:{port}')
    
    server.start()
    node.log_info(f"Node {node_id} started on port {port}")

    try:
        time.sleep(3)  # Give time for other nodes to start
        if node_id == 1:  # Leader node
            block = pbft_pb2.Block(previous_blockhash="0000", blockhash="blockhash_1", blockheight=1)
            node.send_message("PrePrepare", block)
        server.wait_for_termination()
    except KeyboardInterrupt:
        node.stop_server(server)

if __name__ == "__main__":
    peers = ['localhost:50052', 'localhost:50053']
    
    threads = []
    for i, is_byzantine in zip([1, 2, 3], [False, False, True]):
        t = threading.Thread(target=serve, args=(i, 50050 + i, peers, is_byzantine))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
