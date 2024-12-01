import logging
import threading
import time
import random
import grpc
from concurrent.futures import ThreadPoolExecutor
import raft_pb2
import raft_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Node %(node_id)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Add a logging filter to ensure `node_id` is always available
class NodeIDFilter(logging.Filter):
    def __init__(self, node_id):
        super().__init__()
        self.node_id = node_id

    def filter(self, record):
        if not hasattr(record, "node_id"):
            record.node_id = self.node_id
        return True

class RaftServicer(raft_pb2_grpc.RaftServicer):
    def __init__(self, node_id, peers):
        self.node_id = node_id
        self.current_term = 0
        self.voted_for = None
        self.state = 'follower'
        self.log = []
        self.votes_received = 0
        self.peers = peers
        self.leader_id = None
        self.commit_index = 0
        self.last_applied = 0
        self.lock = threading.Lock()
        self.kv_store = {}
        self.election_timeout = self.get_election_timeout()
        self.election_timer = threading.Timer(self.election_timeout, self.start_election)
        self.election_timer.start()
        self.tied_vote_timeout = 4  # Timeout duration in seconds for tied votes
        self.tied_vote_in_progress = False  # Track if a tie vote timeout is in progress

        # Attach a filter to ensure `node_id` is always available
        node_id_filter = NodeIDFilter(self.node_id)
        logging.getLogger().addFilter(node_id_filter)

        logging.info(f"Node {self.node_id} initialized with peers: {self.peers}")

    def get_election_timeout(self):
        return 1.5 + ( 1.5 * random.random())

    def reset_election_timer(self):
        self.election_timer.cancel()
        self.election_timer = threading.Timer(self.get_election_timeout(), self.start_election)
        self.election_timer.start()

    def start_election(self):
        with self.lock:
            if self.state == 'leader' or self.tied_vote_in_progress:
                return  
            self.state = 'candidate'
            self.current_term += 1
            self.voted_for = self.node_id
            self.votes_received = 1
        logging.info(f"Node {self.node_id} starting election for term {self.current_term}")
        with ThreadPoolExecutor() as executor:
            for peer in self.peers:
                executor.submit(self.send_request_vote, peer)
        logging.info(f"Node {self.node_id} sent vote requests to peers: {self.peers}")
        self.reset_election_timer()

    def send_request_vote(self, peer):
        try:
            with grpc.insecure_channel(f'localhost:{peer}') as channel:
                stub = raft_pb2_grpc.RaftStub(channel)
                request = raft_pb2.RequestVoteRequest(
                    term=self.current_term,
                    candidateId=str(self.node_id),  # Ensure candidateId is a string
                    lastLogIndex=len(self.log) - 1,
                    lastLogTerm=self.log[-1].term if self.log else 0,
                )
                logging.info(f"Node {self.node_id} sending RequestVote to {peer}: term={self.current_term}, lastLogIndex={request.lastLogIndex}, lastLogTerm={request.lastLogTerm}")
                response = stub.RequestVote(request, timeout=500)  # Increase timeout
                logging.info(f"Received RequestVote response from Node {peer}: {response}")
                if response.voteGranted:
                    with self.lock:
                        self.votes_received += 1
                        if self.votes_received > len(self.peers) // 2:
                            self.state = 'leader'
                            self.leader_id = self.node_id
                            logging.info(f"Node {self.node_id} became leader for term {self.current_term}")
                            self.reset_election_timer()
                            self.heartbeat()
        except Exception as e:
            logging.error(f"Node {self.node_id} failed to contact Node {peer}: {e}")

    def heartbeat(self):
        while self.state == 'leader':
            logging.info("-" * 50)  # Separator does not need `extra`
            logging.info(f"Node {self.node_id} sending heartbeats to all peers")
            with ThreadPoolExecutor() as executor:
                for peer in self.peers:
                    executor.submit(self.send_append_entries, peer)
            time.sleep(0.5)

    def send_append_entries(self, peer):
        try:
            with grpc.insecure_channel(f'localhost:{peer}') as channel:
                stub = raft_pb2_grpc.RaftStub(channel)
                prev_log_index = len(self.log) - 1
                prev_log_term = self.log[prev_log_index].term if prev_log_index >= 0 else 0

                request = raft_pb2.AppendEntriesRequest(
                    term=self.current_term,
                    leaderId=str(self.node_id),
                    prevLogIndex=prev_log_index,
                    prevLogTerm=prev_log_term,
                    entries=[],
                    leaderCommit=self.commit_index,
                )

                logging.info(f"Node {self.node_id} sending AppendEntries to Node {peer}: {request}")
                response = stub.AppendEntries(request, timeout=5)

                # If the response term is higher, step down
                if response.term > self.current_term:
                    logging.info(f"Node {self.node_id} stepping down: higher term {response.term} received.")
                    self.current_term = response.term
                    self.state = 'follower'
                    self.leader_id = None
                    self.reset_election_timer()
        except Exception as e:
            logging.error(f"Failed to send AppendEntries to Node {peer}: {e}")

                
        except Exception as e:
            logging.error(f"Failed to send AppendEntries to Node {peer}: {e}")

    def RequestVote(self, request, context):
        logging.info(f"RequestVote called on node {self.node_id} with request:\n{request}")
        with self.lock:
            if request.term > self.current_term:
                self.current_term = request.term
                self.voted_for = None
                self.state = 'follower'
                self.reset_election_timer()
            vote_granted = (self.voted_for in [None, request.candidateId] and request.term >= self.current_term)
            if vote_granted:
                self.voted_for = request.candidateId
                self.reset_election_timer()
        logging.info(f"RequestVote response from node {self.node_id}: term={self.current_term}, voteGranted={vote_granted}")
        return raft_pb2.RequestVoteResponse(term=self.current_term, voteGranted=vote_granted)

    def AppendEntries(self, request, context):
        logging.info(f"AppendEntries called on node {self.node_id} with request: {request}")
        with self.lock:
            if request.term < self.current_term:
                return raft_pb2.AppendEntriesResponse(term=self.current_term, success=False)
            self.current_term = request.term
            self.state = 'follower'
            self.leader_id = request.leaderId
            self.reset_election_timer()
        logging.info(f"AppendEntries response from node {self.node_id}: term={self.current_term}, success=True")
        return raft_pb2.AppendEntriesResponse(term=self.current_term, success=True)


    def GetStatus(self, request, context):
        with self.lock:
            logging.info(f"GetStatus called on node {self.node_id}")
            return raft_pb2.GetStatusResponse(
                term=self.current_term,
                state=self.state
            )

    def handle_tied_vote(self):
        """ Handle the tie vote scenario by putting the node in timeout for 4 seconds. """
        logging.info(f"Node {self.node_id} detected a tied vote. Timing out for {self.tied_vote_timeout} seconds.")
        self.tied_vote_in_progress = True
        time.sleep(self.tied_vote_timeout)
        self.tied_vote_in_progress = False
        logging.info(f"Node {self.node_id} timeout finished. Ready for next election.")

def serve(node_id, port, peers):
    server = grpc.server(ThreadPoolExecutor(max_workers=10))
    raft_servicer = RaftServicer(node_id, peers)
    raft_pb2_grpc.add_RaftServicer_to_server(raft_servicer, server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    logging.info(f"Node {node_id} gRPC server started and listening on port {port}")
    server.wait_for_termination()


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("Usage: python raft_server.py <node_id> <port> [peer_ports...]")
        sys.exit(1)

    node_id = int(sys.argv[1])
    port = int(sys.argv[2])
    peers = list(map(int, sys.argv[3:]))
    try:
        peers.remove(port)
    except ValueError:
        pass

    serve(node_id, port, peers)
