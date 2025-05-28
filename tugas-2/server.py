from socket import *
import socket
import threading
import logging
from datetime import datetime

logging.basicConfig(
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        threading.Thread.__init__(self)

    def run(self):
        logging.warning(f"[SERVER] Terhubung dengan {self.address}")
        try:
            while True:
                data = self.connection.recv(256)
                if not data:
                    break

                text = data.decode().strip()
                logging.warning(f"[SERVER] Data diterima dari {self.address}: {text}")

                if text.upper() == "TIME":
                    now = datetime.now()
                    jam = now.strftime("%H:%M:%S")
                    msg = f"JAM {jam}\r\n"
                    self.connection.sendall(msg.encode())
                    logging.warning(f"[SERVER] Mengirim waktu ke {self.address}: {msg.strip()}")
                elif text.upper() == "QUIT":
                    logging.warning(f"[SERVER] {self.address} meminta keluar.")
                    break
                else:
                    err = "PERINTAH TIDAK VALID\r\n"
                    self.connection.sendall(err.encode())
                    logging.warning(f"[SERVER] Perintah tidak dikenal dari {self.address}: {text}")
        except Exception as e:
            logging.error(f"[SERVER] Error dengan {self.address}: {e}")
        finally:
            self.connection.close()
            logging.warning(f"[SERVER] Koneksi ditutup dengan {self.address}\n")

class Server(threading.Thread):
    def __init__(self):
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        threading.Thread.__init__(self)

    def run(self):
        host = '0.0.0.0'
        port = 45000
        self.my_socket.bind((host, port))
        self.my_socket.listen(1)
        logging.warning(f"SERVER LISTENING ON {host}:{port}") # Tambahan pesan ini
        while True:
            self.connection, self.client_address = self.my_socket.accept()
            logging.warning(f"connection from {self.client_address}")

            clt = ProcessTheClient(self.connection, self.client_address)
            clt.start()
            self.the_clients.append(clt)

def main():
    svr = Server()
    svr.start()

if __name__ == "__main__":
    main()
