import socket
import json
import base64
import logging
import os
import sys
import time
import random
import threading
import multiprocessing
import concurrent.futures
import argparse
from collections import defaultdict
import statistics
import csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stress_test.log"),
        logging.StreamHandler()
    ]
)

class StressTestRunner:
    def __init__(self, target_server=('localhost', 7778)):
        self.target_server = target_server
        self.test_results = {
            'upload': [],
            'download': [],
            'list': []
        }
        self.operation_success = {
            'upload': 0,
            'download': 0,
            'list': 0
        }
        self.operation_failures = {
            'upload': 0,
            'download': 0,
            'list': 0
        }
        
        # Create test files directory if it doesn't exist
        if not os.path.exists('test_files'):
            os.makedirs('test_files')
        
        # Create downloads directory if it doesn't exist
        if not os.path.exists('downloads'):
            os.makedirs('downloads')

    def create_test_file(self, file_size_mb):
        """Generate a test file of specified size"""
        test_filename = f"test_file_{file_size_mb}MB.bin"
        test_filepath = os.path.join('test_files', test_filename)
        
        # Check if the file already exists with the correct size
        if os.path.exists(test_filepath) and os.path.getsize(test_filepath) == file_size_mb * 1024 * 1024:
            logging.info(f"Test file {test_filename} already exists with correct size")
            return test_filepath
        
        logging.info(f"Generating test file: {test_filename} ({file_size_mb} MB)")
        with open(test_filepath, 'wb') as file_writer:
            # Generate chunks of 1MB to avoid memory issues
            data_chunk_size = 1024 * 1024  # 1MB
            for _ in range(file_size_mb):
                file_writer.write(os.urandom(data_chunk_size))
        
        logging.info(f"Test file generated: {test_filepath}")
        return test_filepath

    def transmit_command(self, cmd_string=""):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(600)  # Increased to 10 minutes for large files
        try:
            connect_start = time.time()
            client_socket.connect(self.target_server)
            connect_duration = time.time() - connect_start
            logging.debug(f"Connection established in {connect_duration:.2f}s")
            
            # Send command in chunks if it's large
            cmd_chunks = [cmd_string[i:i+65536] for i in range(0, len(cmd_string), 65536)]
            for chunk_data in cmd_chunks:
                client_socket.sendall((chunk_data).encode())
            
            # Send terminator
            client_socket.sendall("\r\n\r\n".encode())
            
            # Receive response in chunks
            response_data = "" 
            while True:
                try:
                    recv_data = client_socket.recv(1024*1024)  # Increased buffer size
                    if recv_data:
                        response_data += recv_data.decode()
                        if "\r\n\r\n" in response_data:
                            break
                    else:
                        break
                except socket.timeout:
                    logging.error("Socket timeout while receiving data")
                    return {'status': 'ERROR', 'data': 'Socket timeout while receiving data'}
            
            json_result = response_data.split("\r\n\r\n")[0]
            parsed_result = json.loads(json_result)
            return parsed_result
        except socket.timeout as timeout_ex:
            logging.error(f"Socket timeout: {str(timeout_ex)}")
            return {'status': 'ERROR', 'data': f'Socket timeout: {str(timeout_ex)}'}
        except ConnectionRefusedError:
            logging.error("Connection refused. Is the server running?")
            return {'status': 'ERROR', 'data': 'Connection refused. Is the server running?'}
        except Exception as general_ex:
            logging.error(f"Error in transmit_command: {str(general_ex)}")
            return {'status': 'ERROR', 'data': str(general_ex)}
        finally:
            client_socket.close()

    def execute_upload(self, target_file_path, worker_num):
        """Upload a file and measure performance"""
        operation_start = time.time()
        target_filename = os.path.basename(target_file_path)
        target_file_size = os.path.getsize(target_file_path)
        
        try:
            logging.info(f"Worker {worker_num}: Starting upload of {target_filename} ({target_file_size/1024/1024:.2f} MB)")
            
            # Read file in chunks to avoid memory issues with large files
            with open(target_file_path, 'rb') as file_reader:
                encoded_content = base64.b64encode(file_reader.read()).decode()
            
            # Prepare command
            upload_cmd = f"UPLOAD {target_filename} {encoded_content}"
            
            # Send command
            cmd_result = self.transmit_command(upload_cmd)
            
            operation_end = time.time()
            operation_time = operation_end - operation_start
            data_rate = target_file_size / operation_time if operation_time > 0 else 0
            
            if cmd_result['status'] == 'OK':
                logging.info(f"Worker {worker_num}: Upload successful - {target_filename} ({target_file_size/1024/1024:.2f} MB) in {operation_time:.2f}s - {data_rate/1024/1024:.2f} MB/s")
                self.operation_success['upload'] += 1
            else:
                logging.error(f"Worker {worker_num}: Upload failed - {target_filename}: {cmd_result['data']}")
                self.operation_failures['upload'] += 1
                
            return {
                'worker_id': worker_num,
                'operation': 'upload',
                'file_size': target_file_size,
                'duration': operation_time,
                'throughput': data_rate,
                'status': cmd_result['status']
            }
        except Exception as upload_ex:
            operation_end = time.time()
            operation_time = operation_end - operation_start
            logging.error(f"Worker {worker_num}: Upload exception - {target_filename}: {str(upload_ex)}")
            self.operation_failures['upload'] += 1
            return {
                'worker_id': worker_num,
                'operation': 'upload',
                'file_size': target_file_size,
                'duration': operation_time,
                'throughput': 0,
                'status': 'ERROR',
                'error': str(upload_ex)
            }

    def execute_download(self, target_filename, worker_num):
        """Download a file and measure performance"""
        operation_start = time.time()
        
        try:
            logging.info(f"Worker {worker_num}: Starting download of {target_filename}")
            
            download_cmd = f"GET {target_filename}"
            cmd_result = self.transmit_command(download_cmd)
            
            if cmd_result['status'] == 'OK':
                decoded_content = base64.b64decode(cmd_result['data_file'])
                downloaded_size = len(decoded_content)
                
                # Save to downloads folder with worker ID prefix to avoid conflicts
                save_path = os.path.join('downloads', f"worker{worker_num}_{target_filename}")
                with open(save_path, 'wb') as file_writer:
                    file_writer.write(decoded_content)
                
                operation_end = time.time()
                operation_time = operation_end - operation_start
                data_rate = downloaded_size / operation_time if operation_time > 0 else 0
                
                logging.info(f"Worker {worker_num}: Download successful - {target_filename} ({downloaded_size/1024/1024:.2f} MB) in {operation_time:.2f}s - {data_rate/1024/1024:.2f} MB/s")
                self.operation_success['download'] += 1
                
                return {
                    'worker_id': worker_num,
                    'operation': 'download',
                    'file_size': downloaded_size,
                    'duration': operation_time,
                    'throughput': data_rate,
                    'status': 'OK'
                }
            else:
                operation_end = time.time()
                operation_time = operation_end - operation_start
                logging.error(f"Worker {worker_num}: Download failed - {target_filename}: {cmd_result['data']}")
                self.operation_failures['download'] += 1
                
                return {
                    'worker_id': worker_num,
                    'operation': 'download',
                    'file_size': 0,
                    'duration': operation_time,
                    'throughput': 0,
                    'status': 'ERROR',
                    'error': cmd_result['data']
                }
        except Exception as download_ex:
            operation_end = time.time()
            operation_time = operation_end - operation_start
            logging.error(f"Worker {worker_num}: Download exception - {target_filename}: {str(download_ex)}")
            self.operation_failures['download'] += 1
            
            return {
                'worker_id': worker_num,
                'operation': 'download',
                'file_size': 0,
                'duration': operation_time,
                'throughput': 0,
                'status': 'ERROR',
                'error': str(download_ex)
            }

    def execute_list_files(self, worker_num):
        """Perform list operation and measure performance"""
        operation_start = time.time()
        
        try:
            list_cmd = "LIST"
            cmd_result = self.transmit_command(list_cmd)
            
            operation_end = time.time()
            operation_time = operation_end - operation_start
            
            if cmd_result['status'] == 'OK':
                files_count = len(cmd_result['data'])
                logging.info(f"Worker {worker_num}: List successful - {files_count} files in {operation_time:.2f}s")
                self.operation_success['list'] += 1
            else:
                logging.error(f"Worker {worker_num}: List failed: {cmd_result['data']}")
                self.operation_failures['list'] += 1
                
            return {
                'worker_id': worker_num,
                'operation': 'list',
                'duration': operation_time,
                'status': cmd_result['status']
            }
        except Exception as list_ex:
            operation_end = time.time()
            operation_time = operation_end - operation_start
            logging.error(f"Worker {worker_num}: List exception: {str(list_ex)}")
            self.operation_failures['list'] += 1
            
            return {
                'worker_id': worker_num,
                'operation': 'list',
                'duration': operation_time,
                'status': 'ERROR',
                'error': str(list_ex)
            }

    def clear_counters(self):
        """Reset success and fail counters"""
        self.operation_success = {
            'upload': 0,
            'download': 0,
            'list': 0
        }
        self.operation_failures = {
            'upload': 0,
            'download': 0,
            'list': 0
        }
        self.test_results = {
            'upload': [],
            'download': [],
            'list': []
        }

    def execute_stress_test(self, test_operation, file_size_mb, worker_pool_size, pool_type='thread'):
        """Run a stress test with specified parameters"""
        self.clear_counters()
        
        if test_operation not in ['upload', 'download', 'list']:
            logging.error(f"Invalid operation: {test_operation}")
            return
            
        logging.info(f"Starting {test_operation} stress test with {file_size_mb}MB files, {worker_pool_size} {pool_type} workers")
        
        # Generate test file if needed for upload tests
        target_test_file = None
        if test_operation == 'upload' or test_operation == 'download':
            target_test_file = self.create_test_file(file_size_mb)
        
        # First, ensure file exists on server for download tests
        if test_operation == 'download':
            logging.info(f"Ensuring test file exists on server for download test")
            setup_result = self.execute_upload(target_test_file, 0)  # Upload with worker ID 0 (setup)
            if setup_result['status'] != 'OK':
                logging.error(f"Failed to upload test file to server: {setup_result.get('error', 'Unknown error')}")
                return None
        
        # Choose the executor based on type
        if pool_type == 'thread':
            executor_class = concurrent.futures.ThreadPoolExecutor
        else:  # process
            executor_class = concurrent.futures.ProcessPoolExecutor
        
        # Run the stress test
        collected_results = []
        
        with executor_class(max_workers=worker_pool_size) as work_executor:
            submitted_futures = []
            
            for worker_idx in range(worker_pool_size):
                if test_operation == 'upload':
                    submitted_futures.append(work_executor.submit(self.execute_upload, target_test_file, worker_idx))
                elif test_operation == 'download':
                    test_file_name = os.path.basename(target_test_file)
                    submitted_futures.append(work_executor.submit(self.execute_download, test_file_name, worker_idx))
                else:  # list
                    submitted_futures.append(work_executor.submit(self.execute_list_files, worker_idx))
            
            for completed_future in concurrent.futures.as_completed(submitted_futures):
                try:
                    future_result = completed_future.result()
                    collected_results.append(future_result)
                    self.test_results[test_operation].append(future_result)
                except Exception as future_ex:
                    logging.error(f"Worker failed with exception: {str(future_ex)}")
        
        # Calculate statistics
        success_durations = [r['duration'] for r in collected_results if r['status'] == 'OK']
        success_throughputs = [r['throughput'] for r in collected_results if r.get('throughput', 0) > 0]
        
        if not success_durations:
            logging.warning("No successful operations to calculate statistics")
            return {
                'operation': test_operation,
                'file_size_mb': file_size_mb,
                'client_pool_size': worker_pool_size,
                'executor_type': pool_type,
                'success_count': self.operation_success[test_operation],
                'fail_count': self.operation_failures[test_operation]
            }
        
        calculated_stats = {
            'operation': test_operation,
            'file_size_mb': file_size_mb,
            'client_pool_size': worker_pool_size,
            'executor_type': pool_type,
            'avg_duration': statistics.mean(success_durations) if success_durations else 0,
            'median_duration': statistics.median(success_durations) if success_durations else 0,
            'min_duration': min(success_durations) if success_durations else 0,
            'max_duration': max(success_durations) if success_durations else 0,
            'avg_throughput': statistics.mean(success_throughputs) if success_throughputs else 0,
            'median_throughput': statistics.median(success_throughputs) if success_throughputs else 0,
            'min_throughput': min(success_throughputs) if success_throughputs else 0,
            'max_throughput': max(success_throughputs) if success_throughputs else 0,
            'success_count': self.operation_success[test_operation],
            'fail_count': self.operation_failures[test_operation]
        }
        
        logging.info(f"Test complete: {calculated_stats['success_count']} succeeded, {calculated_stats['fail_count']} failed")
        logging.info(f"Average duration: {calculated_stats['avg_duration']:.2f}s, Average throughput: {calculated_stats['avg_throughput']/1024/1024:.2f} MB/s")
        
        return calculated_stats

    def execute_all_test_combinations(self, test_file_sizes, test_client_pools, test_server_pools, test_executor_types, test_operations):
        """Run all test combinations and save results to CSV"""
        all_test_stats = []
        
        # For each server configuration, we'd need to manually restart the server
        for server_pool_size in test_server_pools:
            logging.info(f"Tests for server pool size: {server_pool_size}")
            logging.info("Please restart the server with the appropriate pool size!")
            input("Press Enter when the server is ready...")
            
            for executor_type in test_executor_types:
                for operation in test_operations:
                    for file_size in test_file_sizes:
                        for client_pool_size in test_client_pools:
                            test_stats = self.execute_stress_test(operation, file_size, client_pool_size, executor_type)
                            if test_stats:
                                test_stats['server_pool_size'] = server_pool_size
                                all_test_stats.append(test_stats)
        
        # Save all results to CSV
        self.export_results_to_csv(all_test_stats)
        
    def export_results_to_csv(self, all_test_stats):
        """Save test results to CSV file"""
        current_timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_csv_file = f"stress_test_results_{current_timestamp}.csv"
        
        with open(output_csv_file, 'w', newline='') as csv_file:
            csv_headers = [
                'operation', 'file_size_mb', 'client_pool_size', 'server_pool_size', 'executor_type',
                'avg_duration', 'median_duration', 'min_duration', 'max_duration',
                'avg_throughput', 'median_throughput', 'min_throughput', 'max_throughput',
                'success_count', 'fail_count'
            ]
            csv_writer = csv.DictWriter(csv_file, fieldnames=csv_headers)
            
            csv_writer.writeheader()
            for stats_data in all_test_stats:
                csv_writer.writerow(stats_data)
        
        logging.info(f"Results saved to {output_csv_file}")
        return output_csv_file

