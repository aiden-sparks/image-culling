"""Module with utility functions for accessing S3 buckets that store images."""

import os
import shutil
from typing import List
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

def upload_files_ordered(local_dir_path: str, bucket_name: str, files_to_upload: List[str]) -> bool:
    """
    Uploads specific files from a local directory to an S3 bucket. Assumes
    that there exists a local .env file with the appropriate credentials.
    The first file uploaded will be labeled "1", the second file "2", and so
    on.

    Args:
    - local_dir_path: local path to the directory where the images live
    - bucket_name: name of the S3 bucket to upload to
    - files_to_upload: full filenames of the files in local_dir_path to upload
    
    Returns:
    - True if successful, False otherwise
    """
    # Load environment variables from .env file
    load_dotenv()

    # Create S3 client using aws credentials from .env environment variables.
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION')
    )

    # Loop over files_to_upload and upload matching files in local_dir_path
    all_success = True
    for idx, filename in enumerate(files_to_upload, start=1):
        local_path = os.path.join(local_dir_path, filename)
        if not os.path.isfile(local_path):
            print(f"File not found: {local_path}")
            all_success = False
            continue
        # Get the file extension
        _, ext = os.path.splitext(filename)
        s3_key = f"{idx}{ext}"
        try:
            s3_client.upload_file(local_path, bucket_name, s3_key)
            print(f"Uploaded {local_path} to bucket {bucket_name} as {s3_key}")
        except (BotoCoreError, ClientError) as e:
            print(f"Failed to upload {local_path}: {e}")
            all_success = False

    return all_success


def download_files(bucket_name: str, local_dir_path: str) -> bool:
    """
    Downloads all files from an S3 bucket to a local directory. Assumes
    that there exists a local .env file with the appropriate credentials.

    Args:
    - bucket_name: name of the S3 bucket
    - local_dir_path: local path to the directory where the images will
      be downloaded
    
    Returns:
    - True if successful, False otherwise
    """
    # Load environment variables from .env file
    load_dotenv()

    # Make the local directory if it doesn't exist.
    os.makedirs(local_dir_path, exist_ok=True)

    # Create S3 client using aws credentials from .env environment variables.
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION')
    )

    # Download all files in the S3 bucket
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    if 'Contents' in response:
        for obj in response['Contents']:
            key = obj['Key']
            local_path = os.path.join(local_dir_path, os.path.basename(key))
            s3_client.download_file(bucket_name, key, local_path)
            print(f"Downloaded {key} to {local_path}")
        return True
    else:
        print(f"No files found in bucket {bucket_name}.")
        return False

def output_files(local_dir_path: str, local_output_path: str, files_to_output: List[str]) -> bool:
    """
    Outputs specific files from a local directory to a local directory.

    Args:
    - local_dir_path: local path to the directory where the images live
    - local_output_path: local path to the directory where the images will
      be output
    - files_to_output: full filenames of the files in local_dir_path to output
    
    Returns:
    - True if successful, False otherwise
    """
    # Make the local output directory if it doesn't exist.
    os.makedirs(local_output_path, exist_ok=True)

    # Loop over files_to_output and output matching files in local_dir_path
    all_success = True
    for filename in files_to_output:
        local_path = os.path.join(local_dir_path, filename)
        if not os.path.isfile(local_path):
            print(f"File not found: {local_path}")
            all_success = False
            continue
        shutil.copy(local_path, local_output_path)
        print(f"Output {local_path} to {local_output_path}")

    return all_success
