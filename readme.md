```
pip install grpcio grpcio-tools
```

```
#Tạo Mã Python từ File .proto
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. raft.proto
```

```
#Chạy Mạng RAFT
python raft.py 2 50052 50051 50053
python raft.py 3 50053 50052 50051
python raft.py 1 50051 50052 50053
```

```
#Thực hiện RequestVote từ Client
python raft_client.py localhost:50051 1 node1 0 0
```

```
.venv\scripts\activate
```

```
python raft_client.py localhost:50053 get_status
INFO:root:Client connected to localhost:50053
GetStatus response: term=1, state=leader
```

python raft_client.py localhost:50052 request_vote 1 2 0 0
python raft_client.py localhost:50051 append_entries 1 1 0 0 "[{'term': 1, 'command': 'set x 10'}]" 0
