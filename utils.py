import struct

class DCCNETFrame:
    SYNC_PATTERN = b'\xdc\xc0\x23\xc2'
    HEADER_SIZE = 112
    
    def __init__(self, data=b'', frame_id=0, flags=0):
        self.data = data
        self.frame_id = frame_id
        self.flags = flags
        
    def to_bytes(self):
        length = len(self.data)
        chksum = self.compute_checksum(self.data)
        header = struct.pack('>8s8sHHBB', self.SYNC_PATTERN, self.SYNC_PATTERN, chksum, length, self.frame_id, self.flags)
        data_bytes = struct.pack('>' + str(length) + 's', self.data)

        frame = header + data_bytes
        return frame
    
    @staticmethod
    def from_bytes(data):
        if len(data) < DCCNETFrame.HEADER_SIZE:
            raise ValueError("Empty data")
            
        sync_pattern, length, frame_id, flags = struct.unpack('>8sHBB', data[:DCCNETFrame.HEADER_SIZE])
        payload = data[DCCNETFrame.HEADER_SIZE:]
        
        if sync_pattern != DCCNETFrame.SYNC_PATTERN * 2:
            raise ValueError("Invalid sync pattern")
        
        checksum = struct.unpack('>H', payload[:2])[0]
        if checksum != DCCNETFrame.compute_checksum(data[DCCNETFrame.HEADER_SIZE:]):
            raise ValueError("Checksum verification failed")
        
        return DCCNETFrame(payload[2:], frame_id, flags)
    
    @staticmethod
    def compute_checksum(data):
        checksum = sum(data) & 0xffff
        return checksum 
