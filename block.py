import hashlib

class Block:
    def __init__(self, previous_hash, blockheight):
        self.previous_hash = previous_hash
        self.blockheight = blockheight
        self.blockhash = self.calculate_hash()

    def calculate_hash(self):
        # Tạo hash bằng cách kết hợp `previous_hash` và `blockheight`
        return hashlib.sha256(f"{self.previous_hash}{self.blockheight}".encode()).hexdigest()

    def to_dict(self):
        return {
            "previous_hash": self.previous_hash,
            "blockhash": self.blockhash,
            "blockheight": self.blockheight,
        }
