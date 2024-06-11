import socket
import time
import struct
import threading
from utils import DCCNETFrame


SYNC = b'\xdc\xc0\x23\xc2'
SYNC_BYTES = struct.pack("!4s", SYNC)
ACK_FLAG = 0x80
END_FLAG = 0x40
RST_FLAG = 0x20
PORT = 8000
INPUT_FILE = "input_file.txt"
OUTPUT_FILE = "output_file.txt"

class DCCNETTransmitter:
    def __init__(self, addr, port):
        self.port = port
        self.addr = addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_ack(self, frame_id):
        ack_frame = DCCNETFrame(b"", frame_id, ACK_FLAG)
        self.sock.sendto(ack_frame.to_bytes(), (self.addr, self.port))


    def send_frame(self, data, frame_id, flags=0):
        frame = DCCNETFrame(data, frame_id=frame_id, flags=flags)
        self.sock.sendto(frame.build_frame(), (self.addr, self.port))
        
    def receive_ack(self):
       
            data, addr = self.sock.recvfrom(1024)
            frame_id, flags, chksum, payload = DCCNETFrame.decode_frame(data)
            if flags == ACK_FLAG:
                return True
            else:
                return False
                
    def start(self):
        threading.Thread(target=self.receive_frame, daemon=True).start()


def main():

    # Create a socket object
    port = int(PORT)
    addr = "127.0.0.1"
    transmitter = DCCNETTransmitter(addr=addr, port=port)

    # Initialize frame_id to 0
    frame_id = 0
    last_received_frame_id = -1

    # Send a frame with input data
    for line in open(INPUT_FILE, "r"):
        print(line)

        while True:
            transmitter.send_frame(data=line.encode(), frame_id=frame_id, flags=0)
            if (transmitter.receive_ack()):
                break
            else:
                print("Retransmitting frame")
                time.sleep(1)
        
        frame_id = 1 - frame_id
    
       


