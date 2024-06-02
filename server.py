import socket
import struct
import threading
from utils import DCCNETFrame

# Constants
SYNC = 0xDCC023C2
SYNC_BYTES = struct.pack('!I', SYNC)
ACK_FLAG = 0x80
END_FLAG = 0x40
PORT = 8000
INPUT_FILE = "input_file.txt"
OUTPUT_FILE = "output_file.txt"

# Frame format:
# SYNC(32) | SYNC(32) | chksum(16) | length(16) | ID(8) | flags(8) | DATA(--)

# Helper function to calculate the Internet checksum
# def internet_checksum(data) -> int:
#     if len(data) % 2:
#         data += b'\x00'
#     checksum = sum(struct.unpack("!%dH" % (len(data) // 2), data))
#     checksum = (checksum >> 16) + (checksum & 0xffff)
#     checksum += checksum >> 16
#     return ~checksum & 0xffff

# Frame parsing function
# def parse_frame(frame):
#     sync_1, sync_2 checksum, length, frame_id, flags = struct.unpack('!IHHHB', frame[:11])
#     data = frame[11:]
#     if sync_1 != SYNC or sync_2 != SYNC:
#         raise ValueError("Invalid SYNC")
#     if internet_checksum(frame[:10] + data) != 0:
#         raise ValueError("Checksum error")
#     return length, frame_id, flags, data

# Receiver implementation
class DCCNETReceiver:
    def __init__(self, port):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(port)
        self.lock = threading.Lock()
        self.last_received_id = None
        self.last_received_checksum = None

    def send_ack(self, frame_id):
        ack_frame = DCCNETFrame(b'', frame_id, ACK_FLAG)
        self.sock.sendto(ack_frame.to_bytes(), self.remote_address)

    def receive_frame(self):
        while True:
            frame, addr = self.sock.recvfrom(1024)
            self.remote_address = addr
            try:
                length, frame_id, flags, data = DCCNETFrame.from_bytes(frame)
                if frame_id == self.last_received_id and DCCNETFrame.compute_checksum(frame[:10] + data) == self.last_received_checksum:
                    # Retransmission detected, resend ACK
                    self.send_ack(frame_id)
                else:
                    # New frame received, process it
                    self.last_received_id = frame_id
                    self.last_received_checksum = DCCNETFrame.compute_checksum(frame[:10] + data)
                    print(f"Received data: {data.decode()}")
                    # Send ACK
                    self.send_ack(frame_id)
            except ValueError as e:
                print(f"Frame error: {e}")

    def start(self):
        threading.Thread(target=self.receive_frame, daemon=True).start()

def server(port : str, input_file : str, output_file : str) -> None:
    PORT = int(port)
    INPUT_FILE = input_file
    OUTPUT_FILE = output_file

# Example usage
if __name__ == "__main__":
    # receiver = DCCNETReceiver(('localhost', PORT))
    # receiver.start()
    # while True:
    #     pass  # Keep the main thread running
    dcc_frame = DCCNETFrame(b'dcc023c2dcc023c2faef0004000001020304')
    print(dcc_frame.data)
    print(dcc_frame.to_bytes(), len(dcc_frame.to_bytes()))
    print(DCCNETFrame.from_bytes(dcc_frame.data))
    

