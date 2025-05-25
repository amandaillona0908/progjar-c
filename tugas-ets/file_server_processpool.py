from socket import *
import socket
import logging
from file_protocol import FileProtocol
import multiprocessing
import concurrent.futures

protocol_handler = FileProtocol()

def process_client_request(client_conn, client_addr):
    """Function to handle client requests"""
    logging.warning(f"handling connection from {client_addr}")
    msg_buffer = ""
    try:
        while True:
            incoming_data = client_conn.recv(1024*1024)
            if not incoming_data:
                break
            msg_buffer += incoming_data.decode()
            while "\r\n\r\n" in msg_buffer:
                request_cmd, msg_buffer = msg_buffer.split("\r\n\r\n", 1)
                processed_result = protocol_handler.proses_string(request_cmd)
                server_response = processed_result + "\r\n\r\n"
                client_conn.sendall(server_response.encode())
    except Exception as ex:
        logging.warning(f"Error: {str(ex)}")
    finally:
        logging.warning(f"connection from {client_addr} closed")
        client_conn.close()


class FileServer:
    def __init__(self, bind_ip='0.0.0.0', bind_port=7778, worker_pool_size=5):
        self.server_addr = (bind_ip, bind_port)
        self.pool_workers = worker_pool_size
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start_server(self):
        logging.warning(f"server running on ip address {self.server_addr} with process pool size {self.pool_workers}")
        self.server_socket.bind(self.server_addr)
        self.server_socket.listen(1)
        
        # Create a ProcessPoolExecutor
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.pool_workers) as proc_executor:
            try:
                while True:
                    client_conn, client_addr = self.server_socket.accept()
                    logging.warning(f"connection from {client_addr}")
                    
                    # Submit the client handling task to the process pool
                    proc_executor.submit(process_client_request, client_conn, client_addr)
            except KeyboardInterrupt:
                logging.warning("Server shutting down")
            except Exception as ex:
                logging.warning(f"Error in server: {str(ex)}")
            finally:
                if self.server_socket:
                    self.server_socket.close()


def run_main():
    import argparse
    cmd_parser = argparse.ArgumentParser(description='File Server')
    cmd_parser.add_argument('--port', type=int, default=7778, help='Server port (default: 7778)')
    cmd_parser.add_argument('--pool-size', type=int, default=5, help='Process pool size (default: 5)')
    cmd_args = cmd_parser.parse_args()
    
    file_server = FileServer(bind_ip='0.0.0.0', bind_port=cmd_args.port, worker_pool_size=cmd_args.pool_size)
    file_server.start_server()


if __name__ == "__main__":
    # This is important for multiprocessing to work properly on some platforms
    multiprocessing.freeze_support()
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
    run_main()