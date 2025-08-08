"""Functions for culling images in a local directory."""

import os
import shutil
from typing import Dict, List
import face_recognition

from scorer import score_images
from duplicate_detector import find_duplicate_images
# from imagededup_duplicate_detector import find_duplicate_images_imagededup

DUPLICATE_THRESHOLD = 0.93
# IMAGEDEDUP_THRESHOLD = 19

def generate_culled_img_list(local_dir_path: str, cull_to: int) -> List[str]:
    """
    Takes a local directory of images and returns a list of the images
    that should be kept, taking into account duplicates and using aesthetic
    scoring to cull the rest.

    Args:
    - local_dir_path: local path to the directory where the images live
    - cull_to: the number of images that should be left after the cull. The
    function may return a smaller list if there were many duplicates

    Returns:
    - A list of the images that should be kept
    """
    culled: List[str] = list()  # list of images that are thrown out ("culled")

    # TODO: Ideally we're not using Dicts for this, especially with a large number of photos
    scored_images: Dict[str, Dict[str, float]] = score_images(local_dir_path)
    # This is the original duplicate detector | "Best" value: 0.93
    duplicates: List[List[str]] = find_duplicate_images(local_dir_path, DUPLICATE_THRESHOLD)
    # This is the imagededup implementation | "Best" value: 19
    # duplicates: List[List[str]] = find_duplicate_images_imagededup(local_dir_path, IMAGEDEDUP_THRESHOLD)

    # Process duplicates for identical faces and save to folders for analysis.
    people_duplicates: List[List[str]] = list()
    people_dup_counter = 1
    for duplicate_set in duplicates:
        non_uniques = find_people_duplicates(local_dir_path, duplicate_set)
        if non_uniques:  # Only process if there are people duplicates
            # Save images to a ./PEOPLE_DUPS/#
            people_dup_dir = f"./PEOPLE_DUPS/{people_dup_counter}"
            os.makedirs(people_dup_dir, exist_ok=True)

            for image in non_uniques:
                src_path = os.path.join(local_dir_path, image)
                dst_path = os.path.join(people_dup_dir, image)
                if os.path.isfile(src_path):
                    shutil.copy(src_path, dst_path)
                    print(f"Copied people duplicate {src_path} to {dst_path}")

            people_dup_counter += 1
        people_duplicates.append(non_uniques)

    # Find best image out of each set of duplicates
    duplicates_to_remove: List[str] = find_duplicates_to_remove(scored_images, people_duplicates)
    # This may cull the number of images below cull_to
    num_dups: int = len(duplicates_to_remove)
    dup_count: int = 1
    for duplicate in duplicates_to_remove:
        print(f"Removing {duplicate} from scored images ({dup_count}/{num_dups})")
        dup_count += 1
        del scored_images[duplicate]
        culled.append(duplicate)
    print("Done removing duplicates.")

    # Rename kept files in PEOPLE_DUPS directories (this is just for testing)
    people_dup_counter = 1
    for people_dup_group in people_duplicates:
        if people_dup_group:  # Only process if there are people duplicates
            people_dup_dir = f"./PEOPLE_DUPS/{people_dup_counter}"
            if os.path.exists(people_dup_dir):
                for image in people_dup_group:
                    if image not in duplicates_to_remove:  # This is the kept file
                        old_path = os.path.join(people_dup_dir, image)
                        if os.path.isfile(old_path):
                            # Split filename and extension
                            name, ext = os.path.splitext(image)
                            new_filename = f"{name}_KEPT{ext}"
                            new_path = os.path.join(people_dup_dir, new_filename)
                            os.rename(old_path, new_path)
                            print(f"Renamed kept file: {old_path} -> {new_path}")
            people_dup_counter += 1

    # Throw out bad images based on aesthetic thresholds
    keys_to_remove = []
    for key, value in scored_images.items():
        if value["Overall"] < 2.50:
            print(f"Removing {key} with low Overall score.")
            keys_to_remove.append(key)
            culled.append(key)
        elif value["Quality"] < 2.50:
            print(f"Removing {key} with low Quality score.")
            keys_to_remove.append(key)
            culled.append(key)
        elif value["Composition"] < 2.75:
            print(f"Removing {key} with low Composition score.")
            keys_to_remove.append(key)
            culled.append(key)
        elif value["Lighting"] < 2.50:
            print(f"Removing {key} with low Lighting score.")
            keys_to_remove.append(key)
            culled.append(key)
        elif value["Depth of Field"] < 2.50:
            print(f"Removing {key} with low Depth of Field score.")
            keys_to_remove.append(key)
            culled.append(key)
        elif value["Content"] < 2.60:
            print(f"Removing {key} with low Content score.")
            keys_to_remove.append(key)
            culled.append(key)
    for key in keys_to_remove:
        del scored_images[key]

    # Sort the images based on their weighted average aesthetic score (ascending)
    sorted_images = dict(sorted(scored_images.items(), key=lambda item: item[1]["Quality"]*0.1 + item[1]["Composition"]*0.3 + item[1]["Depth of Field"]*0.2 + item[1]["Color"]*0.15 + item[1]["Lighting"]*0.25))
    print(f"There are {len(sorted_images)} images left.")

    # Cull down remaining images to cull_to value
    num_images_to_cull: int = max(0, len(scored_images) - cull_to)
    print(f"Culling {num_images_to_cull} images.")
    if num_images_to_cull < 0:
        num_images_to_cull = 0

    # Generate the list of images left after culling
    culled_img_list: List[str] = list()
    for image in sorted_images:
        if num_images_to_cull == 0:
            culled_img_list.append(image)
        else:
            num_images_to_cull -= 1

    # Save culled images to "./CULLED"
    culled_dir = "./CULLED"
    os.makedirs(culled_dir, exist_ok=True)
    for image in culled:
        src_path = os.path.join(local_dir_path, image)
        dst_path = os.path.join(culled_dir, image)
        if os.path.isfile(src_path):
            shutil.copy(src_path, dst_path)
            print(f"Exported {src_path} to {dst_path}")
        else:
            print(f"File not found for export: {src_path}")

    print("Culling done.")
    return culled_img_list

