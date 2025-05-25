import os
import json
import base64
from glob import glob

class FileInterface:
    def __init__(self):
        if not os.path.exists('files/'):
            os.makedirs('files/')
        os.chdir('files/')

    def list(self, params=[]):
        try:
            filelist = glob('*.*')
            return dict(status='OK', data=filelist)
        except Exception as e:
            return dict(status='ERROR', data=str(e))

    def get(self, params=[]):
        try:
            filename = params[0]
            if not filename:
                return None
            with open(filename, 'rb') as fp:
                isifile = base64.b64encode(fp.read()).decode()
            return dict(status='OK', data_namafile=filename, data_file=isifile)
        except Exception as e:
            return dict(status='ERROR', data=str(e))

    def upload(self, params=[]):  
        try:
            if len(params) < 2:
                return dict(status='ERROR', data='Parameter tidak lengkap')
            
            filename = params[0]
            file_content_b64 = params[1]
            
            if not filename:
                return dict(status='ERROR', data='Nama file kosong')
            
            file_content = base64.b64decode(file_content_b64)
            
            with open(filename, 'wb') as fp:
                fp.write(file_content)
                
            return dict(status='OK', data=f'File {filename} berhasil diupload')
            
        except Exception as e:
            return dict(status='ERROR', data=str(e))
            
    def delete(self, params=[]):
        try:
            if len(params) < 1:
                return dict(status='ERROR', data='Parameter nama file diperlukan')
                
            filename = params[0]
            
            if not filename:
                return dict(status='ERROR', data='Nama file kosong')
            
            if not os.path.exists(filename):
                return dict(status='ERROR', data=f'File {filename} tidak ditemukan')
            
            os.remove(filename)
            
            return dict(status='OK', data=f'File {filename} berhasil dihapus')
            
        except Exception as e:
            return dict(status='ERROR', data=str(e))