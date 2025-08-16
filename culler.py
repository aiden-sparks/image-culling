"""Functions for culling images in a local directory."""

import os
import shutil
from typing import Dict, List
import face_recognition

from scorer import score_images
from duplicate_detector import find_dup_imgs
from utils import (
    all_images_have_datetime_original,
    group_imgs_by_datetime,
    num_files_in_directory,
)


DUPLICATE_THRESHOLD = 0.93  # Higher means fewer duplicates detected
DUP_THRESHOLD_FAST = 0.96  # Higher means fewer duplicates detected


def generate_culled_img_list(
    local_dir_path: str, cull_to: int, use_fast_culler=False, use_exif=True
) -> List[str]:
    """
    Takes a local directory of images and returns a list of the images
    that should be kept, taking into account duplicates and using aesthetic
    scoring to cull the rest.

    Args:
    - local_dir_path: local path to the directory where the images live
    - cull_to: the number of images that should be left after the cull. The
    function may return a smaller list if there were many duplicates
    - use_fast_culler: specifies whether the faster or slower culling algorithm
    should be used. The slower algorithm tends to be better at reducing
    duplicates.

    Returns:
    - A list of the images that should be kept
    """
    if not use_exif or not all_images_have_datetime_original(local_dir_path):
        if use_fast_culler:
            print(
                "use_fast_culler set to True. "
                "Using faster culling algorithm."
            )
            print(
                f"There are {num_files_in_directory(local_dir_path)} "
                "images to process. Culling to {cull_to} images..."
            )
            return gen_culled_list_fast(local_dir_path, cull_to)
        else:
            return gen_culled_list_slow(local_dir_path, cull_to)
    else:
        print("DateTimeOriginal EXIF field found. Culling with bursts.")
        print(
            f"There are {num_files_in_directory(local_dir_path)} "
            "images to process. Culling to {cull_to} images..."
        )
        return gen_culled_list_with_exif(
            local_dir_path, cull_to, group_imgs_by_datetime(local_dir_path)
        )


def gen_culled_list_with_exif(
    local_dir_path: str, cull_to: int, duplicates: List[List[str]]
) -> List[str]:
    """
    Takes a local directory of images with DateTimeOriginal EXIF fields and
    returns a list of the images that should be kept, assuming that images
    taken close together are duplicates and using aesthetic scoring to cull
    the rest.

    Args:
    - local_dir_path: local path to the directory where the images live
    - cull_to: the number of images that should be left after the cull. The
    function may return a smaller list if there were many duplicates

    Returns:
    - A list of the images that should be kept
    """
    culled: List[str] = list()  # list of images that are thrown out ("culled")

    # Score images
    scored_images: Dict[str, Dict[str, float]] = score_images(local_dir_path)
    num_images: int = len(scored_images)

    # Find best image out of each set of duplicates
    duplicates_to_remove: List[str] = find_dups_to_remove(
        scored_images, duplicates
    )

    # This may cull the number of images below cull_to
    num_dups: int = len(duplicates_to_remove)
    dup_count: int = 1
    print("Removing low-aesthetic scoring duplicates...")
    for duplicate in duplicates_to_remove:
        print(
            f"    Removing {duplicate} from scored images "
            "({dup_count}/{num_dups})"
        )
        dup_count += 1
        del scored_images[duplicate]
        culled.append(duplicate)
    print("Done removing duplicates.")

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

    # Sort the images based on their weighted average aesthetic score (ASC)
    sorted_images = dict(
        sorted(
            scored_images.items(),
            key=lambda item: item[1]["Quality"] * 0.1
            + item[1]["Composition"] * 0.3
            + item[1]["Depth of Field"] * 0.2
            + item[1]["Color"] * 0.15
            + item[1]["Lighting"] * 0.25,
        )
    )
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
        else:
            print(f"File not found for export: {src_path}")

    pct_culled: float = len(culled) / num_images
    print("STATS")
    num_dups = 0
    for dup_set in duplicates:
        num_dups += len(dup_set)
    print(
        f"    Found {num_dups} duplicates across {len(duplicates)} sets using "
        "threshold of {DUP_THRESHOLD_FAST}."
    )
    print(
        f"    Culled {len(culled)} images. Kept {len(culled_img_list)} images."
    )
    print(f"    Culled {round(pct_culled, 2)*100}% of images.")

    print("Culling done.")
    return culled_img_list


