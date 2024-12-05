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
        lastLogTerm=last_log_term,
    )
    return stub.RequestVote(request)


def get_status(stub):
    request = raft_pb2.GetStatusRequest()
    return stub.GetStatus(request, timeout=20)


def get_committed_logs(stub):
    request = raft_pb2.GetCommittedLogsRequest()
    return stub.GetCommittedLogs(request)


def append_entries(stub, term, leader_id, prev_log_index, prev_log_term, entries, leader_commit):
    request = raft_pb2.AppendEntriesRequest(
        term=term,
        leaderId=leader_id,
        prevLogIndex=prev_log_index,
        prevLogTerm=prev_log_term,
        entries=[
            raft_pb2.LogEntry(term=entries[i], command=entries[i + 1])
            for i in range(0, len(entries), 2)
        ],
        leaderCommit=leader_commit,
    )
    return stub.AppendEntries(request)


def run_client(node_address, action, *args):
    with grpc.insecure_channel(node_address) as channel:
        stub = raft_pb2_grpc.RaftStub(channel)
        logging.info(f"Client connected to {node_address}")

        if action == 'request_vote':
            term, candidate_id, last_log_index, last_log_term = map(int, args)
            response = request_vote(stub, term, candidate_id, last_log_index, last_log_term)
            print(f"RequestVote response: term={response.term}, voteGranted={response.voteGranted}")

        elif action == 'append_entries':
            # Parse common arguments
            term = int(args[0])
            leader_id = int(args[1])
            prev_log_index = int(args[2])
            prev_log_term = int(args[3])
            leader_commit = int(args[-1])

            # Entries: Remaining arguments (skipping the last one, which is leader_commit)
            entries_args = args[4:-1]
            if len(entries_args) % 2 != 0:
                raise ValueError("Entries must have even number of arguments (term and command pairs).")

            # Create entries as list of term-command pairs
            entries = [(int(entries_args[i]), entries_args[i + 1]) for i in range(0, len(entries_args), 2)]

            response = append_entries(
                stub, term, leader_id, prev_log_index, prev_log_term, entries, leader_commit
            )
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

    # Get inputs from command line
    node_address = sys.argv[1]
    action = sys.argv[2]
    args = sys.argv[3:]
    run_client(node_address, action, *args)
