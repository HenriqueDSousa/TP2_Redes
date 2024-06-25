import struct

ACK_FLAG = b'\x80'
END_FLAG = b'\x40'
RST_FLAG = b'\x20'

def bitwise_and(byte1, byte2):
    return int.from_bytes(byte1, byteorder="big") & int.from_bytes(byte2, byteorder="big")

class DCCNETFrame:
    SYNC_PATTERN = b'\xdc\xc0\x23\xc2'
    SYNC_BYTES = b'\xdc\xc0\x23\xc2'
    HEADER_SIZE = 15 # Bytes

    def __init__(self, data=b"", frame_id=0, flags=b'\x00'):
        self.data = data
        self.frame_id = frame_id
        self.flags = flags

    def build_frame(self):
        length = len(self.data)
        temp_header = struct.pack(
            "!4s4sHHHs",
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
            "!4s4sHHHs",
            self.SYNC_PATTERN,
            self.SYNC_PATTERN,
            chksum,
            length,
            self.frame_id,
            self.flags,
        )
        # print(f"chksum={hex(chksum)}\tlength={length}\tid={self.frame_id}\tflags={hex(self.flags)}\tdata={self.data}\n")
        self.frame = header + data_bytes

        return self.frame

    @staticmethod
    def decode_frame(data):
        
        # print(data[:8], data[8:10], data[10:12], data[12:14], data[15])
        sync_pattern, chksum, length, frame_id, flags = struct.unpack(
            "!8sHHHs", data[: DCCNETFrame.HEADER_SIZE]
        )
        

        payload = data[DCCNETFrame.HEADER_SIZE:DCCNETFrame.HEADER_SIZE + length]

        if sync_pattern != DCCNETFrame.SYNC_PATTERN * 2:
            raise ValueError("Invalid sync pattern")

        if length != len(payload):
            raise ValueError("Invalid length")
        
        if length > 0 and bitwise_and(flags, ACK_FLAG):
            raise ValueError("ACK flag should not be set for data frames")
        
        if bitwise_and(flags, ACK_FLAG) and bitwise_and(flags, END_FLAG):
            raise ValueError("ACK and END flags cannot be set simultaneously")

        temp_frame = data[:8] + struct.pack("!H", 0) + data[10:]

        if chksum != (DCCNETFrame.compute_checksum(temp_frame)):
            raise ValueError("Checksum verification failed")

        payload_str = payload.decode('ascii', errors='ignore')

        return chksum, length, frame_id, flags, payload_str

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