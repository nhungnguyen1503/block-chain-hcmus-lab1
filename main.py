from peer import run_peer
import multiprocessing

if __name__ == "__main__":
    peers = [
        {"id": 1, "port": 5001, "is_byzantine": False},
        {"id": 2, "port": 5002, "is_byzantine": False},
        {"id": 3, "port": 5003, "is_byzantine": True},
        {"id": 4, "port": 5004, "is_byzantine": False},
        {"id": 5, "port": 5005, "is_byzantine": False},
    ]

    processes = []
    for peer in peers:
        # Tạo danh sách các peer khác
        other_peers = [(p["id"], p["port"]) for p in peers if p["id"] != peer["id"]]

        # Truyền danh sách này vào hàm `run_peer`
        process = multiprocessing.Process(
            target=run_peer, args=(peer["id"], peer["port"], other_peers, peer["is_byzantine"])
        )
        process.start()
        processes.append(process)

    for process in processes:
        process.join()
