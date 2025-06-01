import os
import pandas as pd
import numpy as np
from PIL import Image
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import matplotlib.pyplot as plt

import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms

from transformers import ViTForImageClassification, ViTImageProcessor, TrainingArguments, Trainer
from sklearn.metrics import accuracy_score, f1_score

# Constants for dataset paths and metadata
DATASET_ROOT = "data/skin_lesion_images"
METADATA_FILE = os.path.join(DATASET_ROOT, 'HAM10000_metadata.csv')
IMAGE_DIR_PART1 = os.path.join(DATASET_ROOT, 'HAM10000_images_part1')
IMAGE_DIR_PART2 = os.path.join(DATASET_ROOT, 'HAM10000_images_part2')

MODEL_CHECKPOINT = "google/vit-base-patch16-224"
OUTPUT_DIR = "./skin_cancer_vit_model"

BATCH_SIZE = 16 # Adjust based on your GPU memory
NUM_EPOCHS = 3 # Start with a few epochs, adjust as needed
LEARNING_RATE = 2e-5 # Common fine-tuning learning rate

# --- 1. Load Data Paths and Labels ---
print("Loading metadata and image paths...")
df = pd.read_csv(METADATA_FILE)

# Map image_id to full path
image_paths = {}
for image_id in tqdm(df['image_id'].unique(), desc="Mapping image paths"):
    path1 = os.path.join(IMAGE_DIR_PART1, f"{image_id}.jpg")
    path2 = os.path.join(IMAGE_DIR_PART2, f"{image_id}.jpg")

    if os.path.exists(path1):
        image_paths[image_id] = path1
    elif os.path.exists(path2):
        image_paths[image_id] = path2
    else:
        raise FileNotFoundError(f"Image file not found for {image_id} in both parts.")
    
df["path"] = df["image_id"].map(image_paths)
df = df.dropna(subset=['path'])

# Map labels to integers
label_mapping = {
    'nv': 0, 'mel': 1, 'bkl': 2, 'bcc': 3,
    'akiec': 4, 'vasc': 5, 'df': 6
}

df['label_id'] = df['dx'].map(label_mapping)



