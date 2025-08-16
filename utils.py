"""Utility functions for the culling pipeline"""

import os
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS


def num_files_in_directory(local_dir_path: str) -> int:
    """
    Returns the number of files in a local directory.

    Args:
    - local_dir_path: local path to the directory where the files live

    Returns:
    - The number of files
    """
    return len(
        [
            f
            for f in os.listdir(local_dir_path)
            if os.path.isfile(os.path.join(local_dir_path, f))
        ]
    )


def all_images_have_datetime_original(local_dir_path: str) -> bool:
    """
    Checks if all images in a directory have the DateTimeOriginal EXIF field.

    Args:
    - local_dir_path: local path to the directory where the images live

    Returns:
    - True if all images have DateTimeOriginal, False otherwise
    """
    # Supported image extensions
    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".tiff",
        ".tif",
        ".bmp",
        ".gif",
    }

    # Get all files in the directory
    try:
        files = os.listdir(local_dir_path)
    except FileNotFoundError:
        print(f"Directory not found: {local_dir_path}")
        return False

    # Filter for image files
    image_files = [
        f for f in files if os.path.splitext(f.lower())[1] in image_extensions
    ]

    if not image_files:
        print(f"No image files found in directory: {local_dir_path}")
        return True  # Return True if no images to check

    # Check each image for DateTimeOriginal
    for image_file in image_files:
        image_path = os.path.join(local_dir_path, image_file)
        try:
            with Image.open(image_path) as img:
                # Get EXIF data
                exif = img._getexif()

                if exif is None:
                    print(f"No EXIF data found in: {image_file}")
                    return False

                # Find the DateTimeOriginal tag
                datetime_original = None
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == "DateTimeOriginal":
                        datetime_original = value
                        break

                if datetime_original is None:
                    print(f"No DateTimeOriginal found in: {image_file}")
                    return False

        except Exception as e:
            print(f"Error reading {image_file}: {str(e)}")
            return False

    return True


def group_imgs_by_datetime(local_dir_path: str) -> list[list[str]]:
    """
    Groups images by their DateTimeOriginal EXIF field. Images taken within
    one second of each other are grouped together, even if the total time
    range exceeds one second.

    Args:
    - local_dir_path: local path to the directory where the images live

    Returns:
    - A list of lists, where each inner list contains filenames of images
    taken within one second of each other
    """
    # Supported image extensions
    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".tiff",
        ".tif",
        ".bmp",
        ".gif",
    }

    # Get all files in the directory
    try:
        files = os.listdir(local_dir_path)
    except FileNotFoundError:
        print(f"Directory not found: {local_dir_path}")
        return []

    # Filter for image files
    image_files = [
        f for f in files if os.path.splitext(f.lower())[1] in image_extensions
    ]

    if not image_files:
        print(f"No image files found in directory: {local_dir_path}")
        return []

    # Extract DateTimeOriginal for each image
    image_datetimes = []
    for image_file in image_files:
        image_path = os.path.join(local_dir_path, image_file)
        try:
            with Image.open(image_path) as img:
                exif = img._getexif()

                if exif is None:
                    print(
                        f"Warning: No EXIF data found in {image_file}, "
                        "skipping"
                    )
                    continue

                # Find the DateTimeOriginal tag
                datetime_original = None
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == "DateTimeOriginal":
                        datetime_original = value
                        break

                if datetime_original is None:
                    print(
                        f"Warning: No DateTimeOriginal found in {image_file}, "
                        "skipping"
                    )
                    continue

                # Parse the datetime string
                try:
                    dt = datetime.strptime(
                        datetime_original, "%Y:%m:%d %H:%M:%S"
                    )
                    image_datetimes.append((image_file, dt))
                except ValueError as e:
                    print(
                        "Warning: Could not parse DateTimeOriginal "
                        f"\'{datetime_original}\' in {image_file}: {e}"
                    )
                    continue

        except Exception as e:
            print(f"Warning: Error reading {image_file}: {str(e)}")
            continue

    if not image_datetimes:
        print("No images with valid DateTimeOriginal found")
        return []

    # Sort by datetime
    image_datetimes.sort(key=lambda x: x[1])

    # Group images that are within one second of each other
    groups = []
    current_group = [image_datetimes[0][0]]  # Start with first image
    current_time = image_datetimes[0][1]

    for i in range(1, len(image_datetimes)):
        image_file, dt = image_datetimes[i]
        time_diff = abs((dt - current_time).total_seconds())

        if time_diff <= 1.0:  # Within one second
            current_group.append(image_file)
        else:
            # Start a new group
            groups.append(current_group)
            current_group = [image_file]
            current_time = dt

    # Add the last group
    groups.append(current_group)

    return groups
