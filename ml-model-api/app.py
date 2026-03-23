from flask import Flask, request, jsonify
from PIL import Image
import io
import torch
import torchvision.transforms as transforms
from torchvision import models
import torch.nn as nn
import time
import os
from datetime import datetime
import uuid

# Import model management components
from model_registry import ModelRegistry
from ab_testing import ABTestManager
from deployment_manager import ModelDeploymentManager, DeploymentConfig
from model_validator import ModelValidator, ValidationConfig
from api_endpoints import register_all_endpoints
from batch_processor import BatchProcessor
from batch_endpoints import register_batch_endpoints

app = Flask(__name__)

# Initialize model management components
model_registry = ModelRegistry()
ab_test_manager = ABTestManager(model_registry)
deployment_config = DeploymentConfig()
deployment_manager = ModelDeploymentManager(model_registry, deployment_config)
validation_config = ValidationConfig()
model_validator = ModelValidator(model_registry, validation_config)

# Initialize batch processor
batch_processor = BatchProcessor(model_registry, ab_test_manager)

# Model cache
cached_models = {}
class_names = ['Akara', 'Bread', 'Egusi', 'Moi Moi', 'Rice and Stew', 'Yam']

# Image transforms
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

def load_model(model_path: str) -> nn.Module:
    """Load model with caching"""
    if model_path not in cached_models:
        model = models.resnet18(weights='IMAGENET1K_V1')
        model.fc = nn.Linear(model.fc.in_features, len(class_names))
        model.load_state_dict(torch.load(model_path, map_location='cpu'))
        model.eval()
        cached_models[model_path] = model
    return cached_models[model_path]

def get_model_for_prediction(model_version: str = None, test_id: str = None):
    """Get appropriate model for prediction"""
    if model_version:
        # Use specified model version
        model_metadata = model_registry.get_model(model_version)
        if not model_metadata:
            raise ValueError(f"Model version {model_version} not found")
        model_path = model_metadata.model_path
        used_version = model_version
    elif test_id:
        # Use A/B test model selection
        used_version, actual_test_id = ab_test_manager.get_model_for_request(test_id)
        model_metadata = model_registry.get_model(used_version)
        model_path = model_metadata.model_path
    else:
        # Use active model or participate in A/B test
        try:
            used_version, actual_test_id = ab_test_manager.get_model_for_request()
            model_metadata = model_registry.get_model(used_version)
            model_path = model_metadata.model_path
            test_id = actual_test_id
        except ValueError:
            # No active tests, use active model
            active_model = model_registry.get_active_model()
            if not active_model:
                raise ValueError("No active model available")
            model_metadata = active_model
            model_path = model_metadata.model_path
            used_version = active_model.version
    
    model = load_model(model_path)
    return model, used_version, test_id

@app.route('/predict', methods=['POST'])
def predict():
    start_time = time.time()
    
    # Get request parameters
    model_version = request.form.get('model_version')
    test_id = request.form.get('test_id')
    user_id = request.form.get('user_id')
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    
    try:
        # Get appropriate model
        model, used_version, actual_test_id = get_model_for_prediction(model_version, test_id)
        
        # Process image
        image = Image.open(file.stream).convert('RGB')
        input_tensor = transform(image).unsqueeze(0)
        
        # Run inference
        with torch.no_grad():
            output = model(input_tensor)
            probabilities = torch.softmax(output, dim=1)
            confidence, predicted_class = torch.max(probabilities, 1)
            
        # Convert to label
        predicted_label = class_names[predicted_class.item()]
        confidence_score = confidence.item()
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Record prediction for A/B testing
        if actual_test_id:
            ab_test_manager.record_prediction(
                test_id=actual_test_id,
                model_version=used_version,
                image_path=file.filename,
                prediction=predicted_label,
                confidence=confidence_score,
                processing_time=processing_time,
                user_id=user_id
            )
        
        # Update deployment health metrics
        deployment_manager.update_health_metrics(
            model_version=used_version,
            response_time=processing_time,
            success=True
        )
        
        # Get top 3 predictions
        top_probs, top_indices = torch.topk(probabilities, 3)
        all_predictions = [
            {
                "label": class_names[idx.item()],
                "confidence": prob.item()
            }
            for prob, idx in zip(top_probs[0], top_indices[0])
        ]
        
        response = {
            'label': predicted_label,
            'confidence': round(confidence_score * 100, 2),
            'all_predictions': all_predictions,
            'processing_time': round(processing_time, 3),
            'model_version': used_version,
            'test_id': actual_test_id
        }
        
        return jsonify(response)
        
    except Exception as e:
        # Record error for deployment health
        if 'used_version' in locals():
            deployment_manager.update_health_metrics(
                model_version=used_version,
                response_time=time.time() - start_time,
                success=False,
                error_message=str(e)
            )
        
        return jsonify({'error': str(e)}), 500

# Register all management endpoints
register_all_endpoints(app, model_registry, ab_test_manager, deployment_manager, model_validator)

# Register batch processing endpoints
register_batch_endpoints(app, batch_processor)

if __name__ == '__main__':
    # Register existing model if not already registered
    active_model = model_registry.get_active_model()
    if not active_model and os.path.exists('models/best_model.pth'):
        model_registry.register_model(
            version='v1.0.0',
            model_path='models/best_model.pth',
            created_by='system',
            description='Initial ResNet18 model for Nigerian food classification',
            accuracy=0.942,
            epochs_trained=50
        )
        model_registry.activate_model('v1.0.0')
        print('Registered and activated initial model v1.0.0')
    
    app.run(debug=True, host='0.0.0.0', port=5000)
