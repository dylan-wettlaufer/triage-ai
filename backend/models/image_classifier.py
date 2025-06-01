# models/image_classifier.py
import torch
from PIL import Image
from transformers import ViTForImageClassification, ViTImageProcessor
import os
from config.settings import settings

class ImageClassifier:
    def __init__(self, model_path: str = None):
        """
        Initializes the ImageClassifier with a pre-trained model.
        If model_path is provided, it loads the model from the specified path.
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        try:
            self.model = ViTForImageClassification.from_pretrained(model_path) # Load the model from Hugging Face or local path
            self.processor = ViTImageProcessor.from_pretrained(model_path) # Load the image processor

            self.model.to(self.device) # Move model to GPU if available
            self.model.eval() # Set model to evaluation mode

            self.id2label = self.model.config.id2label # Mapping from label IDs to label names
            self.label2id = self.model.config.label2id # Mapping from label names to label IDs

            print(f"ImageClassifier initialized. Model loaded from: {model_path}")
            print(f"Classes: {self.id2label}")

        except Exception as e:
            raise RuntimeError(f"Failed to load model from {model_path}: {e}")
    

    async def classify_image(self, image_path: str) -> str:
        """
        Classifies an image and returns the predicted label.
        :param image_path: Path to the image file.
        :return: Predicted label as a string.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        