def gen_culled_list_fast(local_dir_path: str, cull_to: int) -> List[str]:
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

    # TODO: Ideally we're not using Dicts for this, especially with a large
    # number of photos
    scored_images: Dict[str, Dict[str, float]] = score_images(local_dir_path)
    num_images: int = len(scored_images)
    # This is the original duplicate detector | "Best" value: 0.93
    duplicates: List[List[str]] = find_dup_imgs(
        local_dir_path, DUP_THRESHOLD_FAST
    )

    # Save duplicate sets to numbered folders for analysis
    duplicate_sets_dir = "./DUPLICATE_SETS"
    os.makedirs(duplicate_sets_dir, exist_ok=True)

    for i, duplicate_set in enumerate(duplicates, 1):
        if len(duplicate_set) > 1:  # Only process actual duplicate sets
            set_dir = os.path.join(duplicate_sets_dir, str(i))
            os.makedirs(set_dir, exist_ok=True)

            for image in duplicate_set:
                src_path = os.path.join(local_dir_path, image)
                dst_path = os.path.join(set_dir, image)
                if os.path.isfile(src_path):
                    shutil.copy(src_path, dst_path)

    # Find best image out of each set of duplicates
    duplicates_to_remove: List[str] = find_dups_to_remove(
        scored_images, duplicates
    )

    # Mark kept images in duplicate sets by appending "KEPT" to filename
    for i, duplicate_set in enumerate(duplicates, 1):
        if len(duplicate_set) > 1:  # Only process actual duplicate sets
            set_dir = os.path.join(duplicate_sets_dir, str(i))
            if os.path.exists(set_dir):
                for image in duplicate_set:
                    if image not in duplicates_to_remove:
                        # This is the kept image
                        old_path = os.path.join(set_dir, image)
                        if os.path.isfile(old_path):
                            # Split filename and extension
                            name, ext = os.path.splitext(image)
                            new_filename = f"{name}_KEPT{ext}"
                            new_path = os.path.join(set_dir, new_filename)
                            os.rename(old_path, new_path)

    # This may cull the number of images below cull_to
    num_dups: int = len(duplicates_to_remove)
    dup_count: int = 1
    print("Removing low-aesthetic scoring duplicates...")
    for duplicate in duplicates_to_remove:
        print(
            f"    Removing {duplicate} from scored images "
            "({dup_count}/{num_dups})"
        )
        dup_count += 1
        del scored_images[duplicate]
        culled.append(duplicate)
    print("Done removing duplicates.")

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

    # Sort images based on their weighted average aesthetic score (ASC)
    sorted_images = dict(
        sorted(
            scored_images.items(),
            key=lambda item: item[1]["Quality"] * 0.1
            + item[1]["Composition"] * 0.3
            + item[1]["Depth of Field"] * 0.2
            + item[1]["Color"] * 0.15
            + item[1]["Lighting"] * 0.25,
        )
    )
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
        else:
            print(f"File not found for export: {src_path}")

    pct_culled: float = len(culled) / num_images
    print("STATS")
    num_dups = 0
    for dup_set in duplicates:
        num_dups += len(dup_set)
    print(
        f"    Found {num_dups} duplicates across {len(duplicates)} "
        "sets using threshold of {DUP_THRESHOLD_FAST}."
    )
    print(
        f"    Culled {len(culled)} images. Kept {len(culled_img_list)} images."
    )
    print(f"    Culled {round(pct_culled, 2)*100}% of images.")

    print("Culling done.")
    return culled_img_list


