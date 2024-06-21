import sys
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
IP = "127.0.0.1"
PORT = 8000
INPUT_FILE = "input_file.txt"
OUTPUT_FILE = "output_file.txt"

class DCCNETTransmitter:
    def __init__(self, addr, port):
        self.port = port
        self.addr = addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(10)
        self.frame_id = 0

    def set_frame_id(self, frame_id):
        self.frame_id = frame_id

    def send_frame(self, data, frame_id, flags):
        frame = DCCNETFrame(data, frame_id=frame_id, flags=flags)
        self.sock.sendto(frame.build_frame(), (self.addr, self.port))

    def send_end(self, frame_id):
        end_frame = DCCNETFrame(b"", frame_id, END_FLAG)
        self.sock.sendto(end_frame.to_bytes(), (self.addr, self.port))
        
    def receive_ack(self):
            
            try:

                data, addr = self.sock.recvfrom(112)
                frame_id, flags, chksum, payload = DCCNETFrame.decode_frame(data)

                if self.frame_id == frame_id and flags == ACK_FLAG and len(payload) == 0: 
                    return True
                
                else:
                    return False
                
            except socket.timeout:
                return False
                
    def start(self):
        threading.Thread(target=self.receive_frame, daemon=True).start()


def main():

    transmitter = DCCNETTransmitter(addr=IP, port=PORT)

    transmitter.set_frame_id(0)

    # Send a frame with input data
    lines = list(open(INPUT_FILE, "r"))
    
    for i, line in enumerate(lines):
        print(line)
        flag = 0
        if i == len(lines) - 1:
            flag = END_FLAG 

        while True:
            transmitter.send_frame(data=line.encode(), frame_id=transmitter.frame_id, flags=flag)

            if transmitter.receive_ack():
                if flag == END_FLAG:
                    transmitter.sock.close()
                break
            else:
                print("Retransmitting frame")
                time.sleep(1)

        transmitter.set_frame_id(1 - transmitter.frame_id)
        
def client(ip: str, port: str, input_file: str, output_file: str) -> None:

    global IP
    global PORT
    global INPUT_FILE
    global OUTPUT_FILE
    IP = ip
    PORT = int(port)
    INPUT_FILE = input_file
    OUTPUT_FILE = output_file


if __name__ == "__main__":
    
    
    # dcc_frame = DCCNETFrame(b"01020304")
    # print(dcc_frame.data)
    # print(dcc_frame.build_frame())
    # print(dcc_frame.decode_frame(dcc_frame.frame))

    main()
       


