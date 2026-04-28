from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import cv2
import numpy as np
import base64
import io
from PIL import Image
import json
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

router = APIRouter(prefix="/api/cv", tags=["computer-vision"])

# Pydantic models
class DetectionRequest(BaseModel):
    image_data: str  # Base64 encoded image
    confidence_threshold: float = 0.5
    max_detections: int = 100
    classes: Optional[List[str]] = None

class DetectionResponse(BaseModel):
    detections: List[Dict[str, Any]]
    processing_time: float
    image_size: Dict[str, int]
    model_info: Dict[str, Any]
    timestamp: datetime

class SegmentationRequest(BaseModel):
    image_data: str
    model_type: str = "semantic"
    output_format: str = "mask"

class SegmentationResponse(BaseModel):
    mask_data: str  # Base64 encoded mask
    segments: List[Dict[str, Any]]
    confidence_scores: List[float]
    processing_time: float
    timestamp: datetime

class FeatureExtractionRequest(BaseModel):
    image_data: str
    feature_type: str = "global"
    normalize: bool = True

class FeatureExtractionResponse(BaseModel):
    features: List[float]
    feature_vector: List[float]
    feature_names: List[str]
    processing_time: float
    timestamp: datetime

class QualityAssessmentRequest(BaseModel):
    image_data: str
    assessment_type: str = "comprehensive"

class QualityAssessmentResponse(BaseModel):
    overall_score: float
    sharpness_score: float
    brightness_score: float
    contrast_score: float
    noise_level: float
    recommendations: List[str]
    processing_time: float
    timestamp: datetime

class RealTimeProcessingRequest(BaseModel):
    stream_url: Optional[str] = None
    processing_type: str = "detection"
    fps_target: int = 30
    quality: str = "medium"

class RealTimeProcessingResponse(BaseModel):
    session_id: str
    status: str
    stream_info: Dict[str, Any]
    processing_config: Dict[str, Any]
    timestamp: datetime

