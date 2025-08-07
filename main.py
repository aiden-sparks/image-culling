"""Main file for image culling POC"""

from typing import List
from culler import generate_culled_img_list
from s3_bucket_utils import upload_files_ordered, download_files, output_files
from utils import num_files_in_directory

DOWNLOAD_BUCKET_NAME = "culling-pipeline-test"
UPLOAD_BUCKET_NAME = "culling-pipeline-upload"
S3_IMAGES_DIR = "./S3_IMAGES"

if __name__ == "__main__":
    # # Download from S3 bucket
    # if not download_files(DOWNLOAD_BUCKET_NAME, S3_IMAGES_DIR):
    #     print("Failed to download files from bucket.")

    num_files: int = num_files_in_directory(S3_IMAGES_DIR)
    cull_to: int = 50
    print(f"There are {num_files} images to process. Culling to {cull_to} images...")

    # Generate cull list
    culled_img_list: List[str] = generate_culled_img_list(S3_IMAGES_DIR, cull_to)
    print("--------------- Final culled list ---------------")
    for img in culled_img_list:
        print(img)
    print("------------- / Final culled list ---------------")

    output_files(S3_IMAGES_DIR, "./PIPELINE_RESULTS", culled_img_list)

    # # Upload to S3 bucket
    # if not upload_files_ordered(S3_IMAGES_DIR, UPLOAD_BUCKET_NAME, culled_img_list):
    #     print("Failed to upload all files")

    # download_files(UPLOAD_BUCKET_NAME, "./PIPELINE_RESULTS")
