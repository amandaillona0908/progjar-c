import socket
import json
import base64
import logging
import os

server_address = ('172.16.16.101', 7778)

logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.WARNING)

def send_command(command_str=""):
    global server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(60)  # 60 detik timeout untuk file besar
    sock.connect(server_address)
    logging.warning(f"connecting to {server_address}")
    
    try:
        logging.warning(f"sending message")
        # Kirim data dalam chunks untuk file besar
        data_to_send = command_str.encode('utf-8')
        total_sent = 0
        while total_sent < len(data_to_send):
            sent = sock.send(data_to_send[total_sent:total_sent + 8192])
            if sent == 0:
                raise RuntimeError("Socket connection broken")
            total_sent += sent
        
        data_received = ""
        while True:
            data = sock.recv(8192)
            if data:
                data_received += data.decode('utf-8')
                if "\r\n\r\n" in data_received:
                    break
            else:
                break
                
        data_received = data_received.replace("\r\n\r\n", "")
        hasil = json.loads(data_received)
        logging.warning("data received from server")
        return hasil
    except Exception as e:
        logging.warning(f"error during data receiving: {e}")
        return dict(status='ERROR', data=str(e))
    finally:
        sock.close()

def remote_list():
    command_str = "LIST"
    hasil = send_command(command_str)
    if hasil['status'] == 'OK':
        print("Daftar file:")
        for nmfile in hasil['data']:
            print(f"- {nmfile}")
        return True
    else:
        print(f"Gagal: {hasil['data']}")
        return False

def remote_get(filename=""):
    command_str = f"GET {filename}"
    hasil = send_command(command_str)
    if hasil['status'] == 'OK':
        namafile = hasil['data_namafile']
        isifile = base64.b64decode(hasil['data_file'])
        with open(f"download_{namafile}", 'wb') as fp:
            fp.write(isifile)
        print(f"File {filename} berhasil didownload sebagai download_{namafile}")
        return True
    else:
        print(f"Gagal: {hasil['data']}")
        return False

def remote_upload(filename=""):
    if not os.path.exists(filename):
        print(f"File {filename} tidak ditemukan")
        return False
        
    try:
        # Cek ukuran file
        file_size = os.path.getsize(filename)
        print(f"Mengupload file {filename} ({file_size} bytes)...")
        
        with open(filename, 'rb') as fp:
            file_content = fp.read()
            
        # Encode ke base64 dengan proper padding
        isifile = base64.b64encode(file_content).decode('utf-8')
        
        # Buat command dengan proper quoting
        base_filename = os.path.basename(filename)
        command_str = f'UPLOAD {base_filename} {isifile}'
        
        hasil = send_command(command_str)
        
        if hasil['status'] == 'OK':
            print(hasil['data'])
            return True
        else:
            print(f"Gagal: {hasil['data']}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def remote_delete(filename=""):
    command_str = f"DELETE {filename}"
    hasil = send_command(command_str)
    if hasil['status'] == 'OK':
        print(hasil['data'])
        return True
    else:
        print(f"Gagal: {hasil['data']}")
        return False

def interactive_client():
    print("=== FILE SERVER CLIENT ===")
    print("Commands: LIST, GET <filename>, UPLOAD <filename>, DELETE <filename>, QUIT")
    print("-" * 50)
    
    while True:
        try:
            command = input("\nMasukkan command: ").strip()
            
            if not command:
                continue
                
            if command.upper() == 'QUIT' or command.upper() == 'EXIT':
                print("Keluar dari client...")
                break
                
            parts = command.split()
            cmd = parts[0].upper()
            
            if cmd == 'LIST':
                remote_list()
                
            elif cmd == 'GET':
                if len(parts) < 2:
                    print("Usage: GET <filename>")
                else:
                    filename = parts[1]
                    remote_get(filename)
                    
            elif cmd == 'UPLOAD':
                if len(parts) < 2:
                    print("Usage: UPLOAD <filename>")
                else:
                    filename = parts[1]
                    remote_upload(filename)
                    
            elif cmd == 'DELETE':
                if len(parts) < 2:
                    print("Usage: DELETE <filename>")
                else:
                    filename = parts[1]
                    remote_delete(filename)
                    
            else:
                print("Command tidak dikenali. Gunakan: LIST, GET, UPLOAD, DELETE, QUIT")
                
        except KeyboardInterrupt:
            print("\nKeluar dari client...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    interactive_client()