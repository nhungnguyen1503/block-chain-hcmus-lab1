import argparse
from multiprocessing import Process
from peerServer import serve

def main():
    parser = argparse.ArgumentParser(description="Run a peer in the P2P network.")
    parser.add_argument("--port", type=int, required=True, help="Port to run the peer on.")
    parser.add_argument("--peers", type=str, nargs="*", default=[], help="List of peer addresses to connect to.")
    args = parser.parse_args()

    # Chạy máy chủ P2P
    serve(args.port, args.peers)

if __name__ == "__main__":
    main()