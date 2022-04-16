from server import Server
from client import Request
import os
import time

class TestHTTPClientServer:
	def test_get(self):
		Request("GET", 'http://localhost', 8080).send()

		time.sleep(10)
		assert self.files_equal("www/index.html", "body.html")
		assert self.files_equal("www/image.png", "images/image.png")

		server.stop()
		

	def files_equal(self, path1, path2):
			with open(path1) as file1:
				with open(path2) as file2:
					return file1.read() == file2.read()
	
		





		