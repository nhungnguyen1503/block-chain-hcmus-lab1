import multiprocessing
from peer import run_peer

if __name__ == "__main__":
    # Định nghĩa cấu hình cho từng peer
    peer_configs = [
        ("Peer1", 5001, [("localhost", 5002), ("localhost", 5003), ("localhost", 5004), ("localhost", 5005)]),
        ("Peer2", 5002, [("localhost", 5001), ("localhost", 5003), ("localhost", 5004), ("localhost", 5005)]),
        ("Peer3", 5003, [("localhost", 5001), ("localhost", 5002), ("localhost", 5004), ("localhost", 5005)]),
        ("Peer4", 5004, [("localhost", 5001), ("localhost", 5002), ("localhost", 5003), ("localhost", 5005)]),
        ("Peer5", 5005, [("localhost", 5001), ("localhost", 5002), ("localhost", 5003), ("localhost", 5004)]),
    ]

    # Khởi động mỗi peer trong một process
    processes = []
    for peer_name, port, peer_list in peer_configs:
        process = multiprocessing.Process(target=run_peer, args=(peer_name, port, peer_list))
        process.start()
        processes.append(process)

    # Chờ các process hoàn thành
    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        print("Shutting down all peers...")
        for process in processes:
            process.terminate()
