import threading
import socket
from email.utils import formatdate
import os

SERVER_HOST = 'localhost'
SERVER_PORT = 8080



def generate_headers(path):
	status_line = "HTTP/1.1 200 OK\r\n"
	headers = dict()
	headers['Date'] = formatdate()
	headers['Content-Length'] = os.path.getsize(path)
	headers['Content-Type'] = 'text/html'

	header_string = status_line
	for (key, value) in headers.items():
		header_string += f"{key}: {value}\r\n"
	header_string += "\r\n"
	return header_string


def send_file(conn, path, file_type):
	return_headers = generate_headers(path)
	conn.send(return_headers.encode())
	with open(path, 'rb') as file:
		while True:
			chunk = file.read(1024)
			if len(chunk) == 0:
				break
			conn.send(chunk)

def handle_get(conn, command, headers):
	conn.setblocking(0)
	path = command[1]
	if path == '/':
		send_file(conn, f"www/index.html", 'text/html')
	elif path == '/image.png':
		send_file(conn, f"www/{path}", "image/png")
	else:
		raise Exception("File not found")

	

def handle_conn(conn, addr):
	conn.settimeout(2)
	print("Started connection")
	data = ""
	while True: 
		try:
			chunk = conn.recv(1024).decode()
			if not chunk:
				break
			data += chunk
			print(data)
		except:
			break

	header_end = data.find("\r\n\r\n")
	command = data[:header_end].splitlines()[0]
	print(command)
	headers = dict([line.split(": ") for line in data[:header_end].splitlines()[1:]])
	data = data[header_end+4:]
	command = command.split()

	if command[0] == 'GET':
		handle_get(conn, command, headers)
	elif command[0] == 'HEAD':
		handle_head(command, headers)
	elif command[0] == 'PUT':
		handle_put(command, headers, data)
	elif command[0] == 'POST':
		handle_post(command, headers, data)
	else:
		raise Exception("Not a valid command")




with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
	print("Setting up socket")
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind((SERVER_HOST, SERVER_PORT))
	s.listen()
	print("Listening for incoming connections...")

	while True:
		conn, addr = s.accept()
		print(f"Accepted incoming connection from addres {addr}!")

		thr = threading.Thread(target=handle_conn, args=(conn, addr))
		thr.start()