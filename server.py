import socket
import struct
import threading
from utils import DCCNETFrame

# Constants
SYNC = b'\xdc\xc0\x23\xc2'
SYNC_BYTES = struct.pack("!4s", SYNC)
ACK_FLAG = 0x80
END_FLAG = 0x40
PORT = 8000
INPUT_FILE = "input_file.txt"
OUTPUT_FILE = "output_file.txt"

# Frame format:
# SYNC(32) | SYNC(32) | chksum(16) | length(16) | ID(8) | flags(8) | DATA(--)

class DCCNETReceiver:
    def __init__(self, port):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(port)
        self.lock = threading.Lock()
        self.last_received_id = None
        self.last_received_checksum = None

    def send_ack(self, frame_id):
        ack_frame = DCCNETFrame(b"", frame_id, ACK_FLAG)
        self.sock.sendto(ack_frame.to_bytes(), self.remote_address)

    # def send_end(seld, frame_id):

    def receive_frame(self):
        while True:
            frame, addr = self.sock.recvfrom(1024)
            self.remote_address = addr
            try:
                frame_id, _, chksum, data = DCCNETFrame.decode_frame(frame)
                if (frame_id != self.last_received_id or self.last_received_checksum != chksum):
                    self.last_received_id = frame_id
                    
                    print(f"Received data:", data)
                self.send_ack(frame_id)
            except ValueError as e:
                print(f"Frame error: {e}")

    def start(self):
        threading.Thread(target=self.receive_frame, daemon=True).start()


def server(port: str, input_file: str, output_file: str) -> None:
    global PORT
    global INPUT_FILE
    global OUTPUT_FILE
    PORT = int(port)
    INPUT_FILE = input_file
    OUTPUT_FILE = output_file


# Example usage
if __name__ == "__main__":
    # receiver = DCCNETReceiver(('localhost', PORT))
    # receiver.start()
    # while True:
    #     pass  # Keep the main thread running
    dcc_frame = DCCNETFrame(b"01020304")
    print(dcc_frame.data)
    print(dcc_frame.build_frame())
    print(dcc_frame.decode_frame(dcc_frame.frame))
