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

        # Đọc dữ liệu log từ file
        self.file_path = f"Save log/log of node {self.node_id}.txt"
        self.log = self.load_log_from_file()
        if self.log:
            self.current_term = self.log[-1]['term']
        
        self.votes_received = 0
        self.peers = peers
        self.active_peers = set(peers)
        self.leader_id = None
        self.commit_index = 0
        self.last_applied = 0
        self.lock = threading.Lock()

        self.kv_store = {}
        self.election_timeout = self.get_election_timeout()
        self.election_timer = threading.Timer(self.election_timeout, self.start_election)
        self.election_timer.start()
        self.tied_vote_timeout = 8  # Timeout duration in seconds for tied votes
        self.tied_vote_in_progress = False  # Track if a tie vote timeout is in progress


        # Attach a filter to ensure `node_id` is always available
        node_id_filter = NodeIDFilter(self.node_id)
        logging.getLogger().addFilter(node_id_filter)

        logging.info(f"Node {self.node_id} initialized with peers: {self.peers}")

    def get_election_timeout(self):
        return 15 + ( 1.5 * random.random())

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
                    candidateId=str(self.node_id),
                    lastLogIndex=len(self.log) - 1,
                    lastLogTerm=self.log[-1]['term'] if self.log else 0,
                )
                logging.info(f"Node {self.node_id} sending RequestVote to {peer}: term={self.current_term}, lastLogIndex={request.lastLogIndex}, lastLogTerm={request.lastLogTerm}")
                response = stub.RequestVote(request, timeout=500)
                logging.info(f"Received RequestVote response from Node {peer}: {response}")
                if response.voteGranted:
                    with self.lock:
                        self.votes_received += 1
                        if self.votes_received > len(self.active_peers) // 2:  # Use active peers for majority calculation
                            self.state = 'leader'
                            self.leader_id = self.node_id
                            logging.info(f"Node {self.node_id} became leader for term {self.current_term}")
                            self.reset_election_timer()
                            self.heartbeat()
        except Exception as e:
            logging.error(f"Node {self.node_id} failed to contact Node {peer}: {e}")
            # Consider the peer inactive if it fails
            self.active_peers.discard(peer)

    def heartbeat(self):
        while self.state == 'leader':
            logging.info("-" * 50)  # Separator does not need `extra`
            logging.info(f"Node {self.node_id} sending heartbeats to all peers")

            with ThreadPoolExecutor() as executor:
                for peer in self.peers:
                    executor.submit(self.send_append_entries, peer, [])
            time.sleep(3.5)

    def recieve_entries_from_client(self, request):
        try:
            # Tạo entry mới từ yêu cầu của client
            new_entry = {"term": self.current_term, "command": request.command}
            logging.info(f"Node {self.node_id} received new entry from client: {new_entry}")

            # Thêm entry mới vào log của leader
            with self.lock:
                self.log.append(new_entry)
                logging.info(f"Node {self.node_id} added new entry to log: {self.log}")

            # Gửi entry mới tới các follower
            _entries = [
                raft_pb2.LogEntry(term=new_entry["term"], command=new_entry["command"])
            ]

            with ThreadPoolExecutor() as executor:
                    for peer in self.peers:
                        executor.submit(self.send_append_entries, peer, [])
                    time.sleep(3.5)

        except Exception as e:
            logging.error(f"Failed to process new entry from client: {e}")

    def send_append_entries(self, peer, _entries):
        try:
            with grpc.insecure_channel(f'localhost:{peer}') as channel:
                stub = raft_pb2_grpc.RaftStub(channel)
                prev_log_index = len(self.log) - 1
                while True:  # Lặp lại cho đến khi follower thành công
                    prev_log_term = self.log[prev_log_index]['term'] if prev_log_index >= 0 else 0

                    request = raft_pb2.AppendEntriesRequest(
                        term=self.current_term,
                        leaderId=str(self.node_id),
                        prevLogIndex=prev_log_index,
                        prevLogTerm=prev_log_term,
                        entries=_entries,
                        leaderCommit=self.commit_index,
                    )

                    logging.info(f"Node {self.node_id} sending AppendEntries to Node {peer}: {request}")
                    response = stub.AppendEntries(request, timeout=5)

                    if response.success:
                        logging.info(f"Node {peer} successfully appended entries.")
                        break  # Dừng lặp khi follower thành công
                    else:
                        logging.error(f"Node {peer} failed to append entries. Adjusting prevLogIndex and retrying...")
                        if response.term == self.current_term:
                            # Lùi prev_log_index và thử gửi lại
                            prev_log_index = prev_log_index - 1 
                            if prev_log_index < 0:
                                logging.error("Cannot decrement prev_log_index further. Aborting append.")
                                break
                            _entries = self.log[prev_log_index:]  # Lấy các entries từ prev_log_index + 1 để gửi
                        else:
                            logging.error("Term mismatch. Aborting append.")
                            break  # Thoát nếu có lỗi nghiêm trọng hơn


        except Exception as e:
            logging.error(f"Failed to send AppendEntries to Node {peer}: {e}")

    def RequestVote(self, request, context):
        logging.info(f"RequestVote called on node {self.node_id} with request:\n{request}")
        with self.lock:
            if self.state == 'candidate': # Nếu node đang là candidate thì không được vote
                vote_granted = False 
                return raft_pb2.RequestVoteResponse(term=self.current_term, voteGranted=vote_granted)


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
            else:
                self.current_term = request.term
                self.state = 'follower'
                self.leader_id = request.leaderId
                self.reset_election_timer()

        # Bước 3: Kiểm tra prevLogIndex và prevLogTerm Và cả command
        if request.prevLogIndex >= 0:
            if request.prevLogIndex >= len(self.log):
                logging.info(f"Node {self.node_id} rejecting AppendEntries due to log mismatch at prevLogIndex {request.prevLogIndex}")
                return raft_pb2.AppendEntriesResponse(term=self.current_term, success=False)
            elif self.log[request.prevLogIndex]['term'] != request.prevLogTerm:
                logging.info(f"Node {self.node_id} rejecting AppendEntries due to log match at prevLogIndex but mismatch term {self.log[request.prevLogIndex]['term']} and {request.prevLogTerm}")
                return raft_pb2.AppendEntriesResponse(term=self.current_term, success=False)
            elif self.log[request.prevLogIndex]['command'] != request.entries[0]['command']:
                logging.info(f"Node {self.node_id} rejecting AppendEntries due to log match at prevLogIndex and term but mismatch command {self.log[request.prevLogIndex]['term']} and {request.prevLogTerm}")
                return raft_pb2.AppendEntriesResponse(term=self.current_term, success=False)
            
        # Bước 4: Xóa các entry conflict 
        for i, entry in enumerate(request.entries):
            if len(self.log) > request.prevLogIndex + 1 + i:
                if self.log[request.prevLogIndex + 1 + i]['term'] != entry['term']:
                    logging.info(f"Node {self.node_id} removing conflicting entries starting from index {request.prevLogIndex + 1 + i}")
                    self.log = self.log[:request.prevLogIndex + 1 + i]
                    break

        # Bước 5: Append các entries mới
        for i, entry in enumerate(request.entries):
            if request.prevLogIndex + 1 + i > len(self.log):
                self.log.append({"term": entry['term'], "command": entry['command']})
                logging.info(f"Node {self.node_id} appended new entry: {self.log[-1]}")

        # Bước 6: Cập nhật commitIndex
        if request.leaderCommit > self.commit_index:
            self.commit_index = min(request.leaderCommit, len(self.log) - 1)
            logging.info(f"Node {self.node_id} updated commitIndex to {self.commit_index}")
 
        logging.info(f"AppendEntries response from node {self.node_id}: term={self.current_term}, success=True")

        return raft_pb2.AppendEntriesResponse(term=self.current_term, success=True)


    def GetStatus(self, request, context):
        with self.lock:
            logging.info(f"GetStatus called on node {self.node_id}")
            return raft_pb2.GetStatusResponse(
                term=self.current_term,
                state=self.state
            )
        
    def load_log_from_file(self):
        file_path = self.file_path
        log = []
        try:
            with open(file_path, "r") as f:
                for line in f:
                    term, command = line.strip().split(",")
                    log.append({"term": int(term), "command": command})
            logging.info(f"Log loaded from {file_path}: {log}")
        except Exception as e:
            logging.error(f"Failed to load log from {file_path}: {e}")
        return log

    def save_log_to_file(self):
        """
        Ghi danh sách log vào file.

        :param log: Danh sách các entries log (list of dicts).
        :param file_path: Đường dẫn tới file cần ghi.
        """
        log = self.log
        file_path = self.file_path
        try:
            with open(file_path, "w") as f:
                for entry in log:
                    # Mỗi entry được ghi ở định dạng: term,command
                    f.write(f"{entry['term']},{entry['command']}\n")
            logging.info(f"Log successfully saved to {file_path}")
        except Exception as e:
            logging.info(f"Failed to save log to {file_path}: {e}")

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
