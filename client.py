import socket
import time
import struct


class Frame:
    SYNC_PATTERN = b"\xdc\xc0\x23\xc2"
    HEADER_SIZE = 112
    ACK_FLAG = hex(0x80)
    END_FLAG = hex(0x40)

    def __init__(self, data=b"", frame_id=0, flags=0):
        self.data = data
        self.frame_id = frame_id
        self.flags = flags
        self.chksum = 0

    def to_bytes(self):
        length = len(self.data)
        chksum = self.compute_checksum(self.data)
        header = struct.pack(
            ">8s8sHHBB",
            self.SYNC_PATTERN,
            self.SYNC_PATTERN,
            chksum,
            length,
            self.frame_id,
            self.flags,
        )
        data_bytes = struct.pack(">" + str(length) + "s", self.data)

        frame = header + data_bytes
        return frame

    def from_bytes(data):
        if len(data) < Frame.HEADER_SIZE:
            raise ValueError("Empty data")

        sync_pattern1, sync_pattern2, length, frame_id, flags = struct.unpack(
            ">8s8sHHBB", data[: Frame.HEADER_SIZE]
        )
        payload = data[Frame.HEADER_SIZE :]

        if sync_pattern1 != Frame.SYNC_PATTERN and sync_pattern2 != Frame.SYNC_PATTERN:
            raise ValueError("Invalid sync pattern")

        checksum = struct.unpack(">H", payload[:2])[0]
        if checksum != Frame.compute_checksum(data[Frame.HEADER_SIZE :]):
            raise ValueError("Checksum verification failed")

        return Frame(payload[2:], frame_id, flags)

    @staticmethod
    def compute_checksum(self, data):
        checksum = sum(data) & 0xFFFF
        self.chksum = checksum
        return checksum


def main():
    ack_frame = Frame(b"", 0, flags=Frame.ACK_FLAG)

    # Create a socket object
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Define the port on which you want to connect
    port = 12345

    s.connect(("127.0.0.1", port))

    # Initialize frame_id to 0
    frame_id = 0
    last_received_frame_id = -1

    while True:
        while True:
            # Create a frame with some data, frame_id and no flags
            frame = Frame(b"some data", frame_id)

            # Send the frame
            s.send(frame.to_bytes())

            # Wait for acknowledgement
            ack = Frame.from_bytes(s.recv(1024))

            if ack.flags == ack_frame.flags:
                # If acknowledgement received, flip the frame_id
                frame_id = 1 - frame_id
                break

            else:
                # If no acknowledgement, retransmit the frame after 1 second
                time.sleep(1)

        # Receive a frame
        data = s.recv(1024)
        received_frame = Frame.from_bytes(data)

        # Check if the frame is valid
        if (
            received_frame.frame_id != last_received_frame_id
            and received_frame.checksum == Frame.compute_checksum(received_frame.data)
        ):
            # If the frame is valid, send an acknowledgement

            ack_frame = Frame(b"", received_frame.frame_id, flags=Frame.ACK_FLAG)
            ack_frame.chksum = Frame.compute_checksum(received_frame.data)
            s.send(ack_frame.to_bytes())
            last_received_frame_id = received_frame.frame_id
