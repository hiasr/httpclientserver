import threading
import socket
from email.utils import formatdate, parsedate
import time
import os
import logging
import mimetypes
from http import HTTPStatus
import traceback

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class Server:
    def __init__(self, address="localhost", port=8080):
        self.address = address
        self.port = port
        self.socket = self.setup_socket()

    def setup_socket(self):
        """Initializing socket"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.address, self.port))
        return s

    def start(self):
        """Start listening for connections
        Spawns a new connection handler thread for each incoming connection
        """
        logger.debug("Started listening for incoming connections...")
        self.socket.listen()

        while True:
            conn, addr = self.socket.accept()
            logger.info(f"Accepted incoming connection from address {addr}!")

            thr = threading.Thread(target=self.handle_conn, args=(conn,))
            thr.start()

    def stop(self):
        logger.info("Shutting down server...")
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def handle_conn(self, conn):
        """Handles an incoming request

        Args:
            conn (socket connection): The connection for the incoming request
        """

        try:
            conn.settimeout(2)
            data = bytes()

            try:
                while b"\r\n\r\n" not in data:
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    data += chunk
            except TimeoutError:
                return
                logger.warn("Connection timed out!")

            header_end = data.find(b"\r\n\r\n")
            headers = data[:header_end].decode()
            request_type, path, _ = headers.splitlines()[0].split()
            logger.debug(f"Incoming {request_type} request for {path}")
            print(headers.splitlines()[0])

            if f"Host: {self.address}" not in headers.splitlines()[1]:
                logger.warning("BAD REQUEST")
                self.send_status_code(conn, HTTPStatus.BAD_REQUEST)
                return

            headers = dict([line.split(": ") for line in headers.splitlines()[2:]])

            data = data[header_end + 4 :]
            if "Content-Length" in headers.keys():
                content_length = headers["Content-Length"]
                data_size = len(data)
                while data_size < content_length:
                    chunk = conn.recv(1024)
                    data += chunk
                    data_size += len(chunk)

            if path == "/":
                path = "/index.html"

            if request_type == "POST":
                self.save_data(data, path, append=False)
            if request_type == "PUT":
                self.save_data(data, path, append=True)

            self.send_file(conn, "www" + path, headers)

            if "Connection" in headers.keys() and headers["Connection"] == "keep-alive":
                self.handle_conn(conn)
        except Exception as e:
            print(e)
            traceback.print_exc()
            print("Tis genaaid")
            self.send_status_code(conn, HTTPStatus.INTERNAL_SERVER_ERROR)

        conn.close()
        logger.debug("Handler thread finished!")

    def generate_headers(self, path=None, code=HTTPStatus.OK):
        """Generates headers for the response

        Args:
                path (string): Path to the file to send with the request

        Returns:
                string: string containing all headers
        """
        status_line = f"HTTP/1.1 {code.value} {code.phrase}\r\n"
        headers = dict()
        headers["Date"] = formatdate(timeval=None, localtime=False, usegmt=True)
        if path is not None:
            headers["Content-Length"] = os.path.getsize(path)
            headers["Content-Type"] = mimetypes.guess_type(path)[0]

        header_string = status_line
        for (key, value) in headers.items():
            header_string += f"{key}: {value}\r\n"
        header_string += "\r\n"

        return header_string

    def send_file(self, conn, path, headers):
        """Send file through open connection

        Args:
                conn (socket.Connection): The connection you want to send the file through
                path (string): Path to the file to send
                file_type (string): The file type
        """
        if not os.path.exists(path):
            logger.debug("Path not found, responding with error code...")
            self.send_status_code(conn, HTTPStatus.NOT_FOUND)
            return

        if "If-Modified-Since" in headers.keys():
            last_mtime = os.path.getmtime(path)
            if last_mtime < time.mktime(parsedate(headers["If-Modified-Since"])):
                logger.debug(
                    "Requested file not modified, responding Not Modified status code..."
                )
                self.send_status_code(conn, HTTPStatus.NOT_MODIFIED)
                return

        return_headers = self.generate_headers(path)

        logger.debug("Sending response...")
        conn.send(return_headers.encode())
        with open(path, "rb") as file:
            while True:
                chunk = file.read(1024)
                if len(chunk) == 0:
                    break
                conn.send(chunk)

    def save_data(self, data, path, append=False):
        """Save string to file

        Args:
            data (string): data to be saved
            path (string): path to save the data to
            append (bool, optional): whether to append to file or (over)write file. Defaults to False.
        """
        logger.debug("Saving incoming data...")
        open_type = "ab" if append else "wb"
        with open("www" + path, open_type) as file:
            file.write(data)

    def send_status_code(self, conn, status_code):
        headers = self.generate_headers(code=status_code)
        print(headers)
        conn.sendall(headers.encode())


if __name__ == "__main__":
    Server().start()
