from typing import Dict, List

from scorer import score_images
from duplicate_detector import find_duplicate_images

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
    # TODO: Ideally we're not using Dicts for this, especially with a large number of photos
    scored_images: Dict[str, Dict[str, float]] = score_images(local_dir_path)
    duplicates: List[List[str]] = find_duplicate_images(local_dir_path, 0.93)

    duplicates_to_remove: List[str] = find_duplicates_to_remove(scored_images, duplicates)
    # This may cull the number of images below cull_to
    num_dups: int = len(duplicates_to_remove)
    dup_count: int = 1
    for duplicate in duplicates_to_remove:
        print(f"Removing {duplicate} from scored images ({dup_count}/{num_dups})")
        dup_count += 1
        del scored_images[duplicate]
    print("Done removing duplicates.")

    # TODO: Throw out bad images here based on thresholds

    # Sort the images based on their average aesthetic score (ascending)
    sorted_images = dict(sorted(scored_images.items(), key=lambda item: sum(item[1].values()) / len(item[1])))
    print(f"There are {len(sorted_images)} images left.")
    for image in sorted_images:
        average: float = round(sum(scored_images[image].values()) / len(scored_images[image]), 2)
        print(f"    {image}: {average}")

    num_images_to_cull: int = len(scored_images) - cull_to
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

    print("Culling done.")
    return culled_img_list

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
            avg_score: float = sum(scored_images[image].values()) / len(scored_images[image])
            if avg_score > max_score:
                max_score = avg_score
                if best_image != "":
                    dups_to_remove.append(best_image)
                best_image = image
            else:
                dups_to_remove.append(image)

    return dups_to_remove
