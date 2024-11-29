import logging
import grpc
import raft_pb2
import raft_pb2_grpc

logging.basicConfig(level=logging.INFO)

def request_vote(stub, term, candidate_id, last_log_index, last_log_term):
    request = raft_pb2.RequestVoteRequest(
        term=term,
        candidateId=candidate_id,
        lastLogIndex=last_log_index,
        lastLogTerm=last_log_term
    )
    return stub.RequestVote(request)

def append_entries(stub, term, leader_id, prev_log_index, prev_log_term, entries, leader_commit):
    request = raft_pb2.AppendEntriesRequest(
        term=term,
        leaderId=leader_id,
        prevLogIndex=prev_log_index,
        prevLogTerm=prev_log_term,
        entries=entries,
        leaderCommit=leader_commit
    )
    return stub.AppendEntries(request)

def get_status(stub):
    request = raft_pb2.GetStatusRequest()
    return stub.GetStatus(request, timeout=20)  # Increase timeout

def get_committed_logs(stub):
    request = raft_pb2.GetCommittedLogsRequest()
    return stub.GetCommittedLogs(request)

def run_client(node_address, action, *args):
    with grpc.insecure_channel(node_address) as channel:
        stub = raft_pb2_grpc.RaftStub(channel)
        logging.info(f"Client connected to {node_address}")
        if action == 'request_vote':
            term, candidate_id, last_log_index, last_log_term = args
            response = request_vote(stub, term, candidate_id, last_log_index, last_log_term)
            print(f"RequestVote response: term={response.term}, voteGranted={response.voteGranted}")
        elif action == 'append_entries':
            term, leader_id, prev_log_index, prev_log_term, entries, leader_commit = args
            response = append_entries(stub, term, leader_id, prev_log_index, prev_log_term, entries, leader_commit)
            print(f"AppendEntries response: term={response.term}, success={response.success}")
        elif action == 'get_status':
            response = get_status(stub)
            print(f"GetStatus response: term={response.term}, state={response.state}")
        elif action == 'get_committed_logs':
            response = get_committed_logs(stub)
            for key, value in response.logs.items():
                print(f"{key}: {value}")

if __name__ == '__main__':
    import sys
    node_address = sys.argv[1]
    action = sys.argv[2]
    args = sys
