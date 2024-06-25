import socket
import struct
import threading
from utils import DCCNETFrame

# Constants
SYNC = b'\xdc\xc0\x23\xc2'
SYNC_BYTES = struct.pack("!4s", SYNC)
ACK_FLAG = 0x80
END_FLAG = 0x40
RST_FLAG = 0x20
PORT = 8000
OUTPUT_FILE = "output_file.txt"

# Frame format:
# SYNC(32) | SYNC(32) | chksum(16) | length(16) | ID(16) | flags(8) | DATA(--)

class DCCNETReceiver:

    def __init__(self, port):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(port)
        self.last_received_id = None
        self.last_received_checksum = None

    def send_ack(self, frame_id):
        ack_frame = DCCNETFrame(b"", frame_id, ACK_FLAG)
        self.sock.sendto(ack_frame.build_frame(), self.remote_address)

    def send_rst(self, error_message):
        rst_frame = DCCNETFrame(error_message.encode(), frame_id=65535, flags=RST_FLAG)
        self.sock.sendto(rst_frame.build_frame(), (self.addr, self.port))
        self.sock.close()


    def receive_frame(self):

        while True:

            frame, addr = self.sock.recvfrom(4096)
            self.remote_address = addr

            try:
                chksum, length, frame_id, flags, payload = DCCNETFrame.decode_frame(frame)
                print(frame_id, flags, chksum, payload)

                if self.last_received_id == frame_id and self.last_received_checksum == chksum:
                    print("Recieved duplicated package, retransmitting....")

                with open(OUTPUT_FILE, "a") as f:
                    f.write(payload)
                    if flags == END_FLAG:
                        f.write("\n")

                self.send_ack(frame_id)

            except ValueError as e:
                print(f"Frame error: {e}, waiting retransmission...")

    def start(self):
        threading.Thread(target=self.receive_frame, daemon=True).start()


def run_server(port: str, output_file: str) -> None:
    global PORT
    global OUTPUT_FILE
    PORT = int(port)
    OUTPUT_FILE = output_file
    
    receiver = DCCNETReceiver(("127.0.0.1", PORT))
    receiver.start()
    print("Listening...")
    while True:
        pass

# Example usage
if __name__ == "__main__":
    receiver = DCCNETReceiver(("127.0.0.1", PORT))
    receiver.start()
    print("Listening...")
    while True:
        pass