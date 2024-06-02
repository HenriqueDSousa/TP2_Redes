#!/usr/bin/python3
# Change path according to python3 path and OS

import socket
import sys
import client
import server

def usage() -> None:
    print("Client: ./dccnet-xfer -c <IP>:<PORT> <INPUT> <OUTPUT>")
    print("Server: ./dccnet-xfer -s <PORT> <INPUT> <OUTPUT>")

def check_args(args : list[str]) -> bool:
    if len(args) != 4:
        raise ValueError("Incorrect number of arguments")
        usage()
    
    if args[0] == '-c':
        print("Client executing...")
        print("IP:PORT:", args[1])
        print("Input file:", args[2])
        print("Output file:", args[3])
        ip_port, input_file, output_file = args[1:]
        ip, port = ip_port.split(":")
        client(ip, port, input_file, output_file)
        
    elif args[0] == '-s':
        print("Server executing...")
        print("PORT:", args[1])
        print("Input file:", args[2])
        print("Output file:", args[3])
        port, input_file, output_file = args[1:]
        server(port, input_file, output_file)



def main() -> None:
    print(sys.argv)
    check_args(sys.argv[1:])

if __name__ == "__main__":
    main()
