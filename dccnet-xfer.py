#!/usr/bin/python3

import sys
import time
import socket
import struct
import threading
from utils import DCCNETFrame, bitwise_and

# Constants
SYNC = b'\xdc\xc0\x23\xc2'
SYNC_BYTES = struct.pack("!4s", SYNC)
ACK_FLAG = b'\x80'
END_FLAG = b'\x40'
RST_FLAG = b'\x20'

class DCCNETXfer:
    def __init__(self, port, input_file, output_file, ip=None):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if ip is None:
            self.remote_address = None
            self.sock.bind(('', port))
        else:
            self.remote_address = (ip, port)
        self.last_received_id = None
        self.last_received_checksum = None
        self.frame_id = 0
        self.input_file = input_file
        self.output_file = output_file

        self.retransmission_counter_ack = 0
        self.retransmission_counter_data = 0
        self.input_lines = list(open(self.input_file, "r"))
        self.current_line = self.input_lines[0]
        self.line_index = 0
        self.current_flags = b'\x00'

        self.end_sent = False
        self.end_received = False

    def set_frame_id(self, frame_id):
        self.frame_id = frame_id

    def send_frame(self, data, frame_id, flags):
        print(f"Sending frame:\tlength={len(data)}\tid={frame_id}\tflags={flags}\tdata={data}")
        frame = DCCNETFrame(data, frame_id=frame_id, flags=flags)
        self.sock.sendto(frame.build_frame(), self.remote_address)

    def send_end(self, frame_id):
        print(f"Sending END flag for frame_id: {frame_id}")
        end_frame = DCCNETFrame(b"", frame_id, END_FLAG)
        self.sock.sendto(end_frame.to_bytes(), self.remote_address)

    def send_ack(self, frame_id):
        print(f"Sending ACK flag for frame_id: {frame_id}")
        ack_frame = DCCNETFrame(b"", frame_id, ACK_FLAG)
        self.sock.sendto(ack_frame.build_frame(), self.remote_address)

    def send_rst(self, error_message):
        print(f"Sending RST flag")
        rst_frame = DCCNETFrame(error_message.encode(), frame_id=65535, flags=RST_FLAG)
        self.sock.sendto(rst_frame.build_frame(), self.remote_address)
        self.sock.close()

    def send_data(self):
        while True:
            self.send_frame(data=self.current_line.encode(), frame_id=self.frame_id, flags=self.current_flags)

            if bitwise_and(self.current_flags, END_FLAG):
                self.end_sent = True
                return
            time.sleep(1)

    def run(self):

        passive_server = True

        if self.remote_address != None:
            passive_server = False
            threading.Thread(target=self.send_data, daemon=True).start()

        while True:

            frame, addr = self.sock.recvfrom(4096)

            if self.remote_address == None and passive_server:
                self.remote_address = addr
                threading.Thread(target=self.send_data, daemon=True).start()

            try:

                chksum, length, frame_id, flags, payload = DCCNETFrame.decode_frame(frame)

                if self.last_received_id == frame_id and self.last_received_checksum == chksum:
                    print("Recieved duplicated package")
                    if self.retrassmission_counter_ack > 16:
                        self.send_rst(b"Too many retransmissions")
                    self.retrassmission_counter_ack += 1

                else:
                    if not bitwise_and(flags, ACK_FLAG) and not self.end_received:

                        self.retrassmission_counter_ack = 0
                        print(f"Received frame:\tchksum={chksum}\tlength={length}\tid={frame_id}\tflags={flags}\tdata={payload}")
                        with open(self.output_file, "a") as f:
                            f.write(payload)
                            if bitwise_and(flags, END_FLAG):
                                self.end_received = True
                                f.write("\n")

                        self.send_ack(frame_id)

                    else:
                        self.line_index += 1
                        if self.line_index < len(self.input_lines):
                            self.current_line = self.input_lines[self.line_index]
                            if self.line_index == len(self.input_lines) - 1:
                                self.current_flags = END_FLAG
                        self.set_frame_id(1 - self.frame_id)


            except ValueError as e:
                print(f"Frame error: {e}, waiting retransmission...")
            
            if self.end_received and self.end_sent:
                print("File transmission ended")
                break

def usage() -> None:
    print("Client: ./dccnet-xfer -c <IP>:<PORT> <INPUT> <OUTPUT>")
    print("Server: ./dccnet-xfer -s <PORT> <INPUT> <OUTPUT>")


def main():
    if len(sys.argv) < 5:
        usage()
        sys.exit(1)

    mode = sys.argv[1]
    if mode == '-s':
        print("Passive server running...")
        port = int(sys.argv[2])
        input_file = sys.argv[3]
        output_file = sys.argv[4]
        server = DCCNETXfer(port, input_file, output_file)
        server.run()

    elif mode == '-c':
        print("Active client running...")
        ip_port = sys.argv[2]
        input_file = sys.argv[3]
        output_file = sys.argv[4]
        ip, port = ip_port.split(':')
        port = int(port)
        client = DCCNETXfer(port, input_file, output_file, ip)
        client.run()
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