def gen_culled_list_slow(local_dir_path: str, cull_to: int) -> List[str]:
    """
    Takes a local directory of images and returns a list of the images
    that should be kept, taking into account duplicates and using aesthetic
    scoring to cull the rest. Will do its best to preserve near-duplicates
    that contain different faces.

    Args:
    - local_dir_path: local path to the directory where the images live
    - cull_to: the number of images that should be left after the cull. The
    function may return a smaller list if there were many duplicates

    Returns:
    - A list of the images that should be kept
    """
    culled: List[str] = list()  # list of images that are thrown out ("culled")

    # TODO: Ideally we're not using Dicts for this, especially with a large
    # number of photos.
    scored_images: Dict[str, Dict[str, float]] = score_images(local_dir_path)
    num_images: int = len(scored_images)
    # This is the original duplicate detector | "Best" value: 0.93
    duplicates: List[List[str]] = find_dup_imgs(
        local_dir_path, DUPLICATE_THRESHOLD
    )

    # Process duplicates for identical faces and save to folders for analysis.
    print("Identifying false positives via face recognition...", end=" ")
    people_duplicates: List[List[str]] = list()
    people_dup_counter = 1
    for duplicate_set in duplicates:
        people_groups = find_people_duplicates(local_dir_path, duplicate_set)
        if people_groups:  # Only process if there are people duplicates
            for group in people_groups:
                # Save images to a ./DUPLICATE_SETS/#
                people_dup_dir = f"./DUPLICATE_SETS/{people_dup_counter}"
                os.makedirs(people_dup_dir, exist_ok=True)

                for image in group:
                    src_path = os.path.join(local_dir_path, image)
                    dst_path = os.path.join(people_dup_dir, image)
                    if os.path.isfile(src_path):
                        shutil.copy(src_path, dst_path)

                people_dup_counter += 1
                people_duplicates.append(group)
    print("Done.")

    # Find best image out of each set of duplicates
    print("Finding best images in duplicate sets...", end=" ")
    duplicates_to_remove: List[str] = find_dups_to_remove(
        scored_images, people_duplicates
    )
    print("Done.")
    # This may cull the number of images below cull_to
    num_dups: int = len(duplicates_to_remove)
    dup_count: int = 1
    print("Removing low-aesthetic scoring duplicates...")
    for duplicate in duplicates_to_remove:
        print(
            f"    Removing {duplicate} from scored images "
            "({dup_count}/{num_dups})"
        )
        dup_count += 1
        del scored_images[duplicate]
        culled.append(duplicate)
    print("Done removing duplicates.")

    # Rename kept files in DUPLICATE_SETS directories
    people_dup_counter = 1
    for people_dup_group in people_duplicates:
        people_dup_dir = f"./DUPLICATE_SETS/{people_dup_counter}"
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

    # Sort the images based on their weighted average aesthetic score (ASC)
    sorted_images = dict(
        sorted(
            scored_images.items(),
            key=lambda item: item[1]["Quality"] * 0.1
            + item[1]["Composition"] * 0.3
            + item[1]["Depth of Field"] * 0.2
            + item[1]["Color"] * 0.15
            + item[1]["Lighting"] * 0.25,
        )
    )
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
        else:
            print(f"File not found for export: {src_path}")

    pct_culled: float = len(culled) / num_images
    print("STATS")
    num_dups = 0
    for dup_set in people_duplicates:
        num_dups += len(dup_set)
    print(
        f"    Found {num_dups} duplicates across {len(people_duplicates)} "
        "sets using threshold of {DUPLICATE_THRESHOLD}."
    )
    print(
        f"    Culled {len(culled)} images. Kept {len(culled_img_list)} images."
    )
    print(f"    Culled {round(pct_culled, 2)*100}% of images.")

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
            match = face_recognition.compare_faces(
                [enc1], enc2, tolerance=0.5
            )[0]
            if match:
                face_matched = True
                break
        if not face_matched:
            return False
    return True


def find_people_duplicates(
    local_dir_path: str, image_list: List[str]
) -> List[List[str]]:
    """
    Finds all the images in a list that share the same faces, grouped into
    distinct sets. This is helpful for differentiating between
    similarly-composed images of different people.

    Args:
    - local_dir_path: local path to the directory where the images live
    - image_list: list of images in the local path to analyze

    Returns:
    - A list of lists, where each inner list contains images that share the
    same faces.
    """
    # Load all images and get their face encodings
    encodings_dict = {}
    for image_name in image_list:
        image_path = os.path.join(local_dir_path, image_name)
        img = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(img)
        encodings_dict[image_name] = encodings

    # Build adjacency graph for images with matching faces
    adjacency = {}
    image_names = list(encodings_dict.keys())

    for i, img1 in enumerate(image_names):
        adjacency[img1] = []
        encs1 = encodings_dict[img1]

        for j, img2 in enumerate(image_names):
            if i == j:
                continue
            encs2 = encodings_dict[img2]

            # Skip if face count differs too much
            if abs(len(encs1) - len(encs2)) > 2:
                continue

            if image_faces_match(encs1, encs2):
                adjacency[img1].append(img2)

    # Find connected components using DFS
    visited = set()
    duplicate_groups = []

    def dfs(node, group):
        visited.add(node)
        group.append(node)
        for neighbor in adjacency[node]:
            if neighbor not in visited:
                dfs(neighbor, group)

    # Find all connected components with more than one image
    for image in image_names:
        if image not in visited and len(adjacency[image]) > 0:
            group = []
            dfs(image, group)
            if len(group) > 1:  # Only include groups with duplicates
                duplicate_groups.append(group)

    return duplicate_groups


def find_dups_to_remove(
    scored_images: Dict[str, Dict[str, float]], duplicates: List[List[str]]
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
    # TODO: We can just take the scored_images Dict and delete the appropriate
    # kv pairs here.

    # For each sub-list, find the current best image, and only add it to the
    # list if a better image is found.
    dups_to_remove: List[str] = list()
    for matching_images in duplicates:
        max_score: float = 0.0
        best_image: str = ""
        for image in matching_images:
            i = scored_images[image]
            avg_score: float = (
                i["Quality"] * 0.1
                + i["Composition"] * 0.3
                + i["Depth of Field"] * 0.2
                + i["Color"] * 0.15
                + i["Lighting"] * 0.25
            )
            if avg_score > max_score:
                max_score = avg_score
                if best_image != "":
                    dups_to_remove.append(best_image)
                best_image = image
            else:
                dups_to_remove.append(image)

    return dups_to_remove
