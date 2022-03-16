import socket
import argparse
import os
from bs4 import BeautifulSoup


def parse_arguments():
    """
    This function parses all the input arguments and validates them
    """
    parser = argparse.ArgumentParser(description="Perform HTTP Request")

    parser.add_argument(
        "command",
        type=str,
        help="HTTP command to perform: HEAD, GET, PUT or POST",
        choices=["HEAD", "GET", "PUT", "POST"],
    )
    parser.add_argument(
        "URI", type=str, help="URI to send the request to (e.g. http://www.example.com)"
    )
    parser.add_argument(
        "port", type=int, default=80, help="Port to send the request to (default: 80)"
    )

    return parser.parse_args()

def http_head(args):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((args.URI, args.port))
        s.settimeout(5)

        request = f"HEAD / HTTP/1.1\r\nHost: {args.URI}\r\n\r\n"

        s.sendall(request.encode())
        response = ""
        while "\r\n\r\n" not in response:
            response += s.recv(1).decode()
        with open('head.html', 'w') as file:
            file.write(response)
        
        
def http_post(args):
    


def http_get(args, path="/", target="body.html"):
    # Setting up socket with IPv4 and TCP options
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Connecting to host and setting timeout
        s.connect((args.URI, args.port))
        s.settimeout(5)

        # Send the request
        request = f"GET /{path} HTTP/1.1\r\nHost: {args.URI}\r\n\r\n"
        s.sendall(request.encode())


        # Getting the headers byte per byte while checking for double carriage return,
        # because then the headers stop and the body begins
        response = ""
        while "\r\n\r\n" not in response:
            response += s.recv(1).decode()

        # Parsing headers into a dictionary for easy access
        headers = dict([line.split(": ") for line in response.splitlines()[1:-1]])
        print(headers)

        # Checking how the content will be sent
        if "Content-Length" in headers:
            with open(target, "wb") as file:
                body_length = 0
                # Keep receiving in blocks of 1024 bytes until the whole message has been received
                while body_length < int(headers["Content-Length"]):
                    block = s.recv(1024)
                    body_length += len(block)
                    file.write(block)
        else:
            with open(target, "wb") as file:
                while True:
                    # Reading the block size as a hexstring byte per byte
                    hex_size = ""
                    while "\r\n" not in hex_size:
                        hex_size += s.recv(1).decode()
                        # print(f"Hexstring: {hex_size}")

                    # Converting the block size in hex to integer
                    block_size = int(hex_size, 16)

                    # If the block size is 0, the whole message is received, RFC 2616 §3.6.1
                    if block_size == 0:
                        break

                    # Read the whole block and write to file
                    while block_size > 0:
                        block = s.recv(min(1024,block_size))
                        block_size -= len(block)
                        file.write(block)

                    # Receive 2 bytes to skip carriage return and immediately go to the hexstring for the next block
                    s.recv(2)
    
    get_images(args, target)


def get_images(args, path):
    with open(path, "rb") as file:
        soup = BeautifulSoup(file, features='lxml')
    
    for img in soup.find_all(['img','IMG']):
        img_path = img['src']
        img_name = img_path[img_path.rfind('/')+1:]
        new_path = f"images/{img_name}"
        http_get(args, img_path, new_path)
        img['src'] = new_path

    with open(path, "wb") as file:
        file.write(soup.prettify().encode())



if __name__ == "__main__":
    args = parse_arguments()
    if args.command == 'GET':
        http_get(args)
    elif args.command == 'HEAD':
        http_head(args)
