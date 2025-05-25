import socket
import threading
import logging
import sys

from file_protocol import FileProtocol

fp = FileProtocol()

logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.WARNING)

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        threading.Thread.__init__(self)

    def run(self):
        logging.warning(f"client connected: {self.address}")
        
        while True:
            try:
                data = self.connection.recv(4096)
                if data:
                    request = data.decode().strip()
                    logging.warning(f"request received: {request[:50]}")
                    
                    result = fp.proses_string(request)
                    response = result + "\r\n\r\n"
                    
                    self.connection.sendall(response.encode())
                    logging.warning(f"response sent")
                else:
                    break
            except Exception as e:
                logging.warning(f"error handling client: {e}")
                break
                
        self.connection.close()
        logging.warning(f"client disconnected: {self.address}")

class Server(threading.Thread):
    def __init__(self, ipaddress='0.0.0.0', port=7778):
        self.ipinfo = (ipaddress, port)
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        threading.Thread.__init__(self)

    def run(self):
        logging.warning(f"server berjalan di ip address {self.ipinfo}")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(5)
        
        while True:
            try:
                self.connection, self.client_address = self.my_socket.accept()
                logging.warning(f"connection from {self.client_address}")

                clt = ProcessTheClient(self.connection, self.client_address)
                clt.start()
                self.the_clients.append(clt)
            except Exception as e:
                logging.warning(f"server error: {e}")
                break

def main():
    svr = Server(ipaddress='0.0.0.0', port=7778)
    svr.start()
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Server stopped")

if __name__ == "__main__":
    main()