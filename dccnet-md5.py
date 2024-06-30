#!/usr/bin/python3

import socket
import struct
import sys
import time
import threading
import hashlib
from utils import DCCNETFrame

SYNC = 0xDCC023C2
ACK_FLAG = b'\x80'
END_FLAG = b'\x40'
RST_FLAG = b'\x20'
DEFAULT_FLAG = b'\x00'

class DCCNETTransmitter:
    def __init__(self, addr, port):
        self.port = port
        self.addr = addr

        
        try:
            
            self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((addr, port))
        except socket.error: 
            print("IPv6 not available")

            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(10)
                self.sock.connect((addr, port))

            except socket.error:
                print("Connection not available")
                exit(1)

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
        rst_frame = DCCNETFrame(error_message.encode('ASCII'), frame_id=65535, flags=RST_FLAG)
        self.sock.sendto(rst_frame.build_frame(), (self.addr, self.port))
        self.sock.close()

    def send_frame(self, data, frame_id, flags):
        print(f"SENDING:")
        frame = DCCNETFrame(data, frame_id=frame_id, flags=flags)
        self.sock.sendto(frame.build_frame(), (self.addr, self.port))

    def receive_ack(self):
            try:
                data, addr = self.sock.recvfrom(4096)

                sync_pattern = struct.unpack("!8s", data[:8])[0]
                
                if sync_pattern != DCCNETFrame.SYNC_PATTERN * 2:
                    data = resync(data)
                    print(data)
                    if data == None:
                        raise ValueError("Invalid sync pattern")


                chksum, length, frame_id, flags = struct.unpack(
                    "!HHHs", data[8:15]
                )
                
                payload = data[DCCNETFrame.HEADER_SIZE:DCCNETFrame.HEADER_SIZE + length]

                if sync_pattern != DCCNETFrame.SYNC_PATTERN * 2:
                    raise ValueError("Invalid sync pattern")

                if length != len(payload):
                    raise ValueError("Invalid length")

                temp_frame = data[:8] + struct.pack("!H", 0) + data[10:]

                if chksum != (DCCNETFrame.compute_checksum(temp_frame)):
                    print("Checksum verification failed")

                payload_str = payload.decode('ascii', errors='ignore')


                print(f"RECEIVING ACK:")
                print(f"chksum={hex(chksum)}\tlength={length}\tid={frame_id}\tflags={hex(flags[0])}\tdata={payload}\n")
                if flags == ACK_FLAG:
                    return True
                else:
                    return False
                
            except socket.timeout:
                print("Timeout Error")
                
        
    def receive_frame(self):

        try:
                
            data, addr = self.sock.recvfrom(4096)

            sync_pattern = struct.unpack("!8s", data[:8])[0]
            
            if sync_pattern != DCCNETFrame.SYNC_PATTERN * 2:
                data = resync(data)
                print(data)
                if data == None:
                    return None, None, None

            chksum, length, frame_id, flags = struct.unpack(
                "!HHHs", data[8:15]
            )
            
            payload = data[DCCNETFrame.HEADER_SIZE:DCCNETFrame.HEADER_SIZE + length]

            if length != len(payload):
                raise ValueError("Invalid length")

            temp_frame = data[:8] + struct.pack("!H", 0) + data[10:]

            if chksum != (DCCNETFrame.compute_checksum(temp_frame)):
                print("Checksum verification failed")

            payload_str = payload.decode('ascii', errors='ignore')

            print(f"RECEIVING FRAME:")
            print(f"chksum={hex(chksum)}\tlength={length}\tid={frame_id}\tflags={hex(flags[0])}\tdata={payload_str}\n")
            return chksum, length, frame_id, flags, payload_str
        
        except socket.timeout:
            print("Timeout Error")
            return None, None, None

def resync(data):
        sync_pattern_bytes = DCCNETFrame.SYNC_PATTERN * 2
        for i in range(1, len(data) - DCCNETFrame.HEADER_SIZE):
            if data[i:i + 8] == sync_pattern_bytes:
                return data[i:]
        return None


def compute_md5(data):
    return hashlib.md5(data.encode('ASCII')).hexdigest()


def main(ip, port, gas):
    
    transmitter = DCCNETTransmitter(addr=ip, port=int(port))
    

    # Send GAS 
    frame_id = 0
    transmitter.send_frame(data=(gas + '\n').encode('ASCII'), frame_id=frame_id, flags=DEFAULT_FLAG)

    # Fetching ACK
    for _ in range(16): 
        if not transmitter.receive_ack():
            print("Retransmitting GAS")
            transmitter.send_frame(data=(gas + '\n').encode('ASCII'), frame_id=frame_id, flags=DEFAULT_FLAG)
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
        
        if flags == RST_FLAG:
            print("Transmission error: received RST flag.")
            transmitter.send_frame(data =("Received RST flag\n").encode('ASCII'), frame_id=frame_id, flags=DEFAULT_FLAG )
            transmitter.sock.close()
            break    

        data_lines = payload.split('\n')

        # print(data_lines)
        for line in data_lines:
            if line:
                md5_checksum = compute_md5(line)
                transmitter.send_frame(data=(md5_checksum + '\n').encode('ASCII'), frame_id=frame_id, flags=DEFAULT_FLAG)
                
                for _ in range(16):
                    if not transmitter.receive_ack():
                        print("Retransmitting checksum")
                        transmitter.send_frame(data=(md5_checksum + '\n').encode('ASCII'), frame_id=frame_id, flags=DEFAULT_FLAG)
                        time.sleep(1)
                    else:
                        break
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

