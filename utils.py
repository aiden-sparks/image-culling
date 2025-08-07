"""Utility functions for the culling pipeline"""

import os

def num_files_in_directory(local_dir_path: str) -> int:
    """
    Returns the number of files in a local directory.

    Args:
    - local_dir_path: local path to the directory where the files live

    Returns:
    - The number of files
    """
    return len([f for f in os.listdir(local_dir_path) if os.path.isfile(os.path.join(local_dir_path, f))])

    