if __name__ == "__main__":
    cmd_parser = argparse.ArgumentParser(description='File Server Stress Test Client')
    cmd_parser.add_argument('--host', default='localhost', help='Server host (default: localhost)')
    cmd_parser.add_argument('--port', type=int, default=7778, help='Server port (default: 7778)')
    cmd_parser.add_argument('--operation', choices=['upload', 'download', 'list', 'all'], default='all', 
                        help='Operation to test (default: all)')
    cmd_parser.add_argument('--file-sizes', type=int, nargs='+', default=[10, 50, 100], 
                        help='File sizes in MB (default: 10 50 100)')
    cmd_parser.add_argument('--client-pools', type=int, nargs='+', default=[1, 5, 10], 
                        help='Client worker pool sizes (default: 1 5 10)')
    cmd_parser.add_argument('--server-pools', type=int, nargs='+', default=[1, 5, 10], 
                        help='Server worker pool sizes to test against (default: 1 5 10)')
    cmd_parser.add_argument('--executor', choices=['thread', 'process', 'both'], default='thread', 
                        help='Executor type (default: thread)')
    cmd_parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    parsed_args = cmd_parser.parse_args()
    
    # Set logging level
    if parsed_args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Prepare test parameters
    test_file_sizes = parsed_args.file_sizes
    test_client_pools = parsed_args.client_pools
    test_server_pools = parsed_args.server_pools
    
    if parsed_args.executor == 'both':
        test_executor_types = ['thread', 'process']
    else:
        test_executor_types = [parsed_args.executor]
        
    if parsed_args.operation == 'all':
        test_operations = ['list', 'download', 'upload']
    else:
        test_operations = [parsed_args.operation]
    
    # Create and run stress test client
    stress_tester = StressTestRunner((parsed_args.host, parsed_args.port))
    
    # Run a single test if specific parameters are provided
    if len(test_operations) == 1 and len(test_file_sizes) == 1 and len(test_client_pools) == 1 and len(test_server_pools) == 1:
        logging.info(f"Running a single test with operation={test_operations[0]}, file_size={test_file_sizes[0]}MB, client_pool={test_client_pools[0]}")
        single_test_stats = stress_tester.execute_stress_test(test_operations[0], test_file_sizes[0], test_client_pools[0], test_executor_types[0])
        if single_test_stats:
            single_test_stats['server_pool_size'] = test_server_pools[0]
            stress_tester.export_results_to_csv([single_test_stats])
    else:
        # Run all test combinations
        stress_tester.execute_all_test_combinations(test_file_sizes, test_client_pools, test_server_pools, test_executor_types, test_operations)