import struct


class DCCNETFrame:
    SYNC_PATTERN = b'\xdc\xc0\x23\xc2'
    HEADER_SIZE = 14 # Bytes
    ACK_FLAG = b'\x80'
    END_FLAG = b'\x40'
    RST_FLAG = b'\x20'

    def __init__(self, data=b"", frame_id=0, flags=0):
        self.data = data
        self.frame_id = frame_id
        self.flags = flags

    def build_frame(self):
        length = len(self.data)
        temp_header = struct.pack(
            "!4s4sHHBB",
            self.SYNC_PATTERN,
            self.SYNC_PATTERN,
            0,
            length,
            self.frame_id,
            self.flags,
        )
        data_bytes = struct.pack(">" + str(length) + "s", self.data)
        temp_frame = temp_header + data_bytes

        chksum = self.compute_checksum(temp_frame)
        header = struct.pack(
            "!4s4sHHBB",
            self.SYNC_PATTERN,
            self.SYNC_PATTERN,
            chksum,
            length,
            self.frame_id,
            self.flags,
        )

        self.frame = header + data_bytes

        return self.frame

    @staticmethod
    def decode_frame(data):
        if len(data) < DCCNETFrame.HEADER_SIZE:
            raise ValueError("Empty data")

        sync_pattern, chksum, length, frame_id, flags = struct.unpack(
            "!8sHHBB", data[: DCCNETFrame.HEADER_SIZE]
        )

        payload = data[DCCNETFrame.HEADER_SIZE:].decode("utf-8")

        if sync_pattern != DCCNETFrame.SYNC_PATTERN * 2:
            raise ValueError("Invalid sync pattern")

        if length != len(payload):
            raise ValueError("Invalid length")
        
        if frame_id < 0 or frame_id > 1:
            raise ValueError("Invalid frame ID")
        
        if chksum != DCCNETFrame.compute_checksum(data):
            print(chksum, DCCNETFrame.compute_checksum(data))
            raise ValueError("Checksum verification failed")

        return frame_id, flags, chksum, payload

    @staticmethod
    def compute_checksum(data):
        data = data[:8] + b'\x00\x00' + data[10:]
        checksum = 0
        # Process each pair of bytes
        for i in range(0, len(data), 2):
            if i + 1 < len(data):
                pair = (data[i] << 8) + data[i + 1]
            else:
                pair = data[i] << 8
            checksum += pair
            # Keep it to 16 bits
            checksum = (checksum & 0xFFFF) + (checksum >> 16)
        # Final wrap-around carry addition
        checksum = (checksum & 0xFFFF) + (checksum >> 16)
        # One's complement
        checksum = ~checksum & 0xFFFF
        return checksum