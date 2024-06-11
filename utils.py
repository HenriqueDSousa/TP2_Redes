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
        chksum = self.compute_checksum(self.data)
        header = struct.pack(
            "!4s4sHHBB",
            self.SYNC_PATTERN,
            self.SYNC_PATTERN,
            chksum,
            length,
            self.frame_id,
            self.flags,
        )
        data_bytes = struct.pack(">" + str(length) + "s", self.data)

        self.frame = header + data_bytes

        return self.frame

    @staticmethod
    def decode_frame(data):
        if len(data) < DCCNETFrame.HEADER_SIZE:
            raise ValueError("Empty data")

        sync_pattern, chksum, length, frame_id, flags = struct.unpack(
            "!8sHHBB", data[: DCCNETFrame.HEADER_SIZE]
        )

        payload = data[DCCNETFrame.HEADER_SIZE :]
        print(sync_pattern, DCCNETFrame.SYNC_PATTERN * 2)
        if sync_pattern != DCCNETFrame.SYNC_PATTERN * 2:
            raise ValueError("Invalid sync pattern")

        if length != len(payload):
            raise ValueError("Invalid length")
        
        if frame_id < 0 or frame_id > 1:
            raise ValueError("Invalid frame ID")
        
        if chksum != DCCNETFrame.compute_checksum(data[DCCNETFrame.HEADER_SIZE :]):
            raise ValueError("Checksum verification failed")

        return frame_id, flags, chksum, payload

    @staticmethod
    def compute_checksum(data):
        checksum = sum(data) & 0xFFFF
        return checksum
