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


def append_entries(stub, term, leader_id, prev_log_index, prev_log_term, commands, leader_commit):
    try:
        request = raft_pb2.AppendEntriesRequest(
            term=term,
            leaderId=leader_id,
            prevLogIndex=prev_log_index,
            prevLogTerm=prev_log_term,
            entries=[
                raft_pb2.LogEntry(term=term, command=command)
                for command in commands  # Iterate over the commands list
            ],
            leaderCommit=leader_commit,
        )
        return stub.AppendEntries(request)
    except Exception as e:
        logging.error(f"Error in append_entries: {e}")
        raise

def set_peers(stub, peers):
    request = raft_pb2.SetPeersRequest(peers=peers)
    return stub.SetPeers(request)

# Đang chờ viết Giao Thức
def append_commands(stub, commands):
    try:
        request = raft_pb2.AppendCommandsRequest(
            commands = commands
        )
        return stub.AppendCommands(request)
    except Exception as e:
        logging.error(f"Error in append_commands: {e}")
        raise

def run_client(node_address, action, *args):
    with grpc.insecure_channel(node_address) as channel:
        stub = raft_pb2_grpc.RaftStub(channel)
        logging.info(f"Client connected to {node_address}")

        if action == 'request_vote':
            term, candidate_id, last_log_index, last_log_term = map(int, args)
            response = request_vote(stub, term, candidate_id, last_log_index, last_log_term)
            print(f"RequestVote response: term={response.term}, voteGranted={response.voteGranted}")
        
        elif action == 'set_peers':
            peers = list(map(int, args))
            response = set_peers(stub, peers)
            print(f"SetPeers response: success={response.success}, message={response.message}")

        elif action == 'append_entries':
                term = int(args[0])
                leader_id = args[1]
                prev_log_index = int(args[2])
                prev_log_term = int(args[3])
                leader_commit = int(args[-1])

                # Commands are the remaining arguments after the header fields
                commands = args[4:-1]

                response = append_entries(
                    stub, term, leader_id, prev_log_index, prev_log_term, commands, leader_commit
                )
                print(f"AppendEntries response: term={response.term}, success={response.success}")
        elif action == 'append_commands':
                # Commands are the remaining arguments after the header fields
                commands = list(args[0:])
                print(commands)

                # Đang chờ viết Giao Thức
                response = append_commands(stub, commands)
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
