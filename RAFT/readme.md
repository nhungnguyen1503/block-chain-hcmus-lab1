```
pip install grpcio grpcio-tools
```

```
#Tạo Mã Python từ File .proto
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. raft.proto
```

//// thời gian time out cho việc bầu cử đang set là khoảng 7s

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

````
# Tạo Phân Mảnh Mạng: 2 Mảnh
-----Mạng 1:
python raft.py 1 50051 50052 50053
python raft.py 2 50052 50051 50053
python raft.py 3 50053 50051 50052

-----Mạng 2:
python raft.py 4 50054 50055
python raft.py 5 50055 50054


```SET PEERS cho phân mảnh mạng. Gửi danh sách các port mới cho tất cả các port có trong danh sách.

``` Hợp 2 mạng lại thành 1
python client.py localhost:50051 set_peers 50051 50052 50053 50054 50055

``` Cắt mạng thành 2 mạng
python client.py localhost:50051 set_peers 50051 50052 50053
python client.py localhost:50051 set_peers 50054 50055
````

```

```

.venv\scripts\activate

````

python client.py localhost:50053 get_status
=> Kết quả:
INFO:root:Client connected to localhost:50053
GetStatus response: term=1, state=leader



```Client gửi tập command đến Server (Leader). Gửi command đến cho Leader (50051)

python client.py localhost:50051 append_commands "set x 10" "delete y"
python client.py localhost:50054 append_commands "set y 150" "delete z"

````
