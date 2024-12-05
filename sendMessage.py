import argparse
from peerClient import send_message

def main():
    parser = argparse.ArgumentParser(description="Send a message to a peer.")
    parser.add_argument("--target", type=str, required=True, help="Target peer address (e.g., localhost:50051).")
    parser.add_argument("--sender", type=str, required=True, help="Name of the sender.")
    parser.add_argument("--message", type=str, required=True, help="Message to send.")
    args = parser.parse_args()

    # Gửi thông điệp
    send_message(args.target, args.sender, args.message)

if __name__ == "__main__":
    main()
