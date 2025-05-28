import socket
import logging
import time

logging.basicConfig(
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)

def send_message():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logging.warning("Membuka koneksi ke server...")

    target_host = '172.16.16.101'
    target_port = 45000

    try:
        sock.connect((target_host, target_port))
        logging.warning(f"Terkoneksi ke {target_host}:{target_port}")

        command_time = "TIME\r\n"
        logging.warning(f"[KLIEN] Mengirim: {command_time.strip()}")
        sock.sendall(command_time.encode('utf-8'))

        response = sock.recv(256)
        logging.warning(f"[DARI SERVER] Respon: {response.decode('utf-8', errors='ignore')}")

        command_quit = "QUIT\r\n"
        logging.warning(f"[KLIEN] Mengirim: {command_quit.strip()}")
        sock.sendall(command_quit.encode('utf-8'))

    except socket.error as err:
        logging.error(f"Gagal koneksi atau komunikasi: {err}")
    finally:
        logging.warning("Menutup koneksi")
        sock.close()

if __name__ == '__main__':
    while True:
        send_message()
        time.sleep(1)
