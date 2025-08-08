from typing import List
from imagededup.methods import PHash
from duplicate_detector import group_duplicates

def find_duplicate_images_imagededup(local_dir_path: str, threshold: float = 0.9) -> List[List[str]]:
    phasher = PHash()

    encodings = phasher.encode_images(image_dir="./S3_IMAGES")
    duplicates = phasher.find_duplicates(encoding_map=encodings, max_distance_threshold=threshold)
    set_of_duplicates = set()

    for key in duplicates:
        for duplicate_of_key in duplicates[key]:
            set_of_duplicates.add((key, duplicate_of_key))

    count, groups = group_duplicates(set_of_duplicates)
    print(f"Found {count} duplicates.")
    return groups
