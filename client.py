import socket
import argparse
import os
from bs4 import BeautifulSoup
import logging
import mimetypes

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Request:
    def __init__(self, command, URI, port, save_path=None):
        """Adding arguments as class variables

        Args:
            args (Namespace): Input arguments 
        """
        self.type = command

        self.uri, self.target = self.parse_uri(URI)
        self.port = port
        self.save_path = save_path
    
    def parse_uri(self, URI):
        """Checks if URI is in correct format
        Currently the only supported format is 'http://example.com'

        Args:
            URI (string): the URI

        Raises:
            Exception: Raise exception if URI not in correct format

        Returns:
            string, string: Returns the host address and the target path
        """
        if URI[:7] != "http://":
            raise Exception("URI must be in the format 'http://example.com'!")
        URI = URI[7:]
        URI_end = URI.find("/")
        if URI_end == -1:
            uri = URI
            target = "/"
        else:
            uri = URI[:URI_end]
            target = URI[URI_end:]
        return uri, target

        

    def send(self):
        """Send the HTTP Request
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            logger.debug("Created socket")
            self.sock = s

            try:
                s.connect((self.uri, self.port))
            except:
                logger.warning("Failed to connect to server")
                return

            logger.debug(f"Connected to {self.uri} on port {self.port}!")

            request = f"{self.type} {self.target} HTTP/1.1\r\nHost: {self.uri}\r\n\r\n"

            if self.type in ["POST", "PUT"]:
                user_input = input("Enter string to send in request: ")
                request += user_input + "\r\n"

            logger.debug("Sending request...")
            s.sendall(request.encode())
            logger.debug("Request has been succesfully sent!")

            self.receive()

    def receive(self):
        """Receive the response from the HTTP Request
        """
        logger.debug("Receiving headers...")
        headers = self.receive_headers()
        logger.debug("Headers succesfully received!")

        if self.type == "HEAD":
            print(headers)
            return

        self.headers = self.parse_headers(headers)

        logger.debug("Receiving body...")
        body = self.receive_body()

        if self.type == "GET":
            mimetype = self.headers["Content-Type"].split(";")[0]

            encoding="ISO-8859-1"
            if mimetype == 'text/html':
                try:
                    encoding = self.headers["Content-Type"].split(";")[1].split("=")[-1]
                except:
                    logger.debug("No encoding found")

                body = self.get_images(body.decode(encoding))
                with open("body.html", "wb") as file:
                    file.write(body.encode())
            else:
                if self.save_path is None:
                    print(mimetype)
                    extension = mimetypes.guess_extension(mimetype)
                    self.save_path = "body" + extension

                with open(self.save_path, "wb") as file:
                    file.write(body)
        else:
            print(body.decode())

        logger.debug("Body succesfully received!")


    def receive_headers(self):
        """Receive response headers

        Returns:
            string: response headers and command
        """
        # Getting the headers byte per byte while checking for double carriage return,
        # because then the headers stop and the body begins
        response = ""
        while "\r\n\r\n" not in response:
            response += self.sock.recv(1).decode()

        return response
    
    def parse_headers(self, headers): 
        """Parse the headers in a dictionary for easy access

        Args:
            headers (string): raw headers and command

        Returns:
            dict: parsed headers
        """
        headers = headers.strip()
        return dict([line.split(": ") for line in headers.splitlines()[1:]])

    def receive_body(self):
        """Receives the response body content

        Returns:
            bytes: the encoded response body 
        """
        # Checking how the content will be sent
        if "Content-Length" in self.headers:
            body_length = 0
            body = bytes()
            # Keep receiving in blocks of 1024 bytes until the whole message has been received
            while body_length < int(self.headers["Content-Length"]):
                block = self.sock.recv(1024)
                body_length += len(block)
                body += block
        else:
            body = bytes()
            while True:
                # Reading the block size as a hexstring byte per byte
                hex_size = ""
                while "\r\n" not in hex_size:
                    hex_size += self.sock.recv(1).decode()

                # Converting the block size in hex to integer
                block_size = int(hex_size, 16)

                # If the block size is 0, the whole message is received, RFC 2616 §3.6.1
                if block_size == 0:
                    break

                # Read the whole block and write to file
                while block_size > 0:
                    block = self.sock.recv(min(1024, block_size))
                    block_size -= len(block)
                    body += block

                # Receive 2 bytes to skip carriage return and immediately go to the hexstring for the next block
                self.sock.recv(2)
        return body

    def get_images(self, html):
        """Downloads images and changes html to use local paths

        Args:
            html (string): a string containing html

        Returns:
            string: the html with changed source paths of images
        """
        soup = BeautifulSoup(html, features="lxml")

        cwd = os.getcwd()

        for img in soup.find_all(["img", "IMG"]):

            img_path = img["src"]
            img_name = img_path[img_path.rfind("/") + 1 :]
            new_path = cwd + f"/images/{img_name}"
             

            # Reuse connection for internal images
            if "://" not in img_path:
                target = img_path if img_path[0] == "/" else "/" + img_path
                self.request_internal_image(target, new_path)
            # Create new connection for external images
            else:
                if "https://" in img_path:
                    continue

                URI = img_path
                port = 80
                Request("GET", URI, port, save_path=new_path).send()

            img["src"] = new_path

        return soup.prettify()

    def request_internal_image(self, target, save_path):
        """Downloads image stored on same host as current request

        Args:
            target (string): the path of the image on the server
            save_path (string): path to store the image locally
        """

        request = f"GET {target} HTTP/1.1\r\nHost: {self.uri}\r\n\r\n"
        self.save_path = save_path
        self.sock.sendall(request.encode())
        self.receive()


def parse_arguments():
    """Parses input arguments and does argument verification

    Returns:
        Namespace: All the provided arguments in a namespace
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


if __name__ == "__main__":
    args = parse_arguments()
    Request(args.command, args.URI, args.port).send()
