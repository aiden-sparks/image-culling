"""Module for scoring images in a directory based on their aesthetics"""

import os
import glob
from typing import Dict
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from aesthetic_repo.aesthetic_scorer import AestheticScorer

def score_images(local_dir_path: str) -> Dict[str, Dict[str, float]]:
    """
    Scores images in a local directory based on their aesthetic qualities.

    Args:
    - local_dir_path: local path to the directory where the images live

    Returns:
    - A dictionary with filenames as the keys and a dict of qualities and
    their scores for that image as the values
    """
    print("Scoring images...")
    # Load processor and backbone model
    processor = CLIPProcessor.from_pretrained("rsinema/aesthetic-scorer")
    clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    backbone = clip_model.vision_model  # This matches the state dict keys

    # Instantiate model and load state dict
    model = AestheticScorer(backbone=backbone)
    state_dict = torch.load("./aesthetic_repo/model.pt", map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()

    # Find all .jpg, .png, and .webp images in the test images directory
    image_paths = (
        glob.glob(os.path.join(local_dir_path, "*.jpg")) +
        glob.glob(os.path.join(local_dir_path, "*.png")) +
        glob.glob(os.path.join(local_dir_path, "*.webp"))
    )

    # Dict with Image names and their set of scores
    output_scores: Dict[str, Dict[str, float]] = dict()

    num_images: int = len(image_paths)
    img_count: int = 1
    for image_path in image_paths:
        # Score image
        image_name = os.path.basename(image_path)
        # print(f"Scoring {image_name} ({img_count}/{num_images})")
        img_count += 1
        image = Image.open(image_path)
        inputs = processor(images=image, return_tensors="pt")["pixel_values"]

        # Get scores
        with torch.no_grad():
            scores = model(inputs)

        # Add score results
        output_scores[image_name] = {}
        aesthetic_categories = [
            "Overall",
            "Quality",
            "Composition",
            "Lighting", "Color",
            "Depth of Field",
            "Content"
        ]
        for category, score in zip(aesthetic_categories, scores):
            output_scores[image_name][category] = round(score.item(), 2)

    print("Done scoring images.")
    return output_scores
