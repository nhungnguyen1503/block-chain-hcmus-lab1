```
pip install grpcio grpcio-tools
```

```
#Tạo Mã Python từ File .proto
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. raft.proto
```

```
#Chạy Mạng RAFT
python raft.py 1 50051 50052 50053
python raft.py 2 50052 50051 50053
python raft.py 3 50053 50052 50051
```

#Chạy Mạng RAFT 4 nodes
python raft.py 1 50051 50052 50053 50054
python raft.py 2 50052 50051 50053 50054
python raft.py 3 50053 50051 50052 50054
python raft.py 4 50054 50051 50052 50053

```
#Chạy Mạng RAFT 4 nodes
python raft.py 1 50051 50052 50053 50054 50055
python raft.py 2 50052 50051 50053 50054 50055
python raft.py 3 50053 50051 50052 50054 50055
python raft.py 4 50054 50051 50052 50053 50055
python raft.py 5 50055 50051 50052 50053 50054
```

#Thực hiện RequestVote từ Client
python client.py localhost:50051 1 node1 0 0

```

```

.venv\scripts\activate

```

```

python client.py localhost:50053 get_status
=> Kết quả:
INFO:root:Client connected to localhost:50053
GetStatus response: term=1, state=leader

```

python client.py localhost:50052 request_vote 1 2 0 0
python client.py localhost:50051 append_entries 1 1 0 0 1 "set x 10" 0
python client.py localhost:50051 append_entries 1 1 0 0 1 "set x 10" 2 "delete y" 0

```

python client.py localhost:50052 set_peers 50051 50053