def image_faces_match(img1_encodings, img2_encodings) -> bool:
    """
    Given the encodings for two images, determine if all the faces in the first
    image have a matching face in the second image.

    Args:
    - img1_encodings: encoding for the first image
    - img2_encodings: encoding for the second image

    Returns:
    - True if every face has a match, False otherwise
    """
    for enc1 in img1_encodings:
        face_matched = False
        for enc2 in img2_encodings:
            match = face_recognition.compare_faces([enc1], enc2, tolerance=0.5)[0]
            if match:
                face_matched = True
                break
        if not face_matched:
            return False
    return True


def find_people_duplicates(local_dir_path: str, image_list: List[str]) -> List[str]:
    """
    Finds all the images in a list that share the same faces. This is helpful
    for differentiating between similarly-composed images of different people.

    Args:
    - local_dir_path: local path to the directory where the images live
    - image_list: list of images in the local path to analyze

    Returns:
    - A list of all images from the list with a non-unique set of faces
    """
    # TODO: There might be multiple distinct sets of images in the list that
    # are non-unique. The function currently lumps all these images together
    # in the return list.

    # Load all images and get their face encodings
    encodings_dict = {}
    for image_name in image_list:
        image_path = os.path.join(local_dir_path, image_name)
        img = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(img)
        encodings_dict[image_name] = encodings

    non_unique_images = set()
    unique_images = set()
    image_names = list(encodings_dict.keys())
    for img1 in image_names:
        if img1 in non_unique_images:
            print("Skipping non-unique image...")
            continue
        is_unique = True
        encs1 = encodings_dict[img1]
        for img2 in image_names:
            if img2 in unique_images:
                continue
            if img1 == img2:
                continue
            print(f"Comparing {img1} and {img2}...")
            encs2 = encodings_dict[img2]
            if abs(len(encs1) - len(encs2)) > 2:
                continue
            if image_faces_match(encs1, encs2):
                print("     Match!")
                non_unique_images.add(img1)
                non_unique_images.add(img2)
                is_unique = False
                break
        if is_unique:
            print("     No Match!")
            unique_images.add(img1)
    return list(non_unique_images)

def find_duplicates_to_remove(
    scored_images: Dict[str, Dict[str, float]],
    duplicates: List[List[str]]
) -> List[str]:
    """
    Takes a list of lists of duplicate images, as well as a Dict containing
    aesthetic scores for those images, and returns every image except the
    best image from each set of duplicates (based on their average scores).

    Args:
    - scored_images: Dict containing the image names and a Dict of their scores
    - duplicates: List containing Lists for each group of duplicates

    Returns:
    - A List of the file names for the duplicate images that should be removed.
    """
    # TODO: We can just take the scored_images Dict and delete the appropriate kv pairs here.

    # For each sub-list, find the current best image, and only add it to the list if a better
    # image is found.
    dups_to_remove: List[str] = list()
    for matching_images in duplicates:
        max_score: float = 0.0
        best_image: str = ""
        for image in matching_images:
            i = scored_images[image]
            avg_score: float = i["Quality"]*0.1 + i["Composition"]*0.3 + i["Depth of Field"]*0.2 + i["Color"]*0.15 + i["Lighting"]*0.25
            if avg_score > max_score:
                max_score = avg_score
                if best_image != "":
                    dups_to_remove.append(best_image)
                best_image = image
            else:
                dups_to_remove.append(image)

    return dups_to_remove
