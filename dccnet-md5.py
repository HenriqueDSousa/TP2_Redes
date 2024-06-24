#!/usr/bin/python3

import socket
import struct
import sys
import time
import threading
import hashlib
from utils import DCCNETFrame

# gas=2021031912:1:a3278d1a43ae8e5fdbe4de24a45f9bbf545e4202a1caa9b1808530f3d6bc1932+6cf2d2cdbfb0678d4db0a2e1337caf56e915769acf91b68e67cd8388e24e4169

SYNC = b'\xdc\xc0\x23\xc2'
SYNC_BYTES = struct.pack("!4s", SYNC)
ACK_FLAG = 0x80
END_FLAG = 0x40
RST_FLAG = 0x20

class DCCNETTransmitter:
    def __init__(self, addr, port):
        self.port = port
        self.addr = addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)

    def send_end(self, frame_id):
        print(f"SENDING:\n  id={frame_id} flags={hex(END_FLAG)} data=\n")
        end_frame = DCCNETFrame(b"", frame_id, END_FLAG)
        self.sock.sendto(end_frame.build_frame(), (self.addr, self.port))

    def send_ack(self, frame_id):
        ack_frame = DCCNETFrame(b"", frame_id, ACK_FLAG)
        print(f"SENDING:\n  id={frame_id} flags={hex(ACK_FLAG)} data=\n")
        self.sock.sendto(ack_frame.build_frame(), (self.addr, self.port))

    def send_rst(self, error_message):
        rst_frame = DCCNETFrame(error_message.encode(), frame_id=65535, flags=RST_FLAG)
        self.sock.sendto(rst_frame.build_frame(), (self.addr, self.port))
        self.sock.close()

    def send_frame(self, data, frame_id, flags):
        frame = DCCNETFrame(data, frame_id=frame_id, flags=flags)
        print(f"SENDING:\n  id={frame_id} flags={hex(flags)} data={data}\n")
        self.sock.sendto(frame.build_frame(), (self.addr, self.port))

    def receive_ack(self):
            try:
                data, addr = self.sock.recvfrom(4096)
                frame_id, flags, chksum, payload = DCCNETFrame.decode_frame(data)
                print(f"RECEIVING ACK:\n  id={frame_id} chksum={hex(chksum)} flags={hex(flags)} data={payload}\n")
                if flags == ACK_FLAG:
                    return True
                else:
                    return False
                
            except socket.timeout:
                print("Timeout Error")
                
        
    def receive_frame(self):
        try:
            data, addr = self.sock.recvfrom(4096)
            print(data)
            frame_id, flags, chksum, payload = DCCNETFrame.decode_frame(data)
            print(f"RECEIVING FRAME:\n  id={frame_id} chksum={hex(chksum)} flags={hex(flags)} data={payload}\n")
            return frame_id, flags, payload
        except socket.timeout:
            return None, None, None
    

def compute_md5(data):
    return hashlib.md5(data.encode()).hexdigest()


def main(ip, port, gas):
    
    transmitter = DCCNETTransmitter(addr=ip, port=int(port))

    try:
        transmitter.sock.connect((ip, int(port)))
    except socket.error: 
        print("Connection error")
        exit(1)

    # Send GAS 
    frame_id = 0
    transmitter.send_frame(data=(gas + '\n').encode(), frame_id=frame_id, flags=0)

    # Fetching ACK
    for _ in range(16): 
        if not transmitter.receive_ack():
            print("Retransmitting GAS")
            transmitter.send_frame(data=(gas + '\n').encode(), frame_id=frame_id, flags=0)
            time.sleep(1)
        else:
            break
    
    frame_id = 1 - frame_id
    
    # Receive and process data from server
    while True:
        frame_id_received, flags, payload = transmitter.receive_frame()

        if flags is None:
            continue
        
        if flags == END_FLAG:
            print("Transmission ended by server.")
            transmitter.send_ack(frame_id_received)
            transmitter.sock.close()
            break
        
        # Sending ACK
        transmitter.send_ack(frame_id=frame_id_received)

        data_lines = payload.decode().split('\n')
        for line in data_lines:
            if line:
                md5_checksum = compute_md5(line)
                transmitter.send_frame(data=(md5_checksum + '\n').encode(), frame_id=frame_id, flags=0)
                while not transmitter.receive_ack():
                    print("Retransmitting checksum")
                    transmitter.send_frame(data=(md5_checksum + '\n').encode(), frame_id=frame_id, flags=0)
                    time.sleep(1)
                frame_id = 1 - frame_id
    


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: ./dccnet-md5 <IP>:<PORT> <GAS>")
        sys.exit(1)
    
    ip_port = sys.argv[1].split(':')
    ip = ip_port[0]
    port = ip_port[1]
    gas = sys.argv[2]
    
    main(ip, port, gas)

