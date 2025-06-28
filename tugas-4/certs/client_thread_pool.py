import socket
import sys
import os

def list_files():
    sock = socket.socket()
    sock.connect(('localhost', 8885))
    request = "GET /list HTTP/1.0\r\n\r\n"
    sock.send(request.encode())
    response = sock.recv(4096)
    print(response.decode())
    sock.close()

def upload_file(file_path):
    ports_to_try = [8885]
    host = 'localhost'

    if not os.path.exists(file_path):
        print("File tidak ditemukan.")
        return

    filename = os.path.basename(file_path)

    with open(file_path, 'rb') as f:
        file_data = f.read()

    body = file_data
    headers = (
        f"POST /upload HTTP/1.0\r\n"
        f"X-Filename: {filename}\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Content-Type: application/octet-stream\r\n"
        f"\r\n"
    ).encode()

    request = headers + body

    for port in ports_to_try:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            sock.sendall(request)

            response = b""
            while True:
                data = sock.recv(1024)
                if not data:
                    break
                response += data
            sock.close()

            print(f"[Sukses upload ke port {port}]")
            print(response.decode())
            return

        except ConnectionRefusedError:
            continue

    print("Gagal terhubung ke server di semua port.")

def delete_file(filename):
    sock = socket.socket()
    sock.connect(('localhost', 8885))
    request = (
        f"DELETE /delete/{filename} HTTP/1.0\r\n"
        f"\r\n"
    )
    sock.send(request.encode())
    response = sock.recv(4096)
    print(response.decode())
    sock.close()

def show_usage():
    print("Usage:")
    print("  python3 client_thread_pool.py list")
    print("  python3 client_thread_pool.py upload <filepath>")
    print("  python3 client_thread_pool.py delete <filename>")

def main():
    if len(sys.argv) < 2:
        print("Error: Tidak ada command yang diberikan!")
        show_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'list':
        list_files()
    elif command == 'upload':
        if len(sys.argv) < 3:
            print("Error: Filepath tidak diberikan!")
            show_usage()
            sys.exit(1)
        filepath = sys.argv[2]
        upload_file(filepath)
    elif command == 'delete':
        if len(sys.argv) < 3:
            print("Error: Filename tidak diberikan!")
            show_usage()
            sys.exit(1)
        filename = sys.argv[2]
        delete_file(filename)
    else:
        print(f"Error: Command '{command}' tidak dikenal!")
        show_usage()
        sys.exit(1)

if __name__ == '__main__':
    main()