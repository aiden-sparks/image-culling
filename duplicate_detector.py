"""Module for detecting duplicate images in a directory."""

import os
from typing import List
from collections import defaultdict, deque
import numpy as np
from keras.applications import ResNet50
from keras.preprocessing import image
from keras.applications.resnet50 import preprocess_input
from sklearn.metrics.pairwise import cosine_similarity

# # Old imports from the model author's code.
# from tensorflow.keras.applications import ResNet50
# from tensorflow.keras.preprocessing import image
# from tensorflow.keras.applications.resnet50 import preprocess_input

def extract_features(img_path, model):
    """
    Extracts a feature vector from an image. This function came with the model.
    """
    img = image.load_img(img_path, target_size=(224, 224))
    img_data = image.img_to_array(img)
    img_data = np.expand_dims(img_data, axis=0)
    img_data = preprocess_input(img_data)
    features = model.predict(img_data)
    return features.flatten()

def find_duplicates(image_dir, threshold=0.9):
    """
    Finds and counts duplicates. This function came with the model.
    """
    # Load the pre-trained ResNet50 model
    model = ResNet50(weights='imagenet', include_top=False, pooling='avg')

    image_features = {}
    for img_file in os.listdir(image_dir):
        img_path = os.path.join(image_dir, img_file)
        features = extract_features(img_path, model)
        image_features[img_file] = features

    feature_list = list(image_features.values())
    file_list = list(image_features.keys())

    num_images = len(file_list)
    similarity_matrix = np.zeros((num_images, num_images))

    for i in range(num_images):
        for j in range(i, num_images):
            if i != j:
                similarity = cosine_similarity(
                    [feature_list[i]],
                    [feature_list[j]]
                )[0][0]
                similarity_matrix[i][j] = similarity
                similarity_matrix[j][i] = similarity

    duplicates = set()
    for i in range(num_images):
        for j in range(i + 1, num_images):
            if similarity_matrix[i][j] > threshold:
                duplicates.add((file_list[j], file_list[i]))

    return duplicates

def group_duplicates(duplicate_pairs):
    """
    Takes pairs of duplicate images and creates a list of lists where each
    sub-list contains all images that are duplicates of each other.

    Args:
    - duplicate_pairs: a pair of filenames for duplicate images

    Returns:
    - A tuple containing the total number of duplicates and the list of lists
    containing each group of duplicate images
    """
    # Build adjacency list
    adj = defaultdict(set)
    for a, b in duplicate_pairs:
        adj[a].add(b)
        adj[b].add(a)

    visited = set()
    groups = []
    for node in adj:
        if node not in visited:
            group = []
            queue = deque([node])
            while queue:
                curr = queue.popleft()
                if curr not in visited:
                    visited.add(curr)
                    group.append(curr)
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            queue.append(neighbor)
            groups.append(group)
    count = 0
    for group in groups:
        count += len(group)
    return count, groups

def find_duplicate_images(local_dir_path: str, threshold: float = 0.9) -> List[List[str]]:
    """
    Find duplicate images given a local directory path and a duplicate
    matching threshold.

    Args:
    - local_dir_path: local path to the directory where the images live
    - threshold: value for how closely images need to match to be considered
    duplicates. Default is 0.9.

    Returns:
    - A list of lists, where each sub-list is a set of images that are
    duplicates of each other.
    """
    duplicates = find_duplicates(local_dir_path, threshold)
    count, groups = group_duplicates(duplicates)
    print(f"Found {count} duplicates.")
    print("Done finding duplicates.")
    return groups

# # Old code from the model's author
# if __name__ == "__main__":
#     import sys

#     image_dir = sys.argv[1] if len(sys.argv) > 1 else './images'
#     threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.9

#     duplicates = find_duplicates(image_dir, threshold)
#     count, groups = group_duplicates(duplicates)
#     print(f"Duplicate Images Count: {count}")
#     print(groups)
