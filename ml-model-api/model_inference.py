"""
Model inference module for FlavorSnap.

Handles model loading, preprocessing, and prediction with caching support.
"""

import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
import numpy as np
import json
import os
import logging
from typing import Dict, List, Tuple, Any, Optional
import time

logger = logging.getLogger(__name__)

class ModelInference:
    """PyTorch model inference engine"""

    def __init__(self, model_path: str = None, classes_path: str = None):
        """
        Initialize model inference engine

        Args:
            model_path: Path to PyTorch model file
            classes_path: Path to classes text file
        """
        self.model_path = model_path or os.path.join(os.path.dirname(__file__), '..', 'models', 'model.pth')
        self.classes_path = classes_path or os.path.join(os.path.dirname(__file__), '..', 'food_classes.txt')
        self.model = None
        self.classes = []
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_model()
        self._load_classes()

        # Define preprocessing transforms
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def _load_model(self):
        """Load PyTorch model"""
        try:
            if not os.path.exists(self.model_path):
                logger.warning(f"Model file not found: {self.model_path}. Using dummy model.")
                self.model = self._create_dummy_model()
                return

            # Load ResNet18 model
            self.model = models.resnet18(pretrained=False)
            num_classes = len(self._read_classes_file())
            self.model.fc = nn.Linear(self.model.fc.in_features, num_classes)

            # Load trained weights
            state_dict = torch.load(self.model_path, map_location=self.device)
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()

            logger.info(f"Model loaded successfully from {self.model_path}")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.model = self._create_dummy_model()

    def _create_dummy_model(self):
        """Create a dummy model for testing when actual model is unavailable"""
        logger.warning("Creating dummy model for testing")
        model = models.resnet18(pretrained=True)
        # Keep the original 1000 classes for dummy predictions
        model.to(self.device)
        model.eval()
        return model

    def _load_classes(self):
        """Load class labels"""
        try:
            self.classes = self._read_classes_file()
            logger.info(f"Loaded {len(self.classes)} classes")
        except Exception as e:
            logger.error(f"Failed to load classes: {e}")
            self.classes = [f"class_{i}" for i in range(1000)]  # Fallback for dummy model

    def _read_classes_file(self) -> List[str]:
        """Read classes from file"""
        if not os.path.exists(self.classes_path):
            # Try relative path
            alt_path = os.path.join(os.path.dirname(__file__), '..', 'food_classes.txt')
            if os.path.exists(alt_path):
                self.classes_path = alt_path
            else:
                raise FileNotFoundError(f"Classes file not found: {self.classes_path}")

        with open(self.classes_path, 'r') as f:
            return [line.strip() for line in f.readlines() if line.strip()]

    def preprocess_image(self, image_path: str) -> torch.Tensor:
        """
        Preprocess image for model inference

        Args:
            image_path: Path to image file

        Returns:
            Preprocessed tensor
        """
        try:
            image = Image.open(image_path).convert('RGB')
            return self.transform(image).unsqueeze(0).to(self.device)
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            raise

    def predict(self, image_path: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Run model prediction on image

        Args:
            image_path: Path to image file
            top_k: Number of top predictions to return

        Returns:
            Prediction results dictionary
        """
        start_time = time.time()

        try:
            # Preprocess image
            input_tensor = self.preprocess_image(image_path)

            # Run inference
            with torch.no_grad():
                outputs = self.model(input_tensor)
                probabilities = torch.nn.functional.softmax(outputs[0], dim=0)

            # Get top k predictions
            top_probabilities, top_class_indices = torch.topk(probabilities, min(top_k, len(probabilities)))

            predictions = []
            for i in range(len(top_probabilities)):
                class_idx = top_class_indices[i].item()
                probability = top_probabilities[i].item()

                # Handle class indexing for dummy vs real model
                if len(self.classes) == 1000 and hasattr(self.model, 'fc') and self.model.fc.out_features != 1000:
                    # This is a dummy model with ImageNet classes
                    class_name = f"imagenet_class_{class_idx}"
                else:
                    class_name = self.classes[class_idx] if class_idx < len(self.classes) else f"class_{class_idx}"

                predictions.append({
                    'class': class_name,
                    'confidence': round(probability * 100, 2)
                })

            processing_time = time.time() - start_time

            result = {
                'predictions': predictions,
                'top_prediction': predictions[0] if predictions else None,
                'processing_time': round(processing_time, 3),
                'model_version': 'v1.0',
                'timestamp': time.time(),
                'cached': False  # Will be set to True by cache manager
            }

            logger.info(f"Prediction completed in {processing_time:.3f}s")
            return result

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            processing_time = time.time() - start_time
            return {
                'error': 'Prediction failed',
                'processing_time': round(processing_time, 3),
                'predictions': [],
                'cached': False
            }

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            'model_type': 'ResNet18',
            'num_classes': len(self.classes),
            'classes': self.classes,
            'device': str(self.device),
            'model_path': self.model_path,
            'classes_path': self.classes_path
        }


# Global model inference instance
model_inference = ModelInference()