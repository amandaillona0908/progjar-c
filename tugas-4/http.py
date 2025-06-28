import os
import logging
from datetime import datetime

class HttpServer:
    def __init__(self):
        self.sessions = {}
        self.mime_types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.txt': 'text/plain',
            '.html': 'text/html',
            '.sh': 'text/plain',
            '.bin': 'application/octet-stream',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json'
        }

        logging.basicConfig(level=logging.INFO, format='%(message)s')
        self.logger = logging.getLogger(__name__)
        
    def create_response(self, status_code=404, message='Not Found', body=bytes(), headers={}):
        timestamp = datetime.now().strftime('%c')
        response_lines = []
        response_lines.append(f"HTTP/1.0 {status_code} {message}\r\n")
        response_lines.append(f"Date: {timestamp}\r\n")
        response_lines.append("Connection: close\r\n")
        response_lines.append("Server: myserver/1.0\r\n")
        response_lines.append(f"Content-Length: {len(body)}\r\n")
        response_lines.append("X-Content-Type-Options: nosniff\r\n")
        response_lines.append("X-Frame-Options: DENY\r\n")
        
        for key, value in headers.items():
            response_lines.append(f"{key}:{value}\r\n")
        response_lines.append("\r\n")

        response_headers = ''.join(response_lines)
            
        if not isinstance(body, bytes):
            body = body.encode()

        return response_headers.encode() + body

    def process_request(self, data, body=b''):
        request_lines = data.split("\r\n")
        
        if not request_lines:
            return self.create_response(400, 'Bad Request', 'Empty request', {})
            
        request_line = request_lines[0]
        headers = [line for line in request_lines[1:] if line != '']

        print(f"Request: {request_line}")
    
        parts = request_line.split(" ")
        try:
            method = parts[0].upper().strip()
            path = parts[1].strip()
            
            if method == 'GET':
                return self.handle_get(path, headers)
            elif method == 'POST':
                return self.handle_post(path, headers, body)
            elif method == 'DELETE':
                return self.handle_delete(path, headers)
            else:
                return self.create_response(405, 'Method Not Allowed', f'Method {method} not supported', 
                                           {'Content-type': 'text/plain'})
        except IndexError:
            return self.create_response(400, 'Bad Request', 'Malformed request line', 
                                       {'Content-type': 'text/plain'})

    def handle_get(self, path, headers):
        base_dir = './'
        
        if path == '/':
            return self.create_response(200, 'OK', 'Ini Adalah web Server percobaan', 
                                       {'Content-type': 'text/plain'})
        if path == '/video':
            return self.create_response(302, 'Found', '', {'Location': 'https://youtu.be/katoxpnTf04'})
        if path == '/santai':
            return self.create_response(200, 'OK', 'santai saja', {'Content-type': 'text/plain'})
        if path == '/list':
            return self.list_directory(base_dir)

        if path.startswith('/'):
            path = path[1:]
        
        if '..' in path or path.startswith('/'):
            return self.create_response(403, 'Forbidden', 'Access denied', 
                                       {'Content-type': 'text/plain'})
        
        file_path = os.path.join(base_dir, path)
        
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return self.create_response(404, 'Not Found', f'File {path} not found', 
                                       {'Content-type': 'text/plain'})
            
        try:
            with open(file_path, 'rb') as file:
                content = file.read()
            
            file_extension = os.path.splitext(file_path)[1].lower()
            content_type = self.mime_types.get(file_extension, 'application/octet-stream')
            
            headers = {'Content-type': content_type}
            return self.create_response(200, 'OK', content, headers)
            
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {str(e)}")
            return self.create_response(500, 'Internal Server Error', f'Error reading file: {str(e)}', 
                                       {'Content-type': 'text/plain'})
    
    def handle_post(self, path, headers, body):
        headers_dict = {}
        for header in headers:
            if ":" in header:
                key, value = header.split(":", 1)
                headers_dict[key.strip().lower()] = value.strip()

        if path == '/upload':
            return self.upload_file(headers_dict, body)
        
        return self.create_response(404, 'Not Found', f'POST endpoint {path} not found', 
                                   {'Content-type': 'text/plain'})

    def handle_delete(self, path, headers):
        if path.startswith('/delete/'):
            filename = path[len('/delete/'):]
            return self.delete_file(filename)
        
        return self.create_response(404, 'Not Found', f'DELETE endpoint {path} not found', 
                                   {'Content-type': 'text/plain'})

    def upload_file(self, headers, body):
        filename = headers.get('x-filename', None)
        content_length = headers.get('content-length', '0')
        
        try:
            length = int(content_length)
        except ValueError:
            return self.create_response(400, 'Bad Request', 'Invalid Content-Length', 
                                       {'Content-type': 'text/plain'})

        if not filename:
            return self.create_response(400, 'Bad Request', 'Missing X-Filename header', 
                                       {'Content-type': 'text/plain'})
        
        if '..' in filename or '/' in filename or '\\' in filename:
            return self.create_response(403, 'Forbidden', 'Invalid filename', 
                                       {'Content-type': 'text/plain'})

        if length == 0 or len(body) != length:
            return self.create_response(400, 'Bad Request', 'Content-Length mismatch', 
                                       {'Content-type': 'text/plain'})

        try:
            with open(filename, 'wb') as file:
                file.write(body)
            print(f"File uploaded: {filename}")
            return self.create_response(200, 'OK', f'File {filename} uploaded successfully.\n', 
                                       {'Content-type': 'text/plain'})
        except Exception as e:
            self.logger.error(f"Error uploading file {filename}: {str(e)}")
            return self.create_response(500, 'Internal Server Error', f'Upload failed: {str(e)}', 
                                       {'Content-type': 'text/plain'})
    
    def delete_file(self, filename):
        try:
            if '..' in filename or '/' in filename or '\\' in filename:
                return self.create_response(403, 'Forbidden', 'Invalid filename', 
                                           {'Content-type': 'text/plain'})

            file_path = os.path.join('./', filename)

            if os.path.exists(file_path) and os.path.isfile(file_path):
                os.remove(file_path)
                print(f"File deleted: {filename}")
                return self.create_response(200, 'OK', f'File {filename} deleted successfully.\n', 
                                           {'Content-type': 'text/plain'})
            else:
                return self.create_response(404, 'Not Found', f'File {filename} not found', 
                                           {'Content-type': 'text/plain'})

        except Exception as e:
            self.logger.error(f"Error deleting file {filename}: {str(e)}")
            return self.create_response(500, 'Internal Server Error', f'Delete failed: {str(e)}', 
                                       {'Content-type': 'text/plain'})

    def list_directory(self, path):
        try:
            files = os.listdir(path)
            file_list = []
            
            for filename in files:
                file_path = os.path.join(path, filename)
                if os.path.isfile(file_path):
                    file_list.append(filename)
            
            if not file_list:
                content = "No files found in directory"
            else:
                content = "\n".join(file_list)
                
            headers = {'Content-type': 'text/plain'}
            return self.create_response(200, 'OK', content, headers)

        except Exception as e:
            self.logger.error(f"Error listing directory {path}: {str(e)}")
            return self.create_response(500, 'Internal Server Error', f'Directory listing failed: {str(e)}', 
                                       {'Content-type': 'text/plain'})

def main():
    http_server = HttpServer()
    response = http_server.process_request('GET /perftest.sh HTTP/1.0')
    print(response)

if __name__ == "__main__":
    main()