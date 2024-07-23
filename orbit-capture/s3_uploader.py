import os
import boto3
from dotenv import load_dotenv
from tqdm import tqdm
from boto3.s3.transfer import TransferConfig, S3Transfer
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

load_dotenv()

MAX_UPLOAD_WORKERS = 5 # how many files can we upload to S3 concurrently

class S3Uploader:
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(S3Uploader, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):  # Avoid re-initialization
            self.s3_client = boto3.client('s3',
                                          aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                                          aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))
            self.initialized = True

    def upload_file_to_s3(self, bucket_name, local_file_path, s3_file_path, position):
        try:
            # Create a transfer configuration with the desired multipart threshold and chunk size
            config = TransferConfig(multipart_threshold=1024 * 25,  # 25MB
                                    max_concurrency=10,
                                    multipart_chunksize=1024 * 25,  # 25MB
                                    use_threads=True)

            # Create a tqdm progress bar
            file_size = os.path.getsize(local_file_path)
            progress_bar = tqdm(total=file_size, unit='B', unit_scale=True, desc=s3_file_path, position=position, leave=True)

            def progress_callback(bytes_transferred):
                progress_bar.update(bytes_transferred)

            # Create a S3Transfer object with the boto3 client and configuration
            transfer = S3Transfer(self.s3_client, config)

            transfer.upload_file(local_file_path, bucket_name, s3_file_path, callback=progress_callback)
            progress_bar.n = file_size
            progress_bar.last_print_n = file_size
            progress_bar.refresh()
            progress_bar.close()
            return True
        except Exception as e:
            progress_bar.clear()
            progress_bar.set_description_str(f"{s3_file_path} - Upload failed.")
            progress_bar.close()
            print(f"\nError uploading file {local_file_path} to {s3_file_path}: {e}")
            return False

    def upload_files_to_s3(self, bucket_name, local_file_paths, s3_file_paths):
        num_files = len(local_file_paths)
        with tqdm(total=num_files, desc='Overall Progress', position=0, leave=True) as overall_progress:
            with ThreadPoolExecutor(max_workers=MAX_UPLOAD_WORKERS) as executor:
                futures = []
                for idx, (local_file_path, s3_file_path) in enumerate(zip(local_file_paths, s3_file_paths)):
                    futures.append(executor.submit(self.upload_file_to_s3, bucket_name, local_file_path, s3_file_path, idx + 1))

                for future in as_completed(futures):
                    result = future.result()
                    overall_progress.update(1)
                    if not result:
                        print("One of the uploads failed.")