# Computer Vision Engine
class ComputerVisionEngine:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.active_sessions = {}
        self.model_cache = {}
        self.performance_metrics = {
            total_requests: 0,
            avg_processing_time: 0,
            success_rate: 0,
            error_count: 0
        }
        
    async def load_model(self, model_name: str):
        """Load and cache computer vision models"""
        if model_name in self.model_cache:
            return self.model_cache[model_name]
        
        # Mock model loading (in real implementation, would load actual models)
        if model_name == "yolo":
            model_info = {
                "name": "YOLO v5",
                "classes": ["person", "car", "bicycle", "dog", "cat", "food"],
                "input_size": [640, 640],
                "confidence_threshold": 0.5,
                "nms_threshold": 0.4
            }
        elif model_name == "segmentation":
            model_info = {
                "name": "U-Net Segmentation",
                "classes": ["background", "food", "plate", "utensil"],
                "input_size": [512, 512],
                "output_channels": 4
            }
        elif model_name == "feature_extractor":
            model_info = {
                "name": "ResNet-50 Feature Extractor",
                "output_dim": 2048,
                "input_size": [224, 224],
                "pretrained": True
            }
        else:
            model_info = {"name": "Unknown", "status": "not_loaded"}
        
        self.model_cache[model_name] = model_info
        return model_info
    
    async def detect_objects(self, image_data: str, confidence_threshold: float = 0.5, max_detections: int = 100, classes: Optional[List[str]] = None):
        """Perform object detection on image"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
            image = Image.open(io.BytesIO(image_bytes))
            image_np = np.array(image)
            
            # Load detection model
            model_info = await self.load_model("yolo")
            
            # Mock detection results (in real implementation, would use actual model)
            detections = [
                {
                    "class": "food",
                    "confidence": 0.85,
                    "bbox": [100, 100, 200, 200],
                    "area": 10000,
                    "center": [150, 150]
                },
                {
                    "class": "plate",
                    "confidence": 0.72,
                    "bbox": [50, 50, 300, 300],
                    "area": 62500,
                    "center": [175, 175]
                }
            ]
            
            # Filter by confidence threshold
            detections = [d for d in detections if d["confidence"] >= confidence_threshold]
            
            # Filter by class if specified
            if classes:
                detections = [d for d in detections if d["class"] in classes]
            
            # Limit number of detections
            detections = detections[:max_detections]
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return {
                "detections": detections,
                "processing_time": processing_time,
                "image_size": {"width": image.width, "height": image.height},
                "model_info": model_info,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            self.performance_metrics["error_count"] += 1
            raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")
    
    async def segment_image(self, image_data: str, model_type: str = "semantic", output_format: str = "mask"):
        """Perform image segmentation"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Load segmentation model
            model_info = await self.load_model("segmentation")
            
            # Mock segmentation results (in real implementation, would use actual model)
            mask_size = (image.height, image.width)
            mask = np.random.randint(0, len(model_info["classes"]), mask_size)
            
            # Convert mask to base64
            mask_image = Image.fromarray(mask.astype(np.uint8))
            buffer = io.BytesIO()
            mask_image.save(buffer, format='PNG')
            mask_data = base64.b64encode(buffer.getvalue()).decode()
            
            # Generate segments
            segments = []
            for i, class_name in enumerate(model_info["classes"]):
                segment_pixels = np.sum(mask == i)
                if segment_pixels > 0:
                    segments.append({
                        "class": class_name,
                        "pixel_count": int(segment_pixels),
                        "percentage": float(segment_pixels / mask.size),
                        "bounding_box": self._get_bounding_box(mask == i)
                    })
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return {
                "mask_data": mask_data,
                "segments": segments,
                "confidence_scores": [0.8, 0.7, 0.6, 0.9][:len(segments)],
                "processing_time": processing_time,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            self.performance_metrics["error_count"] += 1
            raise HTTPException(status_code=500, detail=f"Segmentation failed: {str(e)}")
    
    async def extract_features(self, image_data: str, feature_type: str = "global", normalize: bool = True):
        """Extract features from image"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Load feature extraction model
            model_info = await self.load_model("feature_extractor")
            
            # Mock feature extraction (in real implementation, would use actual model)
            feature_vector = np.random.rand(model_info["output_dim"]).astype(np.float32)
            
            if normalize:
                feature_vector = feature_vector / np.linalg.norm(feature_vector)
            
            # Generate feature names
            feature_names = [f"feature_{i}" for i in range(len(feature_vector))]
            
            # Extract specific features
            features = [
                float(np.mean(feature_vector)),
                float(np.std(feature_vector)),
                float(np.max(feature_vector)),
                float(np.min(feature_vector)),
                float(np.median(feature_vector))
            ]
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return {
                "features": features,
                "feature_vector": feature_vector.tolist(),
                "feature_names": feature_names,
                "processing_time": processing_time,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            self.performance_metrics["error_count"] += 1
            raise HTTPException(status_code=500, detail=f"Feature extraction failed: {str(e)}")
    
    async def assess_quality(self, image_data: str, assessment_type: str = "comprehensive"):
        """Assess image quality"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
            image = Image.open(io.BytesIO(image_bytes))
            image_np = np.array(image)
            
            # Convert to grayscale for analysis
            if len(image_np.shape) == 3:
                gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
            else:
                gray = image_np
            
            # Calculate quality metrics
            sharpness_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            brightness_score = float(np.mean(gray) / 255.0)
            contrast_score = float(np.std(gray) / 255.0)
            
            # Calculate noise level
            if len(image_np.shape) == 3:
                noise = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
            else:
                noise = image_np
            noise_level = float(np.std(cv2.GaussianBlur(noise, (3, 3), 0) - noise))
            
            # Normalize scores to 0-1 range
            sharpness_score = min(sharpness_score / 1000, 1.0)
            brightness_score = max(0, min(brightness_score, 1.0))
            contrast_score = min(contrast_score * 2, 1.0)
            noise_level = min(noise_level / 50, 1.0)
            
            # Calculate overall score
            overall_score = (sharpness_score + brightness_score + contrast_score - noise_level) / 3
            overall_score = max(0, min(overall_score, 1.0))
            
            # Generate recommendations
            recommendations = []
            if sharpness_score < 0.3:
                recommendations.append("Image appears blurry - consider using a sharper image")
            if brightness_score < 0.3:
                recommendations.append("Image is too dark - consider increasing brightness")
            if brightness_score > 0.8:
                recommendations.append("Image is too bright - consider decreasing brightness")
            if contrast_score < 0.3:
                recommendations.append("Low contrast - consider enhancing image contrast")
            if noise_level > 0.5:
                recommendations.append("High noise level - consider denoising the image")
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return {
                "overall_score": overall_score,
                "sharpness_score": sharpness_score,
                "brightness_score": brightness_score,
                "contrast_score": contrast_score,
                "noise_level": noise_level,
                "recommendations": recommendations,
                "processing_time": processing_time,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            self.performance_metrics["error_count"] += 1
            raise HTTPException(status_code=500, detail=f"Quality assessment failed: {str(e)}")
    
    def _get_bounding_box(self, mask):
        """Get bounding box of a binary mask"""
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        
        if not np.any(rows) or not np.any(cols):
            return [0, 0, 0, 0]
        
        y_min, y_max = np.where(rows)[0][[0, -1]]
        x_min, x_max = np.where(cols)[0][[0, -1]]
        
        return [int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min)]
    
    async def start_real_time_processing(self, stream_url: str, processing_type: str, fps_target: int, quality: str):
        """Start real-time video processing"""
        session_id = str(uuid.uuid4())
        
        session_info = {
            "session_id": session_id,
            "stream_url": stream_url,
            "processing_type": processing_type,
            "fps_target": fps_target,
            "quality": quality,
            "status": "starting",
            "start_time": datetime.now(),
            "frame_count": 0,
            "processing_times": []
        }
        
        self.active_sessions[session_id] = session_info
        
        # Start processing in background
        asyncio.create_task(self._process_stream(session_id))
        
        return session_info
    
    async def _process_stream(self, session_id: str):
        """Process video stream in real-time"""
        session = self.active_sessions.get(session_id)
        if not session:
            return
        
        session["status"] = "active"
        
        # Mock stream processing (in real implementation, would process actual video stream)
        while session["status"] == "active":
            try:
                start_time = asyncio.get_event_loop().time()
                
                # Simulate frame processing
                await asyncio.sleep(1.0 / session["fps_target"])
                
                processing_time = asyncio.get_event_loop().time() - start_time
                session["processing_times"].append(processing_time)
                session["frame_count"] += 1
                
                # Keep only last 100 processing times
                if len(session["processing_times"]) > 100:
                    session["processing_times"] = session["processing_times"][-100:]
                
            except Exception as e:
                session["status"] = "error"
                session["error"] = str(e)
                break
    
    def stop_real_time_processing(self, session_id: str):
        """Stop real-time processing session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["status"] = "stopped"
            return True
        return False
    
    def get_session_info(self, session_id: str):
        """Get real-time processing session information"""
        return self.active_sessions.get(session_id)
    
    def get_performance_metrics(self):
        """Get engine performance metrics"""
        return self.performance_metrics

# Initialize CV engine
cv_engine = ComputerVisionEngine()

# Database dependency
def get_db():
    # This would be replaced with actual database session
    pass

# API Endpoints
@router.post("/detect", response_model=DetectionResponse)
async def detect_objects(request: DetectionRequest, db: Session = Depends(get_db)):
    """Detect objects in image"""
    try:
        result = await cv_engine.detect_objects(
            request.image_data,
            request.confidence_threshold,
            request.max_detections,
            request.classes
        )
        
        cv_engine.performance_metrics["total_requests"] += 1
        return DetectionResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Object detection failed: {str(e)}")

@router.post("/segment", response_model=SegmentationResponse)
async def segment_image(request: SegmentationRequest, db: Session = Depends(get_db)):
    """Segment image"""
    try:
        result = await cv_engine.segment_image(
            request.image_data,
            request.model_type,
            request.output_format
        )
        
        cv_engine.performance_metrics["total_requests"] += 1
        return SegmentationResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image segmentation failed: {str(e)}")

@router.post("/extract-features", response_model=FeatureExtractionResponse)
async def extract_features(request: FeatureExtractionRequest, db: Session = Depends(get_db)):
    """Extract features from image"""
    try:
        result = await cv_engine.extract_features(
            request.image_data,
            request.feature_type,
            request.normalize
        )
        
        cv_engine.performance_metrics["total_requests"] += 1
        return FeatureExtractionResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feature extraction failed: {str(e)}")

@router.post("/assess-quality", response_model=QualityAssessmentResponse)
async def assess_quality(request: QualityAssessmentRequest, db: Session = Depends(get_db)):
    """Assess image quality"""
    try:
        result = await cv_engine.assess_quality(
            request.image_data,
            request.assessment_type
        )
        
        cv_engine.performance_metrics["total_requests"] += 1
        return QualityAssessmentResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quality assessment failed: {str(e)}")

@router.post("/real-time/start", response_model=RealTimeProcessingResponse)
async def start_real_time_processing(request: RealTimeProcessingRequest, db: Session = Depends(get_db)):
    """Start real-time video processing"""
    try:
        session_info = await cv_engine.start_real_time_processing(
            request.stream_url,
            request.processing_type,
            request.fps_target,
            request.quality
        )
        
        return RealTimeProcessingResponse(**session_info)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start real-time processing: {str(e)}")

@router.post("/real-time/stop/{session_id}")
async def stop_real_time_processing(session_id: str, db: Session = Depends(get_db)):
    """Stop real-time processing session"""
    try:
        success = cv_engine.stop_real_time_processing(session_id)
        
        if success:
            return {"message": f"Session {session_id} stopped successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop real-time processing: {str(e)}")

@router.get("/real-time/status/{session_id}")
async def get_real_time_status(session_id: str, db: Session = Depends(get_db)):
    """Get real-time processing session status"""
    try:
        session_info = cv_engine.get_session_info(session_id)
        
        if session_info:
            return session_info
        else:
            raise HTTPException(status_code=404, detail="Session not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session status: {str(e)}")

@router.get("/performance")
async def get_performance_metrics(db: Session = Depends(get_db)):
    """Get computer vision engine performance metrics"""
    try:
        metrics = cv_engine.get_performance_metrics()
        
        # Calculate success rate
        if metrics["total_requests"] > 0:
            metrics["success_rate"] = (metrics["total_requests"] - metrics["error_count"]) / metrics["total_requests"]
        
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")

@router.get("/models")
async def get_available_models(db: Session = Depends(get_db)):
    """Get list of available computer vision models"""
    try:
        models = {
            "detection": {
                "name": "YOLO v5",
                "description": "Real-time object detection",
                "classes": ["person", "car", "bicycle", "dog", "cat", "food"],
                "input_size": [640, 640],
                "performance": {"fps": 30, "accuracy": 0.85}
            },
            "segmentation": {
                "name": "U-Net",
                "description": "Semantic segmentation",
                "classes": ["background", "food", "plate", "utensil"],
                "input_size": [512, 512],
                "performance": {"fps": 15, "accuracy": 0.78}
            },
            "feature_extraction": {
                "name": "ResNet-50",
                "description": "Deep feature extraction",
                "output_dim": 2048,
                "input_size": [224, 224],
                "performance": {"fps": 45, "accuracy": 0.92}
            }
        }
        
        return models
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model information: {str(e)}")

@router.post("/batch-process")
async def batch_process_images(
    images: List[str] = Form(...),
    processing_type: str = Form("detect"),
    confidence_threshold: float = Form(0.5),
    db: Session = Depends(get_db)
):
    """Process multiple images in batch"""
    try:
        results = []
        
        for i, image_data in enumerate(images):
            try:
                if processing_type == "detect":
                    result = await cv_engine.detect_objects(image_data, confidence_threshold)
                elif processing_type == "segment":
                    result = await cv_engine.segment_image(image_data)
                elif processing_type == "extract":
                    result = await cv_engine.extract_features(image_data)
                elif processing_type == "quality":
                    result = await cv_engine.assess_quality(image_data)
                else:
                    raise ValueError(f"Unknown processing type: {processing_type}")
                
                result["image_index"] = i
                results.append(result)
                
            except Exception as e:
                results.append({
                    "image_index": i,
                    "error": str(e),
                    "status": "failed"
                })
        
        return {
            "results": results,
            "total_images": len(images),
            "successful": len([r for r in results if "error" not in r]),
            "failed": len([r for r in results if "error" in r]),
            "processing_type": processing_type,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")
