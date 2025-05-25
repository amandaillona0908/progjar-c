import json
import logging
import shlex

from file_interface import FileInterface

class FileProtocol:
    def __init__(self):
        self.file = FileInterface()
    
    def proses_string(self, string_datamasuk=''):
        logging.warning(f"string diproses: {string_datamasuk}")
        
        try:
            c = shlex.split(string_datamasuk)
            if len(c) == 0:
                return json.dumps(dict(status='ERROR', data='request tidak dikenali'))
            
            command = c[0].lower().strip()
            params = c[1:] if len(c) > 1 else []
            
            logging.warning(f"memproses request: {command}")
            
            # Validasi command yang didukung
            valid_commands = ['list', 'get', 'upload', 'delete']
            if command not in valid_commands:
                return json.dumps(dict(status='ERROR', data='request tidak dikenali'))
            
            # Panggil method yang sesuai
            method = getattr(self.file, command)
            result = method(params)
            return json.dumps(result)
            
        except Exception as e:
            return json.dumps(dict(status='ERROR', data='request tidak dikenali'))

if __name__ == '__main__':
    fp = FileProtocol()
    print(fp.proses_string("LIST"))
    print(fp.proses_string("GET test.txt"))