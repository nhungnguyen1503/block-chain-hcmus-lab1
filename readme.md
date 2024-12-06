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
#Chạy Mạng RAFT 5 nodes
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

```SET PEERS cho phân mảnh mạng
python client.py localhost:50051 set_peers 50052 50053 50053 50054 50055
```

```Client gửi tập command đến Server (Leader).
Mô tả: Đưa "set x 10" "delete y" vào list() và gửi nó  cho Server (Leader), nhận về success(thành công hoặc thất bại).

raft_pb2.AppendCommandRequest(
    commands =[]
)
raft_pb2.AppendCommandResponse(
    term=term,
    leaderId=leader_id,
    success = true/false
)


python client.py localhost:50051 append_commands "set x 10" "delete y"
```
