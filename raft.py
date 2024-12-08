import logging
import threading
import time
import signal
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
        self.leader_id = None
        self.commit_index = 0
        self.last_applied = 0
        self.lock = threading.Lock()

        self.nextIndex= {peer: len(self.log) for peer in self.peers}
        self.heartbeat_responses = {x: 1 for x in self.peers}

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
        return 7 + ( 3 * random.random())

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
            self.heartbeat_responses = {x: 1 for x in self.peers}
        logging.info(f"Node {self.node_id} starting election for term {self.current_term}")
        with ThreadPoolExecutor() as executor:
            for peer in self.peers:
                executor.submit(self.send_request_vote, peer)
        logging.info(f"Node {self.node_id} sent vote requests to peers: {self.peers}")
        
        # Wait for election results with a slight delay for processing
        time.sleep(2)
        with self.lock:
            if self.votes_received > ((len(self.peers) + 1) // 2):
                self.state = 'leader'
                self.leader_id = self.node_id
                self.heartbeat_responses = {x: 1 for x in self.peers}
                logging.info(f"Node {self.node_id} became leader for term {self.current_term}")
                self.reset_election_timer()
                self.heartbeat()
            elif self.votes_received == ((len(self.peers) + 1)  // 2):
                # Tied vote detected
                logging.info(f"Node {self.node_id} detected a tie in election for term {self.current_term}")
                threading.Thread(target=self.handle_tied_vote).start()
            else:
                # Election failed, reset to follower and wait for the next election
                logging.info(f"Node {self.node_id} failed to win election for term {self.current_term}, returning to follower state")
                self.state = 'follower'
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
                        logging.info(f"Votes received: {self.votes_received}")
                        if self.votes_received > ((len(self.peers) + 1)  // 2):  
                            self.state = 'leader'
                            self.leader_id = self.node_id
                            logging.info(f"Node {self.node_id} became leader for term {self.current_term}")
                            self.reset_election_timer()
                            self.heartbeat()
        except Exception as e:
            logging.error(f"Node {self.node_id} failed to contact Node {peer}: {e}")
           

    def heartbeat(self):
        while self.state == 'leader':

            if((sum(self.heartbeat_responses.values()) + 1) <= ((len(self.peers) +1 ) // 2)):  # cộng thêm 1 của bản thân thì mạng mới đủ 100%
                self.state = 'follower'
                self.leader_id = None
                break

            self.heartbeat_responses = {x: 1 for x in self.peers}
            logging.info("-" * 50)  # Separator does not need `extra`
            logging.info(f"Node {self.node_id} sending heartbeats to all peers")

            with ThreadPoolExecutor() as executor:
                for peer in self.peers:
                    executor.submit(self.send_append_entries, peer)

            # logging.info(f"Node {self.node_id} received {self.heartbeat_responses} heartbeat responses")
            # if self.heartbeat_responses < (len(self.peers) // 2):
            #     logging.info(f"Node {self.node_id} has lost quorum, returning to follower state")
            #     self.state = 'follower'
            #     self.reset_election_timer()
            time.sleep(2)


    def AppendCommands(self, request, context):
        try:
            print(request)
            if not request.commands:
                logging.warning("Received an empty commands list from client.")
                return raft_pb2.AppendCommandsResponse(
                    term=self.current_term,
                    leaderId=str(self.node_id),
                    success=False
                )
            # Tạo danh sách entries từ các command trong request.commands
            new_entries = []
            for command in request.commands:
                entry = {
                    "term": self.current_term,  # Sử dụng current_term của leader
                    "command": command          # Command nhận từ request
                }
                new_entries.append(entry)

            # Log thông tin để kiểm tra
            logging.info(f"Received commands from client: {request.commands}")
            logging.info(f"Generated log entries: {new_entries}")


            self.log.extend(new_entries)
            self.save_log_to_file()

            # ** Không cần phải gửi các entries này tới các server(Follower) khác, vì nó sẽ tự động gửi ở Heartbeat tiếp theo **

            return raft_pb2.AppendCommandsResponse(term=self.current_term, leaderId = str(self.node_id) ,success= True)

        except Exception as e:
            logging.error(f"Failed to process new entry from client: {e}")
            return raft_pb2.AppendCommandsResponse(term=self.current_term, leaderId = str(self.node_id) ,success= False)


    def send_append_entries(self, peer):
        try:
            with grpc.insecure_channel(f'localhost:{peer}') as channel:
                stub = raft_pb2_grpc.RaftStub(channel)
                prev_log_index = self.nextIndex[peer] - 1
                if self.nextIndex[peer] == len(self.log): # Nếu Leader  và Follower giống nhau thì _entries = []
                    _entries = []
                elif prev_log_index >=0:
                    _entries = self.log[prev_log_index:]
                elif prev_log_index < 0:
                    _entries = self.log
                
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
                    self.heartbeat_responses[peer] = 1
                    self.nextIndex[peer] = len(self.log) # khi success thì đặt lại nextIndex 
                    logging.info(f"Node {peer} successfully appended entries.")
                else:
                    self.heartbeat_responses[peer] = 1
                    logging.error(f"Node {peer} failed to append entries. Adjusting prevLogIndex and retrying...")
                    if response.term == self.current_term:
                        # Lùi nextIndex
                        self.nextIndex[peer] = self.nextIndex[peer] - 1 
                        if self.nextIndex[peer] < 0:
                            logging.error("Cannot decrement nextIndex further. Aborting append.")
                    else:
                        logging.error("Term mismatch. Aborting append.")
                        
        except Exception as e:
            # Dùng để kiểm tra xem có bao nhiêu Server đã bị mất kết nối với Leader
            self.heartbeat_responses[peer] = 0 
            print(":self.num_peer_fail: ",self.num_peer_fail)
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
            if request.entries:
                print(request.entries[0].command)
            print("=================================================")
            if request.prevLogIndex < len(self.log) and request.prevLogIndex >= 0:
                print(self.log[request.prevLogIndex]['command'])
            
            ## Các Log bị Sai hoàn Toàn 
            if request.prevLogIndex < 0:
                self.log = []
                for i, entry in enumerate(request.entries):
                    self.log.append({"term": entry.term, "command": entry.command})
                    logging.info(f"Node {self.node_id} appended new entry: {self.log[-1]}")

                if request.leaderCommit > self.commit_index:
                    self.commit_index = min(request.leaderCommit, len(self.log) - 1)
                    logging.info(f"Node {self.node_id} updated commitIndex to {self.commit_index}")

                logging.info(f"AppendEntries response from node {self.node_id}: term={self.current_term}, success=True")
                self.save_log_to_file()
                return raft_pb2.AppendEntriesResponse(term=self.current_term, success=True)

            # Bước 3: Kiểm tra prevLogIndex và prevLogTerm Và cả command
            if request.prevLogIndex >= 0:
                if request.prevLogIndex >= len(self.log):
                    logging.info(f"Node {self.node_id} rejecting AppendEntries due to log mismatch at prevLogIndex {request.prevLogIndex}")
                    return raft_pb2.AppendEntriesResponse(term=self.current_term, success=False)
                elif self.log[request.prevLogIndex]['term'] != request.prevLogTerm:
                    logging.info(f"Node {self.node_id} rejecting AppendEntries due to log match at prevLogIndex but mismatch term {self.log[request.prevLogIndex]['term']} and {request.prevLogTerm}")
                    return raft_pb2.AppendEntriesResponse(term=self.current_term, success=False)
                elif request.entries:
                    if self.log[request.prevLogIndex]['command'] != request.entries[0].command:
                        logging.info(f"Node {self.node_id} rejecting AppendEntries due to log match at prevLogIndex and term but mismatch command {self.log[request.prevLogIndex]['term']} and {request.prevLogTerm}")
                        return raft_pb2.AppendEntriesResponse(term=self.current_term, success=False)

            #  Check HeartBeat:
            if not request.entries: #  entries rỗng
                logging.info(f"AppendEntries [] response from node {self.node_id}: term={self.current_term}, success=True")
                return raft_pb2.AppendEntriesResponse(term=self.current_term, success=True)

            # Bước 4: Xóa các entry conflict 
            for i, entry in enumerate(request.entries):
                print("i của enum", i)
                if len(self.log) >= request.prevLogIndex + 1 + i:
                    print(self.log[request.prevLogIndex  + i], " and ", entry.term)
                    if self.log[request.prevLogIndex + i]['term'] != entry.term or self.log[request.prevLogIndex]['command'] != entry.command:
                        logging.info(f"Node {self.node_id} removing conflicting entries starting from index {request.prevLogIndex + i} and {i}")
                        self.log = self.log[:request.prevLogIndex + i]
                        break

            # Bước 5: Append các entries mới
            for i, entry in enumerate(request.entries):
                if request.prevLogIndex + 1 + i > len(self.log):
                    self.log.append({"term": entry.term, "command": entry.command})
                    logging.info(f"Node {self.node_id} appended new entry: {self.log[-1]}")

            # Bước 6: Cập nhật commitIndex
            if request.leaderCommit > self.commit_index:
                self.commit_index = min(request.leaderCommit, len(self.log) - 1)
                logging.info(f"Node {self.node_id} updated commitIndex to {self.commit_index}")
    
            logging.info(f"AppendEntries response from node {self.node_id}: term={self.current_term}, success=True")
            self.save_log_to_file()
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
            print(f"Log loaded from {file_path}: {log}")
        except Exception as e:
            print(f"Failed to load log from {file_path}: {e}")
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
            print(f"Log successfully saved to {file_path}")
        except Exception as e:
            print(f"Failed to save log to {file_path}: {e}")

    def handle_tied_vote(self):
        """ Handle the tie vote scenario by putting the node in timeout for 4 seconds. """
        logging.info(f"Node {self.node_id} detected a tied vote. Timing out for {self.tied_vote_timeout} seconds.")
        self.tied_vote_in_progress = True
        time.sleep(self.tied_vote_timeout)
        self.tied_vote_in_progress = False
        logging.info(f"Node {self.node_id} timeout finished. Ready for next election.")
    
    def SetPeers(self, request, context):
        try:
            logging.info(f"Node {self.node_id} updating peers: {request.peers}")
            self.peers = list(request.peers)
            self.nextIndex = {peer: len(self.log) for peer in self.peers}
            # self.state = 'follower'
            # self.start_election()

            logging.info(f"Node {self.node_id} updated peers to: {self.peers}")
            return raft_pb2.SetPeersResponse(success=True, message="Peers updated successfully.")
        except Exception as e:
            logging.error(f"Error in SetPeers: {e}")
            return raft_pb2.SetPeersResponse(success=False, message=str(e))
        
def serve(node_id, port, peers):
    server = grpc.server(ThreadPoolExecutor(max_workers=10))
    raft_servicer = RaftServicer(node_id, peers)
    raft_pb2_grpc.add_RaftServicer_to_server(raft_servicer, server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    logging.info(f"Node {node_id} gRPC server started and listening on port {port}")

    # Graceful shutdown handling
    def handle_termination(signum, frame):
        logging.info("Graceful shutdown initiated...")
        raft_servicer.election_timer.cancel()
        server.stop(0)  # Stop the gRPC server
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_termination)
    signal.signal(signal.SIGTERM, handle_termination)

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
