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
    """
    Class to handle DCCNET file transfer.

    Attributes:
        port (int): Port for communication.
        input_file (str): Input file path.
        output_file (str): Output file path.
        ip (str): IP address for communication.
    """
    
    def __init__(self, port, input_file, output_file, ip=None):
        self.port = port

        if ip is None:
            self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.remote_address = None
            self.sock.bind(('', port))
            self.sock.listen(1)
        else:
            family = socket.AF_INET6 if ':' in ip else socket.AF_INET
            self.sock = socket.socket(family, socket.SOCK_STREAM)
            self.remote_address = (ip, port)
            self.sock.connect(self.remote_address)

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

        self.lock = threading.Lock()

    def set_frame_id(self, frame_id):
        self.frame_id = frame_id

    def send_frame(self, data, frame_id, flags):
        """
        Send a frame to the remote address.

        Args:
            data (bytes): Data to send.
            frame_id (int): Frame ID.
            flags (bytes): Flags for the frame.
        """
        print(f"Sending frame:\tlength={len(data)}\tid={frame_id}\tflags={flags}\tdata={data}")
        frame = DCCNETFrame(data, frame_id=frame_id, flags=flags)
        self.sock.send(frame.build_frame())

    def send_end(self, frame_id):
        """
        Send an END frame to the remote address.

        Args:
            frame_id (int): Frame ID.
        """
        print(f"Sending END flag for frame_id: {frame_id}")
        end_frame = DCCNETFrame(b"", frame_id, END_FLAG)
        self.sock.send(end_frame.to_bytes())

    def send_ack(self, frame_id):
        """
        Send an ACK frame to the remote address.

        Args:
            frame_id (int): Frame ID.
        """
        print(f"Sending ACK flag for frame_id: {frame_id}")
        ack_frame = DCCNETFrame(b"", frame_id, ACK_FLAG)
        self.sock.send(ack_frame.build_frame())

    def send_rst(self, error_message):
        """
        Send a RST frame with an error message.

        Args:
            error_message (str): Error message to send.
        """
        print(f"Sending RST flag")
        rst_frame = DCCNETFrame(error_message.encode(), frame_id=65535, flags=RST_FLAG)
        self.sock.send(rst_frame.build_frame())
        self.sock.close()

    def send_data(self):
        """
        Periodically send data frames.
        """
        num_retransmissions = 0
        last_id = self.frame_id
        while True:
            with self.lock:

                if last_id == self.frame_id:
                    num_retransmissions += 1
                    if num_retransmissions > 17:
                        print("Max num of retransmissions reached")
                        self.send_rst("Max num of retransmissions reached")
                        self.sock.close()
                        return
                else:
                    num_retransmissions = 0

                self.send_frame(data=self.current_line.encode(), frame_id=self.frame_id, flags=self.current_flags)
                last_id = self.frame_id

                if bitwise_and(self.current_flags, END_FLAG):
                    self.end_sent = True

            time.sleep(1)

    def run(self):
        """
        Main loop for handling incoming frames.
        """
        passive_server = True

        if self.remote_address:
            passive_server = False
            threading.Thread(target=self.send_data, daemon=True).start()

        while True:

            if not self.remote_address and passive_server:
                self.sock, addr = self.sock.accept()
                self.remote_address = addr
                threading.Thread(target=self.send_data, daemon=True).start()

            frame = self.sock.recv(4096)
            try:
                chksum, length, frame_id, flags, payload = DCCNETFrame.decode_frame(frame)

                if bitwise_and(flags, RST_FLAG):
                    print("Received Reset Flag")
                    print("Error message:", payload)
                    print("Connection terminated..")
                    self.sock.close()
                    return

                if self.last_received_id == frame_id and self.last_received_checksum == chksum:
                    print("Received duplicated package")
                    if self.retransmission_counter_ack > 16:
                        self.send_rst("Too many retransmissions")
                    self.send_ack(frame_id)
                    self.retransmission_counter_ack += 1
                else:
                    if not bitwise_and(flags, ACK_FLAG):
                        if not self.end_received:
                            self.retransmission_counter_ack = 0
                            print(f"Received frame:\tchksum={chksum}\tlength={length}\tid={frame_id}\tflags={flags}\tdata={payload}")
                            with open(self.output_file, "a") as f:
                                f.write(payload)
                                if bitwise_and(flags, END_FLAG):
                                    self.end_received = True
                                    f.write("\n")
                            self.send_ack(frame_id)
                    else:
                        if self.frame_id == frame_id:
                            with self.lock:
                                self.line_index += 1
                                if self.line_index < len(self.input_lines):
                                    self.current_line = self.input_lines[self.line_index]
                                    if self.line_index == len(self.input_lines) - 1:
                                        self.current_flags = END_FLAG
                                self.set_frame_id(1 - self.frame_id)

            except ValueError as e:
                print(f"Frame error: {e}, waiting retransmission...")

            with self.lock:
                if self.end_received and self.end_sent:
                    print("File transmission ended")
                    self.sock.close() 
                    break


def usage() -> None:
    """
    Print usage instructions for the script.
    """
    print("Client: ./dccnet-xfer -c <IP>:<PORT> <INPUT> <OUTPUT>")
    print("Server: ./dccnet-xfer -s <PORT> <INPUT> <OUTPUT>")


def main():
    """
    Main function to parse arguments and start the client or server.
    """
    if len(sys.argv) < 5:
        usage()
        sys.exit(1)

    mode = sys.argv[1]
    addr = sys.argv[2]
    input_file = sys.argv[3]
    output_file = sys.argv[4]

    if mode == '-s':
        print("Passive server running...")
        port = int(addr)
        server = DCCNETXfer(port, input_file, output_file)
        server.run()
    elif mode == '-c':
        print("Active client running...")
        ip, port = addr.split(':')
        client = DCCNETXfer(int(port), input_file, output_file, ip)
        client.run()
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
