#!/usr/bin/python3

import socket
import struct
import sys
import time
import threading
import hashlib
from utils import DCCNETFrame

# gas=2021031912:1:a3278d1a43ae8e5fdbe4de24a45f9bbf545e4202a1caa9b1808530f3d6bc1932+6cf2d2cdbfb0678d4db0a2e1337caf56e915769acf91b68e67cd8388e24e4169

SYNC = 0xDCC023C2
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
        print(f"SENDING:")
        end_frame = DCCNETFrame(b"", frame_id, END_FLAG)
        self.sock.sendto(end_frame.build_frame(), (self.addr, self.port))

    def send_ack(self, frame_id):
        print(f"SENDING:")
        ack_frame = DCCNETFrame(b"", frame_id, ACK_FLAG)
        self.sock.sendto(ack_frame.build_frame(), (self.addr, self.port))

    def send_rst(self, error_message):
        print(f"SENDING:")
        rst_frame = DCCNETFrame(error_message.encode(), frame_id=65535, flags=RST_FLAG)
        self.sock.sendto(rst_frame.build_frame(), (self.addr, self.port))
        self.sock.close()

    def send_frame(self, data, frame_id, flags):
        print(f"SENDING:")
        frame = DCCNETFrame(data, frame_id=frame_id, flags=flags)
        self.sock.sendto(frame.build_frame(), (self.addr, self.port))

    def receive_ack(self):
            try:
                sync1, addr = self.sock.recvfrom(4)
                
                if sync1 != DCCNETFrame.SYNC_BYTES:
                    raise ValueError("Invalid sync pattern")

                sync2, addr = self.sock.recvfrom(4)

                if sync2 != DCCNETFrame.SYNC_BYTES:
                    raise ValueError("Invalid sync pattern")
                
                header_data, addr = self.sock.recvfrom(7)
                
                chksum, length, frame_id, flags = struct.unpack("!HHHB", header_data)

                data, addr = self.sock.recvfrom(length)

                payload = data.decode('ascii', errors='ignore')

                print(f"RECEIVING ACK:")
                print(f"chksum={hex(chksum)}\tlength={length}\tid={frame_id}\tflags={hex(flags)}\tdata={payload}\n")
                if flags == ACK_FLAG:
                    return True
                else:
                    return False
                
            except socket.timeout:
                print("Timeout Error")
                
        
    def receive_frame(self):
        try:
            sync1, addr = self.sock.recvfrom(4)

            if sync1 != DCCNETFrame.SYNC_BYTES:
                raise ValueError("Invalid sync pattern")

            sync2, addr = self.sock.recvfrom(4)
            
            if sync2 != DCCNETFrame.SYNC_BYTES:
                raise ValueError("Invalid sync pattern")
            
            header_data, addr = self.sock.recvfrom(7)
            
            chksum, length, frame_id, flags = struct.unpack("!HHHB", header_data)

            data, addr = self.sock.recvfrom(length)

            payload = data.decode('ascii', errors='ignore')

            if length != len(payload):
                raise ValueError("Invalid length")

            temp_frame = struct.pack(
                "!4s4sHHHB"+str(length)+"s",
                sync1,
                sync2,
                0,
                length,
                frame_id,
                flags,
                payload.encode()
            )

            if chksum != (DCCNETFrame.compute_checksum(temp_frame)):
                raise ValueError("Checksum verification failed")

            print(f"RECEIVING FRAME:")
            print(f"chksum={hex(chksum)}\tlength={length}\tid={frame_id}\tflags={hex(flags)}\tdata={payload}\n")
            return chksum, length, frame_id, flags, payload
    
        except socket.timeout:
            print("Timeout Error")
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
        chksum, length, frame_id_received, flags, payload = transmitter.receive_frame()

        # Sending ACK
        transmitter.send_ack(frame_id=frame_id_received)

        if flags == 0:
            continue
        
        if flags == END_FLAG:
            print("Transmission ended by server.")
            transmitter.sock.close()
            break

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

