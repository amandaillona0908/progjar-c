import socket
import time
import logging
import signal
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from http import HttpServer

http_server = HttpServer()
shutdown_event = threading.Event()
server_socket = None
logger = None

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    return logging.getLogger(__name__)

def signal_handler(signum, frame):
    if logger:
        logger.info(f"Received signal {signum}, shutting down gracefully...")
    else:
        print(f"Received signal {signum}, shutting down gracefully...")
    shutdown_event.set()
    if server_socket:
        server_socket.close()

def process_client(connection, address):
    try:
        connection.settimeout(30.0)
        
        header_data = b""
        start_time = time.time()
        
        while b"\r\n\r\n" not in header_data:
            if time.time() - start_time > 30:
                print(f"Request timeout from {address}")
                return
                
            try:
                data = connection.recv(1024)
                if not data:
                    break
                header_data += data
            except socket.timeout:
                print(f"Socket timeout from {address}")
                return
            except socket.error as e:
                print(f"Socket error from {address}: {e}")
                return

        if b"\r\n\r\n" not in header_data:
            print(f"Incomplete request from {address}")
            return

        header_end_pos = header_data.find(b"\r\n\r\n") + 4
        header_bytes_only = header_data[:header_end_pos]
        body = header_data[header_end_pos:]
        
        try:
            headers_text = header_bytes_only.decode('utf-8')
        except UnicodeDecodeError:
            print(f"Invalid UTF-8 in headers from {address}")
            return
            
        headers_lines = headers_text.split("\r\n")
        
        content_length = 0
        for line in headers_lines:
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    print(f"Invalid Content-Length from {address}")
                    content_length = 0
                break

        while len(body) < content_length:
            try:
                remaining = content_length - len(body)
                data = connection.recv(min(1024, remaining))
                if not data:
                    break
                body += data
            except socket.error as e:
                print(f"Error reading body from {address}: {e}")
                break

        response = http_server.process_request(headers_text, body)
        
        try:
            connection.sendall(response)
            print(f"Request processed successfully for {address}")
        except socket.error as e:
            print(f"Error sending response to {address}: {e}")
            
    except Exception as e:
        print(f"Error in process_client from {address}: {e}")
    finally:
        try:
            connection.close()
        except:
            pass

def cleanup_completed_futures(clients):
    completed = []
    remaining = []
    
    for future in clients:
        if future.done():
            try:
                future.result()
            except Exception as e:
                if logger:
                    logger.error(f"Thread completed with error: {e}")
                else:
                    print(f"Thread completed with error: {e}")
            completed.append(future)
        else:
            remaining.append(future)
    
    if completed and logger:
        logger.debug(f"Cleaned up {len(completed)} completed futures")
    elif completed:
        print(f"Cleaned up {len(completed)} completed futures")
    return remaining

def get_server_stats(clients):
    running_count = sum(1 for f in clients if f.running())
    total_count = len(clients)
    return {
        'running': running_count,
        'completed': total_count - running_count,
        'total': total_count
    }

def start_server():
    global server_socket, logger
    logger = setup_logging()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    clients = []
    
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)	
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', 8885))
        server_socket.listen(128)
        
        print("ThreadPool HTTP Server started on 0.0.0.0:8885")
        print("Max threads: 50")

        with ThreadPoolExecutor(50) as executor:
            while not shutdown_event.is_set():
                try:
                    server_socket.settimeout(1.0)
                    connection, client_address = server_socket.accept()
                    
                    print()
                    future = executor.submit(process_client, connection, client_address)
                    clients.append(future)
                    
                    if len(clients) % 20 == 0:
                        clients = cleanup_completed_futures(clients)
                    
                except socket.timeout:
                    continue
                except socket.error as e:
                    if shutdown_event.is_set():
                        break
                    logger.error(f"Socket error: {e}")
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Unexpected error in server loop: {e}")
                    time.sleep(0.1)
            
            logger.info("Server shutting down...")
            logger.info("Waiting for active connections to complete...")
            
            try:
                active_futures = [f for f in clients if not f.done()]
                if active_futures:
                    logger.info(f"Waiting for {len(active_futures)} active connections...")
                    for future in as_completed(active_futures, timeout=30):
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(f"Thread completed with error: {e}")
                else:
                    logger.info("No active connections to wait for")
            except Exception as e:
                logger.warning(f"Timeout waiting for connections to complete: {e}")
                
    except OSError as e:
        if e.errno == 98:
            logger.error("Error: Port 8885 is already in use")
        else:
            logger.error(f"Socket error: {e}")
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected server error: {e}")
    finally:
        if server_socket:
            server_socket.close()
        logger.info("Server stopped")

def main():
    start_server()

if __name__ == "__main__":
    main()